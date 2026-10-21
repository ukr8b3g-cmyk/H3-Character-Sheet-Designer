import copy
import json
import unittest
from h3_character_sheet.state_13 import DEFAULT_STATE, parse_reference13_state
from h3_character_sheet.on_compiler_13 import compile_reference13_state

class ReferenceRoleTests(unittest.TestCase):
    def test_roles_follow_connected_images_and_layout_numbering(self):
        state=copy.deepcopy(DEFAULT_STATE)
        state['reference_roles']={'reference_image_1':'face','reference_image_2':'clothing','reference_image_3':'clothing_back'}
        for enabled in (False,True):
            result=compile_reference13_state(json.dumps(state),use_layout_image=enabled,reference_presence={'reference_image_2':True,'reference_image_3':True})
            offset=3 if enabled else 2
            self.assertIn(f'<Picture {offset}> has role clothing:',result['prompt'])
            self.assertIn(f'<Picture {offset+1}> has role clothing_back:',result['prompt'])
            self.assertNotIn('has role face:',result['prompt'])
            self.assertIn("Ignore the source person's face",result['prompt'])
            self.assertEqual(json.loads(result['state_json'])['reference_roles'],state['reference_roles'])
    def test_default_roles_preserve_prompt(self):
        state=copy.deepcopy(DEFAULT_STATE)
        kwargs={'reference_presence':{'reference_image_3':True}}
        before=compile_reference13_state(json.dumps(state),**kwargs)
        state['reference_roles']={f'reference_image_{i}':'same_character' for i in range(1,4)}
        self.assertEqual(before['prompt'],compile_reference13_state(json.dumps(state),**kwargs)['prompt'])
    def test_reject_unknown_and_incomplete_roles(self):
        for roles in ({},{'reference_image_1':'face'}, {f'reference_image_{i}':'invalid' for i in range(1,4)}):
            with self.assertRaises(ValueError):
                parse_reference13_state(json.dumps({**DEFAULT_STATE,'reference_roles':roles}))
