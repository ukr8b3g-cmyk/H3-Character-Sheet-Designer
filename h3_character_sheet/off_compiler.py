"""Character-only instructions based on the original Designer's format and geometry."""

import json

from .compiler import (
    BODY_IDS, PART_RULES, PORTRAIT_IDS, _active_part_prompts,
    _layout_prose, _panel_content, compile_prompt,
)

OFF_VIEW_DETAILS = {
    "face_front": "Show one front-facing bust of <Subject 1>, including the complete hairstyle, head, neck, shoulders and upper chest. The face and chest point directly toward the camera. The lower crop ends across the chest, above the waist.",
    "face_left": "Show one strict anatomical left-profile bust of <Subject 1>, with the camera looking directly at the subject's anatomical left side. Include the complete hairstyle, head, neck, shoulders and upper chest. Keep a true side view rather than a front or three-quarter view. The lower crop ends across the chest, above the waist.",
    "body_front": "Show one full-body front view of <Subject 1> in a neutral standing pose. Include the complete hairstyle and head through the bottoms of both feet or footwear, with clear space inside the assigned region above the head and below the soles or heels.",
    "body_left": "Show one full-body anatomical left profile of <Subject 1>, with the camera looking directly at the subject's anatomical left side, in a neutral standing pose. Include the complete hairstyle and head through the bottoms of the feet or footwear, with clear space inside the assigned region above the head and below the soles or heels.",
    "body_back": "Show one full-body direct rear view of <Subject 1> in a neutral standing pose. Include the complete hairstyle and head through the bottoms of both feet or footwear, with clear space inside the assigned region above the head and below the soles or heels.",
    "hands": "Show one separate close-up of both complete hands of <Subject 1>, cropped at the wrists. Preserve the reference's gloves, bare hands and existing accessories unless an applicable part directive changes them. Keep this detail separate from the busts and full-body figures.",
    "feet": "Show one separate close-up of both complete feet or footwear of <Subject 1> in a natural three-quarter detail view. Include toe areas, heels, sole edges and any visible boot shafts inside the assigned region. Preserve the reference's barefoot or footwear state and visible design unless an applicable part directive changes them. Show outer toe boxes for closed shoes and visible toes only for bare feet or open-toed footwear. Infer unseen surfaces conservatively without inventing a specific shoe design.",
}


def compile_off_prompt(state, layout, *, style_instruction="", refine=True):
    # Empty content keeps user text out of the legacy scaffold before it is split.
    scaffold_layout = {**layout, "panels": [{**panel, "content": ""} for panel in layout["panels"]]}
    scaffold = compile_prompt(state, scaffold_layout, style_instruction=style_instruction)
    header, description = scaffold.split("detailed_description:\n", 1)
    visuals, sound = description.rsplit("\noverall_soundscape:\n", 1)
    opening = visuals.split("\nLayout specification (semantic guidance, not visible text):", 1)[0]
    ending = visuals.rstrip().splitlines()[-1]
    active = _active_part_prompts(state)
    views = state["views"]

    if refine:
        header = header.replace("selectively_modified -", "partially_preserved -")
        if "hands" not in active and "other" not in active:
            header = header.replace(
                "Preserve reference gloves; do not substitute bare hands for them.",
                "Preserve the reference's gloved or bare-hand state consistently across views.",
            )
        if "footwear" not in active and "other" not in active:
            header = header.replace(
                "Preserve reference gloves and footwear; do not substitute bare hands or bare feet for them.",
                "Preserve the reference's gloved or bare-hand state and barefoot or footwear state consistently across views.",
            ).replace(
                "Preserve reference footwear or bare feet; do not substitute bare feet for reference footwear.",
                "Preserve the reference's barefoot or footwear state consistently across views.",
            )
        counts = []
        for ids, label in ((PORTRAIT_IDS, "bust portraits"), (BODY_IDS, "full-body views"), (("hands", "feet"), "isolated detail views")):
            count = sum(view in ids for view in views)
            if count:
                counts.append(f"{count} {label}")
        opening += "\nShow exactly " + str(len(views)) + " selected depictions: " + ", ".join(counts) + ". Each selected view appears once."

    geometry = {
        "canvas": layout["canvas"],
        "panels": [{key: panel[key] for key in ("id", "rect", "view")} for panel in layout["panels"]],
        "feet_y": layout["feet_y"],
    }
    lines = [header + "detailed_description:", opening,
        "Layout specification (semantic guidance, not visible text): " + json.dumps(geometry, ensure_ascii=True, separators=(",", ":")),
        "Read rect coordinates as normalized [left, top, width, height], measured from the upper-left corner of the canvas. The canvas dimensions are in pixels. Use the specified placement and proportions without drawing the layout data into the image.",
    ]
    for line in _layout_prose(state, scaffold_layout):
        if line.startswith("Panel "):
            continue
        if refine and line.startswith("Keep a common subject scale"):
            if sum(view in BODY_IDS for view in views) < 2:
                continue
            line = "Keep a common subject scale and matching head heights across the full-body views. Align the bottoms of the feet or footwear to the shared feet_y baseline, retaining clear empty space beneath every sole and heel."
        lines.append(line)
    for panel in layout["panels"]:
        content = OFF_VIEW_DETAILS[panel["id"]] if refine else _panel_content(state, panel["id"]).split("\n", 1)[0]
        lines.append(f"Panel {panel['id']}: {content}")
    for part, text in active.items():
        rule = PART_RULES[part]
        eligible = ", ".join(view for view in views if view in rule["views"])
        lines.append(f"Part directive {part} ({rule['label']}; applies to {eligible}): {rule['scope']} Explicit appearance instruction (verbatim):\n{text}")
    lines.extend([ending, "", "overall_soundscape:", sound.rstrip()])
    return "\n".join(lines) + "\n"
