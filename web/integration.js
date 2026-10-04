import {DesignerController, getLocale, subscribeLocale} from './state.js';
import {createDesignerUI, translations} from './ui.js';
const instances = new WeakMap();
export const NODE_TYPE = 'H3CharacterSheetDesigner';

export function previewRequester(api) {
  return async (raw, signal) => {
    const response = await api.fetchApi('/h3_character_sheet_designer/preview', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({state_json: raw}), signal,
    });
    let data;
    try { data = await response.json(); } catch { throw new Error(`Preview HTTP ${response.status}`); }
    if (!response.ok) { const error = new Error(data?.error?.message || `Preview HTTP ${response.status}`); error.serverMessage = error.message; error.serverCode = data?.error?.code; throw error; }
    return data;
  };
}
export function graphTransaction(node, change) {
  const graph = node.graph;
  if (typeof graph?.beforeChange === 'function' && typeof graph?.afterChange === 'function') {
    graph.beforeChange(node);
    try { change(); } finally { graph.afterChange(node); }
  } else change();
  node.setDirtyCanvas?.(true, true);
}
/** Chains instance hooks only. Return values and prior hook invocation are retained. */
function chain(node, name, after) {
  const prior = node[name];
  node[name] = function (...args) { const result = prior?.apply(this, args); after.apply(this, args); return result; };
}
function fallback(node, original, app, reason) {
  const message = translations[getLocale(app)].fallback;
  if (original) { original.options ??= {}; original.options.tooltip = message; original.options.dynamicPrompts = false; }
  node.h3DesignerCompatibility = {graphical: false, reason, message};
  console.warn(`[H3 Character Sheet Designer] ${message}`, reason);
  app?.extensionManager?.toast?.add?.({severity: 'warn', summary: 'H3 Character Sheet Designer', detail: message, life: 12000});
  return null;
}
export function installDesigner(node, app, api) {
  if (instances.has(node)) return instances.get(node);
  const original = node.widgets?.find(widget => widget.name === 'state_json');
  if (!original || typeof node.addDOMWidget !== 'function' || typeof document === 'undefined') return fallback(node, original, app, 'DOM widget API unavailable');
  const originalIndex = node.widgets.indexOf(original);
  const raw = original.value; // Never replace a malformed/restored value with defaults.
  const existingWidgets = new Set(node.widgets);
  const previousHooks = Object.fromEntries(['onAdded', 'onRemoved', 'onResize', 'onConfigure'].map(name => [name, node[name]]));
  let ui, widget, unsubscribe = () => {}; 
  const controller = new DesignerController({
    raw, requestPreview: previewRequester(api),
    transaction: change => graphTransaction(node, change),
    onCommit: (next, previous) => { node.onWidgetChanged?.('state_json', next, previous, widget); },
    onChange: (_, reason) => ui?.render(reason),
  });
  try {
    ui = createDesignerUI({controller, locale: getLocale(app), compatibilityWarning: Boolean(node.graph && (typeof node.graph.beforeChange !== 'function' || typeof node.graph.afterChange !== 'function'))});
    widget = node.addDOMWidget('state_json', 'STRING', ui.root, {
      getValue: () => controller.raw,
      setValue: value => controller.restore(value),
      getMinHeight: () => 600, getHeight: () => 600,
      hideOnZoom: false, serialize: true, dynamicPrompts: false,
    });
    if (!widget || !node.widgets.includes(widget)) throw new Error('addDOMWidget did not return an installed widget');
    widget.options ??= {}; widget.options.dynamicPrompts = false; widget.serialize = true;
    // Preserve the original serialization position while retaining one named input.
    const addedIndex = node.widgets.indexOf(widget); node.widgets.splice(addedIndex, 1);
    node.widgets.splice(node.widgets.indexOf(original), 1, widget);
    // Older and current addDOMWidget closures can re-register the retired STRING.
    chain(node, 'onAdded', () => { original.onRemove?.(); });
    unsubscribe = subscribeLocale(app, value => ui.setLocale(value));
    const record = {controller, ui, widget, originalIndex, dispose() {
      if (record.disposed) return; record.disposed = true;
      unsubscribe(); controller.dispose(); ui.dispose(); widget.onRemove?.(); instances.delete(node);
    }, afterConfigure() { if (!record.disposed) controller.restore(widget.value); }};
    instances.set(node, record);
    chain(node, 'onConfigure', () => record.afterConfigure());
    chain(node, 'onRemoved', () => record.dispose());
    node.h3DesignerCompatibility = {graphical: true, undoTransactions: typeof node.graph?.beforeChange === 'function' && typeof node.graph?.afterChange === 'function'};
    if (typeof node.setSize === 'function') node.setSize([Math.max(560, node.size?.[0] || 0), Math.max(650, node.size?.[1] || 0)]);
    ui.render();
    original.onRemove?.(); original.element?.remove?.(); original.inputEl?.remove?.();
    return record;
  } catch (error) {
    unsubscribe(); controller.dispose(); ui?.dispose(); instances.delete(node);
    // addDOMWidget may append/register a widget and then throw before returning.
    for (const added of [...node.widgets]) {
      if (!existingWidgets.has(added)) {
        try { added.onRemove?.(); added.element?.remove?.(); } catch {}
        const index = node.widgets.indexOf(added); if (index >= 0) node.widgets.splice(index, 1);
      }
    }
    for (const [name, prior] of Object.entries(previousHooks)) { if (prior === undefined) delete node[name]; else node[name] = prior; }
    if (!node.widgets.includes(original)) node.widgets.splice(originalIndex, 0, original);
    return fallback(node, original, app, error.message);
  }
}
export function getDesigner(node) { return instances.get(node); }
export function createExtension(app, api) {
  return {
    name: 'h3.CharacterSheetDesigner',
    nodeCreated(node) { if (node.comfyClass === NODE_TYPE || node.type === NODE_TYPE) installDesigner(node, app, api); },
    afterConfigureGraph() {
      for (const node of app.graph?._nodes ?? []) getDesigner(node)?.afterConfigure();
    },
  };
}
