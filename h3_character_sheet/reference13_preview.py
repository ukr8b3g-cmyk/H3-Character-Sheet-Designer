"""Read-only dedicated preview; execution never calls this HTTP adapter."""
from .compiler import StateValidationError, decode_json
from .on_compiler_13 import compile_reference13_state
from .preview import HTTP_MAX_BYTES, _preview

PREVIEW_PATH = '/h3_character_sheet_designer/reference13/preview'


def compile_preview_request(body, *, max_resolution):
    if len(body) > HTTP_MAX_BYTES:
        raise StateValidationError('Preview request is too large.', 'request_too_large')
    try:
        text = body.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise StateValidationError('Preview must be valid UTF-8.', 'invalid_utf8') from exc
    envelope = decode_json(text, byte_limit=HTTP_MAX_BYTES)
    if type(envelope) is not dict or 'state_json' not in envelope or set(envelope)-{'state_json', 'use_layout_image', 'style', 'reference_presence'}:
        raise StateValidationError('Invalid Reference13 preview request.', 'invalid_request')
    return compile_reference13_state(**envelope, max_resolution=max_resolution)


async def preview(request):
    return await _preview(request, compile_preview_request)


def register_routes():
    try:
        from server import PromptServer
    except ModuleNotFoundError as exc:
        if exc.name == 'server':
            return False
        raise
    instance = getattr(PromptServer, 'instance', None)
    if instance is None:
        return False
    if not getattr(instance, '_h3_reference13_route_registered', False):
        instance.routes.post(PREVIEW_PATH)(preview)
        instance._h3_reference13_route_registered = True
    return True
