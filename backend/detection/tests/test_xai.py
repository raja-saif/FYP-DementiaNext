"""Comprehensive tests for the Grad-CAM XAI module (detection/xai/gradcam_pytorch.py)."""

import base64
import tempfile
import os

import numpy as np
import torch
import torch.nn as nn
from django.test import TestCase

from detection.xai.gradcam_pytorch import (
    GradCAMError,
    _ensure_torch,
    _to_numpy,
    GradCAM,
    compute_gradcam,
    overlay_heatmap_on_image,
    save_gradcam_image,
    image_to_base64,
    run_gradcam_explanation,
    get_gradcam_for_detection,
)


# ---------------------------------------------------------------------------
# Helper models
# ---------------------------------------------------------------------------

class SimpleTestModel(nn.Module):
    """Multi-class CNN used by most tests (default 2 outputs)."""

    def __init__(self, num_classes=2):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(16, num_classes)

    def forward(self, x):
        x = self.conv1(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)


class BinaryTestModel(nn.Module):
    """Single-output binary model (sigmoid path)."""

    def __init__(self):
        super().__init__()
        self.conv1 = nn.Conv2d(3, 16, 3, padding=1)
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(16, 1)

    def forward(self, x):
        x = self.conv1(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        return self.fc(x)


class NoConvModel(nn.Module):
    """Model without any Conv2d layers."""

    def __init__(self):
        super().__init__()
        self.fc = nn.Linear(3 * 8 * 8, 2)

    def forward(self, x):
        return self.fc(x.view(x.size(0), -1))


class TwoConvModel(nn.Module):
    """Model with two Conv2d layers for named-layer look-up tests."""

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 8, 3, padding=1),
            nn.ReLU(),
            nn.Conv2d(8, 16, 3, padding=1),
            nn.ReLU(),
        )
        self.pool = nn.AdaptiveAvgPool2d(1)
        self.classifier = nn.Linear(16, 4)

    def forward(self, x):
        x = self.features(x)
        x = self.pool(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rand_input(batch=True):
    """Return a random (1, 3, 32, 32) float tensor."""
    t = torch.randn(1, 3, 32, 32)
    return t if batch else t.squeeze(0)


def _rand_image(h=64, w=64, channels=3):
    """Return a random uint8 numpy image."""
    if channels is None:
        return np.random.randint(0, 256, (h, w), dtype=np.uint8)
    return np.random.randint(0, 256, (h, w, channels), dtype=np.uint8)


# ===================================================================
# 1. GradCAMError
# ===================================================================
class TestGradCAMError(TestCase):
    """Test-XAI-001 — GradCAMError is importable and behaves like an exception."""

    def test_is_exception(self):
        self.assertTrue(issubclass(GradCAMError, Exception))

    def test_can_raise_and_catch(self):
        with self.assertRaises(GradCAMError):
            raise GradCAMError("test error")

    def test_message_preserved(self):
        try:
            raise GradCAMError("custom message")
        except GradCAMError as exc:
            self.assertEqual(str(exc), "custom message")


# ===================================================================
# 2. _ensure_torch / _to_numpy
# ===================================================================
class TestEnsureTorchAndToNumpy(TestCase):
    """Test-XAI-002 — _ensure_torch and _to_numpy utilities."""

    def test_ensure_torch_populates_globals(self):
        _ensure_torch()
        import detection.xai.gradcam_pytorch as mod
        self.assertIsNotNone(mod.torch)
        self.assertIsNotNone(mod.nn)
        self.assertIsNotNone(mod.F)

    def test_to_numpy_from_tensor(self):
        t = torch.tensor([1.0, 2.0, 3.0])
        arr = _to_numpy(t)
        self.assertIsInstance(arr, np.ndarray)
        np.testing.assert_array_almost_equal(arr, [1.0, 2.0, 3.0])

    def test_to_numpy_from_ndarray(self):
        a = np.array([4, 5, 6])
        arr = _to_numpy(a)
        self.assertIsInstance(arr, np.ndarray)
        np.testing.assert_array_equal(arr, a)

    def test_to_numpy_from_list(self):
        result = _to_numpy([7, 8, 9])
        self.assertIsInstance(result, np.ndarray)
        np.testing.assert_array_equal(result, [7, 8, 9])


# ===================================================================
# 3. GradCAM — binary model (1 output, sigmoid path)
# ===================================================================
class TestGradCAMBinary(TestCase):
    """Test-XAI-003 — GradCAM with a single-output binary model."""

    def setUp(self):
        self.model = BinaryTestModel().eval()
        self.input_tensor = _rand_input()

    def test_returns_tuple_of_three(self):
        gc = GradCAM(self.model)
        try:
            result = gc(self.input_tensor)
            self.assertEqual(len(result), 3)
        finally:
            gc.remove_hooks()

    def test_heatmap_shape_and_range(self):
        gc = GradCAM(self.model)
        try:
            heatmap, pred_class, confidence = gc(self.input_tensor)
            self.assertEqual(heatmap.ndim, 2)
            self.assertGreaterEqual(heatmap.min(), 0.0)
            self.assertLessEqual(heatmap.max(), 1.0 + 1e-6)
        finally:
            gc.remove_hooks()

    def test_predicted_class_is_0_or_1(self):
        gc = GradCAM(self.model)
        try:
            _, pred_class, _ = gc(self.input_tensor)
            self.assertIn(pred_class, (0, 1))
        finally:
            gc.remove_hooks()

    def test_confidence_in_range(self):
        gc = GradCAM(self.model)
        try:
            _, _, confidence = gc(self.input_tensor)
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)
        finally:
            gc.remove_hooks()

    def test_explicit_target_class(self):
        gc = GradCAM(self.model)
        try:
            _, pred_class, _ = gc(self.input_tensor, target_class=0)
            self.assertEqual(pred_class, 0)
        finally:
            gc.remove_hooks()


