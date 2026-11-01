# What's New / Changelog

## v1.3.0

- Add the V1.3 node; keep previous v1.2.2 Reference13. Remove older menu registrations while retaining historical files/releases.
- Align MOSS presets and add seven views: portraits left, bodies center, hands/feet far right.
- Share the guide/layout between ON and OFF; OFF still passes no guide image. Reduce margins and enlarge Auto body columns for requested height; Auto width/time/VRAM can increase.
- Compact UI, Settings tab, Worn switch removal and clothing shape Auto retained.
- Small clothing/all-13 prompt adjustments: extraction / No human / flat, scoped to clothing panels. No major general quality improvement is claimed; human remnants, missing/duplicate views and outfit/body confusion remain possible.
- Add supplied v1.3 subgraph template with Hybrid V4, H3 INT8 TE and Pika Ref2VA. Preserve node titles; document both Pika LoRA URLs.
- Preserve four-image pass-through and eight outputs. No new LLM, TE generation or hard regional prompt separation.

### 日本語
v1.3ノード／テンプレート、MOSS準拠プリセットと7面、共通ガイド、余白・全身列、UIを更新。衣装・13面は小修正で、大幅改善は未確認。前版Reference13と旧ファイル／Releaseを保持。Auto幅増加の時間・VRAM負荷等をREADMEへ明記。詳細は[リリースノート](docs/releases/v1.3.0.md)。


## v1.2.2

- Fix stale part and numeric drafts after successful Apply JSON in standard and Reference13 UIs.
- Preserve invalid input, IME behavior, existing UI, node contracts, saved states and workflows.
- Add 14 DOM regressions; CPU 157 and JavaScript/DOM 108 pass locally.
- 通常版・Reference13版のApply JSON後の下書き同期を修正。既存UI・保存互換性を維持。

## v1.2.1

- Align dedicated Reference13 roles with scoped retention, panel instructions and priority.
- Validate Batch Out previews against real individual outputs.
- Add Reference13 DOM serialization/lifecycle and CPU/JS boundary regressions.
- Preserve existing node IDs, state schemas, workflows and runtime dependencies.

## v1.2.0

### Added
- Reference13 node: 13 selectable views and up to four same-character images.
- Reference-relative clothing, worn/garment-only, hand and footwear choices with scoped part directives.
- Four-image GUI template with external RandomNoise and accessible fixed/randomize control.
- Multi Reference and Reference V1.1 workflows, including V1.1 independent-view Batch Out and adaptive Manual layout.

### Compatibility
- Retain all four previous node IDs and existing workflow files. No automatic replacement or deletion.
- Reference13 reads legacy schema 1/2 states. Reference13 schema 3 is separate from Multi Reference schema 3.
- Image port ordering, true Layout OFF bypass and existing model choices are preserved.
- Preserve upstream LICENSE, NOTICE.md and Comfy Registry PublisherId.

### Known limits
- Layout OFF uses text instructions, not a hard geometry constraint. Clothing crops, panel count and detail placement may vary.
- The experimental 2:3 clothing regions were reverted. The prior full-height allocation is retained.
- No general GPU-quality, speed, VRAM or cross-model success claim is made.

### 日本語
Reference13と4画像テンプレートを追加します。Seed固定／ランダム化はサブグラフ外から操作できます。旧4ノードと旧ワークフローは残します。互換性は旧ノードでの継続利用であり、新旧の無変更の置き換えを意味しません。Layout OFFでの衣装・全13ビューの制約は残ります。

## Previous versions

The original Designer and Reference workflows remain bundled. Local Multi Reference and Reference V1.1 work is included in this release; no separate published v1.1.0 release is asserted here. Existing tags, releases and assets must be retained when publishing a new version.
