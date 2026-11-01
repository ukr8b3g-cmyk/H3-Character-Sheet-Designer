"""V1.3: object-only outfit panels, preserving the native four-reference contract."""
from .on_compiler_13 import compile_reference13_state

def compile_reference_v13_state(state_json, **kwargs):
    return compile_reference13_state(state_json, optimize_outfit=True, **kwargs)