# ===================================================================
# 4. GradCAM — multi-class model (4 outputs, softmax path)
# ===================================================================
class TestGradCAMMultiClass(TestCase):
    """Test-XAI-004 — GradCAM with a 4-class model."""

    def setUp(self):
        self.model = SimpleTestModel(num_classes=4).eval()
        self.input_tensor = _rand_input()

    def test_heatmap_is_2d(self):
        gc = GradCAM(self.model)
        try:
            heatmap, _, _ = gc(self.input_tensor)
            self.assertEqual(heatmap.ndim, 2)
        finally:
            gc.remove_hooks()

    def test_predicted_class_in_valid_range(self):
        gc = GradCAM(self.model)
        try:
            _, pred_class, _ = gc(self.input_tensor)
            self.assertIn(pred_class, range(4))
        finally:
            gc.remove_hooks()

    def test_explicit_target_class(self):
        gc = GradCAM(self.model)
        try:
            _, pred_class, _ = gc(self.input_tensor, target_class=2)
            self.assertEqual(pred_class, 2)
        finally:
            gc.remove_hooks()

    def test_confidence_sums_to_one_approx(self):
        gc = GradCAM(self.model)
        try:
            with torch.no_grad():
                out = self.model(self.input_tensor)
                probs = torch.softmax(out, dim=1)
            self.assertAlmostEqual(probs.sum().item(), 1.0, places=5)
        finally:
            gc.remove_hooks()


# ===================================================================
# 5. GradCAM with explicit target_layer
# ===================================================================
class TestGradCAMExplicitLayer(TestCase):
    """Test-XAI-005 — GradCAM accepts an explicit target_layer argument."""

    def test_explicit_layer(self):
        model = TwoConvModel().eval()
        first_conv = model.features[0]
        gc = GradCAM(model, target_layer=first_conv)
        try:
            self.assertIs(gc.target_layer, first_conv)
            heatmap, _, _ = gc(_rand_input())
            self.assertEqual(heatmap.ndim, 2)
        finally:
            gc.remove_hooks()


