import copy
import itertools
import json
import sys
import types
import unittest
import torch
from unittest import mock

from h3_character_sheet import compiler as legacy
from h3_character_sheet.guide_13 import derive_guide_geometry, render_reference13_guide
from h3_character_sheet.layout_13 import compute_semantic_layout
from h3_character_sheet.layout_image import render_layout_image
from h3_character_sheet.on_compiler_13 import compile_reference13_state
from h3_character_sheet.reference13_node import H3CharacterSheetDesignerReference13
from h3_character_sheet.reference13_preview import compile_preview_request
from h3_character_sheet.reference_compiler import compile_reference_state
from h3_character_sheet.state_13 import DEFAULT_STATE, DEFAULT_STATE_JSON, parse_reference13_state
from h3_character_sheet.view_catalog_13 import VIEW_IDS


class Reference13Tests(unittest.TestCase):
    def state(self, **fields):
        state = copy.deepcopy(DEFAULT_STATE)
        state.update(fields)
        return state

    def test_all_legacy_subsets_preserve_geometry_with_new_prompt_contract(self):
        count = 0
        for mask in range(1, 128):
            views = [v for i, v in enumerate(legacy.VIEW_IDS) if mask & (1 << i)]
            for mode, h, width, height in [('auto', 672, 2208, 1280), ('auto', 1120, 2208, 1280), ('manual', 1120, 896, 512), ('manual', 672, 1536, 768)]:
                for version in (1, 2):
                    old = {'schema_version': version, 'views': views,
                           'size': {'mode': mode, 'body_height': h, 'manual_width': width, 'manual_height': height}}
                    if version == 2:
                        old['part_prompts'] = {}
                    raw = json.dumps(old)
                    before = compile_reference_state(raw)
                    after = compile_reference13_state(raw)
                    self.assertEqual(after['semantic_layout'], before['layout'])
                    v3 = self.state(views=views, size=old['size'])
                    self.assertEqual(compile_reference13_state(json.dumps(v3))['prompt'], after['prompt'])
                    for view in views:
                        self.assertIn(f'Panel {view}:', after['prompt'])
                    count += 1
        self.assertEqual(count, 1016)

    def test_all_8191_subsets_auto_and_manual(self):
        for mask in range(1, 8192):
            views = [v for i, v in enumerate(VIEW_IDS) if mask & (1 << i)]
            for mode, width, height in [('auto', 2208, 1280), ('manual', 896, 512)]:
                state = self.state(views=views)
                state['size'].update(mode=mode, manual_width=width, manual_height=height)
                layout = compute_semantic_layout(state)
                self.assertEqual([p['id'] for p in layout['panels']], views)
                if mode == 'manual':
                    self.assertEqual(layout['canvas'], [width, height])
                self.assertTrue(all(d % 32 == 0 for d in layout['canvas']))
                for p in layout['panels']:
                    x, y, w, h = p['rect']
                    self.assertGreater(w, 0)
                    self.assertGreater(h, 0)
                    self.assertGreaterEqual(x, 0)
                    self.assertGreaterEqual(y, 0)
                    self.assertLessEqual(x+w, 1.000002)
                    self.assertLessEqual(y+h, 1.000002)
                for a, b in itertools.combinations(layout['panels'], 2):
                    x, y, w, h = a['rect']; u, v, bw, bh = b['rect']
                    self.assertTrue(x+w <= u+0.000002 or u+bw <= x+0.000002 or y+h <= v+0.000002 or v+bh <= y+0.000002)

    def test_dimensions_and_core_limit(self):
        cases = [('basic', 1120, (2208, 1280)), ('five', 1120, (2816, 1280)), ('detail', 1120, (4416, 1280)), ('five', 672, (1696, 768))]
        from h3_character_sheet.view_catalog_13 import PRESETS
        for preset, h, dimensions in cases:
            state = self.state(views=list(PRESETS[preset])); state['size']['body_height'] = h
            result = compile_reference13_state(json.dumps(state))
            self.assertEqual((result['width'], result['height']), dimensions)
        with self.assertRaises(legacy.StateValidationError):
            compile_reference13_state(DEFAULT_STATE_JSON, max_resolution=1024)

    def test_off_never_opens_renders_or_tensorizes(self):
        with mock.patch.dict(sys.modules, {'nodes': types.SimpleNamespace(MAX_RESOLUTION=16384)}), \
             mock.patch('PIL.Image.open', side_effect=AssertionError('image read')), \
             mock.patch('h3_character_sheet.on_compiler_13.derive_guide_geometry', side_effect=AssertionError('guide')), \
             mock.patch('h3_character_sheet.reference13_node.render_reference13_guide', side_effect=AssertionError('render')), \
             mock.patch('torch.from_numpy', side_effect=AssertionError('tensor')):
            node = H3CharacterSheetDesignerReference13()
            self.assertIs(node.VALIDATE_INPUTS(DEFAULT_STATE_JSON), True)
            character = torch.zeros(1, 2, 3, 3)
            self.assertIsNone(node.compile(DEFAULT_STATE_JSON, character)[3])
            all_views = json.dumps(self.state(views=list(VIEW_IDS)))
            self.assertIsNone(node.compile(all_views, character)[3])

    def test_off_independent_of_guide_changes(self):
        raw = json.dumps(self.state(views=list(VIEW_IDS)))
        before = compile_reference13_state(raw)
        with mock.patch('h3_character_sheet.guide_13.ATLAS_CROPS', {}), \
             mock.patch('h3_character_sheet.guide_13.EXTRA_SIZES', {}):
            self.assertEqual(compile_reference13_state(raw), before)

    def test_legacy_on_pixels_preserved_with_new_prompt_contract(self):
        for views in [list(legacy.PRESETS['five']), list(legacy.VIEW_IDS), ['body_front']]:
            state = self.state(views=views)
            raw = json.dumps(state)
            actual = compile_reference13_state(raw, use_layout_image=True, style='anime')
            old = {'schema_version': 2, 'views': views, 'size': state['size'], 'part_prompts': {}}
            expected = compile_reference_state(json.dumps(old), use_layout_image=True, style='anime')
            self.assertIn('Apply anime-style linework and cel shading.', actual['prompt'])
            self.assertEqual(render_reference13_guide(actual['guide_geometry'], actual['layout']).tobytes(), render_layout_image(expected['layout']).tobytes())

    def test_parts_style_and_irrelevant_settings_remain_scoped(self):
        parts = {part: '日本語 {literal|text} ' + part for part in legacy.PART_IDS}
        state = self.state(part_prompts=parts)
        for style in ('none', 'anime', 'photo'):
            prompt = compile_reference13_state(json.dumps(state), style=style)['prompt']
            for text in parts.values():
                self.assertIn(text, prompt)
        state = self.state(views=['face_front'], hand_state='bare', footwear_state='unshod', clothing_type='pants', clothing_mode='garment')
        plain = self.state(views=['face_front'])
        self.assertEqual(compile_reference13_state(json.dumps(state))['prompt'], compile_reference13_state(json.dumps(plain))['prompt'])

    def test_choices_apply_to_bodies_without_detail_cards(self):
        state = self.state(views=list(legacy.BODY_IDS), hand_state='bare', footwear_state='unshod', clothing_type='skirt_robe', part_prompts={'upper_clothing': '青い絹', 'footwear': '白いタイツ'})
        prompt = compile_reference13_state(json.dumps(state))['prompt']
        self.assertIn('No shoes or boots', prompt)
        self.assertIn('no gloves', prompt)
        self.assertIn('continuous skirt or robe hem', prompt)
        self.assertIn('青い絹', prompt)
        self.assertIn('白いタイツ', prompt)
        self.assertNotIn('Preserve reference gloves', prompt)
        self.assertNotIn('<Picture 2>', prompt)

    def test_garment_guide_has_empty_clothing_frames(self):
        state = self.state(views=['clothing_front', 'clothing_back'], clothing_mode='garment', hand_state='gloved', footwear_state='shod')
        result = compile_reference13_state(json.dumps(state), use_layout_image=True)
        self.assertTrue(all(p['blank'] for p in result['guide_geometry']['panels']))
        image = render_reference13_guide(result['guide_geometry'], result['layout'])
        for p in result['guide_geometry']['panels']:
            left, top, right, bottom = p['bounds']
            self.assertEqual(image.getpixel(((left+right)//2, (top+bottom)//2)), (255, 255, 255))
        self.assertNotIn('Choice hand_state', result['prompt'])
        self.assertNotIn('Choice footwear_state', result['prompt'])

    def test_strict_state_and_preview(self):
        invalid = [DEFAULT_STATE_JSON.replace('"schema_version":3', '"schema_version":true'), '{"schema_version":3,"schema_version":3}', DEFAULT_STATE_JSON.replace('1120', '1120.5'), DEFAULT_STATE_JSON.replace('"reference"', '"unknown"', 1)]
        for raw in invalid:
            with self.assertRaises(legacy.StateValidationError): parse_reference13_state(raw)
        state = self.state(part_prompts={'face': '😀'*501})
        with self.assertRaises(legacy.StateValidationError): parse_reference13_state(json.dumps(state))
        with self.assertRaises(legacy.StateValidationError): parse_reference13_state(json.dumps({**self.state(), 'reference_roles': {}}))
        result = compile_preview_request(json.dumps({'state_json': DEFAULT_STATE_JSON, 'use_layout_image': False, 'style': 'none'}).encode(), max_resolution=16384)
        self.assertIsNone(result['guide_geometry'])
        self.assertEqual(result['width'], 2816)


    def test_image_ports_match_old_node_and_preserve_existing_outputs(self):
        from h3_character_sheet.multi_reference_node import H3CharacterSheetDesignerMultiReference as Old
        node = H3CharacterSheetDesignerReference13
        self.assertEqual(node.RETURN_NAMES[:7], Old.RETURN_NAMES)
        self.assertEqual(node.RETURN_TYPES[:7], Old.RETURN_TYPES)
        self.assertEqual(node.RETURN_NAMES[7:], ('reference_image_3',))
        self.assertEqual(node.RETURN_TYPES[7:], ('IMAGE',))
        self.assertEqual(node.INPUT_TYPES()['required']['character_image'], ('IMAGE',))
        for name in ('reference_image_1', 'reference_image_2', 'reference_image_3'):
            self.assertEqual(node.INPUT_TYPES()['optional'][name], ('IMAGE',))

    @mock.patch('h3_character_sheet.reference13_node.runtime_max_resolution', return_value=16384)
    def test_images_pass_through_unchanged_and_numbering_skips_gaps(self, _maximum):
        character = torch.zeros(1, 3, 5, 3)
        extra1, extra2 = torch.ones(1, 7, 2, 3), torch.zeros(1, 4, 8, 3)
        extra3 = torch.full((1, 5, 3, 3), 0.5)
        node = H3CharacterSheetDesignerReference13()
        # Exercise both compilers, OFF/ON and every optional connection pattern.
        for raw in (DEFAULT_STATE_JSON, json.dumps(self.state(views=list(VIEW_IDS), hand_state='bare'))):
            for enabled, present1, present2, present3 in itertools.product((False, True), repeat=4):
                first, second = extra1 if present1 else None, extra2 if present2 else None
                third = extra3 if present3 else None
                with mock.patch('h3_character_sheet.reference13_node.render_reference13_guide') as render:
                    from PIL import Image
                    render.return_value = Image.new('RGB', (8, 8))
                    actual = node.compile(raw, character, first, second, use_layout_image=enabled, reference_image_3=third)
                self.assertIs(actual[4], character)
                self.assertIs(actual[5], first)
                self.assertIs(actual[6], second)
                self.assertIs(actual[7], third)
                self.assertEqual(render.call_count, int(enabled))
                self.assertEqual(actual[3] is not None, enabled)
                presence = dict(reference_image_1=present1, reference_image_2=present2, reference_image_3=present3)
                preview = compile_preview_request(json.dumps(dict(state_json=raw, use_layout_image=enabled,
                    reference_presence=presence)).encode(), max_resolution=16384)
                self.assertEqual(actual[0], preview['prompt'])
                self.assertEqual([r['picture_number'] for r in preview['reference_plan']], list(range(1, 2+int(enabled)+int(present1)+int(present2)+int(present3))))
                if present3:
                    self.assertEqual(preview['reference_plan'][-1]['core_input'], 'ref_images.ref_image_4')
                for ref in preview['reference_plan']:
                    if ref['source'].startswith('reference_image_'):
                        self.assertIn(ref['tag'] + ' is an additional reference', actual[0])
                if not present1 and not present2 and not present3:
                    self.assertEqual(actual[0], compile_reference13_state(raw, use_layout_image=enabled)['prompt'])

    def test_reject_invalid_images_and_preview_presence(self):
        node = H3CharacterSheetDesignerReference13()
        character = torch.zeros(1, 2, 2, 3)
        with self.assertRaises(legacy.StateValidationError): node.compile(DEFAULT_STATE_JSON, None)
        for bad in (torch.zeros(2, 2, 2, 3), torch.zeros(1, 2, 2, 4), torch.zeros(1, 0, 2, 3), torch.zeros(1, 2, 2, 3, dtype=torch.int32), 'image'):
            for target in ('character_image', 'reference_image_1', 'reference_image_2', 'reference_image_3'):
                with self.assertRaises(legacy.StateValidationError):
                    node.compile(DEFAULT_STATE_JSON, **{'character_image': character, target: bad})
        for presence in ([], {'reference_image_1': 1}, {'other': True}, {'reference_image_2': None}, {'reference_image_3': 'true'}):
            with self.assertRaises(legacy.StateValidationError):
                compile_preview_request(json.dumps(dict(state_json=DEFAULT_STATE_JSON, reference_presence=presence)).encode(), max_resolution=16384)


if __name__ == '__main__': unittest.main()
