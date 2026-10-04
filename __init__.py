"""Install this directory in ComfyUI/custom_nodes to register the designer."""

from .h3_character_sheet.node import H3CharacterSheetDesigner
from .h3_character_sheet.preview import register_routes

NODE_CLASS_MAPPINGS = {"H3CharacterSheetDesigner": H3CharacterSheetDesigner}
NODE_DISPLAY_NAME_MAPPINGS = {"H3CharacterSheetDesigner": "H3 Character Sheet Designer"}
WEB_DIRECTORY = "./web"

register_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