# ===================================================================
# 6. GradCAM with target_layer_name
# ===================================================================
class TestGradCAMLayerByName(TestCase):
    """Test-XAI-006 — GradCAM finds a layer by name."""

    def test_find_by_name(self):
        model = TwoConvModel().eval()
        gc = GradCAM(model, target_layer_name="features.0")
        try:
            self.assertIs(gc.target_layer, model.features[0])
        finally:
            gc.remove_hooks()


# ===================================================================
# 7. _find_last_conv_layer raises for non-CNN
# ===================================================================
class TestFindLastConvLayerError(TestCase):
    """Test-XAI-007 — _find_last_conv_layer raises GradCAMError for non-CNN."""

    def test_raises_for_no_conv(self):
        model = NoConvModel().eval()
        with self.assertRaises(GradCAMError) as ctx:
            GradCAM(model)
        self.assertIn("No Conv2d layer", str(ctx.exception))


# ===================================================================
# 8. _find_layer_by_name raises for bad name
# ===================================================================
class TestFindLayerByNameError(TestCase):
    """Test-XAI-008 — _find_layer_by_name raises GradCAMError for bad name."""

    def test_raises_for_nonexistent_name(self):
        model = SimpleTestModel().eval()
        with self.assertRaises(GradCAMError) as ctx:
            GradCAM(model, target_layer_name="nonexistent_layer")
        self.assertIn("not found", str(ctx.exception))


# ===================================================================
# 9. GradCAM input validation (wrong dimensions)
# ===================================================================
class TestGradCAMInputValidation(TestCase):
    """Test-XAI-009 — GradCAM rejects tensors with wrong dimensions."""

    def test_rejects_2d_input(self):
        model = SimpleTestModel().eval()
        gc = GradCAM(model)
        try:
            with self.assertRaises(GradCAMError) as ctx:
                gc(torch.randn(32, 32))
            self.assertIn("3D", str(ctx.exception))
        finally:
            gc.remove_hooks()

    def test_rejects_5d_input(self):
        model = SimpleTestModel().eval()
        gc = GradCAM(model)
        try:
            with self.assertRaises(GradCAMError) as ctx:
                gc(torch.randn(1, 1, 3, 32, 32))
            self.assertIn("4D", str(ctx.exception))
        finally:
            gc.remove_hooks()

    def test_accepts_3d_input(self):
        model = SimpleTestModel().eval()
        gc = GradCAM(model)
        try:
            heatmap, _, _ = gc(_rand_input(batch=False))
            self.assertEqual(heatmap.ndim, 2)
        finally:
            gc.remove_hooks()

    def test_none_model_raises(self):
        with self.assertRaises(GradCAMError) as ctx:
            GradCAM(None)
        self.assertIn("Model is missing", str(ctx.exception))


# ===================================================================
# 10. overlay_heatmap_on_image — grayscale input
# ===================================================================
class TestOverlayGrayscale(TestCase):
    """Test-XAI-010 — overlay_heatmap_on_image with grayscale images."""

    def test_grayscale_2d(self):
        img = _rand_image(64, 64, channels=None)
        heatmap = np.random.rand(16, 16).astype(np.float32)
        original_rgb, heatmap_rgb, overlay_rgb = overlay_heatmap_on_image(img, heatmap)

        self.assertEqual(original_rgb.shape, (64, 64, 3))
        self.assertEqual(heatmap_rgb.shape, (64, 64, 3))
        self.assertEqual(overlay_rgb.shape, (64, 64, 3))
        self.assertEqual(original_rgb.dtype, np.uint8)

    def test_grayscale_single_channel(self):
        img = _rand_image(64, 64, channels=1)
        heatmap = np.random.rand(16, 16).astype(np.float32)
        original_rgb, _, _ = overlay_heatmap_on_image(img, heatmap)
        self.assertEqual(original_rgb.shape, (64, 64, 3))


