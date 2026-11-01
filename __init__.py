"""Register the previous release and the current character-sheet node."""
from .h3_character_sheet.reference13_node import H3CharacterSheetDesignerReference13
from .h3_character_sheet.reference13_preview import register_routes as register_reference13_routes
from .h3_character_sheet.reference_v13_node import H3CharacterSheetDesignerReferenceV13
from .h3_character_sheet.reference_v13_preview import register_routes as register_v13_routes

NODE_CLASS_MAPPINGS = {
    "H3CharacterSheetDesignerReference13": H3CharacterSheetDesignerReference13,
    "H3CharacterSheetDesignerReferenceV13": H3CharacterSheetDesignerReferenceV13,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "H3CharacterSheetDesignerReference13": "H3 Character Sheet Designer v1.2.2",
    "H3CharacterSheetDesignerReferenceV13": "H3 Character Sheet Designer v1.3.0",
}
WEB_DIRECTORY = "./web"
register_reference13_routes()
register_v13_routes()
__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
