"""PyTorch Grad-CAM++ utilities for dementia MRI explainability.

This module provides Grad-CAM++ visualization for PyTorch CNN models,
specifically designed for the ResNet-34 based dementia detection models.

Grad-CAM++ uses second-order gradients to produce sharper, more spatially
precise heatmaps than vanilla Grad-CAM — particularly beneficial for
detecting small lesions and early-stage atrophy in brain MRI.

Reference: Chattopadhay et al., "Grad-CAM++: Generalized Gradient-based
Visual Explanations for Deep Convolutional Networks", WACV 2018.
"""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from typing import Any, Optional, Union

import cv2
import numpy as np

# Lazy imports for torch
torch = None
nn = None
F = None


class GradCAMError(Exception):
    """Raised when Grad-CAM cannot be generated due to invalid inputs/model."""


def _ensure_torch():
    """Import PyTorch lazily."""
    global torch, nn, F
    if torch is not None:
        return
    import torch as _torch
    import torch.nn as _nn
    import torch.nn.functional as _F
    torch = _torch
    nn = _nn
    F = _F


def _to_numpy(x: Any) -> np.ndarray:
    """Convert input array/tensor to a numpy array."""
    _ensure_torch()
    if isinstance(x, torch.Tensor):
        return x.detach().cpu().numpy()
    return np.asarray(x)


