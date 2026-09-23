"""Dependency-free, accessible browser review surface for live microscopy QC."""

DEMO_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>HAL LabSight — Agentic Microscopy QC</title>
<style>
:root{color-scheme:dark;font-family:ui-sans-serif,system-ui,sans-serif;--bg:#080e14;--panel:#101b26;--line:#314355;--muted:#b4c4d2;--ink:#f1f6fa;--accent:#8fe3dc}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);line-height:1.55}
main{max-width:1180px;margin:0 auto;padding:28px 24px 64px}a{color:var(--accent)}
.skip{position:absolute;top:-80px;background:var(--panel);padding:12px;z-index:9}.skip:focus{top:8px}
header{padding:18px 0 28px;border-bottom:1px solid var(--line)}.eyebrow{font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);font-weight:750}
h1{font-size:clamp(2.6rem,5vw,4.1rem);letter-spacing:-.05em;line-height:1.08;margin:12px 0}h2{font-size:1.25rem;margin:0 0 12px}h3{font-size:1.05rem;margin:0 0 8px}
p{margin:8px 0 16px}.sub,.note,figcaption{color:var(--muted)}.lead{max-width:760px;font-size:1.08rem}.note{font-size:.88rem}
.badge{display:inline-block;padding:4px 10px;border:1px solid var(--line);border-radius:6px;font-size:.8rem;margin:4px 8px 4px 0}
.runtime{margin:14px 0 0;font-size:.9rem;color:var(--muted);overflow-wrap:anywhere}
.grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:24px 0}
.card,.panel{border:1px solid var(--line);border-radius:12px;background:var(--panel);padding:18px}.card p{font-size:.9rem;color:var(--muted);min-height:44px}
button{border:1px solid #53768a;border-radius:7px;padding:11px 15px;background:#183448;color:var(--ink);font:inherit;font-weight:650;cursor:pointer}
button:hover{background:#254b60}button:disabled{opacity:.5;cursor:not-allowed}button:focus-visible,input:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.card button{width:100%}.primary{background:#134d4a;border-color:#80d5cb}.primary:hover{background:#19625e}.toolbar{display:flex;gap:12px;align-items:center;flex-wrap:wrap;margin:18px 0}
.workspace{display:grid;grid-template-columns:minmax(230px,340px) minmax(0,1fr);gap:20px}.workspace>*{min-width:0}
input[type=file]{display:block;width:100%;margin:14px 0;font:inherit;font-size:.86rem}label{font-weight:700}
figure{margin:18px 0 0}#preview{width:100%;aspect-ratio:1;object-fit:contain;background:#05090d;border:1px solid var(--line);border-radius:8px}figcaption{font-size:.85rem;margin:8px 0}
#status{min-height:30px;margin:0 0 12px;font-weight:650}#status[data-state=error]{color:#ffb8b8}
#decision{font-size:1.55rem;line-height:1.3;margin:8px 0}.ok{color:#8fe3bd}.warn{color:#ffdc98}.fail{color:#ffb8b8}
.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:18px 0}.metric{padding:10px;border:1px solid var(--line);border-radius:7px;overflow-wrap:anywhere}.metric dt{font-size:.78rem;color:var(--muted)}.metric dd{margin:2px 0;font-size:1.08rem;font-variant-numeric:tabular-nums}
.trace{padding:0;list-style:none}.trace li{border-left:3px solid #5689a0;padding:6px 0 8px 16px;margin:14px 0}.trace h3{color:var(--accent)}.trace .metrics{margin:10px 0}.trace .metric{background:#0b141d}
.scenario{border-top:1px solid var(--line);padding:18px 0}.scenario:first-child{border-top:0}details{margin-top:18px}summary{cursor:pointer;font-weight:650}pre{white-space:pre-wrap;overflow-wrap:anywhere;padding:16px;background:#050a10;border:1px solid var(--line);border-radius:8px;max-height:480px;overflow:auto;font-size:.83rem}
[hidden]{display:none!important}footer{margin-top:24px;border-top:1px solid var(--line);padding-top:18px}
@media(max-width:840px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.workspace{grid-template-columns:1fr}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}#preview{max-height:300px}}
@media(max-width:430px){main{padding:18px 14px 40px}.card,.panel{padding:14px}.grid{gap:8px}.card button{font-size:.88rem;padding:10px 6px}}
</style>
</head>
<body>
<a class="skip" href="#review">Skip to QC review</a>
<main>
<header>
<div class="eyebrow">UniteAndCreateForLife / Open visual instrumentation</div>
<h1>HAL LabSight</h1>
<p class="lead">See the capture. Follow the evidence. Understand the next action.</p>
<p class="sub">Microscopy image-quality control with an auditable OpenCV perception → decision → action loop. Not a diagnostic system.</p>
<span class="badge">Image quality only</span><span class="badge">Human review retained</span><span class="badge">No cloud account needed for this demo</span>
<p class="runtime" id="runtime" role="status" aria-live="polite">Checking this server's runtime…</p>
<p class="note">Runtime checks below do not prove AWS deployment or competition submission readiness.</p>
</header>
<section aria-label="Deterministic synthetic examples" class="grid">
<div class="card"><h2>01 / Clean</h2><p>Inspect a capture expected to pass the QC gates.</p><button data-scenario="clean">Analyze clean</button></div>
<div class="card"><h2>02 / Blur</h2><p>Severe blur should request a focused recapture.</p><button data-scenario="blurred">Analyze blurred</button></div>
<div class="card"><h2>03 / Illumination</h2><p>Uneven lighting should invoke CLAHE, then re-measure.</p><button data-scenario="uneven">Analyze uneven</button></div>
<div class="card"><h2>04 / Exposure</h2><p>Clipped pixels should request an exposure recapture.</p><button data-scenario="clipped">Analyze clipped</button></div>
</section>
<div class="toolbar"><button class="primary" id="judge">Run judge suite</button><span class="note">Four synthetic regression scenarios. Not real-world validation.</span></div>
<div class="workspace">
<aside class="panel">
<h2>Your capture</h2><label for="file">Choose a PNG or JPEG</label>
<input id="file" type="file" accept="image/png,image/jpeg" aria-describedby="upload-help" />
<p id="upload-help" class="note">Maximum 8 MiB, 8192 pixels per axis, 16 megapixels total. Use open or consented, non-sensitive images only.</p>
<button id="upload">Analyze uploaded image</button>
<p class="note">Analysis sends the selected image to the server hosting this page. The preview stays in your browser. Downloads exclude image bytes and filenames.</p>
<figure id="preview-panel" hidden><img id="preview" alt="" /><figcaption id="preview-caption"></figcaption></figure>
</aside>
<section class="panel" id="review" tabindex="-1" aria-labelledby="review-title">
<h2 id="review-title">Evidence workspace</h2>
<p id="status" role="status" aria-live="polite" aria-atomic="true">Choose an example or run the judge suite.</p>
<div id="summary" hidden><p id="decision"></p><p id="reason" class="sub"></p><div id="metrics"></div><div id="trace"></div></div>
<div id="suite" hidden></div>
<div class="toolbar"><button id="download" disabled>Download evidence JSON</button></div>
<p class="note">Download scope: interactive demo receipt, not AWS or final-submission evidence. No automatic diagnosis or microscope control is performed.</p>
<details><summary>Inspect complete response and receipt</summary><pre id="result">No analysis yet.</pre></details>
</section>
</div>
<footer><h2>Interpretation and limitations</h2><p class="note">Focus, illumination, clipping and segmentation measurements are heuristic capture-quality signals. An accepted capture is not a biological or clinical conclusion. Synthetic demonstrations are regression checks, not independent validation. Ambiguous captures remain subject to human review; inspect the full trace and use the documented evaluation corpus for quantitative claims.</p></footer>
</main>
<script>
'use strict';
const el = id => document.getElementById(id);
const LABELS = Object.freeze({accept:'Accept capture',request_recapture_focus:'Recapture: adjust focus',request_recapture_exposure:'Recapture: adjust exposure',enhance_and_reanalyze:'Run CLAHE and re-analyze',human_review:'Human review required'});
const METRICS = [['focus_variance','Focus score',false],['illumination_cv','Illumination CV',false],['saturation_fraction','Clipped pixels',true],['edge_density','Edge density',true],['foreground_fraction','Foreground',true],['object_count','Connected objects',false]];
const MAX_BYTES = 8 * 1024 * 1024;
let receipt = null, previewUrl = null, requestSerial = 0, activeController = null;
function node(tag, text, css) { const n=document.createElement(tag); if(text!==undefined) n.textContent=String(text); if(css) n.className=css; return n; }
function actionLabel(action) { return Object.hasOwn(LABELS,action) ? LABELS[action] : 'Unrecognized action'; }
function metricGrid(values) {
  const grid=node('dl',undefined,'metrics');
  for(const [key,label,percent] of METRICS) {
    const value=values?.[key], box=node('div',undefined,'metric');
    const text=typeof value==='number' && Number.isFinite(value) ? (percent ? `${(value*100).toFixed(2)}%` : key==='object_count' ? String(value) : value.toFixed(3)) : 'Not reported';
    box.append(node('dt',label),node('dd',text)); grid.append(box);
  }
  return grid;
}
function traceView(trace) {
  const list=node('ol',undefined,'trace'); list.setAttribute('aria-label','Perception decision action trace');
  for(const step of trace || []) {
    const item=node('li'); item.append(node('h3',`Pass ${step.step}: ${actionLabel(step.decision)}`),node('p',step.reason || 'Reason not reported','note'),metricGrid(step.observation));
    if(step.decision==='enhance_and_reanalyze') item.append(node('p','Next action: OpenCV CLAHE tool call → second visual measurement.','note'));
    list.append(item);
  }
  return list;
}
function clearPreview() {
  if(previewUrl) { URL.revokeObjectURL(previewUrl); previewUrl=null; }
  el('preview').removeAttribute('src'); el('preview-panel').hidden=true;
}
function preview(src, caption, alt) { el('preview').src=src; el('preview').alt=alt; el('preview-caption').textContent=caption; el('preview-panel').hidden=false; }
function busy(value) {
  document.querySelectorAll('button').forEach(b => { b.disabled=value; });
  el('file').disabled=value; el('download').disabled=value || !receipt;
  el('review').setAttribute('aria-busy',String(value));
}
function clearResult() {
  receipt=null; el('download').disabled=true; el('summary').hidden=true; el('suite').hidden=true; el('suite').replaceChildren();
  el('result').textContent='No completed evidence for this request.';
}
function reportError(message) { clearResult(); el('status').dataset.state='error'; el('status').textContent=message; }
function runtimeText(h) {
  const exact=h?.opencv5_verified===true && h.opencv_distribution==='5.0.0.93' && h.opencv==='5.0.0';
  return `${exact ? 'Exact OpenCV 5 package/core reported' : 'Development or unverified runtime'} · package ${h?.opencv_distribution ?? 'unknown'} · core ${h?.opencv ?? 'unknown'} · source ${h?.source_sha ?? 'unknown'}`;
}
async function fetchJson(path, options={}) {
  const response=await fetch(path,options);
  let data; try { data=await response.json(); } catch { throw new Error(`Server returned a non-JSON response (HTTP ${response.status}).`); }
  if(!response.ok) {
    const detail=typeof data.detail==='string' ? data.detail : 'The server could not process this request.';
    throw new Error(`HTTP ${response.status}: ${detail}`);
  }
  return {data,request_id:response.headers.get('x-labsight-request-id'),server_timing:response.headers.get('server-timing')};
}
async function loadRuntime(signal) {
  try { const r=await fetchJson('/health',{signal}); el('runtime').textContent=runtimeText(r.data); return r.data; }
  catch(error) { if(error.name==='AbortError') throw error; el('runtime').textContent='Runtime unavailable — do not infer OpenCV 5 or cloud evidence.'; return null; }
}
function renderAnalysis(data) {
  if(!Object.hasOwn(LABELS,data.status) || !Array.isArray(data.trace) || !data.trace.length) throw new Error('Server response is missing a supported QC action or trace.');
  el('summary').hidden=false; el('decision').textContent=actionLabel(data.status); el('decision').className=data.status==='accept'?'ok':'warn';
  el('reason').textContent=data.trace[data.trace.length-1].reason || 'Reason not reported';
  el('metrics').replaceChildren(metricGrid(data.metrics)); el('trace').replaceChildren(node('h2','Why this action?'),traceView(data.trace));
  el('status').textContent=`Analysis complete · ${data.trace.length} perception ${data.trace.length===1?'pass':'passes'} · ${data.used_enhancement?'CLAHE used':'no enhancement tool used'}`;
}
function renderSuite(data) {
  if(!Array.isArray(data.scenarios) || data.scenarios.length!==4 || typeof data.all_expectations_met!=='boolean') throw new Error('Server returned an incomplete judge suite.');
  const proved=data.agentic_vision?.opencv_observation_changes_next_action===true && data.agentic_vision?.second_visual_pass===true;
  const passed=data.all_expectations_met && proved;
  el('suite').hidden=false;
  el('status').textContent=`Judge suite: ${passed?'PASS':'FAIL'} · ${data.scenarios.filter(s=>s.passed===true).length}/4 scenario expectations · Agentic Vision ${proved?'demonstrated':'not demonstrated'}`;
  for(const s of data.scenarios) {
    const card=node('article',undefined,'scenario');
    card.append(node('h3',`${s.passed===true?'PASS':'FAIL'} / ${s.label}`,s.passed===true?'ok':'fail'));
    card.append(node('p',`Expected: ${actionLabel(s.expected_first_action)} → ${actionLabel(s.expected_final_action)}`,'note'));
    card.append(node('p',`Observed: ${actionLabel(s.observed_first_action)} → ${actionLabel(s.observed_final_action)}`));
    card.append(traceView(s.trace)); el('suite').append(card);
  }
}
async function run(path, label, options={}) {
  const serial=++requestSerial;
  if(activeController) activeController.abort();
  const controller=new AbortController(); activeController=controller;
  const timer=setTimeout(()=>controller.abort(),30000);
  clearResult(); busy(true); el('status').dataset.state='working'; el('status').textContent=label;
  try {
    const response=await fetchJson(path,{...options,signal:controller.signal});
    const health=response.data.runtime || await loadRuntime(controller.signal);
    if(serial!==requestSerial) return;
    if(response.data.runtime) el('runtime').textContent=runtimeText(health);
    if(path==='/demo/judge') renderSuite(response.data); else renderAnalysis(response.data);
    receipt={schema_version:'1.0',purpose:'image_quality_control_only',diagnostic_claims:false,evidence_scope:'interactive_demo_not_aws_or_submission_evidence',runtime_observation:health,runtime_observation_note:'Health metadata is not independent deployment attestation.',request_id:response.request_id,server_timing:response.server_timing,response:response.data};
    el('result').textContent=JSON.stringify(receipt,null,2); el('status').dataset.state='complete';
  } catch(error) {
    if(serial===requestSerial) reportError(error.name==='AbortError'?'Request timed out or was cancelled. Retry when the server is available.':error.message || 'Network request failed.');
  } finally {
    clearTimeout(timer);
    if(serial===requestSerial) { activeController=null; busy(false); }
  }
}
async function demo(kind) {
  if(!['clean','blurred','uneven','clipped'].includes(kind)) return;
  clearPreview(); preview(`/demo/image/${kind}`,`Synthetic ${kind} capture. Same deterministic source as this demo's analysis.`,'Synthetic microscopy capture for '+kind+' QC demonstration');
  await run(`/demo/analyze/${kind}`,'Analyzing synthetic capture…');
}
async function judgeSuite() { clearPreview(); await run('/demo/judge','Running four deterministic judge scenarios…'); }
async function upload() {
  const file=el('file').files[0];
  if(!file) { reportError('Select a PNG or JPEG image first.'); return; }
  if(file.size>MAX_BYTES) { reportError('Image exceeds the 8 MiB upload limit. Choose a smaller PNG or JPEG.'); return; }
  if(file.size===0 || !['image/png','image/jpeg'].includes(file.type)) { reportError('Choose a non-empty PNG or JPEG image.'); return; }
  clearPreview(); previewUrl=URL.createObjectURL(file); preview(previewUrl,'Selected capture — local browser preview.','Selected microscopy image for capture-quality review');
  clearResult(); busy(true); el('status').textContent='Reading selected image…';
  try {
    const bytes=new Uint8Array(await file.arrayBuffer());
    let binary=''; for(let i=0;i<bytes.length;i+=8192) binary+=String.fromCharCode(...bytes.subarray(i,i+8192));
    await run('/analyze','Analyzing uploaded capture…',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({image_base64:btoa(binary)})});
  } catch(error) { reportError(error.message || 'The selected file could not be read.'); busy(false); }
}
function downloadEvidence() {
  if(!receipt) return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(receipt,null,2)+'\n'],{type:'application/json'}));
  const link=node('a'); link.href=url; link.download='labsight-demo-evidence.json'; document.body.append(link); link.click(); link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
}
document.querySelectorAll('[data-scenario]').forEach(b=>b.addEventListener('click',()=>demo(b.dataset.scenario)));
el('judge').addEventListener('click',judgeSuite); el('upload').addEventListener('click',upload); el('download').addEventListener('click',downloadEvidence);
el('preview').addEventListener('error',()=>{ clearPreview(); });
el('file').addEventListener('change',()=>{ clearResult(); clearPreview(); el('status').textContent='New file selected. Run analysis to create fresh evidence.'; });
window.addEventListener('pagehide',()=>{ if(activeController) activeController.abort(); clearPreview(); });
// A bounded, independent startup health request must not race later analysis metadata.
const bootSerial=requestSerial, bootController=new AbortController();
const bootTimer=setTimeout(()=>bootController.abort(),10000);
fetchJson('/health',{signal:bootController.signal}).then(r=>{if(requestSerial===bootSerial) el('runtime').textContent=runtimeText(r.data);}).catch(()=>{if(requestSerial===bootSerial) el('runtime').textContent='Runtime unavailable — do not infer OpenCV 5 or cloud evidence.';}).finally(()=>clearTimeout(bootTimer));
</script>
</body></html>'''
