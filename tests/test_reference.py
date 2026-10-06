"""Reference role, selection, style and legacy regression contracts."""

import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

import torch

from h3_character_sheet.compiler import VIEW_IDS, StateValidationError, compile_state
from h3_character_sheet.layout_image import render_layout_image
from h3_character_sheet.preview import compile_reference_preview_request
from h3_character_sheet.reference_compiler import DEFAULT_REFERENCE_STATE_JSON, FIVE_VIEWS, STYLE_PROMPTS, compile_reference_state
from h3_character_sheet.reference_node import H3CharacterSheetDesignerReference


def raw_state(views=FIVE_VIEWS, parts=None):
    state = json.loads(DEFAULT_REFERENCE_STATE_JSON)
    state['views'] = list(views)
    state['size'].update(mode='manual', manual_width=320, manual_height=192)
    state['part_prompts'] = parts or {}
    return json.dumps(state)


class ReferenceTests(unittest.TestCase):
    def test_off_preserves_original_state_layout_and_part_scope(self):
        for bits in range(1, 128):
            views = [view for index, view in enumerate(VIEW_IDS) if bits & (1 << index)]
            for parts in ({}, {'back_clothing': ' 背中にMOON {red|blue}\n星柄 ', 'footwear': 'bare feet'}):
                raw = raw_state(views, parts)
                refined = compile_reference_state(raw)
                legacy = compile_state(raw)
                self.assertEqual({k: v for k, v in refined.items() if k != 'prompt'}, {k: v for k, v in legacy.items() if k != 'prompt'})
                self.assertNotIn('<Picture 2>', refined['prompt'])
                self.assertNotIn('gray mannequin', refined['prompt'])
                self.assertIn('panel borders', refined['prompt'])
                self.assertEqual([panel['id'] for panel in refined['layout']['panels']], views)
                self.assertIn(f'Show exactly {len(views)} selected depictions:', refined['prompt'])
                for view in VIEW_IDS:
                    self.assertEqual(f'Panel {view}:' in refined['prompt'], view in views)
                self.assertEqual('Explicit appearance instruction (verbatim):\nbare feet' in refined['prompt'], bool(parts) and any(view in views for view in ('body_front', 'body_left', 'body_back', 'feet')))

    def test_off_style_does_not_rewrite_part_text_or_legacy_layout(self):
        instruction = 'Keep the rendering style of <Picture 1>; skin appearance, visual style, clothing\n 背中の「MOON」'
        raw = raw_state(VIEW_IDS, {'other': instruction})
        legacy = compile_state(raw)
        for style, text in STYLE_PROMPTS.items():
            result = compile_reference_state(raw, style=style)
            self.assertEqual(result['layout'], legacy['layout'])
            self.assertEqual(result['state_json'], legacy['state_json'])
            self.assertEqual(result['prompt'].count(instruction), 1)
            self.assertIn('Layout specification (semantic guidance, not visible text):', result['prompt'])
            if style != 'none':
                self.assertIn(text, result['prompt'])
                self.assertNotIn('Keep the rendering style of <Picture 1> except for appearance changes', result['prompt'])

    def test_all_selected_views_only_reach_reference_instructions_and_image(self):
        for bits in range(1, 128):
            views = [view for index, view in enumerate(VIEW_IDS) if bits & (1 << index)]
            result = compile_reference_state(raw_state(views), use_layout_image=True)
            self.assertEqual([panel['id'] for panel in result['layout']['panels']], views)
            self.assertIn(f'{len(views)} selected panels', result['prompt'])
            for view in VIEW_IDS:
                self.assertEqual(f'Panel {view}:' in result['prompt'], view in views)
            image = render_layout_image(result['layout'])
            self.assertEqual(image.size, (320, 192))
            for panel in result['layout']['panels']:
                left, top, width, height = panel['rect']
                self.assertEqual(image.getpixel((round(left * 320), round(top * 192))), (0, 0, 0))

    def test_picture_roles_static_frames_busts_and_no_coordinate_duplication(self):
        prompt = compile_reference_state(raw_state(VIEW_IDS), use_layout_image=True)['prompt']
        for text in ('single character in <Picture 1>', '<Picture 2> is the white sheet', '2 bust portraits', '3 full-body views', '2 isolated detail panels', 'Crop at the chest', 'nose points to the RIGHT', 'black panel frames', 'first frame', 'last frame', 'No speech'):
            self.assertIn(text, prompt)
        for text in ('"rect":', '"canvas":', 'Do not add panel borders', '<image1>', '<image2>', 'Keep the rendering style of <Picture 2>'):
            self.assertNotIn(text, prompt)

    def test_styles_change_rendering_only_without_competing_reference_style(self):
        raw = raw_state()
        for guided in (False, True):
            for style, instruction in STYLE_PROMPTS.items():
                prompt = compile_reference_state(raw, use_layout_image=guided, style=style)['prompt']
                if style != 'none':
                    self.assertIn(instruction, prompt)
                    self.assertNotIn('Keep the rendering style of <Picture 1>', prompt)
                    self.assertIn('Change rendering technique only', prompt)
                    self.assertIn('do not add scenery, props', prompt)
                    self.assertIn('overall_soundscape:', prompt)

    def test_verbatim_part_scope_precedence_and_subject_lettering(self):
        instruction = ' 背中に「MOON {red|blue}」\n星柄 \\ "青" '
        for guided in (False, True):
            prompt = compile_reference_state(raw_state(VIEW_IDS, {'back_clothing': instruction, 'upper_clothing': 'blue shirt', 'footwear': 'bare feet', 'other': 'silver buttons'}), use_layout_image=guided)['prompt']
            self.assertIn(instruction, prompt)
            self.assertIn('back_clothing takes precedence over upper_clothing', prompt)
            if guided:
                self.assertIn('applies to body_left, body_back', prompt)
                self.assertIn('subject lettering or patterns are allowed', prompt)
            else:
                self.assertEqual(prompt.count(instruction), 1)
                self.assertIn('applies to body_left, body_back', prompt)
                self.assertIn('partially_preserved -', prompt)
            prompt = compile_reference_state(raw_state(['hands'], {'back_clothing': instruction}), use_layout_image=guided)['prompt']
            self.assertNotIn(instruction, prompt)

    def test_node_tensor_and_preview_match_without_preview_image_rendering(self):
        node = H3CharacterSheetDesignerReference()
        inputs = node.INPUT_TYPES()
        self.assertEqual(json.loads(inputs['required']['state_json'][1]['default'])['views'], list(FIVE_VIEWS))
        self.assertEqual(inputs['optional']['style'][1]['default'], 'none')
        self.assertEqual(node.RETURN_TYPES, ('STRING', 'INT', 'INT', 'IMAGE'))
        raw = raw_state()
        for guided, style in ((False, 'none'), (False, 'photo'), (True, 'none'), (True, 'photo')):
            envelope = {'state_json': raw, 'use_layout_image': guided, 'style': style}
            with mock.patch.dict(sys.modules, {'nodes': types.SimpleNamespace(MAX_RESOLUTION=16384)}):
                output = node.compile(**envelope)
                self.assertIs(node.VALIDATE_INPUTS(**envelope), True)
            with mock.patch('h3_character_sheet.reference_node.render_layout_image', side_effect=AssertionError('Preview must not draw IMAGE')):
                preview = compile_reference_preview_request(json.dumps(envelope).encode(), max_resolution=16384)
            self.assertEqual(output[:3], (preview['prompt'], preview['width'], preview['height']))
            if guided:
                self.assertEqual(tuple(output[3].shape), (1, 192, 320, 3))
                self.assertEqual(output[3].dtype, torch.float32)
                self.assertGreaterEqual(float(output[3].min()), 0)
                self.assertLessEqual(float(output[3].max()), 1)
            else:
                self.assertIsNone(output[3])

    def test_off_bypasses_image_rendering_and_on_restores_the_same_layout(self):
        node = H3CharacterSheetDesignerReference()
        raw = raw_state()
        with mock.patch.dict(sys.modules, {'nodes': types.SimpleNamespace(MAX_RESOLUTION=16384)}):
            first_on = node.compile(raw, use_layout_image=True)
            with mock.patch('h3_character_sheet.reference_node.render_layout_image', side_effect=AssertionError('OFF must not render an image')):
                off = node.compile(raw, use_layout_image=False)
            second_on = node.compile(raw, use_layout_image=True)
        self.assertEqual(off[:3], tuple(compile_reference_state(raw)[key] for key in ('prompt', 'width', 'height')))
        self.assertIsNone(off[3])
        self.assertEqual(first_on[:3], second_on[:3])
        self.assertTrue(torch.equal(first_on[3], second_on[3]))

    def test_invalid_reference_envelopes_fail_clearly(self):
        for override in ({'style': 'unknown'}, {'style': []}, {'use_layout_image': 1}, {'unrecognized': True}):
            with self.assertRaises(StateValidationError):
                compile_reference_preview_request(json.dumps({'state_json': raw_state(), **override}).encode(), max_resolution=16384)

    def test_official_template_orders_character_before_layout_and_defaults_off(self):
        workflow = json.loads((Path(__file__).resolve().parents[1] / 'workflows/H3_Character_Sheet_Designer_wf.json').read_text(encoding='utf-8'))
        graph = workflow['definitions']['subgraphs'][0]
        designer = next(node for node in workflow['nodes'] if node['type'] == 'H3CharacterSheetDesignerReference')
        self.assertIs(designer['widgets_values'][1], False)
        self.assertIs(designer['widgets_values_named']['use_layout_image'], False)
        self.assertEqual(designer['widgets_values'][2], 'none')
        self.assertEqual(json.loads(designer['widgets_values'][0])['views'], list(FIVE_VIEWS))
        self.assertEqual(designer['size'], [870, 1100])
        subgraph = next(node for node in workflow['nodes'] if node['type'] == graph['id'])
        native = next(node for node in graph['nodes'] if node['type'] == 'MiniMaxH3ReferenceToVideo')
        ref_inputs = [value for value in native['inputs'] if value['name'].startswith('ref_images.') and value.get('link')]
        self.assertEqual([value['name'] for value in ref_inputs], ['ref_images.ref_image_0', 'ref_images.ref_image_1'])
        outer_links = {link[0]: link for link in workflow['links']}
        inner_links = {link['id']: link for link in graph['links']}
        load_image = next(node for node in workflow['nodes'] if node['type'] == 'LoadImage')
        expected = {'ref_images.ref_image_0': (load_image['id'], 0), 'ref_images.ref_image_1': (designer['id'], 3), 'prompt': (designer['id'], 0), 'width': (designer['id'], 1), 'height': (designer['id'], 2)}
        for name, source in expected.items():
            native_input = next(value for value in native['inputs'] if value['name'] == name)
            internal = inner_links[native_input['link']]
            self.assertEqual(internal['origin_id'], graph['inputNode']['id'])
            exposed_name = graph['inputs'][internal['origin_slot']]['name']
            external_input = next(value for value in subgraph['inputs'] if value['name'] == exposed_name)
            external = outer_links[external_input['link']]
            self.assertEqual(tuple(external[1:3]), source)
        self.assertEqual(native['widgets_values_named']['length'], 5)
        self.assertEqual(native['widgets_values_named']['ref_image_size'], 'match')
        self.assertEqual(subgraph['widgets_values_named']['sampler_name'], 'euler')
        self.assertEqual(subgraph['widgets_values_named']['scheduler'], 'simple')
        self.assertEqual(subgraph['widgets_values_named']['steps'], 20)
        nodes = {node['type']: node for node in graph['nodes']}
        self.assertEqual(nodes['ImageFromBatch']['widgets_values'], [0, 1])
        self.assertEqual(nodes['ImageFromBatch']['widgets_values_named'], {'batch_index': 0, 'length': 1})
        self.assertNotIn('MiniMaxH3AddGuide', nodes)


if __name__ == '__main__':
    unittest.main()
