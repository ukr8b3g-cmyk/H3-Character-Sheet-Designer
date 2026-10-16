import test from 'node:test';
import assert from 'node:assert/strict';
import {selectedOutput,renderOutputGallery} from '../../web/output_preview.js';

class Element {
  constructor(tag) { this.tag=tag; this.style={}; this.dataset={}; this.children=[]; this.attrs={}; this.events={}; }
  append(...items) { this.children.push(...items); }
  replaceChildren() { this.children=[]; }
  setAttribute(key,value) { this.attrs[key]=value; }
  addEventListener(name,fn) { this.events[name]=fn; }
}
test('Batch gallery uses individual canvas sizes, one panel and display-only selection',()=>{
  const previous=globalThis.document;
  globalThis.document={createElement:tag=>new Element(tag)};
  try {
    const items=[['face_front',1024,1024],['body_front',768,1344]].map(([view_id,width,height],index)=>({
      index:index+1,view_id,width,height,layout:{panels:[{id:view_id,rect:[.02,.02,.96,.96]}]},
      guide_artwork:{[view_id]:{rect:[20,20,Math.floor(width*.8),Math.floor(height*.8)]}},
    }));
    const preview={width:2816,height:1280,batch_plan:{enabled:true,items}};
    assert.equal(selectedOutput(preview,true,1),items[1]);
    assert.equal(selectedOutput(preview,false,1),preview);
    const root=new Element('div'); let chosen=-1;
    renderOutputGallery(root,preview.batch_plan,{prefix:'test',id:'fixture',label:id=>id,createArtwork:()=>new Element('img'),mirrored:[],garmentOnly:false,activeIndex:0,onSelect:index=>{chosen=index;}});
    assert.equal(root.children.length,2);
    for (const [i,card] of root.children.entries()) {
      const canvas=card.children[1];
      assert.equal(canvas.style.aspectRatio,`${items[i].width} / ${items[i].height}`);
      assert.equal(canvas.children.length,1);
      assert.equal(canvas.children[0].dataset.panel,items[i].view_id);
    }
    root.children[1].events.click(); assert.equal(chosen,1);
    assert.equal(preview.width,2816);
  } finally { globalThis.document=previous; }
});
