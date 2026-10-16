"""One ordered reference plan shared by prompt numbering and IMAGE outputs."""

from dataclasses import dataclass
from typing import Any

REFERENCE_ROLES = (
    "same_character", "face", "head", "clothing", "clothing_front",
    "clothing_back", "hands", "footwear",
)
EXTRA_INPUTS = ("reference_image_1", "reference_image_2")
CORE_IMAGE_INPUTS = (
    "ref_images.ref_image_0", "ref_images.ref_image_1",
    "ref_images.ref_image_2", "ref_images.ref_image_3",
)


@dataclass(frozen=True)
class ReferencePlan:
    # Includes None: these are the four fixed Core wires, not a packed batch.
    images: tuple[Any, Any, Any, Any]
    references: tuple[dict, ...]


def build_reference_plan(character_image, layout_image, reference_image_1,
                         reference_image_2, roles) -> ReferencePlan:
    ordered = (
        ("character_image", "character", character_image),
        ("layout_image", "layout", layout_image),
        ("reference_image_1", roles["reference_image_1"], reference_image_1),
        ("reference_image_2", roles["reference_image_2"], reference_image_2),
    )
    references = []
    for slot, (source, role, image) in enumerate(ordered):
        if image is None:
            continue
        number = len(references) + 1
        references.append({
            "source": source, "role": role, "picture_number": number,
            "tag": f"<Picture {number}>", "core_input": CORE_IMAGE_INPUTS[slot],
        })
    return ReferencePlan(tuple(item[2] for item in ordered), tuple(references))
