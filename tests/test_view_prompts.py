import copy
import json
import unittest
from h3_character_sheet.state_13 import DEFAULT_STATE
from h3_character_sheet.view_catalog_13 import VIEW_IDS
from h3_character_sheet.reference_v13_compiler import compile_reference_v13_state as compile_state
from h3_character_sheet.on_compiler_13 import compile_reference13_state
from h3_character_sheet.compiler import StateValidationError

class ViewPromptTests(unittest.TestCase):
    def test_all_views_roundtrip_and_guide_modes(self):
        state = copy.deepcopy(DEFAULT_STATE)
        state['views'] = list(VIEW_IDS)
        presence = {f'reference_image_{i}': True for i in range(1, 4)}
        for guide in (False, True):
            baseline = compile_state(json.dumps(state), use_layout_image=guide, reference_presence=presence)
            for view in VIEW_IDS:
                with self.subTest(guide=guide, view=view):
                    edited = dict(state, view_prompts={view: 'Custom view instruction.\nSecond sentence.'})
                    result = compile_state(json.dumps(edited), use_layout_image=guide, reference_presence=presence)
                    restored = compile_state(result['state_json'], use_layout_image=guide, reference_presence=presence)
                    self.assertEqual(restored['prompt'], result['prompt'])
                    self.assertEqual(result['layout'], baseline['layout'])
                    self.assertEqual(result['reference_plan'], baseline['reference_plan'])
                    self.assertEqual(len(result['view_prompts']), 13)
                    for before, after in zip(baseline['view_prompts'], result['view_prompts']):
                        if before.startswith('Panel ' + view + ':'):
                            self.assertIn('Custom view instruction.\nSecond sentence.', after)
                        else:
                            self.assertEqual(before, after)
    def test_blank_reset_and_context_defaults(self):
        for views in (['clothing_front','clothing_back'], list(VIEW_IDS)):
            state = dict(copy.deepcopy(DEFAULT_STATE), views=views)
            original = compile_state(json.dumps(state))
            edited = compile_state(json.dumps(dict(state, view_prompts={'clothing_front':''})))
            self.assertEqual(json.loads(edited['state_json'])['view_prompts']['clothing_front'], '')
            self.assertEqual(original['default_view_prompts'], edited['default_view_prompts'])
            reset = compile_state(json.dumps(dict(state, view_prompts={})))
            self.assertEqual(original['prompt'], reset['prompt'])
    def test_invalid_edits_and_previous_node(self):
        for overrides in ({'unknown':'text'}, {'hands':4}, {'feet':'x'*2001}, {'feet':chr(0xD800)}, []):
            with self.subTest(overrides=repr(overrides)):
                with self.assertRaises(StateValidationError):
                    compile_state(json.dumps(dict(copy.deepcopy(DEFAULT_STATE),view_prompts=overrides)))
        with self.assertRaises(StateValidationError):
            compile_reference13_state(json.dumps(dict(copy.deepcopy(DEFAULT_STATE),view_prompts={})))
