import base64
import json
import urllib.request
import urllib.error
import re
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
        padding-top: 0.5rem;
        padding-bottom: 1rem;
        padding-left: 1rem;
        padding-right: 1rem;
        max-width: 100%;
    }
    .stApp {
        background-color: #1e1f22;
    }
    .admin-box {
        background-color: #2b2d31;
        border: 1px solid rgba(88, 101, 242, 0.3);
        border-radius: 10px;
        padding: 16px;
        margin-top: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Assets directory
ASSETS_DIR = Path(__file__).parent / "assets"
MANIFEST_FILE = ASSETS_DIR / "manifest.json"

# Helper: encode file to base64
def get_base64_data_uri(file_path: Path) -> str:
    with open(file_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
        ext = file_path.suffix.lstrip(".").lower()
        if ext == "png":
            mime = "image/png"
        elif ext == "webp":
            mime = "image/webp"
        else:
            mime = "image/jpeg"
        return f"data:{mime};base64,{encoded}"

# Helper: load faces dynamically from manifest
def load_faces_catalog():
    faces_list = []
    if MANIFEST_FILE.exists():
        try:
            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                manifest_items = json.load(f)
                for item in manifest_items:
                    img_path = ASSETS_DIR / item["file"]
                    if img_path.exists():
                        faces_list.append({
                            "id": item["id"],
                            "name": item["name"],
                            "src": get_base64_data_uri(img_path)
                        })
        except Exception:
            pass

    # Fallback to scan directory if manifest missing
    if not faces_list:
        for p in ASSETS_DIR.glob("*.png"):
            faces_list.append({
                "id": p.stem,
                "name": p.stem.replace("murad_", "").replace("_", " ").title() + " 📸",
                "src": get_base64_data_uri(p)
            })

    return faces_list

# Templates directory & catalog
TEMPLATES_DIR = ASSETS_DIR / "templates"

def load_templates_catalog():
    tpl_defs = [
        {"id": "suit", "name": "🤵 Fancy Tux", "file": "tux.jpg"},
        {"id": "gigachad", "name": "🗿 Gigachad", "file": "gigachad.webp"},
        {"id": "throne", "name": "👑 King Throne", "file": "king_throne.jpg"},
        {"id": "astronaut", "name": "🚀 Space", "file": "space.jpg"},
        {"id": "doge", "name": "🐕 Doge", "file": "dog.jpg"},
    ]
    tpl_list = []
    for item in tpl_defs:
        p = TEMPLATES_DIR / item["file"]
        if p.exists():
            tpl_list.append({
                "id": item["id"],
                "name": item["name"],
                "src": get_base64_data_uri(p)
            })
    return tpl_list

# Helper: GitHub Contents API to commit without browser login
def push_file_to_github(repo_owner: str, repo_name: str, file_path: str, content_bytes: bytes, commit_message: str, token: str) -> tuple[bool, str]:
    clean_token = token.strip()
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "MuradMemeAdmin",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Check if file exists to fetch sha
    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pass  # New file, sha not required
        elif e.code in (401, 403):
            err_body = e.read().decode("utf-8", errors="replace")
            try:
                msg = json.loads(err_body).get("message", err_body)
            except Exception:
                msg = err_body
            return False, f"HTTP {e.code}: {msg}"
    except Exception as e:
        pass

    payload = {
        "message": commit_message,
        "content": base64.b64encode(content_bytes).decode("utf-8")
    }
    if sha:
        payload["sha"] = sha

    put_req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="PUT"
    )
    try:
        with urllib.request.urlopen(put_req) as resp:
            if resp.status in (200, 201):
                return True, ""
            return False, f"Unexpected response HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(err_body).get("message", err_body)
        except Exception:
            msg = err_body
        return False, f"HTTP {e.code}: {msg}"
    except Exception as e:
        return False, f"Network error: {str(e)}"

# Read local libraries
with open(ASSETS_DIR / "gifshot.min.js", "r", encoding="utf-8") as f:
    gifshot_script = f.read()

gifuct_script = ""
gifuct_path = ASSETS_DIR / "gifuct-js.js"
if gifuct_path.exists():
    with open(gifuct_path, "r", encoding="utf-8") as f:
        gifuct_script = f.read()

faces_data = load_faces_catalog()
faces_json = json.dumps(faces_data)

templates_data = load_templates_catalog()
templates_json = json.dumps(templates_data)

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
    padding: 8px 12px;
  }}
  .app-container {{
    display: grid;
    grid-template-columns: 360px 1fr;
    gap: 16px;
    max-width: 1300px;
    margin: 0 auto;
  }}
  @media (max-width: 920px) {{
    .app-container {{ grid-template-columns: 1fr; }}
  }}
  .card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 12px 14px;
    margin-bottom: 10px;
  }}
  .card-title {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
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
    padding: 9px;
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
    transition: all 0.15s ease;
  }}
  .preset-btn:hover {{ border-color: var(--blurple); }}
  .preset-btn.active {{
    background: var(--blurple);
    color: #fff;
    border-color: var(--blurple);
  }}
  .faces-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    max-height: 230px;
    overflow-y: auto;
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
    background: rgba(88,101,242,0.25);
    box-shadow: 0 0 10px rgba(88,101,242,0.4);
  }}
  .face-btn img {{
    width: 52px;
    height: 52px;
    border-radius: 50%;
    object-fit: cover;
    display: block;
    margin: 0 auto 3px;
    border: 2px solid rgba(255,255,255,0.15);
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
  .accessories-row {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .acc-btn {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-muted);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .acc-btn.active {{
    background: rgba(88,101,242,0.25);
    border-color: var(--blurple);
    color: #fff;
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
    max-width: 440px;
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
    border: 1px solid rgba(35,165,90,0.3);
  }}
  .canvas-box {{
    width: 100%;
    max-width: 480px;
    background: #111214;
    border: 2px solid rgba(88,101,242,0.5);
    border-radius: 12px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 10px 36px rgba(0,0,0,0.6);
    touch-action: none;
    display: flex;
    justify-content: center;
    align-items: center;
  }}
  #mainCanvas {{
    max-width: 100%;
    max-height: 520px;
    height: auto;
    display: block;
    cursor: grab;
  }}
  #mainCanvas:active {{
    cursor: grabbing;
  }}
  .quick-tools {{
    display: flex;
    gap: 6px;
    margin-top: 8px;
    width: 100%;
    max-width: 440px;
    justify-content: center;
  }}
  .quick-btn {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 11px;
    padding: 5px 10px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
  }}
  .quick-btn:hover {{ color: #fff; border-color: var(--blurple); }}
  .action-row {{
    width: 100%;
    max-width: 440px;
    display: flex;
    gap: 8px;
    margin-top: 10px;
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
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    box-shadow: 0 4px 16px rgba(88,101,242,0.4);
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
    max-width: 440px;
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
    max-width: 440px;
    background: #313338;
    border: 1px solid #232428;
    border-radius: 8px;
    padding: 10px 12px;
    margin-top: 12px;
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
<script>
{gifuct_script}
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
        <span>Background Image / Meme / GIF</span>
      </div>
      <div class="hint">Upload any image/meme/GIF or pick a preset body:</div>
      <label class="btn-upload">
        <span>📁 Upload Picture / Meme / Animated GIF</span>
        <input type="file" id="bgFileInput" accept="image/*,.gif">
      </label>
      <div class="presets-row" id="bgPresetsRow">
        <!-- Dynamically populated from real meme template images -->
      </div>

      <!-- Framing & True Size Mode -->
      <div style="margin-top: 10px; margin-bottom: 6px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <span style="font-size: 11px; color: var(--text-muted); font-weight:600;">Canvas Size & Ratio:</span>
          <span id="canvasDimsBadge" style="font-size: 10px; background: rgba(88,101,242,0.2); color: #5865F2; padding: 1px 6px; border-radius: 8px;">500x500</span>
        </div>
        <div class="btn-group" id="canvasSizeGroup" style="display:flex; gap:3px;">
          <button class="btn-toggle active" data-size="true_size" title="Keep natural true size and aspect ratio of upload">📐 True Size</button>
          <button class="btn-toggle" data-size="square" title="1:1 Square Discord sticker">⏹️ Square</button>
          <button class="btn-toggle" data-size="landscape" title="16:9 Landscape">🖼️ 16:9</button>
          <button class="btn-toggle" data-size="portrait" title="9:16 Portrait">📱 9:16</button>
        </div>
      </div>

      <!-- Crop & Framing Controls -->
      <div style="margin-top: 8px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
          <span style="font-size: 11px; color: var(--text-muted); font-weight:600;">Crop & Fit:</span>
          <button id="resetBgCropBtn" style="font-size: 10px; background: transparent; border: 1px solid var(--border); color: var(--text-muted); padding: 2px 6px; border-radius: 4px; cursor: pointer;">🔄 Reset Crop</button>
        </div>
        <div class="btn-group" id="bgFitGroup" style="display:flex; gap:3px; margin-bottom: 6px;">
          <button class="btn-toggle active" data-fit="cover" title="Fill canvas (auto-crop edges)">✂️ Fill & Crop</button>
          <button class="btn-toggle" data-fit="fit" title="Fit entire image without cropping">🔍 Full Image</button>
        </div>

        <div style="background: rgba(0,0,0,0.25); border-radius: 6px; padding: 8px; border: 1px solid rgba(255,255,255,0.05);">
          <div style="display:flex; justify-content:space-between; font-size:11px; margin-bottom:3px;">
            <span style="color:var(--text-muted);">Background Zoom:</span>
            <span id="bgZoomVal" style="color:#fff; font-weight:600;">100%</span>
          </div>
          <input type="range" id="bgZoomSlider" min="0.4" max="2.5" step="0.05" value="1.0" style="width:100%; margin-bottom:6px;">

          <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 8px;">
            <div>
              <span style="font-size:10px; color:var(--text-muted);">Pan Left / Right:</span>
              <input type="range" id="bgPanXSlider" min="-300" max="300" step="2" value="0" style="width:100%;">
            </div>
            <div>
              <span style="font-size:10px; color:var(--text-muted);">Pan Up / Down:</span>
              <input type="range" id="bgPanYSlider" min="-300" max="300" step="2" value="0" style="width:100%;">
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 2. Choose Murad's Face -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">2</span>
        <span>Choose Murad's Face</span>
      </div>
      <div class="hint">Pick a face to slap on the meme:</div>
      <div class="faces-grid" id="facesGrid"></div>
      
      <div class="row-flex">
        <span style="font-size: 11px; color: var(--text-muted);">Cutout Shape:</span>
        <div class="btn-group" id="maskGroup">
          <button class="btn-toggle active" data-mask="circle">Sticker Circle</button>
          <button class="btn-toggle" data-mask="oval">Oval Face</button>
          <button class="btn-toggle" data-mask="square">Full Frame</button>
        </div>
      </div>
    </div>

    <!-- 3. Meme Accessories -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">3</span>
        <span>Meme Accessories & Stickers</span>
      </div>
      <div class="hint">Toggle funny accessories on Murad's head:</div>
      <div class="accessories-row" id="accRow">
        <button class="acc-btn" data-acc="shades">🕶️ Thug Shades</button>
        <button class="acc-btn" data-acc="laser">🔴 Laser Eyes</button>
        <button class="acc-btn" data-acc="crown">👑 Gold Crown</button>
        <button class="acc-btn" data-acc="bubble">💬 Speech Bubble</button>
      </div>
    </div>

    <!-- 4. Face Sizing & Rotation -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">4</span>
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
    </div>

    <!-- 5. Discord Animation -->
    <div class="card">
      <div class="card-title">
        <span class="step-badge">5</span>
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
      <input type="text" id="memeCaption" class="caption-input" placeholder="Meme caption (e.g. WHEN MURAD...)" maxlength="45">
    </div>

  </div>

  <!-- Stage Column -->
  <div class="canvas-stage">
    <div class="canvas-header">
      <div class="drag-badge">🖱️ CLICK & DRAG MURAD'S FACE WITH MOUSE!</div>
      <span style="font-size: 11px; color: var(--text-muted);">Scroll wheel = Zoom</span>
    </div>

    <div class="canvas-box" id="canvasBox">
      <canvas id="mainCanvas" width="440" height="440"></canvas>
    </div>

    <div class="quick-tools">
      <button class="quick-btn" id="zoomInBtn">🔍 Zoom In (+)</button>
      <button class="quick-btn" id="zoomOutBtn">🔍 Zoom Out (-)</button>
      <button class="quick-btn" id="rotLeftBtn">↺ Rotate Left</button>
      <button class="quick-btn" id="rotRightBtn">↻ Rotate Right</button>
      <button class="quick-btn" id="recenterBtn">🎯 Center Face</button>
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
const templates = {templates_json};
const state = {{
  activeFaceIndex: 0,
  bgType: 'preset',
  presetBg: templates.length > 0 ? templates[0].id : 'suit',
  customBgImg: null,
  canvasSizeRatio: 'true_size',
  bgFitMode: 'cover',
  bgScale: 1.0,
  bgPanX: 0,
  bgPanY: 0,
  isBgGif: false,
  bgGifFrames: [],
  gifBgFrameIndex: 0,
  lastNatW: 500,
  lastNatH: 500,
  faceX: 0,
  faceY: -65,
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
  initialFaceY: 0,
  accShades: false,
  accLaser: false,
  accCrown: false,
  accBubble: false
}};

// Preload face images
const loadedFaces = [];
faces.forEach((f, idx) => {{
  const img = new Image();
  img.src = f.src;
  loadedFaces.push(img);
}});

// Preload template images
const loadedTemplates = {{}};
templates.forEach(t => {{
  const img = new Image();
  img.src = t.src;
  loadedTemplates[t.id] = img;
}});

const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');

function init() {{
  buildTemplatesUI();
  buildFacesUI();
  setupEvents();
  setupDragging();
  startAnim();
  if (templates.length > 0 && loadedTemplates[templates[0].id]) {{
    const firstImg = loadedTemplates[templates[0].id];
    if (firstImg.complete && firstImg.naturalWidth) {{
      updateCanvasDimensions(firstImg.naturalWidth, firstImg.naturalHeight);
    }} else {{
      firstImg.onload = () => updateCanvasDimensions(firstImg.naturalWidth, firstImg.naturalHeight);
    }}
  }} else {{
    updateCanvasDimensions(500, 500);
  }}
  draw();
}}

function updateCanvasDimensions(natW, natH) {{
  if (natW && natH) {{
    state.lastNatW = natW;
    state.lastNatH = natH;
  }}
  const nw = state.lastNatW || 500;
  const nh = state.lastNatH || 500;

  if (state.canvasSizeRatio === 'true_size') {{
    const maxSide = 520;
    const aspect = nw / nh;
    let tw, th;
    if (aspect >= 1) {{
      tw = Math.min(nw, maxSide);
      th = Math.round(tw / aspect);
    }} else {{
      th = Math.min(nh, maxSide);
      tw = Math.round(th * aspect);
    }}
    canvas.width = Math.max(280, tw);
    canvas.height = Math.max(280, th);
  }} else if (state.canvasSizeRatio === 'square') {{
    canvas.width = 500;
    canvas.height = 500;
  }} else if (state.canvasSizeRatio === 'landscape') {{
    canvas.width = 533;
    canvas.height = 300;
  }} else if (state.canvasSizeRatio === 'portrait') {{
    canvas.width = 300;
    canvas.height = 533;
  }}
  const badge = document.getElementById('canvasDimsBadge');
  if (badge) badge.innerText = `${{canvas.width}}x${{canvas.height}}`;
  draw();
}}

function processGifBuffer(buffer) {{
  try {{
    if (!window.GIF) return false;
    const gif = new window.GIF(buffer);
    const rawFrames = gif.decompressFrames(true);
    if (!rawFrames || rawFrames.length === 0) return false;

    const gifW = rawFrames[0].dims.width;
    const gifH = rawFrames[0].dims.height;

    const fullFrames = [];
    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = gifW;
    tempCanvas.height = gifH;
    const tempCtx = tempCanvas.getContext('2d');

    rawFrames.forEach((frame) => {{
      const frameCanvas = document.createElement('canvas');
      frameCanvas.width = gifW;
      frameCanvas.height = gifH;
      const frameCtx = frameCanvas.getContext('2d');

      const patchData = new ImageData(frame.patch, frame.dims.width, frame.dims.height);
      const patchCanvas = document.createElement('canvas');
      patchCanvas.width = frame.dims.width;
      patchCanvas.height = frame.dims.height;
      patchCanvas.getContext('2d').putImageData(patchData, 0, 0);

      frameCtx.drawImage(tempCanvas, 0, 0);
      frameCtx.drawImage(patchCanvas, frame.dims.left, frame.dims.top);

      if (frame.disposalType === 2) {{
        tempCtx.clearRect(0, 0, gifW, gifH);
      }} else {{
        tempCtx.drawImage(frameCanvas, 0, 0);
      }}

      fullFrames.push({{
        canvas: frameCanvas,
        delay: frame.delay || 100
      }});
    }});

    state.isBgGif = true;
    state.bgGifFrames = fullFrames;
    state.gifBgFrameIndex = 0;
    state.bgType = 'custom';
    state.customBgImg = null;

    updateCanvasDimensions(gifW, gifH);
    return true;
  }} catch (err) {{
    console.error('Error parsing GIF:', err);
    return false;
  }}
}}

function buildTemplatesUI() {{
  const container = document.getElementById('bgPresetsRow');
  if (!container) return;
  container.innerHTML = '';
  templates.forEach((t, idx) => {{
    const btn = document.createElement('button');
    btn.className = 'preset-btn' + (idx === 0 ? ' active' : '');
    btn.dataset.bg = t.id;
    btn.innerText = t.name;
    btn.onclick = () => {{
      document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.isBgGif = false;
      state.bgGifFrames = [];
      state.bgType = 'preset';
      state.presetBg = t.id;
      state.customBgImg = null;
      if (t.id === 'suit') {{ state.faceX = 0; state.faceY = -65; state.faceScale = 1.0; }}
      else if (t.id === 'gigachad') {{ state.faceX = 0; state.faceY = -60; state.faceScale = 0.95; }}
      else if (t.id === 'throne') {{ state.faceX = 0; state.faceY = -50; state.faceScale = 0.85; }}
      else if (t.id === 'astronaut') {{ state.faceX = 0; state.faceY = -35; state.faceScale = 0.85; }}
      else if (t.id === 'doge') {{ state.faceX = 0; state.faceY = -35; state.faceScale = 0.9; }}

      const tplImg = loadedTemplates[t.id];
      if (tplImg && tplImg.naturalWidth) {{
        updateCanvasDimensions(tplImg.naturalWidth, tplImg.naturalHeight);
      }} else {{
        updateCanvasDimensions(500, 500);
      }}
      draw();
    }};
    container.appendChild(btn);
  }});
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
  if (faces.length > 0) {{
    document.getElementById('discordAvatar').src = faces[0].src;
  }}
}}

function setupEvents() {{
  document.getElementById('bgFileInput').onchange = (e) => {{
    if (e.target.files && e.target.files[0]) {{
      const file = e.target.files[0];
      const isGif = file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif');

      if (isGif && window.GIF) {{
        const reader = new FileReader();
        reader.onload = (evt) => {{
          const ok = processGifBuffer(evt.target.result);
          if (!ok) {{
            loadAsStaticImage(file);
          }} else {{
            document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(b => b.classList.remove('active'));
            draw();
          }}
        }};
        reader.readAsArrayBuffer(file);
      }} else {{
        loadAsStaticImage(file);
      }}
    }}
  }};

  function loadAsStaticImage(file) {{
    const reader = new FileReader();
    reader.onload = (evt) => {{
      const img = new Image();
      img.onload = () => {{
        state.isBgGif = false;
        state.bgGifFrames = [];
        state.customBgImg = img;
        state.bgType = 'custom';
        document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(b => b.classList.remove('active'));
        updateCanvasDimensions(img.naturalWidth, img.naturalHeight);
        draw();
      }};
      img.src = evt.target.result;
    }};
    reader.readAsDataURL(file);
  }}

  // Canvas size mode buttons (True Size, Square, 16:9, 9:16)
  document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.canvasSizeRatio = btn.dataset.size;
      updateCanvasDimensions();
    }};
  }});

  // Background Fit mode buttons (Cover vs Fit)
  document.querySelectorAll('#bgFitGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#bgFitGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.bgFitMode = btn.dataset.fit;
      draw();
    }};
  }});

  // Background zoom slider
  const bgZoomSlider = document.getElementById('bgZoomSlider');
  if (bgZoomSlider) {{
    bgZoomSlider.oninput = (e) => {{
      state.bgScale = parseFloat(e.target.value);
      document.getElementById('bgZoomVal').innerText = Math.round(state.bgScale * 100) + '%';
      draw();
    }};
  }}

  // Background Pan X and Pan Y sliders
  const bgPanXSlider = document.getElementById('bgPanXSlider');
  if (bgPanXSlider) {{
    bgPanXSlider.oninput = (e) => {{
      state.bgPanX = parseInt(e.target.value);
      draw();
    }};
  }}

  const bgPanYSlider = document.getElementById('bgPanYSlider');
  if (bgPanYSlider) {{
    bgPanYSlider.oninput = (e) => {{
      state.bgPanY = parseInt(e.target.value);
      draw();
    }};
  }}

  // Reset Background Crop button
  const resetBgCropBtn = document.getElementById('resetBgCropBtn');
  if (resetBgCropBtn) {{
    resetBgCropBtn.onclick = () => {{
      state.bgScale = 1.0;
      state.bgPanX = 0;
      state.bgPanY = 0;
      if (bgZoomSlider) bgZoomSlider.value = 1.0;
      if (bgPanXSlider) bgPanXSlider.value = 0;
      if (bgPanYSlider) bgPanYSlider.value = 0;
      document.getElementById('bgZoomVal').innerText = '100%';
      draw();
    }};
  }}

  document.querySelectorAll('#maskGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.mask = btn.dataset.mask;
      draw();
    }};
  }});

  document.querySelectorAll('#accRow .acc-btn').forEach(btn => {{
    btn.onclick = () => {{
      const acc = btn.dataset.acc;
      if (acc === 'shades') state.accShades = !state.accShades;
      else if (acc === 'laser') state.accLaser = !state.accLaser;
      else if (acc === 'crown') state.accCrown = !state.accCrown;
      else if (acc === 'bubble') state.accBubble = !state.accBubble;
      btn.classList.toggle('active');
      draw();
    }};
  }});

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

  document.getElementById('zoomInBtn').onclick = () => {{
    state.faceScale = Math.min(2.5, state.faceScale + 0.15);
    document.getElementById('faceScale').value = state.faceScale;
    document.getElementById('sizeVal').innerText = Math.round(state.faceScale * 100) + '%';
    draw();
  }};

  document.getElementById('zoomOutBtn').onclick = () => {{
    state.faceScale = Math.max(0.3, state.faceScale - 0.15);
    document.getElementById('faceScale').value = state.faceScale;
    document.getElementById('sizeVal').innerText = Math.round(state.faceScale * 100) + '%';
    draw();
  }};

  document.getElementById('rotLeftBtn').onclick = () => {{
    state.faceRot = (state.faceRot - 15) % 360;
    document.getElementById('faceRot').value = state.faceRot;
    document.getElementById('rotVal').innerText = state.faceRot + '°';
    draw();
  }};

  document.getElementById('rotRightBtn').onclick = () => {{
    state.faceRot = (state.faceRot + 15) % 360;
    document.getElementById('faceRot').value = state.faceRot;
    document.getElementById('rotVal').innerText = state.faceRot + '°';
    draw();
  }};

  document.getElementById('recenterBtn').onclick = () => {{
    state.faceX = 0;
    state.faceY = -35;
    state.faceRot = 0;
    state.faceScale = 1.0;
    document.getElementById('faceScale').value = 1.0;
    document.getElementById('faceRot').value = 0;
    document.getElementById('sizeVal').innerText = '100%';
    document.getElementById('rotVal').innerText = '0°';
    draw();
  }};

  canvas.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.05 : -0.05;
    state.faceScale = Math.max(0.3, Math.min(2.5, state.faceScale + delta));
    document.getElementById('faceScale').value = state.faceScale;
    document.getElementById('sizeVal').innerText = Math.round(state.faceScale * 100) + '%';
    draw();
  }}, {{ passive: false }});

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

  document.getElementById('memeCaption').oninput = (e) => {{
    state.caption = e.target.value;
    document.getElementById('discordMsgText').innerText = state.caption || 'Look at this new meme sticker! 💀';
    draw();
  }};

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
    draw();
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
    if (state.isDragging) {{
      state.isDragging = false;
      draw();
    }}
  }}

  canvas.addEventListener('mousedown', onPointerDown);
  window.addEventListener('mousemove', onPointerMove);
  window.addEventListener('mouseup', onPointerUp);

  canvas.addEventListener('touchstart', onPointerDown, {{ passive: false }});
  window.addEventListener('touchmove', onPointerMove, {{ passive: false }});
  window.addEventListener('touchend', onPointerUp);
}}

