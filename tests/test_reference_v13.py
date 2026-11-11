import copy, json, unittest
from h3_character_sheet.state_13 import DEFAULT_STATE
from h3_character_sheet.view_catalog_13 import VIEW_IDS
from h3_character_sheet.reference_v13_compiler import compile_reference_v13_state
from h3_character_sheet.on_compiler_13 import compile_reference13_state
from h3_character_sheet.guide_13 import render_reference13_guide

class V13Tests(unittest.TestCase):
    def test_objects_scopes_and_legacy(self):
        s=copy.deepcopy(DEFAULT_STATE); s['views']=list(VIEW_IDS)
        s['part_prompts']={'head_hair':'silver hair','hands':'red gloves','upper_clothing':'purple coat','back_clothing':'gold pattern'}
        raw=json.dumps(s); old=compile_reference13_state(raw)
        new=compile_reference_v13_state(raw, reference_presence={'reference_image_1':True,'reference_image_2':True,'reference_image_3':True})
        self.assertEqual(new['layout'],compile_reference_v13_state(raw,use_layout_image=True)['layout'])
        self.assertEqual(new['state']['clothing_mode'],'garment')
        self.assertIn('same character wearing the outfit',old['prompt'])
        self.assertNotIn('same character wearing the outfit',new['prompt'])
        self.assertEqual(len(new['reference_plan']),4)
        for v in VIEW_IDS:self.assertEqual(new['prompt'].count('Panel '+v+':'),1)
        for line in new['prompt'].splitlines():
            if line.startswith(('Part directive head_hair','Part directive hands')):self.assertNotIn('clothing_',line)
        self.assertIn('purple coat',new['prompt']);self.assertIn('gold pattern',new['prompt'])
        self.assertEqual(new['prompt'].count('No human.'),2)
    def test_guide_contains_outfits_and_five_references(self):
        s=copy.deepcopy(DEFAULT_STATE);s['views']=list(VIEW_IDS)
        r=compile_reference_v13_state(json.dumps(s),use_layout_image=True,reference_presence={f'reference_image_{i}':True for i in range(1,4)})
        self.assertEqual(len(r['reference_plan']),5)
        image=render_reference13_guide(r['guide_geometry'],r['layout'])
        for p in r['guide_geometry']['panels']:
            if p['id'].startswith('clothing_'):
                self.assertFalse(p['blank']);x,y,w,h=p['rect']
                self.assertLess(image.crop((x+5,y+5,x+w-5,y+h-5)).convert('L').getextrema()[0],200)

    def test_successful_non_clothing_prompts_unchanged(self):
        groups=[['face_front','face_left','body_front','body_left','body_back'],
                ['body_front'],['body_front','body_left','body_back'],
                ['face_front','face_left','face_right','face_3q_left','face_3q_right','face_back']]
        for views in groups:
            for guide in [False,True]:
                with self.subTest(views=views,guide=guide):
                    state=copy.deepcopy(DEFAULT_STATE);state['views']=views
                    state['part_prompts']={'upper_clothing':'purple coat','head_hair':'silver hair'}
                    raw=json.dumps(state)
                    old=compile_reference13_state(raw,use_layout_image=guide)
                    new=compile_reference_v13_state(raw,use_layout_image=guide)
                    import re
                    def content(text):
                        return [re.sub(r'normalized y=[0-9.]+', 'normalized y=baseline', re.sub(r'(guide frame bounds in pixels|rect) \[[^]]+\]', 'region bounds', line)) for line in text.splitlines()
                                if not line.startswith(('<Picture 2> is ', '<Picture 2> provides spatial guidance:', 'Use <Picture 2> for region placement', 'Create a new finished sheet', 'Align feet or footwear bottoms'))]
                    self.assertEqual(content(old['prompt']),content(new['prompt']))
                    self.assertEqual(old['layout']['canvas'][1],new['layout']['canvas'][1])
                    self.assertEqual(old['reference_plan'],new['reference_plan'])

    def test_four_reference_passthrough_and_output_contract(self):
        import torch
        from unittest.mock import patch
        from h3_character_sheet.reference_v13_node import H3CharacterSheetDesignerReferenceV13
        from h3_character_sheet.reference13_node import H3CharacterSheetDesignerReference13
        cls=H3CharacterSheetDesignerReferenceV13
        self.assertEqual(cls.RETURN_TYPES,H3CharacterSheetDesignerReference13.RETURN_TYPES)
        self.assertEqual(cls.RETURN_NAMES,H3CharacterSheetDesignerReference13.RETURN_NAMES)
        images=[torch.full((1,16,16,3),i/4) for i in range(4)]
        state=copy.deepcopy(DEFAULT_STATE);state['views']=['clothing_front','clothing_back']
        with patch('h3_character_sheet.reference_v13_node.runtime_max_resolution',return_value=16384):
            for guide in [False,True]:
                outputs=cls().compile(json.dumps(state),images[0],reference_image_1=images[1],
                    reference_image_2=images[2],reference_image_3=images[3],use_layout_image=guide)
                self.assertEqual(len(outputs),8)
                for actual,expected in zip(outputs[4:],images):self.assertIs(actual,expected)
                if guide:self.assertEqual(tuple(outputs[3].shape),(1,outputs[2],outputs[1],3))
                else:self.assertIsNone(outputs[3])

    def test_outfit_only_scope_preserves_directives_and_mixed_sheets(self):
        for views in [['clothing_front'],['clothing_front','clothing_back']]:
            state=copy.deepcopy(DEFAULT_STATE);state['views']=views
            state['part_prompts']={'upper_clothing':'purple coat','back_clothing':'gold pattern'}
            for guide in [False,True]:
                result=compile_reference_v13_state(json.dumps(state),use_layout_image=guide,
                    reference_presence={'reference_image_1':True})
                text=result['prompt']
                self.assertIn('<Subject 2> (appears in [Shot 1]):',text)
                self.assertNotIn('Retain the same identity',text)
                self.assertIn('purple coat',text)
                self.assertIn('supplements the source outfit',text)
                if 'clothing_back' in views:self.assertIn('gold pattern',text)
        state['views']=['body_front','clothing_front','clothing_back']
        mixed=compile_reference_v13_state(json.dumps(state))['prompt']
        self.assertNotIn('<Subject 2>',mixed)
        self.assertIn('static character sheet',mixed)

    def test_current_version_never_uses_legacy_worn_mode(self):
        for views in [['clothing_front','clothing_back'],list(VIEW_IDS)]:
            for guide in [False,True]:
                state=copy.deepcopy(DEFAULT_STATE);state['views']=views
                state['clothing_mode']='worn'
                worn=compile_reference_v13_state(json.dumps(state),use_layout_image=guide)
                state['clothing_mode']='garment'
                garment=compile_reference_v13_state(json.dumps(state),use_layout_image=guide)
                self.assertEqual(worn['prompt'],garment['prompt'])
                self.assertEqual(worn['state']['clothing_mode'],'garment')
                self.assertNotIn('same character wearing the outfit',worn['prompt'])

    def test_previous_current_and_dedicated_image_nodes_are_registered(self):
        import importlib.util,sys
        from pathlib import Path
        from unittest.mock import patch
        root=Path(__file__).resolve().parents[1]
        spec=importlib.util.spec_from_file_location('h3_registration_check',root/'__init__.py',submodule_search_locations=[str(root)])
        module=importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules,{'h3_registration_check':module,'server':None}):
            spec.loader.exec_module(module)
        self.assertEqual(set(module.NODE_CLASS_MAPPINGS),{'H3CharacterSheetDesignerReference13','H3CharacterSheetDesignerReferenceV13','MiniMaxH3ImageCharacterSheetDesigner'})
        self.assertEqual(set(module.NODE_DISPLAY_NAME_MAPPINGS.values()),{'H3 Character Sheet Designer v1.2.2','H3 Character Sheet Designer v1.3.0','MiniMax H3 Image Character Sheet Designer v1.4.0'})
        self.assertTrue(module.NODE_CLASS_MAPPINGS['H3CharacterSheetDesignerReference13'].DEPRECATED)

    def test_outfit_only_has_shared_object_scope_for_front_and_back(self):
        for views in [['clothing_front'], ['clothing_back'], ['clothing_front','clothing_back']]:
            for guide in [False, True]:
                state=copy.deepcopy(DEFAULT_STATE);state['views']=views
                result=compile_reference_v13_state(json.dumps(state),use_layout_image=guide,
                    reference_presence={'reference_image_1':True})
                text=result['prompt']
                for old in ['baseline identity', 'same identity', 'Never turn the person', 'same person as', 'full-body depiction does not replace']:
                    self.assertNotIn(old,text)
                self.assertIn('<Subject 2> is the complete outfit from <Picture 1>.',text)
                for view in views:
                    self.assertEqual(text.count('Panel '+view+':'),1)
                if len(views)==2:
                    panels=[line.split('. Extract the ',1)[1] for line in text.splitlines() if line.startswith('Panel clothing_')]
                    self.assertEqual(panels[0].replace('front of','back of'),panels[1])

    def test_mixed_sheet_scopes_identity_and_keeps_outfit_panel_text(self):
        state=copy.deepcopy(DEFAULT_STATE);state['views']=list(VIEW_IDS)
        text=compile_reference_v13_state(json.dumps(state))['prompt']
        self.assertIn('same identity across character regions',text)
        self.assertIn('same garment design across clothing regions',text)
        self.assertNotIn('Never turn the person',text)
        for side in ['front','back']:
            self.assertIn('Extract the '+side+' of the complete referenced outfit',text)

    def test_guide_uses_regions_without_copying_placeholder_scale(self):
        for views in [['body_front'],['clothing_front','clothing_back'],list(VIEW_IDS)]:
            state=copy.deepcopy(DEFAULT_STATE);state['views']=views
            off=compile_reference_v13_state(json.dumps(state),use_layout_image=False)
            on=compile_reference_v13_state(json.dumps(state),use_layout_image=True)
            self.assertEqual(off['layout']['canvas'][1],on['layout']['canvas'][1])
            self.assertIn('at natural proportions with a small margin',on['prompt'])
            self.assertIn('Scale each requested view to make full use of its region',on['prompt'])
            self.assertIn(f'Render all {len(views)} selected views',on['prompt'])
            self.assertNotIn('The clothing silhouettes show placement only',on['prompt'])
            self.assertNotIn('Its silhouettes are schematic placeholders',on['prompt'])
            self.assertNotIn('Preserve every black frame',on['prompt'])
            self.assertNotIn('relative size',on['prompt'])
            for view in views:
                self.assertEqual(on['prompt'].count('Panel '+view+':'),1)
            self.assertIsNotNone(on['guide_geometry'])
            self.assertIn('provides spatial guidance',on['prompt'])
            self.assertIn('Create a new finished sheet using the appearance from <Picture 1>',on['prompt'])

    def test_no_human_is_scoped_to_clothing_panels(self):
        for views in [['clothing_front','clothing_back'],list(VIEW_IDS)]:
            state=copy.deepcopy(DEFAULT_STATE);state['views']=views
            for guide in [False,True]:
                text=compile_reference_v13_state(json.dumps(state),use_layout_image=guide)['prompt']
                hits=[line for line in text.splitlines() if 'No human.' in line]
                self.assertEqual(len(hits),2)
                self.assertTrue(all(line.startswith(('Panel clothing_front:', 'Panel clothing_back:')) for line in hits))
                self.assertNotIn('Unworn clothing objects',text)
                self.assertNotIn('Sleeves and openings are empty',text)
                self.assertEqual(text.count('The outfit is flat.'),2)

    def test_compact_guide_expands_panels_and_preserves_canvas(self):
        state=copy.deepcopy(DEFAULT_STATE);state['views']=list(VIEW_IDS)
        old=compile_reference13_state(json.dumps(state),use_layout_image=True)
        new=compile_reference_v13_state(json.dumps(state),use_layout_image=True)
        self.assertEqual(old['layout']['canvas'][1],new['layout']['canvas'][1])
        self.assertEqual(new['guide_geometry']['frame_width'],1)
        for a,b in zip(old['guide_geometry']['panels'],new['guide_geometry']['panels']):
            self.assertGreaterEqual(b['bounds'][2]-b['bounds'][0],a['bounds'][2]-a['bounds'][0])
            self.assertGreaterEqual(b['bounds'][3]-b['bounds'][1],a['bounds'][3]-a['bounds'][1])
        self.assertEqual(min(p['bounds'][0] for p in new['guide_geometry']['panels']),2)
        self.assertEqual(min(p['bounds'][1] for p in new['guide_geometry']['panels']),2)

    def test_compact_guide_partial_grid_and_small_manual_canvas(self):
        for views in [['face_front','face_left','face_right'],list(VIEW_IDS)]:
            for mode,width,height in [('auto',512,2048),('manual',32,32),('manual',512,2048)]:
                state=copy.deepcopy(DEFAULT_STATE);state['views']=views
                state['size'].update(mode=mode,manual_width=width,manual_height=height)
                r=compile_reference_v13_state(json.dumps(state),use_layout_image=True)
                boxes=[p['rect'] for p in r['layout']['panels']]
                for i,(x,y,w,h) in enumerate(boxes):
                    self.assertGreater(w,0);self.assertGreater(h,0)
                    for xx,yy,ww,hh in boxes[i+1:]:
                        self.assertTrue(min(x+w,xx+ww)-max(x,xx)<0.000003 or min(y+h,yy+hh)-max(y,yy)<0.000003)

    def test_auto_body_guide_reaches_requested_height(self):
        for views in [['body_front'],['body_back'],['body_front','body_left','body_back'],list(VIEW_IDS)]:
            state=copy.deepcopy(DEFAULT_STATE);state['views']=views
            result=compile_reference_v13_state(json.dumps(state),use_layout_image=True)
            for p in result['guide_geometry']['panels']:
                if p['id'].startswith('body_'):self.assertGreaterEqual(p['rect'][3],state['size']['body_height']-2)
            for a in result['guide_geometry']['panels']:
                for b in result['guide_geometry']['panels']:
                    if a['id']>=b['id']:continue
                    l,t,r,bb=a['bounds'];x,y,xx,yy=b['bounds']
                    self.assertTrue(min(r,xx)<=max(l,x) or min(bb,yy)<=max(t,y))

    def test_seven_views_put_hands_and_feet_at_far_right(self):
        state=copy.deepcopy(DEFAULT_STATE);state['views']=['face_front','face_left','body_front','body_left','body_back','hands','feet']
        for guide in [False,True]:
            result=compile_reference_v13_state(json.dumps(state),use_layout_image=guide)
            p={p['id']:p['rect'] for p in result['layout']['panels']}
            self.assertAlmostEqual(p['face_front'][0],p['face_left'][0],places=5)
            self.assertLess(p['face_front'][1],p['face_left'][1])
            right=max(p[v][0]+p[v][2] for v in ['body_front','body_left','body_back'])
            self.assertGreater(p['hands'][0],right)
            self.assertEqual(p['hands'][0],p['feet'][0])
            self.assertLess(p['hands'][1],p['feet'][1])

    def test_on_off_share_one_guide_and_only_toggle_reference_delivery(self):
        for views in [['body_front'],['clothing_front','clothing_back'],['face_front','face_left','body_front','body_left','body_back','hands','feet'],list(VIEW_IDS)]:
            state=copy.deepcopy(DEFAULT_STATE);state['views']=views
            off=compile_reference_v13_state(json.dumps(state),use_layout_image=False)
            on=compile_reference_v13_state(json.dumps(state),use_layout_image=True)
            self.assertEqual(off['layout'],on['layout'])
            self.assertEqual(off['guide_geometry'],on['guide_geometry'])
            self.assertFalse(off['guide_enabled']);self.assertTrue(on['guide_enabled'])
            self.assertEqual([r['source'] for r in off['reference_plan']],['character_image'])
            self.assertEqual([r['source'] for r in on['reference_plan']],['character_image','layout_image'])
