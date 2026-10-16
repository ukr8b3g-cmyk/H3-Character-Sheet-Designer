"""Reference-driven, subject-independent prompt contracts for Reference13."""
import copy
import json
import unittest

from h3_character_sheet.on_compiler_13 import compile_reference13_state
from h3_character_sheet.state_13 import DEFAULT_STATE
from h3_character_sheet.view_catalog_13 import PRESETS, VIEW_IDS


class Reference13PromptContractTests(unittest.TestCase):
    def result(self, views, guide=False, **choices):
        state = copy.deepcopy(DEFAULT_STATE)
        state.update(choices, views=list(views))
        return compile_reference13_state(json.dumps(state), use_layout_image=guide)

    def test_single_front_does_not_use_multi_view_scaffold(self):
        for guide in (False, True):
            p = self.result(['body_front'], guide)['prompt']
            self.assertIn('Exactly one selected view in one region', p)
            self.assertIn('Exactly one depiction of the person', p)
            self.assertNotIn('All views coexist', p)
            self.assertNotIn('alternate views', p)
            self.assertNotIn('full-body columns', p)
            self.assertNotIn('Required inventory:', p)
            self.assertNotIn('other views', p)
            self.assertEqual(p.count('Panel body_front:'), 1)

    def test_paired_details_remain_pairs_and_garments_do_not_require_a_person(self):
        for view in ('hands', 'feet'):
            p = self.result([view])['prompt']
            self.assertIn('one left and one right' if view == 'feet' else 'one left and one right', p)
            self.assertNotIn('Exactly one depiction of the person', p)
            self.assertNotIn('side-by-side pair', p)
        garment = self.result(['clothing_front'], clothing_mode='garment')['prompt']
        self.assertNotIn('Exactly one depiction of the person', garment)
        self.assertIn('Sleeves and openings are empty', garment)

    def test_left_direction_is_explicit_in_standard_and_extended_paths(self):
        for guide in (False, True):
            for preset in ('five', 'turnaround', 'head', 'detail'):
                p = self.result(PRESETS[preset], guide)['prompt']
                for view in ('face_left', 'body_left'):
                    if view in PRESETS[preset]:
                        line = next(line for line in p.splitlines() if line.startswith(f'Panel {view}:'))
                        self.assertIn('RIGHT', line)
                for view in ('face_right', 'face_3q_right'):
                    if view in PRESETS[preset]:
                        line = next(line for line in p.splitlines() if line.startswith(f'Panel {view}:'))
                        self.assertIn('LEFT', line)

    def test_head_grid_prose_follows_existing_two_column_three_row_geometry(self):
        for guide in (False, True):
            r = self.result(PRESETS['head'], guide)
            p = r['prompt']
            self.assertIn('Head views: 6 separate regions in 3 row(s) and 2 column(s)', p)
            self.assertIn('row 1, column 1: front portrait', p)
            self.assertIn('row 3, column 2: rear portrait', p)
            self.assertIn('Both eyes visible with the farther eye foreshortened', p)

    def test_all_thirteen_have_distinct_inventory_and_instructions(self):
        for guide in (False, True):
            p = self.result(VIEW_IDS, guide)['prompt']
            self.assertIn('6 head-and-chest views + 3 full-body views + 2 clothing-detail views + 1 paired-hands detail + 1 paired-feet/footwear detail = 13', p)
            for view in VIEW_IDS:
                self.assertEqual(p.count(f'Panel {view}:'), 1)
            self.assertIn('Front and rear clothing details are separate required depictions', p)
            self.assertIn('Clothing details: 2 separate regions in 1 row(s) and 2 column(s)', p)

    def test_unselected_clothing_back_is_not_required(self):
        p = self.result(['body_front', 'clothing_front'])['prompt']
        self.assertNotIn('Front and rear clothing details are separate required depictions', p)
        self.assertNotIn('Panel clothing_back:', p)

    def test_worn_clothing_crop_and_garment_only_are_distinct(self):
        for guide in (False, True):
            worn = self.result(PRESETS['clothing'], guide)['prompt']
            self.assertIn('same character wearing the outfit', worn)
            self.assertIn('do not extend', worn.lower())
            self.assertIn('complete referenced garment set, whether one piece or multiple pieces', worn)
            self.assertIn('body parts or accessories below that edge', worn)
            self.assertIn('never widen the crop to include them', worn)
            self.assertIn('Fit the whole outfit inside this region at a uniform scale', worn)
            self.assertNotIn('No wearer, skin', worn)
            garment = self.result(PRESETS['clothing'], guide, clothing_mode='garment')['prompt']
            self.assertIn('No head, neck, torso, skin, body, arms, hands, legs, feet or wearer', garment)

    def test_auto_retains_coverage_but_explicit_choices_override_it(self):
        auto = self.result(PRESETS['five'])['prompt']
        self.assertIn('tied or loose arrangement', auto)
        self.assertIn('do not add gloves to bare hands', auto)
        self.assertIn('Keep referenced socks or tights separately', auto)
        explicit = self.result(PRESETS['five'], hand_state='gloved', footwear_state='unshod', clothing_type='pants')['prompt']
        self.assertNotIn('do not add gloves to bare hands', explicit)
        self.assertNotIn('Do not add or remove footwear', explicit)
        self.assertIn('All naturally visible hands wear actual gloves', explicit)
        self.assertIn('No shoes or boots on either foot', explicit)
        self.assertIn('separate trouser or pants leg structures', explicit)

    def test_each_region_has_placement_camera_and_content_in_one_record(self):
        for guide in (False, True):
            r = self.result(VIEW_IDS, guide)
            p = r['prompt']
            records = [line for line in p.splitlines() if line.startswith('Panel ')]
            self.assertEqual(len(records), len(VIEW_IDS))
            for panel in r['layout']['panels']:
                record = next(line for line in records if line.startswith(f"Panel {panel['id']}:"))
                self.assertIn('row ', record)
                self.assertIn('column ', record)
                if guide:
                    bounds = next(g['bounds'] for g in r['guide_geometry']['panels'] if g['id'] == panel['id'])
                    self.assertIn(json.dumps(bounds, separators=(',', ':')), record)
                else:
                    self.assertIn(json.dumps(panel['rect'], separators=(',', ':')), record)
            self.assertNotIn('"panels":', p)
            self.assertNotIn('Guide artwork geometry', p)
            self.assertNotIn('anatomical left', p)
            self.assertNotIn('anatomical right', p)

    def test_auto_does_not_prescribe_the_test_subject_or_a_costume(self):
        p = self.result(VIEW_IDS)['prompt'].lower()
        for subject_detail in ('white blouse', 'plaid', 'burgundy', 'school uniform', 'blazer',
                               'ponytail', 'twintails', 'black socks', 'krea2_', 'dasiwa'):
            self.assertNotIn(subject_detail, p)
        self.assertIn('exactly the referenced garment inventory', p)
        self.assertIn('do not complete a presumed costume category', p)
        self.assertIn('closed material stays closed', p)
        self.assertIn('existing openings stay open', p)
        self.assertIn('uncovered skin stays uncovered', p)
        self.assertIn('number and placement of gathered sections', p)
        self.assertIn('presence or absence of hair', p)

    def test_general_rules_allow_arbitrary_requested_designs(self):
        # Details come only from user choices or part text, never the test image.
        from itertools import product
        from h3_character_sheet.state_13 import SETTINGS
        fields = tuple(SETTINGS)
        for values in product(*(SETTINGS[field] for field in fields)):
            choices = dict(zip(fields, values))
            p = self.result(VIEW_IDS, part_prompts={'upper_clothing': 'layered copper armor',
                                                   'head_hair': 'short silver hair'}, **choices)['prompt']
            self.assertIn('layered copper armor', p)
            self.assertIn('short silver hair', p)
            if choices['clothing_type'] == 'reference':
                self.assertIn('exactly the referenced garment inventory', p)
            else:
                self.assertNotIn('exactly the referenced garment inventory', p)
            if choices['footwear_state'] == 'reference':
                self.assertIn('closed material stays closed', p)
            else:
                self.assertNotIn('closed material stays closed', p)

    def test_complete_outfit_framing_applies_to_single_clothing_and_thirteen_views(self):
        for guide in (False, True):
            for shape in ('reference', 'pants', 'skirt_robe'):
                for views in (['clothing_front'], ['clothing_back'], PRESETS['clothing'], PRESETS['detail']):
                    p = self.result(views, guide, clothing_type=shape)['prompt']
                    for view in ('clothing_front', 'clothing_back'):
                        if view not in views:
                            continue
                        record = next(line for line in p.splitlines() if line.startswith(f'Panel {view}:'))
                        self.assertIn('complete referenced garment set, whether one piece or multiple pieces', record)
                        self.assertIn('start above its neckline and shoulders', record)
                        self.assertIn('entire upper garment and all garment layers', record)
                        self.assertIn('finish just below the lowest garment hem', record)
                        self.assertIn('reduce magnification until both its neckline and lowest hem are visible together', record)
                        self.assertIn('front-facing' if view == 'clothing_front' else 'direct rear', record)
                        self.assertNotIn('upper crop is at the base of the neck', record)
                        self.assertNotIn('shared garment construction', record)
                p = self.result(PRESETS['detail'], guide, clothing_type=shape)['prompt']
                body = next(line for line in p.splitlines() if line.startswith('Panel body_front:'))
                self.assertIn('shared garment construction', body)
                self.assertIn('shared identity and hair construction', body)
                garment = self.result(PRESETS['clothing'], guide, clothing_mode='garment', clothing_type=shape)['prompt']
                self.assertNotIn('shoulder outlines', garment)
                self.assertNotIn('visible length of limb', garment)

    def test_region_appearance_is_shared_without_overriding_explicit_changes(self):
        for guide in (False, True):
            p = self.result(VIEW_IDS, guide, clothing_type='pants',
                            part_prompts={'head_hair': 'bald head', 'upper_clothing': 'short sleeveless armor'})['prompt']
            self.assertIn('Resolve one shared character design', p)
            self.assertIn('bald head', p)
            self.assertIn('short sleeveless armor', p)
            self.assertNotIn('exactly the referenced garment inventory', p)
            for view in (*PRESETS['head'], 'body_front', 'body_left', 'body_back'):
                record = next(line for line in p.splitlines() if line.startswith(f'Panel {view}:'))
                self.assertIn('based on <Picture 1> and applicable explicit directives', record)
                self.assertIn('Apply an eligible head_hair directive consistently', record)
                self.assertIn('do not restyle hair for this camera', record)
            for view in ('hands', 'feet', 'clothing_front', 'clothing_back'):
                record = next(line for line in p.splitlines() if line.startswith(f'Panel {view}:'))
                self.assertNotIn('head_hair directive', record)


if __name__ == '__main__':
    unittest.main()
