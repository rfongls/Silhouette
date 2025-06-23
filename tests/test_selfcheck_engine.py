import unittest
import sys
from io import StringIO
import selfcheck_engine as sce

class TestSelfcheck(unittest.TestCase):
    def test_missing_files(self):
        backup = sys.stdout
        sys.stdout = StringIO()
        missing = sce.check_files()
        output = sys.stdout.getvalue()
        sys.stdout = backup
        self.assertTrue('Missing required files' in output)
        self.assertIn('persona.dsl', missing)