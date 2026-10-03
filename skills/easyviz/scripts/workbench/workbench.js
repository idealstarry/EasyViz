'use strict';
const $ = (id) => document.getElementById(id);
let state, svg, annotations = [], activeNumber = null, nextNumber = 1, mode = 'element', drag = null;
let loading = false, saving = false;
let storageUnavailable = false;
const NS = 'http://www.w3.org/2000/svg';
const dropdowns = new Map();
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
  const panel = entry.wrapper.closest('.inspector-panel');
  if (panel && getComputedStyle(panel).overflowY === 'auto') {
    entry.menu.style.maxHeight = Math.max(44, Math.min(210, panel.clientHeight-44))+'px';
    const overflow = entry.menu.getBoundingClientRect().bottom - panel.getBoundingClientRect().bottom + 2;
    if (overflow > 0) panel.scrollTop += overflow;
  }
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
  if (!select.ownerDocument) return;
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
  const options = payload ? {method:'POST', headers:{'Content-Type':'application/json','X-EasyViz-Token':state.token}, body:JSON.stringify(payload)} : {};
  const response = await fetch(path, options);
  const body = await response.json();
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
  $('preview-size').textContent=mode==='region'?'Drag to add a numbered region':element?element.label+' · '+element.role.replaceAll('-',' '):'Click to add an annotation';
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
function annotationElements(note) { return state.elements.filter(element=>(note?.element_ids||[]).includes(element.id)); }
function annotationLabel(note) {
  const elements=annotationElements(note);
  return elements.length===1?elements[0].label:elements.length?elements.length+' mapped elements':note.region_mm?'Selected region':'Whole figure';
}
function draftKey() { return 'easyviz-annotations:'+state.figure_name+':'+JSON.stringify(state.version); }
function annotationStatus() {
  const note=activeAnnotation();
  $('annotation-state').hidden=!note||(!note.saved&&!storageUnavailable);
  $('annotation-state').textContent=note?.saved?'Saved · use Requests to undo this instruction':storageUnavailable?'Draft · save before closing or refreshing this page':'Draft · this instruction has not been saved';
}
function persistDrafts() {
  if(!state) return;
  try { sessionStorage.setItem(draftKey(),JSON.stringify({nextNumber,activeNumber,notes:annotations.filter(note=>!note.saved)}));storageUnavailable=false; } catch (_) { storageUnavailable=true; }
  annotationStatus();
}
function captureAnnotation() {
  const note=activeAnnotation();
  if(!note||note.saved) return;
  note.instruction=$('instruction').value;note.property=$('property').value;note.value=$('property-value').value;
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
    let bx=Math.max(vx,Math.min(vx+vw-badgeWidth,vx+anchor.x/state.panel.width_mm*vw-badgeWidth/2));
    let by=Math.max(vy,Math.min(vy+vh-badgeHeight,vy+anchor.y/state.panel.height_mm*vh-badgeHeight/2));
    // Stack badges at a shared corner so every number remains clickable.
    for(let attempt=0;attempt<annotations.length;attempt++) {
      if(!placed.some(box=>bx<box.x+box.width&&bx+badgeWidth>box.x&&by<box.y+box.height&&by+badgeHeight>box.y)) break;
      if(by+2*badgeHeight+3/scaleY<=vy+vh) by+=badgeHeight+3/scaleY;
      else {by=vy;bx=Math.max(vx,bx-badgeWidth-3/scaleX);}
    }
    placed.push({x:bx,y:by,width:badgeWidth,height:badgeHeight});
    const badge=document.createElementNS(NS,'g');badge.setAttribute('class','annotation-badge'+(active?' active':''));
    badge.setAttribute('role','button');badge.setAttribute('tabindex','0');badge.setAttribute('aria-label',`Annotation ${note.number}: ${annotationLabel(note)}`);badge.setAttribute('aria-pressed',String(active));
    badge.setAttribute('data-annotation-number',String(note.number));
    const tile=document.createElementNS(NS,'rect');
    for(const [key,value] of Object.entries({x:bx,y:by,width:badgeWidth,height:badgeHeight,rx:6/scaleX,ry:6/scaleY})) tile.setAttribute(key,String(value));
    const label=document.createElementNS(NS,'text');label.setAttribute('x',String(bx+badgeWidth/2));label.setAttribute('y',String(by+badgeHeight/2));label.setAttribute('font-size',String(11/scaleY));label.textContent=String(note.number);
    badge.append(tile,label);
    badge.addEventListener('click',event=>{event.stopPropagation();if(!loading&&!saving) focusAnnotation(note.number);});
    badge.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();event.stopPropagation();if(!loading&&!saving)focusAnnotation(note.number);}});
    layer.append(badge);
  }
  svg.append(layer);
}
function annotationChips() {
  const list=$('annotation-list');list.replaceChildren();
  if(!annotations.length) {const empty=document.createElement('p');empty.className='empty';empty.textContent='Click elements or draw regions to add numbered annotations.';list.append(empty);}
  for(const note of annotations) {
    const chip=document.createElement('button');chip.type='button';chip.className='annotation-chip'+(note.saved?' saved':note.instruction.trim()?' complete':'');chip.textContent=String(note.number);
    chip.setAttribute('aria-label',`Annotation ${note.number}: ${annotationLabel(note)}, ${note.saved?'saved':note.instruction.trim()?'ready to save':'draft'}`);
    chip.setAttribute('aria-pressed',String(note.number===activeNumber));chip.disabled=loading||saving;
    chip.addEventListener('click',()=>focusAnnotation(note.number));list.append(chip);
  }
}
function focusAnnotation(number) {
  if(loading||saving) return;
  captureAnnotation();activeNumber=number;showPanel('edit');selectionChanged();persistDrafts();
}
function addAnnotation(target,forceNew=false) {
  if(loading||saving||!state||!svg) return;
  captureAnnotation();
  const signature=note=>JSON.stringify({ids:[...(note.element_ids||[])].sort(),region:note.region_mm||null,selector:note.selector||null});
  const existing=!forceNew&&(annotations.find(note=>!note.saved&&signature(note)===signature(target))||annotations.find(note=>signature(note)===signature(target)));
  if(existing) {focusAnnotation(existing.number);return;}
  if(annotations.filter(note=>!note.saved).length>=100) {message('Save or remove some drafts before adding more annotations.',true);return;}
  if(nextNumber>1000000) {message('The annotation number limit has been reached for this figure version.',true);return;}
  const note={...target,element_ids:target.element_ids||[],number:nextNumber++,instruction:'',property:'',value:'',saved:false};
  note.anchor_mm=annotationAnchor(note);annotations.push(note);activeNumber=note.number;
  showPanel('edit');selectionChanged();persistDrafts();message(`Annotation ${note.number} added. Select another location or write its instruction.`);
}
function selectElements(ids,selector=null) {
  addAnnotation({element_ids:[...new Set(ids)].filter(id=>state.elements.some(element=>element.id===id)),...(selector?{selector}:{})});
}
function matches(element, selector) {
  const keys=element.source_keys||[];
  return (!selector.role||element.role===selector.role)&&(!selector.spec_path||(element.spec_paths||[]).includes(selector.spec_path))&&(!selector.category||keys.some(key=>key.category===selector.category||key.group===selector.category))&&(!selector.source_key||keys.some(key=>Object.entries(selector.source_key).every(([name,value])=>Object.hasOwn(key,name)&&key[name]===value)));
}
function semanticOptions() {
  const list=$('semantic-list');list.replaceChildren(new Option('Choose a category, role or source/spec path…',''));
  const choices=new Map();
  const add=(label,selector)=>choices.set(JSON.stringify(selector),label);
  for(const element of state.elements) {
    add('Role · '+element.role,{role:element.role});
    for(const path of element.spec_paths||[]) add('Spec · '+path,{spec_path:path});
    for(const key of element.source_keys||[]) {
      for(const name of ['category','group']) if(typeof key[name]==='string') add('Category · '+key[name],{category:key[name]});
      for(const [name,value] of Object.entries(key)) if(['string','number','boolean'].includes(typeof value)&&!['group','category'].includes(name)) add(`Source · ${name} = ${value}`,{source_key:{[name]:value}});
    }
  }
  for(const [value,label] of choices) list.add(new Option(label,value));
  syncDropdown('semantic-list');
}
function selectionChanged() {
  const note=activeAnnotation(),elements=annotationElements(note),region=note?.region_mm;
  $('element-list').value=elements.length===1?elements[0].id:'';
  $('semantic-list').value=note?.selector?JSON.stringify(note.selector):'';
  $('active-annotation').hidden=!note;annotationStatus();
  $('annotation-title').textContent=note?`${note.number} · ${annotationLabel(note)}`:'';
  $('remove-annotation').hidden=!note||note.saved;
  $('new-instruction').hidden=!note||!note.saved;
  $('remove-annotation').setAttribute('aria-label',note?`Remove annotation ${note.number}`:'Remove annotation');
  const property=$('property'); property.replaceChildren(new Option('Free-form instruction',''));
  if(elements.length) {
    const properties=element=>Array.isArray(element.editable)?element.editable:Object.keys(element.editable||{});
    const editable=properties(elements[0]).filter(name=>elements.every(element=>properties(element).includes(name)));
    for(const name of editable) property.add(new Option(propertyNames[name]||name.replaceAll('_',' '),name));
    $('selection-details').textContent=elements.length===1?elements[0].label+' · '+elements[0].role:`${elements.length} mapped elements · `+elements.slice(0,4).map(element=>element.label).join(', ');
  } else if(region) {
    $('selection-details').textContent=`Region: ${region.x.toFixed(2)}, ${region.y.toFixed(2)} mm · ${region.width.toFixed(2)} × ${region.height.toFixed(2)} mm (top-left origin)`;
  } else { $('selection-details').textContent=note?'Whole figure / general note':'Select a location or add a general note.'; }
  $('selection-details').hidden=!region;
  $('property').value=note?.property||'';$('instruction').value=note?.instruction||'';
  $('value-field').hidden=!note?.property;$('property-value').value=note?.value??'';
  syncDropdown('property');syncDropdown('semantic-list');
  annotationChips();highlight(null);drawAnnotations();controls();
}

