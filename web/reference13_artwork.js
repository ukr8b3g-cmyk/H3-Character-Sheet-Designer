/** Reuse the installed PNGs; H3's left profile points to screen right. */
import {createArtwork as legacyArtwork} from './artwork.js';
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
