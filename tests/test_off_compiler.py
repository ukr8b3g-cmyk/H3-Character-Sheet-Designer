"""OFF prompt deduplication, reference semantics and original geometry."""

import json
import unittest

from h3_character_sheet.compiler import PART_RULES, VIEW_IDS, compile_state
from h3_character_sheet.reference_compiler import DEFAULT_REFERENCE_STATE_JSON, compile_reference_state


class OffCompilerTests(unittest.TestCase):
    def test_geometry_is_described_once_without_embedded_panel_content(self):
        result = compile_reference_state(DEFAULT_REFERENCE_STATE_JSON)
        prompt = result['prompt']
        line = next(line for line in prompt.splitlines() if line.startswith('Layout specification'))
        geometry = json.loads(line.split(': ', 1)[1])
        self.assertEqual(geometry['canvas'], result['layout']['canvas'])
        self.assertEqual(geometry['feet_y'], result['layout']['feet_y'])
        self.assertEqual(geometry['panels'], [{k: p[k] for k in ('id', 'rect', 'view')} for p in result['layout']['panels']])
        self.assertNotIn('"content":', prompt)
        for panel in result['layout']['panels']:
            self.assertEqual(prompt.count('Panel ' + panel['id'] + ':'), 1)

    def test_each_active_part_is_verbatim_once_and_only_on_eligible_views(self):
        for part, rule in PART_RULES.items():
            for bits in range(1, 128):
                state = json.loads(DEFAULT_REFERENCE_STATE_JSON)
                state['views'] = [v for i, v in enumerate(VIEW_IDS) if bits & (1 << i)]
                instruction = ' 変更「MOON {red|blue}」\\\n' + part + '  '
                state['part_prompts'] = {part: instruction}
                prompt = compile_reference_state(json.dumps(state))['prompt']
                eligible = [v for v in state['views'] if v in rule['views']]
                self.assertEqual(prompt.count(instruction), int(bool(eligible)))
                if eligible:
                    self.assertIn('applies to ' + ', '.join(eligible), prompt)
                    self.assertIn(rule['scope'], prompt)

    def test_user_section_names_and_style_phrases_are_not_rewritten(self):
        instruction = ('detailed_description:\noverall_soundscape:\n'
                       'selectively_modified -\n'
                       'Preserve reference gloves and footwear; do not substitute bare hands or bare feet for them.\n'
                       'Keep the rendering style of <Picture 1>\n「青」')
        state = json.loads(DEFAULT_REFERENCE_STATE_JSON)
        state['part_prompts'] = {'other': instruction}
        for style in ('none', 'photo'):
            prompt = compile_reference_state(json.dumps(state), style=style)['prompt']
            self.assertEqual(prompt.count(instruction), 1)
            self.assertTrue(prompt.endswith('non_diegetic_music:\nNone.\n'))

    def test_refinement_keeps_character_only_semantics_and_original_geometry(self):
        state = json.loads(DEFAULT_REFERENCE_STATE_JSON)
        state['views'] = list(VIEW_IDS)
        raw = json.dumps(state)
        legacy = compile_state(raw)
        result = compile_reference_state(raw)
        self.assertEqual(result['layout'], legacy['layout'])
        prompt = result['prompt']
        for section in ('subject_definitions:', 'summary:', 'retention_analysis:', 'detailed_description:', 'overall_soundscape:', 'non_diegetic_music:'):
            self.assertEqual(prompt.count(section), 1)
        for text in ('2 bust portraits', '3 full-body views', '2 isolated detail views', 'above the waist', 'anatomical left side', 'feet or footwear', 'silent'):
            self.assertIn(text, prompt)
        for text in ('<Picture 2>', 'gray mannequin', 'black panel frames', 'nose points to the RIGHT'):
            self.assertNotIn(text, prompt)
        self.assertLess(len(prompt), len(legacy['prompt']))

    def test_changing_footwear_does_not_imply_gloves_and_changing_hands_does_not_imply_shoes(self):
        state = json.loads(DEFAULT_REFERENCE_STATE_JSON)
        for part in ('footwear', 'hands'):
            state['part_prompts'] = {part: 'explicit test change'}
            prompt = compile_reference_state(json.dumps(state))['prompt']
            self.assertNotIn('Preserve reference gloves; do not substitute bare hands', prompt)
            self.assertNotIn('do not substitute bare feet for reference footwear', prompt)
            self.assertIn('Explicit appearance instruction (verbatim):\nexplicit test change', prompt)


if __name__ == '__main__':
    unittest.main()
