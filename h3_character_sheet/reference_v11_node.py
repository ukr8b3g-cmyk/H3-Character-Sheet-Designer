"""Reference V1.1 adapter: sheet or independent views, with true guide bypass."""
import numpy as np
import torch

from .compiler import StateValidationError
from .reference_compiler import STYLE_PROMPTS
from .multi_reference_node import validate_reference_image
from .multi_reference_compiler import DEFAULT_MULTI_STATE_JSON, parse_multi_state
from .output_plan import compile_output_plan
from .layout_image import render_layout_image
from .node import runtime_max_resolution


class H3CharacterSheetDesignerReferenceV11:
    CATEGORY = 'H3/Character Sheet'
    DESCRIPTION = (
        '13-view character sheet with two optional part references. Fan out the character '
        'to character_image and Core ref_images.ref_image_0; extra 1/2 to both Designer and Core '
        'ref_images.ref_image_2/3. layout_image connects to Core ref_images.ref_image_1. OFF returns None. '
        'Connect prompt and width/height to MiniMaxH3ReferenceToVideo. Batch Out generates each selected view '
        'separately; Manual width/height applies to every image. Preview shows each '
        'output at its actual aspect ratio. Standard list execution saves after sampling all views. '
        'Layout guidance does not guarantee geometry.'
    )
    RETURN_TYPES = ('STRING', 'INT', 'INT', 'IMAGE', 'STRING')
    RETURN_NAMES = ('prompt', 'width', 'height', 'layout_image', 'filename_suffix')
    OUTPUT_IS_LIST = (True, True, True, True, True)
    FUNCTION = 'compile'

    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'state_json': ('STRING', {'default': DEFAULT_MULTI_STATE_JSON, 'multiline': True, 'dynamicPrompts': False}),
            'character_image': ('IMAGE',),
        }, 'optional': {
            'reference_image_1': ('IMAGE',), 'reference_image_2': ('IMAGE',),
            'use_layout_image': ('BOOLEAN', {'default': False, 'tooltip': 'ON: layout to Core ref_image_1. Always fan out character to Core ref_image_0 and extra 1/2 to ref_image_2/3.'}),
            'style': (list(STYLE_PROMPTS), {'default': 'none'}),
            'batch_out': ('BOOLEAN', {'default': False, 'label_on': 'Batch Out ON', 'label_off': 'Batch Out OFF',
                                     'tooltip': 'ON: generate each selected view separately. Manual width/height applies to every image. / ON: 選択ビューを1枚ずつ生成。Manual寸法は各画像に適用。'}),
        }}

    @classmethod
    def VALIDATE_INPUTS(cls, state_json, use_layout_image=False, style='none', batch_out=False):
        # Core validates required links; actual IMAGE presence is resolved at
        # execution. Never parse connection tuples as image content.
        try:
            compile_output_plan(state_json, max_resolution=runtime_max_resolution(),
                                use_layout_image=use_layout_image, style=style, batch_out=batch_out)
        except StateValidationError as exc:
            return str(exc)
        return True

    def compile(self, state_json, character_image, reference_image_1=None,
                reference_image_2=None, use_layout_image=False, style='none', batch_out=False):
        validate_reference_image(character_image, 'character_image', required=True)
        validate_reference_image(reference_image_1, 'reference_image_1')
        validate_reference_image(reference_image_2, 'reference_image_2')
        max_resolution = runtime_max_resolution()
        plan = compile_output_plan(
            state_json, max_resolution=max_resolution, use_layout_image=use_layout_image,
            style=style, batch_out=batch_out, reference_presence={'reference_image_1': reference_image_1 is not None,
            'reference_image_2': reference_image_2 is not None})
        images = [None] * plan['count']
        if use_layout_image:
            state = parse_multi_state(state_json, max_resolution=max_resolution)
            for index, item in enumerate(plan['items']):
                layout = item['layout']
                try:
                    image = render_layout_image(layout, multi_reference=True, clothing_mode=state['clothing_mode'])
                except FileNotFoundError as exc:
                    raise StateValidationError('A bundled Multi Reference guide PNG is missing; restore the local node assets.', 'missing_guide_asset') from exc
                images[index] = torch.from_numpy(np.asarray(image, dtype=np.float32) / 255.0).unsqueeze(0)
        return ([item['prompt'] for item in plan['items']],
                [item['width'] for item in plan['items']],
                [item['height'] for item in plan['items']], images,
                [item['filename_suffix'] for item in plan['items']])
