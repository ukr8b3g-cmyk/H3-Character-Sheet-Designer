# Verification record

Implementation verification dates: 2026-10-03 and 2026-10-04 (UI correction and pre-Phase-2 profile/footwear work). Tests run in the dot cloud workspace, without changing a user's ComfyUI installation.

## Scope

The test suites exercise the production Python compiler and frontend controller, and provide a browser harness that mounts the production DOM renderer and calls the production Python compiler through a local test HTTP server. The harness simulates the ComfyUI boundary. It is not a real ComfyUI frontend integration test. Browser execution was blocked in this workspace: Chromium could not create its required socket, and the supported cloud browser rejected localhost. These restrictions were respected; no real UI screenshots or browser pass are claimed.

## Automated results

- Python 3.12.14: **54 tests passed**, with no skips (aiohttp 3.13.5)
- Node.js 24.19.0: **48 tests passed**, with no skips (jsdom 30.1.1)
- Python compileall, JavaScript syntax checks, and `git diff --check`: passed
- Python layouts: every one of the 127 nonempty view combinations across 11 Auto/Manual configurations, plus all documented dimension examples
- Fifteen byte-exact English prompt snapshots, strict malformed JSON rejection, runtime Core limit changes, real aiohttp route/error/body-limit tests, and JS/Python semantic parity
- DOM simulation: immediate saved value, single named input at its original position, transaction calls, standard setter restoration, duplicate instances, locale changes, cleanup, invalid-state repair, numeric drafts, partial-install rollback, timeout/retry, and stale-response races
- Artwork: bundled PNG signature/dimensions/alpha channel, bounded atlas viewports, matching full-body viewport scales, and generated-raster-to-local-SVG fallback behavior

Run `python -m unittest discover -s tests -p 'test_*.py' -v` and `npm test` after installing the development-only dependencies in the README. Earlier checks reused a preinstalled jsdom via `H3_JSDOM_PATH`; the profile/footwear run used repository-installed jsdom. That optional path is not required when jsdom is installed in the repository. jsdom does not calculate browser layout or certify CSS appearance, zoom behavior, or ComfyUI compatibility.

## UI correction and supplied workflow check (2026-10-04)

