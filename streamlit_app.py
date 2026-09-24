import base64
import json
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components

# Configure Streamlit page for full width
st.set_page_config(
    page_title="Murad Face Slapper | Discord Meme & GIF Maker",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom minimal styles to remove extra padding
st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden; }
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    .stApp {
        background-color: #1e1f22;
    }
</style>
""", unsafe_allow_html=True)

# Load assets and encode to base64 for seamless self-contained browser execution
ASSETS_DIR = Path(__file__).parent / "assets"

def get_base64_data_uri(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
        ext = file_path.suffix.lstrip(".").lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        return f"data:{mime};base64,{encoded}"

faces_data = [
    {"id": "murad_wide", "name": "Wide Cam 📸", "src": get_base64_data_uri(ASSETS_DIR / "murad_wide.png")},
    {"id": "murad_scream", "name": "Scream 😱", "src": get_base64_data_uri(ASSETS_DIR / "murad_scream.png")},
    {"id": "murad_purple", "name": "Purple Grin 😈", "src": get_base64_data_uri(ASSETS_DIR / "murad_purple.png")},
    {"id": "murad_pixel", "name": "Pixel Smirk 👾", "src": get_base64_data_uri(ASSETS_DIR / "murad_pixel.png")},
    {"id": "murad_serious", "name": "Serious 🤨", "src": get_base64_data_uri(ASSETS_DIR / "murad_serious.png")},
    {"id": "murad_laser", "name": "Laser Scream ⚡", "src": get_base64_data_uri(ASSETS_DIR / "murad_laser.png")},
]

# Read local gifshot library
with open(ASSETS_DIR / "gifshot.min.js", "r", encoding="utf-8") as f:
    gifshot_script = f.read()

faces_json = json.dumps(faces_data)

# Embed Interactive HTML5 Canvas Application with Real-Time Mouse Dragging
html_app = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {{
    --bg-dark: #1e1f22;
    --bg-card: #2b2d31;
    --bg-sidebar: #232428;
    --bg-input: #111214;
    --border: rgba(255, 255, 255, 0.08);
    --blurple: #5865F2;
    --blurple-hover: #4752C4;
    --text-main: #f2f3f5;
    --text-muted: #949ba4;
    --green: #23a55a;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg-dark);
    color: var(--text-main);
    overflow-x: hidden;
    padding: 10px;
  }}
  .app-container {{
    display: grid;
    grid-template-columns: 340px 1fr;
    gap: 16px;
    max-width: 1400px;
    margin: 0 auto;
  }}
  @media (max-width: 900px) {{
    .app-container {{ grid-template-columns: 1fr; }}
  }}
  .card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    margin-bottom: 12px;
  }}
  .card-title {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    font-weight: 700;
    margin-bottom: 4px;
  }}
  .step-badge {{
    width: 20px;
    height: 20px;
    background: var(--blurple);
    color: #fff;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 11px;
    font-weight: 700;
  }}
  .hint {{ font-size: 11px; color: var(--text-muted); margin-bottom: 8px; }}
  .btn-upload {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    background: var(--blurple);
    color: #fff;
    border-radius: 6px;
    padding: 10px;
    font-weight: 700;
    font-size: 12px;
    cursor: pointer;
    text-align: center;
    transition: background 0.15s ease;
  }}
  .btn-upload:hover {{ background: var(--blurple-hover); }}
  .btn-upload input {{ display: none; }}
  .presets-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 8px;
  }}
  .preset-btn {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 11px;
    cursor: pointer;
  }}
  .preset-btn.active {{
    background: var(--blurple);
    color: #fff;
    border-color: var(--blurple);
  }}
  .faces-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }}
  .face-btn {{
    background: var(--bg-input);
    border: 2px solid transparent;
    border-radius: 8px;
    padding: 4px;
    cursor: pointer;
    text-align: center;
    transition: all 0.15s ease;
  }}
  .face-btn:hover {{ border-color: rgba(88,101,242,0.5); }}
  .face-btn.active {{
    border-color: var(--blurple);
    background: rgba(88,101,242,0.2);
  }}
  .face-btn img {{
    width: 54px;
    height: 54px;
    border-radius: 50%;
    object-fit: cover;
    display: block;
    margin: 0 auto 4px;
  }}
  .face-btn span {{
    font-size: 10px;
    font-weight: 600;
    display: block;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .row-flex {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 8px;
  }}
  .btn-group {{
    display: flex;
    background: var(--bg-input);
    padding: 2px;
    border-radius: 6px;
    gap: 2px;
  }}
  .btn-toggle {{
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 600;
    padding: 4px 8px;
    border-radius: 4px;
    cursor: pointer;
  }}
  .btn-toggle.active {{
    background: var(--blurple);
    color: #fff;
  }}
  .slider-control {{ margin-bottom: 8px; }}
  .slider-control label {{
    display: flex;
    justify-content: space-between;
    font-size: 11px;
    color: var(--text-muted);
    margin-bottom: 3px;
  }}
  .slider-control input[type="range"] {{
    width: 100%;
    accent-color: var(--blurple);
    cursor: pointer;
  }}
  .anim-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
  }}
  .anim-btn {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 6px 2px;
    cursor: pointer;
    color: var(--text-main);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    font-size: 10px;
    font-weight: 600;
  }}
  .anim-btn.active {{
    background: rgba(88,101,242,0.25);
    border-color: var(--blurple);
  }}
  .canvas-stage {{
    display: flex;
    flex-direction: column;
    align-items: center;
  }}
  .canvas-header {{
    width: 100%;
    max-width: 480px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }}
  .drag-badge {{
    background: rgba(35,165,90,0.15);
    color: #57f287;
    font-size: 11px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 9999px;
  }}
  .canvas-box {{
    width: 100%;
    max-width: 480px;
    aspect-ratio: 1;
    background: #111214;
    border: 2px solid rgba(88,101,242,0.4);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    touch-action: none;
  }}
  #mainCanvas {{
    width: 100%;
    height: 100%;
    display: block;
    cursor: grab;
  }}
  #mainCanvas:active {{
    cursor: grabbing;
  }}
  .action-row {{
    width: 100%;
    max-width: 480px;
    display: flex;
    gap: 8px;
    margin-top: 12px;
  }}
  .btn-action-primary {{
    flex: 2;
    background: var(--blurple);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 12px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
  }}
  .btn-action-primary:hover {{ background: var(--blurple-hover); }}
  .btn-action-secondary {{
    flex: 1;
    background: var(--bg-card);
    color: var(--text-main);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 12px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }}
  .btn-action-secondary:hover {{ background: #35373c; }}
  .caption-input {{
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 8px 10px;
    color: #fff;
    font-size: 12px;
    margin-top: 6px;
    outline: none;
  }}
  .caption-input:focus {{ border-color: var(--blurple); }}
  .progress-wrap {{
    width: 100%;
    max-width: 480px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
    margin-top: 10px;
    display: none;
  }}
  .progress-track {{
    height: 8px;
    background: var(--bg-input);
    border-radius: 4px;
    overflow: hidden;
  }}
  .progress-bar {{
    height: 100%;
    background: var(--blurple);
    width: 0%;
    transition: width 0.1s linear;
  }}
  .progress-text {{
    font-size: 11px;
    color: var(--text-muted);
    text-align: center;
    margin-top: 6px;
  }}
  .discord-mockup {{
    width: 100%;
    max-width: 480px;
    background: #313338;
    border: 1px solid #232428;
    border-radius: 8px;
    padding: 12px;
    margin-top: 14px;
    display: flex;
    gap: 10px;
  }}
  .mockup-avatar {{
    width: 36px;
    height: 36px;
    border-radius: 50%;
    object-fit: cover;
  }}
</style>
<script>
{gifshot_script}
</script>
</head>
<body>

<div class="app-container">
  <!-- Controls Column -->
  <div class="sidebar-col">
    
    <!-- 1. Background -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">1</span>
        <span>Background Image / Meme</span>
      </div>
      <div class="hint">Upload any image or choose a preset body:</div>
      <label class="btn-upload">
        <span>📁 Upload Any Picture / Meme</span>
        <input type="file" id="bgFileInput" accept="image/*">
      </label>
      <div class="presets-row" id="bgPresetsRow">
        <button class="preset-btn active" data-bg="suit">🤵 Suit</button>
        <button class="preset-btn" data-bg="gigachad">🗿 Chad</button>
        <button class="preset-btn" data-bg="astronaut">🚀 Space</button>
        <button class="preset-btn" data-bg="doge">🐕 Doge</button>
        <button class="preset-btn" data-bg="buff">💪 Buff</button>
      </div>
    </div>

    <!-- 2. Choose Murad's Face -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">2</span>
        <span>Choose Murad's Face</span>
      </div>
      <div class="hint">Click a face to place it on the image:</div>
      <div class="faces-grid" id="facesGrid"></div>
      
      <div class="row-flex">
        <span style="font-size: 11px; color: var(--text-muted);">Cutout Mask:</span>
        <div class="btn-group" id="maskGroup">
          <button class="btn-toggle active" data-mask="circle">Circle</button>
          <button class="btn-toggle" data-mask="oval">Oval Face</button>
          <button class="btn-toggle" data-mask="square">Square</button>
        </div>
      </div>
    </div>

    <!-- 3. Face Sliders -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">3</span>
        <span>Face Sizing & Rotation</span>
      </div>
      <div class="slider-control">
        <label>Size: <span id="sizeVal">100%</span></label>
        <input type="range" id="faceScale" min="0.3" max="2.5" step="0.05" value="1.0">
      </div>
      <div class="slider-control">
        <label>Rotation: <span id="rotVal">0°</span></label>
        <input type="range" id="faceRot" min="-180" max="180" step="5" value="0">
      </div>
      <button class="preset-btn" id="recenterBtn" style="width: 100%; padding: 6px; font-weight: 600;">↺ Re-center Face</button>
    </div>

    <!-- 4. Discord Animation -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">4</span>
        <span>Discord GIF Animation</span>
      </div>
      <div class="anim-grid" id="animGrid">
        <button class="anim-btn active" data-anim="none"><span>🖼️</span><span>Still</span></button>
        <button class="anim-btn" data-anim="bob"><span>🕺</span><span>Head Bob</span></button>
        <button class="anim-btn" data-anim="shake"><span>💢</span><span>Shake</span></button>
        <button class="anim-btn" data-anim="spin"><span>🌀</span><span>Speen</span></button>
        <button class="anim-btn" data-anim="petpet"><span>👋</span><span>Petpet</span></button>
        <button class="anim-btn" data-anim="zoom"><span>💥</span><span>Zoom</span></button>
      </div>
      <input type="text" id="memeCaption" class="caption-input" placeholder="Top caption (e.g. WHEN MURAD...)" maxlength="45">
    </div>

  </div>

  <!-- Stage Column -->
  <div class="canvas-stage">
    <div class="canvas-header">
      <div class="drag-badge">🖱️ CLICK & DRAG MURAD'S FACE WITH MOUSE!</div>
      <span style="font-size: 11px; color: var(--text-muted);">Live 60 FPS</span>
    </div>

    <div class="canvas-box" id="canvasBox">
      <canvas id="mainCanvas" width="440" height="440"></canvas>
    </div>

    <div class="action-row">
      <button id="downloadGifBtn" class="btn-action-primary">⬇️ Download for Discord (.GIF)</button>
      <button id="downloadPngBtn" class="btn-action-secondary">Download .PNG</button>
    </div>

    <!-- Progress bar -->
    <div class="progress-wrap" id="progressWrap">
      <div class="progress-track"><div class="progress-bar" id="progressBar"></div></div>
      <div class="progress-text" id="progressText">Encoding Discord GIF...</div>
    </div>

    <!-- Discord Preview -->
    <div class="discord-mockup">
      <img src="" id="discordAvatar" class="mockup-avatar">
      <div>
        <div style="display:flex; align-items:baseline; gap:6px; margin-bottom:2px;">
          <strong style="font-size:13px; color:#fff;">Murad</strong>
          <span style="background:#5865F2; font-size:9px; font-weight:700; padding:1px 4px; border-radius:3px; color:#fff;">APP</span>
          <span style="font-size:10px; color:#949ba4;">Today at 10:30 PM</span>
        </div>
        <div style="font-size:12px; color:#dbdee1;" id="discordMsgText">Check out this new meme sticker! 💀</div>
      </div>
    </div>

  </div>
</div>

<script>
const faces = {faces_json};
const state = {{
  activeFaceIndex: 0,
  bgType: 'preset',
  presetBg: 'suit',
  customBgImg: null,
  faceX: 0,
  faceY: -20,
  faceScale: 1.0,
  faceRot: 0,
  mask: 'circle',
  anim: 'none',
  caption: '',
  frame: 0,
  totalFrames: 12,
  fps: 12,
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0,
  initialFaceX: 0,
  initialFaceY: 0
}};

// Preload face images
const loadedFaces = [];
faces.forEach((f, idx) => {{
  const img = new Image();
  img.src = f.src;
  loadedFaces.push(img);
}});

const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');

function init() {{
  buildFacesUI();
  setupEvents();
  setupDragging();
  startAnim();
  draw();
}}

function buildFacesUI() {{
  const container = document.getElementById('facesGrid');
  faces.forEach((f, idx) => {{
    const btn = document.createElement('div');
    btn.className = 'face-btn' + (idx === 0 ? ' active' : '');
    btn.innerHTML = `<img src="${{f.src}}"><span>${{f.name}}</span>`;
    btn.onclick = () => {{
      state.activeFaceIndex = idx;
      document.querySelectorAll('.face-btn').forEach((b, i) => b.classList.toggle('active', i === idx));
      document.getElementById('discordAvatar').src = f.src;
      draw();
    }};
    container.appendChild(btn);
  }});
  document.getElementById('discordAvatar').src = faces[0].src;
}}

function setupEvents() {{
  // Background presets
  document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.bgType = 'preset';
      state.presetBg = btn.dataset.bg;
      state.customBgImg = null;
      draw();
    }};
  }});

  // Background file upload
  document.getElementById('bgFileInput').onchange = (e) => {{
    if (e.target.files && e.target.files[0]) {{
      const reader = new FileReader();
      reader.onload = (evt) => {{
        const img = new Image();
        img.onload = () => {{
          state.customBgImg = img;
          state.bgType = 'custom';
          document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(b => b.classList.remove('active'));
          draw();
        }};
        img.src = evt.target.result;
      }};
      reader.readAsDataURL(e.target.files[0]);
    }}
  }};

  // Cutout mask
  document.querySelectorAll('#maskGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.mask = btn.dataset.mask;
      draw();
    }};
  }});

  // Sliders
  document.getElementById('faceScale').oninput = (e) => {{
    state.faceScale = parseFloat(e.target.value);
    document.getElementById('sizeVal').innerText = Math.round(state.faceScale * 100) + '%';
    draw();
  }};

  document.getElementById('faceRot').oninput = (e) => {{
    state.faceRot = parseInt(e.target.value);
    document.getElementById('rotVal').innerText = state.faceRot + '°';
    draw();
  }};

  document.getElementById('recenterBtn').onclick = () => {{
    state.faceX = 0;
    state.faceY = -20;
    state.faceRot = 0;
    state.faceScale = 1.0;
    document.getElementById('faceScale').value = 1.0;
    document.getElementById('faceRot').value = 0;
    document.getElementById('sizeVal').innerText = '100%';
    document.getElementById('rotVal').innerText = '0°';
    draw();
  }};

  // Animations
  document.querySelectorAll('#animGrid .anim-btn').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#animGrid .anim-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.anim = btn.dataset.anim;
      state.frame = 0;
      state.totalFrames = state.anim === 'none' ? 1 : (state.anim === 'petpet' ? 8 : 12);
      state.fps = state.anim === 'petpet' ? 14 : 12;
      draw();
    }};
  }});

  // Caption
  document.getElementById('memeCaption').oninput = (e) => {{
    state.caption = e.target.value;
    document.getElementById('discordMsgText').innerText = state.caption || 'Look at this new meme sticker! 💀';
    draw();
  }};

  // Downloads
  document.getElementById('downloadPngBtn').onclick = downloadPng;
  document.getElementById('downloadGifBtn').onclick = exportGif;
}}

// REAL-TIME MOUSE DRAG & DROP FOR MURAD'S FACE
function setupDragging() {{
  function getCanvasPos(e) {{
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {{
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY
    }};
  }}

  function onPointerDown(e) {{
    const pos = getCanvasPos(e);
    state.isDragging = true;
    state.dragStartX = pos.x;
    state.dragStartY = pos.y;
    state.initialFaceX = state.faceX;
    state.initialFaceY = state.faceY;
  }}

  function onPointerMove(e) {{
    if (!state.isDragging) return;
    if (e.cancelable) e.preventDefault();
    const pos = getCanvasPos(e);
    const dx = pos.x - state.dragStartX;
    const dy = pos.y - state.dragStartY;
    state.faceX = Math.round(state.initialFaceX + dx);
    state.faceY = Math.round(state.initialFaceY + dy);
    draw();
  }}

  function onPointerUp() {{
    state.isDragging = false;
  }}

  canvas.addEventListener('mousedown', onPointerDown);
  window.addEventListener('mousemove', onPointerMove);
  window.addEventListener('mouseup', onPointerUp);

  canvas.addEventListener('touchstart', onPointerDown, {{ passive: false }});
  window.addEventListener('touchmove', onPointerMove, {{ passive: false }});
  window.addEventListener('touchend', onPointerUp);
}}

function drawBackground(tCtx, w, h) {{
  if (state.bgType === 'custom' && state.customBgImg) {{
    const img = state.customBgImg;
    const scale = Math.max(w / img.width, h / img.height);
    const dw = img.width * scale;
    const dh = img.height * scale;
    tCtx.drawImage(img, (w - dw)/2, (h - dh)/2, dw, dh);
    return;
  }}

  const id = state.presetBg;
  tCtx.fillStyle = '#1e293b';
  tCtx.fillRect(0, 0, w, h);

  if (id === 'suit') {{
    tCtx.fillStyle = '#0f172a';
    tCtx.beginPath();
    tCtx.moveTo(w*0.1, h); tCtx.lineTo(w*0.2, h*0.55); tCtx.lineTo(w*0.35, h*0.52);
    tCtx.lineTo(w*0.5, h*0.75); tCtx.lineTo(w*0.65, h*0.52); tCtx.lineTo(w*0.8, h*0.55);
    tCtx.lineTo(w*0.9, h); tCtx.closePath(); tCtx.fill();
    tCtx.fillStyle = '#ffffff';
    tCtx.beginPath(); tCtx.moveTo(w*0.35, h*0.52); tCtx.lineTo(w*0.5, h*0.82); tCtx.lineTo(w*0.65, h*0.52); tCtx.fill();
    tCtx.fillStyle = '#dc2626';
    tCtx.beginPath(); tCtx.moveTo(w*0.46, h*0.54); tCtx.lineTo(w*0.54, h*0.54); tCtx.lineTo(w*0.56, h*0.62);
    tCtx.lineTo(w*0.58, h*0.92); tCtx.lineTo(w*0.5, h*0.98); tCtx.lineTo(w*0.42, h*0.92); tCtx.lineTo(w*0.44, h*0.62); tCtx.fill();
  }} else if (id === 'gigachad') {{
    tCtx.fillStyle = '#374151'; tCtx.fillRect(0, 0, w, h);
    tCtx.fillStyle = '#b45309';
    tCtx.beginPath(); tCtx.moveTo(w*0.3, h*0.45); tCtx.lineTo(w*0.15, h); tCtx.lineTo(w*0.85, h); tCtx.lineTo(w*0.7, h*0.45); tCtx.fill();
    tCtx.strokeStyle = '#78350f'; tCtx.lineWidth = 6;
    tCtx.beginPath(); tCtx.arc(w*0.38, h*0.72, w*0.14, 0.2, Math.PI*0.9); tCtx.stroke();
    tCtx.beginPath(); tCtx.arc(w*0.62, h*0.72, w*0.14, 0.1, Math.PI*0.8); tCtx.stroke();
  }} else if (id === 'astronaut') {{
    tCtx.fillStyle = '#090d16'; tCtx.fillRect(0, 0, w, h);
    tCtx.fillStyle = '#fff';
    for (let i=0; i<30; i++) tCtx.fillRect((i*47)%w, (i*73)%h, 2, 2);
    tCtx.fillStyle = '#cbd5e1'; tCtx.beginPath(); tCtx.ellipse(w*0.5, h*0.42, w*0.35, h*0.35, 0, 0, Math.PI*2); tCtx.fill();
    tCtx.fillStyle = '#0f172a'; tCtx.beginPath(); tCtx.ellipse(w*0.5, h*0.42, w*0.3, h*0.3, 0, 0, Math.PI*2); tCtx.fill();
    tCtx.fillStyle = '#f8fafc'; tCtx.beginPath(); tCtx.moveTo(0, h); tCtx.lineTo(w*0.15, h*0.68); tCtx.lineTo(w*0.85, h*0.68); tCtx.lineTo(w, h); tCtx.fill();
  }} else if (id === 'doge') {{
    tCtx.fillStyle = '#fef3c7'; tCtx.fillRect(0, 0, w, h);
    tCtx.fillStyle = '#d97706'; tCtx.beginPath(); tCtx.arc(w*0.5, h*0.85, w*0.35, 0, Math.PI*2); tCtx.fill();
    tCtx.fillStyle = '#fffbeb'; tCtx.beginPath(); tCtx.ellipse(w*0.5, h*0.8, w*0.18, h*0.25, 0, 0, Math.PI*2); tCtx.fill();
  }} else if (id === 'buff') {{
    tCtx.fillStyle = '#18181b'; tCtx.fillRect(0, 0, w, h);
    tCtx.fillStyle = '#f59e0b'; tCtx.beginPath(); tCtx.moveTo(w*0.25, h*0.5); tCtx.lineTo(w*0.05, h*0.65); tCtx.lineTo(w*0.1, h); tCtx.lineTo(w*0.9, h); tCtx.lineTo(w*0.95, h*0.65); tCtx.lineTo(w*0.75, h*0.5); tCtx.fill();
    tCtx.fillStyle = '#dc2626'; tCtx.beginPath(); tCtx.moveTo(w*0.35, h*0.65); tCtx.lineTo(w*0.3, h); tCtx.lineTo(w*0.7, h); tCtx.lineTo(w*0.65, h*0.65); tCtx.fill();
  }}
}}

function render(tCtx, w, h, frameIdx) {{
  tCtx.clearRect(0, 0, w, h);
  drawBackground(tCtx, w, h);

  // Animation values
  let ax = 0, ay = 0, as = 1.0, ar = 0;
  const progress = (frameIdx / state.totalFrames) * Math.PI * 2;
  if (state.anim === 'bob') {{
    ay = Math.sin(progress) * 14;
    ar = Math.cos(progress) * 0.08;
  }} else if (state.anim === 'shake') {{
    ax = (Math.random() - 0.5) * 12;
    ay = (Math.random() - 0.5) * 12;
  }} else if (state.anim === 'spin') {{
    ar = (frameIdx / state.totalFrames) * Math.PI * 2;
  }} else if (state.anim === 'zoom') {{
    as = 1 + Math.sin(progress) * 0.18;
  }} else if (state.anim === 'petpet') {{
    const squish = Math.sin((frameIdx % 5) / 5 * Math.PI);
    as = 1 - squish * 0.2;
    ay = squish * 12;
  }}

  // Draw Face
  const faceImg = loadedFaces[state.activeFaceIndex];
  if (faceImg && faceImg.complete) {{
    tCtx.save();
    const cx = w/2 + state.faceX + ax;
    const cy = h/2 + state.faceY + ay;
    tCtx.translate(cx, cy);
    tCtx.rotate((state.faceRot * Math.PI / 180) + ar);
    tCtx.scale(state.faceScale * as, state.faceScale * as);

    const fSize = w * 0.45;
    tCtx.beginPath();
    if (state.mask === 'circle') {{
      tCtx.arc(0, 0, fSize/2, 0, Math.PI*2);
    }} else if (state.mask === 'oval') {{
      tCtx.ellipse(0, 0, fSize*0.42, fSize*0.55, 0, 0, Math.PI*2);
    }} else {{
      tCtx.rect(-fSize/2, -fSize/2, fSize, fSize);
    }}
    tCtx.clip();

    const aspect = faceImg.width / faceImg.height;
    let fw = fSize, fh = fSize;
    if (aspect > 1) fw = fSize * aspect;
    else fh = fSize / aspect;
    tCtx.drawImage(faceImg, -fw/2, -fh/2, fw, fh);
    tCtx.restore();

    // Subtle drag indicator ring
    tCtx.save();
    tCtx.translate(cx, cy);
    tCtx.rotate((state.faceRot * Math.PI / 180) + ar);
    tCtx.scale(state.faceScale * as, state.faceScale * as);
    tCtx.strokeStyle = state.isDragging ? '#5865F2' : 'rgba(255, 255, 255, 0.4)';
    tCtx.lineWidth = state.isDragging ? 4 : 2;
    tCtx.beginPath();
    if (state.mask === 'circle') tCtx.arc(0, 0, fSize/2, 0, Math.PI*2);
    else if (state.mask === 'oval') tCtx.ellipse(0, 0, fSize*0.42, fSize*0.55, 0, 0, Math.PI*2);
    else tCtx.rect(-fSize/2, -fSize/2, fSize, fSize);
    tCtx.stroke();
    tCtx.restore();
  }}

  // Petpet Hand
  if (state.anim === 'petpet') {{
    const squish = Math.sin((frameIdx % 5) / 5 * Math.PI);
    const handY = h * 0.2 + squish * (h * 0.12);
    const handX = w * 0.5;
    tCtx.save();
    tCtx.translate(handX, handY);
    tCtx.fillStyle = '#fff4e6';
    tCtx.strokeStyle = '#1e1f22';
    tCtx.lineWidth = 4;
    tCtx.beginPath();
    tCtx.moveTo(-40, -10);
    tCtx.bezierCurveTo(-45, 12, -40, 28, -25, 32);
    tCtx.bezierCurveTo(-15, 36, 0, 38, 15, 32);
    tCtx.bezierCurveTo(28, 26, 32, 12, 25, -5);
    tCtx.closePath(); tCtx.fill(); tCtx.stroke();
    tCtx.fillStyle = '#5865F2';
    tCtx.beginPath();
    tCtx.moveTo(-50, -40); tCtx.lineTo(25, -30); tCtx.lineTo(20, -5); tCtx.lineTo(-45, -10);
    tCtx.closePath(); tCtx.fill(); tCtx.stroke();
    tCtx.restore();
  }}

  // Caption text
  if (state.caption && state.caption.trim()) {{
    tCtx.save();
    tCtx.font = `900 ${{Math.max(16, Math.floor(w*0.08))}}px Impact, sans-serif`;
    tCtx.textAlign = 'center';
    tCtx.textBaseline = 'top';
    tCtx.fillStyle = '#ffffff';
    tCtx.strokeStyle = '#000000';
    tCtx.lineWidth = Math.max(4, Math.floor(w*0.02));
    const txt = state.caption.toUpperCase();
    tCtx.strokeText(txt, w/2, 12, w-16);
    tCtx.fillText(txt, w/2, 12, w-16);
    tCtx.restore();
  }}
}}

function draw() {{
  render(ctx, canvas.width, canvas.height, state.frame);
}}

function startAnim() {{
  setInterval(() => {{
    if (state.anim !== 'none') {{
      state.frame = (state.frame + 1) % state.totalFrames;
      draw();
    }}
  }}, Math.round(1000 / state.fps));
}}

function downloadPng() {{
  const link = document.createElement('a');
  link.download = 'murad_meme.png';
  link.href = canvas.toDataURL('image/png');
  link.click();
}}

function exportGif() {{
  if (state.anim === 'none') {{
    downloadPng();
    return;
  }}
  const wrap = document.getElementById('progressWrap');
  const bar = document.getElementById('progressBar');
  const txt = document.getElementById('progressText');
  wrap.style.display = 'block';
  bar.style.width = '10%';
  txt.innerText = 'Capturing GIF frames...';

  const exportSize = 256;
  const offscreen = document.createElement('canvas');
  offscreen.width = exportSize;
  offscreen.height = exportSize;
  const offCtx = offscreen.getContext('2d');

  const frames = [];
  for (let i = 0; i < state.totalFrames; i++) {{
    render(offCtx, exportSize, exportSize, i);
    frames.push(offscreen.toDataURL('image/png'));
  }}

  bar.style.width = '40%';
  txt.innerText = 'Encoding Discord GIF...';

  if (window.gifshot) {{
    window.gifshot.createGIF({{
      images: frames,
      gifWidth: exportSize,
      gifHeight: exportSize,
      interval: 1 / state.fps,
      numFrames: state.totalFrames,
      sampleInterval: 8,
      numWorkers: 2,
      progressCallback: (p) => {{
        const pct = Math.round(40 + p * 55);
        bar.style.width = pct + '%';
        txt.innerText = `Encoding: ${{pct}}%...`;
      }}
    }}, (obj) => {{
      bar.style.width = '100%';
      txt.innerText = 'Ready!';
      if (!obj.error) {{
        const link = document.createElement('a');
        link.download = `murad_${{state.anim}}_meme.gif`;
        link.href = obj.image;
        link.click();
        setTimeout(() => {{ wrap.style.display = 'none'; }}, 2000);
      }} else {{
        alert('GIF error: ' + obj.errorMsg);
        wrap.style.display = 'none';
      }}
    }});
  }}
}}

window.onload = init;
</script>
</body>
</html>
"""

components.html(html_app, height=880, scrolling=True)