class GradCAM:
    """Grad-CAM implementation for PyTorch models.
    
    Generates class activation maps by computing gradients of the target class
    with respect to the feature maps of a convolutional layer.
    """
    
    def __init__(
        self,
        model: Any,
        target_layer: Optional[Any] = None,
        target_layer_name: Optional[str] = None,
    ):
        """Initialize GradCAM.
        
        Args:
            model: PyTorch model (must be in eval mode).
            target_layer: The convolutional layer to use for Grad-CAM.
                         If None, will auto-detect the last conv layer.
            target_layer_name: Name hint for finding the target layer.
        """
        _ensure_torch()
        
        if model is None:
            raise GradCAMError("Model is missing. Pass a loaded PyTorch model instance.")
        
        self.model = model
        self.model.eval()
        
        self.gradients = None
        self.activations = None
        self.handles = []
        
        # Find target layer
        if target_layer is not None:
            self.target_layer = target_layer
        elif target_layer_name is not None:
            self.target_layer = self._find_layer_by_name(target_layer_name)
        else:
            self.target_layer = self._find_last_conv_layer()
        
        self._register_hooks()
    
    def _find_layer_by_name(self, name: str) -> Any:
        """Find a layer by name in the model."""
        for n, module in self.model.named_modules():
            if name in n:
                return module
        raise GradCAMError(f"Layer '{name}' not found in model.")
    
    def _find_last_conv_layer(self) -> Any:
        """Find the last convolutional layer in the model."""
        last_conv = None
        for module in self.model.modules():
            if isinstance(module, nn.Conv2d):
                last_conv = module
        
        if last_conv is None:
            raise GradCAMError(
                "No Conv2d layer found in model. "
                "Ensure your model is a CNN with 2D convolutions."
            )
        return last_conv
    
    def _register_hooks(self):
        """Register forward and backward hooks on the target layer."""
        def forward_hook(module, input, output):
            self.activations = output.detach()
        
        def backward_hook(module, grad_input, grad_output):
            self.gradients = grad_output[0].detach()
        
        self.handles.append(
            self.target_layer.register_forward_hook(forward_hook)
        )
        self.handles.append(
            self.target_layer.register_full_backward_hook(backward_hook)
        )
    
    def remove_hooks(self):
        """Remove registered hooks."""
        for handle in self.handles:
            handle.remove()
        self.handles = []
    
    def __del__(self):
        """Clean up hooks on deletion."""
        self.remove_hooks()
    
    def __call__(
        self,
        input_tensor: Any,
        target_class: Optional[int] = None,
    ) -> tuple[np.ndarray, int, float]:
        """Generate Grad-CAM heatmap.
        
        Args:
            input_tensor: Input tensor of shape (1, C, H, W) or (C, H, W).
            target_class: Target class index. If None, uses predicted class.
        
        Returns:
            heatmap: Normalized heatmap array of shape (H, W) in range [0, 1].
            predicted_class: The class index used for Grad-CAM.
            confidence: Confidence score for the predicted class.
        """
        _ensure_torch()
        
        # Ensure input is a tensor with batch dimension
        if not isinstance(input_tensor, torch.Tensor):
            input_tensor = torch.tensor(input_tensor, dtype=torch.float32)
        
        if input_tensor.dim() == 3:
            input_tensor = input_tensor.unsqueeze(0)
        
        if input_tensor.dim() != 4:
            raise GradCAMError(
                f"Input tensor must be 3D (C,H,W) or 4D (B,C,H,W), got {input_tensor.dim()}D"
            )
        
        device = next(self.model.parameters()).device
        input_tensor = input_tensor.to(device)
        input_tensor.requires_grad_(True)
        
        # Forward pass
        output = self.model(input_tensor)
        
        # Handle different output formats (binary vs multi-class)
        if output.dim() == 1 or (output.dim() == 2 and output.shape[1] == 1):
            # Binary classification with sigmoid
            prob = torch.sigmoid(output.view(-1)[0])
            predicted_class = 1 if prob > 0.5 else 0
            confidence = float(prob.item()) if predicted_class == 1 else float(1 - prob.item())
            
            if target_class is None:
                target_class = predicted_class
            
            # For binary, use the raw output for gradients
            target_score = output.view(-1)[0]
            if target_class == 0:
                target_score = -target_score
        else:
            # Multi-class classification
            probs = F.softmax(output, dim=1)
            
            if target_class is None:
                predicted_class = int(torch.argmax(probs, dim=1).item())
            else:
                predicted_class = target_class
            
            confidence = float(probs[0, predicted_class].item())
            target_score = output[0, predicted_class]
        
        # Grad-CAM++ backward pass — need second-order gradients
        self.model.zero_grad()
        target_score.backward(retain_graph=True, create_graph=True)
        
        if self.gradients is None:
            raise GradCAMError("Failed to compute gradients. Check model architecture.")
        
        grads = self.gradients          # (1, C, H, W)
        acts  = self.activations        # (1, C, H, W)
        
        # Grad-CAM++ weight computation
        grads2 = grads.pow(2)
        grads3 = grads.pow(3)
        
        # Pixel-wise importance coefficient alpha
        spatial_sum = torch.sum(acts * grads3, dim=(2, 3), keepdim=True)
        denom = 2.0 * grads2 + spatial_sum + 1e-8
        alpha = F.relu(grads2) / denom
        
        # Channel weights: sum over spatial dims of alpha * relu(dy/dA)
        weights = torch.sum(alpha * F.relu(grads), dim=(2, 3), keepdim=True)
        
        # Weighted combination of activation maps
        cam = torch.sum(weights * acts, dim=1, keepdim=True)
        
        # ReLU and normalize
        cam = F.relu(cam)
        cam = cam.squeeze()
        
        if cam.max() > 0:
            cam = cam / cam.max()
        
        heatmap = cam.detach().cpu().numpy()
        
        return heatmap, predicted_class, confidence


def compute_gradcam(
    model: Any,
    input_tensor: Any,
    target_class: Optional[int] = None,
    target_layer: Optional[Any] = None,
) -> tuple[np.ndarray, int, float, str]:
    """Compute Grad-CAM heatmap for a PyTorch model.
    
    Args:
        model: Trained PyTorch model.
        input_tensor: Preprocessed input tensor (1, C, H, W).
        target_class: Optional class index. If None, uses predicted class.
        target_layer: Optional target conv layer. If None, auto-detects.
    
    Returns:
        heatmap: float32 array in range [0, 1], shape (Hf, Wf)
        predicted_class: int
        confidence: float
        layer_name: str
    """
    _ensure_torch()
    
    gradcam = GradCAM(model, target_layer=target_layer)
    
    # Get layer name
    layer_name = "unknown"
    for name, module in model.named_modules():
        if module is gradcam.target_layer:
            layer_name = name
            break
    
    try:
        heatmap, pred_class, confidence = gradcam(input_tensor, target_class)
    finally:
        gradcam.remove_hooks()
    
    return heatmap, pred_class, confidence, layer_name


