"""Single-sheet Reference13 adapter with validated, unchanged IMAGE passthrough."""
import numpy as np
import torch

from .compiler import StateValidationError
from .guide_13 import render_reference13_guide
from .node import runtime_max_resolution
from .on_compiler_13 import compile_reference13_state
from .reference_compiler import STYLE_PROMPTS
from .state_13 import DEFAULT_STATE_JSON
from .multi_reference_node import validate_reference_image


class H3CharacterSheetDesignerReference13:
    CATEGORY = 'H3/Character Sheet'
    DESCRIPTION = ('13-view H3 sheet with one required character image and three optional same-character references. '
                   'Wire character_image, layout_image, reference_image_1, reference_image_2 and reference_image_3 '
                   'to H3 ref_images.ref_image_0, 1, 2, 3 and 4. Picture numbers skip None images. '
                   'OFF returns no layout image. One sheet per execution.')
    RETURN_TYPES = ('STRING', 'INT', 'INT', 'IMAGE', 'IMAGE', 'IMAGE', 'IMAGE', 'IMAGE')
    RETURN_NAMES = ('prompt', 'width', 'height', 'layout_image', 'character_image',
                    'reference_image_1', 'reference_image_2', 'reference_image_3')
    FUNCTION = 'compile'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {'state_json': ('STRING', {'default': DEFAULT_STATE_JSON,
                'multiline': True, 'dynamicPrompts': False}), 'character_image': ('IMAGE',)},
                'optional': {'reference_image_1': ('IMAGE',), 'reference_image_2': ('IMAGE',),
                             'reference_image_3': ('IMAGE',),
                             'use_layout_image': ('BOOLEAN', {'default': False}),
                             'style': (list(STYLE_PROMPTS), {'default': 'none'})}}

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style='none'):
        try:
            compile_reference13_state(state_json, use_layout_image=use_layout_image,
                                      style=style, max_resolution=runtime_max_resolution())
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, character_image, reference_image_1=None,
                reference_image_2=None, use_layout_image=False, style='none', reference_image_3=None):
        validate_reference_image(character_image, 'character_image', required=True)
        validate_reference_image(reference_image_1, 'reference_image_1')
        validate_reference_image(reference_image_2, 'reference_image_2')
        validate_reference_image(reference_image_3, 'reference_image_3')
        result = compile_reference13_state(state_json, use_layout_image=use_layout_image,
                                          style=style, max_resolution=runtime_max_resolution(),
                                          reference_presence={'reference_image_1': reference_image_1 is not None,
                                                              'reference_image_2': reference_image_2 is not None,
                                                              'reference_image_3': reference_image_3 is not None})
        image = None
        if use_layout_image:
            guide = render_reference13_guide(result['guide_geometry'], result['semantic_layout'])
            image = torch.from_numpy(np.asarray(guide, dtype=np.float32)/255.0).unsqueeze(0)
        return (result['prompt'], result['width'], result['height'], image,
                character_image, reference_image_1, reference_image_2, reference_image_3)
