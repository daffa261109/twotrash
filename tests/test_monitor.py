"""Layar monitor diuji tanpa Pi, webcam, atau Chromium."""

import json
import time
import unittest
import urllib.error
import urllib.request

from trash2trace.monitor import Monitor, browser_command


class MonitorTests(unittest.TestCase):
    def test_browser_command_is_kiosk_fullscreen(self):
        command = browser_command("/usr/bin/chromium", "http://127.0.0.1:8080/")
        self.assertEqual(command[0], "/usr/bin/chromium")
        self.assertIn("--kiosk", command)
        self.assertIn("--start-fullscreen", command)
        self.assertEqual(command[-1], "http://127.0.0.1:8080/")

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