# ===================================================================
# 11. overlay_heatmap_on_image — RGB input
# ===================================================================
class TestOverlayRGB(TestCase):
    """Test-XAI-011 — overlay_heatmap_on_image with RGB images."""

    def test_rgb(self):
        img = _rand_image(64, 64, channels=3)
        heatmap = np.random.rand(16, 16).astype(np.float32)
        original_rgb, heatmap_rgb, overlay_rgb = overlay_heatmap_on_image(img, heatmap)

        self.assertEqual(original_rgb.shape, (64, 64, 3))
        self.assertEqual(overlay_rgb.shape, (64, 64, 3))

    def test_rgba_truncated_to_rgb(self):
        img = _rand_image(64, 64, channels=4)
        heatmap = np.random.rand(16, 16).astype(np.float32)
        original_rgb, _, _ = overlay_heatmap_on_image(img, heatmap)
        self.assertEqual(original_rgb.shape[2], 3)


# ===================================================================
# 12. overlay_heatmap_on_image — alpha validation
# ===================================================================
class TestOverlayAlphaValidation(TestCase):
    """Test-XAI-012 — overlay_heatmap_on_image validates alpha range."""

    def test_alpha_below_zero(self):
        img = _rand_image(32, 32)
        heatmap = np.random.rand(8, 8).astype(np.float32)
        with self.assertRaises(GradCAMError) as ctx:
            overlay_heatmap_on_image(img, heatmap, alpha=-0.1)
        self.assertIn("alpha", str(ctx.exception))

    def test_alpha_above_one(self):
        img = _rand_image(32, 32)
        heatmap = np.random.rand(8, 8).astype(np.float32)
        with self.assertRaises(GradCAMError) as ctx:
            overlay_heatmap_on_image(img, heatmap, alpha=1.5)
        self.assertIn("alpha", str(ctx.exception))

    def test_alpha_boundary_zero(self):
        img = _rand_image(32, 32)
        heatmap = np.random.rand(8, 8).astype(np.float32)
        _, _, overlay = overlay_heatmap_on_image(img, heatmap, alpha=0.0)
        self.assertEqual(overlay.shape[2], 3)

    def test_alpha_boundary_one(self):
        img = _rand_image(32, 32)
        heatmap = np.random.rand(8, 8).astype(np.float32)
        _, _, overlay = overlay_heatmap_on_image(img, heatmap, alpha=1.0)
        self.assertEqual(overlay.shape[2], 3)

    def test_invalid_image_dims(self):
        img = np.random.rand(10).astype(np.float32)
        heatmap = np.random.rand(8, 8).astype(np.float32)
        with self.assertRaises(GradCAMError) as ctx:
            overlay_heatmap_on_image(img, heatmap)
        self.assertIn("Invalid image shape", str(ctx.exception))


# ===================================================================
# 13. save_gradcam_image
# ===================================================================
class TestSaveGradcamImage(TestCase):
    """Test-XAI-013 — save_gradcam_image writes to disk correctly."""

    def test_saves_and_returns_path(self):
        img = _rand_image(64, 64, channels=3)
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "test_heatmap.png")
            result = save_gradcam_image(save_path, img)
            self.assertTrue(result.exists())
            self.assertGreater(result.stat().st_size, 0)

    def test_creates_parent_dirs(self):
        img = _rand_image(32, 32, channels=3)
        with tempfile.TemporaryDirectory() as tmpdir:
            nested = os.path.join(tmpdir, "a", "b", "c", "img.png")
            result = save_gradcam_image(nested, img)
            self.assertTrue(result.exists())

    def test_invalid_shape_raises(self):
        img = np.random.randint(0, 256, (32, 32), dtype=np.uint8)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "bad.png")
            with self.assertRaises(GradCAMError) as ctx:
                save_gradcam_image(path, img)
            self.assertIn("RGB", str(ctx.exception))


# ===================================================================
# 14. image_to_base64
# ===================================================================
class TestImageToBase64(TestCase):
    """Test-XAI-014 — image_to_base64 produces a valid base64 string."""

    def test_returns_string(self):
        img = _rand_image(32, 32, channels=3)
        b64 = image_to_base64(img)
        self.assertIsInstance(b64, str)
        self.assertGreater(len(b64), 0)

    def test_decodeable(self):
        img = _rand_image(32, 32, channels=3)
        b64 = image_to_base64(img)
        decoded = base64.b64decode(b64)
        self.assertGreater(len(decoded), 0)

    def test_jpeg_format(self):
        img = _rand_image(32, 32, channels=3)
        b64 = image_to_base64(img, format="JPEG")
        decoded = base64.b64decode(b64)
        self.assertTrue(decoded[:2] == b'\xff\xd8')


