import unittest
import os
from offline_mode import is_offline

class TestOfflineMode(unittest.TestCase):
    def test_env_off(self):
        os.environ['SILHOUETTE_OFFLINE'] = '1'
        self.assertTrue(is_offline())

    def test_missing_files(self):
        os.environ.pop('SILHOUETTE_OFFLINE', None)
        # ensure persona.dsl not present
        persona = Path('persona.dsl')
        if persona.is_file():
            persona.unlink()
        self.assertTrue(is_offline())