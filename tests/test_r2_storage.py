import os
import unittest
from unittest import mock

import r2_storage


class R2ConfiguredTests(unittest.TestCase):
    REQUIRED = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")

    def _clear_env(self):
        return mock.patch.dict(os.environ, {}, clear=False)

    def test_fully_configured_when_all_vars_present_and_nonblank(self):
        with mock.patch.dict(os.environ, {name: "value" for name in self.REQUIRED}):
            self.assertTrue(r2_storage.r2_configured())

    def test_not_configured_when_a_var_is_entirely_unset(self):
        env = {name: "value" for name in self.REQUIRED}
        del env["R2_BUCKET_NAME"]
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(r2_storage.r2_configured())

    def test_not_configured_when_a_var_is_empty_string(self):
        # This is the exact failure mode from reading a secret via `vars.` in the
        # workflow: the key exists in the environment but resolves to "".
        env = {name: "value" for name in self.REQUIRED}
        env["R2_BUCKET_NAME"] = ""
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(r2_storage.r2_configured())

    def test_not_configured_when_a_var_is_whitespace_only(self):
        env = {name: "value" for name in self.REQUIRED}
        env["R2_BUCKET_NAME"] = "   "
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(r2_storage.r2_configured())

    def test_download_prefix_returns_zero_without_raising_when_unconfigured(self):
        with mock.patch.dict(os.environ, {"R2_BUCKET_NAME": ""}, clear=True):
            from pathlib import Path
            self.assertEqual(r2_storage.download_prefix("stock-cache/library", Path("/tmp/does-not-matter")), 0)

    def test_upload_prefix_returns_zero_without_raising_when_unconfigured(self):
        with mock.patch.dict(os.environ, {"R2_BUCKET_NAME": ""}, clear=True):
            from pathlib import Path
            self.assertEqual(r2_storage.upload_prefix(Path("/tmp/does-not-matter"), "stock-cache/library"), 0)


if __name__ == "__main__":
    unittest.main()