function drawBackground(tCtx, w, h) {{
  let source = null;
  let srcW = 0, srcH = 0;

  if (state.bgType === 'custom') {{
    if (state.isBgGif && state.bgGifFrames.length > 0) {{
      const frameIdx = state.gifBgFrameIndex % state.bgGifFrames.length;
      source = state.bgGifFrames[frameIdx].canvas;
      srcW = source.width;
      srcH = source.height;
    }} else if (state.customBgImg) {{
      source = state.customBgImg;
      srcW = source.naturalWidth || source.width;
      srcH = source.naturalHeight || source.height;
    }}
  }} else {{
    const tplImg = loadedTemplates[state.presetBg];
    if (tplImg && tplImg.complete && tplImg.naturalWidth > 0) {{
      source = tplImg;
      srcW = tplImg.naturalWidth;
      srcH = tplImg.naturalHeight;
    }}
  }}

  if (!source || !srcW || !srcH) {{
    tCtx.fillStyle = '#1e1f22';
    tCtx.fillRect(0, 0, w, h);
    return;
  }}

  let baseScale = 1;
  if (state.bgFitMode === 'fit') {{
    baseScale = Math.min(w / srcW, h / srcH);
  }} else {{
    baseScale = Math.max(w / srcW, h / srcH);
  }}

  const finalScale = baseScale * state.bgScale;
  const dw = srcW * finalScale;
  const dh = srcH * finalScale;
  const dx = (w - dw) / 2 + state.bgPanX;
  const dy = (h - dh) / 2 + state.bgPanY;

  tCtx.fillStyle = '#111214';
  tCtx.fillRect(0, 0, w, h);
  tCtx.drawImage(source, dx, dy, dw, dh);
}}