# ===================================================================
# 15. run_gradcam_explanation (end-to-end)
# ===================================================================
class TestRunGradcamExplanation(TestCase):
    """Test-XAI-015 — run_gradcam_explanation end-to-end."""

    def setUp(self):
        self.model = SimpleTestModel(num_classes=3).eval()
        self.input_tensor = _rand_input()
        self.original_image = _rand_image(64, 64, channels=3)

    def test_returns_expected_keys(self):
        result = run_gradcam_explanation(
            self.model, self.input_tensor, self.original_image,
        )
        expected_keys = {
            "predicted_class", "predicted_class_name", "confidence",
            "layer_name", "heatmap", "original_rgb", "heatmap_rgb",
            "overlay_rgb", "overlay_base64", "heatmap_base64", "saved_path",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_confidence_in_range(self):
        result = run_gradcam_explanation(
            self.model, self.input_tensor, self.original_image,
        )
        self.assertGreaterEqual(result["confidence"], 0.0)
        self.assertLessEqual(result["confidence"], 1.0)

    def test_class_name_populated_when_given(self):
        names = ["A", "B", "C"]
        result = run_gradcam_explanation(
            self.model, self.input_tensor, self.original_image,
            class_names=names,
        )
        self.assertIn(result["predicted_class_name"], names)

    def test_class_name_none_without_names(self):
        result = run_gradcam_explanation(
            self.model, self.input_tensor, self.original_image,
        )
        self.assertIsNone(result["predicted_class_name"])

    def test_saved_path_none_when_not_given(self):
        result = run_gradcam_explanation(
            self.model, self.input_tensor, self.original_image,
        )
        self.assertIsNone(result["saved_path"])

    def test_saved_path_set_when_given(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "overlay.png")
            result = run_gradcam_explanation(
                self.model, self.input_tensor, self.original_image,
                save_path=path,
            )
            self.assertIsNotNone(result["saved_path"])
            self.assertTrue(result["saved_path"].exists())

    def test_overlay_base64_is_string(self):
        result = run_gradcam_explanation(
            self.model, self.input_tensor, self.original_image,
        )
        self.assertIsInstance(result["overlay_base64"], str)
        self.assertGreater(len(result["overlay_base64"]), 0)


# ===================================================================
# 16. get_gradcam_for_detection — binary
# ===================================================================
class TestGetGradcamForDetectionBinary(TestCase):
    """Test-XAI-016 — get_gradcam_for_detection with binary model."""

    def setUp(self):
        self.model = BinaryTestModel().eval()
        self.input_tensor = _rand_input()
        self.image = _rand_image(64, 64, channels=None)

    def test_returns_expected_keys(self):
        result = get_gradcam_for_detection(
            self.model, self.input_tensor, self.image, is_binary=True,
        )
        expected_keys = {
            "predicted_class", "predicted_class_name", "confidence",
            "layer_name", "overlay_base64", "heatmap_base64", "original_base64",
        }
        self.assertEqual(set(result.keys()), expected_keys)

    def test_default_class_names_binary(self):
        result = get_gradcam_for_detection(
            self.model, self.input_tensor, self.image, is_binary=True,
        )
        self.assertIn(result["predicted_class_name"], ["Normal", "Dementia"])

    def test_base64_fields_are_strings(self):
        result = get_gradcam_for_detection(
            self.model, self.input_tensor, self.image, is_binary=True,
        )
        for key in ("overlay_base64", "heatmap_base64", "original_base64"):
            self.assertIsInstance(result[key], str)
            self.assertGreater(len(result[key]), 0)


# ===================================================================
# 17. get_gradcam_for_detection — subtype
# ===================================================================
class TestGetGradcamForDetectionSubtype(TestCase):
    """Test-XAI-017 — get_gradcam_for_detection with subtype (4-class) model."""

    def setUp(self):
        self.model = SimpleTestModel(num_classes=4).eval()
        self.input_tensor = _rand_input()
        self.image = _rand_image(64, 64)

    def test_default_class_names_subtype(self):
        result = get_gradcam_for_detection(
            self.model, self.input_tensor, self.image, is_binary=False,
        )
        self.assertIn(
            result["predicted_class_name"],
            ["Alzheimer's", "Parkinson's", "FTD", "Normal"],
        )

    def test_custom_class_names(self):
        names = ["Alpha", "Beta", "Gamma", "Delta"]
        result = get_gradcam_for_detection(
            self.model, self.input_tensor, self.image,
            is_binary=False, class_names=names,
        )
        self.assertIn(result["predicted_class_name"], names)


# ===================================================================
# 18. compute_gradcam convenience function
# ===================================================================
class TestComputeGradcam(TestCase):
    """Test-XAI-018 — compute_gradcam convenience wrapper."""

    def setUp(self):
        self.model = SimpleTestModel(num_classes=3).eval()
        self.input_tensor = _rand_input()

    def test_returns_four_values(self):
        result = compute_gradcam(self.model, self.input_tensor)
        self.assertEqual(len(result), 4)

    def test_layer_name_is_string(self):
        _, _, _, layer_name = compute_gradcam(self.model, self.input_tensor)
        self.assertIsInstance(layer_name, str)
        self.assertNotEqual(layer_name, "unknown")

    def test_heatmap_normalized(self):
        heatmap, _, _, _ = compute_gradcam(self.model, self.input_tensor)
        self.assertGreaterEqual(heatmap.min(), 0.0)
        self.assertLessEqual(heatmap.max(), 1.0 + 1e-6)

    def test_explicit_target_layer(self):
        layer = self.model.conv1
        heatmap, _, _, name = compute_gradcam(
            self.model, self.input_tensor, target_layer=layer,
        )
        self.assertEqual(heatmap.ndim, 2)

    def test_explicit_target_class(self):
        _, pred_class, _, _ = compute_gradcam(
            self.model, self.input_tensor, target_class=1,
        )
        self.assertEqual(pred_class, 1)


# ===================================================================
# 19. GradCAM remove_hooks
# ===================================================================
class TestGradCAMRemoveHooks(TestCase):
    """Test-XAI-019 — remove_hooks clears handle list."""

    def test_handles_empty_after_remove(self):
        model = SimpleTestModel().eval()
        gc = GradCAM(model)
        self.assertGreater(len(gc.handles), 0)
        gc.remove_hooks()
        self.assertEqual(len(gc.handles), 0)

    def test_double_remove_is_safe(self):
        model = SimpleTestModel().eval()
        gc = GradCAM(model)
        gc.remove_hooks()
        gc.remove_hooks()
        self.assertEqual(len(gc.handles), 0)


# ===================================================================
# 20. Import test for detection.xai.__init__
# ===================================================================
class TestXAIPackageImports(TestCase):
    """Test-XAI-020 — detection.xai exposes public API via __init__.py."""

    def test_gradcam_error_importable(self):
        from detection.xai import GradCAMError as Err
        self.assertIs(Err, GradCAMError)

    def test_gradcam_class_importable(self):
        from detection.xai import GradCAM as GC
        self.assertIs(GC, GradCAM)

    def test_compute_gradcam_importable(self):
        from detection.xai import compute_gradcam as fn
        self.assertTrue(callable(fn))

    def test_overlay_importable(self):
        from detection.xai import overlay_heatmap_on_image as fn
        self.assertTrue(callable(fn))

    def test_save_importable(self):
        from detection.xai import save_gradcam_image as fn
        self.assertTrue(callable(fn))

    def test_image_to_base64_importable(self):
        from detection.xai import image_to_base64 as fn
        self.assertTrue(callable(fn))

    def test_run_gradcam_explanation_importable(self):
        from detection.xai import run_gradcam_explanation as fn
        self.assertTrue(callable(fn))

    def test_get_gradcam_for_detection_importable(self):
        from detection.xai import get_gradcam_for_detection as fn
        self.assertTrue(callable(fn))
