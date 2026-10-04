import {DEFAULT_JSON, getLocale} from '../../web/state.js';
import {createExtension, getDesigner, NODE_TYPE} from '../../web/integration.js';
const nodesRoot = document.querySelector('#nodes');
const history = [], future = [];
const settings = new EventTarget(); let locale = new URL(location.href).searchParams.get('locale') || 'en';
const app = {graph: {_nodes: []}, extensionManager: {setting: {get: key => key === 'Comfy.Locale' ? locale : undefined}}, ui: {settings}};
let previewDelay = 0, failNext = false;
const api = {fetchApi: async (path, options) => {
  if (previewDelay) await new Promise(resolve => setTimeout(resolve, previewDelay));
  if (failNext) { failNext = false; throw new Error('Simulated network failure'); }
  return fetch(path, options);
}};
const extension = createExtension(app, api); let nodeID = 0;
const graph = app.graph;
graph.beforeChange = () => { history.push(serialize()); future.length = 0; };
graph.afterChange = () => {};
function serialize() { return graph._nodes.map(node => ({id: node.id, widgets_values: node.widgets.map(w => w.value), widgets_values_named: Object.fromEntries(node.widgets.map(w => [w.name, w.value]))})); }
function createNode(raw = DEFAULT_JSON, id) {
  const host = document.createElement('section'); host.className = 'demo-node'; host.innerHTML = '<h2>H3 Character Sheet Designer</h2><div class="ports"><span>prompt ●</span><span>width ●</span><span>height ●</span></div>'; nodesRoot.append(host);
  const node = {id: id ?? ++nodeID, comfyClass: NODE_TYPE, type: NODE_TYPE, widgets: [{name: 'state_json', type: 'STRING', value: raw, options: {}}], graph, size: [560, 650], host,
    addDOMWidget(name, type, element, options) {
      const widget = {name, type, options, element, onRemove() { element.remove(); }};
      Object.defineProperty(widget, 'value', {get: options.getValue, set: options.setValue});
      this.widgets.push(widget); host.append(element); return widget;
    }, setSize(size) { this.size = size; }, setDirtyCanvas() {},
  };
  graph._nodes.push(node); extension.nodeCreated(node); node.onAdded?.(); return node;
}
function restore(data) {
  for (const node of [...graph._nodes]) { node.onRemoved?.(); node.host.remove(); }
  graph._nodes.length = 0;
  for (const saved of data) { const node = createNode(DEFAULT_JSON, saved.id); node.widgets.find(w => w.name === 'state_json').value = saved.widgets_values_named?.state_json ?? saved.widgets_values[0]; node.onConfigure?.(saved); }
  extension.afterConfigureGraph();
}
createNode();
const select = document.querySelector('#locale'); select.value = locale;
select.addEventListener('change', () => { locale = select.value; settings.dispatchEvent(new Event('Comfy.Locale.change')); });
document.querySelector('#undo').onclick = () => { if (history.length) { future.push(serialize()); restore(history.pop()); } };
document.querySelector('#redo').onclick = () => { if (future.length) { history.push(serialize()); restore(future.pop()); } };
document.querySelector('#duplicate').onclick = () => { const raw = graph._nodes.at(-1)?.widgets.find(w => w.name === 'state_json').value; if (raw !== undefined) createNode(raw); };
document.querySelector('#reload').onclick = () => restore(serialize());
document.querySelector('#queue').onclick = () => { const inputs = graph._nodes.map(node => ({class_type: NODE_TYPE, inputs: {state_json: node.widgets.find(w => w.name === 'state_json').value}})); document.querySelector('#snapshot').textContent = JSON.stringify(inputs, null, 2); };
document.querySelector('#narrow').onclick = () => { for (const node of graph._nodes) node.host.style.width = node.host.style.width === '360px' ? '560px' : '360px'; };
document.querySelector('#remove').onclick = () => { const node = graph._nodes.pop(); node?.onRemoved?.(); node?.host.remove(); };
window.h3Harness = {app, serialize, restore, createNode, getDesigner, history, future, getLocale: () => getLocale(app), setDelay(value) { previewDelay = value; }, failNext() { failNext = true; }};
