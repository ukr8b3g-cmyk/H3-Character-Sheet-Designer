"""One authoritative CPU plan for prompts, canvases, guides and list outputs."""
import json

from .adaptive_layout import auto_view_size, compute_adaptive_layout
from .compiler import StateValidationError
from .multi_reference_compiler import (
    DEFAULT_MAX_RESOLUTION, compile_multi_state, finish_layout, parse_multi_state,
)


def compile_output_plan(state_json, *, max_resolution=DEFAULT_MAX_RESOLUTION,
                        use_layout_image=False, style='none', reference_presence=None,
                        batch_out=False):
    if type(batch_out) is not bool:
        raise StateValidationError('batch_out must be a boolean.', 'invalid_type')
    state = parse_multi_state(state_json, max_resolution=max_resolution)
    options = dict(max_resolution=max_resolution, use_layout_image=use_layout_image,
                   style=style, reference_presence=reference_presence)
    items = []
    for index, view in enumerate(state['views'] if batch_out else ['sheet'], start=1):
        selected = {**state, 'views': [view]} if batch_out else state
        layout = None
        if batch_out or state['size']['mode'] == 'manual':
            width, height = (auto_view_size(view, state['size']['body_height'], 'h3')
                             if batch_out and state['size']['mode'] == 'auto'
                             else (state['size']['manual_width'], state['size']['manual_height']))
            if max(width, height) > max_resolution:
                raise StateValidationError(f'Output {width}x{height} exceeds the runtime maximum {max_resolution}.', 'size_limit')
            layout = finish_layout(selected, compute_adaptive_layout(selected['views'], width, height))
        raw = json.dumps(selected, ensure_ascii=False) if batch_out else state_json
        result = compile_multi_state(raw, layout=layout, **options)
        items.append({**result, 'index': index, 'view_id': view,
                      'filename_suffix': f'_{index:02d}_{view}' if batch_out else ''})
    return {'enabled': batch_out, 'count': len(items), 'items': items}


def compile_output_preview(state_json, **options):
    plan = compile_output_plan(state_json, **options)
    if not plan['enabled']:
        summary = plan['items'][0]
    else:
        # The root remains a selection overview for canonical state validation;
        # the UI and execution use each output's actual dimensions and geometry.
        summary = compile_output_plan(state_json, **{**options, 'batch_out': False})['items'][0]
    return {**{key: value for key, value in summary.items() if key not in ('index', 'view_id', 'filename_suffix')}, 'batch_plan': plan}
