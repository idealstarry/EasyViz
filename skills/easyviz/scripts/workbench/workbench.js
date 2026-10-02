'use strict';
const $ = (id) => document.getElementById(id);
let state, svg, selectedId = null, selectedIds = [], selectedSelector = null, region = null, mode = 'element', drag = null;
let loading = false, saving = false;
const NS = 'http://www.w3.org/2000/svg';
const propertyNames = { color:'Color', facecolor:'Fill color', edgecolor:'Outline color', linewidth:'Line width (pt)', line_width_pt:'Line width (pt)', text:'Text', position:'Position', position_mm:'Position (mm)', layout:'Layout', fontsize:'Font size', font_size_pt:'Font size (pt)', palette:'Palette', alpha:'Opacity (0–1)', linestyle:'Line style', legend_position:'Legend position' };
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
function highlightElements(elements) {
  highlight(null);
  for(const element of elements) {
    const node=svg.getElementById(element.id);
    if(!node) continue;
    try {
      const mark=document.createElementNS(NS,'rect'),rect=elementBox(node);
      for(const key of ['x','y','width','height']) mark.setAttribute(key,String(rect[key]));
      mark.setAttribute('data-review-highlight','true');svg.append(mark);
    } catch (_) { /* An artist without a measurable box remains selectable by ID. */ }
  }
}
function selectedElements() { return state.elements.filter(element=>selectedIds.includes(element.id)); }
function selectedElement() { return state.elements.find(element=>element.id===selectedId); }
function selectElements(ids, selector=null) {
  selectedIds=[...new Set(ids)].filter(id=>state.elements.some(element=>element.id===id));
  selectedId=selectedIds.length===1?selectedIds[0]:null;selectedSelector=selector;region=null;
  selectionChanged();
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
}
function selectionChanged() {
  const list=$('element-list');
  if(list.options) for(const option of list.options) option.selected=selectedIds.includes(option.value)||(!selectedIds.length&&!region&&option.value==='');
  else list.value=selectedId||'';
  const elements=selectedElements();
  const property=$('property'); property.replaceChildren(new Option('Free-form instruction',''));
  if(elements.length) {
    const properties=element=>Array.isArray(element.editable)?element.editable:Object.keys(element.editable||{});
    const editable=properties(elements[0]).filter(name=>elements.every(element=>properties(element).includes(name)));
    for(const name of editable) property.add(new Option(propertyNames[name]||name.replaceAll('_',' '),name));
    const paths=[...new Set(elements.flatMap(element=>element.spec_paths||[]))];
    $('selection-details').textContent=(elements.length===1?elements[0].label+' · '+elements[0].role:`${elements.length} mapped elements · `+elements.slice(0,4).map(element=>element.label).join(', '))+(paths.length?' · '+paths.join(', '):'');
    highlightElements(elements);
  } else if(region) {
    $('selection-details').textContent=`Region: ${region.x.toFixed(2)}, ${region.y.toFixed(2)} mm · ${region.width.toFixed(2)} × ${region.height.toFixed(2)} mm (top-left origin)`;
    highlight(fromMm(region));
  } else { $('selection-details').textContent='Whole figure / general note';highlight(null); }
  $('value-field').hidden=true;$('property-value').value='';
}
function queue() {
  const list=$('request-list');list.replaceChildren();
  if(!state.requests.length) { const p=document.createElement('p');p.className='empty';p.textContent='No changes requested yet.';list.append(p); }
  for(const [index,item] of state.requests.entries()) {
    const row=document.createElement('div');row.className='request-item';
    row.classList.toggle('undone',['undone','superseded'].includes(item.status));row.classList.toggle('older',!item.current_version);
    const label=document.createElement('p');label.className='request-label';label.textContent=`${index+1}. ${item.elements?.length>1?item.elements.length+' mapped elements':item.element?.label|| (item.region_mm?'Selected region':'Whole figure')}`;
    const instruction=document.createElement('p');instruction.textContent=item.instruction;
    const status=document.createElement('p');status.className='request-status';status.textContent=`${item.status}${item.current_version?'':' · older figure version'}${item.result?.target_attempt?' · '+item.result.target_attempt.split('/').pop():''}`;
    row.append(label,instruction,status);list.append(row);
  }
  const history=$('history-list');history.replaceChildren();
  $('history-section').hidden=!(state.history||[]).length;
  for(const item of state.history||[]) {
    const row=document.createElement('p');row.className='request-status';
    const target=item.target_attempt?.split('/').pop()||(item.version?.figure_sha256?'version '+item.version.figure_sha256.slice(0,8):'version');
    row.textContent=`${item.action} · ${target}${item.validation?' · '+item.validation:''}`;history.append(row);
  }
  controls();
}
function controls() {
  const busy=loading||saving;
  $('reload').disabled=busy;
  $('save').disabled=busy||!state||!svg||state.source_current===false;
  $('undo').disabled=busy||!state||!state.requests.some(item=>item.status==='pending'&&item.current_version);
  for(const id of ['element-list','semantic-list','region-mode','clear']) $(id).disabled=loading||!svg;
  $('element-mode').disabled=loading||!state?.manifest_valid;
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
    state=nextState;svg=nextSvg;selectedId=null;selectedIds=[];selectedSelector=null;region=null;
    $('figure-host').replaceChildren(svg);
    $('figure-name').textContent=state.figure_name;
    $('track').textContent=state.track;$('track').hidden=!state.track;
    $('dimensions').textContent=`${state.panel.width_mm.toFixed(1)} × ${state.panel.height_mm.toFixed(1)} mm`;
    $('selection-message').textContent=state.selection_message;
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
    $('downloads').replaceChildren();
    for(const extension of ['svg','pdf','png']) if(state.files.includes('panel.'+extension)) {const link=document.createElement('a');link.href='/files/panel.'+extension;link.download='panel.'+extension;link.textContent=extension.toUpperCase();$('downloads').append(link);}
    selectionChanged();queue();setMode(state.manifest_valid?'element':'region');
    message('Select an element or region, then save your instruction.');
  } catch(error) {message(error.message,true);} finally {loading=false;controls();}
}
$('element-mode').addEventListener('click',()=>setMode('element'));
$('region-mode').addEventListener('click',()=>setMode('region'));
$('clear').addEventListener('click',()=>{selectedId=null;selectedIds=[];selectedSelector=null;region=null;$('semantic-list').value='';selectionChanged();});
$('element-list').addEventListener('change',()=>{const list=$('element-list');const ids=list.selectedOptions?[...list.selectedOptions].map(option=>option.value).filter(Boolean):[list.value].filter(Boolean);setMode('element');$('semantic-list').value='';selectElements(ids);});
$('semantic-list').addEventListener('change',()=>{const value=$('semantic-list').value;if(!value)return;const selector=JSON.parse(value);setMode('element');selectElements(state.elements.filter(element=>matches(element,selector)).map(element=>element.id),selector);});
$('property').addEventListener('change',()=>{$('value-field').hidden=!$('property').value;});
$('reload').addEventListener('click',load);
$('figure-host').addEventListener('click',event=>{
  if(loading||mode!=='element'||!svg) return;
  let node=event.target;
  while(node&&node!==svg) {if(state.elements.some(element=>element.id===node.id)){const ids=event.shiftKey?(selectedIds.includes(node.id)?selectedIds.filter(id=>id!==node.id):[...selectedIds,node.id]):[node.id];$('semantic-list').value='';selectElements(ids);return;}node=node.parentNode;}
});
$('figure-host').addEventListener('pointerdown',event=>{
  if(loading||mode!=='region'||!svg||!svg.contains(event.target)||event.button!==0) return;
  event.preventDefault();$('figure-host').setPointerCapture(event.pointerId);drag=svgPoint(event);selectedId=null;selectedIds=[];selectedSelector=null;region=null;
});
$('figure-host').addEventListener('pointermove',event=>{
  if(!drag) return;const point=svgPoint(event);highlight({x:Math.min(point.x,drag.x),y:Math.min(point.y,drag.y),width:Math.abs(point.x-drag.x),height:Math.abs(point.y-drag.y)});
});
$('figure-host').addEventListener('pointerup',event=>{
  if(!drag) return;const point=svgPoint(event),rect={x:Math.min(point.x,drag.x),y:Math.min(point.y,drag.y),width:Math.abs(point.x-drag.x),height:Math.abs(point.y-drag.y)};
  drag=null;region=rect.width>0&&rect.height>0?toMm(rect):null;selectionChanged();
});
$('figure-host').addEventListener('pointercancel',()=>{drag=null;selectionChanged();});
$('request-form').addEventListener('submit',async event=>{
  event.preventDefault();if(loading||saving||!state||!svg||state.source_current===false) return;saving=true;controls();
  try {
    const payload={version:state.version,instruction:$('instruction').value};
    if(selectedSelector) payload.selector=selectedSelector;
    else if(selectedIds.length>1) payload.element_ids=selectedIds;
    else payload.element_id=selectedId;
    if(region) payload.region_mm=region;
    if($('property').value) {payload.property=$('property').value;payload.value=$('property-value').value;}
    const result=await api('/api/requests',payload);updateQueue(result.state);$('instruction').value='';
    message('Request saved. Ask your Agent to read requests.json and render a new attempt.');
  } catch(error) {message(error.message,true);} finally {saving=false;controls();}
});
$('undo').addEventListener('click',async()=>{
  if(loading||saving||!state) return;
  const item=[...state.requests].reverse().find(item=>item.status==='pending'&&item.current_version);if(!item) return;
  saving=true;controls();
  try {const result=await api('/api/undo',{version:state.version,request_id:item.id});updateQueue(result.state);message('Last request undone. The figure exports are unchanged.');} catch(error) {message(error.message,true);} finally {saving=false;controls();}
});
load();
