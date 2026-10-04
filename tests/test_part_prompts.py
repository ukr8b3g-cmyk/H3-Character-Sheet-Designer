"""Version-two literal part directives, strict state, and legacy compatibility."""

import copy
import json
from pathlib import Path
import random
import unittest

from h3_character_sheet.compiler import (
    BODY_IDS, DEFAULT_STATE, DEFAULT_STATE_JSON, PART_IDS, PART_PROMPT_MAX_UNITS,
    PART_RULES, PORTRAIT_IDS, PRESETS, STATE_MAX_BYTES, VIEW_IDS, StateValidationError,
    compile_state, layout_json, parse_state, serialize_state,
)


def make_state(prompts=None, views=VIEW_IDS, **size_updates):
    state = copy.deepcopy(DEFAULT_STATE)
    state.update(schema_version=2, views=list(views), part_prompts={} if prompts is None else prompts)
    state["size"].update(size_updates)
    return state


def compile_parts(prompts=None, views=VIEW_IDS, **size_updates):
    return compile_state(json.dumps(make_state(prompts, views, **size_updates)))


def geometry(result):
    layout = result["layout"]
    return (result["width"], result["height"], layout["canvas"], layout["feet_y"],
            [{key: panel[key] for key in ("id", "rect", "view")} for panel in layout["panels"]])


