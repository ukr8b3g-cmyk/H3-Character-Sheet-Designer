import {VIEW_IDS, PART_IDS, PART_PROMPT_MAX_LENGTH, PRESETS, presetOf, StateError} from './state.js';
import {createArtwork} from './artwork.js';
let sequence = 0;
export const HEIGHT_PRESETS = [672, 896, 1120, 1344, 1792];
const EN = {
  intro: 'Choose the views for your character sheet', selected: 'selected',
  face_front: 'Portrait', face_left: 'Left portrait', body_front: 'Front', body_left: 'Left side', body_back: 'Back', hands: 'Hands', feet: 'Footwear',
  face_front_tip: 'Front-facing face to chest', face_left_tip: 'Head to chest, camera facing the subject’s anatomical left side', body_front_tip: 'Full body, head to soles', body_left_tip: "Camera looks directly at the subject’s anatomical left side", body_back_tip: 'Direct rear view, full body', hands_tip: 'Both hands; retain gloves from the reference', feet_tip: 'Separate close-up of both feet in reference footwear; visible boot shafts retained',
  preset: 'Preset', basic: 'Basic · 4 views', detail: 'Detail · 7 views', turnaround: 'Turnaround · 3', single: 'Single view', custom: 'Custom',
  auto: 'Auto', manual: 'Manual', size: 'Output size', bodyHeight: 'Panel height', width: 'Width', height: 'Height', returnAuto: 'Back to Auto', updating: 'Updating dimensions…',
  customHeight: 'Custom panel height', customHeightChoice: 'Custom…',
  autoHint: 'Auto keeps the requested full-body panel height.', manualHint: 'Manual keeps your canvas size when views change.',
  layout: 'SHEET PREVIEW', diagram: 'Layout guide', experimental: 'Experimental', pixels: 'pixels',
  caveat: 'A prompt layout guide. Exact geometry and generation quality are not guaranteed.',
  resolutionWarning: 'High resolution uses the full H3 generation path. VRAM and processing time vary.',
  committed: 'Saved immediately', pending: 'Updating layout…', stale: 'Previous layout · updating', previous: 'Previous layout', unavailable: 'Preview unavailable', retry: 'Retry preview', empty: 'Waiting for Python layout',
  draft: 'Uncommitted values are not saved or queued.', invalid: 'Saved JSON is invalid. Its original value is preserved.', editJSON: 'Repair saved JSON', apply: 'Apply valid JSON', rawHint: 'Only Apply changes the saved input.',
  lastView: 'Keep at least one view selected.', sizeError: 'Enter a whole number of at least 32, in steps of 32.', maxSize: 'Exceeds the ComfyUI resolution limit.', integer: 'JSON integer fields cannot use decimal or exponent notation.', version: 'Only schema_version 1 or 2 is supported.', views: 'Select one or more of the seven known view IDs.', json: 'The JSON syntax is invalid.', duplicateKey: 'Duplicate JSON key', keys: 'Unknown or missing JSON keys', oversize: 'JSON must be no larger than 64 KiB.', mode: 'Size mode must be auto or manual.', object: 'Expected a JSON object', string: 'state_json must be a string.', preview: 'The server returned an invalid preview.', timeout: 'Preview timed out. The saved selection is unchanged.', network: 'Could not reach the preview endpoint. Queue still validates on the server.',
  fallback: 'Graphical designer unavailable. Edit the normal state_json string; Python compilation is still available.',
  layoutTab: 'Layout', partsTab: 'Part prompts', part: 'Body part', partPrompt: 'Prompt', partCount: 'parts specified',
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
  preset: 'プリセット', basic: '基本4面', detail: '7面・ディテール', turnaround: '三面図のみ', single: '1カット', custom: 'カスタム',
  auto: 'Auto', manual: 'Manual', size: '出力サイズ', bodyHeight: '基準高', width: '幅', height: '高さ', returnAuto: 'Autoに戻す', updating: '寸法更新中…',
  customHeight: '基準高を手入力', customHeightChoice: '手入力…',
  autoHint: 'Autoは指定した全身パネルの高さを維持します。', manualHint: 'Manualはビューを変えても幅・高さを維持します。',
  layout: 'シートプレビュー', diagram: '配置ガイド', experimental: 'Experimental', pixels: '画素',
  caveat: '配置はプロンプト上の指示です。正確な形状や生成品質は保証しません。',
  resolutionWarning: '高解像度は通常のH3生成経路を使います。VRAM・処理時間は環境に依存します。',
  committed: '選択は即時保存', pending: '配置更新中…', stale: '前の配置・更新中', previous: '前の配置', unavailable: 'プレビュー取得失敗', retry: '再試行', empty: 'Pythonの配置を取得中',
  draft: '未確定の値は保存・実行されません。', invalid: '保存JSONが不正です。原文を保持しています。', editJSON: '保存JSONを修正', apply: '有効なJSONを適用', rawHint: '「適用」を押したときだけ保存値を変更します。',
  lastView: '最低1つのビューを選択してください。', sizeError: '32以上の32倍数を整数で入力してください。', maxSize: 'ComfyUIの解像度上限を超えています。', integer: 'JSONの整数項目に小数・指数表記は使えません。', version: 'schema_versionは整数の1または2に対応しています。', views: '既知の7種類から1つ以上のビューを指定してください。', json: 'JSONの構文が不正です。', duplicateKey: 'JSONキーが重複しています', keys: 'JSONキーの不足または未知のキー', oversize: 'JSONは64 KiB以内にしてください。', mode: 'size.modeはautoまたはmanualにしてください。', object: 'JSONオブジェクトが必要です', string: 'state_jsonは文字列で指定してください。', preview: 'サーバーからのプレビューが不正です。', timeout: 'プレビューがタイムアウトしました。保存済み選択は維持しています。', network: 'プレビューを取得できません。Queue時にはサーバーで検証されます。',
  fallback: 'GUIデザイナーを利用できません。通常のstate_json文字列を編集してください。Python実行は利用可能です。',
  layoutTab: 'レイアウト', partsTab: '部位指定', part: '部位', partPrompt: 'プロンプト', partCount: '部位を指定中',
  partPlaceholder: '色・形・柄・文字・位置などを自由に入力',
  partHint: '部位ごとの指示を、関連する選択ビューへ共通で反映します。空欄なら参照画像に従います。',
  partSaved: '入力は即時保存。Enterで改行します。', partGuide: 'マネキンは配置確認用です。部位指定の見た目はプレビューに反映しません。',
  head_hair_part: '頭・髪', face_part: '顔', upper_clothing_part: '上半身の服', back_clothing_part: '背面の服', lower_body_part: '下半身', hands_part: '手・手袋', footwear_part: '足・履物', other_part: '全体・その他',
  partText: '部位プロンプトは文字列で入力してください。', parts: '未知の部位です。', partLength: '各プロンプトは1000文字以内にしてください（絵文字などは複数文字分）。', partUnicode: 'プロンプトに不正なUnicodeが含まれています。',
  undoWarning: 'このfrontendでは必要なUndoトランザクションAPIを確認できません。',
};
export const translations = {en: EN, ja: JA};
export function errorText(error, locale = 'en') {
  const t = translations[locale] ?? EN;
  if (error instanceof StateError) {
    const key = error.code === 'size' ? 'sizeError' : error.code;
    return `${t[key] ?? t.network}${['duplicateKey', 'keys', 'object', 'maxSize'].includes(error.code) && error.detail ? ` (${error.detail})` : ''}`;
  }
  const serverCodes = {duplicate_key: 'duplicateKey', non_finite: 'integer', invalid_integer: 'integer', invalid_size: 'sizeError', size_limit: 'maxSize', unsupported_schema: 'version', empty_views: 'views', unknown_view: 'views', invalid_mode: 'mode', missing_key: 'keys', unknown_key: 'keys', invalid_json: 'json', invalid_utf8: 'json', state_too_large: 'oversize', request_too_large: 'oversize', unknown_part: 'parts', part_prompt_too_long: 'partLength'};
  return error?.serverCode && serverCodes[error.serverCode] ? t[serverCodes[error.serverCode]] : error?.serverMessage || t.network;
}
function element(tag, className, text) { const el = document.createElement(tag); if (className) el.className = className; if (text) el.textContent = text; return el; }
const button = className => { const el = element('button', className); el.type = 'button'; return el; };
export function loadStyles() {
  if (document.querySelector('link[data-h3-character-sheet]')) return;
  const link = document.createElement('link'); link.rel = 'stylesheet'; link.href = new URL('./style.css', import.meta.url).href; link.dataset.h3CharacterSheet = ''; document.head.append(link);
}

