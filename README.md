# H3 Character Sheet Designer

Implementation planning for a standalone ComfyUI custom node that designs a multi-view character sheet and compiles its selection into an English MiniMax H3 reference prompt plus output dimensions.

**Status: specification only. No installable node or runtime implementation is included yet.**

## Planned behavior

- Six graphical view selectors: front portrait, full-body front, anatomical left profile, full-body back, hands, and feet/footwear
- Four presets, automatic width growth with a fixed requested full-body panel height, and editable manual dimensions on a 32-pixel grid
- Default high-resolution layout: 2208 × 1280, marked experimental; a lower 1344 × 768 option remains available
- Local deterministic Python compiler; no LLM, external service, or additional model dependency for the designer itself
- One versioned JSON STRING input; `prompt: STRING`, `width: INT`, and `height: INT` outputs for the native `MiniMaxH3ReferenceToVideo` node
- Japanese UI when ComfyUI selects Japanese; English otherwise

The graphical mannequins are UI illustrations only. Layout coordinates are semantic prompt instructions, not hard image constraints. Exact identity, panel geometry, unseen anatomy, clothing fidelity, and high-resolution generation quality cannot be guaranteed. Generation still requires an appropriate H3 model and the normal ComfyUI generation workflow.

See the [Japanese implementation specification](docs/IMPLEMENTATION_SPEC_JA.md) for state, layout mathematics, persistence, failure behavior, and acceptance tests.

## 日本語

ComfyUI用の独立カスタムノード「H3 Character Sheet Designer」の実装計画です。ビューを図で選び、ネイティブH3参照ノードへ渡す英文プロンプト・幅・高さを決定します。

**現在は仕様書のみです。インストール可能なノードや製品コードはまだ含まれていません。**

既定の高解像度は2208×1280で、Experimental扱いです。低負荷向けの1344×768も選択できます。Autoは全身枠の指定高さを維持して幅を変え、Manualはビュー変更でも入力寸法を維持します。UIの疑似3Dマネキンは生成用画像として送信しません。

保存・即時Queue・Undo／Redo・API・Nodes 2.0の互換性は実装後の試験項目です。未実装のため、動作確認済みとはしていません。詳細は[初版実装仕様](docs/IMPLEMENTATION_SPEC_JA.md)をご覧ください。
