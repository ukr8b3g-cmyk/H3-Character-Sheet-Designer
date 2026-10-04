# Verification record

Implementation verification date: 2026-10-03. Tests run in the dot cloud workspace, without changing a user's ComfyUI installation.

## Scope

The test suites exercise the production Python compiler and frontend controller, and provide a browser harness that mounts the production DOM renderer and calls the production Python compiler through a local test HTTP server. The harness simulates the ComfyUI boundary. It is not a real ComfyUI frontend integration test. Browser execution was blocked in this workspace: Chromium could not create its required socket, and the supported cloud browser rejected localhost. These restrictions were respected; no real UI screenshots or browser pass are claimed.

## Automated results

- Python 3.12.14: **50 tests passed**, with no skips (aiohttp 3.13.5)
- Node.js 24.19.0: **36 tests passed**, with no skips (jsdom 30.1.1)
- Python compileall, JavaScript syntax checks, and `git diff --check`: passed
- Python layouts: every one of the 63 nonempty view combinations across 11 Auto/Manual configurations, plus all documented dimension examples
- Eleven byte-exact English prompt snapshots, strict malformed JSON rejection, runtime Core limit changes, real aiohttp route/error/body-limit tests, and JS/Python semantic parity
- DOM simulation: immediate saved value, single named input at its original position, transaction calls, standard setter restoration, duplicate instances, locale changes, cleanup, invalid-state repair, numeric drafts, partial-install rollback, timeout/retry, and stale-response races
- Artwork: bundled PNG signature/dimensions/alpha channel, bounded atlas viewports, matching full-body viewport scales, and generated-raster-to-local-SVG fallback behavior

Run `python -m unittest discover -s tests -p 'test_*.py' -v` and `npm test` after installing the development-only dependencies in the README. The verification environment reused a preinstalled jsdom via `H3_JSDOM_PATH`; this optional path is not required when jsdom is installed in the repository. jsdom does not calculate browser layout or certify CSS appearance, zoom behavior, or ComfyUI compatibility.

## Artwork inspection

The primary artwork is the final user-requested faceted low-poly, blank-faced, bald mannequin with abstract foot volumes. It is a locally bundled [GPT Image PNG atlas](../web/assets/mannequin-atlas.png), not a runtime image-service request. It was inspected against light and dark backgrounds. SVG is used only as a lossless bitmap viewport and a simple fallback when the local image cannot load. Full-body viewports use the same width and height to preserve a consistent illustrative scale. Asset inspection is not a screenshot or browser-layout test of the ComfyUI widget.

## Not verified

- Installation and widget persistence inside an actual released ComfyUI frontend
- Real ComfyUI graph Undo/Redo, graph-to-prompt serialization, and native H3 downstream Queue
- Native H3 model loading, GPU generation, image quality, and VRAM requirements
- Legacy frontend and Nodes 2.0 compatibility

No minimum supported frontend version is claimed until it has been tested inside that frontend. The standard STRING fallback and compiler remain available independently of the graphical interface. Browser harness checks do not establish compatibility with all frontend releases.

## Manual acceptance checklist for a model-equipped ComfyUI environment

1. Record ComfyUI commit, frontend version, browser version, model identifier, and available VRAM
2. Add the node, use each preset, Save and reload, duplicate, and create multiple independent instances
3. Click a view and immediately Save, export API JSON, and Queue. Confirm `inputs.state_json` has that click's committed selection
4. Exercise Undo/Redo with requests in flight, repeated A→B→A selection, graph reload, and deletion
5. Change ComfyUI locale ja→en and ensure labels change without modifying the saved JSON or adding an Undo entry
6. Connect the three output slots to native `MiniMaxH3ReferenceToVideo`. Confirm literal prompt braces arrive intact and width/height match the current compiler result
7. With a single reference image and H3 Ref2VA model, test a 672-height baseline and the default 1120-height experimental layout, `length=5`, `ref_image_size=match`
8. Separately record structural pass, queue pass, successful GPU generation, and observed image quality. Inspect identity, anatomical side, footwear/gloves, exact selected views, and layout adherence
9. Repeat applicable frontend checks independently for legacy UI and Nodes 2.0; do not infer their support from the classic harness
