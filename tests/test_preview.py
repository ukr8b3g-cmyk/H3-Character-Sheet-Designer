"""Bounded preview transport and parity with headless execution."""

import json
import sys
import types
import unittest
from unittest import mock

from h3_character_sheet.compiler import DEFAULT_STATE_JSON, PART_IDS, STATE_MAX_BYTES, StateValidationError, compile_state
from h3_character_sheet.preview import HTTP_MAX_BYTES, PREVIEW_PATH, compile_preview_request, preview

try:
    from aiohttp import web
    from aiohttp.test_utils import TestClient, TestServer
except ImportError:
    web = None


def request_bytes(state=DEFAULT_STATE_JSON):
    return json.dumps({"state_json": state}).encode("utf-8")


class PreviewEnvelopeTests(unittest.TestCase):
    def test_preview_matches_compiler(self):
        self.assertEqual(compile_preview_request(request_bytes(), max_resolution=16384), compile_state(DEFAULT_STATE_JSON))

    def test_maximal_v2_directives_and_padded_state_fit_transport(self):
        state = json.loads(DEFAULT_STATE_JSON)
        state.update(schema_version=2, part_prompts={part: "界" * 1000 for part in PART_IDS})
        raw = json.dumps(state)
        self.assertGreater(len(raw), 32768)  # Exceeds the previous HTTP limit.
        self.assertEqual(compile_preview_request(request_bytes(raw), max_resolution=16384), compile_state(raw))
        padded = raw + " " * (STATE_MAX_BYTES - len(raw.encode("utf-8")))
        body = request_bytes(padded)
        self.assertLess(len(body), HTTP_MAX_BYTES)
        self.assertEqual(compile_preview_request(body, max_resolution=16384), compile_state(raw))

    def test_transport_keys_types_duplicates_and_utf8(self):
        invalid = [b"null", b"[]", b"{}", b'{"state_json":null}', b'{"state_json":{}}', b'{"state_json":"{}","extra":1}', b'{"state_json":"{}","state_json":"{}"}', b'\xff']
        for body in invalid:
            with self.subTest(body=body):
                with self.assertRaises(StateValidationError):
                    compile_preview_request(body, max_resolution=16384)

    def test_transport_bound_inclusive(self):
        raw = request_bytes()
        body = raw + b" " * (HTTP_MAX_BYTES - len(raw))
        self.assertEqual(compile_preview_request(body, max_resolution=16384)["width"], 2208)
        with self.assertRaises(StateValidationError) as caught:
            compile_preview_request(body + b" ", max_resolution=16384)
        self.assertEqual(caught.exception.code, "request_too_large")

    def test_inner_state_bound_is_independent_of_http_bound(self):
        with self.assertRaises(StateValidationError) as caught:
            compile_preview_request(request_bytes(DEFAULT_STATE_JSON + " " * STATE_MAX_BYTES), max_resolution=16384)
        self.assertEqual(caught.exception.code, "state_too_large")


@unittest.skipIf(web is None, "aiohttp is supplied by ComfyUI; not installed in this standalone test environment")
class PreviewHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.core = types.SimpleNamespace(MAX_RESOLUTION=16384)
        self.module_patch = mock.patch.dict(sys.modules, {"nodes": self.core})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        app = web.Application(client_max_size=1024 * 1024)
        app.router.add_post(PREVIEW_PATH, preview)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()
        self.addAsyncCleanup(self.client.close)

    async def test_success_and_core_limit_read_at_request_time(self):
        response = await self.client.post(PREVIEW_PATH, json={"state_json": DEFAULT_STATE_JSON})
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertEqual(result, compile_state(DEFAULT_STATE_JSON))
        self.core.MAX_RESOLUTION = 1024
        response = await self.client.post(PREVIEW_PATH, json={"state_json": DEFAULT_STATE_JSON})
        self.assertEqual(response.status, 400)
        self.assertEqual((await response.json())["error"]["code"], "size_limit")

    async def test_maximal_v2_directives_http_200(self):
        state = json.loads(DEFAULT_STATE_JSON)
        state.update(schema_version=2, part_prompts={part: "\U0001f600" * 500 for part in PART_IDS})
        raw = json.dumps(state)
        response = await self.client.post(PREVIEW_PATH, json={"state_json": raw})
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.json(), compile_state(raw))

    async def test_invalid_state_http_400_retains_no_stale_success(self):
        response = await self.client.post(PREVIEW_PATH, json={"state_json": DEFAULT_STATE_JSON})
        self.assertEqual(response.status, 200)
        response = await self.client.post(PREVIEW_PATH, json={"state_json": "{}"})
        self.assertEqual(response.status, 400)
        result = await response.json()
        self.assertIn("error", result)
        self.assertNotIn("prompt", result)

    async def test_content_type_http_415(self):
        response = await self.client.post(PREVIEW_PATH, data=request_bytes())
        self.assertEqual(response.status, 415)

    async def test_oversized_content_length_http_413(self):
        response = await self.client.post(PREVIEW_PATH, data=b" " * (HTTP_MAX_BYTES + 1), headers={"Content-Type": "application/json"})
        self.assertEqual(response.status, 413)
        self.assertEqual((await response.json())["error"]["code"], "request_too_large")

    async def test_oversized_chunked_body_http_413(self):
        async def chunks():
            for _ in range(HTTP_MAX_BYTES // 4096 + 1):
                yield b" " * 4096
        response = await self.client.post(PREVIEW_PATH, data=chunks(), headers={"Content-Type": "application/json"})
        self.assertEqual(response.status, 413)

    async def test_inner_oversized_state_http_413(self):
        response = await self.client.post(PREVIEW_PATH, json={"state_json": DEFAULT_STATE_JSON + " " * STATE_MAX_BYTES})
        self.assertEqual(response.status, 413)
        self.assertEqual((await response.json())["error"]["code"], "state_too_large")

    async def test_malformed_envelopes_http_400(self):
        for body in (b"{", b"[]", b'{"state_json":"{}","state_json":"{}"}', b'\xff'):
            with self.subTest(body=body):
                response = await self.client.post(PREVIEW_PATH, data=body, headers={"Content-Type": "application/json"})
                self.assertEqual(response.status, 400)


if __name__ == "__main__":
    unittest.main()
