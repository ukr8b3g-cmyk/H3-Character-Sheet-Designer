"""ComfyUI adapter with role-aware IMAGE passthrough; no model selection."""

import numpy as np
import torch

from .compiler import StateValidationError
from .layout_image import render_layout_image
from .multi_reference_compiler import (
    DEFAULT_MULTI_STATE_JSON, compile_multi_prompt, compile_multi_state,
    parse_multi_state,
)
from .node import runtime_max_resolution
from .reference_compiler import STYLE_PROMPTS
from .reference_plan import build_reference_plan


def validate_reference_image(image, name, *, required=False):
    if image is None:
        if required:
            raise StateValidationError(f"Connect {name}.", "missing_character")
        return
    if not isinstance(image, torch.Tensor) or image.ndim != 4:
        raise StateValidationError(f"{name} must be an IMAGE tensor [1,H,W,3].", "invalid_image")
    if image.shape[0] != 1:
        raise StateValidationError(f"{name} accepts one image; connect separate LoadImage nodes instead of ImageBatch.", "image_batch")
    if image.shape[-1] != 3 or min(image.shape[1:3]) < 1 or not image.is_floating_point():
        raise StateValidationError(f"{name} must be a nonempty floating-point RGB IMAGE.", "invalid_image")


class H3CharacterSheetDesignerMultiReference:
    CATEGORY = "H3/Character Sheet"
    DESCRIPTION = (
        "13 views with a required character image and two optional role references. "
        "Wire character_image, layout_image, reference_image_1 and reference_image_2 "
        "to H3 ref_images.ref_image_0, 1, 2 and 3, respectively. "
        "Picture numbers skip None images. Model selection belongs to the user."
    )
    RETURN_TYPES = ("STRING", "INT", "INT", "IMAGE", "IMAGE", "IMAGE", "IMAGE")
    RETURN_NAMES = ("prompt", "width", "height", "layout_image", "character_image",
                    "reference_image_1", "reference_image_2")
    FUNCTION = "compile"

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "state_json": ("STRING", {"default": DEFAULT_MULTI_STATE_JSON,
                                         "multiline": True, "dynamicPrompts": False}),
                "character_image": ("IMAGE",),
            },
            "optional": {
                "reference_image_1": ("IMAGE",),
                "reference_image_2": ("IMAGE",),
                "use_layout_image": ("BOOLEAN", {"default": False}),
                "style": (list(STYLE_PROMPTS), {"default": "none"}),
            },
        }

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style="none"):
        try:
            compile_multi_state(state_json, use_layout_image=use_layout_image,
                                style=style, max_resolution=runtime_max_resolution())
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, character_image, reference_image_1=None,
                reference_image_2=None, use_layout_image=False, style="none"):
        # Validate widget values even when callers bypass Core's queue validation.
        validated = compile_multi_state(state_json, use_layout_image=use_layout_image,
                                        style=style, max_resolution=runtime_max_resolution())
        state = parse_multi_state(validated["state_json"], max_resolution=runtime_max_resolution())
        validate_reference_image(character_image, "character_image", required=True)
        validate_reference_image(reference_image_1, "reference_image_1")
        validate_reference_image(reference_image_2, "reference_image_2")
        layout_image = None
        if use_layout_image:
            image = render_layout_image(validated["layout"], multi_reference=True,
                                        clothing_mode=state['clothing_mode'])
            layout_image = torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0).unsqueeze(0)
        plan = build_reference_plan(character_image, layout_image, reference_image_1,
                                    reference_image_2, state["reference_roles"])
        prompt = compile_multi_prompt(state, validated["layout"], plan,
                                      use_layout_image=use_layout_image, style=style)
        character, layout, extra_1, extra_2 = plan.images
        return prompt, validated["width"], validated["height"], layout, character, extra_1, extra_2
