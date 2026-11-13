import copy
import json
import unittest
from unittest.mock import patch

from h3_character_sheet.compiler import StateValidationError
from h3_character_sheet.guide_13 import render_reference13_guide
from h3_character_sheet.minimax_image_compiler import VIEW_PROMPTS, compile_minimax_image_state
from h3_character_sheet.minimax_image_preview import compile_preview_request
from h3_character_sheet.on_compiler_13 import compile_reference13_state
from h3_character_sheet.reference_v13_compiler import compile_reference_v13_state
from h3_character_sheet.state_13 import DEFAULT_STATE, serialize_reference13_state
from h3_character_sheet.view_catalog_13 import PRESETS, VIEW_IDS


class MiniMaxImageTests(unittest.TestCase):
    def test_no_clothing_uses_eleven_views_and_preserves_saved_choices(self):
        state = {**DEFAULT_STATE, 'views': list(VIEW_IDS), 'clothing_type': 'none',
                 'hand_state': 'gloved', 'footwear_state': 'unshod',
                 'view_prompts': {'clothing_front': 'Keep this clothing edit', 'face_front': 'Custom portrait'},
                 'part_prompts': {'upper_clothing': 'Gold jacket', 'back_clothing': 'Silver jacket',
                                  'lower_body': 'Dark leg markings'}}
        expected = [view for view in VIEW_IDS if not view.startswith('clothing_')]
        for compile_state in (compile_minimax_image_state, compile_reference_v13_state):
            with self.subTest(compiler=compile_state.__name__):
                off, on = [compile_state(json.dumps(state), use_layout_image=enabled) for enabled in (False, True)]
                for result in (off, on):
                    saved = json.loads(result['state_json'])
                    self.assertEqual(saved['views'], list(VIEW_IDS))
                    self.assertEqual(saved['view_prompts'], state['view_prompts'])
                    self.assertEqual(saved['part_prompts'], state['part_prompts'])
                    self.assertEqual([p['id'] for p in result['layout']['panels']], expected)
                    self.assertIn('Custom portrait', result['prompt'])
                    self.assertIn('Dark leg markings', result['prompt'])
                    self.assertIn('socks or tights', result['prompt'])
                    for text in ('Keep this clothing edit', 'Gold jacket', 'Silver jacket', 'neutral standing',
                                 'shared garment construction', '13 selected views'):
                        self.assertNotIn(text, result['prompt'])
                    self.assertFalse(result['guide_geometry']['legacy'])
                    self.assertTrue(all(panel['blank'] for panel in result['guide_geometry']['panels']))
                self.assertEqual(off['guide_geometry'], on['guide_geometry'])
                self.assertFalse(off['guide_enabled'])
                self.assertTrue(on['guide_enabled'])
                with patch('h3_character_sheet.guide_13.Image.open', side_effect=AssertionError('artwork read')):
                    guide = render_reference13_guide(on['guide_geometry'], on['layout'])
                self.assertEqual(guide.size, (on['width'], on['height']))
                restored = compile_state(json.dumps({**saved, 'clothing_type': 'reference'}))
                self.assertEqual([p['id'] for p in restored['layout']['panels']], list(VIEW_IDS))
                self.assertIn('Keep this clothing edit', restored['prompt'])
                self.assertIn('Gold jacket', restored['prompt'])

    def test_no_clothing_validates_views_and_connected_roles(self):
        state = {**DEFAULT_STATE, 'clothing_type': 'none',
                 'reference_roles': {'reference_image_1': 'face', 'reference_image_2': 'clothing_back',
                                     'reference_image_3': 'same_character'}}
        raw = json.dumps(state)
        for compile_state in (compile_minimax_image_state, compile_reference_v13_state):
            self.assertEqual(len(compile_state(raw)['layout']['panels']), 5)
            with self.assertRaisesRegex(StateValidationError, 'Extra reference 2'):
                compile_state(raw, reference_presence={'reference_image_2': True})
            with self.assertRaisesRegex(StateValidationError, 'Select a non-clothing view'):
                compile_state(json.dumps({**state, 'views': ['clothing_front', 'clothing_back']}))
            details = compile_state(json.dumps({**state, 'views': ['hands', 'feet']}))
            self.assertNotIn('natural stance', details['prompt'])
            self.assertIn('forepaws', details['prompt'])
        with self.assertRaisesRegex(StateValidationError, 'P-H3 v1.3'):
            compile_reference13_state(raw)

    def test_minimax_eleven_view_guide_matches_the_reference_stance(self):
        state = {**DEFAULT_STATE, 'views': list(VIEW_IDS), 'clothing_type': 'none',
                 'size': {**DEFAULT_STATE['size'], 'mode': 'manual', 'manual_width': 4224, 'manual_height': 1280}}
        on = compile_minimax_image_state(json.dumps(state), use_layout_image=True)
        off = compile_minimax_image_state(json.dumps(state), use_layout_image=False)
        self.assertIn('same stance and limb arrangement', on['prompt'])
        self.assertIn('six portraits in the two columns on the left', on['prompt'])
        self.assertIn('same stance and limb arrangement', off['prompt'])
        self.assertIn('same weight-bearing limbs', off['prompt'])
        self.assertNotIn('same weight-bearing limbs', on['prompt'])
        self.assertNotIn('<Picture 2>', off['prompt'])

    def test_minimax_eleven_view_stance_applies_only_to_unedited_body_views(self):
        state = {**DEFAULT_STATE, 'views': list(VIEW_IDS), 'clothing_type': 'none'}
        seated = 'Full-body side view seated on the ground.'
        for guide in (False, True):
            for overrides, expected_scope in (
                ({'face_front': 'Custom portrait'}, 'across all three full-body views.'),
                ({'body_left': seated}, 'for the full-body front view and full-body back view.'),
                ({'body_front': VIEW_PROMPTS['body_front'], 'body_left': ''}, 'for the full-body back view.'),
                ({'body_front': VIEW_PROMPTS['body_front'], 'body_left': seated, 'body_back': ''}, None),
            ):
                with self.subTest(guide=guide, overrides=overrides):
                    result = compile_minimax_image_state(json.dumps({**state, 'view_prompts': overrides}),
                                                         use_layout_image=guide)
                    prompt = result['prompt']
                    stance = 'Use the same stance and limb arrangement as <Picture 1>'
                    lines = [line for line in prompt.splitlines() if line.startswith(stance)]
                    self.assertEqual([line.partition('. ')[0] + '.' for line in lines],
                                     [f'{stance} {expected_scope}'] if expected_scope else [])
                    if 'body_left' in overrides:
                        self.assertNotIn('same weight-bearing limbs', prompt)
                    for view, text in overrides.items():
                        self.assertIn(f'{view}: {text}', result['view_prompts'])
                    self.assertEqual(json.loads(result['state_json'])['view_prompts'], overrides)

    def test_minimax_guided_eleven_view_side_edit_assigns_each_portrait_slot(self):
        state = {**DEFAULT_STATE, 'views': list(VIEW_IDS), 'clothing_type': 'none',
                 'view_prompts': {'body_left': 'Full-body side view seated on the ground.',
                                  'face_front': 'Custom front portrait.'}}
        for guide in (False, True):
            for side_edited in (False, True):
                with self.subTest(guide=guide, side_edited=side_edited):
                    overrides = dict(state['view_prompts'])
                    if not side_edited:
                        overrides.pop('body_left')
                    result = compile_minimax_image_state(json.dumps({**state, 'view_prompts': overrides}),
                                                         use_layout_image=guide)
                    prompt = result['prompt']
                    rows = [line for line in prompt.splitlines() if ' portrait row.' in line]
                    borderless = 'Separate the finished views with plain white space. Omit all guide outlines and divider lines.'
                    if not (guide and side_edited):
                        self.assertEqual(rows, [])
                        self.assertNotIn(borderless, prompt)
                        continue
                    self.assertIn(borderless, prompt)
                    defaults = result['default_view_prompts']
                    self.assertEqual(rows, [
                        f"Top portrait row. Left slot: Custom front portrait. Right slot: {defaults['face_left']}",
                        f"Middle portrait row. Left slot: {defaults['face_right']} Right slot: {defaults['face_3q_left']}",
                        f"Bottom portrait row. Left slot: {defaults['face_3q_right']} Right slot: {defaults['face_back']}",
                    ])
                    self.assertEqual(len(result['view_prompts']), 11)

    def test_reference_v13_eleven_view_close_up_column_without_guide(self):
        state = {**DEFAULT_STATE, 'views': list(VIEW_IDS), 'clothing_type': 'none'}
        off = compile_reference_v13_state(json.dumps(state), use_layout_image=False)
        on = compile_reference_v13_state(json.dumps(state), use_layout_image=True)
        cue = 'Reserve the far-right column for two separate close-ups'
        self.assertIn(cue, off['prompt'])
        self.assertNotIn(cue, on['prompt'])
        details = compile_reference_v13_state(json.dumps({**state, 'views': ['hands', 'feet']}), use_layout_image=False)
        self.assertNotIn(cue, details['prompt'])

    def test_auto_profiles_preserve_layout_and_order_at_all_presets(self):
        presets = {**PRESETS, 'seven': (*DEFAULT_STATE['views'], 'hands', 'feet')}
        for name, views in presets.items():
            state = {**DEFAULT_STATE, 'views': list(views)}
            for guide in (False, True):
                with self.subTest(preset=name, guide=guide):
                    current = compile_minimax_image_state(json.dumps(state), use_layout_image=guide)
                    high, eight, sixteen = [compile_minimax_image_state(json.dumps({**state, 'resolution_profile': profile}),
                                             use_layout_image=guide) for profile in ('high', 'max_8mp', 'max_16mp')]
                    self.assertLess(current['pixel_count'], high['pixel_count'])
                    self.assertLess(high['pixel_count'], eight['pixel_count'])
                    self.assertLessEqual(eight['pixel_count'], 8_000_000)
                    self.assertGreater(sixteen['pixel_count'], 15_200_000)
                    self.assertLessEqual(sixteen['pixel_count'], 16_000_000)
                    base = current['pixel_count']
                    target = 2 * base if 2 * base < 8_000_000 else (base + 8_000_000) / 2
                    self.assertGreater(high['pixel_count'], target * 0.95)
                    for result in (high, eight, sixteen):
                        canvas = [result['width'], result['height']]
                        self.assertEqual([n % 32 for n in canvas], [0, 0])
                        self.assertEqual(result['semantic_layout']['panels'], current['semantic_layout']['panels'])
                        self.assertEqual(result['prompt'], current['prompt'])
                        self.assertEqual(result['layout']['canvas'], canvas)
                        self.assertEqual(result['guide_geometry']['canvas'], canvas)
                        for panel in result['guide_geometry']['panels']:
                            l, t, r, b = panel['bounds']
                            self.assertTrue(0 <= l < r <= canvas[0] and 0 <= t < b <= canvas[1])

    def test_resolution_profile_roundtrip_and_manual_override(self):
        state = {**DEFAULT_STATE, 'resolution_profile': 'max_16mp'}
        state['size'] = {**state['size'], 'mode': 'manual', 'manual_width': 768, 'manual_height': 1536}
        raw = json.dumps(state)
        preview = compile_preview_request(json.dumps({'state_json': raw}).encode(), max_resolution=16384)
        self.assertEqual((preview['width'], preview['height']), (768, 1536))
        restored = compile_minimax_image_state(preview['state_json'])
        self.assertEqual(restored, preview)
        with self.assertRaises(StateValidationError):
            compile_reference_v13_state(raw)
        with self.assertRaises(StateValidationError):
            compile_minimax_image_state(json.dumps({**state, 'resolution_profile': 'unknown'}))

    def test_five_view_prompt_has_no_coordinate_or_video_instructions(self):
        result = compile_minimax_image_state(json.dumps(DEFAULT_STATE))
        text = result['prompt']
        self.assertEqual(len(result['view_prompts']), 5)
        for view in result['state']['views']:
            self.assertEqual(text.count(VIEW_PROMPTS[view]), 1)
        for forbidden in ['rect [', 'normalized', '[Shot', 'first frame', 'soundscape', '<Subject']:
            self.assertNotIn(forbidden, text)
        self.assertNotRegex(text, r'\d+\.\d+')
        self.assertIn('rect [', compile_reference_v13_state(json.dumps(DEFAULT_STATE))['prompt'])

    def test_overrides_survive_roundtrip_and_layout_switch(self):
        state = copy.deepcopy(DEFAULT_STATE)
        state['view_prompts'] = {'face_front': 'Custom front portrait.', 'face_left': ''}
        state['part_prompts'] = {'upper_clothing': 'Purple jacket.'}
        raw = serialize_reference13_state(state)
        for guide in [False, True]:
            result = compile_minimax_image_state(raw, use_layout_image=guide)
            reloaded = compile_minimax_image_state(serialize_reference13_state(result['state']), use_layout_image=guide)
            self.assertEqual(result['prompt'], reloaded['prompt'])
            self.assertIn('Custom front portrait.', result['prompt'])
            self.assertNotIn(VIEW_PROMPTS['face_left'], result['prompt'])
            self.assertIn('Purple jacket.', result['prompt'])
            legacy = compile_reference_v13_state(raw, use_layout_image=guide)
            self.assertEqual(result['layout'], legacy['layout'])
            self.assertEqual(result['state']['view_prompts'], state['view_prompts'])

    def test_single_view_requests_one_illustration_and_respects_overrides(self):
        for view in VIEW_IDS:
            state = copy.deepcopy(DEFAULT_STATE)
            state['views'] = [view]
            with self.subTest(view=view):
                result = compile_minimax_image_state(json.dumps(state))
                self.assertIn('Create a single centered', result['prompt'])
                self.assertEqual(result['prompt'].count(VIEW_PROMPTS[view]), 1)
                self.assertNotIn('reference sheet', result['prompt'])
                self.assertNotIn('Arrange columns', result['prompt'])
                self.assertEqual(len(result['view_prompts']), 1)
                state['view_prompts'] = {view: 'Custom single view.'}
                edited = compile_minimax_image_state(json.dumps(state), use_layout_image=True)
                self.assertIn('Use <Picture 2> for framing.', edited['prompt'])
                self.assertIn('Custom single view.', edited['prompt'])
                self.assertNotIn(VIEW_PROMPTS[view], edited['prompt'])

    def test_all_views_and_manual_layout_have_one_record_each(self):
        state = copy.deepcopy(DEFAULT_STATE)
        state['views'] = list(VIEW_IDS)
        state['size'].update(mode='manual', manual_width=512, manual_height=2048)
        result = compile_minimax_image_state(json.dumps(state))
        self.assertEqual((result['width'], result['height']), (512, 2048))
        self.assertEqual({s.split(':', 1)[0] for s in result['view_prompts']}, set(VIEW_IDS))
        self.assertEqual(len(result['view_prompts']), 13)
        self.assertNotRegex(result['prompt'], r'\d+\.\d+')

    def test_all_views_without_guide_describe_the_four_blocks(self):
        state = {**DEFAULT_STATE, 'views': list(VIEW_IDS),
                 'view_prompts': {'body_back': 'Custom full-body back.'}}
        raw = json.dumps(state)
        without_guide = compile_minimax_image_state(raw)['prompt']
        with_guide = compile_minimax_image_state(raw, use_layout_image=True)['prompt']
        self.assertIn('two-column, three-row grid', without_guide)
        self.assertIn('hands above footwear', without_guide)
        self.assertNotIn('two-column, three-row grid', with_guide)
        body_line = next(line for line in without_guide.splitlines() if 'Custom full-body back.' in line)
        self.assertEqual(body_line, f"From left to right: {VIEW_PROMPTS['body_front']} {VIEW_PROMPTS['body_left']} Custom full-body back.")
        self.assertEqual(without_guide.count(VIEW_PROMPTS['clothing_back']), 1)
        self.assertNotIn(VIEW_PROMPTS['body_back'], without_guide)

    def test_picture_numbers_follow_present_images(self):
        for guide in [False, True]:
            result = compile_minimax_image_state(json.dumps(DEFAULT_STATE), use_layout_image=guide,
                reference_presence={'reference_image_1': False, 'reference_image_2': True, 'reference_image_3': False})
            refs = result['reference_plan']
            extra = next(r for r in refs if r['source'] == 'reference_image_2')
            self.assertEqual(extra['tag'], '<Picture 3>' if guide else '<Picture 2>')
            self.assertEqual(extra['core_input'], 'images.image_3')
            self.assertIn(extra['tag'], result['prompt'])

    def test_bare_hands_and_unshod_feet_replace_only_defaults(self):
        cases = (
            ('hands', 'hand_state', 'bare', 'gloved', 'Close-up of both hands.', 'Bare hands.'),
            ('feet', 'footwear_state', 'unshod', 'shod', 'Close-up of both feet.',
             'Shoes removed; retain reference socks or tights.'),
        )
        for view, field, setting, covered, default, directive in cases:
            for guide in (False, True):
                for views in ([view], ['body_front', view]):
                    with self.subTest(view=view, guide=guide, views=views):
                        state = {**DEFAULT_STATE, 'views': views}
                        for value in ('reference', covered):
                            result = compile_minimax_image_state(
                                json.dumps({**state, field: value}), use_layout_image=guide)
                            self.assertEqual(result['default_view_prompts'], VIEW_PROMPTS)
                            self.assertIn(VIEW_PROMPTS[view], result['prompt'])

                        state[field] = setting
                        result = compile_minimax_image_state(json.dumps(state), use_layout_image=guide)
                        self.assertEqual(result['default_view_prompts'], {**VIEW_PROMPTS, view: default})
                        self.assertIn(f'{default} {directive}', result['prompt'])
                        self.assertNotIn(VIEW_PROMPTS[view], result['prompt'])
                        self.assertNotIn('Follow selected settings first', result['prompt'])

                        for override in ('', VIEW_PROMPTS[view]):
                            state['view_prompts'] = {view: override}
                            edited = compile_minimax_image_state(json.dumps(state), use_layout_image=guide)
                            self.assertEqual(json.loads(edited['state_json'])['view_prompts'], {view: override})
                            self.assertIn(' '.join(filter(None, (override, directive))), edited['prompt'])
                            self.assertEqual(VIEW_PROMPTS[view] in edited['prompt'], bool(override))

    def test_guide_off_hand_and_foot_pair_uses_white_space_between_close_ups(self):
        state = {**DEFAULT_STATE, 'views': ['hands', 'feet'],
                 'hand_state': 'bare', 'footwear_state': 'unshod'}
        raw = json.dumps(state)
        result = compile_minimax_image_state(raw, use_layout_image=False)
        layout_instruction = 'exactly two borderless close-up views'
        self.assertIn(layout_instruction, result['prompt'])
        self.assertIn('blank white space between the views', result['prompt'])
        self.assertIn('Upper half: Close-up of both hands. Bare hands.', result['prompt'])
        self.assertIn('Lower half: Close-up of both feet. Shoes removed; retain reference socks or tights.',
                      result['prompt'])
        self.assertNotIn('character reference sheet', result['prompt'])

        guided = compile_minimax_image_state(raw, use_layout_image=True)
        self.assertNotIn(layout_instruction, guided['prompt'])
        self.assertEqual(result['view_prompts'], guided['view_prompts'])
        mixed = compile_minimax_image_state(json.dumps({**state, 'views': ['body_front', 'hands', 'feet']}))
        self.assertNotIn(layout_instruction, mixed['prompt'])

    def test_reference_priority_is_stated_once_for_additional_references(self):
        state = {**DEFAULT_STATE, 'hand_state': 'bare',
                 'part_prompts': {'hands': 'Retain silver rings.'},
                 'reference_roles': {'reference_image_1': 'hands',
                                     'reference_image_2': 'same_character',
                                     'reference_image_3': 'hands'}}
        presence = {'reference_image_1': True, 'reference_image_3': True}
        for guide in (False, True):
            for views in (['hands'], ['body_front', 'hands']):
                with self.subTest(guide=guide, views=views):
                    result = compile_minimax_image_state(
                        json.dumps({**state, 'views': views}), use_layout_image=guide,
                        reference_presence=presence)
                    prompt = result['prompt']
                    self.assertEqual(prompt.count('Follow selected settings first, then compatible part instructions, '
                                                  'then dedicated references.'), 1)
                    self.assertEqual(prompt.count('If dedicated references for the same role conflict, '
                                                  'prefer the later input.'), 1)
                    first = 3 if guide else 2
                    self.assertIn(f'Use <Picture {first}> for hands and gloves.', prompt)
                    self.assertIn(f'Use <Picture {first + 1}> for hands and gloves.', prompt)
                    self.assertIn('Retain silver rings.', prompt)

    def test_node_preserves_image_passthrough_and_output_contract(self):
        import torch
        from unittest.mock import patch
        from h3_character_sheet.minimax_image_node import MiniMaxH3ImageCharacterSheetDesigner as Node
        from h3_character_sheet.reference_v13_node import H3CharacterSheetDesignerReferenceV13 as Old
        self.assertEqual(Node.RETURN_TYPES, Old.RETURN_TYPES)
        self.assertEqual(Node.RETURN_NAMES, Old.RETURN_NAMES)
        images = [torch.full((1, 16, 16, 3), i / 4) for i in range(4)]
        with patch('h3_character_sheet.minimax_image_node.runtime_max_resolution', return_value=16384):
            for guide in [False, True]:
                outputs = Node().compile(json.dumps(DEFAULT_STATE), images[0], reference_image_1=images[1],
                    reference_image_2=images[2], reference_image_3=images[3], use_layout_image=guide)
                for actual, expected in zip(outputs[4:], images):
                    self.assertIs(actual, expected)
                if guide:
                    self.assertEqual(tuple(outputs[3].shape), (1, outputs[2], outputs[1], 3))
                else:
                    self.assertIsNone(outputs[3])
