import {VIEW_IDS, PART_IDS, PART_PROMPT_MAX_LENGTH, PRESETS, V13_PRESETS, IMAGE_RESOLUTION_PROFILES, presetOf, StateError} from './reference13_state.js';
import {createArtwork, createGuideArtwork} from './reference13_artwork.js';
import {MULTI_VIEW_IDS, MULTI_PRESETS, REFERENCE_INPUTS, REFERENCE_ROLES, SETTINGS, DEFAULTS, MULTI_MIRRORED_VIEWS} from './reference13_state.js';
let sequence = 0;
export const HEIGHT_PRESETS = [672, 896, 1120, 1344, 1792];
export const STYLE_IDS = ['none', 'anime', 'photo', 'realistic_painting', 'semi_realistic_anime', 'oil_painting', 'watercolor', 'gouache', 'colored_pencil', '3d'];
const EN = {
  intro: 'Choose the views for your character sheet', selected: 'selected',
  face_front: 'Portrait', face_left: 'Left portrait', body_front: 'Front', body_left: 'Left side', body_back: 'Back', hands: 'Hands', feet: 'Footwear',
  face_front_tip: 'Front-facing face to chest', face_left_tip: 'Head to chest, camera facing the subject’s anatomical left side', body_front_tip: 'Full body, head to soles', body_left_tip: "Camera looks directly at the subject’s anatomical left side", body_back_tip: 'Direct rear view, full body', hands_tip: 'Both hands; retain gloves from the reference', feet_tip: 'Separate close-up of both feet in reference footwear; visible boot shafts retained',
  preset: 'Preset', five: 'Standard · 5 views', basic: 'Basic · 4 views', detail: 'Detail · 7 views', turnaround: 'Turnaround · 3', single: 'Single view', seven: '7 views · hands and feet', custom: 'Custom',
  auto: 'Auto', manual: 'Manual', size: 'Output size', bodyHeight: 'Panel height', width: 'Width', height: 'Height', returnAuto: 'Back to Auto', updating: 'Updating dimensions…',
  resolution: 'Resolution', resolution_current: 'Current', resolution_high: 'High detail', resolution_max_8mp: '8 MP', resolution_max_16mp: '16 MP',
  resolutionProfile: 'Select a valid resolution.', resolutionHint: 'Current uses panel height. High detail increases pixel count toward 8 MP. Choose 8 MP or 16 MP to set the canvas area directly.',
  imageResolutionWarning: 'This canvas exceeds 16 MP.',
  customHeight: 'Custom panel height', customHeightChoice: 'Custom…',
  autoHint: 'Auto keeps the requested full-body panel height.', manualHint: 'Manual keeps your canvas size when views change.',
  layout: 'SHEET PREVIEW', diagram: 'Layout guide', experimental: 'Experimental', pixels: 'pixels',
  caveat: 'A prompt layout guide. Exact geometry and generation quality are not guaranteed.',
  resolutionWarning: 'High resolution is experimental. This inherited display threshold is not a H3 quality or VRAM limit.',
  committed: 'Saved immediately', pending: 'Updating layout…', stale: 'Previous layout · updating', previous: 'Previous layout', unavailable: 'Preview unavailable', retry: 'Retry preview', empty: 'Waiting for Python layout',
  draft: 'Uncommitted values are not saved or queued.', invalid: 'Saved JSON is invalid. Its original value is preserved.', editJSON: 'Repair saved JSON', apply: 'Apply valid JSON', rawHint: 'Only Apply changes the saved input.',
  lastView: 'Keep at least one view selected.', sizeError: 'Enter a whole number of at least 32, in steps of 32.', maxSize: 'Exceeds the ComfyUI resolution limit.', integer: 'JSON integer fields cannot use decimal or exponent notation.', version: 'Only schema_version 1 or 2 is supported.', views: 'Select one or more of the seven known view IDs.', json: 'The JSON syntax is invalid.', duplicateKey: 'Duplicate JSON key', keys: 'Unknown or missing JSON keys', oversize: 'JSON must be no larger than 64 KiB.', mode: 'Size mode must be auto or manual.', object: 'Expected a JSON object', string: 'state_json must be a string.', preview: 'The server returned an invalid preview.', timeout: 'Preview timed out. The saved selection is unchanged.', network: 'Could not reach the preview endpoint. Queue still validates on the server.',
  fallback: 'Graphical designer unavailable. Edit the normal state_json string; Python compilation is still available.',
  layoutTab: 'Layout', partsTab: 'Part prompts', part: 'Body part', partPrompt: 'Prompt', partCount: 'parts specified',
  generatedPrompt: 'Generated prompt', characterOnly: 'Optimized original Designer prompt · Picture 1 only · layout reference bypassed', layoutReference: 'Picture 1: character / Picture 2: layout',
  styleTab: 'Style', style: 'Style', clearStyle: 'Clear', styleHint: 'Changes rendering only. Keeps the reference character, outfit, accessories and colors, except for your part prompts. Applies to all selected views.',
  styleUnavailable: 'Restart ComfyUI and reload the page to enable the style input.',
  style_none: 'None · default', style_anime: 'Anime', style_photo: 'Photo', style_realistic_painting: 'Realistic painting', style_semi_realistic_anime: 'Semi-realistic anime', style_oil_painting: 'Oil painting', style_watercolor: 'Watercolor', style_gouache: 'Gouache', style_colored_pencil: 'Colored pencil', style_3d: '3D CG',
  style_none_tip: 'Adds no style instruction.', style_anime_tip: 'Anime linework and cel shading.', style_photo_tip: 'Photographic surface rendering.', style_realistic_painting_tip: 'Realistic forms rendered as a painting.', style_semi_realistic_anime_tip: 'Anime linework with softly modeled shading; keeps reference proportions.', style_oil_painting_tip: 'Oil-painted brushwork.', style_watercolor_tip: 'Pigment washes with clear contours.', style_gouache_tip: 'Opaque painted color fills.', style_colored_pencil_tip: 'Colored-pencil strokes and shading.', style_3d_tip: 'Three-dimensional surface shading.',
  partPlaceholder: 'Describe colors, shapes, patterns, text, or placement freely.',
  partHint: 'One instruction per part, shared across related selected views. Leave blank to follow the reference.',
  partSaved: 'Saved as you type. Enter adds a new line.', partGuide: 'The layout guide uses mannequins; it does not visualize these instructions.',
  head_hair_part: 'Head / hair', face_part: 'Face', upper_clothing_part: 'Upper-body clothing', back_clothing_part: 'Back of clothing', lower_body_part: 'Lower body', hands_part: 'Hands / gloves', footwear_part: 'Feet / footwear', other_part: 'Overall / other',
  partText: 'Each part prompt must be a string.', parts: 'Unknown body part.', partLength: 'Keep each prompt within 1000 characters; some symbols count as more than one.', partUnicode: 'The prompt contains invalid Unicode.',
  undoWarning: 'This frontend does not expose the expected Undo transaction API.',
};
const JA = {
  intro: 'キャラクターシートに使うビューを選択', selected: '選択中',
  face_front: '顔・胸', face_left: '横顔・左', body_front: '全身正面', body_left: '左側面', body_back: '全身背面', hands: '両手', feet: '足・履物',
  face_front_tip: '正面の顔から胸まで', face_left_tip: '人物の解剖学的左側から見た横顔。髪全体から胸まで', body_front_tip: '頭頂から靴底までの全身正面', body_left_tip: 'カメラが人物の解剖学的左側を正面から見る', body_back_tip: '真後ろから見た全身', hands_tip: '左右の手。参照にある手袋を保持', feet_tip: '両足の独立した拡大図。参照の履物と見えているブーツの筒を保持',
  preset: 'プリセット', five: '標準5ビュー', basic: '基本4面', detail: '7面・ディテール', turnaround: '三面図のみ', single: '1カット', seven: '7ビュー・手と足', custom: 'カスタム',
  auto: 'Auto', manual: 'Manual', size: '出力サイズ', bodyHeight: '基準高', width: '幅', height: '高さ', returnAuto: 'Autoに戻す', updating: '寸法更新中…',
  resolution: '解像度', resolution_current: '現行', resolution_high: '高精細', resolution_max_8mp: '8 MP', resolution_max_16mp: '16 MP',
  resolutionProfile: '有効な解像度を選択してください。', resolutionHint: '現行は基準高で算出し、高精細は8 MPを上限に画素数を増やします。8 MPと16 MPは出力全体の画素数です。',
  imageResolutionWarning: '出力サイズが16 MPを超えています。',
  customHeight: '基準高を手入力', customHeightChoice: '手入力…',
  autoHint: 'Autoは指定した全身パネルの高さを維持します。', manualHint: 'Manualはビューを変えても幅・高さを維持します。',
  layout: 'シートプレビュー', diagram: '配置ガイド', experimental: 'Experimental', pixels: '画素',
  caveat: '配置はプロンプト上の指示です。正確な形状や生成品質は保証しません。',
  resolutionWarning: '高解像度は試験対象です。この既存の表示閾値はH3の品質・VRAM上限ではありません。',
  committed: '選択は即時保存', pending: '配置更新中…', stale: '前の配置・更新中', previous: '前の配置', unavailable: 'プレビュー取得失敗', retry: '再試行', empty: 'Pythonの配置を取得中',
  draft: '未確定の値は保存・実行されません。', invalid: '保存JSONが不正です。原文を保持しています。', editJSON: '保存JSONを修正', apply: '有効なJSONを適用', rawHint: '「適用」を押したときだけ保存値を変更します。',
  lastView: '最低1つのビューを選択してください。', sizeError: '32以上の32倍数を整数で入力してください。', maxSize: 'ComfyUIの解像度上限を超えています。', integer: 'JSONの整数項目に小数・指数表記は使えません。', version: 'schema_versionは整数の1または2に対応しています。', views: '既知の7種類から1つ以上のビューを指定してください。', json: 'JSONの構文が不正です。', duplicateKey: 'JSONキーが重複しています', keys: 'JSONキーの不足または未知のキー', oversize: 'JSONは64 KiB以内にしてください。', mode: 'size.modeはautoまたはmanualにしてください。', object: 'JSONオブジェクトが必要です', string: 'state_jsonは文字列で指定してください。', preview: 'サーバーからのプレビューが不正です。', timeout: 'プレビューがタイムアウトしました。保存済み選択は維持しています。', network: 'プレビューを取得できません。Queue時にはサーバーで検証されます。',
  fallback: 'GUIデザイナーを利用できません。通常のstate_json文字列を編集してください。Python実行は利用可能です。',
  layoutTab: 'レイアウト', partsTab: '部位指定', part: '部位', partPrompt: 'プロンプト', partCount: '部位を指定中',
  generatedPrompt: '生成プロンプト', characterOnly: '旧版ベースの最適化・Picture 1のみ・配置参照は自動バイパス', layoutReference: 'Picture 1：人物／Picture 2：配置',
  styleTab: 'スタイル', style: 'スタイル', clearStyle: '解除', styleHint: '人物の描画方法だけを変更します。部位指定を除き、参照の人物・衣装・小物・色を保持し、選択中の全ビューへ共通で適用します。',
  styleUnavailable: 'スタイル入力を有効にするには、ComfyUIを再起動してページを再読込してください。',
  style_none: '指定なし〈デフォルト〉', style_anime: 'アニメ', style_photo: 'フォト〈写真〉', style_realistic_painting: '写実〈絵画〉', style_semi_realistic_anime: '写実アニメ', style_oil_painting: '油彩', style_watercolor: '水彩', style_gouache: 'ガッシュ〈不透明水彩〉', style_colored_pencil: '色鉛筆', style_3d: '3D CG',
  style_none_tip: 'スタイル文を追加しません。', style_anime_tip: 'アニメ風の線とセル塗り。', style_photo_tip: '写真としての表面・陰影表現。', style_realistic_painting_tip: '写実的な形と立体感を絵として描きます。', style_semi_realistic_anime_tip: '参照の顔立ち・体格に、アニメの線と立体的な陰影。', style_oil_painting_tip: '油絵の筆触。', style_watercolor_tip: '輪郭を保った水彩の色の重なり。', style_gouache_tip: '不透明な色面と筆触。', style_colored_pencil_tip: '色鉛筆の線・塗りの質感。', style_3d_tip: '立体レンダリングの表面・陰影表現。',
  partPlaceholder: '色・形・柄・文字・位置などを自由に入力',
  partHint: '部位ごとの指示を、関連する選択ビューへ共通で反映します。空欄なら参照画像に従います。',
  partSaved: '入力は即時保存。Enterで改行します。', partGuide: 'マネキンは配置確認用です。部位指定の見た目はプレビューに反映しません。',
  head_hair_part: '頭・髪', face_part: '顔', upper_clothing_part: '上半身の服', back_clothing_part: '背面の服', lower_body_part: '下半身', hands_part: '手・手袋', footwear_part: '足・履物', other_part: '全体・その他',
  partText: '部位プロンプトは文字列で入力してください。', parts: '未知の部位です。', partLength: '各プロンプトは1000文字以内にしてください（絵文字などは複数文字分）。', partUnicode: 'プロンプトに不正なUnicodeが含まれています。',
  undoWarning: 'このfrontendでは必要なUndoトランザクションAPIを確認できません。',
};
Object.assign(EN, {
  handState: 'Unknown hand state.', clothingMode: 'Unknown clothing mode.',
  handStateLabel: 'Hand appearance', hand_reference: 'Follow reference', hand_bare: 'Bare hands', hand_gloved: 'Gloves',
  qualityHint: 'Hand choice overrides coverage only; other part text remains. Garments only excludes the wearer from the two clothing panels.',
  multiHandsTip: 'Both complete hands; follow the reference or the explicit hand choice',
  garmentTip: 'Referenced garments alone, with no head, limbs, skin, body or mannequin',
  face_right: 'Right portrait', face_3q_left: 'Left 3/4', face_3q_right: 'Right 3/4', face_back: 'Rear portrait',
  clothing_front: 'Clothing front', clothing_back: 'Clothing back',
  face_right_tip: 'Strict anatomical-right profile, head through chest',
  face_3q_left_tip: 'Front-left three-quarter bust, anatomical-left side',
  face_3q_right_tip: 'Front-right three-quarter bust, anatomical-right side',
  face_back_tip: 'Head through chest directly from behind, no visible face',
  clothing_front_tip: 'Front of the complete worn outfit, neck to lowest hem or cuffs',
  clothing_back_tip: 'Back of the complete worn outfit, neck to lowest hem or cuffs',
  head: 'Head · 6 views', clothing: 'Clothing · front/back', multiDetail: 'All · 13 views',
  references: 'Additional reference roles', extraReference: 'Additional reference',
  connected: 'connected', notConnected: 'not connected', roles: 'Unknown reference role.',
  role_same_character: 'Same character · additional angle', role_face: 'Face only', role_head: 'Head / face / hair',
  role_clothing: 'Complete outfit', role_clothing_front: 'Front of outfit', role_clothing_back: 'Back of outfit',
  role_hands: 'Hands / accessories', role_footwear: 'Feet / footwear',
  referenceRoleHint: 'Connect external LoadImage nodes to the Designer. Roles apply wherever visible, even with the detail card off.',
  numberingProvisional: 'Planned Picture numbers from connections; actual images are resolved at execution.',
});
Object.assign(JA, {
  handState: '未知の手の状態です。', clothingMode: '未知の衣装表示です。',
  handStateLabel: '手の状態', hand_reference: '参照に従う', hand_bare: '素手', hand_gloved: '手袋',
  qualityHint: '手の選択は着用有無を優先し、部位文は形・素材などに使います。衣服のみでは衣装2枚に人物を描きません。',
  multiHandsTip: '両手の全体。参照または手の状態の明示指定に従う',
  garmentTip: '参照の衣服のみ。頭・手足・肌・身体・マネキンを描かない',
  face_right: '横顔・右', face_3q_left: '左斜め', face_3q_right: '右斜め', face_back: '頭部背面',
  clothing_front: '衣装正面', clothing_back: '衣装背面',
  face_right_tip: '人物の解剖学的右側から見た横顔。髪全体から胸まで',
  face_3q_left_tip: '人物の左側から45度の斜め正面。頭から胸まで',
  face_3q_right_tip: '人物の右側から45度の斜め正面。頭から胸まで',
  face_back_tip: '真後ろの頭から胸まで。顔を見せない',
  clothing_front_tip: '着用衣装の正面。首元から服の最下端まで。上下別・ワンピースにも対応',
  clothing_back_tip: '着用衣装の背面。首元から服の最下端まで',
  head: '頭部6ビュー', clothing: '衣装・前後', multiDetail: '全13ビュー',
  references: '追加参照の役割', extraReference: '追加参照',
  connected: '接続中', notConnected: '未接続', roles: '未知の参照役割です。',
  role_same_character: '同一人物・補足画像', role_face: '顔のみ', role_head: '頭部・顔・髪',
  role_clothing: '衣装全体', role_clothing_front: '衣装前面', role_clothing_back: '衣装背面',
  role_hands: '手・小物', role_footwear: '足・履物',
  referenceRoleHint: '外部のLoadImageをDesignerに接続します。詳細カードがOFFでも、見える部位へ適用します。',
  numberingProvisional: '接続に基づくPicture予定番号です。実際の画像は実行時に確定します。',
});
export const translations = {en: EN, ja: JA};
const multiTips = {
  en: {face_left: 'H3 anatomical-left strict profile; nose toward the RIGHT image edge',
    face_right: 'H3 anatomical-right strict profile; nose toward the LEFT image edge',
    face_3q_left: 'H3 anatomical-left 45-degree view; nose toward the RIGHT image edge',
    face_3q_right: 'H3 anatomical-right 45-degree view; nose toward the LEFT image edge',
    body_left: 'H3 anatomical-left full-body profile; nose and toes toward the RIGHT image edge'},
  ja: {face_left: 'H3の左側面規約。厳密な横顔で鼻は画面の右へ',
    face_right: 'H3の右側面規約。厳密な横顔で鼻は画面の左へ',
    face_3q_left: 'H3の左側から45度。鼻は画面の右へ',
    face_3q_right: 'H3の右側から45度。鼻は画面の左へ',
    body_left: 'H3の左側面規約。全身側面で鼻・つま先は画面の右へ'},
};
export function errorText(error, locale = 'en') {
  const t = translations[locale] ?? EN;
  if (error instanceof StateError) {
    const key = error.code === 'size' ? 'sizeError' : error.code;
    return `${t[key] ?? t.network}${['duplicateKey', 'keys', 'object', 'maxSize'].includes(error.code) && error.detail ? ` (${error.detail})` : ''}`;
  }
  const serverCodes = {duplicate_key: 'duplicateKey', non_finite: 'integer', invalid_integer: 'integer', invalid_size: 'sizeError', size_limit: 'maxSize', unsupported_schema: 'version', empty_views: 'views', unknown_view: 'views', invalid_mode: 'mode', missing_key: 'keys', unknown_key: 'keys', invalid_json: 'json', invalid_utf8: 'json', state_too_large: 'oversize', request_too_large: 'oversize', unknown_part: 'parts', part_prompt_too_long: 'partLength', invalid_hand_state: 'handState', invalid_clothing_mode: 'clothingMode'};
  return error?.serverCode && serverCodes[error.serverCode] ? t[serverCodes[error.serverCode]] : error?.serverMessage || t.network;
}
function element(tag, className, text) { const el = document.createElement(tag); if (className) el.className = className; if (text) el.textContent = text; return el; }
const button = className => { const el = element('button', className); el.type = 'button'; return el; };
export function loadStyles() {
  if (document.querySelector('link[data-h3-reference13]')) return;
  const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = new URL('./reference13_style.css', import.meta.url).href; link.dataset.h3Reference13 = ''; document.head.append(link);
}