function render(tCtx, w, h, frameIdx) {{
  tCtx.clearRect(0, 0, w, h);
  drawBackground(tCtx, w, h);

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

  // Draw Murad's Face
  const faceImg = loadedFaces[state.activeFaceIndex];
  if (faceImg && faceImg.complete) {{
    tCtx.save();
    const cx = w/2 + state.faceX + ax;
    const cy = h/2 + state.faceY + ay;
    tCtx.translate(cx, cy);
    tCtx.rotate((state.faceRot * Math.PI / 180) + ar);
    tCtx.scale(state.faceScale * as, state.faceScale * as);

    const fSize = w * 0.44;

    // Drop Shadow for Sticker Cutout
    if (state.mask !== 'square') {{
      tCtx.shadowColor = 'rgba(0, 0, 0, 0.45)';
      tCtx.shadowBlur = 16;
      tCtx.shadowOffsetX = 0;
      tCtx.shadowOffsetY = 6;
    }}

    tCtx.beginPath();
    if (state.mask === 'circle') {{
      tCtx.arc(0, 0, fSize/2, 0, Math.PI*2);
    }} else if (state.mask === 'oval') {{
      tCtx.ellipse(0, 0, fSize*0.42, fSize*0.55, 0, 0, Math.PI*2);
    }} else {{
      tCtx.rect(-fSize/2, -fSize/2, fSize, fSize);
    }}
    tCtx.save();
    tCtx.clip();

    const aspect = faceImg.width / faceImg.height;
    let fw = fSize, fh = fSize;
    if (aspect > 1) fw = fSize * aspect;
    else fh = fSize / aspect;
    tCtx.drawImage(faceImg, -fw/2, -fh/2, fw, fh);
    tCtx.restore();

    // Clean white sticker border
    if (state.mask !== 'square') {{
      tCtx.strokeStyle = '#ffffff';
      tCtx.lineWidth = 4;
      tCtx.stroke();
    }}

    // Selection ring indicator while dragging
    if (state.isDragging) {{
      tCtx.strokeStyle = '#5865F2';
      tCtx.lineWidth = 3;
      tCtx.stroke();
    }}

    // 1. Thug Shades
    if (state.accShades) {{
      tCtx.fillStyle = '#000000';
      tCtx.fillRect(-fSize*0.35, -fSize*0.12, fSize*0.32, fSize*0.14);
      tCtx.fillRect(fSize*0.03, -fSize*0.12, fSize*0.32, fSize*0.14);
      tCtx.fillRect(-fSize*0.05, -fSize*0.08, fSize*0.1, 4);
      tCtx.fillStyle = 'rgba(255,255,255,0.4)';
      tCtx.fillRect(-fSize*0.3, -fSize*0.1, 4, 6);
      tCtx.fillRect(fSize*0.08, -fSize*0.1, 4, 6);
    }}

    // 2. Laser Eyes
    if (state.accLaser) {{
      const eye1X = -fSize*0.15, eye2X = fSize*0.15, eyeY = -fSize*0.06;
      [eye1X, eye2X].forEach(ex => {{
        const rad = tCtx.createRadialGradient(ex, eyeY, 2, ex, eyeY, 25);
        rad.addColorStop(0, '#ffffff'); rad.addColorStop(0.3, '#ff003b'); rad.addColorStop(1, 'transparent');
        tCtx.fillStyle = rad;
        tCtx.beginPath(); tCtx.arc(ex, eyeY, 25, 0, Math.PI*2); tCtx.fill();
        tCtx.strokeStyle = '#ff003b'; tCtx.lineWidth = 4;
        tCtx.beginPath(); tCtx.moveTo(ex, eyeY); tCtx.lineTo(ex > 0 ? ex + 120 : ex - 120, h*0.5); tCtx.stroke();
      }});
    }}

    // 3. Gold Crown
    if (state.accCrown) {{
      tCtx.fillStyle = '#eab308';
      tCtx.strokeStyle = '#a16207';
      tCtx.lineWidth = 2;
      tCtx.beginPath();
      tCtx.moveTo(-fSize*0.35, -fSize*0.36);
      tCtx.lineTo(-fSize*0.38, -fSize*0.55);
      tCtx.lineTo(-fSize*0.18, -fSize*0.44);
      tCtx.lineTo(0, -fSize*0.62);
      tCtx.lineTo(fSize*0.18, -fSize*0.44);
      tCtx.lineTo(fSize*0.38, -fSize*0.55);
      tCtx.lineTo(fSize*0.35, -fSize*0.36);
      tCtx.closePath();
      tCtx.fill(); tCtx.stroke();
      tCtx.fillStyle = '#ef4444';
      tCtx.beginPath(); tCtx.arc(0, -fSize*0.46, 5, 0, Math.PI*2); tCtx.fill();
    }}

    // 4. Speech Bubble
    if (state.accBubble) {{
      tCtx.save();
      tCtx.fillStyle = '#ffffff';
      tCtx.strokeStyle = '#000000';
      tCtx.lineWidth = 2;
      tCtx.beginPath();
      tCtx.roundRect(fSize*0.25, -fSize*0.6, 90, 36, 8);
      tCtx.fill(); tCtx.stroke();
      tCtx.fillStyle = '#000000';
      tCtx.font = 'bold 12px sans-serif';
      tCtx.textAlign = 'center';
      tCtx.fillText('W MURAD', fSize*0.25 + 45, -fSize*0.6 + 22);
      tCtx.restore();
    }}

    tCtx.restore();
  }}

  // Petpet Hand
  if (state.anim === 'petpet') {{
    const squish = Math.sin((frameIdx % 5) / 5 * Math.PI);
    const handY = h * 0.16 + squish * (h * 0.12);
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
    let needsRedraw = false;
    if (state.isBgGif && state.bgGifFrames.length > 1) {{
      state.gifBgFrameIndex = (state.gifBgFrameIndex + 1) % state.bgGifFrames.length;
      needsRedraw = true;
    }}
    if (state.anim !== 'none') {{
      state.frame = (state.frame + 1) % state.totalFrames;
      needsRedraw = true;
    }}
    if (needsRedraw) {{
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
  const isAnimated = state.anim !== 'none' || (state.isBgGif && state.bgGifFrames.length > 1);
  if (!isAnimated) {{
    downloadPng();
    return;
  }}
  const wrap = document.getElementById('progressWrap');
  const bar = document.getElementById('progressBar');
  const txt = document.getElementById('progressText');
  wrap.style.display = 'block';
  bar.style.width = '10%';
  txt.innerText = 'Capturing GIF frames...';

  const maxExp = 320;
  const aspect = canvas.width / canvas.height;
  let expW, expH;
  if (aspect >= 1) {{
    expW = maxExp;
    expH = Math.round(maxExp / aspect);
  }} else {{
    expH = maxExp;
    expW = Math.round(maxExp * aspect);
  }}

  const offscreen = document.createElement('canvas');
  offscreen.width = expW;
  offscreen.height = expH;
  const offCtx = offscreen.getContext('2d');

  let totalExportFrames = state.totalFrames;
  if (state.isBgGif && state.bgGifFrames.length > 1) {{
    totalExportFrames = Math.max(state.totalFrames, Math.min(state.bgGifFrames.length, 30));
  }}

  const frames = [];
  const origGifIndex = state.gifBgFrameIndex;
  const origFrame = state.frame;

  for (let i = 0; i < totalExportFrames; i++) {{
    if (state.isBgGif && state.bgGifFrames.length > 0) {{
      state.gifBgFrameIndex = i % state.bgGifFrames.length;
    }}
    state.frame = i % state.totalFrames;
    render(offCtx, expW, expH, state.frame);
    frames.push(offscreen.toDataURL('image/png'));
  }}

  state.gifBgFrameIndex = origGifIndex;
  state.frame = origFrame;

  bar.style.width = '40%';
  txt.innerText = 'Encoding Discord GIF...';

  if (window.gifshot) {{
    window.gifshot.createGIF({{
      images: frames,
      gifWidth: expW,
      gifHeight: expH,
      interval: 1 / state.fps,
      numFrames: totalExportFrames,
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
        link.download = `murad_meme.gif`;
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

# --- TOP HEADER & ADMIN PANEL (TOP RIGHT) ---
col_head_left, col_head_right = st.columns([5, 2])
with col_head_left:
    st.markdown("<div style='padding: 4px 0;'><h2 style='margin:0; font-size: 22px; color: #fff; display: flex; align-items: center; gap: 8px;'>🎭 Murad Face Slapper <span style='font-size: 13px; color: #5865F2; background: rgba(88,101,242,0.15); padding: 2px 8px; border-radius: 12px; font-weight: 500;'>Discord Meme & GIF Maker</span></h2></div>", unsafe_allow_html=True)

with col_head_right:
    admin_ui = st.popover("🔐 Admin Panel", use_container_width=True) if hasattr(st, "popover") else st.expander("🔐 Admin Panel")
    with admin_ui:
        st.markdown("### 🔐 Admin Panel")
        st.caption("Upload new faces directly to the permanent default catalog for all users!")

        expected_pwd = ""
        try:
            expected_pwd = st.secrets.get("ADMIN_PASSWORD", "")
        except Exception:
            pass
        if not expected_pwd:
            expected_pwd = "MuradAdmin"

        admin_pwd = st.text_input("Enter Admin Password:", type="password", key="top_admin_pwd", placeholder="Password...")

        if admin_pwd and admin_pwd == expected_pwd:
            st.success("✅ Admin Access Granted!")
            new_face_name = st.text_input("Face Display Name & Emoji:", placeholder="e.g. Gaming Murad 🎮")
            new_face_file = st.file_uploader("Upload Face Image (PNG / JPG):", type=["png", "jpg", "jpeg", "webp"], key="top_face_file")

            token_secret = ""
            try:
                token_secret = st.secrets.get("GITHUB_TOKEN", "")
            except Exception:
                pass

            if token_secret:
                st.markdown("<small style='color: #23a55a; font-weight: 600;'>🟢 GitHub Auto-Sync: Active (Connected via Streamlit Secrets)</small>", unsafe_allow_html=True)
                gh_token = token_secret
            else:
                gh_token = st.text_input(
                    "GitHub Personal Access Token:",
                    type="password",
                    placeholder="github_pat_... or ghp_...",
                    help="Tip: Add GITHUB_TOKEN to Streamlit Secrets so you never have to paste it here!"
                )
                with st.expander("ℹ️ How to keep token safe in Streamlit Secrets"):
                    st.markdown("""
                    **Add to Streamlit Cloud Secrets (Never store in Git files):**
                    1. In [share.streamlit.io](https://share.streamlit.io) → Click `...` next to `muradeditor` → **Settings** → **Secrets**.
                    2. Add:
                       ```toml
                       GITHUB_TOKEN = "your_token_here"
                       ```
                    3. Click **Save**. Your token stays completely private!
                    """)

            if st.button("🚀 Push Face to Default Catalog", type="primary", use_container_width=True):
                if not new_face_name or not new_face_file:
                    st.error("Please enter a name and select an image file!")
                else:
                    img_bytes = new_face_file.read()
                    clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', new_face_name.split()[0].lower())
                    filename = f"murad_{clean_name}.png"
                    face_id = f"murad_{clean_name}"

                    # 1. Save locally to assets
                    local_path = ASSETS_DIR / filename
                    with open(local_path, "wb") as f:
                        f.write(img_bytes)

                    # 2. Update local manifest.json
                    current_manifest = []
                    if MANIFEST_FILE.exists():
                        try:
                            with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                                current_manifest = json.load(f)
                        except Exception:
                            pass

                    current_manifest.append({
                        "id": face_id,
                        "name": new_face_name,
                        "file": filename
                    })

                    manifest_bytes = json.dumps(current_manifest, indent=2).encode("utf-8")
                    with open(MANIFEST_FILE, "wb") as f:
                        f.write(manifest_bytes)

                    # 3. Push to GitHub repository
                    with st.spinner("Pushing to GitHub repository (Aboodi-8/Muradeditor)..."):
                        ok_img, err_img = push_file_to_github(
                            "Aboodi-8", "Muradeditor", f"assets/{filename}", img_bytes,
                            f"Add new default face: {new_face_name}", gh_token
                        )
                        if not ok_img:
                            st.error(f"❌ Could not upload image to GitHub: {err_img}")
                        else:
                            ok_manifest, err_manifest = push_file_to_github(
                                "Aboodi-8", "Muradeditor", "assets/manifest.json", manifest_bytes,
                                f"Update manifest for {new_face_name}", gh_token
                            )
                            if ok_manifest:
                                st.success(f"🎉 Successfully saved! '{new_face_name}' is permanently added to the default catalog!")
                                st.balloons()
                                st.rerun()
                            else:
                                st.error(f"❌ Image saved, but manifest.json update failed: {err_manifest}")
        elif admin_pwd:
            st.error("❌ Incorrect Admin Password.")

# Embed Interactive HTML5 Canvas Application with Real-Time Mouse Dragging
components.html(html_app, height=1120, scrolling=True)
