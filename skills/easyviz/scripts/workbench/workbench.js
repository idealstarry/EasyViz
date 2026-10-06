'use strict';
const $ = (id) => document.getElementById(id);
let state, svg, annotations = [], activeNumber = null, nextNumber = 1, mode = 'element', drag = null;
let generalDraft = null;
let loading = false, saving = false, operating = false;
let attempts = [], activeJob = null, jobTimer = null, serviceRevision = 0, jobStatusError = null;
let agentConnection = null, libraryVisible = false, agentTimer = null, agentRevision = 0;
let comparisonVisible = true;
let storageUnavailable = false;
const NS = 'http://www.w3.org/2000/svg';
const dropdowns = new Map();
const pages = {annotations:{page:0,size:12},requests:{page:0,size:3},history:{page:0,size:3}};
function pageItems(items, name) {
  const page=pages[name],count=Math.max(1,Math.ceil(items.length/page.size));
  page.page=Math.max(0,Math.min(page.page,count-1));
  page.count=count;
  $(name+'-pager').hidden=count===1;
  $(name+'-page').textContent=`${page.page+1} / ${count}`;
  $(name+'-previous').disabled=loading||saving||operating||page.page===0;
  $(name+'-next').disabled=loading||saving||operating||page.page===count-1;
  return items.slice(page.page*page.size,(page.page+1)*page.size);
}
function readNote(title, text) {
  $('note-dialog-title').textContent=title;
  $('note-dialog-text').textContent=text;
  $('note-dialog').showModal();
}
function readButton(label, title, text) {
  const button=document.createElement('button');button.type='button';button.className='text-button';button.textContent=label;
  button.addEventListener('click',()=>readNote(title,text));
  return button;
}
function closeDropdown(entry) {
  entry.menu.hidden = true;
  entry.trigger.setAttribute('aria-expanded', 'false');
  entry.trigger.removeAttribute('aria-activedescendant');
  entry.wrapper.classList.remove('open');
}
function activateOption(entry, index) {
  if (!entry.items.length) return;
  entry.active = Math.max(0, Math.min(index, entry.items.length-1));
  for (const [i, item] of entry.items.entries()) item.classList.toggle('active', i===entry.active);
  const item = entry.items[entry.active];
  entry.trigger.setAttribute('aria-activedescendant', item.id);
  const top = item.offsetTop, bottom = top + item.offsetHeight;
  if (top < entry.menu.scrollTop) entry.menu.scrollTop = top;
  else if (bottom > entry.menu.scrollTop + entry.menu.clientHeight) entry.menu.scrollTop = bottom - entry.menu.clientHeight;
}
function openDropdown(entry) {
  for (const other of dropdowns.values()) if (other !== entry) closeDropdown(other);
  entry.menu.hidden = false;
  entry.trigger.setAttribute('aria-expanded', 'true');
  entry.wrapper.classList.add('open');
  activateOption(entry, Math.max(0, entry.values.indexOf(entry.select.value)));
}
function chooseOption(entry, index) {
  entry.select.value = entry.values[index];
  entry.select.dispatchEvent(new Event('change', {bubbles:true}));
  closeDropdown(entry);
  entry.trigger.focus({preventScroll:true});
}
function syncDropdown(id) {
  const select = $(id);
  // The plain select remains the state source and the no-JavaScript fallback.
  if (!select?.ownerDocument) return;
  let entry = dropdowns.get(id);
  if (!entry) {
    const wrapper = document.createElement('div'); wrapper.className = 'select-control';
    const trigger = document.createElement('button'); trigger.type = 'button'; trigger.id = id+'-control';
    trigger.className = 'select-trigger'; trigger.setAttribute('role', 'combobox');
    trigger.setAttribute('aria-haspopup', 'listbox'); trigger.setAttribute('aria-expanded', 'false');
    const label = document.querySelector('label[for="'+id+'"]');
    if (label) { label.id = id+'-label'; label.htmlFor = trigger.id; trigger.setAttribute('aria-labelledby', label.id); }
    const text = document.createElement('span'); text.className = 'select-text';
    const arrow = document.createElementNS(NS,'svg'); arrow.setAttribute('viewBox','0 0 16 16'); arrow.setAttribute('aria-hidden','true');
    const path = document.createElementNS(NS,'path'); path.setAttribute('d','M4 6 8 10 12 6'); arrow.append(path);
    trigger.append(text, arrow);
    const menu = document.createElement('ul'); menu.className = 'select-menu'; menu.id = id+'-options'; menu.hidden = true;
    menu.setAttribute('role', 'listbox'); menu.setAttribute('aria-labelledby', label?.id || trigger.id);
    trigger.setAttribute('aria-controls', menu.id);
    select.before(wrapper); wrapper.append(select,trigger,menu); select.hidden = true;
    entry = {select,wrapper,trigger,text,menu,items:[],values:[],active:0,typed:'',typedAt:0}; dropdowns.set(id,entry);
    trigger.addEventListener('click', () => entry.menu.hidden ? openDropdown(entry) : closeDropdown(entry));
    trigger.addEventListener('keydown', event => {
      const open = !entry.menu.hidden;
      if (event.key==='Escape') { event.preventDefault(); closeDropdown(entry); return; }
      if (event.key==='Tab') { closeDropdown(entry); return; }
      if (['Enter',' '].includes(event.key)) { event.preventDefault(); open ? chooseOption(entry,entry.active) : openDropdown(entry); return; }
      if (['ArrowDown','ArrowUp','Home','End'].includes(event.key)) {
        event.preventDefault(); if (!open) openDropdown(entry);
        const index = event.key==='Home' ? 0 : event.key==='End' ? entry.items.length-1 : open ? entry.active+(event.key==='ArrowDown'?1:-1) : entry.active;
        activateOption(entry,index); return;
      }
      if (event.key.length===1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault(); if (!open) openDropdown(entry);
        const now = Date.now(); entry.typed = (now-entry.typedAt>800?'':entry.typed)+event.key.toLowerCase(); entry.typedAt = now;
        const index = entry.items.findIndex(item=>item.textContent.toLowerCase().startsWith(entry.typed));
        if (index>=0) activateOption(entry,index);
      }
    });
    select.addEventListener('change', () => syncDropdown(id));
    document.addEventListener('pointerdown', event => { if (!wrapper.contains(event.target)) closeDropdown(entry); });
  }
  closeDropdown(entry);
  entry.trigger.disabled = select.disabled;
  entry.text.textContent = select.selectedOptions[0]?.textContent || select.options[0]?.textContent || '';
  entry.menu.replaceChildren(); entry.items=[]; entry.values=[];
  for (const option of select.options) {
    if (option.disabled) continue;
    const index = entry.items.length, item = document.createElement('li');
    item.id = id+'-option-'+index; item.setAttribute('role','option'); item.setAttribute('aria-selected',String(option.selected));
    item.textContent = option.textContent; item.addEventListener('click',()=>chooseOption(entry,index));
    item.addEventListener('pointermove',()=>activateOption(entry,index));
    entry.items.push(item); entry.values.push(option.value); entry.menu.append(item);
  }
}
const propertyNames = { color:'Color', facecolor:'Fill color', edgecolor:'Outline color', linewidth:'Line width (pt)', line_width_pt:'Line width (pt)', text:'Text', position:'Position', position_mm:'Position (mm)', layout:'Layout', fontsize:'Font size', font_size_pt:'Font size (pt)', palette:'Palette', alpha:'Opacity (0–1)', linestyle:'Line style', legend_position:'Legend position' };
const reviewPanels = ['edit', 'requests', 'history'];
function showPanel(name, focus = false) {
  for (const entry of dropdowns.values()) closeDropdown(entry);
  for (const panel of reviewPanels) {
    const active = panel === name;
    $(panel+'-panel').hidden = !active;
    $(panel+'-tab').setAttribute('aria-selected', String(active));
    $(panel+'-tab').setAttribute('tabindex', active ? '0' : '-1');
  }
  $('edit-footer').hidden = name !== 'edit';
  if (focus) $(name+'-tab').focus();
}
for (const [index, name] of reviewPanels.entries()) {
  $(name+'-tab').addEventListener('click', () => showPanel(name));
  $(name+'-tab').addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index+1) % reviewPanels.length;
    if (event.key === 'ArrowLeft') next = (index+reviewPanels.length-1) % reviewPanels.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = reviewPanels.length-1;
    if (next !== undefined) { event.preventDefault(); showPanel(reviewPanels[next], true); }
  });
}
function message(text, error = false) { $('message').textContent = text; $('message').classList.toggle('error', error); }
async function api(path, payload) {
  const options = payload !== undefined ? {method:'POST', headers:{'Content-Type':'application/json','X-EasyViz-Token':state.token}, body:JSON.stringify(payload)} : {};
  const response = await fetch(path, options);
  let body;
  try { body = await response.json(); } catch (_) { throw new Error('The local service returned an unreadable response. Reload the figure and try again.'); }
  if (!response.ok) throw new Error(body.error || 'Unable to read this figure.');
  return body;
}
function setMode(next) {
  mode = next; drag = null;
  for (const item of ['element','region']) { $(item+'-mode').classList.toggle('active', item===mode); $(item+'-mode').setAttribute('aria-pressed', String(item===mode)); }
  $('figure-host').classList.toggle('region-mode', mode==='region');
  selectionHint();
}
function selectionHint(element=null) {
  const hint=mode==='region'?'Drag to add a numbered region':element?element.label+' · '+element.role.replaceAll('-',' '):'Click to add an annotation';
  $('preview-size').textContent=hint;
  $('preview-size').title=hint;
  $('figure-host').classList.toggle('element-hit',!!element&&mode==='element');
}
function mappedElement(node) {
  if(!svg||!node||!svg.contains(node)) return null;
  while(node&&node!==svg) {
    const element=state.elements.find(element=>element.id===node.id);
    if(element) return element;
    node=node.parentNode;
  }
  return null;
}
function pickElement(event) {
  if(!state?.manifest_valid||!svg) return null;
  const direct=mappedElement(event.target);
  if(direct&&direct.role!=='axes') return direct;
  // Probe actual painted SVG content nearby, never a collection's bounding box.
  // Screen-pixel tolerance stays constant when the figure is scaled or zoomed.
  if(typeof document.elementFromPoint==='function') {
    for(let radius=1;radius<=6;radius++) {
      for(let step=0;step<16;step++) {
        const angle=step*Math.PI/8;
        const candidate=mappedElement(document.elementFromPoint(event.clientX+radius*Math.cos(angle),event.clientY+radius*Math.sin(angle)));
        if(candidate&&candidate.role!=='axes') return candidate;
      }
    }
  }
  return direct;
}
function svgPoint(event) {
  const point = svg.createSVGPoint(); point.x = event.clientX; point.y = event.clientY;
  const transformed = point.matrixTransform(svg.getScreenCTM().inverse());
  const [x,y,width,height] = state.view_box;
  return {x:Math.max(x,Math.min(x+width,transformed.x)),y:Math.max(y,Math.min(y+height,transformed.y))};
}
function toMm(rect) {
  const [x,y,width,height] = state.view_box;
  return {x:(rect.x-x)/width*state.panel.width_mm,y:(rect.y-y)/height*state.panel.height_mm,width:rect.width/width*state.panel.width_mm,height:rect.height/height*state.panel.height_mm};
}
function fromMm(rect) {
  const [x,y,width,height] = state.view_box;
  return {x:x+rect.x/state.panel.width_mm*width,y:y+rect.y/state.panel.height_mm*height,width:rect.width/state.panel.width_mm*width,height:rect.height/state.panel.height_mm*height};
}
function elementBox(element) {
  const box = element.getBBox(), transform = svg.getScreenCTM().inverse().multiply(element.getScreenCTM());
  const points = [[box.x,box.y],[box.x+box.width,box.y],[box.x,box.y+box.height],[box.x+box.width,box.y+box.height]].map(([x,y])=>{const p=svg.createSVGPoint();p.x=x;p.y=y;return p.matrixTransform(transform);});
  const xs=points.map(p=>p.x),ys=points.map(p=>p.y);
  return {x:Math.min(...xs),y:Math.min(...ys),width:Math.max(...xs)-Math.min(...xs),height:Math.max(...ys)-Math.min(...ys)};
}
function highlight(rect) {
  svg.querySelectorAll('[data-review-highlight]').forEach(node=>node.remove());
  if (!rect) return;
  const mark=document.createElementNS(NS,'rect');
  for(const key of ['x','y','width','height']) mark.setAttribute(key, String(rect[key]));
  mark.setAttribute('data-review-highlight','true');
  svg.append(mark);
}
function activeAnnotation() { return annotations.find(note=>note.number===activeNumber); }
function isGeneralNote(note) { return !(note.element_ids||[]).length&&!note.region_mm&&!note.selector; }
function resetNextNumber() {
  const reserved=(state?.requests||[]).filter(item=>item.current_version&&Number.isInteger(item.annotation_number)).map(item=>item.annotation_number);
  nextNumber=Math.max(1,...reserved.map(number=>number+1),...annotations.map(note=>note.number+1));
}
function annotationElements(note) { return (state?.elements||[]).filter(element=>(note?.element_ids||[]).includes(element.id)); }
function effectiveInstruction(note) {
  return note.instruction.trim();
}
function annotationLabel(note) {
  const elements=annotationElements(note);
  return elements.length===1?elements[0].label:elements.length?elements.length+' mapped elements':note.region_mm?'Selected region':'Whole figure';
}
function draftKey() { return 'easyviz-annotations:'+(state.project_id?state.project_id+':':'')+(state.attempt_id||state.figure_name)+':'+JSON.stringify(state.version); }
function legacyDraftKey() { return 'easyviz-annotations:'+state.figure_name+':'+JSON.stringify(state.version); }
function readStoredDrafts() {
  const oldAttemptKey='easyviz-annotations:'+(state.attempt_id||state.figure_name)+':'+JSON.stringify(state.version);
  for(const key of new Set([draftKey(),oldAttemptKey,legacyDraftKey()])) {
    const stored=JSON.parse(sessionStorage.getItem(key)||'null');
    if(stored&&(!stored.project_id||stored.project_id===state.project_id)&&(!stored.attempt_id||stored.attempt_id===state.attempt_id))return stored;
  }
  return null;
}
function annotationStatus() {
  const note=activeAnnotation();
  $('annotation-state').hidden=!note||(!note.saved&&!storageUnavailable);
  const request=note?.request_id?state.requests.find(item=>item.id===note.request_id):null;
  $('annotation-state').textContent=note?.saved?(request?.status==='applied'?'Applied · review the rendered attempt':request?.status==='pending'?'Saved · use Requests to undo this instruction':'Saved · '+(request?.status||'recorded')):storageUnavailable?'Draft · save before closing or refreshing this page':'Draft · this instruction has not been saved';
}
function persistDrafts() {
  if(!state) return;
  try { sessionStorage.setItem(draftKey(),JSON.stringify({project_id:state.project_id,attempt_id:state.attempt_id,nextNumber,activeNumber,notes:annotations.filter(note=>!note.saved)}));storageUnavailable=false; } catch (_) { storageUnavailable=true; }
  annotationStatus();
}
function captureAnnotation() {
  if(generalDraft) {generalDraft.instruction=$('instruction').value;return;}
  const note=activeAnnotation();
  if(!note||note.saved) return;
  note.instruction=$('instruction').value;
}
function annotationBox(note) {
  if(note.region_mm) return fromMm(note.region_mm);
  const boxes=[];
  for(const element of annotationElements(note)) {
    const node=svg.getElementById(element.id);
    if(node) try { boxes.push(elementBox(node)); } catch (_) { /* IDs remain editable when geometry is unavailable. */ }
  }
  if(!boxes.length) return null;
  const x=Math.min(...boxes.map(box=>box.x)),y=Math.min(...boxes.map(box=>box.y));
  return {x,y,width:Math.max(...boxes.map(box=>box.x+box.width))-x,height:Math.max(...boxes.map(box=>box.y+box.height))-y};
}
function annotationAnchor(note) {
  if(note.anchor_mm) return note.anchor_mm;
  const box=annotationBox(note),[x,y,width,height]=state.view_box;
  return {x:Math.max(0,Math.min(state.panel.width_mm,box?(box.x+box.width-x)/width*state.panel.width_mm:state.panel.width_mm)),y:Math.max(0,Math.min(state.panel.height_mm,box?(box.y-y)/height*state.panel.height_mm:0))};
}
function placeAnnotationBadge(anchor,mark,width,height,gutter,canvas,placed) {
  const clamp=box=>({...box,x:Math.max(canvas.x,Math.min(canvas.x+canvas.width-width,box.x)),y:Math.max(canvas.y,Math.min(canvas.y+canvas.height-height,box.y))});
  const overlap=(a,b)=>{
    const width=Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x),height=Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y);
    return width>1e-7&&height>1e-7?width*height:0;
  };
  const left=mark?.x??anchor.x,right=mark?mark.x+mark.width:anchor.x;
  const top=mark?.y??anchor.y,bottom=mark?mark.y+mark.height:anchor.y;
  const candidates=[
    {x:right+gutter.x,y:top-height-gutter.y},
    {x:left-width-gutter.x,y:top-height-gutter.y},
    {x:right+gutter.x,y:bottom+gutter.y},
    {x:left-width-gutter.x,y:bottom+gutter.y}
  ];
  const protectedMark=mark?{x:mark.x-gutter.x,y:mark.y-gutter.y,width:mark.width+2*gutter.x,height:mark.height+2*gutter.y}:null;
  for(const position of candidates) {
    const box={...position,width,height};
    if(box.x>=canvas.x&&box.y>=canvas.y&&box.x+width<=canvas.x+canvas.width&&box.y+height<=canvas.y+canvas.height&&(!protectedMark||!overlap(box,protectedMark))&&!placed.some(other=>overlap(box,other)>0))return box;
  }
  // Prefer a nearby outside corner; the grid provides distinct, bounded
  // positions when several comments share a target or its edge is crowded.
  for(let y=canvas.y;y+height<=canvas.y+canvas.height;y+=height+gutter.y) {
    for(let x=canvas.x+canvas.width-width;x>=canvas.x;x-=width+gutter.x)candidates.push({x,y});
  }
  let best=null,score=null;
  for(const position of candidates) {
    const box=clamp({...position,width,height});
    const next=[placed.reduce((count,other)=>count+(overlap(box,other)>0?1:0),0),protectedMark?overlap(box,protectedMark):0,Math.hypot(box.x+width/2-anchor.x,box.y+height/2-anchor.y)];
    if(!score||next[0]<score[0]||next[0]===score[0]&&(next[1]<score[1]||next[1]===score[1]&&next[2]<score[2])) {best=box;score=next;}
  }
  return best;
}
function drawAnnotations() {
  if(!svg||typeof svg.getScreenCTM!=='function') return;
  svg.querySelectorAll('[data-review-annotation]').forEach(node=>node.remove());
  const matrix=svg.getScreenCTM();if(!matrix) return;
  const scaleX=Math.hypot(matrix.a,matrix.b),scaleY=Math.hypot(matrix.c,matrix.d);
  if(!scaleX||!scaleY) return;
  const [vx,vy,vw,vh]=state.view_box,placed=[];
  const layer=document.createElementNS(NS,'g');layer.setAttribute('data-review-annotation','true');
  for(const note of annotations) {
    const rect=annotationBox(note),active=note.number===activeNumber;
    if(rect) {
      const frame=document.createElementNS(NS,'rect');
      for(const [key,value] of Object.entries(rect)) frame.setAttribute(key,String(value));
      frame.setAttribute('class','annotation-frame'+(active?' active':''));layer.append(frame);
    }
    const anchor=annotationAnchor(note),badgeWidth=Math.max(22,12+String(note.number).length*7)/scaleX,badgeHeight=22/scaleY;
    const position=placeAnnotationBadge({x:vx+anchor.x/state.panel.width_mm*vw,y:vy+anchor.y/state.panel.height_mm*vh},rect,badgeWidth,badgeHeight,{x:4/scaleX,y:4/scaleY},{x:vx,y:vy,width:vw,height:vh},placed);
    const bx=position.x,by=position.y;
    placed.push(position);
    const badge=document.createElementNS(NS,'g');badge.setAttribute('class','annotation-badge'+(active?' active':''));
    badge.setAttribute('role','button');badge.setAttribute('tabindex','0');badge.setAttribute('aria-label',`Annotation ${note.number}: ${annotationLabel(note)}`);badge.setAttribute('aria-pressed',String(active));
    badge.setAttribute('data-annotation-number',String(note.number));
    const tile=document.createElementNS(NS,'rect');
    for(const [key,value] of Object.entries({x:bx,y:by,width:badgeWidth,height:badgeHeight,rx:6/scaleX,ry:6/scaleY})) tile.setAttribute(key,String(value));
    const label=document.createElementNS(NS,'text');label.setAttribute('x',String(bx+badgeWidth/2));label.setAttribute('y',String(by+badgeHeight/2));label.setAttribute('font-size',String(11/scaleY));label.textContent=String(note.number);
    badge.append(tile,label);
    badge.addEventListener('click',event=>{event.stopPropagation();if(!loading&&!saving&&!operating) focusAnnotation(note.number);});
    badge.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();event.stopPropagation();if(!loading&&!saving&&!operating)focusAnnotation(note.number);}});
    layer.append(badge);
  }
  svg.append(layer);
}
function annotationChips() {
  const list=$('annotation-list');list.replaceChildren();
  if(!annotations.length) {const empty=document.createElement('p');empty.className='empty';empty.textContent='Click elements or draw regions to add numbered annotations.';list.append(empty);}
  for(const note of pageItems(annotations,'annotations')) {
    const chip=document.createElement('button');chip.type='button';chip.className='annotation-chip'+(note.saved?' saved':effectiveInstruction(note)?' complete':'');chip.textContent=String(note.number);
    chip.setAttribute('aria-label',`Annotation ${note.number}: ${annotationLabel(note)}, ${note.saved?'saved':effectiveInstruction(note)?'ready to save':'draft'}`);
    chip.setAttribute('aria-pressed',String(note.number===activeNumber));chip.disabled=loading||saving||operating;
    chip.addEventListener('click',()=>focusAnnotation(note.number));list.append(chip);
  }
}
function focusAnnotation(number) {
  if(loading||saving||operating) return;
  captureAnnotation();generalDraft=null;activeNumber=number;
  pages.annotations.page=Math.floor(Math.max(0,annotations.findIndex(note=>note.number===number))/pages.annotations.size);
  showPanel('edit');selectionChanged();persistDrafts();
}
function beginGeneralNote(forceNew=false) {
  if(loading||saving||operating||!state||!svg) return;
  captureAnnotation();
  const existing=!forceNew&&(annotations.find(note=>!note.saved&&isGeneralNote(note))||annotations.find(isGeneralNote));
  if(existing) {focusAnnotation(existing.number);return;}
  if(annotations.filter(note=>!note.saved).length>=100) {message('Save or remove some drafts before adding more annotations.',true);return;}
  if(nextNumber>1000000) {message('The annotation number limit has been reached for this figure version.',true);return;}
  generalDraft=generalDraft||{instruction:''};activeNumber=null;
  showPanel('edit');selectionChanged();persistDrafts();$('instruction').focus();
}
function addAnnotation(target,forceNew=false) {
  if(loading||saving||operating||!state||!svg) return;
  captureAnnotation();
  const signature=note=>JSON.stringify({ids:[...(note.element_ids||[])].sort(),region:note.region_mm||null,selector:note.selector||null});
  const existing=!forceNew&&(annotations.find(note=>!note.saved&&signature(note)===signature(target))||annotations.find(note=>signature(note)===signature(target)));
  if(existing) {focusAnnotation(existing.number);return existing;}
  if(annotations.filter(note=>!note.saved).length>=100) {message('Save or remove some drafts before adding more annotations.',true);return;}
  if(nextNumber>1000000) {message('The annotation number limit has been reached for this figure version.',true);return;}
  const note={...target,element_ids:target.element_ids||[],number:nextNumber++,instruction:'',saved:false};
  generalDraft=null;note.anchor_mm=annotationAnchor(note);annotations.push(note);activeNumber=note.number;
  pages.annotations.page=Math.floor((annotations.length-1)/pages.annotations.size);
  showPanel('edit');selectionChanged();persistDrafts();message(`Annotation ${note.number} added. Select another location or write its instruction.`);
  return note;
}
function selectElements(ids,selector=null) {
  addAnnotation({element_ids:[...new Set(ids)].filter(id=>state.elements.some(element=>element.id===id)),...(selector?{selector}:{})});
}
function selectionChanged() {
  const note=activeAnnotation(),elements=annotationElements(note),region=note?.region_mm;
  $('active-annotation').hidden=!note&&!generalDraft;annotationStatus();
  $('annotation-title').textContent=note?`Annotation ${note.number}`:generalDraft?'General note':'';
  $('remove-annotation').hidden=!generalDraft&&(!note||note.saved);
  $('new-instruction').hidden=!note||!note.saved;
  $('remove-annotation').setAttribute('aria-label',note?`Remove annotation ${note.number}`:generalDraft?'Cancel general note':'Remove annotation');
  if(elements.length) {
    $('selection-details').textContent=elements.length===1?elements[0].label:`${elements.length} selected elements`;
  } else if(region) {
    $('selection-details').textContent='Selected region';
  } else { $('selection-details').textContent=note||generalDraft?'Whole figure / general note':'Select a location or add a general note.'; }
  $('selection-details').hidden=!note&&!generalDraft;
  $('instruction').value=note?.instruction??generalDraft?.instruction??'';
  annotationChips();highlight(null);drawAnnotations();controls();
}
function runningJob() { return activeJob&&['queued','running'].includes(activeJob.status); }
function currentPending() { return (state?.requests||[]).filter(item=>item.status==='pending'&&item.current_version); }
function reviewingPartialSource() {
  return activeJob?.status==='succeeded'&&activeJob.target_attempt_id&&activeJob.source_attempt_id===state?.attempt_id&&(activeJob.agent_request_ids||[]).length>0;
}
function showLibrary(visible) {
  libraryVisible=visible||!state?.version;
  $('figure-library').hidden=!libraryVisible;
  $('open-library').setAttribute('aria-expanded',String(libraryVisible));
}
function renderLibrary() {
  const list=$('library-list');list.replaceChildren();
  const available=attempts.filter(item=>!item.unavailable);
  $('library-empty').hidden=!!available.length;
  for(const attempt of available) {
    const card=document.createElement('button');card.type='button';card.className='library-card';
    card.setAttribute('aria-current',String(attempt.id===state?.attempt_id));
    card.disabled=loading||saving||operating||!!runningJob();
    const image=document.createElement('img');image.src=attempt.preview_url;image.alt='';image.loading='lazy';
    const title=document.createElement('strong');title.textContent=attempt.name||attempt.id;
    const detail=document.createElement('span');detail.textContent=(attempt.track?attempt.track+' · ':'')+(attempt.accepted?'Accepted · ':'')+(attempt.panel?`${Number(attempt.panel.width_mm).toFixed(0)} × ${Number(attempt.panel.height_mm).toFixed(0)} mm`:'SVG figure');
    card.append(image,title,detail);card.addEventListener('click',async()=>{
      if(attempt.id===state?.attempt_id) {showLibrary(false);return;}
      await switchAttempt(attempt.id);
    });list.append(card);
  }
}
async function refreshLibrary() {
  if(loading||saving||operating||runningJob()) return;
  operating=true;controls();
  try {
    const result=await api('/api/library/refresh',{});attempts=result.attempts||[];
    $('library-project').textContent=result.project_name||'';renderLibrary();
    if(!state?.version&&attempts.some(item=>!item.unavailable)) {
      const first=attempts.find(item=>!item.unavailable);operating=false;await switchAttempt(first.id);
    } else message('The figure library is up to date.');
  } catch(error) {message(error.message,true);} finally {operating=false;controls();}
}
function closeNameEditor(focus=false) {
  $('figure-name-form').hidden=true;$('figure-name-display').hidden=false;
  if(focus)$('rename-figure').focus();
}
function editFigureName() {
  if(loading||saving||operating||runningJob()||!state?.attempt_id)return;
  $('figure-name-input').value=state.figure_name;
  $('figure-name-display').hidden=true;$('figure-name-form').hidden=false;
  controls();$('figure-name-input').focus();$('figure-name-input').select?.();
}
async function saveFigureName(event) {
  event.preventDefault();
  if(loading||saving||operating||runningJob()||!state?.attempt_id)return;
  const name=$('figure-name-input').value.trim();
  if(!name||Array.from(name).length>120||/[\u0000-\u001f\u007f-\u009f]/.test(name)) {
    message('Enter a figure name of 1–120 characters without control characters.',true);return;
  }
  if(name===state.figure_name){closeNameEditor(true);return;}
  captureAnnotation();persistDrafts();
  const identity=state.attempt_id;operating=true;controls();
  try {
    const result=await api('/api/attempts/rename',{attempt_id:identity,name});
    if(result.attempt?.id!==identity||typeof result.attempt.name!=='string')throw new Error('The local service did not confirm the figure name. Reload to check it.');
    state.figure_name=result.attempt.name;
    $('figure-name').textContent=state.figure_name;$('current-label').textContent='Current · '+state.figure_name;
    attempts=attempts.map(item=>item.id===identity?{...item,name:state.figure_name}:item);
    persistDrafts();closeNameEditor();renderAttempts();
    await refreshService();
    message('Figure name saved. Connected Agents can read it with the project.');
  } catch(error) {message(error.message,true);}
  finally {operating=false;controls();if($('figure-name-form').hidden)$('rename-figure').focus();}
}
async function openDocument(file) {
  if(!file||loading||saving||operating||runningJob()) return;
  if(!file.name.toLowerCase().endsWith('.ev')) {message('Choose an EasyViz .ev project file. SVG, PDF and PNG exports cannot provide the editable source bundle.',true);return;}
  if(file.size>64*1024*1024) {message('The .ev file exceeds the 64 MiB limit.',true);return;}
  captureAnnotation();persistDrafts();operating=true;controls();
  try {
    const response=await fetch('/api/documents/import?name='+encodeURIComponent(file.name),{
      method:'POST',headers:{'Content-Type':'application/octet-stream','X-EasyViz-Token':state.token},body:file});
    const result=await response.json();if(!response.ok)throw new Error(result.error||'The .ev project could not be opened.');
    operating=false;
    if(await load(result.state)) {showLibrary(false);message('Opened a new copy of the EasyViz project. The imported file is unchanged.');}
  } catch(error) {message(error.message,true);} finally {operating=false;$('document-file').value='';controls();}
}
function originalSessionConnection() {
  return agentConnection?.backend==='session';
}
function scheduledOriginalConnection() {
  const trigger=agentConnection?.host_trigger;
  if(!originalSessionConnection()||!agentConnection.enabled||!agentConnection.available||agentConnection.same_session!==true||agentConnection.scheduled_dispatch!==true||agentConnection.dispatch_mode!=='host_heartbeat')return false;
  const owner=agentConnection.owner_session_id,expiry=trigger?.expires_at,interval=trigger?.interval_seconds;
  return typeof owner==='string'&&!!owner&&trigger?.kind==='heartbeat'&&trigger.host==='codex_desktop'&&trigger.registered===true&&trigger.active===true&&trigger.enabled===true&&trigger.verification==='owner_registered'&&trigger.owner_session_id===owner&&typeof trigger.automation_id==='string'&&!!trigger.automation_id&&typeof expiry==='number'&&Number.isFinite(expiry)&&expiry>Date.now()/1000&&Number.isInteger(interval)&&interval>=60&&interval<=3600;
}
function checkIntervalHint() {
  const seconds=Number(agentConnection?.host_trigger?.interval_seconds);
  const value=seconds<60?seconds:Number((seconds/60).toFixed(2));
  const unit=seconds<60?'second':'minute';
  return `About every ${value} ${unit}${value===1?'':'s'}.`;
}
function liveOriginalConnection() {
  if(!originalSessionConnection()||!agentConnection.enabled||!agentConnection.available||agentConnection.live_listener===false)return false;
  const expiry=Number(agentConnection.lease_expires_at);
  return agentConnection.same_session===true&&typeof agentConnection.owner_session_id==='string'&&!!agentConnection.owner_session_id&&agentConnection.lease_expires_at!=null&&Number.isFinite(expiry)&&expiry>Date.now()/1000;
}
function agentConnected() {
  if(!agentConnection?.enabled||!agentConnection?.available)return false;
  if(!originalSessionConnection())return true;
  return liveOriginalConnection()||scheduledOriginalConnection();
}
function serviceControls() {
  const busy=loading||saving||operating,rendering=runningJob();
  // Job actions share the same transient operation state as all other controls.
  // Acceptance/restore can refresh a job while operating is true; the final
  // controls() call must restore these buttons without another job response.
  $('cancel-job').disabled=busy;
  $('open-job-result').disabled=busy||!!rendering;
  $('review-remaining-requests').disabled=busy||!!rendering;
  $('attempt-toolbar').hidden=!attempts.length;
  $('attempt-list').disabled=busy||!!rendering;
  const current=attempts.find(item=>item.id===state?.attempt_id);
  $('accept-attempt').disabled=busy||!!rendering||!current||current.unavailable||current.accepted||state?.source_current===false;
  $('accept-attempt').textContent=current?.accepted?'Accepted':'Accept';
  $('restore-attempt').hidden=!attempts.some(item=>item.accepted);
  $('restore-attempt').disabled=busy||!!rendering;
  $('compare-toggle').hidden=!state?.comparison;
  $('compare-toggle').disabled=busy;
  $('compare-toggle').textContent=comparisonVisible?'Hide comparison':'Show comparison';
  $('compare-toggle').setAttribute('aria-pressed',String(comparisonVisible));
  const connected=agentConnected(),original=originalSessionConnection(),scheduled=scheduledOriginalConnection();
  const drafts=annotations.filter(note=>!note.saved&&effectiveInstruction(note)).length;
  $('submit-edits').disabled=busy||!!rendering||!connected||!state?.version||state.source_current===false||(!drafts&&!currentPending().length);
  $('submit-edits').textContent=rendering?'Working…':reviewingPartialSource()?'Submit from original':'Submit edits';
  $('connect-agent').disabled=busy||!!rendering;
  $('connect-agent').textContent=agentConnection?.enabled?'Disconnect':'Connect original Agent';
  const expired=original&&(agentConnection.runtime_state==='expired'||agentConnection.enabled&&agentConnection.lease_expires_at!=null&&Number.isFinite(Number(agentConnection.lease_expires_at))&&Number(agentConnection.lease_expires_at)<=Date.now()/1000);
  $('agent-label').textContent=connected?(scheduled?'Automatic check enabled':original?'Original Agent connected':agentConnection.runtime_state==='startup_failed'?'Separate worker needs attention':'Separate Codex worker enabled'):!agentConnection?'Connection status unavailable':expired?'Original Agent connection expired':agentConnection.enabled?'Agent unavailable':'Agent disconnected';
  $('agent-label').title=original&&connected?`${agentConnection.host||'Agent'} · original conversation ${agentConnection.owner_session_id}. ${agentConnection.message||''}`:String(agentConnection?.message||agentConnection?.reason||'Ask the Agent in your original conversation to connect this workbench.');
  $('agent-check-hint').hidden=!scheduled;
  $('agent-check-hint').textContent=scheduled?checkIntervalHint():'';
  $('import-document').disabled=busy||!!rendering;
  $('refresh-library').disabled=busy||!!rendering;
  $('rename-figure').hidden=!state?.attempt_id;
  $('rename-figure').disabled=busy||!!rendering||!state?.attempt_id;
  $('figure-name-input').disabled=busy;
  $('save-figure-name').disabled=busy||!!rendering||!$('figure-name-input').value.trim();
  $('cancel-figure-name').disabled=busy;
  for(const card of $('library-list').children) card.disabled=busy||!!rendering;
  $('handoff-hint').hidden=!reviewingPartialSource();
  $('handoff-hint').textContent=reviewingPartialSource()?'Remaining comments belong to the original. Submit here for a separate branch, or annotate the new version to continue.':'';
  syncDropdown('attempt-list');
}
function renderAttempts() {
  const list=$('attempt-list');list.replaceChildren();
  for(const attempt of attempts) if(!attempt.unavailable) list.add(new Option(attempt.name+(attempt.accepted?' · accepted':''),attempt.id));
  list.value=state?.attempt_id||'';syncDropdown('attempt-list');
  renderHistory();renderLibrary();renderJob();serviceControls();
}
function renderHistory() {
  const history=$('history-list');history.replaceChildren();
  const entries=[...attempts.map(item=>({attempt:item})),...(state?.history||[]).map(item=>({event:item}))];
  $('history-section').hidden=!entries.length;$('history-empty').hidden=!!entries.length;
  for(const entry of pageItems(entries,'history')) {
    if(entry.event) {
      const item=entry.event,row=document.createElement('div');row.className='attempt-row';
      const title=document.createElement('p');title.className='attempt-title';
      const target=item.target_attempt?.split('/').pop()||(item.version?.figure_sha256?'version '+item.version.figure_sha256.slice(0,8):'version');
      title.textContent=`${item.action} · ${target}`;row.append(title);
      if(item.validation) {
        const text=document.createElement('p');text.className='note-preview';text.textContent=item.validation;
        row.append(text,readButton('Read details',title.textContent,item.validation));
      }
      history.append(row);continue;
    }
    const attempt=entry.attempt;
    const row=document.createElement('div');row.className='attempt-row';
    const title=document.createElement('p');title.className='attempt-title';title.textContent=(attempt.name||attempt.id)+(attempt.unavailable?' · unavailable':'')+(attempt.id===state?.attempt_id?' · current':'')+(attempt.accepted?' · accepted':'');
    const meta=document.createElement('p');meta.className='attempt-meta';
    meta.textContent=attempt.unavailable?attempt.error||'This attempt is unavailable.':attempt.panel?`${Number(attempt.panel.width_mm).toFixed(1)} × ${Number(attempt.panel.height_mm).toFixed(1)} mm`:'';
    const links=document.createElement('div');links.className='attempt-links';
    const open=document.createElement('button');open.type='button';open.className='text-button';open.textContent='View attempt';open.disabled=attempt.unavailable||attempt.id===state?.attempt_id||!!runningJob();open.addEventListener('click',()=>switchAttempt(attempt.id));links.append(open);
    for(const [extension,url] of Object.entries(attempt.files||{})) {
      if(!['svg','pdf','png'].includes(extension)||typeof url!=='string'||!url.startsWith('/')) continue;
      const link=document.createElement('a');link.href=url;link.download='panel.'+extension;link.textContent=extension.toUpperCase();links.append(link);
    }
    row.append(title,meta,links);history.append(row);
  }
}
async function refreshService() {
  if(!state) return;
  const revision=++serviceRevision,connectionRevision=++agentRevision,identity=state.attempt_id||JSON.stringify(state.version);
  const results=await Promise.allSettled([api('/api/library'),api('/api/jobs'),api('/api/agent')]);
  if(revision!==serviceRevision||identity!==(state?.attempt_id||JSON.stringify(state?.version))) return;
  attempts=results[0].status==='fulfilled'&&Array.isArray(results[0].value.attempts)?results[0].value.attempts:[];
  if(connectionRevision===agentRevision)agentConnection=results[2].status==='fulfilled'?results[2].value:null;
  if(results[0].status==='fulfilled') $('library-project').textContent=results[0].value.project_name||state.project_name||'This project';
  if(results[1].status==='fulfilled'&&Array.isArray(results[1].value.jobs)) {
    jobStatusError=null;
    const jobs=results[1].value.jobs;
    const currentJob=activeJob?jobs.find(item=>item.id===activeJob.id&&(['queued','running'].includes(item.status)||item.source_attempt_id===state?.attempt_id||item.target_attempt_id===state?.attempt_id)):null;
    const relevant=currentJob||[...jobs].reverse().find(item=>['queued','running'].includes(item.status))||[...jobs].reverse().find(item=>item.source_attempt_id===state?.attempt_id||item.target_attempt_id===state?.attempt_id);
    activeJob=relevant||null;renderJob();scheduleJobPoll();
  } else if(activeJob) jobStatusError='Task status could not be refreshed. Reload the figure to reconnect.';
  renderAttempts();serviceControls();
}
function scheduleAgentPoll() {
  if(agentTimer!==null&&typeof clearTimeout==='function')clearTimeout(agentTimer);
  agentTimer=null;
  if(typeof setTimeout==='function')agentTimer=setTimeout(pollAgent,3000);
}
async function pollAgent() {
  agentTimer=null;
  try {
    if(state&&!loading&&!operating) {
      const revision=++agentRevision;
      try {
        const result=await api('/api/agent');
        if(revision===agentRevision){agentConnection=result;renderJob();serviceControls();}
      } catch(error) {
        if(revision===agentRevision){agentConnection=null;serviceControls();$('agent-label').title='Connection status unavailable. '+error.message;}
      }
    }
  } finally {scheduleAgentPoll();}
}
function jobPresentation(job) {
  const original=job.backend==='session',agent=job.kind==='agent';
  const pending=(job.agent_request_ids||[]).length;
  const accepted=job.target_attempt_id&&attempts.some(attempt=>attempt.id===job.target_attempt_id&&attempt.accepted);
  const timestamp=value=>(typeof value==='string'&&Number.isFinite(Date.parse(value)))||(typeof value==='number'&&Number.isFinite(value)&&value>0);
  if(job.status==='queued') {
    const scheduled=original&&scheduledOriginalConnection()&&job.owner_session_id===agentConnection.owner_session_id&&job.host_trigger_id===agentConnection.host_trigger.automation_id;
    return {state:'waiting',title:scheduled?'Waiting for automatic check':agent?'Submitted · waiting for Agent':'Preview queued',detail:scheduled?checkIntervalHint()+' Your original conversation will check for submitted edits.':original?'Your edits are saved and waiting for your original Agent.':agent?'Your edits are saved and waiting for the separate worker.':'Waiting to render the saved edits.'};
  }
  if(job.status==='running') {
    if(original) {
      const steps={session_editing:'Your original Agent is updating the figure.',session_rendering:'Your original Agent is rendering fresh exports.',session_reviewing:'Your original Agent is checking the rendered figure.'};
      if(steps[job.phase]&&timestamp(job.editing_started_at)) return {state:'editing',title:'Editing',detail:steps[job.phase]};
      if(timestamp(job.received_at)||timestamp(job.claimed_at)) return {state:'received',title:'Agent received',detail:'Your original conversation has received the submission.'};
      return {state:'processing',title:'Processing',detail:'Waiting for confirmed progress from your original Agent.'};
    }
    return {state:'editing',title:job.phase==='validating'?'Checking exports':agent?'Editing':'Rendering preview',detail:agent?'The separate worker is updating the figure.':'A fresh attempt is being rendered from the saved edits.'};
  }
  if(job.status==='succeeded') {
    if(!job.target_attempt_id) return {state:'attention',title:'No new figure',detail:'The task ended without a new rendered attempt.'};
    if(accepted&&!pending) return {state:'completed',title:'Completed',detail:'The new figure has been accepted.'};
    return {state:'review',title:'Ready to review',detail:'A new attempt is ready. Review the figure before accepting it.'};
  }
  if(job.status==='failed') return {state:'failed',title:'Failed',detail:'The task failed. Your submitted comments remain saved.'};
  if(job.status==='cancelled') return {state:'cancelled',title:'Cancelled',detail:'The task was cancelled. Your submitted comments remain saved.'};
  return {state:'unknown',title:'Status unavailable',detail:'Waiting for a verified task status.'};
}
function renderJob() {
  $('job-status').hidden=!activeJob;
  if(!activeJob) return;
  const presentation=jobStatusError?{state:'unknown',title:'Status unavailable',detail:jobStatusError}:jobPresentation(activeJob);
  $('job-title').textContent=presentation.title;
  $('job-status').setAttribute('data-state',presentation.state);
  $('job-status').classList.toggle('failed',activeJob.status==='failed');
  // Keep protocol phases and long worker diagnostics out of the compact inspector.
  const error=!jobStatusError&&typeof activeJob.error==='string'?activeJob.error.trim():'';
  const detail=error?error.length>240?error.slice(0,237)+'…':error:presentation.detail;
  const agentCount=(activeJob.agent_request_ids||[]).length;
  const remaining=activeJob.status==='succeeded'&&agentCount?` ${agentCount} ${agentCount===1?'instruction remains':'instructions remain'} pending on the original figure.`:'';
  $('job-detail').textContent=detail+remaining;
  $('job-detail').title=(error||presentation.detail)+remaining;
  $('cancel-job').hidden=!!jobStatusError||!runningJob();
  $('open-job-result').hidden=!!jobStatusError||activeJob.status!=='succeeded'||!activeJob.target_attempt_id||activeJob.target_attempt_id===state?.attempt_id;
  $('review-remaining-requests').hidden=!!jobStatusError||activeJob.status!=='succeeded'||!agentCount||!activeJob.source_attempt_id;
  serviceControls();
}
function scheduleJobPoll() {
  if(jobTimer!==null&&typeof clearTimeout==='function') clearTimeout(jobTimer);
  jobTimer=null;
  if(runningJob()&&typeof setTimeout==='function') jobTimer=setTimeout(pollJob,1200);
}
async function pollJob() {
  jobTimer=null;
  if(!runningJob()) return;
  const id=activeJob.id;
  try {
    const result=await api('/api/jobs/'+encodeURIComponent(id));
    if(activeJob?.id!==id) return;
    activeJob=result.job;jobStatusError=null;renderJob();
    if(!runningJob()) {
      const nextState=await api('/api/state');
      if(nextState.attempt_id===state?.attempt_id||!nextState.attempt_id) updateQueue(nextState);
      await refreshService();
      if(activeJob.status==='succeeded'&&activeJob.source_attempt_id===state?.attempt_id&&activeJob.target_attempt_id&&!annotations.some(note=>!note.saved&&effectiveInstruction(note))) await switchAttempt(activeJob.target_attempt_id);
      else if(activeJob.status==='failed') message('Preview failed. The current attempt and saved instructions have been kept.',true);
    }
  } catch(error) {
    // A disconnected service has no reliable job state. Keep its identity and
    // stop claiming the render is active until a successful status refresh.
    jobStatusError=error.message+' Reload the figure to reconnect.';renderJob();
    message('Unable to read render status. Your saved instructions remain available.',true);
    return;
  }
  scheduleJobPoll();
}
async function switchAttempt(id) {
  if(loading||saving||operating||runningJob()||!state||!id) return;
  captureAnnotation();persistDrafts();operating=true;controls();
  try {
    const result=await api('/api/attempts/switch',{attempt_id:id,...(comparisonVisible&&state.attempt_id!==id?{compare_attempt_id:state.attempt_id}:{})});
    operating=false;
    if(!await load(result.state)) return false;
    showLibrary(false);
    message('Viewing '+state.figure_name+'. Each attempt retains its own exports and numbered requests.');
    return true;
  } catch(error) {message(error.message,true);return false;} finally {operating=false;controls();renderJob();}
}

