import copy, json, unittest
from h3_character_sheet.state_13 import DEFAULT_STATE
from h3_character_sheet.view_catalog_13 import PRESETS, VIEW_IDS
from h3_character_sheet.minimax_image_compiler import compile_minimax_image_state
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

    def test_guided_full_sheet_only_sends_natural_positions_to_the_model(self):
        state = {
            **DEFAULT_STATE,
            'views': list(VIEW_IDS),
            'part_prompts': {'head_hair': 'Silver hair.'},
            'footwear_state': 'shod',
            'view_prompts': {'face_3q_left': 'Keep the original expression.'},
        }
        for size in (state['size'], {**state['size'], 'mode': 'manual',
                                    'manual_width': 3968, 'manual_height': 1024}):
            with self.subTest(size=size):
                raw = json.dumps({**state, 'size': size})
                result = compile_reference_v13_state(raw, use_layout_image=True)
                legacy_format = compile_reference13_state(raw, optimize_outfit=True, use_layout_image=True)
                for key in ('semantic_layout', 'view_prompts', 'state_json'):
                    self.assertEqual(result[key], legacy_format[key])
                geometry = result['guide_geometry']
                self.assertEqual(geometry['panel_fill'], '#f7f7f7')
                for panel, original in zip(geometry['panels'], legacy_format['guide_geometry']['panels']):
                    self.assertEqual(panel['bounds'], original['bounds'])
                    if panel['id'] in ('face_front', 'face_left'):
                        self.assertGreater(panel['rect'][1], original['rect'][1])
                        self.assertLess(panel['rect'][3], original['rect'][3])
                    elif panel['id'] == 'face_back':
                        self.assertTrue(panel['blank'])
                    else:
                        self.assertEqual(panel, original)
                prompt = result['prompt']
                for view in VIEW_IDS:
                    if '_' in view:
                        self.assertNotIn(view, prompt)
                self.assertNotRegex(prompt, r'\[\s*\d+\s*,')
                self.assertNotIn('[Shot 1]', prompt)
                panels = [line for line in prompt.splitlines() if line.startswith('Place the ')]
                positions = [line.split('. ', 1)[0] for line in panels]
                self.assertEqual(len(positions), 13)
                self.assertEqual(len(set(positions)), 13)
                self.assertIn('Place the front portrait in the upper-left area of the portrait block at the far left', positions)
                self.assertIn('Place the screen-right-facing full-body profile in the center area of the full-body block next to the portraits', positions)
                self.assertIn('Place the feet and footwear detail in the lower area of the detail column at the far right', positions)
                self.assertIn('Keep the original expression.', prompt)
                self.assertIn('Silver hair.', prompt)
                footwear = next(line for line in prompt.splitlines() if line.startswith('Choice footwear_state'))
                self.assertIn('feet and footwear detail)', footwear)
                self.assertIn('keep any hat or head ornament worn by the character in <Picture 1>', prompt)
                self.assertIn('Preserve an uncovered head when the reference has one.', prompt)
                self.assertIn('Follow applicable explicit head directives and dedicated head references', prompt)
                for panel in panels:
                    person = 'portrait block' in panel or 'full-body block' in panel
                    self.assertEqual('complete silhouette of any headwear' in panel, person)
                    self.assertEqual('seen on the full-body rear figure' in panel,
                                     panel.startswith('Place the rear portrait '))
                layout_off = compile_reference_v13_state(raw)['prompt']
                self.assertIn('Panel face_front:', layout_off)
                self.assertNotIn('complete silhouette of any headwear', layout_off)
        unguided_subset = json.dumps({**DEFAULT_STATE, 'views': list(PRESETS['five'])})
        self.assertIn('guide frame bounds in pixels',
                      compile_reference_v13_state(unguided_subset, use_layout_image=True)['prompt'])
        edited_rear = json.dumps({**state, 'view_prompts': {'face_back': 'Draw a bare head.'}})
        prompt = compile_reference_v13_state(edited_rear, use_layout_image=True)['prompt']
        self.assertIn('Draw a bare head.', prompt)
        self.assertNotIn('seen on the full-body rear figure', prompt)

    def test_successful_non_clothing_prompts_unchanged(self):
        groups=[['face_front','face_left','body_front','body_left','body_back'],
                ['body_front'],['body_front','body_left','body_back']]
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
                    self.assertEqual(
                        [(ref['source'], ref['role'], ref['picture_number'], ref['tag']) for ref in old['reference_plan']],
                        [(ref['source'], ref['role'], ref['picture_number'], ref['tag']) for ref in new['reference_plan']],
                    )

    def test_head_six_matches_minimax_layout_and_prompt_at_the_same_size(self):
        state = {
            **DEFAULT_STATE,
            'views': list(PRESETS['head']),
            'size': {**DEFAULT_STATE['size'], 'mode': 'manual', 'manual_width': 1888, 'manual_height': 1792},
            'view_prompts': {'face_left': '', 'face_back': 'Show a braid.'},
            'part_prompts': {'head_hair': 'Silver hair.'},
            'reference_roles': {'reference_image_1': 'same_character',
                                'reference_image_2': 'face',
                                'reference_image_3': 'same_character'},
        }
        for guided in (False, True):
            with self.subTest(guided=guided):
                kwargs = {'use_layout_image': guided, 'reference_presence': {'reference_image_2': True}}
                ph3 = compile_reference_v13_state(json.dumps(state), **kwargs)
                image = compile_minimax_image_state(json.dumps(state), **kwargs)
                for key in ('semantic_layout', 'guide_geometry', 'prompt', 'view_prompts', 'state_json'):
                    self.assertEqual(ph3[key], image[key])
                self.assertEqual(ph3['guide_geometry']['frame_width'], 0)
                lower_left = next(line for line in ph3['prompt'].splitlines() if line.startswith('The lower-left panel.'))
                self.assertIn('Silver hair.', lower_left)
                self.assertIn('The lower-right panel. Show a braid.', ph3['prompt'])
                self.assertEqual(ph3['reference_plan'][-1]['core_input'], 'images.image_4')
                self.assertEqual(image['reference_plan'][-1]['core_input'], 'images.image_3')

    def test_preview_reference_input_names_match_ph3_workflow_wiring(self):
        from itertools import product
        from pathlib import Path
        from h3_character_sheet.reference_v13_preview import compile_preview_request

        path = Path(__file__).resolve().parents[1] / 'workflows' / 'H3 Character Sheet Designer - P-H3 Subgraph.json'
        workflow = json.loads(path.read_text(encoding='utf-8-sig'))
        designer = next(node for node in workflow['nodes'] if node['type'] == 'H3CharacterSheetDesignerReferenceV13')
        output_links = {link[0]: link for link in workflow['links']}
        nodes = {node['id']: node for node in workflow['nodes']}
        subgraphs = {graph['id']: graph for graph in workflow['definitions']['subgraphs']}
        sources = ('character_image', 'layout_image', 'reference_image_1', 'reference_image_2', 'reference_image_3')
        wired_inputs = {}
        for output in designer['outputs']:
            if output['name'] not in sources:
                continue
            outer_link, = output['links']
            wrapper = nodes[output_links[outer_link][3]]
            graph = subgraphs[wrapper['type']]
            input_name = wrapper['inputs'][output_links[outer_link][4]]['name']
            graph_input = next(port for port in graph['inputs'] if port['name'] == input_name)
            conditioning = next(node for node in graph['nodes'] if node['type'] == 'PH3ImageConditioning')
            wire, = (link for link in graph['links'] if link['id'] in graph_input['linkIds']
                     and link['target_id'] == conditioning['id'])
            wired_inputs[output['name']] = conditioning['inputs'][wire['target_slot']]['name']

        self.assertEqual(set(wired_inputs), set(sources))
        for preset in ('five', 'head'):
            raw = json.dumps({**DEFAULT_STATE, 'views': list(PRESETS[preset])})
            for guide, *extras in product((False, True), repeat=4):
                with self.subTest(preset=preset, guide=guide, extras=extras):
                    body = json.dumps({'state_json': raw, 'use_layout_image': guide,
                                       'reference_presence': dict(zip(sources[2:], extras))}).encode()
                    plan = compile_preview_request(body, max_resolution=16384)['reference_plan']
                    selected = [source for source, present in zip(sources, (True, guide, *extras)) if present]
                    self.assertEqual(
                        [(ref['source'], ref['core_input'], ref['tag']) for ref in plan],
                        [(source, wired_inputs[source], f'<Picture {number}>')
                         for number, source in enumerate(selected, start=1)],
                    )

    def test_selected_style_replaces_reference_rendering_in_both_nodes(self):
        from h3_character_sheet.reference_compiler import STYLE_PROMPTS

        view_sets = (PRESETS['head'], PRESETS['five'], ('hands', 'feet'), ('face_front',))
        for compiler in (compile_minimax_image_state, compile_reference_v13_state):
            for views in view_sets:
                for guide in (False, True):
                    for clothing in ('reference', 'none'):
                        raw = json.dumps({**DEFAULT_STATE, 'views': list(views), 'clothing_type': clothing})
                        baseline = compiler(raw, use_layout_image=guide)
                        self.assertIn('rendering style', baseline['prompt'])
                        for style, instruction in STYLE_PROMPTS.items():
                            if not instruction:
                                continue
                            with self.subTest(compiler=compiler.__name__, views=views, guide=guide, clothing=clothing, style=style):
                                result = compiler(raw, use_layout_image=guide, style=style)
                                prompt = result['prompt']
                                self.assertEqual(prompt.count(instruction), 1)
                                for conflict in ('and illustration style', 'and rendering style',
                                                 'rendering style of <Picture 1>', 'rendering style as <Picture 1>'):
                                    self.assertNotIn(conflict, prompt)
                                self.assertEqual(result['guide_geometry'], baseline['guide_geometry'])
                                self.assertEqual(result['reference_plan'], baseline['reference_plan'])

    def test_unused_reference_keeps_its_number_and_image_in_preview_and_node_output(self):
        import torch
        from unittest.mock import patch
        from h3_character_sheet import minimax_image_node, reference_v13_node
        from h3_character_sheet.minimax_image_preview import compile_preview_request as image_preview
        from h3_character_sheet.reference_v13_preview import compile_preview_request as ph3_preview

        modules = ((minimax_image_node, minimax_image_node.MiniMaxH3ImageCharacterSheetDesigner, image_preview),
                   (reference_v13_node, reference_v13_node.H3CharacterSheetDesignerReferenceV13, ph3_preview))
        character, face, shoes = (torch.full((1, 16, 16, 3), value) for value in (0.0, 0.5, 1.0))
        roles = {'reference_image_1': 'face', 'reference_image_2': 'same_character',
                 'reference_image_3': 'footwear'}
        presence = {'reference_image_1': True, 'reference_image_3': True}
        for module, node_type, preview in modules:
            with patch.object(module, 'runtime_max_resolution', return_value=16384):
                for views, unused_role in ((PRESETS['head'], 'footwear'), (('face_front',), 'footwear'), (('feet',), 'face')):
                    state = {**DEFAULT_STATE, 'views': list(views), 'reference_roles': roles,
                             'size': {**DEFAULT_STATE['size'], 'mode': 'manual', 'manual_width': 512, 'manual_height': 512}}
                    raw = json.dumps(state)
                    for guide in (False, True):
                        with self.subTest(node=node_type.__name__, views=views, guide=guide):
                            request = {'state_json': raw, 'use_layout_image': guide, 'style': 'watercolor',
                                       'reference_presence': presence}
                            data = preview(json.dumps(request).encode(), max_resolution=16384)
                            output = node_type().compile(raw, character, reference_image_1=face,
                                                         reference_image_3=shoes, use_layout_image=guide, style='watercolor')
                            self.assertEqual(output[0], data['prompt'])
                            self.assertEqual(output[1:3], (data['width'], data['height']))
                            self.assertEqual(output[3] is not None, guide)
                            self.assertIs(output[4], character)
                            self.assertIs(output[5], face)
                            self.assertIsNone(output[6])
                            self.assertIs(output[7], shoes)
                            unused_number = (3 if guide else 2) + (unused_role == 'footwear')
                            self.assertEqual(output[0].count(
                                f'<Picture {unused_number}> has role {unused_role}, but no eligible part is visible '
                                'in the selected views. Ignore it for appearance changes.'), 1)
                            self.assertEqual(output[0].count('Ignore it for appearance changes.'), 1)
                            self.assertEqual(data['reference_plan'][-1]['tag'], f'<Picture {4 if guide else 3}>')

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
        self.assertEqual(set(module.NODE_DISPLAY_NAME_MAPPINGS.values()),{'H3 Character Sheet Designer v1.2.2','H3 Character Sheet Designer v1.5.2','MiniMax H3 Image Character Sheet Designer v1.5.2'})
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
            if views == list(VIEW_IDS):
                self.assertEqual(sum(line.startswith('Place the ') for line in on['prompt'].splitlines()), len(views))
            else:
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
                prefixes = (('Place the clothing front ', 'Place the clothing back ')
                            if guide and views == list(VIEW_IDS) else
                            ('Panel clothing_front:', 'Panel clothing_back:'))
                self.assertEqual([line.startswith(prefix) for line, prefix in zip(hits, prefixes)], [True, True])
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