/** Real UI renderer shared by the ComfyUI extension and the browser test harness. */
export function createDesignerUI({controller, v13 = false, imageNode = false, versionLabel = undefined, locale = 'en', compatibilityWarning = false, useLayoutImage = () => false, readStyle = () => 'none', readBatchOut = () => false, outputAware = false, writeStyle = null, reference = false, multiReference = false, readReferencePresence = () => ({reference_image_1: false, reference_image_2: false})}) {
  loadStyles();
  const id = `h3-reference13-${++sequence}`;
  const root = element('section', 'h3-designer h3-reference13'); root.dataset.instance = id; root.classList.toggle('h3-reference', reference); root.setAttribute('aria-label', reference ? 'H3 Character Sheet Designer Reference' : 'H3 Character Sheet Designer');
  root.classList.toggle('h3-multi-reference', multiReference);
  const nodeVersion = versionLabel ?? (v13 ? 'v1.3.0' : 'v1.2.2');
  root.dataset.nodeVersion = nodeVersion;
  root.setAttribute('aria-label', `H3 Character Sheet Designer ${nodeVersion}`);
  root.classList.toggle('h3-v13', v13);
  const viewIds = multiReference ? MULTI_VIEW_IDS : VIEW_IDS;
  const presets = v13 ? V13_PRESETS : multiReference ? MULTI_PRESETS : PRESETS;
  const abort = new AbortController(); const listen = (el, type, handler) => el.addEventListener(type, handler, {signal: abort.signal});
  let language = locale, t = translations[locale] ?? EN, disposed = false;
  const partDrafts = new Map(); let selectedPart = PART_IDS[0], activeTab = 'layout';
  const drafts = new Map(); let customHeight = false; let localError = null, lastRaw = Symbol(), lastPreviewKey = null; let activeOutput = 0;
  const header = element('div', 'h3-intro'), intro = element('span'), count = element('span', 'h3-count'); header.append(intro, count);
  const versionBadge = element('span', 'h3-node-version', nodeVersion); header.prepend(versionBadge);
  const cards = element('div', 'h3-cards'), cardMap = new Map();
  const headRow = element('div', 'h3-card-row h3-head-row'), bodyRow = element('div', 'h3-card-row h3-body-row');
  if (multiReference) cards.append(headRow, bodyRow);
  for (const view of viewIds) {
    const card = button('h3-card'); card.dataset.view = view;
    const figure = element('span', 'h3-card-figure'); figure.append(createArtwork(view, `${id}-card-${view}`, {mirror: multiReference && MULTI_MIRRORED_VIEWS.includes(view), garment: v13}));
    const check = element('span', 'h3-check', '✓'); check.setAttribute('aria-hidden', 'true');
    const label = element('span', 'h3-card-label'); card.append(figure, check, label);
    listen(card, 'click', () => act(() => controller.toggle(view)));
    (multiReference ? (viewIds.indexOf(view) < 6 ? headRow : bodyRow) : cards).append(card); cardMap.set(view, {card, label});
  }
  const clothingGroup = element('div', 'h3r13-clothing-group');
  const clothingCards = element('div', 'h3r13-clothing-cards');
  if (multiReference) {
    bodyRow.insertBefore(clothingGroup, cardMap.get('clothing_front').card);
    clothingCards.append(cardMap.get('clothing_front').card, cardMap.get('clothing_back').card);
    clothingGroup.append(clothingCards);
  }
  const presetRow = element('div', 'h3-preset-row'), presetLabel = element('label'), preset = element('select', 'h3-select'); preset.id = `${id}-preset`; presetLabel.htmlFor = preset.id;
  for (const name of [...Object.keys(presets), 'custom']) { const option = element('option'); option.value = name; option.disabled = name === 'custom'; preset.append(option); }
  presetRow.append(presetLabel, preset); listen(preset, 'change', () => act(() => controller.preset(preset.value)));
  const controls = element('div', 'h3-controls');
  const modeRow = element('div', 'h3-mode-row'), sizeLabel = element('span', 'h3-field-title'), modeGroup = element('div', 'h3-mode-group');
  const auto = button('h3-mode'), manual = button('h3-mode'); auto.dataset.mode = 'auto'; manual.dataset.mode = 'manual'; modeGroup.append(auto, manual); modeRow.append(sizeLabel, modeGroup);
  listen(auto, 'click', () => act(() => controller.setMode('auto'))); listen(manual, 'click', () => act(() => controller.setMode('manual', displayOutput())));
  const numberRow = element('div', 'h3-number-row'), fields = new Map();
  const resolution = imageNode ? element('select', 'h3-select') : null;
  const resolutionLabel = imageNode ? element('label') : null;
  if (resolution) {
    controls.classList.add('h3-image-controls');
    numberRow.classList.add('h3-resolution-row');
    resolution.id = `${id}-resolution`; resolution.dataset.resolutionProfile = '';
    resolutionLabel.htmlFor = resolution.id;
    for (const value of IMAGE_RESOLUTION_PROFILES) {
      const option = element('option'); option.value = value; resolution.append(option);
    }
    const wrap = element('div', 'h3-number-field'), line = element('div', 'h3-input-line');
    line.append(resolution); wrap.append(resolutionLabel, line); numberRow.append(wrap);
    listen(resolution, 'change', () => act(() => controller.change(next => {
      if (resolution.value === 'current') delete next.resolution_profile;
      else next.resolution_profile = resolution.value;
    })));
  }
  for (const [field, labelKey] of [['body_height', 'bodyHeight'], ['manual_width', 'width'], ['manual_height', 'height']]) {
    const wrap = element('div', 'h3-number-field'), label = element('label'), input = element('input'); input.type = 'text'; input.inputMode = 'numeric'; input.autocomplete = 'off'; input.spellcheck = false; input.id = `${id}-${field}`; input.dataset.field = field; label.htmlFor = input.id;
    const message = element('span', 'h3-draft-note'); message.id = `${input.id}-note`; input.setAttribute('aria-describedby', message.id);
    const line = element('div', 'h3-input-line'); line.append(input);
    if (field === 'body_height') {
      // The value and arrow are one full-width native select. A tiny separate
      // select anchors its popup to the arrow instead of the displayed value.
      const choices = element('select', 'h3-select h3-height-choices'); choices.dataset.heightPresets = '';
      choices.id = `${input.id}-choices`; label.htmlFor = choices.id;
      for (const height of HEIGHT_PRESETS) { const option = element('option', '', String(height)); option.value = String(height); choices.append(option); }
      const custom = element('option'); custom.value = 'custom'; choices.append(custom);
      listen(choices, 'change', () => {
        if (choices.value === 'custom') {
          customHeight = true; renderFields(); input.focus(); input.select();
        } else {
          customHeight = false; drafts.delete(field); act(() => controller.setSize(field, choices.value));
        }
      });
      line.prepend(choices); fields.set(field, {wrap, label, input, message, labelKey, choices, custom});
    } else fields.set(field, {wrap, label, input, message, labelKey});
    wrap.append(label, line, message); numberRow.append(wrap);
    listen(input, 'input', () => { drafts.set(field, {text: input.value, error: null}); renderFields(); });
    listen(input, 'blur', () => commitDraft(field));
    listen(input, 'keydown', event => { if (event.isComposing || event.keyCode === 229) return; if (event.key === 'Enter') { event.preventDefault(); event.stopPropagation(); commitDraft(field); } if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); drafts.delete(field); if (field === 'body_height') customHeight = false; renderFields(); fields.get(field).choices?.focus(); } });
  }
  const returnAuto = button('h3-link-button'); listen(returnAuto, 'click', () => act(() => controller.setMode('auto')));
  const modeHint = element('div', 'h3-mode-hint'); controls.append(modeRow, numberRow, returnAuto, modeHint);
  const metrics = element('div', 'h3-metrics'), dimensions = element('strong', 'h3-dimensions'), pixels = element('span', 'h3-pixels'), badge = element('span', 'h3-experimental'); metrics.append(dimensions, pixels, badge);
  const warning = element('div', 'h3-resolution-note');
  const status = element('div', 'h3-status'); status.setAttribute('role', 'status'); status.setAttribute('aria-live', 'polite');
  const errorBox = element('div', 'h3-error'); errorBox.setAttribute('role', 'alert');
  const retry = button('h3-retry'); listen(retry, 'click', () => { localError = null; void controller.refreshPreview(); });
  const styleStatus = element('div', 'h3-style-status'), styleBadge = element('span'), clearStyle = button('h3-clear-style');
  styleStatus.dataset.styleStatus = ''; styleStatus.setAttribute('role', 'status'); styleStatus.setAttribute('aria-live', 'polite');
  clearStyle.dataset.clearStyle = ''; listen(clearStyle, 'click', () => act(() => writeStyle('none'))); styleStatus.append(styleBadge, clearStyle);
  const previewHead = element('div', 'h3-preview-head'), tabs = element('div', 'h3-tabs'), previewTag = element('span', 'h3-preview-tag');
  tabs.setAttribute('role', 'tablist'); const tabMap = new Map();
  const tabNames = reference ? ['layout', 'parts', 'style', ...(v13 ? ['settings', 'prompts'] : [])] : ['layout', 'parts', ...(v13 ? ['settings', 'prompts'] : [])];
  for (const name of tabNames) {
    const tab = button('h3-tab'); tab.id = `${id}-${name}-tab`; tab.dataset.tab = name;
    tab.setAttribute('role', 'tab'); tab.setAttribute('aria-controls', `${id}-${name}-panel`);
    listen(tab, 'click', () => { activeTab = name; render(); });
    listen(tab, 'keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation();
      activeTab = event.key === 'Home' ? tabNames[0] : event.key === 'End' ? tabNames.at(-1) : tabNames[(tabNames.indexOf(activeTab) + (event.key === 'ArrowRight' ? 1 : tabNames.length - 1)) % tabNames.length];
      render(); tabMap.get(activeTab).focus();
    });
    tabs.append(tab); tabMap.set(name, tab);
  }
  previewHead.append(tabs, previewTag);
  const stage = element('div', 'h3-stage'); stage.id = `${id}-layout-panel`; stage.setAttribute('role', 'tabpanel'); stage.setAttribute('aria-labelledby', `${id}-layout-tab`); stage.tabIndex = 0;
  stage.dataset.previewStage = ''; const canvas = element('div', 'h3-sheet'); const empty = element('div', 'h3-empty'); stage.append(canvas, empty);
  const gallery = element('div', 'h3-output-gallery'); gallery.dataset.outputGallery = ''; gallery.hidden = true; stage.append(gallery);
  function displayOutput() { return controller.isCurrentPreview ? controller.preview : null; }
  const partPanel = element('div', 'h3-part-panel'); partPanel.id = `${id}-parts-panel`; partPanel.setAttribute('role', 'tabpanel'); partPanel.setAttribute('aria-labelledby', `${id}-parts-tab`);
  const partRow = element('div', 'h3-part-row'), partLabel = element('label'), partSelect = element('select', 'h3-select');
  partSelect.id = `${id}-part`; partSelect.dataset.partSelect = ''; partLabel.htmlFor = partSelect.id;
  for (const part of PART_IDS) { const option = element('option'); option.value = part; partSelect.append(option); }
  const partCount = element('span', 'h3-part-count'); partCount.setAttribute('aria-live', 'polite');
  partRow.append(partLabel, partSelect, partCount);
  const promptLabel = element('label', 'h3-prompt-label'), partInput = element('textarea', 'h3-part-input');
  partInput.id = `${id}-part-prompt`; partInput.dataset.partPrompt = ''; promptLabel.htmlFor = partInput.id;
  partInput.maxLength = PART_PROMPT_MAX_LENGTH; partInput.spellcheck = false; partInput.rows = 5;
  const partHint = element('div', 'h3-part-hint'), partNote = element('div', 'h3-part-note'), partLength = element('span', 'h3-part-length');
  partHint.id = `${id}-part-hint`; partNote.id = `${id}-part-note`;
  partInput.setAttribute('aria-describedby', `${partHint.id} ${partNote.id}`);
  const partBottom = element('div', 'h3-part-bottom'); partBottom.append(partNote, partLength);
  partPanel.append(partRow, partHint, promptLabel, partInput, partBottom);
  const roleMap = new Map();
  const rolesBox = element('div', 'h3-reference-roles');
  for (const [index, input] of REFERENCE_INPUTS.entries()) {
    const row = element('div', 'h3-reference-role-row'), label = element('label'), select = element('select', 'h3-select');
    select.id = `${id}-${input}-role`; select.dataset.referenceRole = input; label.htmlFor = select.id;
    for (const role of REFERENCE_ROLES) { const option = element('option'); option.value = role; select.append(option); }
    listen(select, 'change', () => act(() => controller.setReferenceRole(input, select.value)));
    row.append(label, select); rolesBox.append(row); roleMap.set(input, {index, label, select});
  }
  partPanel.append(rolesBox);
  const qualityMap = new Map();
  const qualityBox = element('div', 'h3r13-choices');
  if (v13) qualityBox.append(presetRow);
  for (const field of ['clothing_type', 'hand_state', 'footwear_state']) {
    const row = element('div', 'h3r13-choice'), label = element('label'), select = element('select', 'h3-select');
    row.dataset.choiceGroup = field; select.dataset.appearanceChoice = field;
    select.id = `${id}-${field}`; label.htmlFor = select.id;
    for (const value of SETTINGS[field]) { const option = element('option'); option.value = value; select.append(option); }
    listen(select, 'change', () => act(() => controller.setChoice(field, select.value)));
    row.append(label, select); qualityBox.append(row); qualityMap.set(field, {label, select});
  }
  const qualityHint = element('div', 'h3r13-choice-hint');
  // Persist synchronously on every input, including IME input. Do not rewrite an
  // unchanged textarea value while composing, so the caret and composition live on.
  listen(partInput, 'input', () => commitPart());
  listen(partInput, 'keydown', event => event.stopPropagation()); // Enter remains a native newline.
  listen(partSelect, 'change', () => { selectedPart = partSelect.value; render(); });
  const stylePanel = element('div', 'h3-style-panel'); stylePanel.id = `${id}-style-panel`; stylePanel.setAttribute('role', 'tabpanel'); stylePanel.setAttribute('aria-labelledby', `${id}-style-tab`);
  const styleHint = element('div', 'h3-part-hint'), styleChoices = element('div', 'h3-style-choices'), styleMap = new Map();
  styleChoices.setAttribute('role', 'radiogroup'); styleChoices.setAttribute('aria-labelledby', `${id}-style-tab`);
  for (const style of STYLE_IDS) {
    const choice = element('label', 'h3-style-choice'), input = element('input'), text = element('span'), label = element('strong'), hint = element('span');
    input.type = 'radio'; input.name = `${id}-style`; input.value = style; input.dataset.style = style;
    text.append(label, hint); choice.append(input, text); styleChoices.append(choice); styleMap.set(style, {choice, input, label, hint});
    listen(input, 'change', () => { if (input.checked) act(() => writeStyle(style)); });
  }
  stylePanel.append(styleHint, styleChoices);
  const footer = element('div', 'h3-footer');
  const generated = element('details', 'h3-generated-prompt'), generatedSummary = element('summary'), generatedText = element('pre');
  generatedText.dataset.generatedPrompt = ''; generated.append(generatedSummary, generatedText);
  const jsonDetails = element('details', 'h3-json-editor'), summary = element('summary'), rawInput = element('textarea'), rawHint = element('p'), apply = button('h3-apply'); rawInput.spellcheck = false; rawInput.setAttribute('aria-label', 'state_json');
  listen(apply, 'click', () => act(() => {
    controller.applyRaw(rawInput.value);
    // A valid JSON replacement owns these values, even when the saved JSON is unchanged.
    drafts.clear(); partDrafts.clear(); viewDirty = false; viewComposing = false;
  })); jsonDetails.append(summary, rawInput, rawHint, apply);
  root.append(header, cards, qualityBox);
  if (!v13) root.append(qualityHint);
  if (!v13) root.append(presetRow);
  root.append(controls, metrics);
  if (!v13) root.append(warning, status); else metrics.append(status);
  root.append(errorBox, retry);
  if (reference) root.append(styleStatus);
  root.append(previewHead, stage, partPanel);
  if (reference) root.append(stylePanel);
  root.append(footer);
  const settingsPanel = element('div', 'h3-v13-settings');
  settingsPanel.id = `${id}-settings-panel`; settingsPanel.setAttribute('role', 'tabpanel'); settingsPanel.setAttribute('aria-labelledby', `${id}-settings-tab`);
  if (v13) {
    settingsPanel.append(modeHint, warning, qualityHint, generated, jsonDetails); root.append(settingsPanel);
  } else {
    if (reference) root.append(generated);
    root.append(jsonDetails);
  }
  const promptsPanel = element('div', 'h3-v13-settings h3-view-prompts');
  promptsPanel.id = id + '-prompts-panel'; promptsPanel.setAttribute('role', 'tabpanel');
  promptsPanel.setAttribute('aria-labelledby', id + '-prompts-tab');
  const viewEditor = element('details'), viewSummary = element('summary');
  viewEditor.open = true;
  const viewSelect = element('select', 'h3-part-select'), viewInput = element('textarea', 'h3-part-input');
  const viewHelp = element('p', 'h3-part-hint'), viewApply = button('h3-apply'), viewReset = button('h3-apply');
  const viewPreview = element('details'), viewPreviewSummary = element('summary'), viewPreviewText = element('pre');
  viewPreviewText.style.whiteSpace = 'pre-wrap';
  let selectedView = VIEW_IDS[0], viewDirty = false, viewComposing = false;
  for (const view of VIEW_IDS) { const option = element('option'); option.value = view; viewSelect.append(option); }
  viewInput.rows = 5; viewInput.spellcheck = false;
  function saveView() {
    if (!viewDirty) return;
    if (viewComposing) throw new StateError('composition');
    controller.setViewPrompt(selectedView, viewInput.value); viewDirty = false;
  }
  listen(viewInput, 'input', () => { viewDirty = true; });
  listen(viewInput, 'compositionstart', () => { viewComposing = true; });
  listen(viewInput, 'compositionend', () => { viewComposing = false; viewDirty = true; });
  listen(viewInput, 'keydown', event => event.stopPropagation());
  listen(viewSelect, 'change', () => {
    const next = viewSelect.value; viewSelect.value = selectedView; act(saveView);
    if (viewDirty) return;
    selectedView = next; viewSelect.value = next; render();
  });
  listen(viewApply, 'click', () => act(saveView));
  listen(viewReset, 'click', () => act(() => {
    controller.setViewPrompt(selectedView, null); viewDirty = false;
  }));
  viewEditor.append(viewSummary, viewSelect, viewInput, viewHelp, viewApply, viewReset);
  viewPreview.append(viewPreviewSummary, viewPreviewText); promptsPanel.append(viewEditor, viewPreview);
  if (v13) root.append(promptsPanel);
  // Keep node dragging out of text controls, but let browser keyboard accessibility work.
  listen(root, 'pointerdown', event => event.stopPropagation());
  const resizeObserver = typeof ResizeObserver === 'function' ? new ResizeObserver(() => fitSheet()) : null;
  resizeObserver?.observe(stage);
  function act(fn) { try { localError = null; fn(); } catch (error) { localError = error; } render(); }
  function commitDraft(field) {
    const draft = drafts.get(field); if (!draft) return;
    try {
      // Remove only this draft before the synchronous commit rerenders the UI.
      drafts.delete(field); controller.setSize(field, draft.text);
    } catch (error) { drafts.set(field, {...draft, error}); }
    render();
  }
  function commitPart() {
    const text = partInput.value;
    try {
      partDrafts.set(selectedPart, {text, error: null}); controller.setPartPrompt(selectedPart, text);
    } catch (error) { partDrafts.set(selectedPart, {text, error}); }
    renderParts();
  }
  function renderParts() {
    const state = controller.state, prompts = state?.part_prompts ?? {}, draft = partDrafts.get(selectedPart);
    for (const [input, item] of roleMap) {
      item.label.textContent = `${language === 'ja' ? '追加参照' : 'Extra reference'} ${item.index + 1}`;
      item.select.disabled = !state; item.select.value = state?.reference_roles?.[input] ?? 'same_character';
      for (const option of item.select.options) option.textContent = t[`role_${option.value}`];
    }
    tabs.setAttribute('aria-label', t.diagram);
    for (const [name, tab] of tabMap) {
      tab.textContent = name === 'layout' ? t.layoutTab : name === 'style' ? t.styleTab : name === 'prompts' ? (language === 'ja' ? 'プロンプト' : 'Prompts') : name === 'settings' ? (language === 'ja' ? '設定' : 'Settings') : `${t.partsTab}${Object.keys(prompts).length ? ` (${Object.keys(prompts).length})` : ''}`;
      tab.setAttribute('aria-selected', String(name === activeTab)); tab.tabIndex = name === activeTab ? 0 : -1;
    }
    stage.hidden = activeTab !== 'layout'; partPanel.hidden = activeTab !== 'parts'; stylePanel.hidden = activeTab !== 'style'; settingsPanel.hidden = activeTab !== 'settings'; promptsPanel.hidden = activeTab !== 'prompts';
    const ja = language === 'ja', current = controller.isCurrentPreview;
    viewSummary.textContent = ja ? 'ビューのプロンプトを編集' : 'Edit view prompts';
    viewApply.textContent = ja ? '適用' : 'Apply';
    viewReset.textContent = ja ? '初期値に戻す' : 'Reset this prompt';
    viewHelp.textContent = ja ? '選んだビューの基本文を置き換えます。空欄も保存できます。配置・参照・部位・各設定の指示は別途加わります。各2,000文字まで。' : 'Replace this view’s base prompt; blank is allowed. Layout, references, part prompts and settings are added separately. Up to 2,000 UTF-16 units each.';
    viewSelect.value = selectedView; viewSelect.setAttribute('aria-label', ja ? '編集するビュー' : 'View to edit');
    for (const option of viewSelect.options) option.textContent = t[option.value] ?? option.value;
    const override = state?.view_prompts?.[selectedView];
    const defaults = current ? controller.preview?.default_view_prompts?.[selectedView] : undefined;
    viewInput.disabled = !state || (override === undefined && defaults === undefined);
    viewInput.setAttribute('aria-label', viewSummary.textContent);
    viewApply.disabled = !state || viewInput.disabled; viewReset.disabled = !state;
    if (!viewDirty) viewInput.value = override ?? defaults ?? '';
    viewPreviewSummary.textContent = ja ? '各ビューの指示（設定プレビュー）' : 'Per-view prompts (settings preview)';
    viewPreviewText.textContent = current ? (controller.preview?.view_prompts ?? []).join('\n\n') : t.pending;
    previewTag.textContent = activeTab === 'layout' ? (language === 'ja' ? (useLayoutImage() ? '生成に渡す配置画像' : v13 ? '配置ガイド' : '配置の目安') : (useLayoutImage() ? 'Generation layout image' : v13 ? 'Layout guide' : 'Conceptual layout')) : activeTab === 'style' ? t.style : t.partSaved;
    const selectedStyle = readStyle();
    styleStatus.hidden = !reference || selectedStyle === 'none'; styleBadge.textContent = `${t.style}：${t[`style_${selectedStyle}`] ?? selectedStyle}`;
    clearStyle.textContent = t.clearStyle; clearStyle.disabled = !writeStyle;
    styleHint.textContent = writeStyle ? t.styleHint : t.styleUnavailable;
    for (const [style, item] of styleMap) {
      item.input.checked = style === selectedStyle; item.input.disabled = !state || !writeStyle;
      item.choice.classList.toggle('h3-style-selected', item.input.checked);
      item.label.textContent = t[`style_${style}`]; item.hint.textContent = t[`style_${style}_tip`];
    }
    partLabel.textContent = t.part; partSelect.disabled = !state; partSelect.value = selectedPart;
    for (const option of partSelect.options) option.textContent = `${prompts[option.value] ? '● ' : ''}${t[`${option.value}_part`]}`;
    partCount.textContent = `${Object.keys(prompts).length} ${t.partCount}`;
    promptLabel.textContent = `${t[`${selectedPart}_part`]} · ${t.partPrompt}`;
    partHint.textContent = t.partHint; partInput.disabled = !state; partInput.placeholder = t.partPlaceholder;
    const value = draft?.text ?? prompts[selectedPart] ?? '';
    if (partInput.value !== value) partInput.value = value;
    partInput.setAttribute('aria-invalid', String(Boolean(draft?.error)));
    partNote.textContent = draft?.error ? `${errorText(draft.error, language)} ${t.draft}` : t.partSaved;
    partNote.classList.toggle('h3-part-invalid', Boolean(draft?.error));
    partLength.textContent = `${partInput.value.length} / ${PART_PROMPT_MAX_LENGTH}`;
  }
  function renderRoles() {
    const ja = language === 'ja';
    const labels = ja ? {clothing_type: '衣装の型', hand_state: '手', footwear_state: '足・履物'} : {clothing_type: 'Clothing shape', hand_state: 'Hands', footwear_state: 'Feet'};
    const options = ja ? {reference: 'Auto', pants: 'パンツ', skirt_robe: 'スカート・ローブ', bare: '素手', gloved: 'グローブ', shod: '靴あり', unshod: '靴なし'} : {reference: 'Auto', pants: 'Pants', skirt_robe: 'Skirt / robe', bare: 'Bare hands', gloved: 'Gloves', shod: 'Footwear on', unshod: 'Footwear off'};
    const tips = ja ? {
      clothing_type: '参照の衣装形状を維持、またはパンツ／スカート・ローブを指定。全身と衣装の前後に適用します。',
      hand_state: '参照維持／素手／グローブ。手の詳細と全身ビューに適用します。',
      footwear_state: '参照維持／靴あり／靴なし。足の詳細と全身ビューに適用。靴なしでも靴下・タイツは維持します。',
    } : {
      clothing_type: 'Follow the reference shape or choose pants / skirt or robe. Applies to full-body and front/back outfit views.',
      hand_state: 'Follow the reference, bare hands or gloves. Applies to hand details and full-body views.',
      footwear_state: 'Follow the reference, footwear on or off. Applies to foot details and full-body views. Footwear off preserves compatible socks and tights.',
    };
    for (const [field, item] of qualityMap) {
      item.label.textContent = labels[field]; item.select.disabled = !controller.state;
      item.select.title = tips[field];
      item.select.value = controller.state?.[field] ?? DEFAULTS[field];
      for (const option of item.select.options) option.textContent = options[option.value];
    }
    qualityHint.textContent = ja ? 'Auto：参照の状態を維持' : 'Auto follows the reference.';
  }
  function renderFields() {
    const state = controller.state;
    for (const [field, item] of fields) {
      const draft = drafts.get(field), active = state && (field === 'body_height' ? state.size.mode === 'auto' : state.size.mode === 'manual');
      item.label.textContent = t[item.labelKey]; item.input.disabled = !active;
      const autoDimension = state?.size.mode === 'auto' && field !== 'body_height';
      const displayValue = autoDimension ? (displayOutput() ? String(field === 'manual_width' ? displayOutput().width : displayOutput().height) : '—') : state ? String(state.size[field]) : '';
      item.input.value = draft ? draft.text : displayValue;
      item.input.title = autoDimension && !controller.isCurrentPreview ? t.updating : ''; 
      item.input.setAttribute('aria-invalid', String(Boolean(draft?.error)));
      item.message.textContent = draft ? `${draft.error ? `${errorText(draft.error, language)} ` : ''}${t.draft}` : '';
      item.wrap.classList.toggle('h3-has-draft', Boolean(draft));
      if (item.choices) {
        const showCustom = Boolean(state && (customHeight || !HEIGHT_PRESETS.includes(state.size.body_height)));
        item.choices.disabled = !active; item.choices.title = t.bodyHeight;
        item.choices.value = showCustom ? 'custom' : state ? String(state.size.body_height) : '';
        item.custom.textContent = t.customHeightChoice;
        item.input.hidden = !showCustom; item.input.disabled = !active || !showCustom;
        item.input.setAttribute('aria-label', t.customHeight);
      }
    }
  }
  function fitSheet() {
    const p = controller.preview; if (!p || !stage.clientWidth || (outputAware && readBatchOut())) return;
    const availableW = Math.max(1, stage.clientWidth - 30), availableH = Math.max(1, stage.clientHeight - 28);
    const scale = Math.min(availableW / p.width, availableH / p.height);
    canvas.style.width = `${p.width * scale}px`; canvas.style.height = `${p.height * scale}px`;
    canvas.style.setProperty('--h3-frame-width', `${(v13 && p.guide_geometry ? p.guide_geometry.frame_width : Math.max(1, Math.floor((Math.min(p.width, p.height) + 128) / 256))) * scale}px`);
  }
  function renderPreview() {
    const p = controller.preview, valid = controller.isCurrentPreview && Boolean(controller.state);
    canvas.hidden = !valid; empty.hidden = valid; gallery.hidden = true;
    empty.textContent = controller.error ? t.invalid : controller.previewError ? t.unavailable : t.empty;
    const key = valid ? JSON.stringify([p.semantic_layout, p.guide_geometry, useLayoutImage()]) : null;
    if (key !== lastPreviewKey) {
      canvas.replaceChildren(); lastPreviewKey = key;
      if (valid && (useLayoutImage() || (v13 && p.guide_geometry))) {
        for (const panel of p.guide_geometry.panels) {
          if (!panel.blank) canvas.append(createGuideArtwork(panel, p.guide_geometry.canvas, `${id}-${panel.id}`));
          const [left, top, right, bottom] = panel.bounds;
          const box = element('div', 'h3-panel'); box.dataset.panel = panel.id;
          Object.assign(box.style, {left: `${left/p.width*100}%`, top: `${top/p.height*100}%`, width: `${(right-left)/p.width*100}%`, height: `${(bottom-top)/p.height*100}%`});
          canvas.append(box);
        }
      } else if (valid) {
        for (const panel of p.semantic_layout.panels) {
          const box = element('div', 'h3-panel'); box.dataset.panel = panel.id;
          const [left, top, width, height] = panel.rect;
          Object.assign(box.style, {left: `${left*100}%`, top: `${top*100}%`, width: `${width*100}%`, height: `${height*100}%`});
          if (v13 || !(controller.state.clothing_mode === 'garment' && panel.id.startsWith('clothing_'))) box.append(createArtwork(panel.id, `${id}-${panel.id}`, {garment: v13}));
          canvas.append(box);
        }
      }
    }
    stage.setAttribute('aria-busy', String(controller.pending)); fitSheet();
  }
  function flushDrafts() {
    if (v13) saveView();
    for (const [field, draft] of [...drafts]) {
      drafts.delete(field);
      try { controller.setSize(field, draft.text); }
      catch (error) { drafts.set(field, {...draft, error}); render(); fields.get(field).input.focus(); throw error; }
    }
    for (const [part, draft] of partDrafts) if (draft.error) { selectedPart = part; activeTab = 'parts'; render(); partInput.focus(); throw draft.error; }
  }
  function render(reason) {
    if (disposed) return;
    if (reason === 'restore') { viewDirty = false; viewComposing = false; activeOutput = 0; drafts.clear(); partDrafts.clear(); customHeight = false; localError = null; }
    t = translations[language] ?? EN; root.lang = language;
    const state = controller.state, current = controller.isCurrentPreview;

    intro.textContent = t.intro; count.textContent = `${state?.views.length ?? 0} / ${viewIds.length} ${t.selected}`;
    for (const [view, {card, label}] of cardMap) {
      card.setAttribute('aria-pressed', String(Boolean(state?.views.includes(view)))); card.disabled = !state;
      const tip = multiReference && view === 'hands' ? t.multiHandsTip : multiReference && (v13 || state?.clothing_mode === 'garment') && view.startsWith('clothing_') ? t.garmentTip : multiReference && multiTips[language]?.[view] || t[`${view}_tip`];
      card.title = tip; card.setAttribute('aria-label', `${t[view]}: ${tip}`); label.textContent = t[view];
    }
    presetLabel.textContent = t.preset; preset.disabled = !state; preset.value = Object.entries(presets).find(([, views]) => views.join() === state?.views.join())?.[0] ?? 'custom';
    for (const option of preset.options) option.textContent = multiReference && option.value === 'detail' ? t.multiDetail : t[option.value];
    auto.textContent = t.auto; manual.textContent = state?.size.mode === 'auto' && !current ? t.updating : t.manual;
    auto.disabled = !state; manual.disabled = !state || (state.size.mode === 'auto' && !current);
    auto.setAttribute('aria-pressed', String(state?.size.mode === 'auto')); manual.setAttribute('aria-pressed', String(state?.size.mode === 'manual'));
    sizeLabel.textContent = t.size; returnAuto.textContent = t.returnAuto; returnAuto.hidden = state?.size.mode !== 'manual';
    if (resolution) {
      resolutionLabel.textContent = t.resolution;
      resolution.disabled = state?.size.mode !== 'auto';
      resolution.title = state?.size.mode === 'manual' ? t.manualHint : t.resolutionHint;
      for (const option of resolution.options) option.textContent = t[`resolution_${option.value}`];
      resolution.value = state?.resolution_profile ?? 'current';
    }
    modeHint.textContent = outputAware && readBatchOut() ? (language === 'ja' ? '各画像を個別に生成。Manual寸法は全画像に共通。Autoはビュー種別ごとの寸法。表示中の画像をクリックしてManualへ切替できます。' : 'Each view is generated separately. Manual dimensions apply to every image; Auto uses the view type. Select a preview to freeze its dimensions in Manual.') : outputAware && state?.size.mode === 'manual' ? (language === 'ja' ? '指定した画像サイズ内に選択ビューを再配置します。' : 'Selected views are rearranged inside the requested canvas.') : state?.size.mode === 'manual' ? t.manualHint : t.autoHint;
    renderFields(); renderParts(); renderRoles();
    const p = controller.preview, actual = displayOutput(), displayP = actual && state;
    dimensions.textContent = displayP ? `${actual.width.toLocaleString('en-US')} × ${actual.height.toLocaleString('en-US')}${outputAware && readBatchOut() ? ' · ' + (language === 'ja' ? '1枚あたり' : 'per image') : ''}` : '— × —';
    const pixelCount = displayP ? actual.width * actual.height : 0;
    pixels.textContent = displayP ? `${pixelCount.toLocaleString(language)} ${t.pixels} · ${(pixelCount / 1e6).toFixed(2)} MP` : '';
    badge.textContent = t.experimental; badge.hidden = !displayP || (imageNode ? pixelCount <= 16_000_000 : pixelCount <= 1032192);
    warning.textContent = imageNode ? t.imageResolutionWarning : t.resolutionWarning; warning.hidden = badge.hidden;
    metrics.classList.toggle('h3-stale', Boolean(displayP && !current));
    status.textContent = controller.pending ? (displayP ? t.stale : t.pending) : controller.previewError ? `${t.unavailable}${displayP ? ` · ${t.previous}` : ''}` : compatibilityWarning ? t.undoWarning : t.committed;
    const problem = controller.error || localError || controller.previewError;
    errorBox.textContent = problem ? `${controller.error ? `${t.invalid} ` : ''}${errorText(problem, language)}` : ''; errorBox.hidden = !problem;
    retry.textContent = t.retry; retry.hidden = !controller.previewError || !state;
    footer.textContent = activeTab === 'parts' ? t.partGuide : activeTab === 'style' ? t.styleHint : t.caveat;
    const hasExtras = p?.reference_plan?.some(item => item.source.startsWith('reference_image_'));
    const referenceLabels = language === 'ja' ? {character_image: '人物', layout_image: '配置', reference_image_1: '追加参照1', reference_image_2: '追加参照2', reference_image_3: '追加参照3'} : {character_image: 'character', layout_image: 'layout', reference_image_1: 'extra reference 1', reference_image_2: 'extra reference 2', reference_image_3: 'extra reference 3'};
    const numbering = hasExtras ? p.reference_plan.map(item => `Picture ${item.picture_number}: ${referenceLabels[item.source]}`).join(' / ') : useLayoutImage() ? t.layoutReference : t.characterOnly;
    generatedSummary.textContent = `${t.generatedPrompt} · ${numbering}${readStyle() === 'none' ? '' : ` · ${t.style}：${t[`style_${readStyle()}`] ?? readStyle()}`}`;
    generatedText.textContent = current && outputAware && readBatchOut() && p?.batch_plan?.enabled ? p.batch_plan.items.map(item => `${item.index}. ${t[item.view_id]} (${item.width} × ${item.height})\n${item.prompt}`).join('\n\n') : current && typeof p?.prompt === 'string' ? p.prompt : controller.pending ? t.pending : t.unavailable;
    summary.textContent = t.editJSON; rawHint.textContent = t.rawHint; apply.textContent = t.apply;
    jsonDetails.hidden = !controller.error && !controller.previewError;
    if (lastRaw !== controller.raw) { rawInput.value = typeof controller.raw === 'string' ? controller.raw : String(controller.raw); lastRaw = controller.raw; }
    if (controller.error) jsonDetails.open = true;
    renderPreview();
  }
  render();
  return {root, render, flushDrafts, setLocale(value) { language = value === 'ja' ? 'ja' : 'en'; render('locale'); }, dispose() { disposed = true; abort.abort(); resizeObserver?.disconnect(); drafts.clear(); partDrafts.clear(); root.remove(); }, controller};
}
