/** Reuse the installed PNGs; H3's left profile points to screen right. */
import {createArtwork as legacyArtwork} from './artwork.js';
// All six preview icons share the same frontal silhouette.
const expressionFeatures = {
  expression_neutral: 'M24 30h4m8 0h4 M28 39h8',
  expression_joy: 'M23 31q3-5 6 0m6 0q3-5 6 0 M26 37q6 9 12 0',
  expression_surprise: 'M23 26q3-3 6-1m6 0q3-2 6 1 M25 30v2m14-2v2 M32 36a3 4 0 1 0 .1 0z',
  expression_anger: 'M22 26l7 3m6 0 7-3 M25 32h3m8 0h3 M27 40q5-4 10 0',
  expression_sadness: 'M22 29l7-3m6 0 7 3 M23 32q3 3 6 0m6 0q3 3 6 0 M24 35l-1 4m17-4 1 4 M27 42q5-7 10 0',
  expression_confusion: 'M22 27l7-3m6 0 7 3 M23 32q2-5 5-1-2 3-5 1zm13-1q3-4 5 1-3 2-5-1z M26 40l3-2 3 2 3-2 3 2',
};
export function createExpressionOutline(view) {
  const ns = 'http://www.w3.org/2000/svg';
  const icon = document.createElementNS(ns, 'svg');
  icon.setAttribute('viewBox', '0 0 64 64');
  icon.setAttribute('aria-hidden', 'true');
  for (const d of [
    'M9 60q1-7 12-10l5-2v-4m12 0v4l5 2q11 3 12 10 M32 9c-9 0-15 7-15 18 0 10 7 20 15 20s15-10 15-20c0-11-6-18-15-18z',
    expressionFeatures[view],
  ]) {
    const path = document.createElementNS(ns, 'path');
    path.setAttribute('d', d);
    icon.append(path);
  }
  return icon;
}
export function createArtwork(view, id, options = {}) {
  if (!options.garment || !view.startsWith('clothing_')) return legacyArtwork(view, id, options);
  const frame = document.createElement('span'); frame.className = 'h3-artwork'; frame.dataset.artwork = view;
  const img = document.createElement('img'); img.alt = ''; img.src = new URL('./assets/' + view + '_garment.png', import.meta.url).href;
  frame.append(img); return frame;
}
export function createGuideArtwork(panel, canvas, id) {
  const box = document.createElement('div');
  const [x, y, w, h] = panel.rect;
  Object.assign(box.style, {position: 'absolute', left: `${x/canvas[0]*100}%`, top: `${y/canvas[1]*100}%`, width: `${w/canvas[0]*100}%`, height: `${h/canvas[1]*100}%`});
  const art = createArtwork(panel.id, id, {crop: panel.crop, mirror: panel.mirror, garment: panel.source?.endsWith('_garment.png')});
  Object.assign(art.style, {width: '100%', height: '100%', display: 'block'});
  box.append(art); return box;
}