/** Real UI renderer shared by the ComfyUI extension and the browser test harness. */
export function createDesignerUI({controller, locale = 'en', compatibilityWarning = false}) {
  loadStyles();
  const id = `h3-sheet-${++sequence}`;
  const root = element('section', 'h3-designer'); root.dataset.instance = id; root.setAttribute('aria-label', 'H3 Character Sheet Designer');
  const abort = new AbortController(); const listen = (el, type, handler) => el.addEventListener(type, handler, {signal: abort.signal});
  let language = locale, t = translations[locale] ?? EN, disposed = false;
  const partDrafts = new Map(); let selectedPart = PART_IDS[0], activeTab = 'layout';
  const drafts = new Map(); let customHeight = false; let localError = null, lastRaw = Symbol(), lastPreviewKey = null;
  const header = element('div', 'h3-intro'), intro = element('span'), count = element('span', 'h3-count'); header.append(intro, count);
  const cards = element('div', 'h3-cards'), cardMap = new Map();
  for (const view of VIEW_IDS) {
    const card = button('h3-card'); card.dataset.view = view;
    const figure = element('span', 'h3-card-figure'); figure.append(createArtwork(view, `${id}-card-${view}`));
    const check = element('span', 'h3-check', '✓'); check.setAttribute('aria-hidden', 'true');
    const label = element('span', 'h3-card-label'); card.append(figure, check, label);
    listen(card, 'click', () => act(() => controller.toggle(view)));
    cards.append(card); cardMap.set(view, {card, label});
  }
  const presetRow = element('div', 'h3-preset-row'), presetLabel = element('label'), preset = element('select', 'h3-select'); preset.id = `${id}-preset`; presetLabel.htmlFor = preset.id;
  for (const name of [...Object.keys(PRESETS), 'custom']) { const option = element('option'); option.value = name; option.disabled = name === 'custom'; preset.append(option); }
  presetRow.append(presetLabel, preset); listen(preset, 'change', () => act(() => controller.preset(preset.value)));
  const controls = element('div', 'h3-controls');
  const modeRow = element('div', 'h3-mode-row'), sizeLabel = element('span', 'h3-field-title'), modeGroup = element('div', 'h3-mode-group');
  const auto = button('h3-mode'), manual = button('h3-mode'); auto.dataset.mode = 'auto'; manual.dataset.mode = 'manual'; modeGroup.append(auto, manual); modeRow.append(sizeLabel, modeGroup);
  listen(auto, 'click', () => act(() => controller.setMode('auto'))); listen(manual, 'click', () => act(() => controller.setMode('manual')));
  const numberRow = element('div', 'h3-number-row'), fields = new Map();
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
  const previewHead = element('div', 'h3-preview-head'), tabs = element('div', 'h3-tabs'), previewTag = element('span', 'h3-preview-tag');
  tabs.setAttribute('role', 'tablist'); const tabMap = new Map();
  for (const name of ['layout', 'parts']) {
    const tab = button('h3-tab'); tab.id = `${id}-${name}-tab`; tab.dataset.tab = name;
    tab.setAttribute('role', 'tab'); tab.setAttribute('aria-controls', `${id}-${name}-panel`);
    listen(tab, 'click', () => { activeTab = name; render(); });
    listen(tab, 'keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault(); event.stopPropagation();
      activeTab = event.key === 'Home' ? 'layout' : event.key === 'End' ? 'parts' : activeTab === 'layout' ? 'parts' : 'layout';
      render(); tabMap.get(activeTab).focus();
    });
    tabs.append(tab); tabMap.set(name, tab);
  }
  previewHead.append(tabs, previewTag);
  const stage = element('div', 'h3-stage'); stage.id = `${id}-layout-panel`; stage.setAttribute('role', 'tabpanel'); stage.setAttribute('aria-labelledby', `${id}-layout-tab`); stage.tabIndex = 0;
  stage.dataset.previewStage = ''; const canvas = element('div', 'h3-sheet'); const empty = element('div', 'h3-empty'); stage.append(canvas, empty);
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
  // Persist synchronously on every input, including IME input. Do not rewrite an
  // unchanged textarea value while composing, so the caret and composition live on.
  listen(partInput, 'input', () => commitPart());
  listen(partInput, 'keydown', event => event.stopPropagation()); // Enter remains a native newline.
  listen(partSelect, 'change', () => { selectedPart = partSelect.value; render(); });
  const footer = element('div', 'h3-footer');
  const jsonDetails = element('details', 'h3-json-editor'), summary = element('summary'), rawInput = element('textarea'), rawHint = element('p'), apply = button('h3-apply'); rawInput.spellcheck = false; rawInput.setAttribute('aria-label', 'state_json');
  listen(apply, 'click', () => act(() => controller.applyRaw(rawInput.value))); jsonDetails.append(summary, rawInput, rawHint, apply);
  root.append(header, cards, presetRow, controls, metrics, warning, status, errorBox, retry, previewHead, stage, partPanel, footer, jsonDetails);
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
    tabs.setAttribute('aria-label', t.diagram);
    for (const [name, tab] of tabMap) {
      tab.textContent = name === 'layout' ? t.layoutTab : `${t.partsTab}${Object.keys(prompts).length ? ` (${Object.keys(prompts).length})` : ''}`;
      tab.setAttribute('aria-selected', String(name === activeTab)); tab.tabIndex = name === activeTab ? 0 : -1;
    }
    stage.hidden = activeTab !== 'layout'; partPanel.hidden = activeTab !== 'parts';
    previewTag.textContent = activeTab === 'layout' ? t.diagram : t.partSaved;
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
  function renderFields() {
    const state = controller.state;
    for (const [field, item] of fields) {
      const draft = drafts.get(field), active = state && (field === 'body_height' ? state.size.mode === 'auto' : state.size.mode === 'manual');
      item.label.textContent = t[item.labelKey]; item.input.disabled = !active;
      const autoDimension = state?.size.mode === 'auto' && field !== 'body_height';
      const displayValue = autoDimension ? (controller.preview ? String(field === 'manual_width' ? controller.preview.width : controller.preview.height) : '—') : state ? String(state.size[field]) : '';
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
    const p = controller.preview; if (!p || !stage.clientWidth) return;
    const availableW = Math.max(1, stage.clientWidth - 30), availableH = Math.max(1, stage.clientHeight - 28);
    const scale = Math.min(availableW / p.width, availableH / p.height);
    canvas.style.width = `${p.width * scale}px`; canvas.style.height = `${p.height * scale}px`;
  }
  function renderPreview() {
    const p = controller.preview, valid = Boolean(p && controller.state);
    canvas.hidden = !valid; empty.hidden = valid;
    empty.textContent = controller.error ? t.invalid : controller.previewError ? t.unavailable : t.empty;
    const key = valid ? JSON.stringify(p.layout) : null;
    if (key !== lastPreviewKey) {
      canvas.replaceChildren(); lastPreviewKey = key;
      if (valid) {
        for (const panel of p.layout.panels) {
          const box = element('div', 'h3-panel'); box.dataset.panel = panel.id;
          const [left, top, width, height] = panel.rect;
          Object.assign(box.style, {left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%`});
          box.append(createArtwork(panel.id, `${id}-preview-${panel.id}`));
          canvas.append(box);
        }
        if (p.layout.feet_y !== null) { const line = element('div', 'h3-baseline'); line.style.top = `${p.layout.feet_y * 100}%`; canvas.append(line); }
      }
    }
    for (const box of canvas.querySelectorAll('[data-panel]')) box.setAttribute('aria-label', t[box.dataset.panel]);
    stage.classList.toggle('h3-stale', !controller.isCurrentPreview && valid);
    stage.setAttribute('aria-busy', String(controller.pending)); fitSheet();
  }
  function render(reason) {
    if (disposed) return;
    if (reason === 'restore') { drafts.clear(); partDrafts.clear(); customHeight = false; localError = null; }
    t = translations[language] ?? EN; root.lang = language;
    const state = controller.state, current = controller.isCurrentPreview;
    intro.textContent = t.intro; count.textContent = `${state?.views.length ?? 0} / ${VIEW_IDS.length} ${t.selected}`;
    for (const [view, {card, label}] of cardMap) { card.setAttribute('aria-pressed', String(Boolean(state?.views.includes(view)))); card.disabled = !state; card.title = t[`${view}_tip`]; card.setAttribute('aria-label', `${t[view]}: ${t[`${view}_tip`]}`); label.textContent = t[view]; }
    presetLabel.textContent = t.preset; preset.disabled = !state; preset.value = presetOf(state);
    for (const option of preset.options) option.textContent = t[option.value];
    auto.textContent = t.auto; manual.textContent = state?.size.mode === 'auto' && !current ? t.updating : t.manual;
    auto.disabled = !state; manual.disabled = !state || (state.size.mode === 'auto' && !current);
    auto.setAttribute('aria-pressed', String(state?.size.mode === 'auto')); manual.setAttribute('aria-pressed', String(state?.size.mode === 'manual'));
    sizeLabel.textContent = t.size; returnAuto.textContent = t.returnAuto; returnAuto.hidden = state?.size.mode !== 'manual';
    modeHint.textContent = state?.size.mode === 'manual' ? t.manualHint : t.autoHint;
    renderFields(); renderParts();
    const p = controller.preview, displayP = p && state;
    dimensions.textContent = displayP ? `${p.width.toLocaleString('en-US')} × ${p.height.toLocaleString('en-US')}` : '— × —';
    const pixelCount = displayP ? p.width * p.height : 0;
    pixels.textContent = displayP ? `${pixelCount.toLocaleString(language)} ${t.pixels} · ${(pixelCount / 1e6).toFixed(2)} MP` : '';
    badge.textContent = t.experimental; badge.hidden = !displayP || pixelCount <= 1032192;
    warning.textContent = t.resolutionWarning; warning.hidden = badge.hidden;
    metrics.classList.toggle('h3-stale', Boolean(displayP && !current));
    status.textContent = controller.pending ? (displayP ? t.stale : t.pending) : controller.previewError ? `${t.unavailable}${displayP ? ` · ${t.previous}` : ''}` : compatibilityWarning ? t.undoWarning : t.committed;
    const problem = controller.error || localError || controller.previewError;
    errorBox.textContent = problem ? `${controller.error ? `${t.invalid} ` : ''}${errorText(problem, language)}` : ''; errorBox.hidden = !problem;
    retry.textContent = t.retry; retry.hidden = !controller.previewError || !state;
    footer.textContent = activeTab === 'parts' ? t.partGuide : t.caveat;
    summary.textContent = t.editJSON; rawHint.textContent = t.rawHint; apply.textContent = t.apply;
    jsonDetails.hidden = !controller.error;
    if (lastRaw !== controller.raw) { rawInput.value = typeof controller.raw === 'string' ? controller.raw : String(controller.raw); lastRaw = controller.raw; }
    if (controller.error) jsonDetails.open = true;
    renderPreview();
  }
  render();
  return {root, render, setLocale(value) { language = value === 'ja' ? 'ja' : 'en'; render('locale'); }, dispose() { disposed = true; abort.abort(); resizeObserver?.disconnect(); drafts.clear(); partDrafts.clear(); root.remove(); }, controller};
}