function restoreAnnotations(memoryDrafts=null) {
  const numbered=state.requests.filter(item=>item.current_version&&Number.isInteger(item.annotation_number));
  nextNumber=Math.max(1,...numbered.map(item=>item.annotation_number+1));
  annotations=numbered.filter(item=>item.status==='pending').map(item=>({number:item.annotation_number,element_ids:item.element_ids||[],...(item.selector?{selector:item.selector}:{}),...(item.region_mm?{region_mm:item.region_mm}:{}),...(item.anchor_mm?{anchor_mm:item.anchor_mm}:{}),instruction:item.instruction,property:item.property||'',value:item.value??'',saved:true,request_id:item.id}));
  let stored=memoryDrafts;
  if(!stored) try {stored=JSON.parse(sessionStorage.getItem(draftKey())||'null');} catch (_) { storageUnavailable=true; }
  if(stored&&Array.isArray(stored.notes)) {
    if(Number.isInteger(stored.nextNumber)&&stored.nextNumber>0&&stored.nextNumber<=1000001) nextNumber=Math.max(nextNumber,stored.nextNumber);
    for(const entry of stored.notes.slice(0,100)) {
      if(!Number.isInteger(entry.number)||entry.number<=0||entry.number>1000000||typeof entry.instruction!=='string'||!Array.isArray(entry.element_ids)||entry.element_ids.some(id=>!state.elements.some(element=>element.id===id))) continue;
      if(entry.region_mm) {
        const r=entry.region_mm;
        if(![r.x,r.y,r.width,r.height].every(Number.isFinite)||r.x<0||r.y<0||r.width<=0||r.height<=0||r.x+r.width>state.panel.width_mm||r.y+r.height>state.panel.height_mm) continue;
      }
      const committed=numbered.find(item=>item.annotation_number===entry.number);
      if(committed&&committed.instruction===entry.instruction.trim()&&JSON.stringify(committed.element_ids||[])===JSON.stringify(entry.element_ids)&&JSON.stringify(committed.region_mm||null)===JSON.stringify(entry.region_mm||null)&&(committed.property||'')===(entry.property||'')&&String(committed.value??'')===String(entry.value??'')) continue;
      const note={...entry,saved:false};
      if(committed||annotations.some(item=>item.number===note.number)) note.number=nextNumber++;
      nextNumber=Math.max(nextNumber,note.number+1);annotations.push(note);
    }
  }
  activeNumber=annotations.some(note=>note.number===stored?.activeNumber)?stored.activeNumber:annotations.find(note=>!note.saved)?.number??annotations[0]?.number??null;
  persistDrafts();
}
function queue() {
  const pending = state.requests.filter(item=>item.status==='pending'&&item.current_version).length;
  $('request-count').textContent = String(pending); $('request-count').hidden = !pending;
  const list=$('request-list');list.replaceChildren();
  if(!state.requests.length) { const p=document.createElement('p');p.className='empty';p.textContent='No changes requested yet.';list.append(p); }
  for(const [index,item] of state.requests.entries()) {
    const row=document.createElement('div');row.className='request-item';
    row.classList.toggle('undone',['undone','superseded'].includes(item.status));row.classList.toggle('older',!item.current_version);
    const label=document.createElement('p');label.className='request-label';label.textContent=`${item.annotation_number?'#'+item.annotation_number:'Request '+(index+1)} · ${item.elements?.length>1?item.elements.length+' mapped elements':item.element?.label|| (item.region_mm?'Selected region':'Whole figure')}`;
    const instruction=document.createElement('p');instruction.textContent=item.instruction;
    const status=document.createElement('p');status.className='request-status';status.textContent=`${item.status}${item.current_version?'':' · older figure version'}${item.result?.target_attempt?' · '+item.result.target_attempt.split('/').pop():''}`;
    row.append(label,instruction,status);list.append(row);
  }
  const history=$('history-list');history.replaceChildren();
  $('history-section').hidden=!(state.history||[]).length;
  $('history-empty').hidden=!!(state.history||[]).length;
  for(const item of state.history||[]) {
    const row=document.createElement('p');row.className='request-status';
    const target=item.target_attempt?.split('/').pop()||(item.version?.figure_sha256?'version '+item.version.figure_sha256.slice(0,8):'version');
    row.textContent=`${item.action} · ${target}${item.validation?' · '+item.validation:''}`;history.append(row);
  }
  controls();
}
function controls() {
  const busy=loading||saving;
  const note=activeAnnotation(),ready=annotations.filter(note=>!note.saved&&note.instruction.trim()).length;
  $('reload').disabled=busy;
  $('save').disabled=busy||!ready||!state||!svg||state.source_current===false;
  $('save').textContent=saving?'Saving…':ready?`Save requests (${ready})`:'Save requests';
  $('undo').disabled=busy||!state||!state.requests.some(item=>item.status==='pending'&&item.current_version);
  for(const id of ['element-list','semantic-list','region-mode','add-general']) $(id).disabled=busy||!svg;
  $('clear').disabled=busy||!annotations.some(note=>!note.saved);
  $('remove-annotation').disabled=busy||!note||note.saved;
  $('new-instruction').disabled=busy||!note||!note.saved;
  for(const id of ['instruction','property','property-value']) $(id).disabled=busy||!note||note.saved;
  $('element-mode').disabled=busy||!state?.manifest_valid;
  for(const chip of $('annotation-list').children) if(chip.tagName==='BUTTON') chip.disabled=busy;
  syncDropdown('property');
  syncDropdown('semantic-list');
}
function updateQueue(nextState) {
  // An HTTP response can observe a subsequent render. Queue updates never
  // replace the version or geometry of the SVG that the user is still viewing.
  const sameVersion=(left,right)=>JSON.stringify(left)===JSON.stringify(right);
  state={...state,history:nextState.history||state.history,requests:nextState.requests.map(item=>({...item,current_version:sameVersion(item.version,state.version)}))};
  queue();
}
async function load() {
  if(loading||saving) return;
  captureAnnotation();persistDrafts();
  const previousIdentity=state?draftKey():null;
  const memoryDrafts={nextNumber,activeNumber,notes:annotations.filter(note=>!note.saved)};
  loading=true;drag=null;controls();
  try {
    const nextState=await api('/api/state');
    const response=await fetch('/api/preview.svg?v='+encodeURIComponent(nextState.version.figure_sha256));
    if(!response.ok) { const error=await response.json();throw new Error(error.error||'Figure preview is unavailable.'); }
    const documentSvg=new DOMParser().parseFromString(await response.text(),'image/svg+xml');
    if(documentSvg.querySelector('parsererror')) throw new Error('The SVG preview could not be opened.');
    const nextSvg=document.importNode(documentSvg.documentElement,true);
    nextSvg.setAttribute('preserveAspectRatio','xMidYMid meet');nextSvg.setAttribute('role','img');nextSvg.setAttribute('aria-label','Scientific figure preview');
    // Commit a figure and its version together only after both have loaded.
    let previousSvg=null;
    if(nextState.comparison) {
      const previous=await fetch('/api/compare.svg?v='+encodeURIComponent(nextState.comparison.version.figure_sha256));
      if(!previous.ok) { const error=await previous.json();throw new Error(error.error||'Previous attempt preview is unavailable.'); }
      const parsed=new DOMParser().parseFromString(await previous.text(),'image/svg+xml');
      if(parsed.querySelector('parsererror')) throw new Error('The previous SVG could not be opened.');
      previousSvg=document.importNode(parsed.documentElement,true);previousSvg.setAttribute('preserveAspectRatio','xMidYMid meet');previousSvg.setAttribute('role','img');previousSvg.setAttribute('aria-label','Previous attempt; read-only');
    }
    state=nextState;svg=nextSvg;
    $('figure-host').replaceChildren(svg);
    $('figure-name').textContent=state.figure_name;
    $('track').textContent=state.track;$('track').hidden=!state.track;
    $('dimensions').textContent=`${state.panel.width_mm.toFixed(1)} × ${state.panel.height_mm.toFixed(1)} mm`;
    $('selection-message').textContent='Click elements or draw regions to add numbered annotations, then write an instruction for each.';
    $('source-status').textContent=state.source_current===false?'Source files have changed. Render a fresh attempt before saving.':state.source_current===true?'Figure and source versions verified.':'Source verification unavailable. Your Agent must verify the source before applying requests.';
    $('source-status').classList.toggle('error',state.source_current===false);
    $('comparison').hidden=!previousSvg;$('current-label').hidden=!previousSvg;
    $('figure-host').parentNode?.classList.toggle('has-comparison',!!previousSvg);
    $('comparison-host').replaceChildren(...(previousSvg?[previousSvg]:[]));
    $('comparison-label').textContent=state.comparison?'Previous · '+state.comparison.figure_name:'';
    $('current-label').textContent='Current · '+state.figure_name;
    $('element-list').replaceChildren(new Option('Whole figure / general note',''));
    for(const element of state.elements) $('element-list').add(new Option(`${element.label} · ${element.role}`,element.id));
    semanticOptions();
    restoreAnnotations(draftKey()===previousIdentity?memoryDrafts:null);
    $('downloads').replaceChildren();
    for(const extension of ['svg','pdf','png']) if(state.files.includes('panel.'+extension)) {const link=document.createElement('a');link.href='/files/panel.'+extension;link.download='panel.'+extension;link.textContent=extension.toUpperCase();$('downloads').append(link);}
    selectionChanged();queue();setMode(state.manifest_valid?'element':'region');
    message('Select numbered annotations to edit their instructions. Save requests saves every completed draft.');
  } catch(error) {message(error.message,true);} finally {loading=false;controls();}
}
$('element-mode').addEventListener('click',()=>setMode('element'));
$('region-mode').addEventListener('click',()=>setMode('region'));
$('clear').addEventListener('click',()=>{if(loading||saving)return;annotations=annotations.filter(note=>note.saved);activeNumber=annotations[0]?.number??null;nextNumber=Math.max(1,...state.requests.filter(item=>item.current_version&&Number.isInteger(item.annotation_number)).map(item=>item.annotation_number+1));selectionChanged();persistDrafts();message('Unsaved annotations cleared. Numbering restarts after any saved requests.');});
$('remove-annotation').addEventListener('click',()=>{const note=activeAnnotation();if(loading||saving||!note||note.saved)return;annotations=annotations.filter(item=>item!==note);activeNumber=annotations.find(item=>!item.saved)?.number??annotations[0]?.number??null;selectionChanged();persistDrafts();message(`Annotation ${note.number} removed. Other numbers stay unchanged.`);});
$('add-general').addEventListener('click',()=>selectElements([]));
$('new-instruction').addEventListener('click',()=>{const note=activeAnnotation();if(!note||!note.saved)return;addAnnotation({element_ids:note.element_ids,...(note.selector?{selector:note.selector}:{}),...(note.region_mm?{region_mm:note.region_mm}:{}),anchor_mm:note.anchor_mm},true);});
$('element-list').addEventListener('change',()=>{setMode('element');selectElements([$('element-list').value].filter(Boolean));});
$('semantic-list').addEventListener('change',()=>{const value=$('semantic-list').value;if(!value)return;const selector=JSON.parse(value);setMode('element');selectElements(state.elements.filter(element=>matches(element,selector)).map(element=>element.id),selector);});
function draftChanged() {captureAnnotation();persistDrafts();annotationChips();controls();}
$('instruction').addEventListener('input',draftChanged);
$('property-value').addEventListener('input',draftChanged);
$('property').addEventListener('change',()=>{$('value-field').hidden=!$('property').value;draftChanged();});
$('reload').addEventListener('click',load);
$('figure-host').addEventListener('click',event=>{
  if(loading||saving||mode!=='element'||!svg) return;
  const element=pickElement(event);
  if(!element) {message('No mapped element here. Choose an item in the list or use Select region.');return;}
  selectElements([element.id]);
});
$('figure-host').addEventListener('pointerdown',event=>{
  if(loading||saving||mode!=='region'||!svg||!svg.contains(event.target)||event.target.closest?.('.annotation-badge')||event.button!==0) return;
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
$('request-form').addEventListener('submit',async event=>{
  event.preventDefault();if(loading||saving||!state||!svg||state.source_current===false) return;
  captureAnnotation();persistDrafts();
  const ready=annotations.filter(note=>!note.saved&&note.instruction.trim());if(!ready.length)return;
  const missing=ready.find(note=>note.property&&!String(note.value).trim());
  if(missing) {focusAnnotation(missing.number);message(`Enter a new value for annotation ${missing.number}, or choose Free-form instruction.`,true);return;}
  saving=true;controls();
  try {
    const requests=ready.map(note=>{
      const item={version:state.version,instruction:note.instruction,annotation_number:note.number,anchor_mm:note.anchor_mm};
      if(note.selector)item.selector=note.selector;
      else if(note.element_ids.length>1)item.element_ids=note.element_ids;
      else if(note.element_ids.length)item.element_id=note.element_ids[0];
      if(note.region_mm)item.region_mm=note.region_mm;
      if(note.property){item.property=note.property;item.value=note.value;}
      return item;
    });
    const result=await api('/api/requests/batch',{version:state.version,requests});
    for(const item of result.requests) {const note=annotations.find(note=>note.number===item.annotation_number);if(note){note.saved=true;note.request_id=item.id;}}
    updateQueue(result.state);persistDrafts();
    message(`${result.requests.length} ${result.requests.length===1?'request':'requests'} saved. Ask your Agent to apply the saved workbench requests.`);
  } catch(error) {message(error.message+' Your draft instructions have been kept.',true);} finally {saving=false;selectionChanged();}
});
$('undo').addEventListener('click',async()=>{
  if(loading||saving||!state) return;
  const item=[...state.requests].reverse().find(item=>item.status==='pending'&&item.current_version);if(!item) return;
  saving=true;controls();
  try {const result=await api('/api/undo',{version:state.version,request_id:item.id});updateQueue(result.state);annotations=annotations.filter(note=>note.request_id!==item.id);if(!activeAnnotation())activeNumber=annotations.find(note=>!note.saved)?.number??annotations[0]?.number??null;persistDrafts();message('Last request undone. The figure exports are unchanged.');} catch(error) {message(error.message,true);} finally {saving=false;selectionChanged();}
});
window.addEventListener('resize',()=>{if(!drag)drawAnnotations();});
load();
