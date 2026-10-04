"""Small same-server preview adapter; no I/O except the HTTP request/response."""

from __future__ import annotations

from .compiler import StateValidationError, compile_state, decode_json
from .node import runtime_max_resolution

PREVIEW_PATH = "/h3_character_sheet_designer/preview"
HTTP_MAX_BYTES = 32 * 1024


def compile_preview_request(body: bytes, *, max_resolution: int) -> dict:
    """Bound and validate the transport envelope before invoking the compiler."""
    if len(body) > HTTP_MAX_BYTES:
        raise StateValidationError("Preview request exceeds the 32768-byte limit.", "request_too_large")
    try:
        text = body.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise StateValidationError("Preview request must be valid UTF-8.", "invalid_utf8") from exc
    envelope = decode_json(text, byte_limit=HTTP_MAX_BYTES)
    if type(envelope) is not dict or set(envelope) != {"state_json"}:
        raise StateValidationError("Preview request must be an object containing only state_json.", "invalid_request")
    return compile_state(envelope["state_json"], max_resolution=max_resolution)


async def preview(request):
    # aiohttp is supplied by ComfyUI; keep it out of the pure compiler's imports.
    from aiohttp import web

    if request.content_length is not None and request.content_length > HTTP_MAX_BYTES:
        return web.json_response({"error": {"code": "request_too_large", "message": "Preview request exceeds the 32768-byte limit."}}, status=413)
    if request.content_type != "application/json":
        return web.json_response({"error": {"code": "invalid_content_type", "message": "Content-Type must be application/json."}}, status=415)
    body = bytearray()
    # Do not call request.json()/read(): chunked requests need a bounded read too.
    async for chunk in request.content.iter_chunked(4096):
        body.extend(chunk)
        if len(body) > HTTP_MAX_BYTES:
            return web.json_response({"error": {"code": "request_too_large", "message": "Preview request exceeds the 32768-byte limit."}}, status=413)
    try:
        result = compile_preview_request(bytes(body), max_resolution=runtime_max_resolution())
    except StateValidationError as exc:
        status = 413 if exc.code in ("state_too_large", "request_too_large") else 400
        return web.json_response({"error": {"code": exc.code, "message": str(exc)}}, status=status)
    return web.json_response(result)


def register_routes() -> bool:
    """Attach to Core's router and middleware; standalone imports remain usable."""
    try:
        from server import PromptServer
    except ModuleNotFoundError as exc:
        if exc.name == "server":
            return False
        raise
    instance = getattr(PromptServer, "instance", None)
    if instance is None:
        return False
    # Prevent duplicate registration if an extension loader imports this twice.
    if getattr(instance, "_h3_character_sheet_designer_route_registered", False):
        return True
    instance.routes.post(PREVIEW_PATH)(preview)
    instance._h3_character_sheet_designer_route_registered = True
    return True
