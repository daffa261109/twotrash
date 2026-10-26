"""Kontrak kamera diuji tanpa Pi, USB, OpenCV, atau picamera2 terpasang."""
import os
import sys
import types
import unittest
from unittest.mock import Mock, patch

from trash2trace.camera import USBCamera, open_camera


class Frame:
    size = 640 * 480 * 3
    ndim = 3
    shape = (480, 640, 3)

    def __init__(self, bgr=(10, 20, 200)):
        self.bgr = bgr

    def __getitem__(self, key):
        return types.SimpleNamespace(mean=lambda: self.bgr[key[2]])


class CameraTests(unittest.TestCase):
    def setUp(self):
        self.capture = Mock()
        self.capture.isOpened.return_value = True
        self.capture.read.return_value = (True, Frame())
        self.capture.grab.return_value = True
        self.cv2 = types.SimpleNamespace(
            VideoCapture=Mock(return_value=self.capture),
            VideoWriter_fourcc=Mock(return_value=123),
            cvtColor=Mock(side_effect=lambda frame, code: frame.bgr[::-1]),
            CAP_V4L2=200, CAP_PROP_FOURCC=6, CAP_PROP_FRAME_WIDTH=3,
            CAP_PROP_FRAME_HEIGHT=4, CAP_PROP_FPS=5, CAP_PROP_BUFFERSIZE=38,
            COLOR_BGR2RGB=4,
        )
        self.modules = patch.dict(sys.modules, {"cv2": self.cv2})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_usb_frames_are_rgb_and_old_frames_are_discarded(self):
        camera = USBCamera("0", (640, 480), 15)
        self.assertEqual(camera.capture_array(), (200, 20, 10))
        self.assertEqual(self.capture.grab.call_count, 3)
        self.cv2.VideoCapture.assert_called_once_with(0, 200)

    def test_stable_device_path_is_preserved_and_close_is_idempotent(self):
        path = "/dev/v4l/by-id/usb-camera-video-index0"
        camera = USBCamera(path, (640, 480), 15)
        self.cv2.VideoCapture.assert_called_once_with(path, 200)
        camera.close()
        camera.close()
        self.capture.release.assert_called_once()
        with self.assertRaisesRegex(RuntimeError, "ditutup"):
            camera.capture_array()

    def test_open_failure_releases_device(self):
        self.capture.isOpened.return_value = False
        with self.assertRaisesRegex(RuntimeError, "tidak terbuka"):
            USBCamera("0", (640, 480), 15)
        self.capture.release.assert_called_once()

    @patch("trash2trace.camera.time.sleep")
    def test_corrupt_green_startup_frames_are_rejected(self, sleep):
        self.capture.read.return_value = (True, Frame((0, 200, 0)))
        with self.assertRaisesRegex(RuntimeError, "gambar valid"):
            USBCamera("0", (640, 480), 15)
        self.capture.release.assert_called_once()
        self.assertEqual(self.capture.read.call_count, 15)

    def test_disconnect_does_not_reuse_last_good_frame(self):
        camera = USBCamera("0", (640, 480), 15)
        self.capture.grab.return_value = False
        with self.assertRaisesRegex(RuntimeError, "terputus"):
            camera.capture_array()

    def test_invalid_frame_during_capture_is_an_error(self):
        camera = USBCamera("0", (640, 480), 15)
        self.capture.read.return_value = (False, None)
        with self.assertRaisesRegex(RuntimeError, "kosong/rusak"):
            camera.capture_array()

    @patch("trash2trace.camera._load_env_file")
    def test_usb_default_does_not_import_picamera(self, load):
        with patch.dict(os.environ, {}, clear=True), patch.dict(sys.modules, {"picamera2": None}):
            camera = open_camera()
            self.assertIsInstance(camera, USBCamera)
            camera.close()

    @patch("trash2trace.camera._load_env_file")
    def test_bad_configuration_fails_before_open(self, load):
        for env in ({"CAMERA_BACKEND": "invalid"}, {"CAMERA_FPS": "0"}):
            with patch.dict(os.environ, env, clear=True), self.assertRaises(ValueError):
                open_camera()
        self.cv2.VideoCapture.assert_not_called()

    @patch("trash2trace.camera._load_env_file")
    def test_csi_opt_in_uses_rgb_array_format(self, load):
        camera = Mock()
        module = types.SimpleNamespace(Picamera2=Mock(return_value=camera))
        with patch.dict(os.environ, {"CAMERA_BACKEND": "csi"}, clear=True), patch.dict(sys.modules, {"picamera2": module}):
            wrapper = open_camera()
            camera.create_preview_configuration.assert_called_once_with(main={"format": "BGR888", "size": (640, 480)})
            wrapper.close()
            camera.stop.assert_called_once()
            camera.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
