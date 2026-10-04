"""Cross-language semantic validation parity; no browser or model required."""
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from h3_character_sheet.compiler import compile_state, VIEW_IDS

ROOT = Path(__file__).resolve().parents[1]
VIEWS = VIEW_IDS


@unittest.skipUnless(shutil.which('node'), 'Node.js is optional for Python-only installations')
class SemanticParityTests(unittest.TestCase):
    def test_all_view_combinations_share_canonical_state(self):
        values = []
        for count in range(1, len(VIEWS) + 1):
            for views in itertools.combinations(VIEWS, count):
                state = {'size': {'manual_height': 1280, 'mode': 'auto',
                                  'manual_width': 2240, 'body_height': 1120},
                         'views': list(reversed(views)) + [views[0]], 'schema_version': 1}
                values.append(json.dumps(state, indent=2))
        script = """
import {parseState, serializeState} from './web/state.js';
let input = ''; for await (const part of process.stdin) input += part;
console.log(JSON.stringify(JSON.parse(input).map(raw => serializeState(parseState(raw)))));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script],
                                cwd=ROOT, input=json.dumps(values), text=True,
                                capture_output=True, check=True)
        actual = json.loads(result.stdout)
        expected = [compile_state(raw, max_resolution=16384)['state_json'] for raw in values]
        self.assertEqual(actual, expected)

    def test_invalid_numeric_tokens_are_rejected_on_both_sides(self):
        raw = json.dumps({'schema_version': 1, 'views': ['body_front'],
                          'size': {'mode': 'auto', 'body_height': 1120,
                                   'manual_width': 2240, 'manual_height': 1280}})
        values = [raw.replace('1120', token) for token in ['1120.0', '1.12e3', 'true', '"1120"', 'NaN', 'Infinity']]
        values += [raw.replace('"schema_version": 1', '"schema_version": ' + token)
                   for token in ['1.0', '1e0', 'true', '"1"']]
        script = """
import {parseState} from './web/state.js';
let input = ''; for await (const part of process.stdin) input += part;
console.log(JSON.stringify(JSON.parse(input).map(raw => {try {parseState(raw);return true;}catch{return false;}})));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                                input=json.dumps(values), capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [False] * len(values))
        for raw in values:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    compile_state(raw, max_resolution=16384)

    def test_defaults_match(self):
        script = "import {DEFAULT_JSON} from './web/state.js'; console.log(DEFAULT_JSON);"
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                                capture_output=True, text=True, check=True)
        raw = result.stdout.strip()
        compiled = compile_state(raw, max_resolution=16384)
        self.assertEqual(raw, compiled['state_json'])
        self.assertEqual((compiled['width'], compiled['height']), (2208, 1280))


if __name__ == '__main__':
    unittest.main()
