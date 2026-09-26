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
    page_title="Murad Photoshop Studio | Discord Meme & GIF Maker",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom minimal styles to remove extra padding and make iframe fill the entire viewport
st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden; }
    .block-container {
        padding: 0 !important;
        max-width: 100% !important;
    }
    iframe {
        width: 100% !important;
        min-height: 94vh !important;
        height: 96vh !important;
        border: none !important;
    }
    .stApp {
        background-color: #1e1e1e;
        overflow: hidden;
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
                            "file": item["file"],
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
                "file": p.name,
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

token_secret = ""
try:
    token_secret = st.secrets.get("GITHUB_TOKEN", "")
except Exception:
    pass

expected_pwd = ""
try:
    expected_pwd = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    pass
if not expected_pwd:
    expected_pwd = "MuradAdmin"

gh_token_json = json.dumps(token_secret)
admin_pwd_json = json.dumps(expected_pwd)

# --- EMBEDDED PHOTOSHOP WEB STUDIO ---
html_app = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Murad Photoshop Studio</title>
<style>
  :root {{
    --ps-bg: #1e1e1e;
    --ps-topbar: #2d2d30;
    --ps-panel: #252526;
    --ps-canvas-bg: #141414;
    --ps-input: #181818;
    --ps-border: #3c3c3c;
    --ps-border-light: #484848;
    --ps-blue: #007acc;
    --ps-blue-hover: #0e8ad6;
    --ps-blue-active: #005a9e;
    --ps-text: #cccccc;
    --ps-text-bright: #ffffff;
    --ps-text-muted: #858585;
    --ps-danger: #f48771;
    --ps-green: #4ec9b0;
    --ps-yellow: #facc15;
  }}

  * {{
    box-sizing: border-box;
    margin: 0;
    padding: 0;
  }}

  html, body {{
    width: 100vw;
    height: 100vh;
    overflow: hidden;
    background: var(--ps-bg);
    color: var(--ps-text);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    font-size: 12px;
    user-select: none;
    -webkit-user-select: none;
  }}

  /* MAIN APP LAYOUT */
  .ps-app {{
    display: flex;
    flex-direction: column;
    width: 100vw;
    height: 100vh;
    overflow: hidden;
  }}

  /* TOP OPTIONS BAR */
  .ps-topbar {{
    height: 38px;
    background: var(--ps-topbar);
    border-bottom: 1px solid var(--ps-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 10px;
    gap: 12px;
    z-index: 100;
    flex-shrink: 0;
  }}

  .ps-brand {{
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
  }}

  .ps-logo {{
    background: var(--ps-blue);
    color: #fff;
    font-weight: 900;
    font-size: 13px;
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: -0.5px;
    box-shadow: 0 2px 5px rgba(0, 122, 204, 0.4);
  }}

  .ps-title {{
    font-weight: 700;
    font-size: 12.5px;
    color: var(--ps-text-bright);
    white-space: nowrap;
  }}

  .ps-doc-badge {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--ps-border);
    font-size: 10.5px;
    padding: 2px 7px;
    border-radius: 3px;
    color: var(--ps-text-muted);
    white-space: nowrap;
  }}

  /* CONTEXT TOOL OPTIONS IN TOPBAR */
  .ps-tool-options {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    overflow-x: auto;
    padding: 0 4px;
  }}

  .ps-opt-label {{
    color: var(--ps-text-muted);
    font-size: 11px;
    white-space: nowrap;
  }}

  .ps-opt-badge {{
    background: rgba(0, 122, 204, 0.2);
    border: 1px solid var(--ps-blue);
    color: #4dc2ff;
    padding: 2px 8px;
    border-radius: 4px;
    font-weight: 700;
    font-size: 11px;
    white-space: nowrap;
  }}

  .ps-opt-group {{
    display: flex;
    align-items: center;
    gap: 4px;
    border-left: 1px solid var(--ps-border);
    padding-left: 8px;
  }}

  .ps-opt-btn {{
    background: var(--ps-input);
    border: 1px solid var(--ps-border);
    color: var(--ps-text);
    padding: 3px 8px;
    border-radius: 3px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.1s ease;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .ps-opt-btn:hover {{
    background: rgba(255, 255, 255, 0.08);
    border-color: var(--ps-border-light);
    color: #fff;
  }}
  .ps-opt-btn.danger:hover {{
    background: var(--ps-danger);
    border-color: var(--ps-danger);
    color: #fff;
  }}

  /* EXPORT ACTIONS IN TOPBAR */
  .ps-actions {{
    display: flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }}

  .ps-btn {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--ps-border);
    color: var(--ps-text-bright);
    padding: 5px 12px;
    border-radius: 4px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
    white-space: nowrap;
  }}
  .ps-btn:hover {{
    background: rgba(255, 255, 255, 0.16);
    border-color: #fff;
  }}
  .ps-btn-primary {{
    background: var(--ps-blue);
    border-color: var(--ps-blue);
    box-shadow: 0 2px 8px rgba(0, 122, 204, 0.35);
  }}
  .ps-btn-primary:hover {{
    background: var(--ps-blue-hover);
    border-color: var(--ps-blue-hover);
  }}

  /* WORKSPACE BODY (TOOLBAR + CANVAS + PANELS) */
  .ps-body {{
    display: flex;
    flex: 1;
    height: calc(100vh - 38px);
    overflow: hidden;
    position: relative;
  }}

  /* SLIM LEFT TOOLBAR */
  .ps-toolbar {{
    width: 44px;
    background: var(--ps-topbar);
    border-right: 1px solid var(--ps-border);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 8px 0;
    gap: 6px;
    flex-shrink: 0;
    z-index: 50;
  }}

  .tool-btn {{
    width: 34px;
    height: 34px;
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    color: var(--ps-text);
    font-size: 16px;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.1s ease;
    position: relative;
  }}
  .tool-btn:hover {{
    background: rgba(255, 255, 255, 0.08);
    color: #fff;
  }}
  .tool-btn.active {{
    background: rgba(0, 122, 204, 0.25);
    border-color: var(--ps-blue);
    color: #fff;
  }}
  .tool-btn.active::before {{
    content: '';
    position: absolute;
    left: -4px;
    top: 6px;
    bottom: 6px;
    width: 3px;
    background: var(--ps-blue);
    border-radius: 2px;
  }}

  /* CENTER CANVAS VIEWPORT */
  .ps-canvas-viewport {{
    flex: 1;
    background: var(--ps-canvas-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    padding: 16px;
  }}

  .canvas-stage {{
    position: relative;
    max-width: 100%;
    max-height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }}

  #mainCanvas {{
    max-width: calc(100vw - 380px);
    max-height: calc(100vh - 90px);
    border: 1px solid var(--ps-border);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7);
    display: block;
    object-fit: contain;
    background: #000;
  }}

  /* RIGHT DOCKED PANELS */
  .ps-panels-sidebar {{
    width: 310px;
    background: var(--ps-panel);
    border-left: 1px solid var(--ps-border);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    height: 100%;
    z-index: 50;
  }}

  .ps-panel-tabs {{
    display: flex;
    background: #1c1c1d;
    border-bottom: 1px solid var(--ps-border);
    overflow-x: auto;
    scrollbar-width: none;
  }}
  .ps-panel-tabs::-webkit-scrollbar {{ display: none; }}

  .panel-tab {{
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--ps-text-muted);
    padding: 9px 11px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    white-space: nowrap;
    transition: all 0.15s ease;
  }}
  .panel-tab:hover {{
    color: var(--ps-text-bright);
  }}
  .panel-tab.active {{
    color: #fff;
    border-bottom-color: var(--ps-blue);
    background: var(--ps-panel);
  }}

  /* PANEL CONTENT AREA */
  .ps-panel-body {{
    flex: 1;
    overflow-y: auto;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }}

  .panel-section-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    border-bottom: 1px solid var(--ps-border);
    padding-bottom: 6px;
    margin-bottom: 4px;
  }}
  .panel-section-title {{
    font-weight: 800;
    font-size: 12.5px;
    color: var(--ps-text-bright);
    display: flex;
    align-items: center;
    gap: 6px;
  }}

  /* DISCRETE CORNER ADMIN LOCK BUTTON */
  .admin-lock-btn {{
    background: transparent;
    border: 1px solid var(--ps-border);
    border-radius: 4px;
    color: var(--ps-text-muted);
    cursor: pointer;
    padding: 2px 6px;
    font-size: 12px;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }}
  .admin-lock-btn:hover {{
    background: rgba(255, 255, 255, 0.08);
    border-color: var(--ps-blue);
    color: #fff;
    transform: scale(1.05);
  }}

  /* DROP ZONES */
  .ps-dropzone {{
    border: 1.5px dashed var(--ps-blue);
    background: rgba(0, 122, 204, 0.08);
    border-radius: 6px;
    padding: 10px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s ease;
    display: block;
    color: #fff;
    font-weight: 600;
    font-size: 11px;
  }}
  .ps-dropzone:hover {{
    background: rgba(0, 122, 204, 0.18);
    border-color: #fff;
  }}
  .ps-dropzone input {{ display: none; }}

  /* GRID CARDS (FACES, TEMPLATES, EFFECTS) */
  .grid-cards {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }}
  .grid-card {{
    background: var(--ps-input);
    border: 1px solid var(--ps-border);
    border-radius: 6px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.1s ease;
  }}
  .grid-card:hover {{
    border-color: var(--ps-border-light);
    transform: translateY(-1px);
    background: rgba(255, 255, 255, 0.04);
  }}
  .grid-card.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 122, 204, 0.2);
  }}
  .grid-card img {{
    width: 60px;
    height: 60px;
    border-radius: 4px;
    object-fit: cover;
    margin-bottom: 4px;
  }}
  .grid-card span {{
    font-size: 10px;
    font-weight: 600;
    color: var(--ps-text);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  }}

  /* BUTTON GROUPS & TOGGLES */
  .btn-group {{
    display: flex;
    background: var(--ps-input);
    border-radius: 6px;
    padding: 2px;
    border: 1px solid var(--ps-border);
    gap: 2px;
    flex-wrap: wrap;
  }}
  .btn-toggle {{
    flex: 1 1 auto;
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    font-size: 10.5px;
    font-weight: 700;
    padding: 5px 6px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.1s ease;
    text-align: center;
    white-space: nowrap;
  }}
  .btn-toggle:hover {{ color: #fff; }}
  .btn-toggle.active {{
    background: var(--ps-blue);
    color: #fff;
  }}

  /* SLIDERS */
  .slider-row {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .slider-row label {{
    font-size: 10.5px;
    color: var(--ps-text-muted);
    display: flex;
    justify-content: space-between;
    font-weight: 600;
  }}
  .slider-row input[type="range"] {{
    width: 100%;
    accent-color: var(--ps-blue);
    cursor: pointer;
  }}

  /* INPUTS */
  .ps-input {{
    width: 100%;
    background: var(--ps-input);
    border: 1px solid var(--ps-border);
    color: #fff;
    font-size: 11.5px;
    padding: 6px 10px;
    border-radius: 4px;
    outline: none;
  }}
  .ps-input:focus {{ border-color: var(--ps-blue); }}

  /* LAYERS LIST */
  .layers-list {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .layer-item {{
    background: var(--ps-input);
    border: 1px solid var(--ps-border);
    border-radius: 4px;
    padding: 6px 8px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    transition: all 0.1s ease;
  }}
  .layer-item:hover {{
    border-color: var(--ps-border-light);
  }}
  .layer-item.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 122, 204, 0.2);
  }}
  .layer-title {{
    font-weight: 600;
    font-size: 11px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .layer-controls {{
    display: flex;
    gap: 3px;
  }}
  .layer-btn {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    cursor: pointer;
    font-size: 11px;
    padding: 2px 4px;
    border-radius: 3px;
  }}
  .layer-btn:hover {{ color: #fff; background: rgba(255, 255, 255, 0.1); }}

  /* FLOATING PROGRESS BAR */
  .progress-wrap {{
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(37, 37, 38, 0.95);
    backdrop-filter: blur(20px);
    border: 1px solid var(--ps-border);
    border-radius: 8px;
    padding: 12px 18px;
    width: 320px;
    box-shadow: 0 16px 40px rgba(0,0,0,0.7);
    z-index: 1000;
  }}
  .progress-track {{
    height: 6px;
    background: var(--ps-input);
    border-radius: 3px;
    overflow: hidden;
  }}
  .progress-bar {{
    height: 100%;
    background: var(--ps-blue);
    width: 0%;
    transition: width 0.1s linear;
  }}
  .progress-text {{
    font-size: 11px;
    color: var(--ps-text);
    text-align: center;
    margin-top: 6px;
  }}

  /* ADMIN MODAL */
  .admin-modal-backdrop {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.65);
    backdrop-filter: blur(8px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 2000;
  }}
  .admin-modal {{
    width: 420px;
    max-width: 90vw;
    background: var(--ps-panel);
    border: 1px solid var(--ps-border-light);
    border-radius: 8px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.85);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .admin-modal-header {{
    background: var(--ps-topbar);
    border-bottom: 1px solid var(--ps-border);
    padding: 10px 14px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .admin-modal-title {{
    font-weight: 800;
    font-size: 13px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .admin-modal-close {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    font-size: 14px;
    cursor: pointer;
  }}
  .admin-modal-close:hover {{ color: #fff; }}
  .admin-modal-body {{
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 70vh;
    overflow-y: auto;
  }}

  /* RESPONSIVE SCALING - GUARANTEE ALL BUTTONS FIT */
  @media (max-width: 900px) {{
    .ps-panels-sidebar {{
      width: 260px;
    }}
    #mainCanvas {{
      max-width: calc(100vw - 320px);
    }}
  }}
  @media (max-width: 720px) {{
    .ps-title, .ps-doc-badge {{
      display: none;
    }}
    .ps-panels-sidebar {{
      position: absolute;
      right: 0;
      top: 38px;
      height: calc(100vh - 38px);
      width: 280px;
      box-shadow: -10px 0 30px rgba(0,0,0,0.8);
    }}
    #mainCanvas {{
      max-width: calc(100vw - 64px);
    }}
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

<div class="ps-app">

  <!-- TOP OPTIONS BAR -->
  <header class="ps-topbar">
    <div class="ps-brand">
      <span class="ps-logo">Ps</span>
      <span class="ps-title">Murad Studio</span>
      <span class="ps-doc-badge" id="docSizeBadge">500 × 500 px</span>
    </div>

    <!-- CONTEXT TOOL OPTIONS -->
    <div class="ps-tool-options" id="toolOptions">
      <span class="ps-opt-label">Transform:</span>
      <span class="ps-opt-badge" id="optLayerName">No layer selected</span>
      <div class="ps-opt-group" id="optActionGroup" style="display:none;">
        <span class="ps-opt-label" id="optScaleVal">100%</span>
        <span class="ps-opt-label" id="optRotVal">0°</span>
        <button id="optFlipBtn" class="ps-opt-btn" title="Flip Horizontal">↔️ Flip</button>
        <button id="optCenterBtn" class="ps-opt-btn" title="Center on Canvas">🎯 Center</button>
        <button id="optDeleteBtn" class="ps-opt-btn danger" title="Delete Layer">🗑️ Delete</button>
      </div>
    </div>

    <!-- EXPORT ACTIONS -->
    <div class="ps-actions">
      <button id="btnExportGif" class="ps-btn ps-btn-primary" title="Export Animated Discord GIF">⬇️ Export GIF</button>
      <button id="btnExportPng" class="ps-btn" title="Export High-Res PNG">⬇️ PNG</button>
      <button id="btnCopyDiscord" class="ps-btn" title="Copy to clipboard for instant Discord paste">📋 Copy</button>
    </div>
  </header>

  <!-- BODY (TOOLBAR + CANVAS + RIGHT PANELS) -->
  <div class="ps-body">

    <!-- LEFT SLIM TOOLBAR -->
    <aside class="ps-toolbar">
      <button class="tool-btn active" data-tool="move" data-target="layers" title="Move & Free Transform (V)">↖️</button>
      <button class="tool-btn" data-tool="faces" data-target="faces" title="Murad Faces (F)">🎭</button>
      <button class="tool-btn" data-tool="bg" data-target="bg" title="Backdrop & Templates (B)">🖼️</button>
      <button class="tool-btn" data-tool="text" data-target="text" title="Meme Text (T)">✍️</button>
      <button class="tool-btn" data-tool="stickers" data-target="stickers" title="Custom Stickers (S)">🎀</button>
      <button class="tool-btn" data-tool="anim" data-target="anim" title="Animation FX (A)">✨</button>
    </aside>

    <!-- CENTER CANVAS VIEWPORT -->
    <main class="ps-canvas-viewport" id="canvasViewport">
      <div class="canvas-stage">
        <canvas id="mainCanvas" width="500" height="500"></canvas>
      </div>
    </main>

    <!-- RIGHT DOCKED PANELS -->
    <aside class="ps-panels-sidebar" id="panelsSidebar">
      <!-- PANEL TABS -->
      <div class="ps-panel-tabs">
        <button class="panel-tab active" data-tab="faces">🎭 Faces</button>
        <button class="panel-tab" data-tab="bg">🖼️ Backdrop</button>
        <button class="panel-tab" data-tab="text">✍️ Text</button>
        <button class="panel-tab" data-tab="stickers">🎀 Stickers</button>
        <button class="panel-tab" data-tab="anim">✨ FX</button>
        <button class="panel-tab" data-tab="layers">📑 Layers</button>
      </div>

      <!-- PANEL: FACES -->
      <div class="ps-panel-body" id="tabContent-faces">
        <div class="panel-section-header">
          <span class="panel-section-title">🎭 Murad Faces</span>
          <!-- DISCRETE CORNER ADMIN LOCK BUTTON -->
          <button id="adminLockBtn" class="admin-lock-btn" title="Admin Face Catalog Settings">🔒</button>
        </div>

        <label class="ps-dropzone">
          <span>📸 Upload Real Photo / Custom Face</span>
          <input type="file" id="faceFileInput" accept="image/*">
        </label>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="font-size:10.5px; color:var(--ps-text-muted); font-weight:700;">DEFAULT FACES:</span>
          <button id="addFaceBtn" class="ps-opt-btn" style="background:var(--ps-blue); border-color:var(--ps-blue); color:#fff;">➕ Add to Canvas</button>
        </div>
        <div class="grid-cards" id="facesGrid" style="max-height:190px; overflow-y:auto;"></div>

        <div style="display:flex; flex-direction:column; gap:4px; margin-top:4px;">
          <span style="font-size:10.5px; color:var(--ps-text-muted); font-weight:700;">CUTOUT SHAPE:</span>
          <div class="btn-group" id="maskGroup">
            <button class="btn-toggle active" data-mask="square">Full Frame</button>
            <button class="btn-toggle" data-mask="circle">Sticker Circle</button>
            <button class="btn-toggle" data-mask="oval">Oval</button>
          </div>
        </div>

        <div class="slider-row">
          <label>Scale: <b id="faceScaleVal">100%</b></label>
          <input type="range" id="faceScaleSlider" min="0.1" max="3.0" step="0.05" value="1.0">
        </div>
        <div class="slider-row">
          <label>Opacity: <b id="faceOpacityVal">100%</b></label>
          <input type="range" id="faceOpacitySlider" min="0.1" max="1.0" step="0.05" value="1.0">
        </div>
      </div>

      <!-- PANEL: BACKDROP -->
      <div class="ps-panel-body" id="tabContent-bg" style="display:none;">
        <div class="panel-section-header">
          <span class="panel-section-title">🖼️ Backdrop & Templates</span>
        </div>

        <label class="ps-dropzone">
          <span>📁 Upload Image, Meme or GIF</span>
          <input type="file" id="bgFileInput" accept="image/*,.gif">
        </label>

        <div style="display:flex; flex-direction:column; gap:4px;">
          <span style="font-size:10.5px; color:var(--ps-text-muted); font-weight:700;">CANVAS RATIO:</span>
          <div class="btn-group" id="canvasSizeGroup">
            <button class="btn-toggle active" data-size="true_size">📐 True Size</button>
            <button class="btn-toggle" data-size="square">⏹️ 1:1</button>
            <button class="btn-toggle" data-size="landscape">🖼️ 16:9</button>
            <button class="btn-toggle" data-size="portrait">📱 9:16</button>
          </div>
        </div>

        <span style="font-size:10.5px; color:var(--ps-text-muted); font-weight:700; margin-top:4px;">POPULAR TEMPLATES:</span>
        <div class="grid-cards" id="bgPresetsRow" style="grid-template-columns: repeat(2, 1fr);"></div>
      </div>

      <!-- PANEL: TEXT -->
      <div class="ps-panel-body" id="tabContent-text" style="display:none;">
        <div class="panel-section-header">
          <span class="panel-section-title">✍️ Meme Text</span>
        </div>

        <div style="display:flex; gap:4px;">
          <button id="addTopTextBtn" class="ps-opt-btn" style="flex:1;">➕ Top</button>
          <button id="addBottomTextBtn" class="ps-opt-btn" style="flex:1;">➕ Bottom</button>
          <button id="addCustomTextBtn" class="ps-opt-btn" style="flex:1; background:var(--ps-blue); color:#fff; border-color:var(--ps-blue);">➕ Custom</button>
        </div>

        <div id="textEditorBox" style="display:flex; flex-direction:column; gap:8px; margin-top:4px;">
          <span style="font-size:10.5px; color:var(--ps-text-muted); font-weight:700;">EDIT TEXT:</span>
          <input type="text" id="activeTextInput" class="ps-input" placeholder="Type meme text here...">

          <div class="slider-row">
            <label>Font Size: <b id="textSizeVal">38px</b></label>
            <input type="range" id="textSizeSlider" min="14" max="90" step="2" value="38">
          </div>

          <div style="display:flex; flex-direction:column; gap:4px;">
            <span style="font-size:10.5px; color:var(--ps-text-muted); font-weight:700;">COLOR:</span>
            <div class="btn-group" id="textColorGroup">
              <button class="btn-toggle active" data-color="#ffffff">White</button>
              <button class="btn-toggle" data-color="#facc15" style="color:#facc15;">Yellow</button>
              <button class="btn-toggle" data-color="#ef4444" style="color:#ef4444;">Red</button>
              <button class="btn-toggle" data-color="#22d3ee" style="color:#22d3ee;">Cyan</button>
              <button class="btn-toggle" data-color="#4ade80" style="color:#4ade80;">Green</button>
            </div>
          </div>
        </div>
      </div>

      <!-- PANEL: STICKERS -->
      <div class="ps-panel-body" id="tabContent-stickers" style="display:none;">
        <div class="panel-section-header">
          <span class="panel-section-title">🎀 Custom Stickers</span>
        </div>

        <label class="ps-dropzone">
          <span>📁 Upload Custom PNG / Sticker</span>
          <input type="file" id="accFileInput" accept="image/*,.gif">
        </label>

        <div id="accEditorBox" style="display:none; flex-direction:column; gap:8px;">
          <div class="slider-row">
            <label>Sticker Size: <b id="accScaleVal">100%</b></label>
            <input type="range" id="accScaleSlider" min="0.1" max="3.0" step="0.05" value="1.0">
          </div>
          <div class="slider-row">
            <label>Opacity: <b id="accOpacityVal">100%</b></label>
            <input type="range" id="accOpacitySlider" min="0.1" max="1.0" step="0.05" value="1.0">
          </div>
        </div>
      </div>

      <!-- PANEL: ANIMATION FX -->
      <div class="ps-panel-body" id="tabContent-anim" style="display:none;">
        <div class="panel-section-header">
          <span class="panel-section-title">✨ Discord GIF Effects</span>
        </div>

        <div class="grid-cards" id="animGrid" style="grid-template-columns:repeat(3, 1fr);">
          <div class="grid-card active" data-anim="none"><span>🖼️</span><span>Still</span></div>
          <div class="grid-card" data-anim="bob"><span>🕺</span><span>Head Bob</span></div>
          <div class="grid-card" data-anim="shake"><span>💢</span><span>Shake</span></div>
          <div class="grid-card" data-anim="spin"><span>🌀</span><span>Speen 360°</span></div>
          <div class="grid-card" data-anim="petpet"><span>👋</span><span>Petpet</span></div>
          <div class="grid-card" data-anim="zoom"><span>💥</span><span>Bass Pulse</span></div>
          <div class="grid-card" data-anim="pulse"><span>💓</span><span>Heartbeat</span></div>
          <div class="grid-card" data-anim="wobble"><span>🌊</span><span>Wobble</span></div>
          <div class="grid-card" data-anim="disco"><span>🪩</span><span>Disco</span></div>
        </div>
      </div>

      <!-- PANEL: LAYERS -->
      <div class="ps-panel-body" id="tabContent-layers" style="display:none;">
        <div class="panel-section-header">
          <span class="panel-section-title">📑 Layers Stack</span>
        </div>
        <div class="layers-list" id="layersList"></div>
      </div>

    </aside>

  </div>

  <!-- FLOATING PROGRESS BAR OVERLAY -->
  <div class="progress-wrap" id="progressWrap" style="display:none;">
    <div class="progress-track"><div class="progress-bar" id="progressBar"></div></div>
    <div class="progress-text" id="progressText">Encoding Discord GIF...</div>
  </div>

  <!-- ADMIN CATALOG MODAL -->
  <div class="admin-modal-backdrop" id="adminModal">
    <div class="admin-modal">
      <div class="admin-modal-header">
        <span class="admin-modal-title">🔐 Face Catalog Admin</span>
        <button class="admin-modal-close" id="adminModalClose">✕</button>
      </div>
      
      <!-- STEP 1: PASSWORD AUTH -->
      <div class="admin-modal-body" id="adminAuthBody">
        <div style="text-align:center; padding: 10px 0;">
          <div style="font-size:32px; margin-bottom:8px;">🔒</div>
          <div style="font-weight:700; font-size:13px; color:#fff; margin-bottom:4px;">Enter Admin Password</div>
          <div style="font-size:11px; color:var(--ps-text-muted); margin-bottom:12px;">Manage default catalog faces or push new ones to GitHub.</div>
          <input type="password" id="adminPwdInput" class="ps-input" placeholder="Password..." style="margin-bottom:8px; text-align:center; width:220px; margin:0 auto 10px auto;">
          <div id="adminAuthError" style="color:var(--ps-danger); font-size:11px; display:none; margin-bottom:8px;">❌ Incorrect Admin Password</div>
          <button id="adminUnlockBtn" class="ps-btn ps-btn-primary" style="width:220px; margin:0 auto; justify-content:center;">Unlock</button>
        </div>
      </div>

      <!-- STEP 2: CATALOG MANAGEMENT -->
      <div class="admin-modal-body" id="adminManageBody" style="display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="color:var(--ps-green); font-weight:700; font-size:11px;">✅ Admin Access Granted</span>
          <button id="adminLockOutBtn" class="ps-opt-btn" style="font-size:10px;">Lock</button>
        </div>

        <div style="border-top:1px solid var(--ps-border); padding-top:8px;">
          <span style="font-size:11px; font-weight:700; color:#fff;">➕ ADD NEW FACE TO CATALOG:</span>
          <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
            <input type="text" id="adminNewFaceName" class="ps-input" placeholder="Face Name & Emoji (e.g. Party Murad 🎉)">
            <input type="file" id="adminNewFaceFile" accept="image/*" class="ps-input" style="padding:4px;">
            <button id="adminUploadBtn" class="ps-btn ps-btn-primary" style="justify-content:center;">🚀 Push to Catalog</button>
            <div id="adminUploadStatus" style="font-size:10.5px; text-align:center;"></div>
          </div>
        </div>

        <div style="border-top:1px solid var(--ps-border); padding-top:8px;">
          <span style="font-size:11px; font-weight:700; color:#fff;">🗑️ MANAGE DEFAULT FACES:</span>
          <div id="adminFacesCatalogList" style="display:flex; flex-direction:column; gap:4px; max-height:180px; overflow-y:auto; margin-top:6px;"></div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
const faces = {faces_json};
const templates = {templates_json};
const GITHUB_TOKEN = {gh_token_json};
const EXPECTED_ADMIN_PWD = {admin_pwd_json};

function makeFaceLayer(faceIndex, x, y, scale) {{
  return {{
    id: 'layer_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
    faceIndex: faceIndex !== undefined ? faceIndex : 0,
    x: x !== undefined ? x : 0,
    y: y !== undefined ? y : -50,
    scale: scale !== undefined ? scale : 1.0,
    rotation: 0,
    flipH: 1,
    opacity: 1.0,
    maskShape: 'square',
    customImg: null
  }};
}}

const state = {{
  bgType: 'template',
  bgTemplateId: templates.length > 0 ? templates[0].id : 'suit',
  bgCustomImg: null,
  bgGifFrames: [],
  bgGifIndex: 0,
  bgGifDelay: 100,
  bgIsGif: false,
  canvasSizeMode: 'true_size',
  
  facesOnCanvas: [makeFaceLayer(0, 0, -60, 1.0)],
  selectedFaceIdx: 0,

  accessoriesOnCanvas: [],
  selectedAccIdx: -1,

  texts: [],
  selectedTextIdx: -1,

  animation: 'none',
  animSpeed: 1.0,
  animIntensity: 1.0,

  transformState: {{
    mode: null, // 'drag', 'scale', 'rotate'
    targetType: null, // 'face', 'acc', 'text'
    targetIdx: -1,
    startX: 0,
    startY: 0,
    initialX: 0,
    initialY: 0,
    initialScale: 1.0,
    initialRotation: 0,
    initialDist: 1.0,
    initialAngle: 0,
    activeHandle: null
  }}
}};

// Preload templates
const loadedTemplates = {{}};
templates.forEach(t => {{
  const img = new Image();
  img.src = t.src;
  loadedTemplates[t.id] = img;
}});

// Preload faces
const loadedFaces = [];
function preloadFacesCatalog() {{
  faces.forEach((f, idx) => {{
    const img = new Image();
    img.src = f.src;
    loadedFaces[idx] = img;
  }});
}}
preloadFacesCatalog();

const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');

// --- COORDINATES & BOUNDING BOX CALCULATION ---
function getActiveLayerData() {{
  if (state.selectedFaceIdx >= 0 && state.selectedFaceIdx < state.facesOnCanvas.length) {{
    const face = state.facesOnCanvas[state.selectedFaceIdx];
    let img = null;
    if (face.customImg) {{
      img = face.customImg;
    }} else if (loadedFaces[face.faceIndex]) {{
      img = loadedFaces[face.faceIndex];
    }}
    const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
    const baseW = 120;
    const baseH = 120 * aspect;
    const hw = (baseW * face.scale) / 2;
    const hh = (baseH * face.scale) / 2;
    return {{
      type: 'face',
      idx: state.selectedFaceIdx,
      obj: face,
      cx: canvas.width / 2 + face.x,
      cy: canvas.height / 2 + face.y,
      hw: hw,
      hh: hh,
      rotation: face.rotation || 0,
      scale: face.scale || 1.0
    }};
  }}
  if (state.selectedAccIdx >= 0 && state.selectedAccIdx < state.accessoriesOnCanvas.length) {{
    const acc = state.accessoriesOnCanvas[state.selectedAccIdx];
    const aspect = (acc.img && acc.img.naturalHeight) ? (acc.img.naturalHeight / acc.img.naturalWidth) : 1.0;
    const baseW = 100;
    const baseH = 100 * aspect;
    const hw = (baseW * acc.scale) / 2;
    const hh = (baseH * acc.scale) / 2;
    return {{
      type: 'acc',
      idx: state.selectedAccIdx,
      obj: acc,
      cx: canvas.width / 2 + acc.x,
      cy: canvas.height / 2 + acc.y,
      hw: hw,
      hh: hh,
      rotation: acc.rotation || 0,
      scale: acc.scale || 1.0
    }};
  }}
  if (state.selectedTextIdx >= 0 && state.selectedTextIdx < state.texts.length) {{
    const t = state.texts[state.selectedTextIdx];
    ctx.font = '900 ' + t.size + 'px Impact, sans-serif';
    const metrics = ctx.measureText(t.text || ' ');
    const bw = metrics.width + 24;
    const bh = t.size + 14;
    const hw = bw / 2;
    const hh = bh / 2;
    return {{
      type: 'text',
      idx: state.selectedTextIdx,
      obj: t,
      cx: canvas.width / 2 + t.x,
      cy: canvas.height / 2 + t.y,
      hw: hw,
      hh: hh,
      rotation: t.rotation || 0,
      scale: 1.0
    }};
  }}
  return null;
}}

// Convert screen/pointer client event to internal canvas pixel coordinates
function getCanvasPointer(e) {{
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

// Convert canvas world coordinates to layer's local unrotated coordinates
function toLocal(mx, my, cx, cy, rotationDeg) {{
  const rad = (rotationDeg * Math.PI) / 180;
  const dx = mx - cx;
  const dy = my - cy;
  return {{
    lx: dx * Math.cos(-rad) - dy * Math.sin(-rad),
    ly: dx * Math.sin(-rad) + dy * Math.cos(-rad)
  }};
}}

// Hit test handles & bounding box for an active layer
function testHandlesHit(mx, my, layerData) {{
  if (!layerData) return null;
  const {{ cx, cy, hw, hh, rotation }} = layerData;
  const {{ lx, ly }} = toLocal(mx, my, cx, cy, rotation);

  // 1. Rotation handle: at (0, -hh - 24)
  const rotDist = Math.hypot(lx - 0, ly - (-hh - 24));
  if (rotDist <= 14) {{
    return 'rot';
  }}

  // 2. Corner handles (size 9x9, radius 10)
  const corners = [
    {{ name: 'tl', x: -hw, y: -hh }},
    {{ name: 'tr', x: hw, y: -hh }},
    {{ name: 'bl', x: -hw, y: hh }},
    {{ name: 'br', x: hw, y: hh }}
  ];
  for (let c of corners) {{
    if (Math.abs(lx - c.x) <= 10 && Math.abs(ly - c.y) <= 10) {{
      return c.name;
    }}
  }}

  // 3. Inside bounding box
  if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {{
    return 'body';
  }}

  return null;
}}

// Find any layer under point
function findLayerAt(mx, my) {{
  // Test active layer handles first
  const active = getActiveLayerData();
  if (active) {{
    const h = testHandlesHit(mx, my, active);
    if (h) return {{ handle: h, layer: active }};
  }}

  // Test other faces from top to bottom
  for (let i = state.facesOnCanvas.length - 1; i >= 0; i--) {{
    const f = state.facesOnCanvas[i];
    let img = f.customImg || loadedFaces[f.faceIndex];
    const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
    const hw = (120 * f.scale) / 2;
    const hh = (120 * aspect * f.scale) / 2;
    const cx = canvas.width / 2 + f.x;
    const cy = canvas.height / 2 + f.y;
    const {{ lx, ly }} = toLocal(mx, my, cx, cy, f.rotation || 0);
    if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {{
      return {{ handle: 'body', layer: {{ type: 'face', idx: i }} }};
    }}
  }}

  // Test custom stickers
  for (let i = state.accessoriesOnCanvas.length - 1; i >= 0; i--) {{
    const a = state.accessoriesOnCanvas[i];
    const aspect = (a.img && a.img.naturalHeight) ? (a.img.naturalHeight / a.img.naturalWidth) : 1.0;
    const hw = (100 * a.scale) / 2;
    const hh = (100 * aspect * a.scale) / 2;
    const cx = canvas.width / 2 + a.x;
    const cy = canvas.height / 2 + a.y;
    const {{ lx, ly }} = toLocal(mx, my, cx, cy, a.rotation || 0);
    if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {{
      return {{ handle: 'body', layer: {{ type: 'acc', idx: i }} }};
    }}
  }}

  // Test text layers
  for (let i = state.texts.length - 1; i >= 0; i--) {{
    const t = state.texts[i];
    ctx.font = '900 ' + t.size + 'px Impact, sans-serif';
    const metrics = ctx.measureText(t.text || ' ');
    const hw = (metrics.width + 24) / 2;
    const hh = (t.size + 14) / 2;
    const cx = canvas.width / 2 + t.x;
    const cy = canvas.height / 2 + t.y;
    const {{ lx, ly }} = toLocal(mx, my, cx, cy, t.rotation || 0);
    if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {{
      return {{ handle: 'body', layer: {{ type: 'text', idx: i }} }};
    }}
  }}

  return null;
}}

// --- RENDER CANVAS ---
function render(offsetObj) {{
  const animOff = offsetObj || {{ x: 0, y: 0, rot: 0, scale: 1.0 }};

  // Determine canvas size
  let bgImg = null;
  if (state.bgType === 'custom' && state.bgCustomImg) {{
    bgImg = state.bgCustomImg;
  }} else if (state.bgIsGif && state.bgGifFrames.length > 0) {{
    bgImg = state.bgGifFrames[state.bgGifIndex];
  }} else if (state.bgType === 'template' && loadedTemplates[state.bgTemplateId]) {{
    bgImg = loadedTemplates[state.bgTemplateId];
  }}

  let cw = 500, ch = 500;
  if (state.canvasSizeMode === 'square') {{
    cw = 500; ch = 500;
  }} else if (state.canvasSizeMode === 'landscape') {{
    cw = 560; ch = 315;
  }} else if (state.canvasSizeMode === 'portrait') {{
    cw = 315; ch = 560;
  }} else if (state.canvasSizeMode === 'true_size' && bgImg && bgImg.naturalWidth) {{
    const maxDim = 560;
    const nw = bgImg.naturalWidth;
    const nh = bgImg.naturalHeight;
    const ratio = Math.min(maxDim / nw, maxDim / nh, 1.0);
    cw = Math.round(nw * ratio);
    ch = Math.round(nh * ratio);
  }}

  if (canvas.width !== cw || canvas.height !== ch) {{
    canvas.width = cw;
    canvas.height = ch;
    document.getElementById('docSizeBadge').innerText = cw + ' × ' + ch + ' px';
  }}

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 1. Draw Background
  if (bgImg) {{
    ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);
  }} else {{
    ctx.fillStyle = '#222';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }}

  // 2. Draw Face Layers
  state.facesOnCanvas.forEach((face, idx) => {{
    let img = face.customImg || loadedFaces[face.faceIndex];
    if (!img) return;

    ctx.save();
    const cx = canvas.width / 2 + face.x + animOff.x;
    const cy = canvas.height / 2 + face.y + animOff.y;
    ctx.translate(cx, cy);
    ctx.rotate(((face.rotation + animOff.rot) * Math.PI) / 180);
    ctx.scale(face.flipH, 1);
    ctx.globalAlpha = face.opacity !== undefined ? face.opacity : 1.0;

    const aspect = (img.naturalHeight || 1) / (img.naturalWidth || 1);
    const baseW = 120;
    const baseH = 120 * aspect;
    const w = baseW * face.scale * animOff.scale;
    const h = baseH * face.scale * animOff.scale;

    if (face.maskShape === 'circle') {{
      ctx.beginPath();
      ctx.arc(0, 0, Math.min(w, h) / 2, 0, Math.PI * 2);
      ctx.closePath();
      ctx.clip();
    }} else if (face.maskShape === 'oval') {{
      ctx.beginPath();
      ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, Math.PI * 2);
      ctx.closePath();
      ctx.clip();
    }}

    ctx.drawImage(img, -w / 2, -h / 2, w, h);
    ctx.restore();
  }});

  // 3. Draw Accessories / Stickers
  state.accessoriesOnCanvas.forEach((acc, idx) => {{
    if (!acc.img) return;
    ctx.save();
    const cx = canvas.width / 2 + acc.x;
    const cy = canvas.height / 2 + acc.y;
    ctx.translate(cx, cy);
    ctx.rotate((acc.rotation * Math.PI) / 180);
    ctx.scale(acc.flipH, 1);
    ctx.globalAlpha = acc.opacity !== undefined ? acc.opacity : 1.0;

    const aspect = (acc.img.naturalHeight || 1) / (acc.img.naturalWidth || 1);
    const baseW = 100;
    const baseH = 100 * aspect;
    const w = baseW * acc.scale;
    const h = baseH * acc.scale;

    ctx.drawImage(acc.img, -w / 2, -h / 2, w, h);
    ctx.restore();
  }});

  // 4. Draw Meme Text
  state.texts.forEach((t, idx) => {{
    ctx.save();
    const cx = canvas.width / 2 + t.x;
    const cy = canvas.height / 2 + t.y;
    ctx.translate(cx, cy);
    ctx.rotate((t.rotation * Math.PI) / 180);

    ctx.font = '900 ' + t.size + 'px Impact, -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = Math.max(3, Math.round(t.size / 8));
    ctx.strokeStyle = '#000000';
    ctx.fillStyle = t.color || '#ffffff';

    ctx.strokeText(t.text, 0, 0);
    ctx.fillText(t.text, 0, 0);
    ctx.restore();
  }});

  // 5. Draw Photoshop Bounding Box & Free Transform Handles
  const active = getActiveLayerData();
  if (active) {{
    const {{ cx, cy, hw, hh, rotation }} = active;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((rotation * Math.PI) / 180);

    // Blue dashed bounding rectangle
    ctx.strokeStyle = '#007acc';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(-hw, -hh, hw * 2, hh * 2);

    // Stem line to rotation handle
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(0, -hh);
    ctx.lineTo(0, -hh - 24);
    ctx.stroke();

    // Top circular rotation handle
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#007acc';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(0, -hh - 24, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // 4 Corner square handles
    const corners = [
      [-hw, -hh],
      [hw, -hh],
      [-hw, hh],
      [hw, hh]
    ];
    const hSize = 8;
    corners.forEach(([x, y]) => {{
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#007acc';
      ctx.lineWidth = 1.5;
      ctx.fillRect(x - hSize / 2, y - hSize / 2, hSize, hSize);
      ctx.strokeRect(x - hSize / 2, y - hSize / 2, hSize, hSize);
    }});

    ctx.restore();
  }}
}}

// --- INTERACTIVE FREE TRANSFORM EVENT LISTENERS ---
function initCanvasEvents() {{
  const ts = state.transformState;

  function onPointerDown(e) {{
    const pt = getCanvasPointer(e);
    const hit = findLayerAt(pt.x, pt.y);

    if (hit) {{
      // Select layer
      if (hit.layer.type === 'face') {{
        state.selectedFaceIdx = hit.layer.idx;
        state.selectedAccIdx = -1;
        state.selectedTextIdx = -1;
      }} else if (hit.layer.type === 'acc') {{
        state.selectedAccIdx = hit.layer.idx;
        state.selectedFaceIdx = -1;
        state.selectedTextIdx = -1;
      }} else if (hit.layer.type === 'text') {{
        state.selectedTextIdx = hit.layer.idx;
        state.selectedFaceIdx = -1;
        state.selectedAccIdx = -1;
      }}

      updateOptionsBar();
      updatePanelInputs();
      render();

      const active = getActiveLayerData();
      if (!active) return;

      const handle = testHandlesHit(pt.x, pt.y, active);
      if (handle === 'rot') {{
        ts.mode = 'rotate';
        ts.targetType = active.type;
        ts.targetIdx = active.idx;
        ts.initialAngle = Math.atan2(pt.y - active.cy, pt.x - active.cx);
        ts.initialRotation = active.rotation;
      }} else if (handle === 'tl' || handle === 'tr' || handle === 'bl' || handle === 'br') {{
        ts.mode = 'scale';
        ts.targetType = active.type;
        ts.targetIdx = active.idx;
        ts.activeHandle = handle;
        ts.initialDist = Math.hypot(pt.x - active.cx, pt.y - active.cy);
        ts.initialScale = active.type === 'text' ? active.obj.size : active.scale;
      }} else if (handle === 'body') {{
        ts.mode = 'drag';
        ts.targetType = active.type;
        ts.targetIdx = active.idx;
        ts.startX = pt.x;
        ts.startY = pt.y;
        ts.initialX = active.obj.x;
        ts.initialY = active.obj.y;
      }}
    }} else {{
      // Clicked on empty canvas -> clear selection
      state.selectedFaceIdx = -1;
      state.selectedAccIdx = -1;
      state.selectedTextIdx = -1;
      updateOptionsBar();
      render();
    }}
  }}

  function onPointerMove(e) {{
    const pt = getCanvasPointer(e);
    const active = getActiveLayerData();

    if (ts.mode === 'rotate' && active) {{
      const currentAngle = Math.atan2(pt.y - active.cy, pt.x - active.cx);
      let deg = Math.round((currentAngle + Math.PI / 2) * (180 / Math.PI));
      deg = (deg % 360 + 360) % 360;
      active.obj.rotation = deg;
      updateOptionsBar();
      render();
    }} else if (ts.mode === 'scale' && active) {{
      const curDist = Math.hypot(pt.x - active.cx, pt.y - active.cy);
      if (active.type === 'text') {{
        const newSize = Math.max(14, Math.min(90, Math.round((curDist / ts.initialDist) * ts.initialScale)));
        active.obj.size = newSize;
        document.getElementById('textSizeSlider').value = newSize;
        document.getElementById('textSizeVal').innerText = newSize + 'px';
      }} else {{
        const newScale = Math.max(0.15, Math.min(3.5, (curDist / ts.initialDist) * ts.initialScale));
        active.obj.scale = parseFloat(newScale.toFixed(2));
        if (active.type === 'face') {{
          document.getElementById('faceScaleSlider').value = active.obj.scale;
          document.getElementById('faceScaleVal').innerText = Math.round(active.obj.scale * 100) + '%';
        }} else if (active.type === 'acc') {{
          document.getElementById('accScaleSlider').value = active.obj.scale;
          document.getElementById('accScaleVal').innerText = Math.round(active.obj.scale * 100) + '%';
        }}
      }}
      updateOptionsBar();
      render();
    }} else if (ts.mode === 'drag' && active) {{
      const dx = pt.x - ts.startX;
      const dy = pt.y - ts.startY;
      active.obj.x = ts.initialX + dx;
      active.obj.y = ts.initialY + dy;
      render();
    }} else if (ts.mode === null) {{
      // Update cursor
      if (active) {{
        const h = testHandlesHit(pt.x, pt.y, active);
        if (h === 'rot') {{
          canvas.style.cursor = 'crosshair';
        }} else if (h === 'tl' || h === 'br') {{
          canvas.style.cursor = 'nwse-resize';
        }} else if (h === 'tr' || h === 'bl') {{
          canvas.style.cursor = 'nesw-resize';
        }} else if (h === 'body') {{
          canvas.style.cursor = 'move';
        }} else {{
          canvas.style.cursor = 'default';
        }}
      }} else {{
        canvas.style.cursor = 'default';
      }}
    }}
  }}

  function onPointerUp() {{
    ts.mode = null;
    ts.activeHandle = null;
    updateLayersList();
  }}

  // Mouse events
  canvas.addEventListener('mousedown', onPointerDown);
  window.addEventListener('mousemove', onPointerMove);
  window.addEventListener('mouseup', onPointerUp);

  // Touch events for iPad/tablet/mobile
  canvas.addEventListener('touchstart', (e) => {{ e.preventDefault(); onPointerDown(e); }}, {{ passive: false }});
  window.addEventListener('touchmove', (e) => {{ if (ts.mode) e.preventDefault(); onPointerMove(e); }}, {{ passive: false }});
  window.addEventListener('touchend', onPointerUp);
}}

// --- UPDATE UI PANELS & TOPBAR OPTIONS ---
function updateOptionsBar() {{
  const active = getActiveLayerData();
  const optName = document.getElementById('optLayerName');
  const optGroup = document.getElementById('optActionGroup');
  const optScale = document.getElementById('optScaleVal');
  const optRot = document.getElementById('optRotVal');

  if (!active) {{
    optName.innerText = 'No layer selected';
    optName.style.borderColor = 'var(--ps-border)';
    optName.style.background = 'transparent';
    optName.style.color = 'var(--ps-text-muted)';
    optGroup.style.display = 'none';
  }} else {{
    let label = '';
    if (active.type === 'face') label = '🎭 Face #' + (active.idx + 1);
    else if (active.type === 'acc') label = '🎀 Sticker #' + (active.idx + 1);
    else if (active.type === 'text') label = '✍️ Text: "' + (active.obj.text || '') + '"';

    optName.innerText = label;
    optName.style.borderColor = 'var(--ps-blue)';
    optName.style.background = 'rgba(0, 122, 204, 0.2)';
    optName.style.color = '#4dc2ff';
    optGroup.style.display = 'flex';

    if (active.type === 'text') {{
      optScale.innerText = 'Size: ' + active.obj.size + 'px';
    }} else {{
      optScale.innerText = 'Scale: ' + Math.round(active.obj.scale * 100) + '%';
    }}
    optRot.innerText = 'Angle: ' + Math.round(active.rotation) + '°';
  }}
}}

function updatePanelInputs() {{
  const active = getActiveLayerData();
  if (!active) return;

  if (active.type === 'face') {{
    document.getElementById('faceScaleSlider').value = active.obj.scale;
    document.getElementById('faceScaleVal').innerText = Math.round(active.obj.scale * 100) + '%';
    document.getElementById('faceOpacitySlider').value = active.obj.opacity !== undefined ? active.obj.opacity : 1.0;
    document.getElementById('faceOpacityVal').innerText = Math.round((active.obj.opacity || 1.0) * 100) + '%';

    document.querySelectorAll('#maskGroup .btn-toggle').forEach(btn => {{
      btn.classList.toggle('active', btn.dataset.mask === (active.obj.maskShape || 'square'));
    }});
  }} else if (active.type === 'acc') {{
    document.getElementById('accEditorBox').style.display = 'flex';
    document.getElementById('accScaleSlider').value = active.obj.scale;
    document.getElementById('accScaleVal').innerText = Math.round(active.obj.scale * 100) + '%';
    document.getElementById('accOpacitySlider').value = active.obj.opacity !== undefined ? active.obj.opacity : 1.0;
    document.getElementById('accOpacityVal').innerText = Math.round((active.obj.opacity || 1.0) * 100) + '%';
  }} else if (active.type === 'text') {{
    document.getElementById('activeTextInput').value = active.obj.text;
    document.getElementById('textSizeSlider').value = active.obj.size;
    document.getElementById('textSizeVal').innerText = active.obj.size + 'px';
    document.querySelectorAll('#textColorGroup .btn-toggle').forEach(btn => {{
      btn.classList.toggle('active', btn.dataset.color === active.obj.color);
    }});
  }}
}}

function updateLayersList() {{
  const list = document.getElementById('layersList');
  list.innerHTML = '';

  const all = [];
  state.facesOnCanvas.forEach((f, idx) => {{
    all.push({{ type: 'face', idx: idx, name: '🎭 Face #' + (idx + 1), isSelected: state.selectedFaceIdx === idx }});
  }});
  state.accessoriesOnCanvas.forEach((a, idx) => {{
    all.push({{ type: 'acc', idx: idx, name: '🎀 Sticker #' + (idx + 1), isSelected: state.selectedAccIdx === idx }});
  }});
  state.texts.forEach((t, idx) => {{
    all.push({{ type: 'text', idx: idx, name: '✍️ "' + (t.text || 'Text') + '"', isSelected: state.selectedTextIdx === idx }});
  }});

  if (all.length === 0) {{
    list.innerHTML = '<div style="color:var(--ps-text-muted); font-size:11px; text-align:center; padding:12px;">No layers on canvas yet.</div>';
    return;
  }}

  all.forEach(item => {{
    const el = document.createElement('div');
    el.className = 'layer-item' + (item.isSelected ? ' active' : '');
    el.innerHTML = `
      <span class="layer-title">${{item.name}}</span>
      <div class="layer-controls">
        <button class="layer-btn del-btn" title="Delete">🗑️</button>
      </div>
    `;

    el.onclick = (e) => {{
      if (e.target.classList.contains('del-btn')) {{
        deleteLayer(item.type, item.idx);
        return;
      }}
      if (item.type === 'face') {{
        state.selectedFaceIdx = item.idx;
        state.selectedAccIdx = -1;
        state.selectedTextIdx = -1;
      }} else if (item.type === 'acc') {{
        state.selectedAccIdx = item.idx;
        state.selectedFaceIdx = -1;
        state.selectedTextIdx = -1;
      }} else if (item.type === 'text') {{
        state.selectedTextIdx = item.idx;
        state.selectedFaceIdx = -1;
        state.selectedAccIdx = -1;
      }}
      updateOptionsBar();
      updatePanelInputs();
      updateLayersList();
      render();
    }};

    list.appendChild(el);
  }});
}}

function deleteLayer(type, idx) {{
  if (type === 'face') {{
    state.facesOnCanvas.splice(idx, 1);
    state.selectedFaceIdx = state.facesOnCanvas.length - 1;
  }} else if (type === 'acc') {{
    state.accessoriesOnCanvas.splice(idx, 1);
    state.selectedAccIdx = state.accessoriesOnCanvas.length - 1;
  }} else if (type === 'text') {{
    state.texts.splice(idx, 1);
    state.selectedTextIdx = state.texts.length - 1;
  }}
  updateOptionsBar();
  updateLayersList();
  render();
}}

// Switch panel tabs
function switchTab(tabId) {{
  document.querySelectorAll('.panel-tab').forEach(t => {{
    t.classList.toggle('active', t.dataset.tab === tabId);
  }});
  document.querySelectorAll('.ps-panel-body').forEach(b => {{
    b.style.display = (b.id === 'tabContent-' + tabId) ? 'flex' : 'none';
  }});
  document.querySelectorAll('.tool-btn').forEach(btn => {{
    btn.classList.toggle('active', btn.dataset.target === tabId);
  }});
}}

// Build catalog grids
function buildFacesUI() {{
  const grid = document.getElementById('facesGrid');
  grid.innerHTML = '';
  faces.forEach((f, idx) => {{
    const card = document.createElement('div');
    const isActive = (state.facesOnCanvas[state.selectedFaceIdx] && state.facesOnCanvas[state.selectedFaceIdx].faceIndex === idx);
    card.className = 'grid-card' + (isActive ? ' active' : '');
    card.innerHTML = `<img src="${{f.src}}"><span>${{f.name}}</span>`;
    card.onclick = () => {{
      if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
        state.facesOnCanvas[state.selectedFaceIdx].faceIndex = idx;
        state.facesOnCanvas[state.selectedFaceIdx].customImg = null;
      }} else {{
        state.facesOnCanvas.push(makeFaceLayer(idx, 0, -40, 1.0));
        state.selectedFaceIdx = state.facesOnCanvas.length - 1;
      }}
      buildFacesUI();
      updateOptionsBar();
      render();
    }};
    grid.appendChild(card);
  }});
}}

function buildTemplatesUI() {{
  const grid = document.getElementById('bgPresetsRow');
  grid.innerHTML = '';
  templates.forEach(t => {{
    const card = document.createElement('div');
    card.className = 'grid-card' + (state.bgTemplateId === t.id && state.bgType === 'template' ? ' active' : '');
    card.innerHTML = `<img src="${{t.src}}"><span>${{t.name}}</span>`;
    card.onclick = () => {{
      state.bgType = 'template';
      state.bgTemplateId = t.id;
      state.bgIsGif = false;
      buildTemplatesUI();
      render();
    }};
    grid.appendChild(card);
  }});
}}

// Setup all click/change handlers
function initUIEvents() {{
  buildFacesUI();
  buildTemplatesUI();
  updateLayersList();
  updateOptionsBar();

  // Tab switching
  document.querySelectorAll('.panel-tab').forEach(tab => {{
    tab.onclick = () => switchTab(tab.dataset.tab);
  }});
  document.querySelectorAll('.tool-btn').forEach(btn => {{
    btn.onclick = () => switchTab(btn.dataset.target);
  }});

  // Topbar Options buttons
  document.getElementById('optFlipBtn').onclick = () => {{
    const a = getActiveLayerData();
    if (a && a.obj.flipH !== undefined) {{
      a.obj.flipH = a.obj.flipH === 1 ? -1 : 1;
      render();
    }}
  }};
  document.getElementById('optCenterBtn').onclick = () => {{
    const a = getActiveLayerData();
    if (a) {{
      a.obj.x = 0;
      a.obj.y = (a.type === 'face' ? -50 : 0);
      render();
    }}
  }};
  document.getElementById('optDeleteBtn').onclick = () => {{
    const a = getActiveLayerData();
    if (a) deleteLayer(a.type, a.idx);
  }};

  // Add face button
  document.getElementById('addFaceBtn').onclick = () => {{
    state.facesOnCanvas.push(makeFaceLayer(0, (Math.random() - 0.5) * 60, -50, 0.9));
    state.selectedFaceIdx = state.facesOnCanvas.length - 1;
    state.selectedAccIdx = -1;
    state.selectedTextIdx = -1;
    updateOptionsBar();
    updateLayersList();
    render();
  }};

  // Face Photo Upload
  document.getElementById('faceFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (re) => {{
      const img = new Image();
      img.onload = () => {{
        if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
          state.facesOnCanvas[state.selectedFaceIdx].customImg = img;
        }} else {{
          const nf = makeFaceLayer(0, 0, -40, 1.0);
          nf.customImg = img;
          state.facesOnCanvas.push(nf);
          state.selectedFaceIdx = state.facesOnCanvas.length - 1;
        }}
        render();
      }};
      img.src = re.target.result;
    }};
    reader.readAsDataURL(file);
  }};

  // Mask cutouts
  document.querySelectorAll('#maskGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
        state.facesOnCanvas[state.selectedFaceIdx].maskShape = btn.dataset.mask;
        render();
      }}
    }};
  }});

  // Face Sliders
  document.getElementById('faceScaleSlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('faceScaleVal').innerText = Math.round(val * 100) + '%';
    if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
      state.facesOnCanvas[state.selectedFaceIdx].scale = val;
      updateOptionsBar();
      render();
    }}
  }};
  document.getElementById('faceOpacitySlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('faceOpacityVal').innerText = Math.round(val * 100) + '%';
    if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
      state.facesOnCanvas[state.selectedFaceIdx].opacity = val;
      render();
    }}
  }};

  // Canvas aspect ratios
  document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.canvasSizeMode = btn.dataset.size;
      render();
    }};
  }});

  // Background file upload (Image or animated GIF)
  document.getElementById('bgFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;
    if (file.name.toLowerCase().endsWith('.gif')) {{
      const reader = new FileReader();
      reader.onload = (re) => {{
        const parsed = window.gifuct ? window.gifuct.parseGIF(re.target.result) : null;
        if (parsed) {{
          const frames = window.gifuct.decompressFrames(parsed, true);
          state.bgGifFrames = [];
          frames.forEach(f => {{
            const fc = document.createElement('canvas');
            fc.width = f.dims.width;
            fc.height = f.dims.height;
            const fctx = fc.getContext('2d');
            const imgData = fctx.createImageData(f.dims.width, f.dims.height);
            imgData.data.set(f.patch);
            fctx.putImageData(imgData, 0, 0);
            state.bgGifFrames.push(fc);
          }});
          state.bgIsGif = true;
          state.bgType = 'custom';
          render();
        }}
      }};
      reader.readAsArrayBuffer(file);
    }} else {{
      const reader = new FileReader();
      reader.onload = (re) => {{
        const img = new Image();
        img.onload = () => {{
          state.bgCustomImg = img;
          state.bgType = 'custom';
          state.bgIsGif = false;
          render();
        }};
        img.src = re.target.result;
      }};
      reader.readAsDataURL(file);
    }}
  }};

  // Text tools
  document.getElementById('addTopTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'TOP TEXT', x: 0, y: -canvas.height / 2 + 35, size: 36, color: '#ffffff', rotation: 0 }});
    state.selectedTextIdx = state.texts.length - 1;
    state.selectedFaceIdx = -1;
    state.selectedAccIdx = -1;
    updatePanelInputs();
    updateOptionsBar();
    updateLayersList();
    render();
  }};
  document.getElementById('addBottomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'BOTTOM TEXT', x: 0, y: canvas.height / 2 - 35, size: 36, color: '#ffffff', rotation: 0 }});
    state.selectedTextIdx = state.texts.length - 1;
    state.selectedFaceIdx = -1;
    state.selectedAccIdx = -1;
    updatePanelInputs();
    updateOptionsBar();
    updateLayersList();
    render();
  }};
  document.getElementById('addCustomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'MEME TEXT', x: 0, y: 0, size: 38, color: '#facc15', rotation: 0 }});
    state.selectedTextIdx = state.texts.length - 1;
    state.selectedFaceIdx = -1;
    state.selectedAccIdx = -1;
    updatePanelInputs();
    updateOptionsBar();
    updateLayersList();
    render();
  }};
  document.getElementById('activeTextInput').oninput = (e) => {{
    if (state.selectedTextIdx >= 0 && state.texts[state.selectedTextIdx]) {{
      state.texts[state.selectedTextIdx].text = e.target.value;
      updateOptionsBar();
      updateLayersList();
      render();
    }}
  }};
  document.getElementById('textSizeSlider').oninput = (e) => {{
    const val = parseInt(e.target.value);
    document.getElementById('textSizeVal').innerText = val + 'px';
    if (state.selectedTextIdx >= 0 && state.texts[state.selectedTextIdx]) {{
      state.texts[state.selectedTextIdx].size = val;
      updateOptionsBar();
      render();
    }}
  }};
  document.querySelectorAll('#textColorGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#textColorGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (state.selectedTextIdx >= 0 && state.texts[state.selectedTextIdx]) {{
        state.texts[state.selectedTextIdx].color = btn.dataset.color;
        render();
      }}
    }};
  }});

  // Custom Sticker Upload
  document.getElementById('accFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (re) => {{
      const img = new Image();
      img.onload = () => {{
        state.accessoriesOnCanvas.push({{
          id: 'acc_' + Date.now(),
          img: img,
          x: 0,
          y: 0,
          scale: 1.0,
          rotation: 0,
          flipH: 1,
          opacity: 1.0
        }});
        state.selectedAccIdx = state.accessoriesOnCanvas.length - 1;
        state.selectedFaceIdx = -1;
        state.selectedTextIdx = -1;
        updatePanelInputs();
        updateOptionsBar();
        updateLayersList();
        render();
      }};
      img.src = re.target.result;
    }};
    reader.readAsDataURL(file);
  }};

  document.getElementById('accScaleSlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('accScaleVal').innerText = Math.round(val * 100) + '%';
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].scale = val;
      updateOptionsBar();
      render();
    }}
  }};
  document.getElementById('accOpacitySlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('accOpacityVal').innerText = Math.round(val * 100) + '%';
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].opacity = val;
      render();
    }}
  }};

  // Animation FX Grid
  document.querySelectorAll('#animGrid .grid-card').forEach(card => {{
    card.onclick = () => {{
      document.querySelectorAll('#animGrid .grid-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.animation = card.dataset.anim;
    }};
  }});

  // Admin Modal Trigger
  document.getElementById('adminLockBtn').onclick = () => {{
    document.getElementById('adminModal').style.display = 'flex';
  }};
  document.getElementById('adminModalClose').onclick = () => {{
    document.getElementById('adminModal').style.display = 'none';
  }};

  // Admin Auth Logic
  document.getElementById('adminUnlockBtn').onclick = () => {{
    const entered = document.getElementById('adminPwdInput').value;
    if (entered === EXPECTED_ADMIN_PWD) {{
      document.getElementById('adminAuthBody').style.display = 'none';
      document.getElementById('adminManageBody').style.display = 'flex';
      renderAdminCatalog();
    }} else {{
      const err = document.getElementById('adminAuthError');
      err.style.display = 'block';
      setTimeout(() => {{ err.style.display = 'none'; }}, 3000);
    }}
  }};
  document.getElementById('adminLockOutBtn').onclick = () => {{
    document.getElementById('adminAuthBody').style.display = 'flex';
    document.getElementById('adminManageBody').style.display = 'none';
    document.getElementById('adminPwdInput').value = '';
  }};

  // Admin Upload New Face via GitHub API
  document.getElementById('adminUploadBtn').onclick = async () => {{
    const name = document.getElementById('adminNewFaceName').value.trim();
    const fileInput = document.getElementById('adminNewFaceFile');
    const status = document.getElementById('adminUploadStatus');

    if (!name || !fileInput.files[0]) {{
      status.innerText = '⚠️ Please enter face name and choose an image file.';
      status.style.color = 'var(--ps-yellow)';
      return;
    }}

    status.innerText = '⏳ Processing image and pushing to GitHub...';
    status.style.color = 'var(--ps-blue)';

    const file = fileInput.files[0];
    const reader = new FileReader();
    reader.onload = async (re) => {{
      const dataUri = re.target.result;
      const base64Data = dataUri.split(',')[1];
      const cleanName = name.split(' ')[0].toLowerCase().replace(/[^a-z0-9_]/g, '_');
      const filename = 'murad_' + cleanName + '.png';
      const faceId = 'murad_' + cleanName;

      // Add to runtime faces array
      faces.push({{
        id: faceId,
        name: name,
        file: filename,
        src: dataUri
      }});

      // Preload image
      const newImg = new Image();
      newImg.src = dataUri;
      loadedFaces.push(newImg);

      buildFacesUI();
      renderAdminCatalog();

      // Push to GitHub if token available
      if (GITHUB_TOKEN) {{
        try {{
          await fetch(`https://api.github.com/repos/Aboodi-8/Muradeditor/contents/assets/${{filename}}`, {{
            method: 'PUT',
            headers: {{
              'Authorization': 'Bearer ' + GITHUB_TOKEN,
              'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{
              message: 'Add catalog face: ' + name,
              content: base64Data
            }})
          }});

          // Update manifest
          const manifestPayload = faces.map(f => ({{ id: f.id, name: f.name, file: f.file || (f.id + '.png') }}));
          const manifestBase64 = btoa(JSON.stringify(manifestPayload, null, 2));

          // Get manifest SHA
          const getRes = await fetch('https://api.github.com/repos/Aboodi-8/Muradeditor/contents/assets/manifest.json', {{
            headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
          }});
          const getData = await getRes.json();

          await fetch('https://api.github.com/repos/Aboodi-8/Muradeditor/contents/assets/manifest.json', {{
            method: 'PUT',
            headers: {{
              'Authorization': 'Bearer ' + GITHUB_TOKEN,
              'Content-Type': 'application/json'
            }},
            body: JSON.stringify({{
              message: 'Update manifest for: ' + name,
              content: manifestBase64,
              sha: getData.sha
            }})
          }});

          status.innerText = '✅ Successfully pushed to GitHub catalog!';
          status.style.color = 'var(--ps-green)';
        }} catch (err) {{
          status.innerText = '✅ Added locally (GitHub sync notice: ' + err.message + ')';
          status.style.color = 'var(--ps-green)';
        }}
      }} else {{
        status.innerText = '✅ Added to active studio catalog!';
        status.style.color = 'var(--ps-green)';
      }}

      document.getElementById('adminNewFaceName').value = '';
      fileInput.value = '';
    }};
    reader.readAsDataURL(file);
  }};

  // Export buttons
  document.getElementById('btnExportPng').onclick = () => {{
    // Deselect handles before export
    const prevFace = state.selectedFaceIdx;
    const prevAcc = state.selectedAccIdx;
    const prevText = state.selectedTextIdx;
    state.selectedFaceIdx = -1;
    state.selectedAccIdx = -1;
    state.selectedTextIdx = -1;
    render();

    const link = document.createElement('a');
    link.download = 'murad_meme.png';
    link.href = canvas.toDataURL('image/png');
    link.click();

    state.selectedFaceIdx = prevFace;
    state.selectedAccIdx = prevAcc;
    state.selectedTextIdx = prevText;
    render();
  }};

  document.getElementById('btnCopyDiscord').onclick = async () => {{
    const prevFace = state.selectedFaceIdx;
    const prevAcc = state.selectedAccIdx;
    const prevText = state.selectedTextIdx;
    state.selectedFaceIdx = -1;
    state.selectedAccIdx = -1;
    state.selectedTextIdx = -1;
    render();

    canvas.toBlob(async (blob) => {{
      try {{
        await navigator.clipboard.write([new ClipboardItem({{ 'image/png': blob }})]);
        const btn = document.getElementById('btnCopyDiscord');
        const orig = btn.innerText;
        btn.innerText = '✅ Copied!';
        btn.style.color = 'var(--ps-green)';
        setTimeout(() => {{
          btn.innerText = orig;
          btn.style.color = '';
        }}, 2000);
      }} catch (err) {{
        alert('Clipboard write permissions needed or browser unsupported.');
      }}
      state.selectedFaceIdx = prevFace;
      state.selectedAccIdx = prevAcc;
      state.selectedTextIdx = prevText;
      render();
    }});
  }};

  document.getElementById('btnExportGif').onclick = () => {{
    generateDiscordGif();
  }};
}}