class PartStateTests(unittest.TestCase):
    def assert_invalid(self, raw, code):
        with self.assertRaises(StateValidationError) as caught:
            compile_state(raw)
        self.assertEqual(caught.exception.code, code)

    def test_fixed_canonical_part_contract(self):
        self.assertEqual(PART_IDS, ("head_hair", "face", "upper_clothing", "back_clothing",
                                    "lower_body", "hands", "footwear", "other"))
        self.assertEqual(tuple(PART_RULES), PART_IDS)
        self.assertEqual(PART_PROMPT_MAX_UNITS, 1000)
        self.assertEqual(STATE_MAX_BYTES, 65536)

    def test_no_automatic_migration_or_downgrade(self):
        v1 = parse_state(DEFAULT_STATE_JSON)
        self.assertEqual(v1["schema_version"], 1)
        self.assertNotIn("part_prompts", v1)
        self.assertEqual(serialize_state(v1), DEFAULT_STATE_JSON)
        v2 = parse_state(json.dumps(make_state()))
        self.assertEqual(v2["schema_version"], 2)
        self.assertEqual(v2["part_prompts"], {})
        self.assertEqual(parse_state(serialize_state(v2)), v2)
        blank = parse_state(json.dumps(make_state({"face": " \n\t"})))
        self.assertEqual(blank["schema_version"], 2)
        self.assertEqual(blank["part_prompts"], {})

    def test_version_specific_exact_keys(self):
        value = copy.deepcopy(DEFAULT_STATE)
        value["part_prompts"] = {}
        self.assert_invalid(json.dumps(value), "unknown_key")
        value["schema_version"] = 2
        self.assertEqual(parse_state(json.dumps(value))["part_prompts"], {})
        for key in value:
            missing = copy.deepcopy(value)
            del missing[key]
            with self.subTest(missing=key):
                self.assert_invalid(json.dumps(missing), "missing_key")
        value["prompt"] = "do not ignore extras"
        self.assert_invalid(json.dumps(value), "unknown_key")

    def test_sparse_map_known_keys_and_only_string_values(self):
        for value in (None, [], "", False, 0):
            with self.subTest(map=value):
                state = make_state()
                state["part_prompts"] = value
                self.assert_invalid(json.dumps(state), "invalid_type")
        for part in ("eyes", "rear", "__proto__", "FOOTWEAR", ""):
            self.assert_invalid(json.dumps(make_state({part: "test"})), "unknown_part")
        for value in (None, 1, True, [], {}):
            self.assert_invalid(json.dumps(make_state({"face": value})), "invalid_type")
        for part in PART_IDS:
            self.assertEqual(parse_state(json.dumps(make_state({part: "test"})))["part_prompts"], {part: "test"})

    def test_duplicate_and_escaped_duplicate_part_keys(self):
        raw = json.dumps(make_state({"face": "first"}), separators=(",", ":"))
        for replacement in ('"face":"first","face":"second"', '"face":"first","fa\\u0063e":"second"'):
            self.assert_invalid(raw.replace('"face":"first"', replacement), "duplicate_key")

    def test_nonblank_is_verbatim_blank_matches_browser_trim(self):
        whitespace = "\t\n\v\f\r \u00a0\u1680\u2000\u2001\u2002\u2003\u2004\u2005\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"
        self.assertEqual(parse_state(json.dumps(make_state({"face": whitespace})))["part_prompts"], {})
        for text in ('  顔はそのまま\n髪の色のみ変更  ', '{red|blue} \\pattern "文字"\r\n次の行', '\x1c', 'e\u0301', '\U0001f9d1\u200d\U0001f9b0'):
            with self.subTest(text=text):
                result = parse_state(json.dumps(make_state({"face": text})))
                self.assertEqual(result["part_prompts"]["face"], text)
                self.assertEqual(parse_state(serialize_state(result)), result)

    def test_utf16_limit_inclusive_for_bmp_astral_and_mixed(self):
        for text in ("a" * 1000, "界" * 1000, "\U0001f600" * 500, "\U0001f600" * 499 + "ab"):
            self.assertEqual(parse_state(json.dumps(make_state({"face": text})))["part_prompts"]["face"], text)
        for text in ("a" * 1001, "界" * 1001, "\U0001f600" * 501, "\U0001f600" * 500 + "a", " " * 1001):
            self.assert_invalid(json.dumps(make_state({"face": text})), "part_prompt_too_long")

    def test_reject_unpaired_surrogates_even_when_json_escaped(self):
        for text in ("\ud800", "\udfff", "x\ud800y", "\ud800\ud800"):
            self.assert_invalid(json.dumps(make_state({"face": text})), "invalid_utf8")
        raw = json.dumps(make_state({"face": "ok"}))
        self.assert_invalid(raw.replace('"face": "ok"', '"fa\\ud800ce": "ok"'), "invalid_utf8")
        valid_pair = raw.replace('"face": "ok"', '"face": "\\ud83d\\ude00"')
        self.assertEqual(parse_state(valid_pair)["part_prompts"]["face"], "\U0001f600")

    def test_all_eight_maximal_escaped_inputs_fit_and_roundtrip(self):
        for char, repetitions in (("界", 1000), ("\x01", 1000), ("\U0001f600", 500)):
            prompts = {part: char * repetitions for part in PART_IDS}
            raw = json.dumps(make_state(prompts))
            self.assertLess(len(raw.encode("utf-8")), STATE_MAX_BYTES)
            result = compile_state(raw)
            self.assertLess(len(result["state_json"].encode("utf-8")), STATE_MAX_BYTES)
            self.assertEqual(json.loads(result["state_json"])["part_prompts"], prompts)
            self.assertEqual(compile_state(result["state_json"]), result)

    def test_canonical_order_and_input_key_order_invariance(self):
        prompts = {part: f"instruction for {part}" for part in PART_IDS}
        baseline = compile_parts(prompts)
        rng = random.Random(83)
        for _ in range(15):
            part_items = list(prompts.items()); rng.shuffle(part_items)
            state = make_state(dict(part_items), reversed(VIEW_IDS))
            size_items = list(state["size"].items()); rng.shuffle(size_items)
            state["size"] = dict(size_items)
            state_items = list(state.items()); rng.shuffle(state_items)
            self.assertEqual(compile_state(json.dumps(dict(state_items), indent=3)), baseline)
        self.assertEqual(tuple(json.loads(baseline["state_json"])["part_prompts"]), PART_IDS)


