import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import boss_recruiter


class FakeRoot:
    def winfo_screenwidth(self):
        return 1920

    def winfo_screenheight(self):
        return 1080


class FakeApp:
    root = FakeRoot()
    browser_proc = None
    running = False
    opening = False

    def __init__(self):
        self.events = []

    def log(self, message, level='info'):
        self.events.append((level, message))

    def st(self, message):
        self.events.append(('status', message))


class PublicBrowserTests(unittest.TestCase):
    def test_selftest_never_opens_browser_and_writes_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            receipt = Path(tmp) / 'receipt.txt'
            with patch.dict('os.environ', {'HRBOSS_SELFTEST_RECEIPT': str(receipt)}), \
                 patch.object(boss_recruiter.subprocess, 'Popen') as popen:
                self.assertEqual(boss_recruiter._self_test(), 0)
            popen.assert_not_called()
            self.assertEqual(receipt.read_text().strip(), 'HRBOSS_PUBLIC_LOGIN_SAFE_OK')

    def test_browser_launch_uses_isolated_profile_without_debug_endpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake = FakeApp()
            browser = Path(tmp) / 'chrome.exe'
            with patch.object(boss_recruiter, 'USER_DATA_DIR', Path(tmp) / 'user-data'), \
                 patch.object(boss_recruiter, 'CACHE_DIR', Path(tmp) / 'cache'), \
                 patch.object(boss_recruiter.subprocess, 'Popen') as popen:
                boss_recruiter.App._launch_browser_process(fake, str(browser))
            command = popen.call_args.args[0]
            self.assertEqual(command[0], str(browser))
            self.assertIn(boss_recruiter.REC_URL, command)
            self.assertTrue(any(part.startswith('--user-data-dir=') for part in command))
            self.assertFalse(any('remote-debugging' in part or 'remote-allow-origins' in part
                                 for part in command))
            self.assertEqual(popen.call_args.kwargs['stdout'], boss_recruiter.subprocess.DEVNULL)
            self.assertFalse(boss_recruiter.HAS_DP)

    def test_main_recruitment_entrypoints_remain_locked(self):
        fake = FakeApp()
        boss_recruiter.App._start(fake)
        boss_recruiter.App._engine(fake)
        self.assertTrue(any('关闭' in message for _, message in fake.events))
        self.assertFalse(fake.running)


if __name__ == '__main__':
    unittest.main()
