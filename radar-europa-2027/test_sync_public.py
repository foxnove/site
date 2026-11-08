"""Exercise public synchronization against real Git checkouts, without network writes."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import sync_public


class PublicSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.backend = self.root / 'backend'
        self.checkout = self.root / 'public'
        (self.backend / 'docs').mkdir(parents=True)
        self.checkout.mkdir()
        (self.backend / 'docs/data.json').write_text(json.dumps({
            'environment': 'production', 'status': 'ok',
            'offers': [{'id': 'verified', 'price': 4200, 'secret': 'never-export'}],
            'history': [], 'email': 'never-export@example.invalid',
        }))
        self.git('init', '-q', '-b', 'master')
        self.git('config', 'user.name', 'Radar tests')
        self.git('config', 'user.email', 'tests@example.invalid')
        (self.checkout / 'unrelated.txt').write_text('existing site')
        self.git('add', '.')
        self.git('commit', '-qm', 'Existing site')
        self.git('remote', 'add', 'origin', 'https://github.com/foxnove/site')

    def git(self, *args):
        return subprocess.check_output(
            ['git', '-C', str(self.checkout), *args], text=True).strip()

    def synchronize(self):
        real_check_output = subprocess.check_output

        def offline_push(command, **kwargs):
            # Every local Git operation is real; only the external push is disabled.
            if command[3:] == ['push', 'origin', 'HEAD:master']:
                return ''
            return real_check_output(command, **kwargs)

        with patch.object(sync_public, 'ROOT', self.backend), \
                patch('sys.argv', ['sync_public.py', '--checkout', str(self.checkout)]), \
                patch.object(sync_public.subprocess, 'check_output', side_effect=offline_push):
            return sync_public.main()

    def test_checkout_remote_without_git_suffix_publishes_only_safe_data(self):
        self.assertEqual(self.synchronize(), 0)
        exported = json.loads((self.checkout / 'radar-europa-2027/data.json').read_text())
        self.assertEqual(exported['offers'], [{'id': 'verified', 'price': 4200}])
        self.assertNotIn('email', exported)
        self.assertEqual(self.git('diff-tree', '--no-commit-id', '--name-only', '-r', 'HEAD'),
                         'radar-europa-2027/data.json')
        self.assertEqual((self.checkout / 'unrelated.txt').read_text(), 'existing site')

    def test_existing_https_and_ssh_remotes_remain_supported(self):
        for remote in ('https://github.com/foxnove/site.git', 'git@github.com:foxnove/site.git'):
            with self.subTest(remote=remote):
                self.git('remote', 'set-url', 'origin', remote)
                self.assertEqual(self.synchronize(), 0)

    def test_wrong_repository_is_rejected_before_writing(self):
        for remote in ('https://github.com/foxnove/youtube',
                       'https://github.com/foxnove/site-foreign',
                       'https://github.com.example.org/foxnove/site'):
            with self.subTest(remote=remote):
                self.git('remote', 'set-url', 'origin', remote)
                with self.assertRaisesRegex(ValueError, 'Unexpected public repository'):
                    self.synchronize()
                self.assertFalse((self.checkout / 'radar-europa-2027/data.json').exists())

    def test_wrong_branch_is_rejected_before_writing(self):
        self.git('remote', 'set-url', 'origin', 'https://github.com/foxnove/site.git')
        self.git('switch', '-qc', 'another-branch')
        with self.assertRaisesRegex(ValueError, 'Unexpected public branch'):
            self.synchronize()
        self.assertFalse((self.checkout / 'radar-europa-2027/data.json').exists())


if __name__ == '__main__':
    unittest.main()
