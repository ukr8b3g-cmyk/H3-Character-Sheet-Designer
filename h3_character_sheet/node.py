"""ComfyUI adapter. Compilation does not depend on the preview endpoint."""

import importlib

from .compiler import DEFAULT_STATE_JSON, StateValidationError, compile_state


def runtime_max_resolution() -> int:
    """Read Core's current limit at invocation time rather than caching it."""
    maximum = importlib.import_module("nodes").MAX_RESOLUTION
    if type(maximum) is not int or maximum < 32:
        raise RuntimeError("ComfyUI nodes.MAX_RESOLUTION must be an integer of at least 32.")
    return maximum


class H3CharacterSheetDesigner:
    CATEGORY = "H3/Character Sheet"
    DESCRIPTION = (
        "Design a static multi-view character sheet. Connect prompt, width, and height "
        "to the native MiniMaxH3ReferenceToVideo node. Reference images are connected "
        "separately. Layout is semantic guidance; high-resolution generation is experimental."
    )
    RETURN_TYPES = ("STRING", "INT", "INT")
    RETURN_NAMES = ("prompt", "width", "height")
    FUNCTION = "compile"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state_json": (
                    "STRING",
                    {"default": DEFAULT_STATE_JSON, "multiline": True, "dynamicPrompts": False},
                )
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, state_json):
        try:
            compile_state(state_json, max_resolution=runtime_max_resolution())
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json):
        result = compile_state(state_json, max_resolution=runtime_max_resolution())
        return result["prompt"], result["width"], result["height"]
