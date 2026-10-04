import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {ATLAS_SIZE, ATLAS_URL, ARTWORK_RECTS, artworkRect} from '../../web/artwork.js';
import {VIEW_IDS} from '../../web/state.js';

test('approved GPT Image atlas is bundled as a real transparent PNG', () => {
  const bytes = readFileSync(fileURLToPath(ATLAS_URL));
  assert.deepEqual([...bytes.subarray(0, 8)], [137,80,78,71,13,10,26,10]);
  assert.equal(bytes.readUInt32BE(16), ATLAS_SIZE[0]);
  assert.equal(bytes.readUInt32BE(20), ATLAS_SIZE[1]);
  assert.equal(bytes[25], 6, 'RGBA PNG expected');
  assert(bytes.length > 100_000, 'Expected full raster artwork, not a placeholder');
});

test('all six atlas viewports are bounded and full bodies share scale', () => {
  assert.deepEqual(Object.keys(ARTWORK_RECTS), VIEW_IDS);
  for (const view of VIEW_IDS) {
    const [x,y,width,height] = artworkRect(view);
    assert(x >= 0 && y >= 0 && width > 0 && height > 0);
    assert(x + width <= ATLAS_SIZE[0] && y + height <= ATLAS_SIZE[1]);
  }
  for (const view of ['body_front','body_left','body_back']) assert.deepEqual(artworkRect(view).slice(2), [350,625]);
  assert.throws(() => artworkRect('unknown'), RangeError);
});