- The supplied screenshot showed the height dropdown anchored to its separate 18-pixel arrow strip. The whole value field is now a native select; arbitrary 32-grid heights remain available through an explicit Custom entry
- Default node size is 870 × 930, matching the supplied workflow. The main font is 18px, key labels 16px, and supporting text 14px; disabled text retains stronger contrast. Larger existing sizes are preserved
- Both dropdowns, all four view presets, all six view buttons, Auto/Manual, custom Enter/blur/Escape, invalid drafts, locale changes, restoration and cleanup are covered by the DOM suite. CSS assertions prevent the tiny-dropdown dimensions from returning; they are not browser layout tests
- The supplied connected workflow has 18 consistent links. Designer node 15 sends prompt/width/height to native H3 node 5 through links 17/18/19. Its saved four-view state compiles locally to 2208 × 1280 with literal layout JSON braces
- In the official [frontend 1.53.6 graphToPrompt source](https://github.com/Comfy-Org/ComfyUI_frontend/blob/v1.53.6/src/utils/executionUtil.ts#L118-L155), resolved input links are written after widget serialization. This supports connected STRING passthrough in place of the older text retained in the native widget, but is not an observed Queue result
- Browser checks were attempted again: local Chromium could not create its required socket (`Operation not permitted`); the supported cloud browser rejected the localhost harness (`ERR_BLOCKED_BY_CLIENT`). No browser appearance, zoom, actual ComfyUI Queue, or GPU pass is claimed
- The browser harness now provides the requested node size and a 66.55% zoom toggle for manual checking when a supported browser environment is available

## Profile and footwear investigation (2026-10-04)

- The supplied UI screenshot was inspected as pixels. Footwear is selected and the illustration is present in the sheet preview. It does not show a generated H3 image, a current Queue payload, or the character reference
- No dropped-selection defect was reproduced locally: for every one of the 127 nonempty selections, an actual DOM button click is serialized immediately while preview is pending, reaches the Python compiler, appears in the layout, and yields byte-exact Designer STRING/INT outputs. The test uses a minimal Core limit stub, not the native H3 model or a real ComfyUI Queue
- The original six-view layout gives the footwear detail approximately 258 × 381 pixels at panel height 1120. That small region and the original combined feet/footwear wording are possible model-adherence factors, not verified causes. All 63 legacy six-view geometries are fixed by a baseline fixture and remain unchanged; an independent review also compared every legacy geometry under the 11 Auto/Manual configurations (693 exact comparisons). The original default JSON and every legacy prompt without a selected footwear panel remain byte-identical
- The selected-only prompt now requires a separate enlarged feet/footwear panel early in the summary and in the detail instructions. It conditionally preserves shoes, open-toed footwear, visible boot shafts, or bare feet. It does not request exposed toes through closed shoes, a footwear redesign, or unseen construction. This is a prompt repair candidate; no improvement in GPU adherence is claimed
- `face_left` is optional and uses anatomical-left head-to-chest wording. The original four-view default and schema remain valid. Detail now selects seven views; saved six-view states are preserved and labeled Custom. A second portrait adds one column only when both portraits are selected. Manual dimensions remain fixed
- All 127 selections have JS/Python state parity and all 1,397 layout configurations have positive, bounded, non-overlapping panels. Tests cover immediate profile persistence, restoration, Auto-to-Manual copying, Japanese/English labels, seven accessible buttons, and the raster/fallback artwork for every view
- The anatomical-left portrait is a bounded head-to-chest viewport from the existing approved GPT Image PNG. Static SVG viewport renders were inspected on light and dark backgrounds; the original atlas is unchanged. This is artwork QA, not a screenshot of browser layout
- The inspected [native H3 tokenizer](https://github.com/Comfy-Org/ComfyUI/blob/f1072eb0350638a3390ddb6afbcaa8c6b237c6fd/comfy/text_encoders/minimax.py#L147-L196) appends the supplied prompt after reference labels/vision entries and disables token-weight syntax. This source review supports text transport, not the user's installed version, received prompt, matching model family, or model compliance

To establish the actual failure, retain the failing output, source reference, current saved workflow/API inputs, installed versions, and exact model identity. Check whether both feet and footwear are visible in the reference, whether the native node receives the current `feet` panel instruction, and whether the loaded model supports that native conditioning path. Neither a UI preview nor a model filename alone settles these questions. Do not switch models, resolutions, or prompts during a controlled comparison.

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
6. Open both dropdowns by clicking the displayed value and select each option. At 870 × 930 and the supplied canvas zoom, inspect popup width, text, disabled dimensions and all view buttons; repeat in Japanese. Then connect the three output slots to native `MiniMaxH3ReferenceToVideo`. Confirm literal prompt braces arrive intact and width/height match the current compiler result
7. Before GPU execution, inspect Export (API) or an intercepted `/prompt` payload: the native node's connected inputs must reference the Designer output slots, not retain the native widget's older text. This payload check alone does not confirm the backend-received compiler string
8. With a single reference image and H3 Ref2VA model, test a 672-height baseline and the default 1120-height experimental layout, `length=5`, `ref_image_size=match`
9. Separately record structural pass, queue pass, successful GPU generation, and observed image quality. Inspect identity, anatomical side, footwear/gloves, exact selected views, and layout adherence
10. Add the optional left portrait, test it alone and with the front portrait, and check true anatomical-left orientation. For footwear, compare the same reference/seed/settings before and after the prompt change: separate panel present, both feet, same shoe or bare-foot state, visible boot shafts, no shoe redesign. Record omission separately from incorrect footwear.
11. Repeat applicable frontend checks independently for legacy UI and Nodes 2.0; do not infer their support from the classic harness