function renderAdminCatalog() {{
  const list = document.getElementById('adminFacesCatalogList');
  list.innerHTML = '';
  faces.forEach((f, idx) => {{
    const row = document.createElement('div');
    row.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:var(--ps-input); padding:4px 8px; border-radius:4px;';
    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px;">
        <img src="${{f.src}}" style="width:28px; height:28px; border-radius:3px; object-fit:cover;">
        <span style="font-weight:600; color:#fff; font-size:11px;">${{f.name}}</span>
      </div>
      <button class="ps-opt-btn danger" style="padding:2px 6px; font-size:10px;">🗑️ Delete</button>
    `;
    row.querySelector('button').onclick = () => {{
      if (confirm('Delete ' + f.name + ' from catalog?')) {{
        faces.splice(idx, 1);
        loadedFaces.splice(idx, 1);
        buildFacesUI();
        renderAdminCatalog();
      }}
    }};
    list.appendChild(row);
  }});
}}

// Discord GIF generator
function generateDiscordGif() {{
  const progWrap = document.getElementById('progressWrap');
  const progBar = document.getElementById('progressBar');
  const progText = document.getElementById('progressText');

  progWrap.style.display = 'block';
  progBar.style.width = '0%';
  progText.innerText = 'Capturing animation frames...';

  const numFrames = (state.animation === 'none' && !state.bgIsGif) ? 1 : 12;
  const frames = [];

  const prevFace = state.selectedFaceIdx;
  const prevAcc = state.selectedAccIdx;
  const prevText = state.selectedTextIdx;
  state.selectedFaceIdx = -1;
  state.selectedAccIdx = -1;
  state.selectedTextIdx = -1;

  for (let i = 0; i < numFrames; i++) {{
    const progress = i / numFrames;
    const off = getAnimOffset(state.animation, progress);
    if (state.bgIsGif && state.bgGifFrames.length > 0) {{
      state.bgGifIndex = i % state.bgGifFrames.length;
    }}
    render(off);
    frames.push(canvas.toDataURL('image/png'));
  }}

  state.selectedFaceIdx = prevFace;
  state.selectedAccIdx = prevAcc;
  state.selectedTextIdx = prevText;
  render();

  gifshot.createGIF({{
    images: frames,
    gifWidth: canvas.width,
    gifHeight: canvas.height,
    interval: 0.08,
    progressCallback: (captureProgress) => {{
      const pct = Math.round(captureProgress * 100);
      progBar.style.width = pct + '%';
      progText.innerText = 'Encoding Discord GIF: ' + pct + '%';
    }}
  }}, (obj) => {{
    if (!obj.error) {{
      const link = document.createElement('a');
      link.download = 'murad_animation.gif';
      link.href = obj.image;
      link.click();
    }}
    progWrap.style.display = 'none';
  }});
}}

function getAnimOffset(anim, progress) {{
  const t = progress * Math.PI * 2;
  if (anim === 'bob') return {{ x: 0, y: Math.sin(t) * 12, rot: 0, scale: 1.0 }};
  if (anim === 'shake') return {{ x: (Math.random() - 0.5) * 14, y: (Math.random() - 0.5) * 14, rot: (Math.random() - 0.5) * 8, scale: 1.0 }};
  if (anim === 'spin') return {{ x: 0, y: 0, rot: progress * 360, scale: 1.0 }};
  if (anim === 'petpet') return {{ x: 0, y: Math.abs(Math.sin(t)) * 14, rot: 0, scale: 1.0 - Math.abs(Math.sin(t)) * 0.15 }};
  if (anim === 'zoom') return {{ x: 0, y: 0, rot: 0, scale: 1.0 + Math.sin(t) * 0.18 }};
  if (anim === 'pulse') return {{ x: 0, y: 0, rot: 0, scale: 1.0 + Math.sin(t * 2) * 0.12 }};
  if (anim === 'wobble') return {{ x: Math.sin(t) * 10, y: 0, rot: Math.sin(t) * 12, scale: 1.0 }};
  if (anim === 'disco') return {{ x: Math.sin(t) * 8, y: Math.cos(t) * 8, rot: Math.sin(t) * 14, scale: 1.0 + Math.sin(t) * 0.1 }};
  return {{ x: 0, y: 0, rot: 0, scale: 1.0 }};
}}

// Live preview loop
let lastFrameTime = 0;
let animProgress = 0;
function animLoop(timestamp) {{
  if (!lastFrameTime) lastFrameTime = timestamp;
  const dt = (timestamp - lastFrameTime) / 1000;
  lastFrameTime = timestamp;

  if (state.animation !== 'none' || state.bgIsGif) {{
    animProgress = (animProgress + dt * 1.5) % 1.0;
    if (state.bgIsGif && state.bgGifFrames.length > 0) {{
      state.bgGifIndex = Math.floor(animProgress * state.bgGifFrames.length) % state.bgGifFrames.length;
    }}
    const off = getAnimOffset(state.animation, animProgress);
    render(off);
  }}

  requestAnimationFrame(animLoop);
}}

// Boot
window.onload = () => {{
  initCanvasEvents();
  initUIEvents();
  render();
  requestAnimationFrame(animLoop);
}};
</script>
</body>
</html>
"""

# Render embedded Photoshop Web Studio
components.html(html_app, height=920, scrolling=False)