def overlay_heatmap_on_image(
    original_image: Any,
    heatmap: np.ndarray,
    alpha: float = 0.45,
    colormap: int = cv2.COLORMAP_JET,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Create color heatmap and overlay on original image.
    
    Args:
        original_image: Original image as numpy array (H, W) or (H, W, C).
        heatmap: Grad-CAM heatmap array (Hf, Wf).
        alpha: Overlay transparency (0 to 1).
        colormap: OpenCV colormap constant.
    
    Returns:
        original_rgb: uint8 RGB image
        heatmap_color_rgb: uint8 RGB heatmap image
        overlay_rgb: uint8 RGB superimposed image
    """
    if not (0.0 <= alpha <= 1.0):
        raise GradCAMError("alpha must be between 0 and 1.")
    
    # Convert original to numpy and normalize
    img = _to_numpy(original_image).astype(np.float32)
    
    if img.ndim not in (2, 3):
        raise GradCAMError(f"Invalid image shape. Expected (H,W) or (H,W,C), got {img.shape}")
    
    # Normalize to [0, 255]
    img_min, img_max = float(img.min()), float(img.max())
    if img_max > img_min:
        img = (img - img_min) / (img_max - img_min)
    else:
        img = np.zeros_like(img)
    
    img_uint8 = (img * 255).clip(0, 255).astype(np.uint8)
    
    # Convert grayscale to RGB
    if img_uint8.ndim == 2:
        original_rgb = cv2.cvtColor(img_uint8, cv2.COLOR_GRAY2RGB)
    elif img_uint8.shape[-1] == 1:
        original_rgb = cv2.cvtColor(img_uint8, cv2.COLOR_GRAY2RGB)
    elif img_uint8.shape[-1] >= 3:
        original_rgb = img_uint8[..., :3]
    else:
        raise GradCAMError("Unsupported image channel configuration.")
    
    # Resize heatmap to match image size
    h, w = original_rgb.shape[:2]
    heatmap_resized = cv2.resize(heatmap, (w, h), interpolation=cv2.INTER_LINEAR)
    heatmap_resized = np.clip(heatmap_resized, 0, 1)
    heatmap_uint8 = (heatmap_resized * 255).astype(np.uint8)
    
    # Apply colormap (OpenCV uses BGR)
    heatmap_color_bgr = cv2.applyColorMap(heatmap_uint8, colormap)
    heatmap_color_rgb = cv2.cvtColor(heatmap_color_bgr, cv2.COLOR_BGR2RGB)
    
    # Create overlay
    overlay_rgb = cv2.addWeighted(original_rgb, 1.0 - alpha, heatmap_color_rgb, alpha, 0)
    
    return original_rgb, heatmap_color_rgb, overlay_rgb


def save_gradcam_image(
    save_path: Union[str, Path],
    image: np.ndarray,
) -> Path:
    """Save Grad-CAM image to disk.
    
    Args:
        save_path: Path to save the image.
        image: RGB image array (H, W, 3).
    
    Returns:
        Path object of saved file.
    """
    path = Path(save_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    img = _to_numpy(image)
    if img.ndim != 3 or img.shape[-1] != 3:
        raise GradCAMError(f"Image must be RGB with shape (H,W,3), got {img.shape}")
    
    # Convert RGB to BGR for OpenCV
    img_bgr = cv2.cvtColor(img.astype(np.uint8), cv2.COLOR_RGB2BGR)
    success = cv2.imwrite(str(path), img_bgr)
    
    if not success:
        raise GradCAMError(f"Failed to save image to: {path}")
    
    return path


def image_to_base64(image: np.ndarray, format: str = "PNG") -> str:
    """Convert numpy image array to base64 string.
    
    Args:
        image: RGB image array (H, W, 3).
        format: Image format (PNG, JPEG, etc.).
    
    Returns:
        Base64 encoded string of the image.
    """
    from PIL import Image as PILImage
    
    img = _to_numpy(image).astype(np.uint8)
    pil_img = PILImage.fromarray(img)
    
    buffer = BytesIO()
    pil_img.save(buffer, format=format)
    buffer.seek(0)
    
    return base64.b64encode(buffer.read()).decode('utf-8')


def run_gradcam_explanation(
    model: Any,
    input_tensor: Any,
    original_image: Any,
    target_class: Optional[int] = None,
    alpha: float = 0.45,
    save_path: Optional[Union[str, Path]] = None,
    class_names: Optional[list[str]] = None,
) -> dict[str, Any]:
    """End-to-end Grad-CAM explanation generation.
    
    Args:
        model: Trained PyTorch model.
        input_tensor: Preprocessed input tensor (1, C, H, W).
        original_image: Original image for visualization (H, W) or (H, W, C).
        target_class: Optional target class index.
        alpha: Overlay transparency.
        save_path: Optional path to save overlay image.
        class_names: Optional list of class names for display.
    
    Returns:
        Dictionary containing:
            - predicted_class: int
            - predicted_class_name: str (if class_names provided)
            - confidence: float
            - layer_name: str
            - heatmap: np.ndarray
            - original_rgb: np.ndarray
            - heatmap_rgb: np.ndarray
            - overlay_rgb: np.ndarray
            - overlay_base64: str (base64 encoded PNG)
            - saved_path: Path or None
    """
    _ensure_torch()
    
    # Compute Grad-CAM
    heatmap, pred_class, confidence, layer_name = compute_gradcam(
        model=model,
        input_tensor=input_tensor,
        target_class=target_class,
    )
    
    # Generate visualization
    original_rgb, heatmap_rgb, overlay_rgb = overlay_heatmap_on_image(
        original_image=original_image,
        heatmap=heatmap,
        alpha=alpha,
    )
    
    # Encode overlay as base64 for API response
    overlay_base64 = image_to_base64(overlay_rgb)
    heatmap_base64 = image_to_base64(heatmap_rgb)
    
    # Save if path provided
    saved_path = None
    if save_path is not None:
        saved_path = save_gradcam_image(save_path, overlay_rgb)
    
    # Get class name if available
    class_name = None
    if class_names is not None and 0 <= pred_class < len(class_names):
        class_name = class_names[pred_class]
    
    return {
        "predicted_class": pred_class,
        "predicted_class_name": class_name,
        "confidence": confidence,
        "layer_name": layer_name,
        "heatmap": heatmap,
        "original_rgb": original_rgb,
        "heatmap_rgb": heatmap_rgb,
        "overlay_rgb": overlay_rgb,
        "overlay_base64": overlay_base64,
        "heatmap_base64": heatmap_base64,
        "saved_path": saved_path,
    }


def get_gradcam_for_detection(
    model: Any,
    input_tensor: Any,
    original_image: Any,
    is_binary: bool = True,
    class_names: Optional[list[str]] = None,
) -> dict[str, Any]:
    """Convenience function for dementia detection Grad-CAM.
    
    Args:
        model: Trained dementia detection model.
        input_tensor: Preprocessed MRI tensor.
        original_image: Original MRI slice for visualization.
        is_binary: True for binary detection, False for subtype classification.
        class_names: Class names for multi-class model.
    
    Returns:
        Dictionary with Grad-CAM results and base64 encoded images.
    """
    if is_binary:
        class_names = class_names or ["Normal", "Dementia"]
    else:
        class_names = class_names or ["Alzheimer's", "Parkinson's", "FTD", "Normal"]
    
    result = run_gradcam_explanation(
        model=model,
        input_tensor=input_tensor,
        original_image=original_image,
        class_names=class_names,
    )
    
    # Encode original MRI image as base64
    original_base64 = image_to_base64(result["original_rgb"])
    
    return {
        "predicted_class": result["predicted_class"],
        "predicted_class_name": result["predicted_class_name"],
        "confidence": result["confidence"],
        "layer_name": result["layer_name"],
        "overlay_base64": result["overlay_base64"],
        "heatmap_base64": result["heatmap_base64"],
        "original_base64": original_base64,
    }
