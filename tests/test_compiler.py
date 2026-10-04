"""Compiler contracts: no ComfyUI installation or third-party packages required."""

import copy
import itertools
import json
import random
from fractions import Fraction
from pathlib import Path
import unittest

from h3_character_sheet.compiler import (
    AUXILIARY_IDS, BODY_IDS, DEFAULT_STATE, DEFAULT_STATE_JSON,
    EXPERIMENTAL_PIXEL_THRESHOLD, PRESETS, STATE_MAX_BYTES, VIEW_IDS,
    StateValidationError, _round_coordinate, compile_state, layout_json, parse_state,
)


def state_json(views=None, **size_updates):
    state = copy.deepcopy(DEFAULT_STATE)
    if views is not None:
        state["views"] = list(views)
    state["size"].update(size_updates)
    return json.dumps(state)


class ValidationTests(unittest.TestCase):
    def assert_invalid(self, value, code=None, maximum=16384):
        with self.assertRaises(StateValidationError) as caught:
            compile_state(value, max_resolution=maximum)
        if code:
            self.assertEqual(caught.exception.code, code)

    def test_default_is_complete_canonical_json(self):
        self.assertEqual(compile_state(DEFAULT_STATE_JSON)["state_json"], DEFAULT_STATE_JSON)
        self.assertEqual(json.loads(DEFAULT_STATE_JSON), DEFAULT_STATE)

    def test_normalization_deduplicates_and_orders_views(self):
        result = compile_state(state_json(["feet", "body_back", "body_front", "feet", "face_front"]))
        self.assertEqual(json.loads(result["state_json"])["views"], ["face_front", "body_front", "body_back", "feet"])

    def test_unknown_and_missing_keys_every_object_level(self):
        for key in DEFAULT_STATE:
            value = copy.deepcopy(DEFAULT_STATE)
            del value[key]
            with self.subTest(missing=key):
                self.assert_invalid(json.dumps(value), "missing_key")
        for key in DEFAULT_STATE["size"]:
            value = copy.deepcopy(DEFAULT_STATE)
            del value["size"][key]
            with self.subTest(missing_size=key):
                self.assert_invalid(json.dumps(value), "missing_key")
        for extra in ("locale", "prompt", "layout", "width", "svg", "preview", "expanded"):
            value = copy.deepcopy(DEFAULT_STATE)
            value[extra] = "ignored?"
            with self.subTest(unknown=extra):
                self.assert_invalid(json.dumps(value), "unknown_key")
        value = copy.deepcopy(DEFAULT_STATE)
        value["size"]["other"] = 32
        self.assert_invalid(json.dumps(value), "unknown_key")

    def test_duplicate_keys_including_nested_and_escaped(self):
        for raw in (
            DEFAULT_STATE_JSON.replace('"schema_version":1', '"schema_version":1,"schema_version":1'),
            DEFAULT_STATE_JSON.replace('"mode":"auto"', '"mode":"auto","mode":"manual"'),
            DEFAULT_STATE_JSON.replace('"schema_version":1', '"schema_version":1,"schema_\\u0076ersion":1'),
        ):
            self.assert_invalid(raw, "duplicate_key")

    def test_nonfinite_tokens(self):
        for token in ("NaN", "Infinity", "-Infinity"):
            self.assert_invalid(DEFAULT_STATE_JSON.replace("1120", token), "non_finite")
        self.assert_invalid(DEFAULT_STATE_JSON.replace("1120", "1e999"), "invalid_integer")

    def test_schema_is_strict_integer_one(self):
        for version in (True, False, 1.0, "1", None, 0, 2, -1, {}, []):
            value = copy.deepcopy(DEFAULT_STATE)
            value["schema_version"] = version
            with self.subTest(version=version):
                self.assert_invalid(json.dumps(value), "unsupported_schema")

    def test_sizes_are_strict_integer_grid_and_runtime_bound(self):
        for field in ("body_height", "manual_width", "manual_height"):
            for value in (True, False, 32.0, "32", None, [], {}):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(state_json(**{field: value}), "invalid_integer")
            for value in (-32, 0, 1, 31, 33, 63):
                with self.subTest(field=field, value=value):
                    self.assert_invalid(state_json(**{field: value}), "invalid_size")
            self.assert_invalid(state_json(**{field: 16416}), "size_limit")
        # Inactive values are still part of the strict schema.
        self.assert_invalid(state_json(mode="auto", manual_width=33), "invalid_size")
        self.assert_invalid(state_json(mode="manual", body_height=33), "invalid_size")

    def test_empty_unknown_or_wrong_typed_views(self):
        self.assert_invalid(state_json([]), "empty_views")
        self.assert_invalid(state_json(["nose_left"]), "unknown_view")
        for value in ("body_front", {}, 1, None, [1], [True], [[]], ["body_front", {}]):
            state = copy.deepcopy(DEFAULT_STATE)
            state["views"] = value
            with self.subTest(value=value):
                self.assert_invalid(json.dumps(state), "invalid_type")

    def test_mode_values_are_exact(self):
        for value in ("AUTO", "Manual", "", None, 0, True, [], {}):
            with self.subTest(mode=value):
                self.assert_invalid(state_json(mode=value), "invalid_mode")

    def test_non_object_or_wrong_nested_type(self):
        for raw in ("null", "1", "[]", '"hello"', "true"):
            self.assert_invalid(raw, "invalid_type")
        for value in (None, 3, "auto", []):
            state = copy.deepcopy(DEFAULT_STATE)
            state["size"] = value
            self.assert_invalid(json.dumps(state), "invalid_type")

    def test_invalid_json_and_utf8_and_type(self):
        for raw in ("", " ", "{", "[", DEFAULT_STATE_JSON + "{}"):
            self.assert_invalid(raw, "invalid_json")
        self.assert_invalid("[" * 2000 + "]" * 2000)
        self.assert_invalid("\ud800", "invalid_utf8")
        for raw in (None, DEFAULT_STATE, b"{}", 123):
            self.assert_invalid(raw, "invalid_type")

    def test_utf8_byte_limit_is_inclusive(self):
        padding = STATE_MAX_BYTES - len(DEFAULT_STATE_JSON.encode("utf-8"))
        self.assertEqual(compile_state(DEFAULT_STATE_JSON + " " * padding)["state_json"], DEFAULT_STATE_JSON)
        self.assert_invalid(DEFAULT_STATE_JSON + " " * (padding + 1), "state_too_large")
        # Multi-byte text, even when parseable JSON, is measured in UTF-8 bytes.
        self.assert_invalid('"' + "界" * (STATE_MAX_BYTES // 3 + 1) + '"', "state_too_large")

    def test_runtime_maximum_not_assumed_multiple_of_32(self):
        result = compile_state(state_json(mode="manual", body_height=32, manual_width=64, manual_height=64), max_resolution=65)
        self.assertEqual([result["width"], result["height"]], [64, 64])
        self.assert_invalid(state_json(mode="manual", body_height=32, manual_width=96, manual_height=64), "size_limit", maximum=65)
        for invalid in (True, 0, 31, "16384", 16384.0):
            with self.assertRaises(ValueError):
                compile_state(DEFAULT_STATE_JSON, max_resolution=invalid)

    def test_validation_never_mutates_input_or_default(self):
        before = copy.deepcopy(DEFAULT_STATE)
        raw = state_json(["feet", "hands", "hands"])
        original = raw
        compile_state(raw)
        self.assertEqual(raw, original)
        self.assertEqual(DEFAULT_STATE, before)
        result = parse_state(DEFAULT_STATE_JSON)
        result["views"].clear()
        self.assertEqual(DEFAULT_STATE, before)


class LayoutTests(unittest.TestCase):
    def test_specification_auto_examples(self):
        examples = [
            (PRESETS["basic"], 1120, 2208, 1280),
            (PRESETS["detail"], 1120, 2208, 1280),
            (PRESETS["turnaround"], 1120, 1600, 1280),
            (["body_front"], 1120, 608, 1280),
            (["body_left"], 1120, 608, 1280),
            (["face_front"], 1120, 736, 1280),
            (["hands", "feet"], 1120, 736, 1280),
            (PRESETS["basic"], 672, 1344, 768),
            (PRESETS["detail"], 672, 1344, 768),
            (PRESETS["turnaround"], 672, 960, 768),
            (["body_front"], 672, 384, 768),
        ]
        for views, body_height, width, height in examples:
            with self.subTest(views=views, body_height=body_height):
                result = compile_state(state_json(views, body_height=body_height))
                self.assertEqual((result["width"], result["height"]), (width, height))
                self.assertEqual(result["pixel_count"], width * height)

    def test_all_63_nonempty_subsets_in_auto_and_manual(self):
        count = 0
        configurations = [
            {"body_height": h} for h in (32, 672, 896, 1120, 1344, 1792)
        ] + [
            {"mode": "manual", "manual_width": w, "manual_height": h}
            for w, h in ((2240, 1280), (1280, 2240), (32, 16384), (16384, 32), (32, 32))
        ]
        for bits in range(1, 64):
            views = [view for index, view in enumerate(VIEW_IDS) if bits & (1 << index)]
            count += 1
            for size in configurations:
                with self.subTest(views=views, size=size):
                    result = compile_state(state_json(views, **size))
                    layout = result["layout"]
                    width, height = layout["canvas"]
                    self.assertEqual(width % 32, 0)
                    self.assertEqual(height % 32, 0)
                    self.assertEqual([panel["id"] for panel in layout["panels"]], views)
                    rects = [panel["rect"] for panel in layout["panels"]]
                    for left, top, rect_width, rect_height in rects:
                        self.assertGreater(rect_width, 0)
                        self.assertGreater(rect_height, 0)
                        self.assertGreaterEqual(left, 0)
                        self.assertGreaterEqual(top, 0)
                        self.assertLessEqual(left + rect_width, 1 + 1e-6)
                        self.assertLessEqual(top + rect_height, 1 + 1e-6)
                    for first, second in itertools.combinations(rects, 2):
                        x1, y1, w1, h1 = first
                        x2, y2, w2, h2 = second
                        self.assertTrue(x1 + w1 <= x2 + 1e-6 or x2 + w2 <= x1 + 1e-6 or y1 + h1 <= y2 + 1e-6 or y2 + h2 <= y1 + 1e-6)
                    bodies = [panel for panel in layout["panels"] if panel["id"] in BODY_IDS]
                    if not bodies:
                        self.assertIsNone(layout["feet_y"])
                        self.assertNotIn("common subject scale", result["prompt"])
                        self.assertNotIn("shared feet_y baseline", result["prompt"])
                    else:
                        self.assertIsNotNone(layout["feet_y"])
                        for panel in bodies:
                            _, top, _, rect_height = panel["rect"]
                            self.assertAlmostEqual(top + rect_height, layout["feet_y"], delta=1.00001e-6)
                            self.assertEqual(top, bodies[0]["rect"][1])
                            self.assertEqual(rect_height, bodies[0]["rect"][3])
        self.assertEqual(count, 63)

    def test_auxiliary_splits(self):
        def panel_map(views):
            return {panel["id"]: panel["rect"] for panel in compile_state(state_json(views))["layout"]["panels"]}
        six = panel_map(VIEW_IDS)
        face, hands, feet = six["face_front"], six["hands"], six["feet"]
        self.assertEqual(hands[1], feet[1])
        self.assertEqual(hands[2:], feet[2:])
        self.assertLess(hands[0], feet[0])
        self.assertLess(face[1] + face[3], hands[1])
        only = panel_map(["hands", "feet"])
        self.assertEqual(only["hands"][0], only["feet"][0])
        self.assertEqual(only["hands"][2:], only["feet"][2:])
        self.assertLess(only["hands"][1] + only["hands"][3], only["feet"][1])

    def test_auto_preserves_requested_body_panel_height(self):
        for h in (32, 672, 896, 1120, 1344, 1792):
            result = compile_state(state_json(body_height=h))
            for panel in result["layout"]["panels"]:
                if panel["id"] in BODY_IDS:
                    self.assertAlmostEqual(panel["rect"][3] * result["height"], h, delta=result["height"] * 1e-6)
                    self.assertAlmostEqual(panel["rect"][2] * result["width"], 2 * h / 5, delta=result["width"] * 1e-6)

    def test_manual_keeps_dimensions_and_uses_unrounded_ideal_canvas(self):
        for views in PRESETS.values():
            result = compile_state(state_json(views, mode="manual", manual_width=2240, manual_height=1280))
            self.assertEqual((result["width"], result["height"]), (2240, 1280))
        # h=32 gives ideal H=256/7, not Auto H=64. In a 32x32
        # manual canvas a body panel occupies exactly 7/8 of the height.
        result = compile_state(state_json(["body_front"], mode="manual", body_height=32, manual_width=32, manual_height=32))
        self.assertEqual(result["layout"]["panels"][0]["rect"][3], 0.875)
        self.assertEqual(result["layout"]["feet_y"], 0.9375)

    def test_manual_is_uniformly_scaled_and_centered(self):
        result = compile_state(state_json(VIEW_IDS, mode="manual", manual_width=1024, manual_height=2048))
        panels = {panel["id"]: panel["rect"] for panel in result["layout"]["panels"]}
        body = panels["body_front"]
        self.assertAlmostEqual(body[2] * 1024 / (body[3] * 2048), 0.4, delta=5e-6)
        self.assertAlmostEqual(body[1], 1 - (body[1] + body[3]), delta=1e-6)
        left = panels["face_front"][0]
        right = panels["body_back"][0] + panels["body_back"][2]
        self.assertAlmostEqual(left, 1 - right, delta=1e-6)

    def test_saved_inactive_manual_sizes_do_not_affect_auto_prompt(self):
        result = compile_state(state_json(manual_width=32, manual_height=16384))
        self.assertEqual(result["prompt"], compile_state(DEFAULT_STATE_JSON)["prompt"])
        self.assertNotEqual(result["state_json"], DEFAULT_STATE_JSON)

    def test_auto_output_limits_checked_separately_from_inputs(self):
        # Every input is <= 2240 but the derived width exceeds it.
        with self.assertRaisesRegex(StateValidationError, "output width"):
            compile_state(state_json(body_height=2240), max_resolution=2240)
        with self.assertRaisesRegex(StateValidationError, "output height"):
            compile_state(state_json(["body_front"], body_height=32, manual_width=32, manual_height=32), max_resolution=32)
        result = compile_state(state_json(["body_front"], body_height=32, manual_width=32, manual_height=32), max_resolution=64)
        self.assertEqual((result["width"], result["height"]), (32, 64))

    def test_round_half_up_at_exact_ties_and_no_negative_zero(self):
        self.assertEqual(_round_coordinate(Fraction(1, 2_000_000)), 0.000001)
        self.assertEqual(_round_coordinate(Fraction(5, 2_000_000)), 0.000003)
        self.assertEqual(_round_coordinate(Fraction(1, 3_000_000)), 0)
        self.assertEqual(str(_round_coordinate(Fraction(0))), "0.0")
        result = compile_state(DEFAULT_STATE_JSON)
        raw = layout_json(result["layout"])
        self.assertNotIn("-0.000000", raw)
        self.assertNotIn("e-", raw)
        self.assertEqual(json.loads(raw), result["layout"])

    def test_experimental_is_only_an_informational_threshold(self):
        low = compile_state(state_json(body_height=672))
        self.assertEqual(low["pixel_count"], EXPERIMENTAL_PIXEL_THRESHOLD)
        self.assertFalse(low["experimental"])
        high = compile_state(DEFAULT_STATE_JSON)
        self.assertEqual(high["pixel_count"], 2826240)
        self.assertTrue(high["experimental"])
        self.assertEqual(high["megapixels"], 2.82624)


class PromptTests(unittest.TestCase):
    def test_fixed_section_order_and_format(self):
        prompt = compile_state(DEFAULT_STATE_JSON)["prompt"]
        sections = ["subject_definitions:", "summary:", "retention_analysis:", "detailed_description:", "overall_soundscape:", "non_diegetic_music:"]
        positions = [prompt.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        self.assertTrue(prompt.startswith(sections[0]))
        self.assertIn("summary:\n[reference generation]", prompt)
        self.assertEqual(prompt.count("\n[Shot 1]"), 1)
        self.assertNotIn("[Shot 2]", prompt)
        self.assertNotIn("\r", prompt)
        self.assertTrue(prompt.endswith("\n"))
        self.assertFalse(prompt.endswith("\n\n"))
        self.assertTrue(prompt.isascii())
        self.assertNotIn("<svg", prompt)
        self.assertNotIn("<html", prompt)

    def test_identity_side_reference_and_retention(self):
        result = compile_state(state_json(VIEW_IDS))
        prompt = result["prompt"]
        self.assertIn("<Subject 1> is the person in <Picture 1>", prompt)
        self.assertIn("camera looking directly at the subject's anatomical left side", prompt)
        self.assertNotIn("nose points", prompt)
        self.assertIn("Infer any unseen surfaces conservatively", prompt)
        self.assertIn("gloves", prompt)
        self.assertIn("boot shafts", prompt)
        self.assertIn("overall_soundscape:\nNone.", prompt)
        self.assertIn("non_diegetic_music:\nNone.", prompt)

    def test_no_unselected_panels_or_body_instructions(self):
        for view in VIEW_IDS:
            with self.subTest(view=view):
                result = compile_state(state_json([view]))
                self.assertEqual([panel["id"] for panel in result["layout"]["panels"]], [view])
                for other in VIEW_IDS:
                    if other != view:
                        self.assertNotIn(f'"id":"{other}"', result["prompt"])
                if view in AUXILIARY_IDS:
                    self.assertNotIn("full-body", result["prompt"])
                    self.assertNotIn("head to the soles", result["prompt"])
                    self.assertIn('"feet_y":null', result["prompt"])

    def test_semantic_order_key_order_and_whitespace_invariance(self):
        randomizer = random.Random(53)
        baseline = compile_state(state_json(VIEW_IDS))
        for _ in range(20):
            views = list(VIEW_IDS) + ["feet", "body_left"]
            randomizer.shuffle(views)
            size_items = list(DEFAULT_STATE["size"].items())
            randomizer.shuffle(size_items)
            items = [("size", dict(size_items)), ("views", views), ("schema_version", 1)]
            randomizer.shuffle(items)
            raw = json.dumps(dict(items), indent=3)
            result = compile_state(raw)
            self.assertEqual(result, baseline)

    def test_snapshot_presets_and_single_views(self):
        cases = {f"preset_{name}": views for name, views in PRESETS.items()}
        cases.update({f"single_{view}": [view] for view in VIEW_IDS})
        cases["hands_and_feet"] = ["hands", "feet"]
        directory = Path(__file__).with_name("snapshots")
        for name, views in cases.items():
            with self.subTest(snapshot=name):
                expected = (directory / f"{name}.txt").read_bytes()
                actual = compile_state(state_json(views))["prompt"].encode("utf-8")
                self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