function restoreAnnotations(memoryDrafts=null) {
  generalDraft=null;
  const numbered=state.requests.filter(item=>item.current_version&&Number.isInteger(item.annotation_number));
  nextNumber=Math.max(1,...numbered.map(item=>item.annotation_number+1));
  annotations=numbered.filter(item=>item.status==='pending').map(item=>({number:item.annotation_number,element_ids:item.element_ids||[],...(item.selector?{selector:item.selector}:{}),...(item.region_mm?{region_mm:item.region_mm}:{}),...(item.anchor_mm?{anchor_mm:item.anchor_mm}:{}),instruction:item.instruction,saved:true,request_id:item.id}));
  let stored=memoryDrafts;
  if(!stored) try {stored=readStoredDrafts();} catch (_) { storageUnavailable=true; }
  if(stored&&Array.isArray(stored.notes)) {
    for(const entry of stored.notes.slice(0,100)) {
      if(!Number.isInteger(entry.number)||entry.number<=0||entry.number>1000000||typeof entry.instruction!=='string'||!Array.isArray(entry.element_ids)||entry.element_ids.some(id=>!state.elements.some(element=>element.id===id))) continue;
      if(entry.region_mm) {
        const r=entry.region_mm;
        if(![r.x,r.y,r.width,r.height].every(Number.isFinite)||r.x<0||r.y<0||r.width<=0||r.height<=0||r.x+r.width>state.panel.width_mm||r.y+r.height>state.panel.height_mm) continue;
      }
      const committed=numbered.find(item=>item.annotation_number===entry.number);
      if(committed&&committed.instruction===entry.instruction.trim()&&JSON.stringify(committed.element_ids||[])===JSON.stringify(entry.element_ids)&&JSON.stringify(committed.region_mm||null)===JSON.stringify(entry.region_mm||null)&&(committed.property||'')===(entry.property||'')&&String(committed.value??'')===String(entry.value??'')) continue;
      const note={...entry,saved:false};
      // Older browser drafts used property controls. Keep their intended value
      // visible in the comment before retiring that hidden structured edit.
      if(note.property&&String(note.value??'').trim()) {
        const value=typeof note.value==='object'?JSON.stringify(note.value):String(note.value);
        const change=`Set ${propertyNames[note.property]||note.property} to ${value} for ${annotationLabel(note)}.`;
        note.instruction=note.instruction.trim()?note.instruction.trim()+'\n'+change:change;
      }
      delete note.property;delete note.value;
      // Older clients numbered general notes before any comment was written.
      // They have no target or instruction to restore and must not reserve IDs.
      if(isGeneralNote(note)&&!effectiveInstruction(note)) continue;
      if(committed||annotations.some(item=>item.number===note.number)) note.number=nextNumber++;
      nextNumber=Math.max(nextNumber,note.number+1);annotations.push(note);
    }
  }
  resetNextNumber();
  activeNumber=annotations.some(note=>note.number===stored?.activeNumber)?stored.activeNumber:annotations.find(note=>!note.saved)?.number??annotations[0]?.number??null;
  persistDrafts();
}
function queue() {
  const pending = state.requests.filter(item=>item.status==='pending'&&item.current_version).length;
  $('request-count').textContent = String(pending); $('request-count').hidden = !pending;
  const list=$('request-list');list.replaceChildren();
  if(!state.requests.length) { const p=document.createElement('p');p.className='empty';p.textContent='No changes requested yet.';list.append(p); }
  for(const item of pageItems(state.requests,'requests')) {
    const index=state.requests.indexOf(item);
    const row=document.createElement('div');row.className='request-item';
    row.classList.toggle('undone',['undone','superseded'].includes(item.status));row.classList.toggle('older',!item.current_version);
    const label=document.createElement('p');label.className='request-label';label.textContent=`${item.annotation_number?'#'+item.annotation_number:'Request '+(index+1)} · ${item.elements?.length>1?item.elements.length+' mapped elements':item.element?.label|| (item.region_mm?'Selected region':'Whole figure')}`;
    const instruction=document.createElement('p');instruction.className='note-preview';instruction.textContent=item.instruction;
    const status=document.createElement('p');status.className='request-status';status.textContent=`${item.status}${item.current_version?'':' · older figure version'}${item.result?.target_attempt?' · '+item.result.target_attempt.split('/').pop():''}`;
    row.append(label,instruction,status);
    const detail=item.result&&(item.result.message||item.result.note||item.result.reason||item.result.validation)||'';
    row.append(readButton('Read instruction',label.textContent,item.instruction+(detail?'\n\n'+detail:'')));
    list.append(row);
  }
  if(attempts.length) renderAttempts();else renderHistory();
  controls();
}
function controls() {
  const busy=loading||saving||operating;
  const note=activeAnnotation(),ready=annotations.filter(note=>!note.saved&&effectiveInstruction(note)).length;
  $('reload').disabled=busy;
  $('save').disabled=busy||!ready||!state||!svg||state.source_current===false;
  $('save').textContent=saving?'Saving…':ready?`Save drafts (${ready})`:'Save drafts';
  $('undo').disabled=busy||!state||!state.requests.some(item=>item.status==='pending'&&item.current_version);
  for(const id of ['region-mode','add-general']) $(id).disabled=busy||!svg;
  $('clear').disabled=busy||(!generalDraft&&!annotations.some(note=>!note.saved));
  $('remove-annotation').disabled=busy||(!generalDraft&&(!note||note.saved));
  $('new-instruction').disabled=busy||!note||!note.saved;
  $('instruction').disabled=busy||(!generalDraft&&(!note||note.saved));
  $('element-mode').disabled=busy||!state?.manifest_valid;
  for(const chip of $('annotation-list').children) if(chip.tagName==='BUTTON') chip.disabled=busy;
  for(const [name,page] of Object.entries(pages)) {
    $(name+'-previous').disabled=busy||page.page===0;
    $(name+'-next').disabled=busy||page.page>=(page.count||1)-1;
  }
  serviceControls();
}
function updateQueue(nextState) {
  // An HTTP response can observe a subsequent render. Queue updates never
  // replace the version or geometry of the SVG that the user is still viewing.
  const sameVersion=(left,right)=>JSON.stringify(left)===JSON.stringify(right);
  state={...state,history:nextState.history||state.history,requests:(nextState.requests||[]).map(item=>({...item,current_version:sameVersion(item.version,state.version)}))};
  queue();annotationStatus();
}
async function load(nextProvided = null) {
  if(loading||saving||operating) return;
  if(nextProvided && !nextProvided.version && !nextProvided.empty) nextProvided=null;
  captureAnnotation();persistDrafts();
  const previousIdentity=state?draftKey():null;
  const memoryDrafts={nextNumber,activeNumber,notes:annotations.filter(note=>!note.saved)};
  loading=true;drag=null;controls();
  let loaded=false;
  try {
    const nextState=nextProvided||await api('/api/state');
    if(nextState.empty) {
      closeNameEditor();
      state=nextState;svg=null;annotations=[];generalDraft=null;activeNumber=null;nextNumber=1;
      $('figure-host').replaceChildren();$('editor-layout').hidden=true;
      $('figure-name').textContent=state.project_name||'Your figure library';
      $('selection-message').textContent='Open an EasyViz .ev project to select elements and submit edits.';
      $('dimensions').textContent='';$('track').hidden=true;showLibrary(true);queue();
      loaded=true;return loaded;
    }
    const response=await fetch('/api/preview.svg?v='+encodeURIComponent(nextState.version.figure_sha256));
    if(!response.ok) { const error=await response.json();throw new Error(error.error||'Figure preview is unavailable.'); }
    const documentSvg=new DOMParser().parseFromString(await response.text(),'image/svg+xml');
    if(documentSvg.querySelector('parsererror')) throw new Error('The SVG preview could not be opened.');
    const nextSvg=document.importNode(documentSvg.documentElement,true);
    nextSvg.setAttribute('preserveAspectRatio','xMidYMid meet');nextSvg.setAttribute('role','group');nextSvg.setAttribute('aria-label','Interactive scientific figure');
    // Commit a figure and its version together only after both have loaded.
    let previousSvg=null;
    if(nextState.comparison) {
      const previous=await fetch('/api/compare.svg?v='+encodeURIComponent(nextState.comparison.version.figure_sha256));
      if(!previous.ok) { const error=await previous.json();throw new Error(error.error||'Previous attempt preview is unavailable.'); }
      const parsed=new DOMParser().parseFromString(await previous.text(),'image/svg+xml');
      if(parsed.querySelector('parsererror')) throw new Error('The previous SVG could not be opened.');
      previousSvg=document.importNode(parsed.documentElement,true);previousSvg.setAttribute('preserveAspectRatio','xMidYMid meet');previousSvg.setAttribute('role','img');previousSvg.setAttribute('aria-label','Previous attempt; read-only');
    }
    state=nextState;svg=nextSvg;closeNameEditor();
    for(const page of Object.values(pages)) page.page=0;
    for(const element of state.manifest_valid?state.elements:[]) {
      const target=svg.getElementById(element.id);if(!target)continue;
      target.setAttribute('tabindex','0');target.setAttribute('role','button');
      target.setAttribute('aria-label','Annotate '+element.label);
      // Hollow bars retain their real closed-path hit area. Later painted
      // observations still take precedence over this native SVG target.
      if(element.role==='summary-box')target.setAttribute('pointer-events','all');
      target.addEventListener('keydown',event=>{
        if(!['Enter',' '].includes(event.key)||loading||saving||operating||!state.manifest_valid)return;
        event.preventDefault();event.stopPropagation();selectElements([element.id]);
      });
    }
    $('editor-layout').hidden=false;
    $('figure-host').replaceChildren(svg);
    $('figure-name').textContent=state.figure_name;
    $('track').textContent=state.track;$('track').hidden=!state.track;
    $('dimensions').textContent=`${state.panel.width_mm.toFixed(1)} × ${state.panel.height_mm.toFixed(1)} mm`;
    $('selection-message').textContent='Click elements or draw regions to add numbered annotations, then write an instruction for each.';
    $('source-status').textContent=state.source_current===false?'Source files have changed. Render a fresh attempt before saving.':state.source_current===true?'Figure and source versions verified.':'Source verification unavailable. Your Agent must verify the source before applying requests.';
    $('source-status').classList.toggle('error',state.source_current===false);
    $('source-status').hidden=state.source_current===true;
    $('comparison').hidden=!previousSvg||!comparisonVisible;$('current-label').hidden=!previousSvg||!comparisonVisible;
    $('figure-host').parentNode?.classList.toggle('has-comparison',!!previousSvg&&comparisonVisible);
    $('comparison-host').replaceChildren(...(previousSvg?[previousSvg]:[]));
    $('comparison-label').textContent=state.comparison?'Previous · '+state.comparison.figure_name:'';
    $('current-label').textContent='Current · '+state.figure_name;
    restoreAnnotations(draftKey()===previousIdentity?memoryDrafts:null);
    pages.annotations.page=Math.floor(Math.max(0,annotations.findIndex(note=>note.number===activeNumber))/pages.annotations.size);
    $('downloads').replaceChildren();
    for(const extension of ['svg','pdf','png']) if(state.files.includes('panel.'+extension)) {const link=document.createElement('a');link.href='/files/panel.'+extension;link.download='panel.'+extension;link.textContent=extension.toUpperCase();$('downloads').append(link);}
    if(state.provenance_valid) {const project=document.createElement('a');project.href='/files/panel.ev';project.download='panel.ev';project.textContent='.ev project';$('downloads').append(project);}
    selectionChanged();queue();setMode(state.manifest_valid?'element':'region');
    message('');
    loaded=true;
  } catch(error) {message(error.message,true);} finally {loading=false;controls();refreshService();}
  return loaded;
}
$('element-mode').addEventListener('click',()=>setMode('element'));
$('region-mode').addEventListener('click',()=>setMode('region'));
$('rename-figure').addEventListener('click',editFigureName);
$('figure-name').addEventListener('click',editFigureName);
$('figure-name-form').addEventListener('submit',saveFigureName);
$('cancel-figure-name').addEventListener('click',()=>closeNameEditor(true));
$('figure-name-input').addEventListener('input',controls);
$('figure-name-input').addEventListener('keydown',event=>{if(event.key==='Escape'&&!operating){event.preventDefault();closeNameEditor(true);}});
$('clear').addEventListener('click',()=>{if(loading||saving||operating)return;generalDraft=null;annotations=annotations.filter(note=>note.saved);activeNumber=annotations[0]?.number??null;resetNextNumber();selectionChanged();persistDrafts();message('Unsaved annotations cleared. Numbering restarts after any saved requests.');});
$('remove-annotation').addEventListener('click',()=>{
  if(loading||saving||operating)return;
  if(generalDraft) {generalDraft=null;selectionChanged();persistDrafts();message('General note cancelled.');return;}
  const note=activeAnnotation();if(!note||note.saved)return;
  annotations=annotations.filter(item=>item!==note);activeNumber=annotations.find(item=>!item.saved)?.number??annotations[0]?.number??null;
  selectionChanged();persistDrafts();message(`Annotation ${note.number} removed. Other numbers stay unchanged.`);
});
$('add-general').addEventListener('click',()=>beginGeneralNote());
$('new-instruction').addEventListener('click',()=>{const note=activeAnnotation();if(!note||!note.saved)return;if(isGeneralNote(note)){beginGeneralNote(true);return;}addAnnotation({element_ids:note.element_ids,...(note.selector?{selector:note.selector}:{}),...(note.region_mm?{region_mm:note.region_mm}:{}),anchor_mm:note.anchor_mm},true);});
function draftChanged() {
  if(loading||saving||operating)return;
  const text=$('instruction').value;
  if(generalDraft) {
    generalDraft.instruction=text;
    if(text.trim()) {
      const draft=generalDraft;generalDraft=null;
      const note=addAnnotation({element_ids:[]},true);
      if(note) {note.instruction=text;$('instruction').value=text;}
      else {generalDraft=draft;selectionChanged();}
    }
  } else {
    captureAnnotation();
    const note=activeAnnotation();
    if(note&&!note.saved&&isGeneralNote(note)&&!text.trim()) {
      annotations=annotations.filter(item=>item!==note);activeNumber=null;generalDraft={instruction:text};
      resetNextNumber();selectionChanged();
    }
  }
  persistDrafts();annotationChips();controls();
}
$('instruction').addEventListener('input',draftChanged);
for(const name of Object.keys(pages)) {
  for(const [suffix,direction] of [['previous',-1],['next',1]]) {
    $(name+'-'+suffix).addEventListener('click',()=>{
      if(loading||saving||operating)return;
      const page=pages[name],next=page.page+direction;
      if(next<0||next>=(page.count||1))return;
      if(name==='annotations') {
        captureAnnotation();page.page=next;
        focusAnnotation(annotations[next*page.size].number);
      } else {page.page=next;name==='requests'?queue():renderHistory();controls();}
    });
  }
}
$('note-dialog-close').addEventListener('click',()=>$('note-dialog').close());
$('reload').addEventListener('click',load);
$('figure-host').addEventListener('click',event=>{
  if(loading||saving||operating||mode!=='element'||!svg) return;
  const element=pickElement(event);
  if(!element) {message('No mapped element here. Use Select region to mark this location.');return;}
  selectElements([element.id]);
});
$('figure-host').addEventListener('pointerdown',event=>{
  if(loading||saving||operating||mode!=='region'||!svg||!svg.contains(event.target)||event.target.closest?.('.annotation-badge')||event.button!==0) return;
  event.preventDefault();$('figure-host').setPointerCapture(event.pointerId);drag=svgPoint(event);
});
$('figure-host').addEventListener('pointermove',event=>{
  if(!drag) {if(!loading&&mode==='element') selectionHint(pickElement(event));return;}const point=svgPoint(event);highlight({x:Math.min(point.x,drag.x),y:Math.min(point.y,drag.y),width:Math.abs(point.x-drag.x),height:Math.abs(point.y-drag.y)});
});
$('figure-host').addEventListener('pointerleave',()=>selectionHint());
$('figure-host').addEventListener('pointerup',event=>{
  if(!drag) return;const point=svgPoint(event),rect={x:Math.min(point.x,drag.x),y:Math.min(point.y,drag.y),width:Math.abs(point.x-drag.x),height:Math.abs(point.y-drag.y)};
  drag=null;highlight(null);if(rect.width>0&&rect.height>0)addAnnotation({region_mm:toMm(rect)});
});
$('figure-host').addEventListener('pointercancel',()=>{drag=null;highlight(null);});
async function saveDrafts() {
  if(loading||saving||operating||!state||!svg||state.source_current===false) return false;
  captureAnnotation();persistDrafts();
  const ready=annotations.filter(note=>!note.saved&&effectiveInstruction(note));if(!ready.length)return true;
  saving=true;controls();
  try {
    const requests=ready.map(note=>{
      const item={version:state.version,instruction:effectiveInstruction(note),annotation_number:note.number,anchor_mm:note.anchor_mm};
      if(note.selector)item.selector=note.selector;
      else if(note.element_ids.length>1)item.element_ids=note.element_ids;
      else if(note.element_ids.length)item.element_id=note.element_ids[0];
      if(note.region_mm)item.region_mm=note.region_mm;
      return item;
    });
    const result=await api('/api/requests/batch',{version:state.version,requests});
    for(const item of result.requests) {const note=annotations.find(note=>note.number===item.annotation_number);if(note){note.saved=true;note.request_id=item.id;}}
    updateQueue(result.state);persistDrafts();
    message(`${result.requests.length} ${result.requests.length===1?'draft':'drafts'} saved. Submit edits sends them to the connected Agent.`);
    return true;
  } catch(error) {message(error.message+' Your draft instructions have been kept.',true);return false;} finally {saving=false;selectionChanged();}
}
$('request-form').addEventListener('submit',async event=>{
  event.preventDefault();await saveDrafts();
});
$('submit-edits').addEventListener('click',async()=>{
  if(loading||saving||operating||runningJob()||!state?.version||!agentConnected()) return;
  if(!await saveDrafts())return;
  const ids=currentPending().map(item=>item.id);if(!ids.length)return;
  operating=true;controls();
  try {
    const result=await api('/api/agent/jobs',{version:state.version,request_ids:ids,attempt_id:state.attempt_id});
    activeJob=result.job;jobStatusError=null;renderJob();scheduleJobPoll();message(activeJob.backend==='session'?(scheduledOriginalConnection()?'Edits saved for your original conversation. '+checkIntervalHint()+' The scheduled check will look for them.':'Edits queued for your original conversation. Its connected Agent will continue when it receives the submission.'):'Edit task submitted to the separate worker. Its actual progress and result appear here.');
  } catch(error) {message(error.message+' Saved instructions have been kept.',true);} finally {operating=false;controls();renderJob();}
});
$('connect-agent').addEventListener('click',async()=>{
  if(loading||saving||operating||runningJob())return;
  if(!agentConnection?.enabled) {
    readNote('Connect your original Agent','Ask the Agent in the conversation that opened EasyViz to connect this workbench through MCP and wait for submitted edits. This page cannot identify or wake that conversation by itself. Your saved drafts remain available; it will not start a separate Agent session.');
    return;
  }
  operating=true;++agentRevision;controls();
  try {
    const result=await api('/api/agent/configure',{backend:originalSessionConnection()?'session':'codex',enabled:false});
    agentConnection=result.agent||result;
    message(agentConnection.message||agentConnection.reason||'Agent disconnected. Saved instructions remain available.');
  } catch(error) {message(error.message,true);} finally {operating=false;controls();}
});
$('open-library').addEventListener('click',()=>{showLibrary(!libraryVisible);if(libraryVisible)refreshService();});
$('refresh-library').addEventListener('click',refreshLibrary);
$('import-document').addEventListener('click',()=>$('document-file').click());
$('document-file').addEventListener('change',()=>openDocument($('document-file').files?.[0]));
$('undo').addEventListener('click',async()=>{
  if(loading||saving||operating||!state) return;
  const item=[...state.requests].reverse().find(item=>item.status==='pending'&&item.current_version);if(!item) return;
  saving=true;controls();
  try {const result=await api('/api/undo',{version:state.version,request_id:item.id});updateQueue(result.state);annotations=annotations.filter(note=>note.request_id!==item.id);if(!activeAnnotation())activeNumber=annotations.find(note=>!note.saved)?.number??annotations[0]?.number??null;persistDrafts();message('Last request undone. The figure exports are unchanged.');} catch(error) {message(error.message,true);} finally {saving=false;selectionChanged();}
});
$('open-job-result').addEventListener('click',()=>switchAttempt(activeJob?.target_attempt_id));
$('review-remaining-requests').addEventListener('click',async()=>{
  if(loading||saving||operating||runningJob()||!activeJob?.source_attempt_id) return;
  const source=activeJob.source_attempt_id;
  if(source!==state?.attempt_id&&!await switchAttempt(source)) return;
  showPanel('requests');
  message('Remaining instructions are shown on the original figure. They were not applied to the new preview. Submitting here starts another branch from the original; annotate the preview to continue from the changes already made.');
});
$('attempt-list').addEventListener('change',()=>switchAttempt($('attempt-list').value));
$('compare-toggle').addEventListener('click',()=>{
  if(loading||saving||operating) return;
  comparisonVisible=!comparisonVisible;
  $('comparison').hidden=!state?.comparison||!comparisonVisible;
  $('current-label').hidden=!state?.comparison||!comparisonVisible;
  $('figure-host').parentNode?.classList.toggle('has-comparison',!!state?.comparison&&comparisonVisible);
  serviceControls();drawAnnotations();
});
$('cancel-job').addEventListener('click',async()=>{
  if(!runningJob()||operating) return;operating=true;controls();renderJob();
  try {const result=await api('/api/jobs/'+encodeURIComponent(activeJob.id)+'/cancel',{});activeJob=result.job;jobStatusError=null;renderJob();scheduleJobPoll();message(activeJob.status==='cancelled'?'Preview cancelled. The current attempt has been kept.':'Cancellation requested; waiting for the renderer to stop.');}
  catch(error) {message(error.message,true);} finally {operating=false;controls();renderJob();}
});
$('accept-attempt').addEventListener('click',async()=>{
  if(loading||saving||operating||runningJob()||!state?.attempt_id) return;operating=true;controls();
  try {const result=await api('/api/attempts/accept',{attempt_id:state.attempt_id,validation:'Reviewed by the user in the EasyViz workbench.'});if(result.state)updateQueue(result.state);await refreshService();message('This attempt is accepted and available to restore.');}
  catch(error) {message(error.message,true);} finally {operating=false;controls();}
});
$('restore-attempt').addEventListener('click',async()=>{
  if(loading||saving||operating||runningJob()||!state) return;captureAnnotation();persistDrafts();operating=true;controls();
  try {const result=await api('/api/attempts/restore',{});operating=false;const loaded=result.attempt?.id?await switchAttempt(result.attempt.id):await load(result.state);if(!loaded)return;message('Restored the accepted source and specification as a separate attempt.');}
  catch(error) {message(error.message,true);} finally {operating=false;controls();}
});
window.addEventListener('resize',()=>{if(!drag)drawAnnotations();});
load();
scheduleAgentPoll();
