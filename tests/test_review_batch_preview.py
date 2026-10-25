import copy
import json
import unittest

from h3_character_sheet.compiler import StateValidationError
from h3_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE, MULTI_VIEW_IDS
from h3_character_sheet.output_plan import compile_output_plan, compile_output_preview


class BatchPreviewTests(unittest.TestCase):
    def test_large_valid_items_have_a_complete_bounded_overview(self):
        for guide in (False, True):
            for height, limit, all_views in [(4480, 16384, True), (4096, 8192, False)]:
                with self.subTest(guide=guide, height=height, limit=limit):
                    state = copy.deepcopy(DEFAULT_MULTI_STATE)
                    state['size']['body_height'] = height
                    if all_views:
                        state['views'] = list(MULTI_VIEW_IDS)
                    raw = json.dumps(state)
                    options = dict(batch_out=True, use_layout_image=guide, max_resolution=limit)
                    plan = compile_output_plan(raw, **options)
                    preview = compile_output_preview(raw, **options)
                    self.assertEqual(plan, preview['batch_plan'])
                    self.assertEqual([p['id'] for p in preview['layout']['panels']], state['views'])
                    self.assertEqual(preview['layout']['canvas'], [preview['width'], preview['height']])
                    self.assertLessEqual(max(preview['width'], preview['height']), limit)
                    self.assertEqual(json.loads(preview['state_json']), state)
                    for item in plan['items']:
                        self.assertLessEqual(max(item['width'], item['height']), limit)

    def test_a_real_oversized_item_is_rejected_by_both_paths(self):
        state = copy.deepcopy(DEFAULT_MULTI_STATE)
        state['size']['body_height'] = 8192
        for compile in (compile_output_plan, compile_output_preview):
            with self.assertRaises(StateValidationError):
                compile(json.dumps(state), batch_out=True, max_resolution=8192)

    def test_manual_item_dimensions_are_preserved_on_and_off(self):
        state = copy.deepcopy(DEFAULT_MULTI_STATE)
        state['views'] = list(MULTI_VIEW_IDS)
        state['size'].update(mode='manual', manual_width=512, manual_height=768)
        for guide in (False, True):
            preview = compile_output_preview(json.dumps(state), batch_out=True, use_layout_image=guide)
            self.assertEqual((preview['width'], preview['height']), (512, 768))
            self.assertEqual({(i['width'], i['height']) for i in preview['batch_plan']['items']}, {(512, 768)})

    def test_non_batch_preserves_existing_plan_and_validation(self):
        state = copy.deepcopy(DEFAULT_MULTI_STATE)
        raw = json.dumps(state)
        plan = compile_output_plan(raw)
        preview = compile_output_preview(raw)
        expected = {k: v for k, v in plan['items'][0].items() if k not in ('index', 'view_id', 'filename_suffix')}
        self.assertEqual({k: v for k, v in preview.items() if k != 'batch_plan'}, expected)
        state['size']['body_height'] = 4480
        state['views'] = list(MULTI_VIEW_IDS)
        with self.assertRaises(StateValidationError):
            compile_output_preview(json.dumps(state), batch_out=False)


if __name__ == '__main__':
    unittest.main()
