/** Display-only output gallery. Geometry comes exclusively from the CPU plan. */
export function selectedOutput(preview, enabled, activeIndex = 0) {
  return enabled && preview?.batch_plan?.enabled
    ? preview.batch_plan.items[Math.min(activeIndex, preview.batch_plan.items.length - 1)] ?? preview
    : preview;
}

export function renderOutputGallery(root, plan, {prefix, id, label, createArtwork, mirrored, garmentOnly, activeIndex, onSelect}) {
  root.replaceChildren();
  for (const [index, item] of plan.items.entries()) {
    const card = document.createElement('button'); card.type = 'button';
    card.className = `${prefix}-output-card`; card.dataset.outputView = item.view_id;
    card.setAttribute('aria-pressed', String(index === activeIndex));
    card.addEventListener('click', () => onSelect(index));
    const title = document.createElement('span'); title.className = `${prefix}-output-title`;
    title.textContent = `${item.index}. ${label(item.view_id)} · ${item.width} × ${item.height}`;
    const canvas = document.createElement('div'); canvas.className = `${prefix}-output-canvas`;
    canvas.dataset.outputCanvas = item.view_id;
    canvas.style.aspectRatio = `${item.width} / ${item.height}`;
    canvas.dataset.width = String(item.width); canvas.dataset.height = String(item.height);
    for (const panel of item.layout.panels) {
      const box = document.createElement('div'); box.className = `${prefix}-panel`;
      box.dataset.panel = panel.id; box.setAttribute('aria-label', label(panel.id));
      const [left, top, width, height] = panel.rect;
      Object.assign(box.style, {left: `${left * 100}%`, top: `${top * 100}%`, width: `${width * 100}%`, height: `${height * 100}%`});
      const placement = item.guide_artwork?.[panel.id];
      if (!(garmentOnly && panel.id.startsWith('clothing_'))) {
        const art = document.createElement('div');
        if (placement) {
          const [x, y, w, h] = placement.rect;
          Object.assign(art.style, {position: 'absolute', left: `${(x / item.width - left) / width * 100}%`, top: `${(y / item.height - top) / height * 100}%`, width: `${w / item.width / width * 100}%`, height: `${h / item.height / height * 100}%`});
        } else Object.assign(art.style, {width: '100%', height: '100%'});
        art.append(createArtwork(panel.id, `${id}-output-${index}-${panel.id}`, {crop: placement?.crop, mirror: mirrored.includes(panel.id)}));
        box.append(art);
      }
      canvas.append(box);
    }
    card.append(title, canvas); root.append(card);
  }
}
