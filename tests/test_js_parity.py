"""Cross-language semantic validation parity; no browser or model required."""
import itertools
import json
from pathlib import Path
import shutil
import subprocess
import unittest

from h3_character_sheet.compiler import DEFAULT_STATE, PART_IDS, compile_state, VIEW_IDS

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

    def test_v2_all_views_and_literal_parts_share_semantics_and_prompt_bytes(self):
        values = []
        prompts = {part: f'  {part}: 青い星柄「MOON」 {{red|blue}} \\ "文字"\n次の行😀  '
                   for part in reversed(PART_IDS)}
        for bits in range(1, 1 << len(VIEWS)):
            views = [view for i, view in enumerate(VIEWS) if bits & (1 << i)]
            state = {**DEFAULT_STATE, 'schema_version': 2, 'views': list(reversed(views)), 'part_prompts': prompts}
            values.append(json.dumps(state, indent=2))
        for text in ('', ' \t\n\ufeff\u3000', '\x1c', '😀' * 500, '界' * 1000, 'e\u0301'):
            values.append(json.dumps({**DEFAULT_STATE, 'schema_version': 2, 'part_prompts': {'other': text}}))
        script = """
import {parseState, serializeState} from './web/state.js';
let input = ''; for await (const part of process.stdin) input += part;
console.log(JSON.stringify(JSON.parse(input).map(raw => serializeState(parseState(raw)))));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                                input=json.dumps(values), text=True, capture_output=True, check=True)
        actual = json.loads(result.stdout)
        self.assertEqual(len(actual), len(values))
        for raw, js_raw in zip(values, actual):
            with self.subTest(raw=raw[:100]):
                expected = compile_state(raw)
                # JS emits literal Unicode; Python's canonical saved JSON uses escapes.
                self.assertEqual(json.loads(js_raw), json.loads(expected['state_json']))
                self.assertEqual(compile_state(js_raw), expected)

    def test_v2_invalid_part_states_rejected_in_both_languages(self):
        base = {**DEFAULT_STATE, 'schema_version': 2, 'part_prompts': {}}
        values = [json.dumps({**base, 'part_prompts': value}) for value in
                  (None, [], '', {'face': None}, {'face': 3}, {'face': True},
                   {'unknown': 'text'}, {'face': 'a' * 1001}, {'face': '😀' * 501},
                   {'face': '😀' * 500 + 'a'}, {'face': '\ud800'}, {'face': '\udfff'})]
        values.extend((json.dumps({**DEFAULT_STATE, 'part_prompts': {}}),
                       json.dumps({**DEFAULT_STATE, 'schema_version': 2})))
        raw = json.dumps({**base, 'part_prompts': {'face': 'ok'}}, separators=(',', ':'))
        values.append(raw.replace('"face":"ok"', '"face":"ok","fa\\u0063e":"again"'))
        values.extend(raw.replace('"schema_version":2', '"schema_version":' + token)
                      for token in ('2.0', '2e0', 'true', '"2"'))
        script = """
import {parseState} from './web/state.js';
let input = ''; for await (const part of process.stdin) input += part;
console.log(JSON.stringify(JSON.parse(input).map(raw => {try {parseState(raw);return true;}catch{return false;}})));
"""
        result = subprocess.run(['node', '--input-type=module', '-e', script], cwd=ROOT,
                                input=json.dumps(values), capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), [False] * len(values))
        for raw in values:
            with self.subTest(raw=raw[:100]):
                with self.assertRaises(ValueError):
                    compile_state(raw)

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
