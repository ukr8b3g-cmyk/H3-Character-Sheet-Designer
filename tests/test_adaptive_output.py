"""Regressions for requested canvas allocation and independent output semantics."""
import json
from copy import deepcopy
from unittest.mock import patch

import unittest
from functools import partial
import torch

from h3_character_sheet.adaptive_layout import compute_adaptive_layout, auto_view_size, FAMILIES
from h3_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE_JSON, compile_multi_state
from h3_character_sheet.output_plan import compile_output_plan, compile_output_preview
from h3_character_sheet.layout_image import render_layout_image
from h3_character_sheet.reference_v11_node import H3CharacterSheetDesignerReferenceV11


def raw(mode='manual', width=768, height=1152, views=None):
    state=json.loads(DEFAULT_MULTI_STATE_JSON)
    state['size'].update(mode=mode,body_height=224,manual_width=width,manual_height=height)
    if views is not None:
        state['views']=views
    return json.dumps(state)


def test_manual_portrait_five_reflows_to_two_busts_above_three_bodies():
    result=compile_output_preview(raw(),reference_presence={'reference_image_1':False,'reference_image_2':False})
    assert (result['width'],result['height']) == (768,1152)
    panels=result['layout']['panels']
    assert panels[0]['rect'][1] == panels[1]['rect'][1]
    assert all(p['rect'][1] > panels[0]['rect'][1]+panels[0]['rect'][3] for p in panels[2:])
    assert len({p['rect'][1] for p in panels[2:]}) == 1
    assert min(p['rect'][0] for p in panels)<.03
    assert max(p['rect'][0]+p['rect'][2] for p in panels)>.97
    assert result['layout']['feet_y'] is None
    assert 'feet_y with' not in result['prompt']
    assert result['layout'] == result['batch_plan']['items'][0]['layout']


def test_auto_off_retains_legacy_geometry_prompt_and_reference_mapping():
    state=raw(mode='auto')
    expected=compile_multi_state(state,reference_presence={'reference_image_1':False,'reference_image_2':False})
    result=compile_output_preview(state,reference_presence={'reference_image_1':False,'reference_image_2':False})
    assert {key:value for key,value in result.items() if key!='batch_plan'} == expected


def _manual_batch_case(size):
    state=raw(width=size[0],height=size[1],views=[v for g in FAMILIES for v in g])
    saved=json.loads(state)
    output=compile_output_preview(state,batch_out=True,reference_presence={'reference_image_1':False,'reference_image_2':False})
    plan=output['batch_plan']
    assert plan['count']==13
    for item in plan['items']:
        assert (item['width'],item['height'])==size
        assert [p['id'] for p in item['layout']['panels']]==[item['view_id']]
        assert set(item['guide_artwork'])=={item['view_id']}
        assert item['filename_suffix'].endswith('_'+item['view_id'])
    assert json.loads(state)==saved
    off=compile_output_preview(state,reference_presence={'reference_image_1':False,'reference_image_2':False})
    assert (off['width'],off['height'])==size


def test_auto_profiles_all_view_types_and_scaling():
    groups=FAMILIES
    expected=((768,768),(768,1344),(768,1344),(1024,768))
    for group, size in zip(groups,expected):
        for view in group:
            assert auto_view_size(view,1120,'h3')==size
            assert auto_view_size(view,2240,'h3')==tuple(n*2 for n in size)
    plan=compile_output_plan(raw(mode='auto'),batch_out=True,reference_presence={'reference_image_1':False,'reference_image_2':False})
    assert plan['items'][0]['width']==160


def test_actual_guides_use_exact_plan_and_none_slots_without_gpu():
    character=torch.zeros((1,32,32,3))
    with patch('h3_character_sheet.reference_v11_node.runtime_max_resolution',return_value=16384):
        with patch('h3_character_sheet.reference_v11_node.render_layout_image',side_effect=AssertionError('OFF draws images')):
            result=H3CharacterSheetDesignerReferenceV11().compile(raw(width=160,height=256),character,batch_out=True)
            assert result[3]==[None]*5
        result=H3CharacterSheetDesignerReferenceV11().compile(raw(width=160,height=256),character,batch_out=True,use_layout_image=True)
    plan=compile_output_plan(raw(width=160,height=256),batch_out=True,use_layout_image=True,reference_presence={'reference_image_1':False,'reference_image_2':False})
    for index,item in enumerate(plan['items']):
        assert result[1][index]==item['width'] and result[2][index]==item['height']
        assert tuple(result[3][index].shape)==(1,256,160,3)
        expected=render_layout_image(item['layout'],multi_reference=True,clothing_mode='worn')
        import numpy as np
        assert torch.equal(result[3][index],torch.from_numpy(np.asarray(expected,dtype=np.float32)/255).unsqueeze(0))
    assert not torch.cuda.is_initialized()


def test_extreme_small_canvas_and_only_clothing_do_not_add_head_or_unselected_panels():
    views=['clothing_front','clothing_back']
    layout=compute_adaptive_layout(views,32,32)
    assert [p['id'] for p in layout['panels']]==views
    guide=render_layout_image(layout,multi_reference=True,clothing_mode='garment')
    colors=set(guide.getdata())
    assert colors.issubset({(0,0,0),(255,255,255)})


def load_tests(loader, tests, pattern):
    for name, function in sorted(globals().items()):
        if name.startswith('test_') and callable(function):
            tests.addTest(unittest.FunctionTestCase(function))
    for size in ((768, 1152), (1152, 768), (1024, 1024)):
        case = partial(_manual_batch_case, size)
        case.__name__ = f'manual_batch_{size[0]}x{size[1]}'
        tests.addTest(unittest.FunctionTestCase(case,
                       description=f'manual batch canvas {size}'))
    return tests
