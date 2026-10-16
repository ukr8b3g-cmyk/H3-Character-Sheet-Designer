# Mannequin artwork

The seven existing views keep the original `mannequin-atlas.png` unchanged.
Six additional illustrations use `mannequin-multi-atlas.png`, made with the
dedicated GPT Image tool using that original atlas as the visual reference.
They match its gray faceted low-poly mannequin finish. The earlier procedural
polygon sketches have been removed.

The new atlas contains right-profile, left/right three-quarter and rear busts,
plus headless front/back whole-outfit coverage figures. The clothing figures
indicate a region of a worn outfit; their body silhouette does not select a
shirt, skirt, dress or trouser design.

`tools/extract_extra_artwork.py` only extracts the six bitmap cells, adds crop
padding, and removes near-transparent encoding noise. It does not synthesize
images, draw geometry, recolor facets or modify the original atlases. Production
assets are local PNGs; neither the interface nor workflow calls an image service.
The same PNGs appear in selection cards and in the optional layout guide.