class PartPromptTests(unittest.TestCase):
    def test_v2_empty_matches_all_fifteen_existing_prompt_snapshots(self):
        cases = {f"preset_{name}": views for name, views in PRESETS.items()}
        cases.update({f"single_{view}": [view] for view in VIEW_IDS})
        cases.update(hands_and_feet=["hands", "feet"], both_portraits=PORTRAIT_IDS,
                     left_portrait_and_feet=["face_left", "feet"],
                     legacy_six_views=[view for view in VIEW_IDS if view != "face_left"])
        self.assertEqual(len(cases), 15)
        for name, views in cases.items():
            with self.subTest(snapshot=name):
                expected = (Path(__file__).with_name("snapshots") / f"{name}.txt").read_bytes()
                self.assertEqual(compile_parts({}, views)["prompt"].encode("utf-8"), expected)

    def test_all_127_geometries_remain_unchanged_empty_or_all_parts(self):
        for bits in range(1, 1 << len(VIEW_IDS)):
            views = [view for i, view in enumerate(VIEW_IDS) if bits & (1 << i)]
            for size in ({}, {"mode": "manual", "manual_width": 1024, "manual_height": 2048}):
                legacy = copy.deepcopy(DEFAULT_STATE); legacy["views"] = views; legacy["size"].update(size)
                expected = compile_state(json.dumps(legacy))
                empty = compile_parts({}, views, **size)
                with self.subTest(views=views, size=size):
                    self.assertEqual({key: value for key, value in empty.items() if key != "state_json"},
                                     {key: value for key, value in expected.items() if key != "state_json"})
                    explicit = compile_parts({part: f"custom {part}" for part in PART_IDS}, views, **size)
                    self.assertEqual(geometry(explicit), geometry(expected))

    def test_every_part_only_reaches_eligible_selected_panels_in_every_subset(self):
        expected_views = {
            "head_hair": (*PORTRAIT_IDS, *BODY_IDS), "face": (*PORTRAIT_IDS, *BODY_IDS),
            "upper_clothing": (*PORTRAIT_IDS, *BODY_IDS), "back_clothing": ("body_left", "body_back"),
            "lower_body": BODY_IDS, "hands": (*BODY_IDS, "hands"),
            "footwear": (*BODY_IDS, "feet"), "other": VIEW_IDS,
        }
        for part, eligible in expected_views.items():
            text = f"Verbatim instruction marker for {part}"
            for bits in range(1, 1 << len(VIEW_IDS)):
                views = [view for i, view in enumerate(VIEW_IDS) if bits & (1 << i)]
                result = compile_parts({part: text}, views)
                baseline = compile_parts({}, views)
                with self.subTest(part=part, views=views):
                    for panel, old in zip(result["layout"]["panels"], baseline["layout"]["panels"]):
                        self.assertEqual(text in panel["content"], panel["id"] in eligible)
                        if panel["id"] not in eligible:
                            self.assertEqual(panel, old)
                    self.assertEqual(text in result["prompt"], bool(set(views) & set(eligible)))
                    if not set(views) & set(eligible):
                        self.assertEqual(result["prompt"], baseline["prompt"])

    def test_json_and_natural_language_share_identical_literal_directives(self):
        text = ' 背中に「MOON {red|blue}」\n星柄 \\ 右下に小さく "青"。\r\n'
        result = compile_parts({"back_clothing": text})
        serialized = layout_json(result["layout"])
        self.assertEqual(json.loads(serialized), result["layout"])
        self.assertIn("Layout specification (semantic guidance, not visible text): " + serialized, result["prompt"])
        self.assertEqual(result["prompt"].count(text), 2)  # Literal copies in eligible panel prose.
        for panel in result["layout"]["panels"]:
            self.assertIn(panel["content"], result["prompt"])
        self.assertEqual(json.loads(result["state_json"])["part_prompts"]["back_clothing"], text)
        self.assertNotIn("\\{red|blue\\}", result["prompt"])

    def test_back_surface_never_reaches_front_or_portraits(self):
        text = "Back only: a large white word STAR and a blue star pattern"
        result = compile_parts({"back_clothing": text})
        for panel in result["layout"]["panels"]:
            if panel["id"] in ("body_left", "body_back"):
                self.assertIn(text, panel["content"])
                self.assertIn("only where that rear surface is visible", panel["content"])
                self.assertIn("Never move this rear-surface design onto the front, side surface, or portraits", panel["content"])
            else:
                self.assertNotIn(text, panel["content"])
        self.assertIn("back_clothing takes precedence over upper_clothing", result["prompt"])

    def test_footwear_override_works_without_feet_panel(self):
        text = "Bare feet with blue painted toenails"
        result = compile_parts({"footwear": text}, BODY_IDS)
        self.assertNotIn('"id":"feet"', result["prompt"])
        self.assertNotIn("required separate panel", result["prompt"])
        for panel in result["layout"]["panels"]:
            self.assertIn(text, panel["content"])
        self.assertIn("bottoms of the feet or footwear aligned to the shared feet_y baseline", result["prompt"])
        self.assertNotIn("soles of the footwear", result["prompt"])
        self.assertNotIn("Preserve reference footwear", result["prompt"])
        self.assertIn("Preserve reference gloves", result["prompt"])

    def test_hand_and_foot_overrides_remove_conflicting_reference_constraints(self):
        hands = compile_parts({"hands": "Bare hands without gloves"})["prompt"]
        self.assertNotIn("keep any gloves from the reference", hands)
        self.assertNotIn("Preserve reference gloves", hands)
        self.assertIn("Preserve reference footwear or bare feet", hands)
        self.assertIn("If the reference is barefoot, preserve bare feet", hands)
        feet = compile_parts({"footwear": "Tall purple boots instead of bare feet"})["prompt"]
        for forbidden in ("If the reference is barefoot, preserve bare feet", "preserving whether the reference shows footwear or bare feet", "do not invent a specific shoe design", "Preserve reference footwear"):
            self.assertNotIn(forbidden, feet)
        self.assertIn("keep any gloves from the reference", feet)
        self.assertIn("required separate panel", feet)
        self.assertIn("do not expose bare toes through closed shoes", feet)

    def test_other_can_modify_parts_without_losing_identity_static_or_geometry(self):
        text = "Cel shaded style, no gloves, bare feet, and a SILVER shirt logo"
        result = compile_parts({"other": text})
        prompt = result["prompt"]
        for forbidden in ("fully_preserved", "Preserve reference gloves", "Preserve reference footwear", "keep any gloves from the reference", "If the reference is barefoot, preserve bare feet", "Do not add captions, labels, lettering"):
            self.assertNotIn(forbidden, prompt)
        for required in ("same person's identity", "More specific named-part directives take precedence", "Keep the subject and camera still", "sheet is silent", "first frame", "last frame", "exactly the selected views", "not explicitly changed", "beyond those explicitly requested", "Text, lettering, logos, or patterns", "except for appearance changes explicitly requested by the other directive"):
            self.assertIn(required, prompt)
        self.assertEqual(geometry(result), geometry(compile_parts()))
        for panel in result["layout"]["panels"]:
            self.assertIn(text, panel["content"])

    def test_combined_global_upper_and_back_rules_keep_precedence_and_exclusions(self):
        directives = {"other": "服は青色", "upper_clothing": "上着は赤色", "back_clothing": "背中だけ白いFLOWER"}
        result = compile_parts(directives)
        prompt = result["prompt"]
        self.assertIn("more specific named-part directives take precedence", prompt)
        self.assertIn("back_clothing takes precedence over upper_clothing on the rear clothing surface", prompt)
        for panel in result["layout"]["panels"]:
            self.assertIn(directives["other"], panel["content"])
            self.assertEqual(directives["upper_clothing"] in panel["content"], panel["id"] in (*PORTRAIT_IDS, *BODY_IDS))
            self.assertEqual(directives["back_clothing"] in panel["content"], panel["id"] in ("body_left", "body_back"))
        self.assertEqual(geometry(result), geometry(compile_parts()))

    def test_named_overrides_qualify_global_preservation_without_dropping_other_parts(self):
        result = compile_parts({"upper_clothing": "A neon green jacket with HELLO on the chest"})
        prompt = result["prompt"]
        self.assertNotIn("fully_preserved", prompt)
        self.assertNotIn("Do not add captions, labels, lettering", prompt)
        self.assertIn("every part and detail not changed", prompt)
        self.assertIn("Preserve reference gloves", prompt)
        self.assertIn("Preserve reference footwear", prompt)
        self.assertIn("Do not add sheet-level captions, panel labels", prompt)
        self.assertIn("without inventing lettering or patterns", prompt)
        self.assertIn("single identity", compile_parts({"other": "red coat"})["prompt"])


if __name__ == "__main__":
    unittest.main()
