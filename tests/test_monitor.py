"""Layar monitor diuji tanpa Pi, webcam, atau Chromium."""

import json
import time
import unittest
import urllib.error
import urllib.request

from trash2trace.monitor import Monitor
from trash2trace.screen import presentation, screen_command


class MonitorTests(unittest.TestCase):
    def test_fullscreen_window_does_not_launch_chromium(self):
        command = screen_command(8080)
        self.assertEqual(command[-1], "8080")
        self.assertNotIn("chromium", " ".join(command).lower())
        shown = presentation({"tone": "organic", "title": "ORGANIK", "headline": "Kulit pisang", "detail": "1.4 detik"})
        self.assertEqual(shown["category"], "ORGANIK")
        self.assertEqual(shown["headline"], "Kulit pisang")
        self.assertEqual(shown["category_color"], "#3ddc6a")

    def test_screen_follows_wait_then_result_without_a_submit_button(self):
        monitor = Monitor(None, port=0)
        monitor.start()
        self.addCleanup(monitor.close)
        page = self._get(monitor, "/")
        self.assertIn("requestFullscreen", page)
        self.assertIn("/stream", page)
        self.assertIn('class="logo"', page)
        self.assertLess(page.index('class="logo"'), page.index('src="/stream"'))
        self.assertNotIn("Proses", page)
        with urllib.request.urlopen(f"http://127.0.0.1:{monitor.port}/frame.jpg", timeout=1) as response:
            self.assertTrue(response.read().startswith(b"\xff\xd8"))

        self.assertEqual(self._status(monitor)["headline"], "MENUNGGU")
        monitor.waiting(3)
        waiting = self._status(monitor)
        self.assertEqual(waiting["tone"], "wait")
        self.assertEqual(waiting["headline"], "3")
        self.assertEqual(waiting["title"], "TUNGGU")
        monitor.reading()
        self.assertEqual(self._status(monitor)["tone"], "reading")
        monitor.result("organic", "1.2 detik", "Kulit pisang")
        result = self._status(monitor)
        self.assertEqual(result["tone"], "organic")
        self.assertEqual(result["title"], "ORGANIK")
        self.assertEqual(result["headline"], "Kulit pisang")
        self.assertEqual(result["detail"], "1.2 detik")
        monitor.result("nonorganic", "2.0 detik")
        self.assertEqual(self._status(monitor)["title"], "NONORGANIK")
        monitor.result("other", "0.8 detik")
        other = self._status(monitor)
        self.assertEqual(other["tone"], "other")
        self.assertEqual(other["title"], "LAINNYA")

    def _status(self, monitor: Monitor) -> dict:
        return json.loads(self._get(monitor, "/status"))

    def _get(self, monitor: Monitor, path: str) -> str:
        url = f"http://127.0.0.1:{monitor.port}{path}"
        last = None
        for _ in range(30):
            try:
                with urllib.request.urlopen(url, timeout=1) as response:
                    return response.read().decode()
            except (urllib.error.URLError, TimeoutError) as exc:
                last = exc
                time.sleep(0.05)
        self.fail(f"{url} tidak menjawab: {last}")


if __name__ == "__main__":
    unittest.main()
