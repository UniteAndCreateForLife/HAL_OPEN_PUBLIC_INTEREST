DEMO_HTML = r'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>HAL LabSight — Agentic Microscopy QC</title>
  <style>
    :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
    body { margin:0; background:#070a0d; color:#e9f1f7; }
    main { width:min(1040px, calc(100% - 32px)); margin:32px auto 64px; }
    h1 { font-size:clamp(30px,5vw,54px); margin:0; letter-spacing:-.04em; }
    .sub { color:#a7bac8; max-width:780px; line-height:1.55; }
    .grid { display:grid; grid-template-columns:repeat(auto-fit,minmax(230px,1fr)); gap:12px; margin:24px 0; }
    .card { border:1px solid #24303a; border-radius:14px; padding:18px; background:#0d1318; }
    button,.upload { width:100%; box-sizing:border-box; border:1px solid #354653; border-radius:10px; padding:12px 14px; background:#15232c; color:#f4fbff; cursor:pointer; font-weight:650; }
    button:hover,.upload:hover { background:#1b303d; }
    input[type=file] { margin-top:12px; width:100%; }
    #status { min-height:24px; color:#8bd4ff; font-weight:650; }
    pre { white-space:pre-wrap; overflow-wrap:anywhere; padding:16px; border-radius:12px; background:#050709; border:1px solid #1d2931; min-height:220px; }
    .pill { display:inline-block; padding:5px 9px; border-radius:999px; background:#15232c; color:#a8e1ff; margin:2px 4px 2px 0; font-size:13px; }
  </style>
</head>
<body><main>
  <div class="pill">OpenCV vision</div><div class="pill">Auditable agent loop</div><div class="pill">AWS target</div>
  <h1>HAL LabSight</h1>
  <p class="sub">Microscopy image-quality control where visual evidence changes the next action. LabSight can accept a capture, request focus/exposure recapture, run CLAHE and re-analyze, or escalate to human review. It is QC tooling—not a diagnostic system.</p>
  <section class="grid">
    <div class="card"><strong>Clean sample</strong><p class="sub">Expected: accept.</p><button onclick="demo('clean')">Analyze clean</button></div>
    <div class="card"><strong>Blurred sample</strong><p class="sub">Expected: focus recapture.</p><button onclick="demo('blurred')">Analyze blurred</button></div>
    <div class="card"><strong>Uneven illumination</strong><p class="sub">Expected: CLAHE → second vision pass.</p><button onclick="demo('uneven')">Analyze uneven</button></div>
    <div class="card"><strong>Clipped exposure</strong><p class="sub">Expected: exposure recapture.</p><button onclick="demo('clipped')">Analyze clipped</button></div>
  </section>
  <section class="card">
    <strong>Analyze your own PNG/JPEG</strong>
    <input id="file" type="file" accept="image/png,image/jpeg" />
    <button style="margin-top:12px" onclick="upload()">Analyze uploaded image</button>
  </section>
  <p id="status"></p>
  <pre id="result">Choose a deterministic demo sample or upload an image.</pre>
<script>
const out = document.getElementById('result');
const statusEl = document.getElementById('status');
function show(data) {
  statusEl.textContent = `Decision: ${data.status || data.result?.status || 'unknown'}`;
  out.textContent = JSON.stringify(data, null, 2);
}
async function demo(kind) {
  statusEl.textContent = 'Analyzing…';
  const r = await fetch(`/demo/analyze/${kind}`);
  show(await r.json());
}
async function upload() {
  const f = document.getElementById('file').files[0];
  if (!f) { statusEl.textContent = 'Select an image first.'; return; }
  statusEl.textContent = 'Analyzing…';
  const bytes = new Uint8Array(await f.arrayBuffer());
  let binary = ''; for (const b of bytes) binary += String.fromCharCode(b);
  const r = await fetch('/analyze', {method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({image_base64:btoa(binary)})});
  show(await r.json());
}
</script>
</main></body></html>'''
