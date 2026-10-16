/** Reuse the installed PNGs; H3's left profile points to screen right. */
import {createArtwork} from './artwork.js';
export {createArtwork};
export function createGuideArtwork(panel, canvas, id) {
  const box = document.createElement('div');
  const [x, y, w, h] = panel.rect;
  Object.assign(box.style, {position: 'absolute', left: `${x/canvas[0]*100}%`, top: `${y/canvas[1]*100}%`, width: `${w/canvas[0]*100}%`, height: `${h/canvas[1]*100}%`});
  const art = createArtwork(panel.id, id, {crop: panel.crop, mirror: panel.mirror});
  Object.assign(art.style, {width: '100%', height: '100%', display: 'block'});
  box.append(art); return box;
}
