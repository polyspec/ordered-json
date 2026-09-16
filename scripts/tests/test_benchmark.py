"""Check that the workload manifest describes the fixtures it names."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'benchmarks'))
from run import structure, validate_workload


class WorkloadChecks(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix='ordered-json-workload-')
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.source = b'{"a":[1,true,null,"b"],"c":{"d":2}}'
        (self.root / 'sample.json').write_bytes(self.source)
        self.entry = {'file': 'sample.json', 'input_bytes': len(self.source),
                      'sha256': hashlib.sha256(self.source).hexdigest(),
                      **structure(json.loads(self.source))}

    def workload(self):
        return {'sample.json': self.entry}

    def test_declared_structure_describes_the_fixture(self):
        validate_workload(self.workload(), self.root)

    def test_wrong_node_count_is_rejected(self):
        self.entry['nodes'] += 1
        with self.assertRaises(SystemExit):
            validate_workload(self.workload(), self.root)

    def test_wrong_depth_is_rejected(self):
        self.entry['max_depth'] += 1
        with self.assertRaises(SystemExit):
            validate_workload(self.workload(), self.root)

    def test_an_object_key_counts_as_a_string_node(self):
        # The committed manifest counts keys, so the counter must too.
        self.assertEqual(structure(json.loads('{"a":1}'))['strings'], 1)
        self.assertEqual(structure(json.loads('{"a":1}'))['nodes'], 3)


if __name__ == '__main__':
    unittest.main()
