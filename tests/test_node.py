"""Headless node contract, runtime limits, and native STRING-output passthrough."""

import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

from h3_character_sheet.compiler import DEFAULT_STATE_JSON, StateValidationError, compile_state
from h3_character_sheet.node import H3CharacterSheetDesigner, runtime_max_resolution
from h3_character_sheet.preview import PREVIEW_PATH, register_routes


class NodeTests(unittest.TestCase):
    def setUp(self):
        self.core = types.SimpleNamespace(MAX_RESOLUTION=16384)
        self.module_patch = mock.patch.dict(sys.modules, {"nodes": self.core})
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)

    def test_exact_one_input_three_output_contract(self):
        inputs = H3CharacterSheetDesigner.INPUT_TYPES()
        self.assertEqual(set(inputs), {"required"})
        self.assertEqual(list(inputs["required"]), ["state_json"])
        kind, options = inputs["required"]["state_json"]
        self.assertEqual(kind, "STRING")
        self.assertEqual(options["default"], DEFAULT_STATE_JSON)
        self.assertIs(options["dynamicPrompts"], False)
        self.assertEqual(H3CharacterSheetDesigner.RETURN_TYPES, ("STRING", "INT", "INT"))
        self.assertEqual(H3CharacterSheetDesigner.RETURN_NAMES, ("prompt", "width", "height"))
        self.assertEqual(H3CharacterSheetDesigner.FUNCTION, "compile")

    def test_headless_run_uses_shared_compiler_without_preview(self):
        with mock.patch("h3_character_sheet.preview.compile_preview_request", side_effect=AssertionError("preview must not be called")):
            result = H3CharacterSheetDesigner().compile(DEFAULT_STATE_JSON)
        expected = compile_state(DEFAULT_STATE_JSON)
        self.assertEqual(result, (expected["prompt"], expected["width"], expected["height"]))
        # The node returns the literal JSON braces in its STRING, unexpanded.
        self.assertIn('"canvas":[2208,1280]', result[0])
        self.assertIn('{"canvas":', result[0])

    def test_v2_directives_reach_native_output_verbatim_without_preview(self):
        state = json.loads(DEFAULT_STATE_JSON)
        instruction = ' 背中に「MOON {red|blue}」\n星柄 \\ "青" '
        state.update(schema_version=2, part_prompts={"back_clothing": instruction, "footwear": "bare feet"})
        raw = json.dumps(state)
        node = H3CharacterSheetDesigner()
        self.assertIs(node.VALIDATE_INPUTS(raw), True)
        with mock.patch("h3_character_sheet.preview.compile_preview_request", side_effect=AssertionError("preview must not be called")):
            result = node.compile(raw)
        expected = compile_state(raw)
        self.assertEqual(result, (expected["prompt"], expected["width"], expected["height"]))
        self.assertIn(instruction, result[0])
        self.assertNotIn("\\{red|blue\\}", result[0])
        self.assertNotIn('"id":"feet"', result[0])

    def test_runtime_limit_is_read_on_every_call(self):
        self.assertEqual(runtime_max_resolution(), 16384)
        self.assertEqual(H3CharacterSheetDesigner().compile(DEFAULT_STATE_JSON)[1:], (2208, 1280))
        self.core.MAX_RESOLUTION = 1024
        self.assertEqual(runtime_max_resolution(), 1024)
        with self.assertRaises(StateValidationError):
            H3CharacterSheetDesigner().compile(DEFAULT_STATE_JSON)
        self.core.MAX_RESOLUTION = True
        with self.assertRaises(RuntimeError):
            runtime_max_resolution()

    def test_invalid_state_not_replaced_with_default_or_cached_output(self):
        node = H3CharacterSheetDesigner()
        node.compile(DEFAULT_STATE_JSON)
        for raw in ('{"schema_version":2}', "{broken", DEFAULT_STATE_JSON.replace('"views":["face_front","body_front","body_left","body_back"]', '"views":[]')):
            with self.assertRaises(StateValidationError):
                node.compile(raw)
            self.assertIsInstance(node.VALIDATE_INPUTS(raw), str)
        self.assertIs(node.VALIDATE_INPUTS(DEFAULT_STATE_JSON), True)

    def test_root_node_registration_and_web_directory(self):
        root = Path(__file__).resolve().parents[1]
        name = "h3_designer_test_extension"
        spec = importlib.util.spec_from_file_location(name, root / "__init__.py", submodule_search_locations=[str(root)])
        module = importlib.util.module_from_spec(spec)
        with mock.patch.dict(sys.modules, {name: module, "server": None}):
            spec.loader.exec_module(module)
        self.assertEqual(list(module.NODE_CLASS_MAPPINGS), ["H3CharacterSheetDesigner", "H3CharacterSheetDesignerReference"])
        self.assertEqual(module.NODE_DISPLAY_NAME_MAPPINGS["H3CharacterSheetDesigner"], "H3 Character Sheet Designer")
        self.assertEqual(module.WEB_DIRECTORY, "./web")

    def test_preview_registration_reuses_core_router_and_is_idempotent(self):
        routes = mock.Mock()
        instance = types.SimpleNamespace(routes=routes)
        fake = types.SimpleNamespace(PromptServer=types.SimpleNamespace(instance=instance))
        with mock.patch.dict(sys.modules, {"server": fake}):
            self.assertTrue(register_routes())
            self.assertTrue(register_routes())
        self.assertEqual(routes.post.call_args_list, [mock.call(PREVIEW_PATH), mock.call("/h3_character_sheet_designer/reference_preview")])

    def test_no_server_import_is_required_for_compiler(self):
        with mock.patch.dict(sys.modules, {"server": None}):
            self.assertFalse(register_routes())
            self.assertEqual(compile_state(DEFAULT_STATE_JSON)["width"], 2208)


if __name__ == "__main__":
    unittest.main()
