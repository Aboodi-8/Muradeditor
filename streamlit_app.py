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
        margin: 0 !important;
    }
    iframe {
        width: 100% !important;
        min-height: 98vh !important;
        height: 98vh !important;
        border: none !important;
        display: block !important;
    }
    .stApp {
        background-color: #000000 !important;
        overflow: hidden !important;
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
    ]
    tpl_list = []
    for t in tpl_defs:
        img_p = TEMPLATES_DIR / t["file"]
        if img_p.exists():
            tpl_list.append({
                "id": t["id"],
                "name": t["name"],
                "src": get_base64_data_uri(img_p)
            })
    return tpl_list

# Load GIF libraries
gifshot_path = ASSETS_DIR / "gifshot.min.js"
gifshot_script = ""
if gifshot_path.exists():
    with open(gifshot_path, "r", encoding="utf-8") as f:
        gifshot_script = f.read()

gifuct_path = ASSETS_DIR / "gifuct-js.min.js"
gifuct_script = ""
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

# --- EMBEDDED PHOTOSHOP WEB STUDIO (WIDER MENUS, HIGH VISIBILITY & SCREEN-FITTING CANVAS) ---
html_app = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Murad Photoshop Studio</title>
<style>
  :root {{
    --ps-bg: #000000;             /* Pure Obsidian Black */
    --ps-topbar: #070709;         /* Ultra dark sleek bar */
    --ps-panel: #0b0c10;          /* Sleek dark sidebars with high contrast */
    --ps-canvas-bg: #030304;      /* Deep black void behind canvas */
    --ps-card: #12141c;           /* Rich card background */
    --ps-card-hover: #181b26;
    --ps-input: #12141c;          /* Clean input background */
    --ps-border: #1e212d;         /* High-visibility crisp border */
    --ps-border-light: #2c3042;   /* Distinct hover border */
    --ps-blue: #0084ff;           /* High-energy electric Photoshop blue */
    --ps-blue-hover: #1a94ff;
    --ps-blue-active: #0066cc;
    --ps-text: #e2e4ea;           /* High contrast crisp white-gray */
    --ps-text-bright: #ffffff;
    --ps-text-muted: #959cb0;     /* Clear readable muted text */
    --ps-danger: #ff4d4f;
    --ps-green: #10b981;
    --ps-yellow: #fbbf24;
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
    font-size: 14px;
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
    background: #000000;
  }}

  /* TOP OPTIONS BAR (HIGH CONTRAST & CLEAN) */
  .ps-topbar {{
    height: 52px;
    background: var(--ps-topbar);
    border-bottom: 1px solid var(--ps-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 16px;
    gap: 16px;
    z-index: 100;
    flex-shrink: 0;
  }}

  .ps-brand {{
    display: flex;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
  }}

  .ps-logo {{
    background: var(--ps-blue);
    color: #fff;
    font-weight: 900;
    font-size: 17px;
    padding: 5px 12px;
    border-radius: 6px;
    letter-spacing: -0.5px;
    box-shadow: 0 2px 10px rgba(0, 132, 255, 0.45);
  }}

  .ps-title {{
    font-weight: 800;
    font-size: 15px;
    color: var(--ps-text-bright);
    white-space: nowrap;
    letter-spacing: 0.2px;
  }}

  .ps-doc-badge {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--ps-border);
    font-size: 12.5px;
    font-weight: 700;
    padding: 4px 10px;
    border-radius: 5px;
    color: #b0b7c9;
    white-space: nowrap;
  }}

  /* CONTEXT TOOL OPTIONS IN TOPBAR */
  .ps-tool-options {{
    display: flex;
    align-items: center;
    gap: 12px;
    flex: 1;
    overflow-x: auto;
    padding: 0 8px;
  }}

  .ps-opt-label {{
    color: var(--ps-text-muted);
    font-size: 13px;
    font-weight: 600;
    white-space: nowrap;
  }}

  .ps-opt-badge {{
    background: rgba(0, 132, 255, 0.18);
    border: 1px solid var(--ps-blue);
    color: #60c5ff;
    padding: 5px 14px;
    border-radius: 6px;
    font-weight: 800;
    font-size: 13px;
    white-space: nowrap;
  }}

  .ps-opt-group {{
    display: flex;
    align-items: center;
    gap: 8px;
    border-left: 1px solid var(--ps-border);
    padding-left: 12px;
  }}

  .ps-opt-btn {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    color: var(--ps-text-bright);
    padding: 6px 14px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.12s ease;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }}
  .ps-opt-btn:hover {{
    background: rgba(255, 255, 255, 0.14);
    border-color: #fff;
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
    gap: 10px;
    flex-shrink: 0;
  }}

  .ps-btn {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--ps-border);
    color: var(--ps-text-bright);
    padding: 8px 18px;
    border-radius: 7px;
    font-size: 13.5px;
    font-weight: 800;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 7px;
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
    box-shadow: 0 2px 12px rgba(0, 132, 255, 0.5);
  }}
  .ps-btn-primary:hover {{
    background: var(--ps-blue-hover);
    border-color: var(--ps-blue-hover);
  }}

  /* WORKSPACE BODY (SPACIOUS WIDER SIDEBARS + DOMINANT CENTER CANVAS) */
  .ps-body {{
    display: flex;
    flex: 1;
    height: calc(100vh - 52px);
    overflow: hidden;
    position: relative;
    background: #000000;
  }}

  /* SIDEBAR PANELS (WIDER FOR MAXIMUM VISIBILITY & EASY SELECTION) */
  .ps-sidebar {{
    width: 340px;
    background: var(--ps-panel);
    display: flex;
    flex-direction: column;
    flex-shrink: 0;
    height: 100%;
    z-index: 50;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: var(--ps-border-light) var(--ps-panel);
    box-shadow: 0 0 25px rgba(0, 0, 0, 0.7);
  }}
  .ps-sidebar-left {{
    width: 340px;
    border-right: 1px solid var(--ps-border);
  }}
  .ps-sidebar-right {{
    width: 350px;
    border-left: 1px solid var(--ps-border);
  }}
  .ps-sidebar::-webkit-scrollbar {{
    width: 7px;
  }}
  .ps-sidebar::-webkit-scrollbar-thumb {{
    background: var(--ps-border-light);
    border-radius: 4px;
  }}

  /* PANEL SECTIONS - VISIBLE, SPACIOUS & HIGH CONTRAST */
  .ps-panel-section {{
    border-bottom: 1px solid var(--ps-border);
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .ps-panel-section:last-child {{
    border-bottom: none;
    padding-bottom: 35px;
  }}

  .panel-section-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #12141c;
    border: 1px solid #222533;
    border-radius: 8px;
    padding: 11px 16px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
  }}
  .panel-section-title {{
    font-weight: 800;
    font-size: 14.5px;
    color: var(--ps-text-bright);
    display: flex;
    align-items: center;
    gap: 9px;
    letter-spacing: 0.2px;
  }}

  .section-label {{
    font-size: 12px;
    color: #a0a6b8;
    font-weight: 800;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}

  /* DISCRETE CORNER ADMIN LOCK BUTTON */
  .admin-lock-btn {{
    background: transparent;
    border: 1px solid #262938;
    border-radius: 6px;
    color: var(--ps-text-muted);
    cursor: pointer;
    padding: 4px 10px;
    font-size: 14px;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }}
  .admin-lock-btn:hover {{
    background: rgba(255, 255, 255, 0.14);
    border-color: var(--ps-blue);
    color: #fff;
    transform: scale(1.08);
  }}

  /* DROP ZONES */
  .ps-dropzone {{
    border: 2px dashed var(--ps-blue);
    background: rgba(0, 132, 255, 0.08);
    border-radius: 9px;
    padding: 16px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s ease;
    display: block;
    color: #fff;
    font-weight: 800;
    font-size: 13.5px;
  }}
  .ps-dropzone:hover {{
    background: rgba(0, 132, 255, 0.2);
    border-color: #fff;
    box-shadow: 0 0 16px rgba(0, 132, 255, 0.35);
  }}
  .ps-dropzone input {{ display: none; }}

  /* GRID CARDS (FACES, TEMPLATES, EFFECTS) - WIDE & EASY TO SEE */
  .grid-cards-faces {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }}
  .grid-card {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 9px;
    padding: 9px;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.14s ease;
  }}
  .grid-card:hover {{
    border-color: var(--ps-border-light);
    transform: translateY(-2px);
    background: var(--ps-card-hover);
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5);
  }}
  .grid-card.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 132, 255, 0.22);
    box-shadow: 0 0 0 2px var(--ps-blue), 0 4px 15px rgba(0, 132, 255, 0.3);
  }}
  .grid-card img {{
    width: 100%;
    height: 125px;
    border-radius: 7px;
    object-fit: cover;
    margin-bottom: 7px;
    background: #000;
  }}
  .grid-card span {{
    font-size: 12.5px;
    font-weight: 700;
    color: var(--ps-text-bright);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  }}

  /* BUTTON GROUPS & TOGGLES */
  .btn-group {{
    display: flex;
    background: var(--ps-card);
    border-radius: 7px;
    padding: 4px;
    border: 1px solid var(--ps-border);
    gap: 4px;
    flex-wrap: wrap;
  }}
  .btn-toggle {{
    flex: 1 1 auto;
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    font-size: 12.5px;
    font-weight: 700;
    padding: 8px 12px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.12s ease;
    text-align: center;
    white-space: nowrap;
  }}
  .btn-toggle:hover {{ color: #fff; }}
  .btn-toggle.active {{
    background: var(--ps-blue);
    color: #fff;
    box-shadow: 0 2px 8px rgba(0, 132, 255, 0.4);
  }}

  /* SLIDERS */
  .slider-row {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .slider-row label {{
    font-size: 12.5px;
    color: var(--ps-text-muted);
    display: flex;
    justify-content: space-between;
    font-weight: 700;
  }}
  .slider-row label b {{
    color: var(--ps-text-bright);
    background: #171924;
    padding: 2px 7px;
    border-radius: 4px;
    border: 1px solid #232736;
  }}
  .slider-row input[type="range"] {{
    width: 100%;
    accent-color: var(--ps-blue);
    cursor: pointer;
    height: 8px;
  }}

  /* INPUTS */
  .ps-input {{
    width: 100%;
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    color: #fff;
    font-size: 14px;
    padding: 11px 15px;
    border-radius: 8px;
    outline: none;
    transition: border-color 0.15s ease;
  }}
  .ps-input:focus {{
    border-color: var(--ps-blue);
    box-shadow: 0 0 0 2px rgba(0, 132, 255, 0.3);
  }}

  /* LAYERS LIST */
  .layers-list {{
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .layer-item {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 8px;
    padding: 11px 15px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    transition: all 0.12s ease;
  }}
  .layer-item:hover {{
    border-color: var(--ps-border-light);
    background: var(--ps-card-hover);
  }}
  .layer-item.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 132, 255, 0.22);
    box-shadow: 0 0 0 1.5px var(--ps-blue);
  }}
  .layer-title {{
    font-weight: 700;
    font-size: 13.5px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 9px;
  }}
  .layer-controls {{
    display: flex;
    gap: 6px;
  }}
  .layer-btn {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    cursor: pointer;
    font-size: 16px;
    padding: 4px 7px;
    border-radius: 4px;
  }}
  .layer-btn:hover {{ color: #fff; background: rgba(255, 255, 255, 0.14); }}

  /* CENTER CANVAS VIEWPORT (DOMINANT & AUTO-FITS SCREEN) */
  .ps-canvas-viewport {{
    flex: 1;
    background-color: #030304;
    background-image: radial-gradient(circle, #1a1c24 1.2px, transparent 1.2px);
    background-size: 26px 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
    padding: 14px;
    height: 100%;
  }}

  .canvas-stage {{
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
  }}

  #mainCanvas {{
    box-shadow: 0 25px 80px rgba(0, 0, 0, 0.98), 0 0 0 1px rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    background: #000;
    display: block;
    cursor: default;
  }}

  /* FLOATING PROGRESS BAR */
  .progress-wrap {{
    position: absolute;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(14, 15, 20, 0.96);
    backdrop-filter: blur(20px);
    border: 1px solid var(--ps-border-light);
    border-radius: 8px;
    padding: 16px 24px;
    width: 380px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.9);
    z-index: 1000;
  }}
  .progress-track {{
    height: 8px;
    background: var(--ps-input);
    border-radius: 4px;
    overflow: hidden;
  }}
  .progress-bar {{
    height: 100%;
    background: var(--ps-blue);
    width: 0%;
    transition: width 0.1s linear;
  }}
  .progress-text {{
    font-size: 13px;
    color: var(--ps-text-bright);
    text-align: center;
    margin-top: 8px;
    font-weight: 700;
  }}

  /* ADMIN MODAL */
  .admin-modal-backdrop {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(0, 0, 0, 0.82);
    backdrop-filter: blur(8px);
    display: none;
    align-items: center;
    justify-content: center;
    z-index: 2000;
  }}
  .admin-modal {{
    width: 440px;
    max-width: 92vw;
    background: var(--ps-panel);
    border: 1px solid var(--ps-border-light);
    border-radius: 8px;
    box-shadow: 0 30px 70px rgba(0,0,0,0.95);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }}
  .admin-modal-header {{
    background: var(--ps-topbar);
    border-bottom: 1px solid var(--ps-border);
    padding: 14px 18px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .admin-modal-title {{
    font-weight: 800;
    font-size: 15px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .admin-modal-close {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    font-size: 18px;
    cursor: pointer;
  }}
  .admin-modal-close:hover {{ color: #fff; }}
  .admin-modal-body {{
    padding: 18px;
    display: flex;
    flex-direction: column;
    gap: 14px;
    max-height: 70vh;
    overflow-y: auto;
  }}

  /* RESPONSIVE SCALING */
  @media (max-width: 1250px) {{
    .ps-sidebar-left {{
      width: 290px;
    }}
    .ps-sidebar-right {{
      width: 300px;
    }}
  }}
  @media (max-width: 860px) {{
    .ps-title, .ps-doc-badge {{
      display: none;
    }}
    .ps-body {{
      flex-direction: column;
      overflow-y: auto;
    }}
    .ps-sidebar {{
      width: 100% !important;
      height: auto;
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
      <span class="ps-title">Murad Photoshop Studio</span>
      <span class="ps-doc-badge" id="docSizeBadge">800 × 800 px</span>
    </div>

    <!-- CONTEXT TOOL OPTIONS -->
    <div class="ps-tool-options" id="toolOptions">
      <button id="fitScreenBtn" class="ps-opt-btn" title="Auto Fit Canvas to Viewport">🔍 Fit Screen</button>
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

  <!-- BODY (LEFT MENUS + DOMINANT CENTER CANVAS + RIGHT MENUS) -->
  <div class="ps-body">

    <!-- LEFT SIDEBAR: FACES & BACKDROP (OPEN BY DEFAULT) -->
    <aside class="ps-sidebar ps-sidebar-left" id="sidebarLeft">

      <!-- 1. SECTION: MURAD FACES -->
      <div class="ps-panel-section" id="section-faces">
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
          <span class="section-label">Default Faces:</span>
          <button id="addFaceBtn" class="ps-opt-btn" style="background:var(--ps-blue); border-color:var(--ps-blue); color:#fff; padding:5px 12px;">➕ Add Face</button>
        </div>
        <div class="grid-cards-faces" id="facesGrid" style="max-height:270px; overflow-y:auto;"></div>

        <div style="display:flex; flex-direction:column; gap:6px; margin-top:4px;">
          <span class="section-label">Cutout Shape:</span>
          <div class="btn-group" id="maskGroup">
            <button class="btn-toggle active" data-mask="square">Full Frame</button>
            <button class="btn-toggle" data-mask="circle">Sticker Circle</button>
            <button class="btn-toggle" data-mask="oval">Oval</button>
          </div>
        </div>

        <div class="slider-row">
          <label>Face Scale: <b id="faceScaleVal">100%</b></label>
          <input type="range" id="faceScaleSlider" min="0.1" max="3.0" step="0.05" value="1.0">
        </div>
        <div class="slider-row">
          <label>Face Opacity: <b id="faceOpacityVal">100%</b></label>
          <input type="range" id="faceOpacitySlider" min="0.1" max="1.0" step="0.05" value="1.0">
        </div>
      </div>

      <!-- 2. SECTION: BACKDROP & TEMPLATES -->
      <div class="ps-panel-section" id="section-bg">
        <div class="panel-section-header">
          <span class="panel-section-title">🖼️ Backdrop & Templates</span>
        </div>

        <label class="ps-dropzone">
          <span>📁 Upload Image, Meme or Animated GIF</span>
          <input type="file" id="bgFileInput" accept="image/*,.gif">
        </label>

        <div style="display:flex; flex-direction:column; gap:6px;">
          <span class="section-label">Canvas Format:</span>
          <div class="btn-group" id="canvasSizeGroup">
            <button class="btn-toggle active" data-size="true_size">📐 True Size</button>
            <button class="btn-toggle" data-size="square">⏹️ 1:1</button>
            <button class="btn-toggle" data-size="landscape">🖼️ 16:9</button>
            <button class="btn-toggle" data-size="portrait">📱 9:16</button>
          </div>
        </div>

        <span class="section-label">Popular Meme Templates:</span>
        <div class="grid-cards-faces" id="bgPresetsRow" style="max-height:230px; overflow-y:auto;"></div>
      </div>

    </aside>

    <!-- CENTER CANVAS VIEWPORT (MASSIVE & AUTO-FITS SCREEN) -->
    <main class="ps-canvas-viewport" id="canvasViewport">
      <div class="canvas-stage">
        <canvas id="mainCanvas" width="800" height="800"></canvas>
      </div>
    </main>

    <!-- RIGHT SIDEBAR: TEXT, STICKERS, FX & LAYERS (OPEN BY DEFAULT) -->
    <aside class="ps-sidebar ps-sidebar-right" id="sidebarRight">

      <!-- 3. SECTION: MEME TEXT -->
      <div class="ps-panel-section" id="section-text">
        <div class="panel-section-header">
          <span class="panel-section-title">✍️ Meme Text</span>
        </div>

        <div style="display:flex; gap:8px;">
          <button id="addTopTextBtn" class="ps-opt-btn" style="flex:1; padding:9px; justify-content:center;">➕ Top</button>
          <button id="addBottomTextBtn" class="ps-opt-btn" style="flex:1; padding:9px; justify-content:center;">➕ Bottom</button>
          <button id="addCustomTextBtn" class="ps-opt-btn" style="flex:1; padding:9px; justify-content:center; background:var(--ps-blue); color:#fff; border-color:var(--ps-blue);">➕ Custom</button>
        </div>

        <div id="textEditorBox" style="display:flex; flex-direction:column; gap:12px;">
          <input type="text" id="activeTextInput" class="ps-input" placeholder="Click + Top/Bottom or type meme text...">

          <div class="slider-row">
            <label>Font Size: <b id="textSizeVal">48px</b></label>
            <input type="range" id="textSizeSlider" min="16" max="130" step="2" value="48">
          </div>

          <div style="display:flex; flex-direction:column; gap:6px;">
            <span class="section-label">Text Color:</span>
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

      <!-- 4. SECTION: CUSTOM STICKERS -->
      <div class="ps-panel-section" id="section-stickers">
        <div class="panel-section-header">
          <span class="panel-section-title">🎀 Custom Stickers</span>
        </div>

        <label class="ps-dropzone">
          <span>📁 Upload Custom PNG / Sticker</span>
          <input type="file" id="accFileInput" accept="image/*,.gif">
        </label>

        <div id="accEditorBox" style="display:none; flex-direction:column; gap:10px;">
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

      <!-- 5. SECTION: ANIMATION FX -->
      <div class="ps-panel-section" id="section-anim">
        <div class="panel-section-header">
          <span class="panel-section-title">✨ Discord GIF Effects</span>
        </div>

        <div class="grid-cards-faces" id="animGrid" style="grid-template-columns:repeat(3, 1fr); gap:8px;">
          <div class="grid-card active" data-anim="none"><span style="font-size:24px;">🖼️</span><span>Still</span></div>
          <div class="grid-card" data-anim="bob"><span style="font-size:24px;">🕺</span><span>Bob</span></div>
          <div class="grid-card" data-anim="shake"><span style="font-size:24px;">💢</span><span>Shake</span></div>
          <div class="grid-card" data-anim="spin"><span style="font-size:24px;">🌀</span><span>Spin 360°</span></div>
          <div class="grid-card" data-anim="petpet"><span style="font-size:24px;">👋</span><span>Petpet</span></div>
          <div class="grid-card" data-anim="zoom"><span style="font-size:24px;">💥</span><span>Bass Pulse</span></div>
          <div class="grid-card" data-anim="pulse"><span style="font-size:24px;">💓</span><span>Heartbeat</span></div>
          <div class="grid-card" data-anim="wobble"><span style="font-size:24px;">🌊</span><span>Wobble</span></div>
          <div class="grid-card" data-anim="disco"><span style="font-size:24px;">🪩</span><span>Disco</span></div>
        </div>
      </div>

      <!-- 6. SECTION: ACTIVE LAYERS -->
      <div class="ps-panel-section" id="section-layers">
        <div class="panel-section-header">
          <span class="panel-section-title">📑 Active Layers</span>
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
        <div style="text-align:center; padding: 14px 0;">
          <div style="font-size:38px; margin-bottom:10px;">🔒</div>
          <div style="font-weight:800; font-size:15px; color:#fff; margin-bottom:5px;">Enter Admin Password</div>
          <div style="font-size:12.5px; color:var(--ps-text-muted); margin-bottom:14px;">Manage default catalog faces or push new ones to GitHub.</div>
          <input type="password" id="adminPwdInput" class="ps-input" placeholder="Password..." style="margin-bottom:8px; text-align:center; width:240px; margin:0 auto 10px auto;">
          <div id="adminAuthError" style="color:var(--ps-danger); font-size:12px; display:none; margin-bottom:8px;">❌ Incorrect Admin Password</div>
          <button id="adminUnlockBtn" class="ps-btn ps-btn-primary" style="width:240px; margin:0 auto; justify-content:center;">Unlock</button>
        </div>
      </div>

      <!-- STEP 2: CATALOG MANAGEMENT -->
      <div class="admin-modal-body" id="adminManageBody" style="display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="color:var(--ps-green); font-weight:800; font-size:12.5px;">✅ Admin Access Granted</span>
          <button id="adminLockOutBtn" class="ps-opt-btn" style="font-size:11px;">Lock</button>
        </div>

        <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
          <span style="font-size:12px; font-weight:800; color:#fff;">➕ ADD NEW FACE TO CATALOG:</span>
          <div style="display:flex; flex-direction:column; gap:7px; margin-top:7px;">
            <input type="text" id="adminNewFaceName" class="ps-input" placeholder="Face Name & Emoji (e.g. Party Murad 🎉)">
            <input type="file" id="adminNewFaceFile" accept="image/*" class="ps-input" style="padding:6px;">
            <button id="adminUploadBtn" class="ps-btn ps-btn-primary" style="justify-content:center;">🚀 Push to Catalog</button>
            <div id="adminUploadStatus" style="font-size:11.5px; text-align:center;"></div>
          </div>
        </div>

        <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
          <span style="font-size:12px; font-weight:800; color:#fff;">🗑️ MANAGE DEFAULT FACES:</span>
          <div id="adminFacesCatalogList" style="display:flex; flex-direction:column; gap:5px; max-height:200px; overflow-y:auto; margin-top:7px;"></div>
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

// DEFAULT STATE: CLEAN CANVAS WITHOUT DEFAULT "WHEN MURAD" / "APPROVES THE CODE" TEXT LAYERS
const state = {{
  facesOnCanvas: [makeFaceLayer(0, 0, -50, 1.0)],
  selectedFaceIdx: 0,

  bgType: 'template',
  bgTemplateId: 'suit',
  bgCustomImg: null,
  bgIsGif: false,
  bgGifFrames: [],
  bgGifIndex: 0,

  canvasSizeMode: 'true_size',

  texts: [],
  selectedTextIdx: -1,

  accessoriesOnCanvas: [],
  selectedAccIdx: -1,

  animation: 'none',

  activeTransformTarget: {{ type: 'face', idx: 0 }},
  dragTarget: null
}};

const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');
canvas.width = 800;
canvas.height = 800;

// Preload face images
const loadedFaces = {{}};
faces.forEach((f, idx) => {{
  const img = new Image();
  img.src = f.src;
  img.onload = () => {{
    render();
  }};
  loadedFaces[idx] = img;
}});

// Preload template images
const loadedTemplates = {{}};
templates.forEach(t => {{
  const img = new Image();
  img.src = t.src;
  img.onload = () => {{
    render();
  }};
  loadedTemplates[t.id] = img;
}});

// --- AUTO FIT CANVAS TO SCREEN VIEWPORT ---
function fitCanvasToScreen() {{
  const vp = document.getElementById('canvasViewport');
  if (!vp || !canvas) return;
  const pad = 24;
  const availW = Math.max(280, vp.clientWidth - pad);
  const availH = Math.max(280, vp.clientHeight - pad);
  const aspect = (canvas.width || 800) / (canvas.height || 800);

  let w = availW;
  let h = w / aspect;
  if (h > availH) {{
    h = availH;
    w = h * aspect;
  }}
  canvas.style.width = Math.round(w) + 'px';
  canvas.style.height = Math.round(h) + 'px';
}}
window.addEventListener('resize', fitCanvasToScreen);

// --- ACTIVE LAYER GETTER ---
function getActiveLayerData() {{
  const t = state.activeTransformTarget;
  if (!t) return null;
  if (t.type === 'face' && state.facesOnCanvas[t.idx]) {{
    const face = state.facesOnCanvas[t.idx];
    let img = face.customImg || loadedFaces[face.faceIndex];
    const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
    const baseW = 200;
    const baseH = 200 * aspect;
    const hw = (baseW * face.scale) / 2;
    const hh = (baseH * face.scale) / 2;
    return {{
      type: 'face',
      idx: t.idx,
      obj: face,
      cx: canvas.width / 2 + face.x,
      cy: canvas.height / 2 + face.y,
      hw: hw,
      hh: hh,
      rotation: face.rotation || 0,
      scale: face.scale || 1.0
    }};
  }}
  if (t.type === 'acc' && state.accessoriesOnCanvas[t.idx]) {{
    const acc = state.accessoriesOnCanvas[t.idx];
    const aspect = (acc.img && acc.img.naturalHeight) ? (acc.img.naturalHeight / acc.img.naturalWidth) : 1.0;
    const baseW = 180;
    const baseH = 180 * aspect;
    const hw = (baseW * acc.scale) / 2;
    const hh = (baseH * acc.scale) / 2;
    return {{
      type: 'acc',
      idx: t.idx,
      obj: acc,
      cx: canvas.width / 2 + acc.x,
      cy: canvas.height / 2 + acc.y,
      hw: hw,
      hh: hh,
      rotation: acc.rotation || 0,
      scale: acc.scale || 1.0
    }};
  }}
  if (t.type === 'text' && state.texts[t.idx]) {{
    const txt = state.texts[t.idx];
    ctx.font = '900 ' + txt.size + 'px Impact, sans-serif';
    const metrics = ctx.measureText(txt.text || ' ');
    const bw = metrics.width + 32;
    const bh = txt.size + 20;
    const hw = bw / 2;
    const hh = bh / 2;
    return {{
      type: 'text',
      idx: t.idx,
      obj: txt,
      cx: canvas.width / 2 + txt.x,
      cy: canvas.height / 2 + txt.y,
      hw: hw,
      hh: hh,
      rotation: txt.rotation || 0,
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

  // 1. Rotation handle: at (0, -hh - 32)
  const rotDist = Math.hypot(lx - 0, ly - (-hh - 32));
  if (rotDist <= 22) {{
    return 'rot';
  }}

  // 2. Corner scale handles: tl, tr, bl, br
  const corners = [
    {{ name: 'tl', x: -hw, y: -hh }},
    {{ name: 'tr', x: hw, y: -hh }},
    {{ name: 'bl', x: -hw, y: hh }},
    {{ name: 'br', x: hw, y: hh }}
  ];
  for (let c of corners) {{
    if (Math.abs(lx - c.x) <= 18 && Math.abs(ly - c.y) <= 18) {{
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

  // Test faces from top to bottom
  for (let i = state.facesOnCanvas.length - 1; i >= 0; i--) {{
    const f = state.facesOnCanvas[i];
    let img = f.customImg || loadedFaces[f.faceIndex];
    const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
    const hw = (200 * f.scale) / 2;
    const hh = (200 * aspect * f.scale) / 2;
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
    const hw = (180 * a.scale) / 2;
    const hh = (180 * aspect * a.scale) / 2;
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
    const hw = (metrics.width + 32) / 2;
    const hh = (t.size + 20) / 2;
    const cx = canvas.width / 2 + t.x;
    const cy = canvas.height / 2 + t.y;
    const {{ lx, ly }} = toLocal(mx, my, cx, cy, t.rotation || 0);
    if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {{
      return {{ handle: 'body', layer: {{ type: 'text', idx: i }} }};
    }}
  }}

  return null;
}}

// --- RENDER CANVAS (LARGE & CRISP RESOLUTION) ---
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

  // High-def canvas resolution
  let cw = 800, ch = 800;
  if (state.canvasSizeMode === 'square') {{
    cw = 800; ch = 800;
  }} else if (state.canvasSizeMode === 'landscape') {{
    cw = 960; ch = 540;
  }} else if (state.canvasSizeMode === 'portrait') {{
    cw = 540; ch = 960;
  }} else if (state.canvasSizeMode === 'true_size' && bgImg && bgImg.naturalWidth) {{
    const maxDim = 1000;
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
    fitCanvasToScreen();
  }}

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  // 1. Draw Background
  if (bgImg) {{
    ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);
  }} else {{
    ctx.fillStyle = '#060608';
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
    const baseW = 200;
    const baseH = 200 * aspect;
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
    const baseW = 180;
    const baseH = 180 * aspect;
    const w = baseW * acc.scale;
    const h = baseH * acc.scale;

    ctx.drawImage(acc.img, -w / 2, -h / 2, w, h);
    ctx.restore();
  }});

  // 4. Draw Meme Text (if any)
  state.texts.forEach((t, idx) => {{
    ctx.save();
    const cx = canvas.width / 2 + t.x;
    const cy = canvas.height / 2 + t.y;
    ctx.translate(cx, cy);
    ctx.rotate((t.rotation * Math.PI) / 180);

    ctx.font = '900 ' + t.size + 'px Impact, -apple-system, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = Math.max(5, Math.round(t.size / 6.5));
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
    ctx.strokeStyle = '#0084ff';
    ctx.lineWidth = 2.5;
    ctx.setLineDash([7, 6]);
    ctx.strokeRect(-hw, -hh, hw * 2, hh * 2);

    // Stem line to rotation handle
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(0, -hh);
    ctx.lineTo(0, -hh - 32);
    ctx.stroke();

    // Top circular rotation handle
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#0084ff';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.arc(0, -hh - 32, 8, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // 4 Corner square handles
    const corners = [
      [-hw, -hh],
      [hw, -hh],
      [-hw, hh],
      [hw, hh]
    ];
    corners.forEach(([kx, ky]) => {{
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#0084ff';
      ctx.lineWidth = 2.5;
      ctx.fillRect(kx - 6, ky - 6, 12, 12);
      ctx.strokeRect(kx - 6, ky - 6, 12, 12);
    }});

    ctx.restore();
  }}

  updateTopbarToolOptions();
}}

// Update context options in topbar
function updateTopbarToolOptions() {{
  const active = getActiveLayerData();
  const nameBadge = document.getElementById('optLayerName');
  const actionGroup = document.getElementById('optActionGroup');
  const scaleVal = document.getElementById('optScaleVal');
  const rotVal = document.getElementById('optRotVal');

  if (!active) {{
    nameBadge.innerText = 'No layer selected';
    actionGroup.style.display = 'none';
    return;
  }}

  actionGroup.style.display = 'inline-flex';
  let title = 'Layer';
  if (active.type === 'face') {{
    const f = faces[active.obj.faceIndex];
    title = f ? f.name : 'Custom Face';
    scaleVal.innerText = Math.round(active.obj.scale * 100) + '%';
    rotVal.innerText = Math.round(active.obj.rotation) + '°';
  }} else if (active.type === 'acc') {{
    title = 'Sticker / Acc';
    scaleVal.innerText = Math.round(active.obj.scale * 100) + '%';
    rotVal.innerText = Math.round(active.obj.rotation) + '°';
  }} else if (active.type === 'text') {{
    title = '"' + active.obj.text.substring(0, 16) + '"';
    scaleVal.innerText = active.obj.size + 'px';
    rotVal.innerText = Math.round(active.obj.rotation) + '°';
  }}
  nameBadge.innerText = title;
}}

// --- INTERACTIVE DRAG & FREE TRANSFORM EVENTS ---
function initCanvasEvents() {{
  let isDragging = false;
  let dragHandle = null;
  let startX = 0, startY = 0;
  let origObjState = {{}};

  function onPointerDown(e) {{
    const {{ x: mx, y: my }} = getCanvasPointer(e);
    const hit = findLayerAt(mx, my);

    if (hit) {{
      isDragging = true;
      dragHandle = hit.handle;
      startX = mx;
      startY = my;

      if (hit.layer.type === 'face') {{
        state.activeTransformTarget = {{ type: 'face', idx: hit.layer.idx }};
        state.selectedFaceIdx = hit.layer.idx;
        const obj = state.facesOnCanvas[hit.layer.idx];
        origObjState = {{ x: obj.x, y: obj.y, scale: obj.scale, rotation: obj.rotation }};
      }} else if (hit.layer.type === 'acc') {{
        state.activeTransformTarget = {{ type: 'acc', idx: hit.layer.idx }};
        state.selectedAccIdx = hit.layer.idx;
        const obj = state.accessoriesOnCanvas[hit.layer.idx];
        origObjState = {{ x: obj.x, y: obj.y, scale: obj.scale, rotation: obj.rotation }};
      }} else if (hit.layer.type === 'text') {{
        state.activeTransformTarget = {{ type: 'text', idx: hit.layer.idx }};
        state.selectedTextIdx = hit.layer.idx;
        const obj = state.texts[hit.layer.idx];
        origObjState = {{ x: obj.x, y: obj.y, size: obj.size, rotation: obj.rotation }};
        document.getElementById('activeTextInput').value = obj.text;
      }}

      render();
      syncLayersUI();
    }} else {{
      state.activeTransformTarget = null;
      render();
      syncLayersUI();
    }}
  }}

  function onPointerMove(e) {{
    const {{ x: mx, y: my }} = getCanvasPointer(e);

    if (!isDragging) {{
      const hit = findLayerAt(mx, my);
      if (!hit) {{
        canvas.style.cursor = 'default';
      }} else if (hit.handle === 'rot') {{
        canvas.style.cursor = 'grab';
      }} else if (hit.handle === 'tl' || hit.handle === 'br') {{
        canvas.style.cursor = 'nwse-resize';
      }} else if (hit.handle === 'tr' || hit.handle === 'bl') {{
        canvas.style.cursor = 'nesw-resize';
      }} else {{
        canvas.style.cursor = 'move';
      }}
      return;
    }}

    const active = getActiveLayerData();
    if (!active) return;

    if (dragHandle === 'body') {{
      const dx = mx - startX;
      const dy = my - startY;
      active.obj.x = origObjState.x + dx;
      active.obj.y = origObjState.y + dy;
      render();
    }} else if (dragHandle === 'rot') {{
      const rad = Math.atan2(my - active.cy, mx - active.cx);
      let deg = (rad * 180) / Math.PI + 90;
      while (deg < -180) deg += 360;
      while (deg > 180) deg -= 360;
      active.obj.rotation = Math.round(deg);
      render();
    }} else if (dragHandle) {{
      const initialDist = Math.hypot(startX - active.cx, startY - active.cy);
      const currentDist = Math.hypot(mx - active.cx, my - active.cy);
      const factor = currentDist / Math.max(initialDist, 1);
      
      if (active.type === 'text') {{
        active.obj.size = Math.max(16, Math.min(130, Math.round(origObjState.size * factor)));
      }} else {{
        active.obj.scale = Math.max(0.15, Math.min(3.5, Number((origObjState.scale * factor).toFixed(2))));
      }}
      render();
    }}
  }}

  function onPointerUp() {{
    isDragging = false;
    dragHandle = null;
    canvas.style.cursor = 'default';
  }}

  canvas.addEventListener('mousedown', onPointerDown);
  window.addEventListener('mousemove', onPointerMove);
  window.addEventListener('mouseup', onPointerUp);

  canvas.addEventListener('touchstart', (e) => {{
    if (e.touches.length === 1) onPointerDown(e);
  }}, {{ passive: false }});
  window.addEventListener('touchmove', (e) => {{
    if (isDragging && e.touches.length === 1) onPointerMove(e);
  }}, {{ passive: false }});
  window.addEventListener('touchend', onPointerUp);

  // Wheel to scale active layer
  canvas.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const active = getActiveLayerData();
    if (!active) return;
    const delta = e.deltaY < 0 ? 0.05 : -0.05;
    if (active.type === 'text') {{
      active.obj.size = Math.max(16, Math.min(130, active.obj.size + (delta > 0 ? 3 : -3)));
    }} else {{
      active.obj.scale = Math.max(0.2, Math.min(3.5, Number((active.obj.scale + delta).toFixed(2))));
    }}
    render();
  }}, {{ passive: false }});
}}

// --- POPULATE SIDEBARS & EVENTS ---
function initUIEvents() {{
  // 1. Populate Faces Grid
  const facesGrid = document.getElementById('facesGrid');
  facesGrid.innerHTML = '';
  faces.forEach((f, idx) => {{
    const card = document.createElement('div');
    card.className = 'grid-card' + (idx === 0 ? ' active' : '');
    card.innerHTML = `<img src="${{f.src}}" alt="${{f.name}}"><span>${{f.name}}</span>`;
    card.onclick = () => {{
      document.querySelectorAll('#facesGrid .grid-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      const active = getActiveLayerData();
      if (active && active.type === 'face') {{
        active.obj.faceIndex = idx;
        active.obj.customImg = null;
      }} else {{
        state.facesOnCanvas.push(makeFaceLayer(idx, 0, 0, 1.0));
        state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
      }}
      render();
      syncLayersUI();
    }};
    facesGrid.appendChild(card);
  }});

  // Add Face Button
  document.getElementById('addFaceBtn').onclick = () => {{
    state.facesOnCanvas.push(makeFaceLayer(0, Math.floor((Math.random() - 0.5) * 80), Math.floor((Math.random() - 0.5) * 80), 1.0));
    state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
    render();
    syncLayersUI();
  }};

  // Custom Face Upload
  document.getElementById('faceFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {{
      const img = new Image();
      img.src = ev.target.result;
      img.onload = () => {{
        const newLayer = makeFaceLayer(0, 0, 0, 1.0);
        newLayer.customImg = img;
        state.facesOnCanvas.push(newLayer);
        state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
        render();
        syncLayersUI();
      }};
    }};
    reader.readAsDataURL(file);
  }};

  // Mask Shape Toggles
  document.querySelectorAll('#maskGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const active = getActiveLayerData();
      if (active && active.type === 'face') {{
        active.obj.maskShape = btn.dataset.mask;
        render();
      }}
    }};
  }});

  // Face Sliders
  document.getElementById('faceScaleSlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('faceScaleVal').innerText = Math.round(val * 100) + '%';
    const active = getActiveLayerData();
    if (active && active.type === 'face') {{
      active.obj.scale = val;
      render();
    }}
  }};
  document.getElementById('faceOpacitySlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('faceOpacityVal').innerText = Math.round(val * 100) + '%';
    const active = getActiveLayerData();
    if (active && active.type === 'face') {{
      active.obj.opacity = val;
      render();
    }}
  }};

  // 2. Populate Templates Grid
  const bgGrid = document.getElementById('bgPresetsRow');
  bgGrid.innerHTML = '';
  templates.forEach(t => {{
    const card = document.createElement('div');
    card.className = 'grid-card' + (t.id === 'suit' ? ' active' : '');
    card.innerHTML = `<img src="${{t.src}}" alt="${{t.name}}"><span>${{t.name}}</span>`;
    card.onclick = () => {{
      document.querySelectorAll('#bgPresetsRow .grid-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.bgType = 'template';
      state.bgTemplateId = t.id;
      state.bgCustomImg = null;
      state.bgIsGif = false;
      render();
    }};
    bgGrid.appendChild(card);
  }});

  // Backdrop Custom File Upload
  document.getElementById('bgFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;

    if (file.name.toLowerCase().endsWith('.gif')) {{
      const reader = new FileReader();
      reader.onload = (ev) => {{
        try {{
          const parsed = window.gifuct ? window.gifuct.parseGIF(ev.target.result) : null;
          const frames = parsed ? window.gifuct.decompressFrames(parsed, true) : null;
          if (frames && frames.length > 0) {{
            const tmpCanv = document.createElement('canvas');
            const tmpCtx = tmpCanv.getContext('2d');
            tmpCanv.width = frames[0].dims.width;
            tmpCanv.height = frames[0].dims.height;

            const loadedFrames = [];
            frames.forEach(f => {{
              const fData = tmpCtx.createImageData(f.dims.width, f.dims.height);
              fData.data.set(f.patch);
              tmpCtx.putImageData(fData, f.dims.left, f.dims.top);
              const img = new Image();
              img.src = tmpCanv.toDataURL();
              loadedFrames.push(img);
            }});

            state.bgIsGif = true;
            state.bgGifFrames = loadedFrames;
            state.bgGifIndex = 0;
            state.bgType = 'gif';
            render();
            return;
          }}
        }} catch (err) {{
          console.error(err);
        }}
      }};
      reader.readAsArrayBuffer(file);
    }} else {{
      const reader = new FileReader();
      reader.onload = (ev) => {{
        const img = new Image();
        img.src = ev.target.result;
        img.onload = () => {{
          state.bgType = 'custom';
          state.bgCustomImg = img;
          state.bgIsGif = false;
          render();
        }};
      }};
      reader.readAsDataURL(file);
    }}
  }};

  // Canvas Size Mode Toggles
  document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.canvasSizeMode = btn.dataset.size;
      render();
    }};
  }});

  // Fit Screen Button in topbar
  document.getElementById('fitScreenBtn').onclick = () => {{
    fitCanvasToScreen();
  }};

  // 3. Text Controls (Top, Bottom, Custom)
  document.getElementById('addTopTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'TOP TEXT', x: 0, y: -Math.round(canvas.height * 0.35), size: 52, color: '#ffffff', rotation: 0 }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'TOP TEXT';
    render();
    syncLayersUI();
  }};
  document.getElementById('addBottomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'BOTTOM TEXT', x: 0, y: Math.round(canvas.height * 0.35), size: 52, color: '#ffffff', rotation: 0 }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'BOTTOM TEXT';
    render();
    syncLayersUI();
  }};
  document.getElementById('addCustomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'YOUR TEXT', x: 0, y: 0, size: 52, color: '#ffffff', rotation: 0 }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'YOUR TEXT';
    render();
    syncLayersUI();
  }};

  const textInput = document.getElementById('activeTextInput');
  textInput.oninput = (e) => {{
    let active = getActiveLayerData();
    if (!active || active.type !== 'text') {{
      if (e.target.value.trim() !== '') {{
        state.texts.push({{
          id: 't_' + Date.now(),
          text: e.target.value.toUpperCase(),
          x: 0,
          y: 0,
          size: 52,
          color: '#ffffff',
          rotation: 0
        }});
        state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
        state.selectedTextIdx = state.texts.length - 1;
        render();
        syncLayersUI();
      }}
      return;
    }}
    active.obj.text = e.target.value.toUpperCase();
    render();
    syncLayersUI();
  }};

  document.getElementById('textSizeSlider').oninput = (e) => {{
    const val = parseInt(e.target.value);
    document.getElementById('textSizeVal').innerText = val + 'px';
    const active = getActiveLayerData();
    if (active && active.type === 'text') {{
      active.obj.size = val;
      render();
    }}
  }};

  document.querySelectorAll('#textColorGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#textColorGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const active = getActiveLayerData();
      if (active && active.type === 'text') {{
        active.obj.color = btn.dataset.color;
        render();
      }}
    }};
  }});

  // 4. Custom Sticker Upload
  document.getElementById('accFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {{
      const img = new Image();
      img.src = ev.target.result;
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
        state.activeTransformTarget = {{ type: 'acc', idx: state.accessoriesOnCanvas.length - 1 }};
        render();
        syncLayersUI();
      }};
    }};
    reader.readAsDataURL(file);
  }};

  // 5. Animation Grid
  document.querySelectorAll('#animGrid .grid-card').forEach(card => {{
    card.onclick = () => {{
      document.querySelectorAll('#animGrid .grid-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.animation = card.dataset.anim;
      render();
    }};
  }});

  // 6. Topbar Context Tool Actions (Flip, Center, Delete)
  document.getElementById('optFlipBtn').onclick = () => {{
    const active = getActiveLayerData();
    if (!active) return;
    if (active.type === 'face' || active.type === 'acc') {{
      active.obj.flipH = (active.obj.flipH || 1) * -1;
      render();
    }}
  }};

  document.getElementById('optCenterBtn').onclick = () => {{
    const active = getActiveLayerData();
    if (!active) return;
    active.obj.x = 0;
    active.obj.y = 0;
    render();
  }};

  document.getElementById('optDeleteBtn').onclick = () => {{
    const active = getActiveLayerData();
    if (!active) return;
    if (active.type === 'face') {{
      state.facesOnCanvas.splice(active.idx, 1);
    }} else if (active.type === 'acc') {{
      state.accessoriesOnCanvas.splice(active.idx, 1);
    }} else if (active.type === 'text') {{
      state.texts.splice(active.idx, 1);
      document.getElementById('activeTextInput').value = '';
    }}
    state.activeTransformTarget = null;
    render();
    syncLayersUI();
  }};

  // 7. Topbar Export Buttons
  document.getElementById('btnExportPng').onclick = exportPng;
  document.getElementById('btnExportGif').onclick = exportGif;
  document.getElementById('btnCopyDiscord').onclick = copyToClipboard;

  // 8. Admin Modal
  const adminModal = document.getElementById('adminModal');
  const adminLockBtn = document.getElementById('adminLockBtn');
  const adminModalClose = document.getElementById('adminModalClose');
  const adminUnlockBtn = document.getElementById('adminUnlockBtn');
  const adminPwdInput = document.getElementById('adminPwdInput');
  const adminAuthError = document.getElementById('adminAuthError');
  const adminAuthBody = document.getElementById('adminAuthBody');
  const adminManageBody = document.getElementById('adminManageBody');
  const adminLockOutBtn = document.getElementById('adminLockOutBtn');

  function openAdminModal() {{
    adminModal.style.display = 'flex';
    adminAuthError.style.display = 'none';
    adminPwdInput.value = '';
    adminPwdInput.focus();
  }}

  adminLockBtn.onclick = openAdminModal;
  adminModalClose.onclick = () => {{ adminModal.style.display = 'none'; }};

  adminUnlockBtn.onclick = () => {{
    if (adminPwdInput.value === EXPECTED_ADMIN_PWD) {{
      adminAuthBody.style.display = 'none';
      adminManageBody.style.display = 'flex';
      renderAdminCatalog();
    }} else {{
      adminAuthError.style.display = 'block';
    }}
  }};

  adminLockOutBtn.onclick = () => {{
    adminManageBody.style.display = 'none';
    adminAuthBody.style.display = 'block';
    adminModal.style.display = 'none';
  }};

  // Secret Hotkey Ctrl+Shift+A
  window.addEventListener('keydown', (e) => {{
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'a') {{
      openAdminModal();
    }}
  }});

  // Admin upload to GitHub
  document.getElementById('adminUploadBtn').onclick = () => {{
    const name = document.getElementById('adminNewFaceName').value.trim();
    const file = document.getElementById('adminNewFaceFile').files[0];
    const status = document.getElementById('adminUploadStatus');

    if (!name || !file) {{
      status.style.color = 'var(--ps-danger)';
      status.innerText = '⚠️ Please enter a face name and select an image.';
      return;
    }}

    status.style.color = 'var(--ps-blue)';
    status.innerText = '⏳ Encoding image...';

    const reader = new FileReader();
    reader.onload = (ev) => {{
      const b64 = ev.target.result;
      const imgId = name.toLowerCase().replace(/[^a-z0-9]/g, '_');
      const filename = imgId + '.png';

      faces.push({{
        id: imgId,
        name: name,
        file: filename,
        src: b64
      }});

      const idx = faces.length - 1;
      const newImg = new Image();
      newImg.src = b64;
      loadedFaces[idx] = newImg;

      initUIEvents();
      renderAdminCatalog();

      status.style.color = 'var(--ps-green)';
      status.innerText = '✅ Face added locally!';

      if (GITHUB_TOKEN) {{
        status.innerText = '🚀 Syncing to GitHub repo...';
        syncFaceToGitHub(name, filename, b64)
          .then(() => {{
            status.innerText = '🎉 Successfully pushed to GitHub repo!';
          }})
          .catch(err => {{
            status.style.color = 'var(--ps-yellow)';
            status.innerText = '⚠️ Local added. GitHub sync error: ' + err.message;
          }});
      }}
    }};
    reader.readAsDataURL(file);
  }};

  fitCanvasToScreen();
  syncLayersUI();
}}

