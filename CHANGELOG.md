# What's New / Changelog

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
