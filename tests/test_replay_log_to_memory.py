import unittest
import tempfile
import json
from pathlib import Path
from replay_log_to_memory import parse_session_logs

class TestReplay(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_file = self.temp_dir / 'session_test.txt'
        self.log_file.write_text('[2025-06-23] USER: Hello world\n')
        self.output = self.temp_dir / 'memory.jsonl'

    def test_parse(self):
        parse_session_logs(self.temp_dir, self.output)
        lines = self.output.read_text().splitlines()
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])
        self.assertEqual(entry['role'], 'user')
        self.assertEqual(entry['content'], 'Hello world')