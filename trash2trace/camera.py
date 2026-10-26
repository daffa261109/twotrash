"""Satu antarmuka RGB untuk webcam USB UVC dan kamera CSI lama.

Lebar pandangan ditentukan lensa. Tidak ada crop atau zoom digital di sini.
"""

from __future__ import annotations

import os
import time

from trash2trace.settings import ENV_PATH, _load_env_file


class USBCamera:
    def __init__(self, device: str, size: tuple[int, int], fps: int) -> None:
        import cv2

        self._cv2 = cv2
        self._capture = cv2.VideoCapture(
            int(device) if device.isdecimal() else device, cv2.CAP_V4L2
        )
        try:
            if not self._capture.isOpened():
                raise RuntimeError(f"Webcam {device} tidak terbuka. Cek USB OTG dan CAMERA_DEVICE.")
            # MJPEG mengurangi bandwidth USB; tidak semua UVC menerima semua mode.
            self._capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            self._capture.set(cv2.CAP_PROP_FRAME_WIDTH, size[0])
            self._capture.set(cv2.CAP_PROP_FRAME_HEIGHT, size[1])
            self._capture.set(cv2.CAP_PROP_FPS, fps)
            self._capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            for _ in range(15):
                ok, frame = self._capture.read()
                if ok and self._usable(frame):
                    print(f"[CAMERA] USB {device}: {frame.shape[1]}x{frame.shape[0]} (tanpa crop)")
                    break
                time.sleep(0.05)
            else:
                raise RuntimeError("Webcam tidak memberi gambar valid. Cek mode MJPEG, kabel, dan daya USB.")
        except Exception:
            self.close()
            raise

    @staticmethod
    def _usable(frame) -> bool:
        if frame is None or getattr(frame, "size", 0) == 0 or getattr(frame, "ndim", 0) != 3:
            return False
        if frame.shape[2] != 3:
            return False
        # Webcam yang ada pernah menghasilkan hijau polos saat negosiasi gagal.
        blue, green, red = (float(frame[:, :, i].mean()) for i in range(3))
        return not (green > 40 and blue < 15 and red < 15)

    def capture_array(self):
        if self._capture is None:
            raise RuntimeError("Webcam sudah ditutup")
        # Buang antrean frame lama saat aplikasi lama menunggu sensor/API.
        for _ in range(3):
            if not self._capture.grab():
                raise RuntimeError("Webcam terputus saat mengambil gambar")
        ok, frame = self._capture.read()
        if not ok or not self._usable(frame):
            raise RuntimeError("Frame webcam kosong/rusak. Cek kabel dan daya USB.")
        return self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2RGB)

    def close(self) -> None:
        capture, self._capture = self._capture, None
        if capture is not None:
            capture.release()


class CSICamera:
    def __init__(self, size: tuple[int, int]) -> None:
        from picamera2 import Picamera2

        self._camera = Picamera2()
        try:
            # Picamera2 BGR888 menghasilkan urutan array R,G,B untuk OpenCV.
            self._camera.configure(self._camera.create_preview_configuration(
                main={"format": "BGR888", "size": size}
            ))
            self._camera.start()
            try:
                self._camera.set_controls({"AwbEnable": True, "AwbMode": 4})
            except Exception as exc:
                print(f"[WARN] Warna kamera: {exc}")
        except Exception:
            self._camera.close()
            raise

    def capture_array(self):
        return self._camera.capture_array()

    def close(self) -> None:
        try:
            self._camera.stop()
        finally:
            self._camera.close()


def open_camera(size: tuple[int, int] = (640, 480)):
    _load_env_file(ENV_PATH)
    backend = os.environ.get("CAMERA_BACKEND", "usb").strip().lower()
    if backend == "csi":
        return CSICamera(size)
    if backend != "usb":
        raise ValueError("CAMERA_BACKEND harus usb atau csi")
    fps = int(os.environ.get("CAMERA_FPS", "15"))
    if not 1 <= fps <= 30:
        raise ValueError("CAMERA_FPS harus antara 1 dan 30")
    return USBCamera(os.environ.get("CAMERA_DEVICE", "/dev/video0"), size, fps)
