"""TensorFlow/Keras Grad-CAM utilities for dementia MRI explainability.

This module is framework-agnostic to your classifier architecture as long as the
model has at least one 2D convolutional feature map (rank-4 output layer).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import cv2
import matplotlib.pyplot as plt
import numpy as np
import tensorflow as tf


class GradCAMError(Exception):
    """Raised when Grad-CAM cannot be generated due to invalid inputs/model."""


def _to_numpy(x: Any) -> np.ndarray:
    """Convert input array/tensor to a numpy array."""
    if isinstance(x, tf.Tensor):
        return x.numpy()
    return np.asarray(x)


def _validate_model(model: Optional[tf.keras.Model]) -> tf.keras.Model:
    """Validate model object and ensure it is a usable Keras model."""
    if model is None:
        raise GradCAMError("Model is missing. Pass a loaded tf.keras.Model instance.")

    if not isinstance(model, tf.keras.Model):
        raise GradCAMError("Invalid model type. Expected tf.keras.Model.")

    if not model.built:
        raise GradCAMError(
            "Model is not built yet. Run one forward pass or load a built model first."
        )

    return model


def _validate_preprocessed_tensor(preprocessed_tensor: Any) -> tf.Tensor:
    """Validate and normalize preprocessed MRI tensor shape to (1, H, W, C)."""
    arr = _to_numpy(preprocessed_tensor)

    if arr.ndim != 4:
        raise GradCAMError(
            "Invalid MRI tensor shape. Expected (1, H, W, C), "
            f"got {arr.shape}."
        )

    if arr.shape[0] != 1:
        raise GradCAMError(
            "Batch size must be 1 for Grad-CAM generation. "
            f"Got batch size {arr.shape[0]}."
        )

    if arr.shape[-1] <= 0:
        raise GradCAMError("Invalid channel dimension in MRI tensor.")

    return tf.convert_to_tensor(arr, dtype=tf.float32)


def _validate_original_image(original_mri: Any) -> np.ndarray:
    """Validate original MRI image and convert to uint8 RGB for visualization."""
    img = _to_numpy(original_mri)

    if img.ndim not in (2, 3):
        raise GradCAMError(
            "Invalid original MRI image shape. Expected (H, W) or (H, W, C), "
            f"got {img.shape}."
        )

    # Normalize image to [0, 255] uint8 for OpenCV/matplotlib display.
    img = img.astype(np.float32)
    img_min, img_max = float(img.min()), float(img.max())
    if img_max > img_min:
        img = (img - img_min) / (img_max - img_min)
    else:
        img = np.zeros_like(img, dtype=np.float32)

    img_uint8 = (img * 255.0).clip(0, 255).astype(np.uint8)

    # Convert grayscale or 1-channel images to RGB.
    if img_uint8.ndim == 2:
        return cv2.cvtColor(img_uint8, cv2.COLOR_GRAY2RGB)

    if img_uint8.shape[-1] == 1:
        return cv2.cvtColor(img_uint8, cv2.COLOR_GRAY2RGB)

    if img_uint8.shape[-1] >= 3:
        return img_uint8[..., :3]

    raise GradCAMError("Unsupported original MRI image channel configuration.")


def find_last_conv_layer(model: tf.keras.Model) -> tf.keras.layers.Layer:
    """Find the last layer with rank-4 output (typical conv feature map).

    This allows auto-detection across many CNN architectures without hardcoding
    layer names.
    """
    model = _validate_model(model)

    for layer in reversed(model.layers):
        output = getattr(layer, "output", None)
        if output is None:
            continue

        shape = getattr(output, "shape", None)
        if shape is None:
            continue

        if len(shape) == 4:
            return layer

    raise GradCAMError(
        "No convolution-like rank-4 layer found. "
        "Ensure your model is a CNN with 2D feature maps."
    )


def compute_gradcam(
    model: tf.keras.Model,
    preprocessed_tensor: Any,
    class_index: Optional[int] = None,
) -> tuple[np.ndarray, int, float, str]:
    """Compute Grad-CAM heatmap for the predicted or provided class index.

    Returns:
        heatmap: float32 array in range [0, 1], shape (Hf, Wf)
        predicted_class_index: int
        predicted_probability: float
        conv_layer_name: str
    """
    model = _validate_model(model)
    input_tensor = _validate_preprocessed_tensor(preprocessed_tensor)

    last_conv_layer = find_last_conv_layer(model)

    # Build model that exposes both conv activations and final predictions.
    grad_model = tf.keras.models.Model(
        inputs=model.inputs,
        outputs=[last_conv_layer.output, model.output],
    )

    with tf.GradientTape() as tape:
        conv_outputs, predictions = grad_model(input_tensor, training=False)

        if predictions.shape.rank != 2:
            raise GradCAMError(
                "Model output must be 2D (batch, classes) for multi-class Grad-CAM. "
                f"Got output shape {predictions.shape}."
            )

        if class_index is None:
            target_class = int(tf.argmax(predictions[0]).numpy())
        else:
            target_class = int(class_index)

        if target_class < 0 or target_class >= int(predictions.shape[-1]):
            raise GradCAMError(
                f"class_index {target_class} is out of range for "
                f"{int(predictions.shape[-1])} classes."
            )

        target_score = predictions[:, target_class]

    grads = tape.gradient(target_score, conv_outputs)
    if grads is None:
        raise GradCAMError(
            "Failed to compute gradients for Grad-CAM. "
            "Check that the model output depends on the detected conv layer."
        )

    # Global-average pool gradients over spatial dimensions.
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    conv_maps = conv_outputs[0]  # (Hf, Wf, channels)
    weighted_maps = conv_maps * pooled_grads
    heatmap = tf.reduce_sum(weighted_maps, axis=-1)

    # ReLU and normalization to [0, 1].
    heatmap = tf.nn.relu(heatmap)
    max_val = tf.reduce_max(heatmap)
    if float(max_val.numpy()) > 0.0:
        heatmap = heatmap / max_val
    else:
        heatmap = tf.zeros_like(heatmap)

    predicted_probability = float(predictions[0, target_class].numpy())

    return (
        heatmap.numpy().astype(np.float32),
        target_class,
        predicted_probability,
        last_conv_layer.name,
    )


def overlay_heatmap_on_mri(
    original_mri: Any,
    heatmap: np.ndarray,
    alpha: float = 0.45,
    colormap: int = cv2.COLORMAP_JET,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create color heatmap and overlay on original MRI image.

    Returns:
        original_rgb: uint8 RGB image
        heatmap_color_rgb: uint8 RGB heatmap image
        overlay_rgb: uint8 RGB superimposed image
    """
    if not (0.0 <= alpha <= 1.0):
        raise GradCAMError("alpha must be between 0 and 1.")

    original_rgb = _validate_original_image(original_mri)

    heatmap_np = _to_numpy(heatmap).astype(np.float32)
    if heatmap_np.ndim != 2:
        raise GradCAMError(
            f"Heatmap must be 2D, got shape {heatmap_np.shape}."
        )

    heatmap_np = np.clip(heatmap_np, 0.0, 1.0)

    h, w = original_rgb.shape[:2]
    heatmap_resized = cv2.resize(heatmap_np, (w, h), interpolation=cv2.INTER_LINEAR)
    heatmap_uint8 = (heatmap_resized * 255.0).astype(np.uint8)

    # OpenCV applies colormap in BGR, convert to RGB for consistent display.
    heatmap_color_bgr = cv2.applyColorMap(heatmap_uint8, colormap)
    heatmap_color_rgb = cv2.cvtColor(heatmap_color_bgr, cv2.COLOR_BGR2RGB)

    overlay_rgb = cv2.addWeighted(original_rgb, 1.0 - alpha, heatmap_color_rgb, alpha, 0)

    return original_rgb, heatmap_color_rgb, overlay_rgb


