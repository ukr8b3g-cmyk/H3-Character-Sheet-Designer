import copy
import json
import unittest

from h3_character_sheet.on_compiler_13 import compile_reference13_state
from h3_character_sheet.state_13 import DEFAULT_STATE


def raw(role='same_character', views=None, **choices):
    state = copy.deepcopy(DEFAULT_STATE)
    state.update(choices)
    state['reference_roles'] = {f'reference_image_{i}': role if i == 1 else 'same_character' for i in (1, 2, 3)}
    if views is not None:
        state['views'] = views
    return json.dumps(state)


def retention(prompt):
    return prompt.split('retention_analysis:', 1)[1].split('detailed_description:', 1)[0]


class Reference13PolicyTests(unittest.TestCase):
    def test_connected_roles_change_retention_and_priority_on_and_off(self):
        for guide in (False, True):
            for role in ('face', 'head', 'clothing', 'hands', 'footwear'):
                with self.subTest(guide=guide, role=role):
                    result = compile_reference13_state(raw(role), use_layout_image=guide,
                                                       reference_presence={'reference_image_1': True})
                    prompt = result['prompt']
                    self.assertIn('partially_preserved', retention(prompt))
                    self.assertNotIn('fully_preserved', retention(prompt))
                    self.assertIn(f'role {role}', retention(prompt))
                    priority = next(line for line in prompt.splitlines() if line.startswith('Priority:'))
                    self.assertLess(priority.index('choices'), priority.index('named-part'))
                    self.assertLess(priority.index('named-part'), priority.index('eligible dedicated'))
                    self.assertLess(priority.index('eligible dedicated'), priority.index('baseline reference'))

    def test_clothing_reference_does_not_remove_hair_or_hand_protection(self):
        prompt = compile_reference13_state(raw('clothing'), reference_presence={'reference_image_1': True})['prompt']
        self.assertNotIn('Auto means retain the reference;', prompt)
        self.assertIn('Auto retains this resolved design', prompt)
        self.assertIn('tied or loose arrangement', prompt)
        self.assertIn('do not add gloves to bare hands', prompt)
        self.assertIn('Keep referenced socks or tights separately', prompt)

    def test_head_hands_footwear_replace_only_their_conflicting_retention(self):
        for role, conflict in [('head', 'Unless an applicable explicit choice'),
                               ('hands', 'Bare hands stay bare'),
                               ('footwear', 'Keep referenced socks or tights separately')]:
            with self.subTest(role=role):
                prompt = compile_reference13_state(raw(role), reference_presence={'reference_image_1': True})['prompt']
                self.assertNotIn(conflict, prompt)
                self.assertIn('Keep exactly the referenced garment inventory', prompt)

    def test_unconnected_dedicated_roles_do_not_change_prompt(self):
        baseline = compile_reference13_state(raw())['prompt']
        for role in ('head', 'clothing', 'hands', 'footwear'):
            self.assertEqual(compile_reference13_state(raw(role))['prompt'], baseline)

    def test_face_role_preserves_hair_and_front_back_roles_keep_surface_scope(self):
        from h3_character_sheet.appearance_policy_13 import build_appearance_policy
        from h3_character_sheet.state_13 import parse_reference13_state
        for guide in (False, True):
            prompt = compile_reference13_state(raw('face'), use_layout_image=guide,
                                               reference_presence={'reference_image_1': True})['prompt']
            self.assertIn('Keep the shared identity and hair construction based on <Picture 1>', prompt)
            self.assertIn('tied or loose arrangement', prompt)
        state = parse_reference13_state(raw(), max_resolution=16384)
        for role, allowed, forbidden in (
            ('clothing_front', 'body_front', 'body_back'),
            ('clothing_back', 'body_back', 'body_front'),
        ):
            policy = build_appearance_policy(state, [{'role': role, 'tag': '<Picture 2>'}])
            views = {view for item in policy for scope in item['parts'].values() for view in scope}
            self.assertIn(allowed, views)
            self.assertNotIn(forbidden, views)

    def test_inapplicable_roles_do_not_change_retention(self):
        cases = [('footwear', ['face_front'], {}), ('head', ['hands'], {}),
                 ('face', ['body_back'], {}), ('clothing', ['feet'], {}),
                 ('hands', ['clothing_front'], {'clothing_mode': 'garment'}),
                 ('clothing_back', ['face_front'], {})]
        for guide in (False, True):
            for role, views, choices in cases:
                with self.subTest(guide=guide, role=role, views=views):
                    value = raw(role, views, **choices)
                    baseline = compile_reference13_state(value, use_layout_image=guide)['prompt']
                    prompt = compile_reference13_state(value, use_layout_image=guide,
                                                       reference_presence={'reference_image_1': True})['prompt']
                    self.assertEqual(retention(prompt), retention(baseline))
                    self.assertIn('no eligible part is visible', prompt)

    def test_missing_slots_preserve_physical_wires_and_packed_numbering(self):
        state = json.loads(raw())
        state['reference_roles']['reference_image_3'] = 'clothing_back'
        for guide in (False, True):
            result = compile_reference13_state(json.dumps(state), use_layout_image=guide,
                                               reference_presence={'reference_image_3': True})
            reference = result['reference_plan'][-1]
            self.assertEqual(reference['source'], 'reference_image_3')
            self.assertEqual(reference['core_input'], 'ref_images.ref_image_4')
            self.assertEqual(reference['picture_number'], 3 if guide else 2)

    def test_explicit_choices_and_parts_remain_above_dedicated_references(self):
        state = json.loads(raw('hands', hand_state='bare'))
        state['part_prompts'] = {'hands': 'silver ring'}
        prompt = compile_reference13_state(json.dumps(state), reference_presence={'reference_image_1': True})['prompt']
        self.assertIn('All naturally visible hands are bare', prompt)
        self.assertIn('silver ring', prompt)
        self.assertIn('higher-priority choices and named-part details', prompt)

    def test_same_role_conflicts_use_later_connected_reference(self):
        state = json.loads(raw('clothing'))
        state['reference_roles']['reference_image_3'] = 'clothing'
        prompt = compile_reference13_state(json.dumps(state), reference_presence={
            'reference_image_1': True, 'reference_image_3': True})['prompt']
        self.assertIn('dedicated <Picture 2> role clothing', retention(prompt))
        self.assertIn('dedicated <Picture 3> role clothing', retention(prompt))
        self.assertIn('later connected references win within the same role', prompt)


if __name__ == '__main__':
    unittest.main()
