import test from 'node:test';
import assert from 'node:assert/strict';
import {avatarSVG} from '../../web/avatar.js';

const views = ['face_front', 'body_front', 'body_left', 'body_back', 'hands', 'feet'];
test('all six decorative SVG views are bounded, self contained, and collision free', () => {
  const ids = new Set();
  for (let instance = 0; instance < 3; instance++) {
    for (const view of views) {
      const svg = avatarSVG(view, 'same-prefix');
      assert.match(svg, /^<svg/);
      assert.match(svg, /viewBox="0 0 160 260"/);
      assert.match(svg, /aria-hidden="true"/);
      assert.doesNotMatch(svg, /<image|<script|<foreignObject|https?:\/\/(?!www\.w3\.org)/);
      const ownIDs = [...svg.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
      for (const id of ownIDs) {
        assert(!ids.has(id), `Duplicate global SVG ID: ${id}`);
        ids.add(id);
      }
      for (const match of svg.matchAll(/url\(#([^)]*)\)/g)) assert(ownIDs.includes(match[1]), `Unresolved gradient: ${match[1]}`);
    }
  }
  assert(ids.size >= 100);
});

test('SVG caller prefixes are sanitized and unknown views rejected', () => {
  const svg = avatarSVG('face_front', '\"<script> bad / prefix');
  assert.doesNotMatch(svg, /<script|bad \/ prefix/);
  assert.throws(() => avatarSVG('unknown'), RangeError);
});