def display_gradcam_results(
    original_rgb: np.ndarray,
    heatmap_color_rgb: np.ndarray,
    overlay_rgb: np.ndarray,
    predicted_class_index: int,
    predicted_probability: float,
    figsize: tuple[int, int] = (16, 5),
) -> None:
    """Display original MRI, Grad-CAM heatmap, and overlay in one figure."""
    plt.figure(figsize=figsize)

    plt.subplot(1, 3, 1)
    plt.imshow(original_rgb, cmap="gray" if original_rgb.ndim == 2 else None)
    plt.title("Original MRI")
    plt.axis("off")

    plt.subplot(1, 3, 2)
    plt.imshow(heatmap_color_rgb)
    plt.title("Grad-CAM Heatmap")
    plt.axis("off")

    plt.subplot(1, 3, 3)
    plt.imshow(overlay_rgb)
    plt.title(
        f"Overlay | Class: {predicted_class_index} | "
        f"Prob: {predicted_probability:.4f}"
    )
    plt.axis("off")

    plt.tight_layout()
    plt.show()


def save_overlay_image(save_path: str | Path, overlay_rgb: np.ndarray) -> Path:
    """Save Grad-CAM overlay image to disk and return final path."""
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    overlay_np = _to_numpy(overlay_rgb)
    if overlay_np.ndim != 3 or overlay_np.shape[-1] != 3:
        raise GradCAMError(
            "Overlay must be an RGB image with shape (H, W, 3)."
        )

    # cv2.imwrite expects BGR.
    overlay_bgr = cv2.cvtColor(overlay_np.astype(np.uint8), cv2.COLOR_RGB2BGR)
    ok = cv2.imwrite(str(path), overlay_bgr)

    if not ok:
        raise GradCAMError(f"Failed to save overlay image to: {path}")

    return path


