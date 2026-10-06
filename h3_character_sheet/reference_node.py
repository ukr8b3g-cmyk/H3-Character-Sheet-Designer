"""Native IMAGE output for H3's second reference slot."""

import numpy as np
import torch

from .compiler import StateValidationError
from .layout_image import render_layout_image
from .node import runtime_max_resolution
from .reference_compiler import DEFAULT_REFERENCE_STATE_JSON, STYLE_PROMPTS, compile_reference_state


class H3CharacterSheetDesignerReference:
    CATEGORY = "H3/Character Sheet"
    DESCRIPTION = (
        "Connect the character image FIRST (ref_image_0 / Picture 1), and layout_image "
        "SECOND (ref_image_1 / Picture 2) to MiniMaxH3ReferenceToVideo. "
        "OFF is recommended for preserving character proportions. It uses an optimized "
        "original Designer prompt and outputs no layout reference; "
        "H3 skips Picture 2 automatically. ON keeps the framed layout reference and may "
        "influence body proportions. "
        "It is not a first-frame image."
    )
    RETURN_TYPES = ("STRING", "INT", "INT", "IMAGE")
    RETURN_NAMES = ("prompt", "width", "height", "layout_image")
    FUNCTION = "compile"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {"state_json": ("STRING", {"default": DEFAULT_REFERENCE_STATE_JSON, "multiline": True, "dynamicPrompts": False})},
            "optional": {
                "use_layout_image": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "OFF (recommended): character reference with optimized original Designer prompt; layout_image=None (H3 skips it). ON: framed layout reference, which may influence body proportions. Keep the character on ref_image_0 and layout_image on ref_image_1.",
                }),
                "style": (list(STYLE_PROMPTS), {"default": "none"}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style="none"):
        try:
            compile_reference_state(state_json, use_layout_image=use_layout_image, style=style, max_resolution=runtime_max_resolution())
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, use_layout_image=False, style="none"):
        result = compile_reference_state(state_json, use_layout_image=use_layout_image, style=style, max_resolution=runtime_max_resolution())
        if not use_layout_image:
            return result["prompt"], result["width"], result["height"], None
        image = render_layout_image(result["layout"])
        tensor = torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0).unsqueeze(0)
        return result["prompt"], result["width"], result["height"], tensor
