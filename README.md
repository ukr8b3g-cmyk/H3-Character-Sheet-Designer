# H3 Character Sheet Designer

A standalone ComfyUI custom node for designing a multi-view character sheet and compiling an English MiniMax H3 reference prompt plus output dimensions.

- Six illustrated view selectors: portrait, full-body front, anatomical left profile, full-body back, hands, and footwear
- Four presets, automatic layout sizing, editable manual dimensions, and a large live layout preview
- Default **2208 × 1280** experimental layout; choose a 672-pixel panel height for **1344 × 768**
- Deterministic local Python compiler, with **no LLM, external API, additional model, or Python package dependency** for the designer itself
- One versioned JSON STRING input; `prompt: STRING`, `width: INT`, `height: INT` outputs
- Japanese interface when ComfyUI's language is Japanese; English for other languages

The bundled low-poly, bald, gender-neutral GPT Image mannequin artwork is displayed locally in the interface, with a simple SVG fallback only if the bitmap cannot load. These mannequins are interface illustrations only. They never become generation inputs. Coordinates in the prompt are semantic guidance, not hard image constraints. Identity, anatomy, unseen surfaces, clothing fidelity, exact geometry, and high-resolution generation quality are not guaranteed.

## Installation

Clone this repository into your ComfyUI `custom_nodes` directory:

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer.git
```

Restart ComfyUI and refresh its browser page. Add **H3 Character Sheet Designer** from the node menu. No `pip install` is required. Keep this repository as a custom-node folder; this is not a standalone image generator.

## Connect to native H3

Connect the Designer's `prompt`, `width`, and `height` outputs to the matching inputs on ComfyUI's native `MiniMaxH3ReferenceToVideo` node. Use **Convert widget to input** on the receiving node where necessary. Provide one character reference image separately, through Load Image, as the native node's first image reference (`<Picture 1>`). Use a compatible H3 Ref2VA model and your normal H3 model loading, sampling, decoding, and saving workflow.

Suggested experimental downstream settings are `length=5` **frames**, not five seconds, and `ref_image_size=match`. The Designer does not modify those settings. To save a still, choose a decoded frame downstream. Even at five frames, H3 uses its audiovisual model generation path; this is not a promise of ordinary still-model memory or speed.

## Using the designer

1. Select views or a preset. Every view click immediately commits the saved node input, even while the preview is loading
2. In Auto mode choose the requested full-body panel height. Dimensions are calculated in Python and rounded upward to a 32-pixel grid
3. To edit width and height, switch to Manual once the current preview has returned. The current Auto dimensions are copied first. Presets preserve Manual dimensions
4. Press Enter or leave a number field to commit a valid edit. Uncommitted drafts are not saved or queued
5. Queue your normal H3 workflow. Preview networking is optional for execution: the node independently validates and compiles the current saved JSON

The final view cannot be deselected. Face-only, hands-only, feet-only, left-profile-only, and hands-plus-feet layouts are supported. A missing or invalid saved value remains visible as an error; it is never silently reset. A failed preview can be retried without losing the committed selection.

**Experimental** appears above 1,032,192 pixels. This is a warning, not an artificial H3 size cap. ComfyUI's runtime axis limit is still enforced. Large outputs may require substantial VRAM and time.

## API and reproducibility

The only input is `state_json`:

```json
{"schema_version":1,"views":["face_front","body_front","body_left","body_back"],"size":{"mode":"auto","body_height":1120,"manual_width":2240,"manual_height":1280}}
```

The compiler rejects missing or unknown keys, duplicate JSON keys, unknown versions/views, empty selections, non-integer dimensions, non-32-grid values, oversize inputs, and values above ComfyUI's runtime maximum. View duplicates are normalized into a fixed order. Equivalent states generate identical English prompt bytes regardless of UI language or JSON formatting. Prompt text is not subject to dynamic prompt expansion.

The GUI uses same-server `POST /h3_character_sheet_designer/preview` with `{"state_json":"..."}`. This read-only endpoint performs no file writes, model execution, or external requests. Its response is advisory and never overwrites saved state. API/headless workflows do not call it.

## Tests and verification

```sh
# Development-only dependencies; not needed to use the custom node
python -m pip install -r requirements-dev.txt
npm install --ignore-scripts
python -m unittest discover -s tests -p 'test_*.py' -v
npm test
```

Node.js is needed only for developer tests, not installation or normal use. Without the optional development dependencies, standard-library Python and dependency-free JavaScript tests still run; HTTP/DOM tests explicitly report skips. `npm run test:js` runs the dependency-free frontend suite. To inspect the actual DOM renderer in a standalone browser harness:

```sh
python tests/serve_demo.py
# Open http://127.0.0.1:8765/tests/browser/
```

The harness uses the production compiler and UI renderer with a simulated ComfyUI boundary. It does **not** demonstrate ComfyUI installation, real frontend Undo/Redo, downstream queue acceptance, or GPU generation. See [verification details](docs/VERIFICATION.md) for tested and untested stages. Legacy frontends, Nodes 2.0, and unspecified ComfyUI versions are not claimed compatible. On unsupported DOM-widget environments, the node retains a standard STRING input and headless compilation.

## 日本語

ComfyUI用の独立ノードです。6種類のビュー、4つのプリセット、Auto／Manual寸法をGUIで選び、ネイティブH3へ渡す英文プロンプトと幅・高さを作ります。ComfyUIの言語設定が日本語の場合だけ日本語UIになります。

`custom_nodes` にcloneしてComfyUIを再起動してください。Designerの3出力を `MiniMaxH3ReferenceToVideo` に接続し、参照画像は別のLoad Imageから最初の画像参照へ渡します。H3モデルと通常の生成ワークフローは別途必要です。

既定値は2208×1280の実験的高解像度です。基準高を672にすると1344×768になります。画面のマネキンは操作用の図であり、生成用画像には送信しません。5フレーム設定も通常のH3 AV生成経路なので、軽量な静止画生成と同じ負荷ではありません。

詳細な入力契約と配置ルールは[日本語仕様書](docs/IMPLEMENTATION_SPEC_JA.md)、検証済み範囲と未検証事項は[検証記録](docs/VERIFICATION.md)をご覧ください。
