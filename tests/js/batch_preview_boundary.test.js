import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {validatePreview} from '../../web/state.js';
import {MultiReferenceController} from '../../web/multi_state.js';

test('large batch preview validates all views and allows Manual selection of real item dimensions', t => {
  const result = spawnSync(process.env.H3_PYTHON || 'python', ['-B', '-c', `
import copy,json
from h3_character_sheet.multi_reference_compiler import DEFAULT_MULTI_STATE,MULTI_VIEW_IDS
from h3_character_sheet.output_plan import compile_output_preview
state=copy.deepcopy(DEFAULT_MULTI_STATE);state['views']=list(MULTI_VIEW_IDS);state['size']['body_height']=4480
print(json.dumps(compile_output_preview(json.dumps(state),batch_out=True,max_resolution=16384)))
`], {cwd: new URL('../..', import.meta.url), encoding: 'utf8'});
  assert.equal(result.status, 0, result.stderr);
  const preview = JSON.parse(result.stdout), state = JSON.parse(preview.state_json);
  assert.equal(validatePreview(preview, state), preview); assert.equal(preview.layout.panels.length, 13);
  const controller = new MultiReferenceController({raw: preview.state_json, requestPreview: () => new Promise(() => {})});
  t.after(() => controller.dispose());
  controller.preview = preview; controller.previewRaw = controller.raw; controller.pending = false; controller.maxResolution = 16384;
  const selected = preview.batch_plan.items.find(item => item.view_id === 'body_front');
  controller.setMode('manual', selected);
  assert.equal(controller.state.size.manual_width, selected.width);
  assert.equal(controller.state.size.manual_height, selected.height);
  assert.equal(controller.state.views.length, 13);
});