// Sync Admin Catalog List
function renderAdminCatalog() {{
  const list = document.getElementById('adminFacesCatalogList');
  if (!list) return;
  list.innerHTML = '';
  faces.forEach((f, idx) => {{
    const row = document.createElement('div');
    row.style = 'display:flex; justify-content:space-between; align-items:center; background:#111217; padding:8px 12px; border-radius:6px; border:1px solid #1f2028;';
    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px;">
        <img src="${{f.src}}" style="width:34px; height:34px; border-radius:5px; object-fit:cover;">
        <span style="font-size:13px; font-weight:700; color:#fff;">${{f.name}}</span>
      </div>
      <button class="ps-opt-btn danger" style="padding:4px 10px; font-size:11.5px;" onclick="deleteAdminFace(${{idx}})">Remove</button>
    `;
    list.appendChild(row);
  }});
}}

window.deleteAdminFace = function(idx) {{
  if (confirm('Remove ' + faces[idx].name + ' from catalog?')) {{
    faces.splice(idx, 1);
    delete loadedFaces[idx];
    initUIEvents();
    renderAdminCatalog();
    render();
  }}
}};

// GitHub API face sync helper
async function syncFaceToGitHub(faceName, filename, base64Data) {{
  const cleanB64 = base64Data.split(',')[1];
  const repo = '3bood011/Muradeditor';
  const branch = 'main';

  // 1. Upload image file
  const filePath = 'assets/' + filename;
  const putUrl = `https://api.github.com/repos/${{repo}}/contents/${{filePath}}`;
  
  await fetch(putUrl, {{
    method: 'PUT',
    headers: {{
      'Authorization': 'token ' + GITHUB_TOKEN,
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify({{
      message: 'Add face: ' + faceName,
      content: cleanB64,
      branch: branch
    }})
  }});
}}

// Sync active layers inspector in right sidebar
function syncLayersUI() {{
  const list = document.getElementById('layersList');
  list.innerHTML = '';

  const active = getActiveLayerData();

  // Face layers
  state.facesOnCanvas.forEach((f, idx) => {{
    const item = document.createElement('div');
    const isAct = active && active.type === 'face' && active.idx === idx;
    item.className = 'layer-item' + (isAct ? ' active' : '');
    const faceObj = faces[f.faceIndex];
    item.innerHTML = `
      <div class="layer-title">
        <span>🎭</span>
        <span>${{faceObj ? faceObj.name : 'Custom Face'}}</span>
      </div>
      <div class="layer-controls">
        <button class="layer-btn" title="Delete Layer" onclick="event.stopPropagation(); deleteFaceLayer(${{idx}})">🗑️</button>
      </div>
    `;
    item.onclick = () => {{
      state.activeTransformTarget = {{ type: 'face', idx: idx }};
      render();
      syncLayersUI();
    }};
    list.appendChild(item);
  }});

  // Accessory layers
  state.accessoriesOnCanvas.forEach((a, idx) => {{
    const item = document.createElement('div');
    const isAct = active && active.type === 'acc' && active.idx === idx;
    item.className = 'layer-item' + (isAct ? ' active' : '');
    item.innerHTML = `
      <div class="layer-title">
        <span>🎀</span>
        <span>Sticker #${{idx + 1}}</span>
      </div>
      <div class="layer-controls">
        <button class="layer-btn" title="Delete Layer" onclick="event.stopPropagation(); deleteAccLayer(${{idx}})">🗑️</button>
      </div>
    `;
    item.onclick = () => {{
      state.activeTransformTarget = {{ type: 'acc', idx: idx }};
      render();
      syncLayersUI();
    }};
    list.appendChild(item);
  }});

  // Text layers
  state.texts.forEach((t, idx) => {{
    const item = document.createElement('div');
    const isAct = active && active.type === 'text' && active.idx === idx;
    item.className = 'layer-item' + (isAct ? ' active' : '');
    item.innerHTML = `
      <div class="layer-title">
        <span>✍️</span>
        <span>"${{t.text.substring(0, 16)}}"</span>
      </div>
      <div class="layer-controls">
        <button class="layer-btn" title="Delete Layer" onclick="event.stopPropagation(); deleteTextLayer(${{idx}})">🗑️</button>
      </div>
    `;
    item.onclick = () => {{
      state.activeTransformTarget = {{ type: 'text', idx: idx }};
      document.getElementById('activeTextInput').value = t.text;
      render();
      syncLayersUI();
    }};
    list.appendChild(item);
  }});
}}

window.deleteFaceLayer = function(idx) {{
  state.facesOnCanvas.splice(idx, 1);
  state.activeTransformTarget = null;
  render();
  syncLayersUI();
}};
window.deleteAccLayer = function(idx) {{
  state.accessoriesOnCanvas.splice(idx, 1);
  state.activeTransformTarget = null;
  render();
  syncLayersUI();
}};
window.deleteTextLayer = function(idx) {{
  state.texts.splice(idx, 1);
  state.activeTransformTarget = null;
  document.getElementById('activeTextInput').value = '';
  render();
  syncLayersUI();
}};

// --- EXPORT FUNCTIONS ---
function exportPng() {{
  const prevTarget = state.activeTransformTarget;
  state.activeTransformTarget = null;
  render();

  const link = document.createElement('a');
  link.download = 'murad_photoshop_meme.png';
  link.href = canvas.toDataURL('image/png');
  link.click();

  state.activeTransformTarget = prevTarget;
  render();
}}

function copyToClipboard() {{
  const prevTarget = state.activeTransformTarget;
  state.activeTransformTarget = null;
  render();

  canvas.toBlob(blob => {{
    if (!blob) return;
    try {{
      const item = new ClipboardItem({{ 'image/png': blob }});
      navigator.clipboard.write([item]).then(() => {{
        alert('🎉 Copied image to clipboard! You can paste directly into Discord with Ctrl+V!');
      }}).catch(() => {{
        alert('⚠️ Clipboard copy blocked by browser. Use Download PNG instead.');
      }});
    }} catch (err) {{
      alert('⚠️ Clipboard API not supported. Use Download PNG instead.');
    }}
  }});

  state.activeTransformTarget = prevTarget;
  render();
}}

function exportGif() {{
  if (!window.gifshot) {{
    alert('GIF library is still loading, please wait a moment.');
    return;
  }}

  const progWrap = document.getElementById('progressWrap');
  const progBar = document.getElementById('progressBar');
  const progText = document.getElementById('progressText');

  progWrap.style.display = 'block';
  progBar.style.width = '0%';
  progText.innerText = 'Rendering animation frames...';

  const prevTarget = state.activeTransformTarget;
  state.activeTransformTarget = null;

  const totalFrames = 18;
  const frameImages = [];

  for (let i = 0; i < totalFrames; i++) {{
    const p = i / totalFrames;
    if (state.bgIsGif && state.bgGifFrames.length > 0) {{
      state.bgGifIndex = Math.floor(p * state.bgGifFrames.length) % state.bgGifFrames.length;
    }}
    const off = getAnimOffset(state.animation, p);
    render(off);
    frameImages.push(canvas.toDataURL('image/png'));
  }}

  state.activeTransformTarget = prevTarget;
  render();

  progText.innerText = 'Encoding Discord GIF...';
  window.gifshot.createGIF({{
    images: frameImages,
    gifWidth: Math.min(canvas.width, 500),
    gifHeight: Math.min(canvas.height, 500),
    interval: 0.06,
    numWorkers: 2,
    progressCallback: (captureProgress) => {{
      progBar.style.width = Math.round(captureProgress * 100) + '%';
      progText.innerText = 'Encoding GIF: ' + Math.round(captureProgress * 100) + '%';
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
  if (anim === 'bob') return {{ x: 0, y: Math.sin(t) * 18, rot: 0, scale: 1.0 }};
  if (anim === 'shake') return {{ x: (Math.random() - 0.5) * 20, y: (Math.random() - 0.5) * 20, rot: (Math.random() - 0.5) * 14, scale: 1.0 }};
  if (anim === 'spin') return {{ x: 0, y: 0, rot: progress * 360, scale: 1.0 }};
  if (anim === 'petpet') return {{ x: 0, y: Math.abs(Math.sin(t)) * 20, rot: 0, scale: 1.0 - Math.abs(Math.sin(t)) * 0.2 }};
  if (anim === 'zoom') return {{ x: 0, y: 0, rot: 0, scale: 1.0 + Math.sin(t) * 0.24 }};
  if (anim === 'pulse') return {{ x: 0, y: 0, rot: 0, scale: 1.0 + Math.sin(t * 2) * 0.18 }};
  if (anim === 'wobble') return {{ x: Math.sin(t) * 16, y: 0, rot: Math.sin(t) * 18, scale: 1.0 }};
  if (anim === 'disco') return {{ x: Math.sin(t) * 14, y: Math.cos(t) * 14, rot: Math.sin(t) * 20, scale: 1.0 + Math.sin(t) * 0.16 }};
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
  fitCanvasToScreen();
  render();
  requestAnimationFrame(animLoop);
}};
</script>
</body>
</html>
"""

# Render embedded Photoshop Web Studio
components.html(html_app, height=980, scrolling=False)
