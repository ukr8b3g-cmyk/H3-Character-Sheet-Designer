# H3 Character Sheet Designer

[日本語](#日本語) · **v1.3** (node/package version `1.3.0`)

Create character reference sheets with native MiniMax H3 image-reference conditioning. One character image and up to three optional part references are passed through unchanged. Select up to 13 views: six head views, three full-body views, front/back clothing, paired hands and paired feet/footwear.

## What's New — v1.3

- **New:** two versioned nodes: **H3 Character Sheet Designer v1.3.0** and the previous **v1.2.2**. Use v1.3.0 for this release's changes.
- **New:** MOSS-style preset order, including **7 views · hands and feet**. Seven-view layout has two portraits stacked on the left, three bodies in the center, and hands above feet at the far right.
- **Updated:** one common guide/layout for ON and OFF. Both display the same arrangement and dimensions. **Use Layout Image** controls whether the guide is passed to H3; OFF still outputs `None` for the guide image.
- **Updated:** smaller guide margins/gaps and wider Auto full-body columns so the figure can reach the requested panel height without changing its proportions. Auto output width/pixel count can grow, increasing time and VRAM use. Manual keeps the specified canvas size.
- **Updated:** compact controls and Settings tab; remove the Worn/Garments-only UI switch. Clothing shape retains Auto / Pants / Skirt or robe. V1.3 normalizes saved Worn values to garment extraction.
- **Small prompt adjustments:** clothing uses extraction, `No human`, and flat-outfit instructions scoped to clothing panels. Clothing-only output retains outfit features rather than person identity. **Clothing and all-13 results have not demonstrated a major general improvement.** Human remnants, missing/duplicate views and outfit/full-body confusion remain possible.
- **New template:** supplied v1.3 subgraph workflow with four character/part images and eight Designer outputs. Uses Hybrid V4, H3 INT8 TE and Pika Ref2VA; existing node titles are preserved.

See [release notes](docs/releases/v1.3.0.md) and [CHANGELOG](CHANGELOG.md). Previous changes remain recorded there.

## Start here

1. Update/install this node pack, restart ComfyUI, and reload the browser (Ctrl+F5).
2. Open **[H3_Character_Sheet_Designer_v1.3.json](workflows/H3_Character_Sheet_Designer_v1.3.json)**. [Release download](https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer/releases/download/v1.3.0/H3_Character_Sheet_Designer_v1.3.json).
3. Select installed models and valid images in every connected Load Image node. Disconnect unused optional inputs on the Designer. Models/images are not bundled.
4. Choose views and optional part instructions/reference roles. Auto retains unspecified reference appearance. Fix the seed for comparisons.
5. Start with **Use Layout Image OFF**, enabling it when composition guidance helps. ON can transfer guide proportions or leave guide content. The UI displays the same guide either way.

The template requires native ComfyUI H3/subgraph support and **[rgthree-comfy](https://github.com/rgthree/rgthree-comfy)** for Power LoRA Loader. The Designer adds no Python runtime dependency. Pika Ref2VA is enabled at 1.0, FL2VA is disabled, and ManualSigmas has eight intervals. These are the supplied comparison settings, not a universal optimum or the original Pika six-NFE sampling contract. Keep the supplied save format unless you intentionally change it.

<img width="1288" height="864" alt="{ADFF3198-407B-4693-A454-F8ED0E0A625F}" src="https://github.com/user-attachments/assets/8478a706-620c-42e2-a13b-068fe601f0b3" />

<img width="1191" height="803" alt="{E6449818-9833-48BF-ABB4-78E75C593EED}" src="https://github.com/user-attachments/assets/c56b09f1-f5bc-41da-84cc-18da76556691" />

## Models and downloads

Set the CLIP loader type to **`minimax`** and select an **H3** encoder. Music3 encoders are incompatible and cause sampler matrix-shape errors (for example 32768 versus 5120). Model switching/first loading is separate from layout compilation.

| Component | Download / filename | Folder under models/ |
| --- | --- | --- |
| Diffusion / template | [DaSiWa Hybrid V4 INT8](https://civitai.red/models/2877206/dasiwa-minimax-h3?modelVersionId=3391862) — `DasiwaMinimaxH3_dasiwaHybridV4_int8.safetensors` | `diffusion_models/minimax/` |
| Native alternative | [H3 Ref2VA INT8](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/diffusion_models/minimax_h3_ref2va_pruned_int8_convrot.safetensors) — `minimax_h3_ref2va_pruned_int8_convrot.safetensors` | `diffusion_models/` |
| Text encoder / CLIP | [H3 Qwen3-VL INT8](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_int8_convrot.safetensors) — `qwen3vl_32b_minimax_h3_int8_convrot.safetensors` | `text_encoders/` |
| Alternative encoder | [H3 NVFP4 AWQ](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/text_encoders/qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors) — `qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors` | `text_encoders/` |
| Video VAE | [H3 VAE INT8](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_int8_convrot.safetensors) — `minimax_h3_video_vae_int8_convrot.safetensors` | `vae/` |
| Alternative VAE | [H3 VAE FP16](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/vae/minimax_h3_video_vae_fp16.safetensors) — `minimax_h3_video_vae_fp16.safetensors` | `vae/` |
| Pika LoRA / enabled | [Ref2VA](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/loras/pika_h3_flex_ref2va_v1_bf16.safetensors) — `pika_h3_flex_ref2va_v1_bf16.safetensors` | `loras/minimax/` |
| Pika LoRA / disabled | [FL2VA](https://huggingface.co/Comfy-Org/MiniMax-H3/resolve/main/loras/pika_h3_flex_fl2va_v1_bf16.safetensors) — `pika_h3_flex_fl2va_v1_bf16.safetensors` | `loras/minimax/` |

Choose the adapter matching your base model and conditioning path. Both Pika links are provided; this template enables Ref2VA only. Follow model licenses/access requirements. The `minimax/` subfolder is template organization, not a required ComfyUI convention.

## Wiring and reference roles

| Designer output | Native H3 input |
| --- | --- |
| `prompt`, `width`, `height` | matching prompt/dimension inputs |
| `character_image` | `ref_images.ref_image_0` |
| `layout_image` | `ref_images.ref_image_1` |
| `reference_image_1` / `2` / `3` | `ref_images.ref_image_2` / `3` / `4` |

Keep the guide wire connected when OFF. Picture numbering skips None images. The four image pass-through outputs retain the input tensors unchanged. The template samples five frames and saves the first decoded frame as the static sheet.

In Part prompts assign extra references to Same character, Face, Head/face/hair, Complete outfit, Outfit front/back, Hands or Footwear. Explicit choices and part instructions take priority, then dedicated references, then the baseline image; later dedicated references of the same role take priority. These are text-based permissions, not regional attention isolation. Separate panel descriptions and `No human` do not guarantee that instructions stay inside one panel.

## Which node / previous workflows

| Node ID / display version | Purpose |
| --- | --- |
| `H3CharacterSheetDesignerReferenceV13` / **v1.3.0** | Current workflow and common guide |
| `H3CharacterSheetDesignerReference13` / **v1.2.2** | Previous behavior for existing Reference13 workflows / comparison |

These are the **two registered nodes**. Earlier Designer, Reference, Multi Reference and Reference V1.1 IDs are not registered in v1.3. Their historical source/workflow files and [old releases](https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer/releases/tag/v1.2.2) remain available; use an earlier release if those IDs are required. Saved workflows and user node titles are not automatically rewritten. V1.2.2 preserves its compiler/state behavior; its shared UI also has the Worn switch removed.

## Limits and validation

- Clothing/all-13 receive small targeted changes, not a demonstrated major visual-quality upgrade. Human remnants, missing/duplicate angles and outfit/body confusion remain possible across photo, anime, CG and seeds.
- Native image references do not guarantee exact identity, unseen surfaces, garment fidelity, viewpoints, view count or geometry. Guides can affect anatomy or be copied.
- Tighter margins and larger guide figures are geometric changes, not proof of GPU quality improvement. Increased Auto width can cost time/memory; Manual can remain width-limited.
- No additional LLM, TE text-generation step, hard BREAK separation or independently encoded regional conditioning was introduced.
- Packaged compiler/UI tests, guide parity, image pass-through and template wiring are checked separately from GPU quality. Earlier GPU comparisons included failures; final changes have no controlled multi-reference/seed success-rate, VRAM or speed benchmark. User functional confirmation is separate from that evaluation.

## Installation and updates

```sh
cd ComfyUI/custom_nodes
git clone https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer.git
```

Update existing installations through your usual Git/Manager workflow, restart ComfyUI, and reload the browser. Model weights are separate downloads. Registry/Manager publication is a separate operation and is not included here.

<img width="2816" height="1280" alt="comfy_minimax_h3_fl2va_pruned_int8_convrot_20261004191840_00001_" src="https://github.com/user-attachments/assets/2265b1fd-3fc8-4331-b0db-5003621bf0b5" />

## 日本語

**v1.3（ノード／パッケージ表記は1.3.0）**。MiniMax H3本来の画像参照でキャラクターシートを生成します。人物画像1枚＋部位参照3枚をそのまま受け渡し、必要なら配置画像を追加参照にします。MOSS版の画像→文章化とは異なる方式です。

### v1.3の変更点 / What's New

- **New：** 今回版 **H3 Character Sheet Designer v1.3.0** と前版 **v1.2.2** の2ノードへ整理。今回の変更にはv1.3.0を使用します。
- **New：** MOSS版と同じプリセット順へ整理し、手・足付き7ビューを追加。頭部2面を左で上下、全身3面を中央、手を右上・足を右下へ配置します。
- **更新：** ON/OFFのガイドを1種類に統一。配置・寸法は同じで、Use Layout Imageは生成へガイド画像を渡すかだけを切り替えます。OFFの画像出力はNoneです。
- **更新：** ガイドの外周余白・枠間を縮小し、Autoの全身列を指定高まで描ける横幅へ拡張。縦横比を保持します。出力幅・画素数が増える場合があり、時間・VRAM負荷も増える可能性があります。Manualの指定サイズは保持します。
- **更新：** コンパクトな操作欄とSettingsタブ。Worn/Garments only切替を削除し、衣装型のAuto／Pants／Skirt or robeは維持。今回版の古いWorn保存値は衣服抽出として処理します。
- **小修正：** 衣装前後を抽出・No human・flatの短い文へ組み直し、衣装枠に適用。衣装単独の全体文も人物保持から衣服抽出へ整理しました。**衣装・全13面は汎用的な大幅改善を確認できていません。** 人物・身体の残留、向きの重複・欠落、衣装と全身の混同は残ります。
- **New：** 今回提示されたサブグラフ型ワークフローをテンプレートに採用。4画像入力・Designerの8出力と既存ノードtitleを保持。モデルは既定方針どおりHybrid V4／H3用INT8 TE／Pika Ref2VAへ整合しました。

[リリースノート](docs/releases/v1.3.0.md)・[変更履歴](CHANGELOG.md)も参照してください。

### 使い方

1. 更新後にComfyUIを通常再起動し、ブラウザーをCtrl+F5で再読込。
2. [v1.3テンプレート](workflows/H3_Character_Sheet_Designer_v1.3.json)を開き、導入済みモデルを選択。接続したLoad Imageすべてに有効な画像を指定するか、使わない追加参照入力をDesignerから外します。
3. ビュー・部位指示・参照の役割を設定。Autoは参照の外見を保つ選択です。比較時はseedを固定します。
4. Use Layout ImageはOFFから試し、配置の補助が必要ならONへ。画面のガイドは共通で、ONだけが画像をH3へ渡します。ONではガイドの体形・図が残る場合があります。

配線は上の表と共通です。人物→ref_image_0、配置画像→1、追加参照3枚→2/3/4。NoneはPicture番号から除外。画像Tensorは変更せず返します。5フレームを生成し、最初の復号フレームを静止画として保存します。

テンプレートは[rgthree-comfy](https://github.com/rgthree/rgthree-comfy)が必要です。Pika Ref2VAは強度1.0で有効、FL2VAは無効、ManualSigmasは8区間。今回の比較設定であり万能な最適値やPika本来の6-NFE契約を保証するものではありません。保存形式は必要に応じて利用者が変更してください。

### モデルと参照の注意

モデル／TE／VAE／LoRAのファイル名・URLは上の **Models and downloads** 表にまとめています。Pika Ref2VA／FL2VA両方のリンクを掲載し、このテンプレートはRef2VAだけを有効にしています。CLIPローダーはtype=minimax、H3用Qwen3-VLを使用。Music3用TEは非互換で行列サイズ不一致になります。初回ロードの時間とDesignerの配置計算は別の処理です。各モデルのライセンス・アクセス条件に従ってください。

追加参照の役割は同一人物／顔／頭部・髪／衣装全体／衣装前／衣装後／手／履物。明示設定・部位指示、専用参照、基準画像の順に適用し、同じ専用役割では後の接続を優先します。これはテキスト上の指示であり、領域attentionを完全分離する機能ではありません。

### 新旧ノードと残る制約

登録は今回版v1.3.0と前版v1.2.2の2つです。前版Reference13の生成動作・状態契約は保持しますが、共有UIのWorn切替は撤去しています。それより前のDesigner／Reference／Multi Reference／V1.1のIDが必要なら[旧リリース](https://github.com/ukr8b3g-cmyk/H3-Character-Sheet-Designer/releases/tag/v1.2.2)を使用してください。旧ファイル・Releaseは履歴として残し、保存済みワークフローやユーザーのノード名は自動変更しません。

衣装・13面は小修正で、人物除去・向き・枚数・同一性の大幅改善を実証した版ではありません。写真・アニメ・CG、別seedでは失敗が残ります。ガイドの幾何改善もGPU画質向上の証明ではありません。Auto幅の拡大は時間・VRAM負荷を増やす場合があります。追加LLM、TE文章生成、BREAKによる分離、領域別エンコードは導入していません。

CPU／UI／配線の確認とGPU評価を区別しています。ユーザーの動作確認はありますが、最終変更の複数参照・複数seedでの成功率、VRAM、速度の比較評価は未完了です。今回の公開にはRegistry／Manager登録を含めません。

<img width="1325" height="646" alt="{A223588C-EEB3-453F-8654-B27084426E4D}" src="https://github.com/user-attachments/assets/519bd600-f0cd-408c-8d30-8181a83d8b0a" />

## Credits / License

Keep [LICENSE](LICENSE), [NOTICE.md](NOTICE.md) and [artwork attribution](docs/MANNEQUIN_ARTWORK.md). Model licenses apply separately.
