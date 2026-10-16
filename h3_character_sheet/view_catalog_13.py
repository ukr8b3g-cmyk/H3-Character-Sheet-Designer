"""H3 view order and camera conventions; no image or model dependencies."""
from .compiler import BODY_IDS, PRESETS as LEGACY_PRESETS, VIEW_IDS as LEGACY_VIEW_IDS

PORTRAIT_IDS = ('face_front', 'face_left', 'face_right', 'face_3q_left', 'face_3q_right', 'face_back')
CLOTHING_IDS = ('clothing_front', 'clothing_back')
VIEW_IDS = (*PORTRAIT_IDS, *BODY_IDS, *CLOTHING_IDS, 'hands', 'feet')
PRESETS = {**LEGACY_PRESETS, 'head': PORTRAIT_IDS, 'clothing': CLOTHING_IDS, 'detail': VIEW_IDS}
VIEW_DETAILS = {
    'face_front': ('front portrait', 'One front-facing bust, complete head and hair through the upper chest. Both eyes visible; no waist, legs or feet.'),
    'face_left': ('anatomical left-profile portrait', 'One strict anatomical left-profile bust, complete head and hair through the upper chest. The nose points to the RIGHT edge of the sheet, as in the H3 left-view convention. One visible eye; no front or three-quarter view.'),
    'face_right': ('anatomical right-profile portrait', 'One strict anatomical right-profile bust, complete head and hair through the upper chest. The nose points to the LEFT edge of the sheet. One visible eye; preserve asymmetric features rather than mirroring the person.'),
    'face_3q_left': ('anatomical left three-quarter portrait', 'One anatomical left three-quarter bust at 45 degrees, complete head and hair through the upper chest. The nose points toward the RIGHT edge. Both eyes visible with the farther eye foreshortened; not a front or strict profile view.'),
    'face_3q_right': ('anatomical right three-quarter portrait', 'One anatomical right three-quarter bust at 45 degrees, complete head and hair through the upper chest. The nose points toward the LEFT edge. Both eyes visible with the farther eye foreshortened; not a front or strict profile view.'),
    'face_back': ('rear portrait', 'One direct rear bust, complete back of head and hair through the upper chest. No face or eyes visible; do not turn the head.'),
    'body_front': ('full-body front', 'One full-body front view in a neutral standing pose. Include the complete head through both feet or footwear, with empty space above the head and beneath the soles.'),
    'body_left': ('full-body anatomical left profile', 'One strict anatomical left-profile full-body neutral standing view. Nose, chest and toes point to the RIGHT edge of the sheet. Include the complete head through feet or footwear; preserve asymmetric clothing.'),
    'body_back': ('full-body back', 'One direct rear full-body neutral standing view. Include the complete head through feet or footwear. No face visible; do not turn the head.'),
    'clothing_front': ('clothing front', 'One front-facing clothing detail of the same character wearing the outfit. Crop from the base of the neck to the complete lowest garment edge. Keep the head outside the frame and retain naturally visible arms and hands.'),
    'clothing_back': ('clothing back', 'One direct rear clothing detail of the same character wearing the outfit. Crop from the base of the neck to the complete lowest garment edge. Keep the head outside the frame and retain naturally visible arms and hands.'),
    'hands': ('hands detail', 'One isolated close-up of exactly two complete hands, one left and one right, cropped at the wrists. No head, torso or whole figure.'),
    'feet': ('feet and footwear detail', 'One isolated close-up of exactly one left and one right complete foot or footwear, including visible boot shafts. Show enclosing shoe surfaces as continuous material, with skin only through existing openings. No head, torso or whole figure.'),
}
