import test from 'node:test';
import assert from 'node:assert/strict';
import {pathToFileURL} from 'node:url';
import {createArtwork, ATLAS_URL, artworkRect} from '../../web/artwork.js';
import {VIEW_IDS} from '../../web/state.js';
let JSDOM;
try { ({JSDOM} = await import(process.env.H3_JSDOM_PATH ? pathToFileURL(process.env.H3_JSDOM_PATH).href : 'jsdom')); } catch {}

test('normal UI displays GPT Image bitmap; missing local asset alone triggers unique SVG fallback', {skip: !JSDOM && 'Optional jsdom unavailable'}, () => {
  const dom = new JSDOM('<!doctype html><html><body></body></html>');
  const old = globalThis.document;
  globalThis.document = dom.window.document;
  try {
    for (const view of VIEW_IDS) {
      const first = createArtwork(view, 'same');
      const second = createArtwork(view, 'same');
      document.body.append(first, second);
      assert.equal(first.dataset.artworkSource, 'gpt-image');
      assert.equal(first.querySelector('svg').getAttribute('viewBox'), artworkRect(view).join(' '));
      assert.equal(first.querySelector('image').getAttribute('href'), ATLAS_URL);
      assert.equal(first.querySelector('image').getAttribute('clip-path'), `url(#${first.querySelector('clipPath').id})`);
      assert.notEqual(first.querySelector('clipPath').id, second.querySelector('clipPath').id);
      const clipRect = first.querySelector('clipPath rect');
      assert.deepEqual(['x','y','width','height'].map(key => Number(clipRect.getAttribute(key))), artworkRect(view));
      assert.equal(first.querySelector('path'), null, 'Normal rendering is generated bitmap, not vector mannequin');
      for (const frame of [first,second]) frame.querySelector('image').dispatchEvent(new dom.window.Event('error'));
      assert.equal(first.dataset.artworkSource, 'local-fallback');
      assert(first.querySelector('path'));
      const ids = [...document.querySelectorAll('[id]')].map(el => el.id);
      assert.equal(new Set(ids).size, ids.length);
    }
  } finally {
    dom.window.close();
    if (old === undefined) delete globalThis.document; else globalThis.document = old;
  }
});
