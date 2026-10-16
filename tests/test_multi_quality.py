"""Appearance priorities, legacy migration, directional and pixel-guide contracts."""
import copy
import json
import re
import unittest

import numpy as np

from h3_character_sheet.compiler import DEFAULT_STATE, StateValidationError
from h3_character_sheet.guide_geometry import BODY_CROPS, MIRRORED_VIEWS, panel_bounds
from h3_character_sheet.layout_image import render_layout_image
from h3_character_sheet.multi_reference_compiler import (
    DEFAULT_MULTI_STATE, MULTI_VIEW_IDS, compile_multi_state, compute_multi_layout,
    parse_multi_state,
)


def state(views=None, **changes):
    value = copy.deepcopy(DEFAULT_MULTI_STATE)
    value['views'] = list(views or MULTI_VIEW_IDS)
    value.update(changes)
    return value


def compile_value(value, **kwargs):
    return compile_multi_state(json.dumps(value), **kwargs)


class MultiQualityTests(unittest.TestCase):
    def test_legacy_versions_and_missing_new_fields_preserve_defaults(self):
        for version in (1, 2, 3):
            value = state() if version == 3 else copy.deepcopy(DEFAULT_STATE)
            value['schema_version'] = version
            if version == 2:
                value['part_prompts'] = {'hands': '  silver ring\n'}
            value.pop('hand_state', None)
            value.pop('clothing_mode', None)
            result = parse_multi_state(json.dumps(value))
            self.assertEqual((result['hand_state'], result['clothing_mode']), ('reference', 'worn'))
            self.assertEqual(parse_multi_state(json.dumps(result)), result)
            if version == 2:
                self.assertEqual(result['part_prompts']['hands'], '  silver ring\n')

    def test_invalid_new_values_and_unknown_keys_are_rejected(self):
        for field in ('hand_state', 'clothing_mode'):
            for invalid in (None, True, 1, [], {}, 'unknown'):
                with self.subTest(field=field, value=invalid), self.assertRaises(StateValidationError):
                    compile_value(state(**{field: invalid}))
        with self.assertRaises(StateValidationError):
            compile_value(state(unknown=True))

    def test_retention_is_full_for_camera_layout_only_or_inactive_changes(self):
        cases = [state(), state(['face_front'], hand_state='gloved', part_prompts={'hands': 'gold ring'}),
                 state(['clothing_back'], reference_roles={'reference_image_1': 'clothing_front', 'reference_image_2': 'same_character'})]
        for value in cases:
            prompt = compile_value(value, reference_presence={'reference_image_1': True, 'reference_image_2': False})['prompt']
            self.assertIn('fully_preserved -', prompt)
            self.assertNotIn('partially_preserved -', prompt)

    def test_retention_changes_only_active_part_style_or_connected_role(self):
        for kwargs, value in [({}, state(part_prompts={'upper_clothing': 'red embroidery'})),
                              ({'style': 'anime'}, state()),
                              ({'reference_presence': {'reference_image_1': False, 'reference_image_2': True}},
                               state(reference_roles={'reference_image_1': 'same_character', 'reference_image_2': 'face'})),
                              ({}, state(hand_state='bare'))]:
            self.assertIn('partially_preserved - change only', compile_value(value, **kwargs)['prompt'])
        value = state(reference_roles={'reference_image_1': 'clothing', 'reference_image_2': 'hands'})
        self.assertIn('fully_preserved -', compile_value(value)['prompt'])

    def test_hand_coverage_priority_preserves_literal_part_text(self):
        text = '  red gloves, a silver ring; {red|blue}\n星 "MOON" '
        for hand, expected in [('reference', None), ('bare', 'Bare uncovered hands'), ('gloved', 'Both hands are covered by gloves')]:
            result = compile_value(state(hand_state=hand, part_prompts={'hands': text}))
            self.assertEqual(json.loads(result['state_json'])['part_prompts']['hands'], text)
            self.assertIn(text, result['prompt'])
            if expected:
                self.assertIn(expected, result['prompt'])
                self.assertIn('highest priority for coverage only', result['prompt'])
                self.assertIn('full-body, worn-clothing and hand-detail', result['prompt'])
                self.assertGreater(result['prompt'].index(expected), result['prompt'].index(text))
            else:
                self.assertNotIn('Hand-state override (', result['prompt'])

    def test_default_hands_are_neutral_and_hidden_override_has_no_effect(self):
        prompt = compile_value(state())['prompt']
        self.assertNotIn('Both hands are covered', prompt)
        self.assertIn('Follow the referenced hand appearance', prompt)
        self.assertNotIn('Hand-state override (', compile_value(state(['face_front'], hand_state='gloved'))['prompt'])

    def test_worn_clothing_includes_hand_priority_but_garments_do_not(self):
        for mode, visible in [('worn', True), ('garment', False)]:
            prompt = compile_value(state(['clothing_front', 'clothing_back'], clothing_mode=mode,
                                         hand_state='gloved', part_prompts={'hands': 'silver ring'}))['prompt']
            self.assertEqual('Hand-state override (' in prompt, visible)
            self.assertEqual('Part directive hands (' in prompt, visible)

    def test_clothing_only_preserves_outfit_and_explicit_changes_without_candidates(self):
        prompt = compile_value(state(clothing_mode='garment', part_prompts={'upper_clothing': 'blue embroidery'}), use_layout_image=True)['prompt']
        self.assertIn('blue embroidery', prompt)
        self.assertIn('No head, neck, arms, hands, legs, feet, torso, skin, person, mannequin or body', prompt)
        self.assertIn('clothing-only guide panels intentionally have blank interiors', prompt)
        self.assertIn('complete referenced clothing silhouette', prompt)
        self.assertNotRegex(prompt.lower(), r'pants|skirt|dress|trousers')

    def test_role_numbers_are_only_actual_images_and_six_sections(self):
        for guide in (False, True):
            result = compile_value(state(reference_roles={'reference_image_1': 'hands', 'reference_image_2': 'clothing_back'}),
                                   use_layout_image=guide, reference_presence={'reference_image_1': False, 'reference_image_2': True})
            self.assertEqual([r['picture_number'] for r in result['reference_plan']], list(range(1, 3 + guide)))
            self.assertEqual(set(re.findall(r'<Picture (\d+)>', result['prompt'])), {str(i) for i in range(1, 3 + guide)})
            self.assertEqual(set(re.findall(r'<Subject (\d+)>', result['prompt'])), {'1'})
            self.assertEqual(re.findall(r'^([a-z_]+):$', result['prompt'], re.M),
                             ['subject_definitions', 'summary', 'retention_analysis', 'detailed_description', 'overall_soundscape', 'non_diegetic_music'])

    def test_direction_uses_anatomical_side_and_image_edge(self):
        panels = {p['id']: p['content'] for p in compile_value(state())['layout']['panels']}
        for view, edge in [('face_left', 'LEFT'), ('face_right', 'RIGHT'), ('body_left', 'LEFT')]:
            self.assertIn(f'{edge} edge of the final image', panels[view])
            self.assertIn('strict', panels[view].lower())
        for view, edge in [('face_3q_left', 'LEFT'), ('face_3q_right', 'RIGHT')]:
            self.assertIn('45 degrees', panels[view])
            self.assertIn(f'{edge} edge', panels[view])
            self.assertIn('both eyes visible', panels[view])
        self.assertIn('No face or eyes visible', panels['face_back'])
        self.assertEqual(set(MIRRORED_VIEWS), {'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'body_left'})

    def test_all_8191_subsets_auto_manual_and_small_manual_bounds(self):
        for mask in range(1, 1 << len(MULTI_VIEW_IDS)):
            selected = [view for i, view in enumerate(MULTI_VIEW_IDS) if mask & (1 << i)]
            for mode, width, height in [('auto', 2208, 1280), ('manual', 1024, 768), ('manual', 32, 32)]:
                value = state(selected)
                value['size'].update(mode=mode, manual_width=width, manual_height=height)
                layout = compute_multi_layout(value)
                artwork = compile_value(value)['guide_artwork']
                bounds = {p['id']: panel_bounds(layout, p) for p in layout['panels']}
                for view, spec in artwork.items():
                    x, y, w, h = spec['rect']
                    left, top, right, bottom = bounds[view]
                    self.assertGreaterEqual(x, left, (mask, mode, view))
                    self.assertGreaterEqual(y, top, (mask, mode, view))
                    self.assertLessEqual(x + w, right, (mask, mode, view))
                    self.assertLessEqual(y + h, bottom, (mask, mode, view))
                    self.assertEqual(y + h - 1, round(layout['feet_y'] * layout['canvas'][1]))
                self.assertLessEqual(len({spec['rect'][3] for spec in artwork.values()}), 1)

    def test_blank_garment_guide_has_no_body_pixels_and_worn_does(self):
        for mode in ('worn', 'garment'):
            value = state(['clothing_front', 'clothing_back'], clothing_mode=mode)
            layout = compile_value(value)['layout']
            image = np.asarray(render_layout_image(layout, multi_reference=True, clothing_mode=mode))
            for panel in layout['panels']:
                left, top, right, bottom = panel_bounds(layout, panel)
                interior = image[top + 8:bottom - 8, left + 8:right - 8]
                self.assertEqual(bool(np.all(interior == 255)), mode == 'garment')

    def test_tight_body_pixels_aspect_and_common_sole_baseline(self):
        result = compile_value(state())
        image = np.asarray(render_layout_image(result['layout'], multi_reference=True))
        bottoms = []
        for view, spec in result['guide_artwork'].items():
            x, y, w, h = spec['rect']
            _, _, source_w, source_h = BODY_CROPS[view]
            self.assertLessEqual(abs(w - h * source_w / source_h), 0.5)
            mask = np.any(image[y:y+h, x:x+w] < 235, axis=-1)
            ys, xs = np.where(mask)
            self.assertGreaterEqual(len(xs), 1)
            self.assertLessEqual(ys.min(), 1)
            self.assertGreaterEqual(ys.max(), h - 2)
            bottoms.append(y + int(ys.max()))
        self.assertLessEqual(max(bottoms) - min(bottoms), 1)
        self.assertEqual((result['width'], result['height']), (4416, 1280))


if __name__ == '__main__':
    unittest.main()
