"""Install this directory in ComfyUI/custom_nodes to register the designer."""

from .h3_character_sheet.node import H3CharacterSheetDesigner
from .h3_character_sheet.reference_node import H3CharacterSheetDesignerReference
from .h3_character_sheet.multi_reference_node import H3CharacterSheetDesignerMultiReference
from .h3_character_sheet.reference_v11_node import H3CharacterSheetDesignerReferenceV11
from .h3_character_sheet.preview import register_routes
from .h3_character_sheet.reference13_node import H3CharacterSheetDesignerReference13
from .h3_character_sheet.reference13_preview import register_routes as register_reference13_routes

NODE_CLASS_MAPPINGS = {"H3CharacterSheetDesigner": H3CharacterSheetDesigner, "H3CharacterSheetDesignerReference": H3CharacterSheetDesignerReference, "H3CharacterSheetDesignerMultiReference": H3CharacterSheetDesignerMultiReference}
NODE_DISPLAY_NAME_MAPPINGS = {"H3CharacterSheetDesigner": "H3 Character Sheet Designer", "H3CharacterSheetDesignerReference": "H3 Character Sheet Designer Reference", "H3CharacterSheetDesignerMultiReference": "H3 Character Sheet Designer Multi Reference"}
NODE_CLASS_MAPPINGS["H3CharacterSheetDesignerReferenceV11"] = H3CharacterSheetDesignerReferenceV11
NODE_DISPLAY_NAME_MAPPINGS["H3CharacterSheetDesignerReferenceV11"] = "H3 Sheet Designer Reference V1.1"
WEB_DIRECTORY = "./web"
NODE_CLASS_MAPPINGS["H3CharacterSheetDesignerReference13"] = H3CharacterSheetDesignerReference13
NODE_DISPLAY_NAME_MAPPINGS["H3CharacterSheetDesignerReference13"] = "H3 Character Sheet Designer Reference 13 Views"

register_routes()
register_reference13_routes()

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]
