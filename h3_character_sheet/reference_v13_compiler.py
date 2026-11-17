"""P-H3 sheet compiler with the native four-reference contract."""
from .head_six import apply_head_six
from .on_compiler_13 import compile_reference13_state
from .state_13 import effective_views
from .view_catalog_13 import PORTRAIT_IDS


def compile_reference_v13_state(state_json, *, style='none', **kwargs):
    result = compile_reference13_state(state_json, optimize_outfit=True, style=style, **kwargs)
    views = effective_views(result['state'])
    if set(views) == set(PORTRAIT_IDS):
        state = {**result['state'], 'views': views}
        return apply_head_six(result, state, result['default_view_prompts'], style=style)
    return result