def run_gradcam_explanation(
    model: tf.keras.Model,
    preprocessed_mri_tensor: Any,
    original_mri_image: Any,
    class_index: Optional[int] = None,
    alpha: float = 0.45,
    show: bool = True,
    save_path: Optional[str | Path] = None,
) -> dict[str, Any]:
    """End-to-end helper to compute, visualize, and optionally save Grad-CAM.

    Args:
        model: Trained tf.keras.Model for multi-class classification.
        preprocessed_mri_tensor: Tensor/array with shape (1, H, W, C).
        original_mri_image: Original MRI numpy array (H, W) or (H, W, C).
        class_index: Optional class index override. If None, uses predicted class.
        alpha: Overlay transparency between 0 and 1.
        show: If True, displays three-panel visualization.
        save_path: If provided, saves overlay image to this path.

    Returns:
        Dictionary containing prediction metadata and generated images.
    """
    heatmap, pred_class, pred_prob, conv_layer_name = compute_gradcam(
        model=model,
        preprocessed_tensor=preprocessed_mri_tensor,
        class_index=class_index,
    )

    original_rgb, heatmap_rgb, overlay_rgb = overlay_heatmap_on_mri(
        original_mri=original_mri_image,
        heatmap=heatmap,
        alpha=alpha,
    )

    print(f"Predicted class index: {pred_class}")
    print(f"Predicted probability: {pred_prob:.6f}")
    print(f"Grad-CAM conv layer: {conv_layer_name}")

    if show:
        display_gradcam_results(
            original_rgb=original_rgb,
            heatmap_color_rgb=heatmap_rgb,
            overlay_rgb=overlay_rgb,
            predicted_class_index=pred_class,
            predicted_probability=pred_prob,
        )

    saved_to = None
    if save_path is not None:
        saved_to = save_overlay_image(save_path=save_path, overlay_rgb=overlay_rgb)

    return {
        "predicted_class_index": pred_class,
        "predicted_probability": pred_prob,
        "conv_layer_name": conv_layer_name,
        "heatmap": heatmap,
        "original_rgb": original_rgb,
        "heatmap_rgb": heatmap_rgb,
        "overlay_rgb": overlay_rgb,
        "saved_path": saved_to,
    }
