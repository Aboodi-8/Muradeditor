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
    page_title="Frutisator | Meme Editor & GIF Maker",
    page_icon="🍉",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Custom styles: completely kill Streamlit headers, decoration, toolbars, and top black bars
st.markdown("""
<style>
    /* Kill all Streamlit Cloud and local headers */
    header, [data-testid="stHeader"], .stAppHeader, [data-testid="stDecoration"], [data-testid="stToolbar"], #MainMenu, footer {
        display: none !important;
        height: 0px !important;
        min-height: 0px !important;
        max-height: 0px !important;
        visibility: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
        border: none !important;
    }
    html, body {
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        height: 100vh !important;
        width: 100vw !important;
        background-color: #000000 !important;
    }
    .stApp {
        background-color: #000000 !important;
        overflow: hidden !important;
        height: 100vh !important;
        max-height: 100vh !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    .block-container {
        padding: 0rem !important;
        margin: 0rem !important;
        max-width: 100% !important;
        height: 100vh !important;
        overflow: hidden !important;
    }
    div[data-testid="stAppViewContainer"],
    div[data-testid="stMain"],
    div[data-testid="stCustomComponentV1"],
    div[data-testid="element-container"],
    div[data-testid="stVerticalBlock"] {
        width: 100% !important;
        height: 100vh !important;
        max-height: 100vh !important;
        overflow: hidden !important;
        padding: 0 !important;
        margin: 0 !important;
        gap: 0 !important;
    }
    iframe {
        width: 100% !important;
        height: 100vh !important;
        max-height: 100vh !important;
        border: none !important;
        display: block !important;
        overflow: hidden !important;
        margin: 0 !important;
        padding: 0 !important;
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

# Helper: load faces dynamically from private repo or local manifest
def load_faces_catalog():
    faces_list = []

    # 1. Private GitHub Repository via Streamlit Secrets (keeps private photos secure)
    try:
        if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets and "PRIVATE_FACES_REPO" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            repo_name = st.secrets["PRIVATE_FACES_REPO"]
            folder = st.secrets.get("PRIVATE_FACES_FOLDER", "faces")
            api_url = f"https://api.github.com/repos/{repo_name}/contents/{folder}"
            req = urllib.request.Request(
                api_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Frutisator-App"
                }
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                items = json.loads(resp.read().decode("utf-8"))
                for item in items:
                    if item.get("type") == "file" and item["name"].lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
                        f_req = urllib.request.Request(
                            item["download_url"],
                            headers={"Authorization": f"Bearer {token}", "User-Agent": "Frutisator-App"}
                        )
                        with urllib.request.urlopen(f_req, timeout=5) as f_resp:
                            b64 = base64.b64encode(f_resp.read()).decode("utf-8")
                            mime = "image/png" if item["name"].endswith(".png") else "image/jpeg"
                            faces_list.append({
                                "id": Path(item["name"]).stem,
                                "name": Path(item["name"]).stem.replace("_", " ").title() + " 🍉",
                                "file": item["name"],
                                "src": f"data:{mime};base64,{b64}"
                            })
            if faces_list:
                return faces_list
    except Exception:
        pass

    # 2. Local manifest check
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
            return faces_list
        except Exception:
            pass

    # 3. Fallback scan if manifest missing
    if not MANIFEST_FILE.exists():
        for p in ASSETS_DIR.glob("*.png"):
            if not p.name.startswith("murad_"):
                faces_list.append({
                    "id": p.stem,
                    "name": p.stem.replace("_", " ").title() + " 🍉",
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

# --- EMBEDDED FRUTISATOR WEB STUDIO ---
html_app = f"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Frutisator</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@600;700;800;900&display=swap" rel="stylesheet">
<style>
  :root {{
    --ps-bg: #000000;
    --ps-topbar: #070709;
    --ps-panel: #0b0c10;
    --ps-canvas-bg: #030304;
    --ps-card: #12141c;
    --ps-card-hover: #181b26;
    --ps-input: #12141c;
    --ps-border: #1e212d;
    --ps-border-light: #2c3042;
    --ps-blue: #0084ff;
    --ps-blue-hover: #1a94ff;
    --ps-blue-active: #0066cc;
    --ps-text: #e2e4ea;
    --ps-text-bright: #ffffff;
    --ps-text-muted: #959cb0;
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
    font-size: 13.5px;
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

  /* TOP OPTIONS BAR */
  .ps-topbar {{
    height: 48px;
    background: var(--ps-topbar);
    border-bottom: 1px solid var(--ps-border);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 14px;
    gap: 12px;
    z-index: 100;
    flex-shrink: 0;
  }}

  .ps-brand {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }}

  .ps-logo {{
    background: var(--ps-blue);
    color: #fff;
    font-weight: 900;
    font-size: 15px;
    padding: 4px 10px;
    border-radius: 6px;
    letter-spacing: -0.5px;
    box-shadow: 0 2px 10px rgba(0, 132, 255, 0.45);
  }}

  .ps-title {{
    font-weight: 800;
    font-size: 14.5px;
    color: var(--ps-text-bright);
    white-space: nowrap;
    letter-spacing: 0.2px;
  }}

  .ps-doc-badge {{
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid var(--ps-border);
    font-size: 11.5px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 5px;
    color: #b0b7c9;
    white-space: nowrap;
  }}

  /* CONTEXT TOOL OPTIONS IN TOPBAR */
  .ps-tool-options {{
    display: flex;
    align-items: center;
    gap: 10px;
    flex: 1;
    overflow-x: auto;
    padding: 0 6px;
  }}

  .ps-opt-label {{
    color: var(--ps-text-muted);
    font-size: 12px;
    font-weight: 600;
    white-space: nowrap;
  }}

  .ps-opt-badge {{
    background: rgba(0, 132, 255, 0.18);
    border: 1px solid var(--ps-blue);
    color: #60c5ff;
    padding: 4px 10px;
    border-radius: 5px;
    font-weight: 800;
    font-size: 12px;
    white-space: nowrap;
  }}

  .ps-opt-group {{
    display: flex;
    align-items: center;
    gap: 6px;
    border-left: 1px solid var(--ps-border);
    padding-left: 10px;
  }}

  .ps-opt-btn {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    color: var(--ps-text-bright);
    padding: 5px 11px;
    border-radius: 5px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.12s ease;
    white-space: nowrap;
    display: inline-flex;
    align-items: center;
    gap: 5px;
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
    gap: 8px;
    flex-shrink: 0;
  }}

  .ps-btn {{
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid var(--ps-border);
    color: var(--ps-text-bright);
    padding: 6px 13px;
    border-radius: 6px;
    font-size: 12.5px;
    font-weight: 800;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 6px;
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
    box-shadow: 0 2px 10px rgba(0, 132, 255, 0.5);
  }}
  .ps-btn-primary:hover {{
    background: var(--ps-blue-hover);
    border-color: var(--ps-blue-hover);
  }}

  /* WORKSPACE BODY */
  .ps-body {{
    display: flex;
    flex: 1;
    height: calc(100vh - 48px);
    overflow: hidden;
    position: relative;
    background: #000000;
  }}

  /* SIDEBAR PANELS */
  .ps-sidebar {{
    width: 330px;
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
    width: 330px;
    border-right: 1px solid var(--ps-border);
  }}
  .ps-sidebar-right {{
    width: 340px;
    border-left: 1px solid var(--ps-border);
  }}
  .ps-sidebar::-webkit-scrollbar {{
    width: 6px;
  }}
  .ps-sidebar::-webkit-scrollbar-thumb {{
    background: var(--ps-border-light);
    border-radius: 3px;
  }}

  /* PANEL SECTIONS */
  .ps-panel-section {{
    border-bottom: 1px solid var(--ps-border);
    padding: 11px 13px;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }}
  .ps-panel-section:last-child {{
    border-bottom: none;
    padding-bottom: 30px;
  }}

  /* COMPACT SHORT SECTION HEADERS */
  .panel-section-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: #12141c;
    border: 1px solid #202330;
    border-radius: 6px;
    padding: 5px 11px;
  }}
  .panel-section-title {{
    font-weight: 800;
    font-size: 13px;
    color: var(--ps-text-bright);
    display: flex;
    align-items: center;
    gap: 7px;
    letter-spacing: 0.1px;
  }}

  .section-label {{
    font-size: 11px;
    color: #a0a6b8;
    font-weight: 800;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }}

  /* DISCRETE CORNER ADMIN LOCK BUTTON */
  .admin-lock-btn {{
    background: transparent;
    border: 1px solid #262938;
    border-radius: 5px;
    color: var(--ps-text-muted);
    cursor: pointer;
    padding: 3px 8px;
    font-size: 13px;
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

  /* DROP ZONES WITH UPLOAD SVG ICON */
  .ps-dropzone {{
    border: 2px dashed var(--ps-blue);
    background: rgba(0, 132, 255, 0.08);
    border-radius: 8px;
    padding: 12px;
    text-align: center;
    cursor: pointer;
    transition: all 0.15s ease;
    display: block;
    color: #fff;
    font-weight: 800;
    font-size: 12.5px;
  }}
  .ps-dropzone:hover {{
    background: rgba(0, 132, 255, 0.2);
    border-color: #fff;
    box-shadow: 0 0 14px rgba(0, 132, 255, 0.35);
  }}
  .ps-dropzone input {{ display: none; }}

  .upload-icon {{
    display: inline-block;
    vertical-align: middle;
    stroke: currentColor;
    flex-shrink: 0;
  }}

  /* GRID CARDS (FACES) */
  .grid-cards-faces {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 9px;
  }}
  .grid-card {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 8px;
    padding: 6px;
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
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  }}
  .grid-card.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 132, 255, 0.22);
    box-shadow: 0 0 0 2px var(--ps-blue), 0 4px 12px rgba(0, 132, 255, 0.3);
  }}
  .grid-card img {{
    width: 100%;
    height: 105px;
    border-radius: 6px;
    object-fit: cover;
    margin-bottom: 5px;
    background: #000;
  }}
  .grid-card span {{
    font-size: 11.5px;
    font-weight: 700;
    color: var(--ps-text-bright);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  }}

  /* COMPACT SHORTER POPULAR TEMPLATES */
  .grid-card-template {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 7px;
    padding: 5px;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.14s ease;
  }}
  .grid-card-template:hover {{
    border-color: var(--ps-border-light);
    transform: translateY(-2px);
    background: var(--ps-card-hover);
  }}
  .grid-card-template.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 132, 255, 0.22);
    box-shadow: 0 0 0 2px var(--ps-blue);
  }}
  .grid-card-template img {{
    width: 100%;
    height: 58px; /* SHORTER: saves space! */
    border-radius: 5px;
    object-fit: cover;
    margin-bottom: 4px;
    background: #000;
  }}
  .grid-card-template span {{
    font-size: 11px;
    font-weight: 700;
    color: var(--ps-text-bright);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  }}

  /* BUTTON GROUPS GRID */
  .btn-group-grid {{
    display: grid;
    background: var(--ps-card);
    border-radius: 6px;
    padding: 3px;
    border: 1px solid var(--ps-border);
    gap: 3px;
  }}
  .btn-group-4 {{
    grid-template-columns: repeat(4, 1fr);
  }}
  .btn-group-6 {{
    grid-template-columns: repeat(6, 1fr);
  }}
  .btn-group-2 {{
    grid-template-columns: repeat(2, 1fr);
  }}

  .btn-toggle {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    font-size: 11px;
    font-weight: 700;
    padding: 6px 2px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.12s ease;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .btn-toggle:hover {{ color: #fff; }}
  .btn-toggle.active {{
    background: var(--ps-blue);
    color: #fff;
    box-shadow: 0 2px 6px rgba(0, 132, 255, 0.4);
  }}

  /* SLIDERS */
  .slider-row {{
    display: flex;
    flex-direction: column;
    gap: 5px;
  }}
  .slider-row label {{
    font-size: 11.5px;
    color: var(--ps-text-muted);
    display: flex;
    justify-content: space-between;
    font-weight: 700;
  }}
  .slider-row label b {{
    color: var(--ps-text-bright);
    background: #171924;
    padding: 1px 6px;
    border-radius: 4px;
    border: 1px solid #232736;
  }}
  .slider-row input[type="range"] {{
    width: 100%;
    accent-color: var(--ps-blue);
    cursor: pointer;
    height: 7px;
  }}

  /* INPUTS */
  .ps-input {{
    width: 100%;
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    color: #fff;
    font-size: 13px;
    padding: 8px 12px;
    border-radius: 6px;
    outline: none;
    transition: border-color 0.15s ease;
  }}
  .ps-input:focus {{
    border-color: var(--ps-blue);
    box-shadow: 0 0 0 2px rgba(0, 132, 255, 0.3);
  }}

  /* DISCORD ANIMATION CHIPS */
  .grid-anim-chips {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 5px;
  }}
  .anim-chip {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 6px;
    padding: 6px 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 700;
    color: #e2e4ea;
    transition: all 0.12s ease;
  }}
  .anim-chip:hover {{
    background: var(--ps-card-hover);
    border-color: var(--ps-border-light);
  }}
  .anim-chip.active {{
    background: rgba(0, 132, 255, 0.22);
    border-color: var(--ps-blue);
    box-shadow: 0 0 0 1.5px var(--ps-blue);
  }}
  .anim-chip span.emoji {{
    font-size: 14px;
  }}

  /* ACTIVE LAYERS LIST */
  .layers-list {{
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}
  .layer-item {{
    background: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 6px;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    transition: all 0.12s ease;
    gap: 8px;
  }}
  .layer-item:hover {{
    border-color: var(--ps-border-light);
    background: var(--ps-card-hover);
  }}
  .layer-item.active {{
    border-color: var(--ps-blue);
    background: rgba(0, 132, 255, 0.2);
    box-shadow: 0 0 0 1.5px var(--ps-blue);
  }}
  .layer-left {{
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
    flex: 1;
  }}
  .layer-thumb {{
    width: 26px;
    height: 26px;
    border-radius: 4px;
    object-fit: cover;
    border: 1px solid #292d3e;
    flex-shrink: 0;
    background: #000;
  }}
  .layer-text-badge {{
    width: 26px;
    height: 26px;
    border-radius: 4px;
    background: #171924;
    color: var(--ps-blue);
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-weight: 900;
    font-size: 13px;
    border: 1px solid #292d3e;
    flex-shrink: 0;
  }}
  .layer-title-text {{
    font-weight: 700;
    font-size: 12px;
    color: #fff;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .layer-actions {{
    display: flex;
    align-items: center;
    gap: 3px;
    flex-shrink: 0;
  }}
  .layer-action-btn {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    cursor: pointer;
    font-size: 13px;
    padding: 3px 5px;
    border-radius: 3px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }}
  .layer-action-btn:hover {{
    color: #fff;
    background: rgba(255, 255, 255, 0.14);
  }}

  /* CENTER CANVAS VIEWPORT */
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
    padding: 12px;
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
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(14, 15, 20, 0.96);
    backdrop-filter: blur(20px);
    border: 1px solid var(--ps-border-light);
    border-radius: 8px;
    padding: 14px 22px;
    width: 360px;
    box-shadow: 0 25px 60px rgba(0,0,0,0.9);
    z-index: 1000;
  }}
  .progress-track {{
    height: 7px;
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
    font-size: 12.5px;
    color: var(--ps-text-bright);
    text-align: center;
    margin-top: 7px;
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
    width: 420px;
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
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .admin-modal-title {{
    font-weight: 800;
    font-size: 14px;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .admin-modal-close {{
    background: transparent;
    border: none;
    color: var(--ps-text-muted);
    font-size: 17px;
    cursor: pointer;
  }}
  .admin-modal-close:hover {{ color: #fff; }}
  .admin-modal-body {{
    padding: 16px;
    display: flex;
    flex-direction: column;
    gap: 12px;
    max-height: 70vh;
    overflow-y: auto;
  }}

  /* RESPONSIVE SCALING */
  @media (max-width: 1200px) {{
    .ps-sidebar-left {{ width: 280px; }}
    .ps-sidebar-right {{ width: 290px; }}
  }}
  @media (max-width: 860px) {{
    .ps-title, .ps-doc-badge {{ display: none; }}
    .ps-body {{ flex-direction: column; overflow-y: auto; }}
    .ps-sidebar {{ width: 100% !important; height: auto; }}
  }}

  /* ARABIC TYPOGRAPHY ENHANCEMENTS: BIGGER & BOLDER */
  body.lang-ar,
  .ps-app.lang-ar {{
    font-family: 'Cairo', -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif !important;
  }}
  .ps-app.lang-ar button,
  .ps-app.lang-ar .ps-opt-btn,
  .ps-app.lang-ar .btn-toggle,
  .ps-app.lang-ar .btn-pill,
  .ps-app.lang-ar .ps-panel-title,
  .ps-app.lang-ar .panel-section-title,
  .ps-app.lang-ar .section-label,
  .ps-app.lang-ar .grid-card span,
  .ps-app.lang-ar .ps-title,
  .ps-app.lang-ar .ps-brand span,
  .ps-app.lang-ar .ps-doc-badge,
  .ps-app.lang-ar .slider-row label,
  .ps-app.lang-ar .slider-row b,
  .ps-app.lang-ar .ps-input,
  .ps-app.lang-ar .ps-dropzone span,
  .ps-app.lang-ar .layer-item span {{
    font-family: 'Cairo', -apple-system, BlinkMacSystemFont, "Segoe UI", Tahoma, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: 0 !important;
  }}
  .ps-app.lang-ar .panel-section-title {{
    font-size: 13.5px !important;
    font-weight: 900 !important;
  }}
  .ps-app.lang-ar .section-label {{
    font-size: 12px !important;
    font-weight: 800 !important;
  }}
  .ps-app.lang-ar .ps-opt-btn,
  .ps-app.lang-ar .btn-toggle {{
    font-size: 12px !important;
    font-weight: 800 !important;
  }}
  .ps-app.lang-ar .ps-title {{
    font-size: 16px !important;
    font-weight: 900 !important;
  }}
  .ps-app.lang-ar .slider-row label {{
    font-size: 12px !important;
    font-weight: 700 !important;
  }}
  .ps-app.lang-ar .slider-row b {{
    font-size: 12.5px !important;
    font-weight: 900 !important;
  }}
  .ps-app.lang-ar #txtShiftTip {{
    font-size: 12px !important;
    font-weight: 800 !important;
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

<div class="ps-app" id="psApp">

  <!-- TOP OPTIONS BAR -->
  <header class="ps-topbar">
    <div class="ps-brand">
      <span class="ps-logo">Fr</span>
      <span class="ps-title" id="appTitle">Frutisator</span>
      <span class="ps-doc-badge" id="docSizeBadge">800 × 800 px</span>
    </div>

    <!-- CONTEXT TOOL OPTIONS -->
    <div class="ps-tool-options" id="toolOptions">
      <button id="fitScreenBtn" class="ps-opt-btn" title="Auto Fit Canvas to Viewport">🔍 Fit Screen</button>
      <span class="ps-opt-label" id="lblTransform">Transform:</span>
      <span class="ps-opt-badge" id="optLayerName">No layer selected</span>
      <div class="ps-opt-group" id="optActionGroup" style="display:none;">
        <span class="ps-opt-label" id="optScaleVal">100%</span>
        <span class="ps-opt-label" id="optRotVal">0°</span>
        <button id="optFlipBtn" class="ps-opt-btn" title="Flip Horizontal">↔️ Flip</button>
        <button id="optCenterBtn" class="ps-opt-btn" title="Center on Canvas">🎯 Center</button>
        <button id="optDeleteBtn" class="ps-opt-btn danger" title="Delete Layer">🗑️ Delete</button>
      </div>
      <span style="font-size:11px; color:#60c5ff; margin-left:6px; font-weight:600;" id="txtShiftTip">💡 Hold Shift while dragging corners to Stretch!</span>
    </div>

    <!-- EXPORT ACTIONS + ARABIC LANGUAGE SWITCHER -->
    <div class="ps-actions">
      <button id="btnExportGif" class="ps-btn ps-btn-primary" title="Export Animated Discord GIF">⬇️ Export GIF</button>
      <button id="btnExportPng" class="ps-btn" title="Export High-Res PNG">⬇️ PNG</button>
      <button id="btnCopyDiscord" class="ps-btn" title="Copy to clipboard for instant Discord paste">📋 Copy</button>
      <button id="btnLangToggle" class="ps-btn" style="background:#161824; border-color:#2a2e42;" title="Toggle Arabic / English">🌐 العربية</button>
    </div>
  </header>

  <!-- BODY (LEFT MENUS + DOMINANT CENTER CANVAS + RIGHT MENUS) -->
  <div class="ps-body">

    <!-- LEFT SIDEBAR: BACKDROP FIRST, THEN FRUITS FACES -->
    <aside class="ps-sidebar ps-sidebar-left" id="sidebarLeft">

      <!-- 1. SECTION: BACKDROP & TEMPLATES -->
      <div class="ps-panel-section" id="section-bg">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleBackdrop">🖼️ Backdrop & Templates</span>
        </div>

        <!-- UPLOAD BACKDROP DROPZONE WITH SVG UPLOAD ICON -->
        <label class="ps-dropzone">
          <div style="display:flex; align-items:center; justify-content:center; gap:8px;">
            <svg class="upload-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span id="txtUploadBg">Upload Image, Meme or Animated GIF</span>
          </div>
          <input type="file" id="bgFileInput" accept="image/*,.gif">
        </label>

        <div style="display:flex; flex-direction:column; gap:5px;">
          <span class="section-label" id="lblCanvasFormat">Canvas Format:</span>
          <div class="btn-group-grid btn-group-4" id="canvasSizeGroup">
            <button class="btn-toggle active" data-size="true_size" id="btnTrueSize">📐 True Size</button>
            <button class="btn-toggle" data-size="square">⏹️ 1:1</button>
            <button class="btn-toggle" data-size="landscape">🖼️ 16:9</button>
            <button class="btn-toggle" data-size="portrait">📱 9:16</button>
          </div>
        </div>

        <span class="section-label" id="lblPopularTemplates">Popular Meme Templates:</span>
        <div class="grid-cards-faces" id="bgPresetsRow" style="max-height:160px; overflow-y:auto;"></div>
      </div>

      <!-- 2. SECTION: FRUITS FACES -->
      <div class="ps-panel-section" id="section-faces">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleFaces">🍉 Fruits Faces</span>
          <!-- DISCRETE CORNER ADMIN LOCK BUTTON -->
          <button id="adminLockBtn" class="admin-lock-btn" title="Admin Fruits Catalog Settings">🔒</button>
        </div>

        <!-- UPLOAD FRUIT DROPZONE WITH SVG UPLOAD ICON -->
        <label class="ps-dropzone">
          <div style="display:flex; align-items:center; justify-content:center; gap:8px;">
            <svg class="upload-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span id="txtUploadFace">Upload Custom Fruit / Photo</span>
          </div>
          <input type="file" id="faceFileInput" accept="image/*">
        </label>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span class="section-label" id="lblDefaultFaces">Default Fruits Faces:</span>
          <button id="addFaceBtn" class="ps-opt-btn" style="background:var(--ps-blue); border-color:var(--ps-blue); color:#fff; padding:4px 10px;">➕ Add Face</button>
        </div>
        <div class="grid-cards-faces" id="facesGrid" style="max-height:240px; overflow-y:auto;"></div>

        <div style="display:flex; flex-direction:column; gap:5px; margin-top:2px;">
          <span class="section-label" id="lblCutoutShape">Cutout Shape:</span>
          <!-- STICKER CIRCLE REMOVED, EXACT 2 COLUMNS -->
          <div class="btn-group-grid btn-group-2" id="maskGroup">
            <button class="btn-toggle active" data-mask="square" id="btnFullFrame">Full Frame</button>
            <button class="btn-toggle" data-mask="oval" id="btnOval">Oval</button>
          </div>
        </div>

        <div class="slider-row">
          <label><span id="lblFaceOpacity">Face Opacity:</span> <b id="faceOpacityVal">100%</b></label>
          <input type="range" id="faceOpacitySlider" min="0.1" max="1.0" step="0.05" value="1.0">
        </div>
      </div>

      <!-- 3. SECTION: COLOR FILTERS & ADJUSTMENTS -->
      <div class="ps-panel-section" id="section-filters">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleFilters">🎨 Color & Filters</span>
          <button id="resetFiltersBtn" class="ps-opt-btn" style="padding:2px 7px; font-size:10.5px;" title="Reset Filters">🔄 Reset</button>
        </div>

        <!-- TARGET SELECTOR: BACKDROP, FACE, STICKER -->
        <div style="display:flex; flex-direction:column; gap:4px;">
          <span class="section-label" id="lblFilterTarget">Apply Filter To:</span>
          <div class="btn-group-grid btn-group-3" id="filterTargetGroup">
            <button class="btn-toggle active" data-target="bg" id="btnFilterBg">🖼️ Backdrop</button>
            <button class="btn-toggle" data-target="face" id="btnFilterFace">🍉 Face</button>
            <button class="btn-toggle" data-target="acc" id="btnFilterAcc">🎀 Sticker</button>
          </div>
        </div>

        <!-- NOTICE WHEN NO FACE/STICKER LAYER IS ACTIVE -->
        <div id="filterNoTargetNotice" style="display:none; color:var(--ps-yellow); font-size:11px; padding:6px 8px; border:1px dashed var(--ps-border); border-radius:5px; background:rgba(255,200,0,0.05); text-align:center;"></div>

        <div id="filterSlidersBox" style="display:flex; flex-direction:column; gap:6px; transition:opacity 0.2s;">
          <!-- QUICK PRESETS: 8 PRESETS IN A 4-COLUMN GRID -->
          <div style="display:flex; flex-direction:column; gap:4px; margin-top:2px;">
            <span class="section-label" id="lblFilterPresets">Quick Presets:</span>
            <div class="btn-group-grid btn-group-4" id="filterPresetsGrid">
              <button class="ps-opt-btn active" data-preset="normal" id="presetNormal" style="padding:4px 2px; font-size:10.5px; justify-content:center;">Normal</button>
              <button class="ps-opt-btn" data-preset="bw" id="presetBw" style="padding:4px 2px; font-size:10.5px; justify-content:center;">🖤 B&W</button>
              <button class="ps-opt-btn" data-preset="sepia" id="presetSepia" style="padding:4px 2px; font-size:10.5px; justify-content:center;">📜 Sepia</button>
              <button class="ps-opt-btn" data-preset="invert" id="presetInvert" style="padding:4px 2px; font-size:10.5px; justify-content:center;">🔮 Invert</button>
              <button class="ps-opt-btn" data-preset="shift" id="presetShift" style="padding:4px 2px; font-size:10.5px; justify-content:center;">🌈 Shift</button>
              <button class="ps-opt-btn" data-preset="vivid" id="presetVivid" style="padding:4px 2px; font-size:10.5px; justify-content:center;">⚡ Vivid</button>
              <button class="ps-opt-btn" data-preset="cyber" id="presetCyber" style="padding:4px 2px; font-size:10.5px; justify-content:center;">🌆 Cyber</button>
              <button class="ps-opt-btn" data-preset="warm" id="presetWarm" style="padding:4px 2px; font-size:10.5px; justify-content:center;">🔥 Warm</button>
            </div>
          </div>

          <!-- FINE ADJUSTMENT SLIDERS -->
          <div style="display:flex; flex-direction:column; gap:5px; margin-top:3px;">
            <div class="slider-row">
              <label><span id="lblFilterHue">Hue / Color Shift:</span> <b id="valFilterHue">0°</b></label>
              <input type="range" id="sliderFilterHue" min="0" max="360" step="5" value="0">
            </div>
            <div class="slider-row">
              <label><span id="lblFilterBw">B&W (Grayscale):</span> <b id="valFilterBw">0%</b></label>
              <input type="range" id="sliderFilterBw" min="0" max="100" step="5" value="0">
            </div>
            <div class="slider-row">
              <label><span id="lblFilterBrightness">Brightness:</span> <b id="valFilterBrightness">100%</b></label>
              <input type="range" id="sliderFilterBrightness" min="40" max="180" step="5" value="100">
            </div>
            <div class="slider-row">
              <label><span id="lblFilterContrast">Contrast:</span> <b id="valFilterContrast">100%</b></label>
              <input type="range" id="sliderFilterContrast" min="40" max="200" step="5" value="100">
            </div>
            <div class="slider-row">
              <label><span id="lblFilterSaturate">Saturation:</span> <b id="valFilterSaturate">100%</b></label>
              <input type="range" id="sliderFilterSaturate" min="0" max="250" step="5" value="100">
            </div>
          </div>
        </div>
      </div>

    </aside>

    <!-- CENTER CANVAS VIEWPORT -->
    <main class="ps-canvas-viewport" id="canvasViewport">
      <div class="canvas-stage">
        <canvas id="mainCanvas" width="800" height="800"></canvas>
      </div>
    </main>

    <!-- RIGHT SIDEBAR: TEXT, STICKERS, FX & ACTIVE LAYERS -->
    <aside class="ps-sidebar ps-sidebar-right" id="sidebarRight">

      <!-- 3. SECTION: MEME TEXT -->
      <div class="ps-panel-section" id="section-text">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleText">✍️ Meme Text</span>
        </div>

        <div style="display:flex; gap:6px;">
          <button id="addTopTextBtn" class="ps-opt-btn" style="flex:1; padding:7px; justify-content:center;">➕ Top</button>
          <button id="addBottomTextBtn" class="ps-opt-btn" style="flex:1; padding:7px; justify-content:center;">➕ Bottom</button>
          <button id="addCustomTextBtn" class="ps-opt-btn" style="flex:1; padding:7px; justify-content:center; background:var(--ps-blue); color:#fff; border-color:var(--ps-blue);">➕ Custom</button>
        </div>

        <div id="textEditorBox" style="display:flex; flex-direction:column; gap:9px;">
          <input type="text" id="activeTextInput" class="ps-input" placeholder="Click + Top/Bottom or type meme text...">

          <!-- FONT SELECTION DROPDOWN -->
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span class="section-label" id="lblFont">Font:</span>
            <select id="fontFamilySelect" class="ps-input" style="padding: 7px 10px; font-weight: 700; cursor: pointer;">
              <option value="Impact, sans-serif">Impact (Classic Meme)</option>
              <option value="'Arial Black', Gadget, sans-serif">Arial Black (Heavy Bold)</option>
              <option value="'Comic Sans MS', cursive, sans-serif">Comic Sans (Doge / Fun)</option>
              <option value="Tahoma, 'Segoe UI', sans-serif">Tahoma (Arabic & Clean)</option>
              <option value="'Courier New', monospace">Courier (Typewriter / Hacker)</option>
              <option value="'Trebuchet MS', sans-serif">Trebuchet MS (Modern)</option>
              <option value="Georgia, serif">Georgia (Classy Serif)</option>
            </select>
          </div>

          <div class="slider-row">
            <label><span id="lblFontSize">Font Size:</span> <b id="textSizeVal">48px</b></label>
            <input type="range" id="textSizeSlider" min="16" max="130" step="2" value="48">
          </div>

          <!-- 6 COLOR OPTIONS INCLUDING COLOR WHEEL -->
          <div style="display:flex; flex-direction:column; gap:4px;">
            <span class="section-label" id="lblTextColor">Text Color:</span>
            <div class="btn-group-grid btn-group-6" id="textColorGroup">
              <button class="btn-toggle active" data-color="#ffffff">White</button>
              <button class="btn-toggle" data-color="#facc15" style="color:#facc15;">Yellow</button>
              <button class="btn-toggle" data-color="#ef4444" style="color:#ef4444;">Red</button>
              <button class="btn-toggle" data-color="#22d3ee" style="color:#22d3ee;">Cyan</button>
              <button class="btn-toggle" data-color="#4ade80" style="color:#4ade80;">Green</button>
              <button class="btn-toggle" id="colorWheelBtn" data-color="wheel" title="Choose any custom color">🎨 Wheel</button>
            </div>
            <input type="color" id="nativeColorPicker" value="#ffffff" style="display:none;">
          </div>
        </div>
      </div>

      <!-- 4. SECTION: CUSTOM STICKERS -->
      <div class="ps-panel-section" id="section-stickers">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleStickers">🎀 Custom Stickers</span>
        </div>

        <!-- UPLOAD STICKER DROPZONE WITH SVG UPLOAD ICON -->
        <label class="ps-dropzone">
          <div style="display:flex; align-items:center; justify-content:center; gap:8px;">
            <svg class="upload-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
              <polyline points="17 8 12 3 7 8"></polyline>
              <line x1="12" y1="3" x2="12" y2="15"></line>
            </svg>
            <span id="txtUploadSticker">Upload Custom PNG / Sticker</span>
          </div>
          <input type="file" id="accFileInput" accept="image/*,.gif">
        </label>

        <div id="accEditorBox" style="display:none; flex-direction:column; gap:8px;">
          <div class="slider-row">
            <label><span id="lblStickerOpacity">Opacity:</span> <b id="accOpacityVal">100%</b></label>
            <input type="range" id="accOpacitySlider" min="0.1" max="1.0" step="0.05" value="1.0">
          </div>
        </div>
      </div>

      <!-- 5. SECTION: COMPACT DISCORD GIF EFFECTS -->
      <div class="ps-panel-section" id="section-anim">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleAnim">✨ Discord GIF Effects</span>
        </div>

        <div class="grid-anim-chips" id="animGrid">
          <div class="anim-chip active" data-anim="none"><span class="emoji">🖼️</span><span id="animStill">Still</span></div>
          <div class="anim-chip" data-anim="bob"><span class="emoji">🕺</span><span id="animBob">Bob</span></div>
          <div class="anim-chip" data-anim="shake"><span class="emoji">💢</span><span id="animShake">Shake</span></div>
          <div class="anim-chip" data-anim="spin"><span class="emoji">🌀</span><span id="animSpin">Spin</span></div>
          <div class="anim-chip" data-anim="petpet"><span class="emoji">👋</span><span id="animPetpet">Petpet</span></div>
          <div class="anim-chip" data-anim="zoom"><span class="emoji">💥</span><span id="animPulse">Pulse</span></div>
          <div class="anim-chip" data-anim="pulse"><span class="emoji">💓</span><span id="animHeart">Heart</span></div>
          <div class="anim-chip" data-anim="wobble"><span class="emoji">🌊</span><span id="animWobble">Wobble</span></div>
          <div class="anim-chip" data-anim="disco"><span class="emoji">🪩</span><span id="animDisco">Disco</span></div>
        </div>
      </div>

      <!-- 6. SECTION: ACTIVE LAYERS -->
      <div class="ps-panel-section" id="section-layers">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleLayers">📑 Active Layers</span>
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
        <span class="admin-modal-title">🔐 Fruits Catalog Admin</span>
        <button class="admin-modal-close" id="adminModalClose">✕</button>
      </div>
      
      <!-- STEP 1: PASSWORD AUTH -->
      <div class="admin-modal-body" id="adminAuthBody">
        <div style="text-align:center; padding: 12px 0;">
          <div style="font-size:36px; margin-bottom:8px;">🔒</div>
          <div style="font-weight:800; font-size:14px; color:#fff; margin-bottom:4px;">Enter Admin Password</div>
          <div style="font-size:12px; color:var(--ps-text-muted); margin-bottom:12px;">Manage default fruit faces or push new ones to GitHub.</div>
          <input type="password" id="adminPwdInput" class="ps-input" placeholder="Password..." style="margin-bottom:8px; text-align:center; width:220px; margin:0 auto 10px auto;">
          <div id="adminAuthError" style="color:var(--ps-danger); font-size:11.5px; display:none; margin-bottom:8px;">❌ Incorrect Admin Password</div>
          <button id="adminUnlockBtn" class="ps-btn ps-btn-primary" style="width:220px; margin:0 auto; justify-content:center;">Unlock</button>
        </div>
      </div>

      <!-- STEP 2: CATALOG MANAGEMENT -->
      <div class="admin-modal-body" id="adminManageBody" style="display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="color:var(--ps-green); font-weight:800; font-size:12px;">✅ Admin Access Granted</span>
          <button id="adminLockOutBtn" class="ps-opt-btn" style="font-size:11px;">Lock</button>
        </div>

        <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
          <span style="font-size:12px; font-weight:800; color:#fff;">➕ ADD NEW FRUIT FACE TO CATALOG:</span>
          <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
            <input type="text" id="adminNewFaceName" class="ps-input" placeholder="Fruit Name & Emoji (e.g. Watermelon 🍉)">
            <input type="file" id="adminNewFaceFile" accept="image/*" class="ps-input" style="padding:6px;">
            <button id="adminUploadBtn" class="ps-btn ps-btn-primary" style="justify-content:center; gap:8px;">
              <svg class="upload-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="17 8 12 3 7 8"></polyline>
                <line x1="12" y1="3" x2="12" y2="15"></line>
              </svg>
              <span>Push to Catalog</span>
            </button>
            <div id="adminUploadStatus" style="font-size:11.5px; text-align:center;"></div>
          </div>
        </div>

        <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
          <span style="font-size:12px; font-weight:800; color:#fff;">🗑️ MANAGE DEFAULT FRUITS:</span>
          <div id="adminFacesCatalogList" style="display:flex; flex-direction:column; gap:5px; max-height:200px; overflow-y:auto; margin-top:6px;"></div>
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

let layerZCounter = 1;
let currentLang = 'en';

// BILINGUAL ARABIC & ENGLISH TRANSLATIONS
const i18n = {{
  en: {{
    langBtn: '🌐 العربية',
    appTitle: 'Frutisator',
    fitScreen: '🔍 Fit Screen',
    lblTransform: 'Transform:',
    noLayer: 'No layer selected',
    flip: '↔️ Flip',
    center: '🎯 Center',
    delete: '🗑️ Delete',
    shiftTip: '💡 Hold Shift while dragging corners to Stretch!',
    exportGif: '⬇️ Export GIF',
    exportPng: '⬇️ PNG',
    copyDiscord: '📋 Copy',
    copiedAlert: '🎉 Copied image to clipboard! You can paste directly into Discord with Ctrl+V!',
    
    secTitleBackdrop: '🖼️ Backdrop & Templates',
    txtUploadBg: 'Upload Image, Meme or Animated GIF',
    lblCanvasFormat: 'Canvas Format:',
    btnTrueSize: '📐 True Size',
    lblPopularTemplates: 'Popular Meme Templates:',

    secTitleFaces: '🍉 Fruits Faces',
    txtUploadFace: 'Upload Custom Fruit / Photo',
    lblDefaultFaces: 'Default Fruits Faces:',
    addFaceBtn: '➕ Add Face',
    lblCutoutShape: 'Cutout Shape:',
    btnFullFrame: 'Full Frame',
    btnOval: 'Oval',
    lblFaceOpacity: 'Face Opacity:',

    secTitleText: '✍️ Meme Text',
    addTopTextBtn: '➕ Top',
    addBottomTextBtn: '➕ Bottom',
    addCustomTextBtn: '➕ Custom',
    textPlaceholder: 'Click + Top/Bottom or type meme text...',
    lblFont: 'Font:',
    lblFontSize: 'Font Size:',
    lblTextColor: 'Text Color:',
    wheelColor: '🎨 Wheel',

    secTitleStickers: '🎀 Custom Stickers',
    txtUploadSticker: 'Upload Custom PNG / Sticker',
    lblStickerOpacity: 'Opacity:',

    secTitleAnim: '✨ Discord GIF Effects',
    animStill: 'Still',
    animBob: 'Bob',
    animShake: 'Shake',
    animSpin: 'Spin',
    animPetpet: 'Petpet',
    animPulse: 'Pulse',
    animHeart: 'Heart',
    animWobble: 'Wobble',
    animDisco: 'Disco',

    secTitleLayers: '📑 Active Layers',
    noLayers: 'No active layers on canvas',

    secTitleFilters: '🎨 Color & Filters',
    resetFilters: '🔄 Reset',
    lblFilterTarget: 'Apply Filter To:',
    btnFilterBg: '🖼️ Backdrop',
    btnFilterFace: '🍉 Face',
    btnFilterAcc: '🎀 Sticker',
    lblFilterPresets: 'Quick Presets:',
    presetNormal: 'Normal',
    presetBw: '🖤 B&W',
    presetSepia: '📜 Sepia',
    presetInvert: '🔮 Invert',
    presetShift: '🌈 Shift',
    presetVivid: '⚡ Vivid',
    presetCyber: '🌆 Cyber',
    presetWarm: '🔥 Warm',
    lblFilterHue: 'Hue / Color Shift:',
    lblFilterBw: 'B&W (Grayscale):',
    lblFilterBrightness: 'Brightness:',
    lblFilterContrast: 'Contrast:',
    lblFilterSaturate: 'Saturation:'
  }},
  ar: {{
    langBtn: '🌐 English',
    appTitle: 'فروتيساتور',
    fitScreen: '🔍 ملاءمة الشاشة',
    lblTransform: 'تحويل:',
    noLayer: 'لم يتم تحديد طبقة',
    flip: '↔️ قلب',
    center: '🎯 توسيط',
    delete: '🗑️ حذف',
    shiftTip: '💡 اضغط Shift أثناء السحب لتمديد ومط الصورة!',
    exportGif: '⬇️ تصدير GIF',
    exportPng: '⬇️ حفظ PNG',
    copyDiscord: '📋 نسخ',
    copiedAlert: '🎉 تم نسخ الصورة إلى الحافظة! يمكنك لصقها مباشرة في ديسكورد عبر Ctrl+V!',
    
    secTitleBackdrop: '🖼️ الخلفيات والقوالب',
    txtUploadBg: 'رفع صورة أو ميم أو GIF متحرك',
    lblCanvasFormat: 'تنسيق الكانفاس:',
    btnTrueSize: '📐 الحجم الأصلي',
    lblPopularTemplates: 'قوالب الميمز الشائعة:',

    secTitleFaces: '🍉 وجوه الفواكه',
    txtUploadFace: 'رفع فاكهة / صورة مخصصة',
    lblDefaultFaces: 'وجوه الفواكه الافتراضية:',
    addFaceBtn: '➕ إضافة وجه',
    lblCutoutShape: 'شكل القص:',
    btnFullFrame: 'إطار كامل',
    btnOval: 'بيضاوي',
    lblFaceOpacity: 'شفافية الوجه:',

    secTitleText: '✍️ نصوص الميم',
    addTopTextBtn: '➕ أعلى',
    addBottomTextBtn: '➕ أسفل',
    addCustomTextBtn: '➕ مخصص',
    textPlaceholder: 'اضغط + أعلى/أسفل أو اكتب النص...',
    lblFont: 'نوع الخط:',
    lblFontSize: 'حجم الخط:',
    lblTextColor: 'لون النص:',
    wheelColor: '🎨 عجلة',

    secTitleStickers: '🎀 ملصقات مخصصة',
    txtUploadSticker: 'رفع ملصق PNG مخصص',
    lblStickerOpacity: 'الشفافية:',

    secTitleAnim: '✨ تأثيرات ديسكورد المتحركة',
    animStill: 'ثابت',
    animBob: 'تمايل',
    animShake: 'اهتزاز',
    animSpin: 'دوران',
    animPetpet: 'تربيت',
    animPulse: 'نبض',
    animHeart: 'قلب',
    animWobble: 'تموج',
    animDisco: 'ديسكو',

    secTitleLayers: '📑 الطبقات النشطة',
    noLayers: 'لا توجد طبقات نشطة على الكانفاس',

    secTitleFilters: '🎨 فلاتر وتعديل الألوان',
    resetFilters: '🔄 إعادة ضبط',
    lblFilterTarget: 'تطبيق الفلتر على:',
    btnFilterBg: '🖼️ الخلفية',
    btnFilterFace: '🍉 الوجه',
    btnFilterAcc: '🎀 الملصق',
    lblFilterPresets: 'فلاتر سريعة جاهزة:',
    presetNormal: 'عادي',
    presetBw: '🖤 أبيض وأسود',
    presetSepia: '📜 كلاسيكي',
    presetInvert: '🔮 عكس الألوان',
    presetShift: '🌈 تدوير الألوان',
    presetVivid: '⚡ ألوان مشبعة',
    presetCyber: '🌆 سايبر نيون',
    presetWarm: '🔥 دافئ',
    lblFilterHue: 'تدوير / إزاحة اللون:',
    lblFilterBw: 'أبيض وأسود (رمادي):',
    lblFilterBrightness: 'السطوع:',
    lblFilterContrast: 'التباين:',
    lblFilterSaturate: 'تشبع الألوان:'
  }}
}};

function applyLanguage(lang) {{
  const t = i18n[lang];
  currentLang = lang;
  if (lang === 'ar') {{
    document.body.classList.add('lang-ar');
    document.getElementById('psApp').classList.add('lang-ar');
  }} else {{
    document.body.classList.remove('lang-ar');
    document.getElementById('psApp').classList.remove('lang-ar');
  }}
  document.getElementById('btnLangToggle').innerText = t.langBtn;
  document.getElementById('appTitle').innerText = t.appTitle;
  document.getElementById('fitScreenBtn').innerText = t.fitScreen;
  document.getElementById('lblTransform').innerText = t.lblTransform;
  document.getElementById('txtShiftTip').innerText = t.shiftTip;
  document.getElementById('btnExportGif').innerText = t.exportGif;
  document.getElementById('btnExportPng').innerText = t.exportPng;
  document.getElementById('btnCopyDiscord').innerText = t.copyDiscord;
  document.getElementById('optFlipBtn').innerText = t.flip;
  document.getElementById('optCenterBtn').innerText = t.center;
  document.getElementById('optDeleteBtn').innerText = t.delete;

  document.getElementById('secTitleBackdrop').innerText = t.secTitleBackdrop;
  document.getElementById('txtUploadBg').innerText = t.txtUploadBg;
  document.getElementById('lblCanvasFormat').innerText = t.lblCanvasFormat;
  document.getElementById('btnTrueSize').innerText = t.trueSize;
  document.getElementById('lblPopularTemplates').innerText = t.lblPopularTemplates;

  document.getElementById('secTitleFaces').innerText = t.secTitleFaces;
  document.getElementById('txtUploadFace').innerText = t.txtUploadFace;
  document.getElementById('lblDefaultFaces').innerText = t.lblDefaultFaces;
  document.getElementById('addFaceBtn').innerText = t.addFaceBtn;
  document.getElementById('lblCutoutShape').innerText = t.lblCutoutShape;
  document.getElementById('btnFullFrame').innerText = t.btnFullFrame;
  document.getElementById('btnOval').innerText = t.btnOval;
  document.getElementById('lblFaceOpacity').innerText = t.lblFaceOpacity;

  document.getElementById('secTitleText').innerText = t.secTitleText;
  document.getElementById('addTopTextBtn').innerText = t.addTopTextBtn;
  document.getElementById('addBottomTextBtn').innerText = t.addBottomTextBtn;
  document.getElementById('addCustomTextBtn').innerText = t.addCustomTextBtn;
  document.getElementById('activeTextInput').placeholder = t.textPlaceholder;
  document.getElementById('lblFont').innerText = t.lblFont;
  document.getElementById('lblFontSize').innerText = t.lblFontSize;
  document.getElementById('lblTextColor').innerText = t.lblTextColor;
  document.getElementById('colorWheelBtn').innerText = t.wheelColor;

  document.getElementById('secTitleStickers').innerText = t.secTitleStickers;
  document.getElementById('txtUploadSticker').innerText = t.txtUploadSticker;
  document.getElementById('lblStickerOpacity').innerText = t.lblStickerOpacity;

  document.getElementById('secTitleAnim').innerText = t.secTitleAnim;
  document.getElementById('animStill').innerText = t.animStill;
  document.getElementById('animBob').innerText = t.animBob;
  document.getElementById('animShake').innerText = t.animShake;
  document.getElementById('animSpin').innerText = t.animSpin;
  document.getElementById('animPetpet').innerText = t.animPetpet;
  document.getElementById('animPulse').innerText = t.animPulse;
  document.getElementById('animHeart').innerText = t.animHeart;
  document.getElementById('animWobble').innerText = t.animWobble;
  document.getElementById('animDisco').innerText = t.animDisco;

  document.getElementById('secTitleLayers').innerText = t.secTitleLayers;
  const emptyNotice = document.getElementById('emptyFacesNotice');
  if (emptyNotice) {{
    emptyNotice.innerText = lang === 'ar' ? 'لا توجد وجوه افتراضية. ارفع فاكهة أو صورة مخصصة بالأعلى للبدء!' : 'No default faces. Upload a custom fruit or photo above to start!';
  }}

  // Filters section translations
  if (document.getElementById('secTitleFilters')) {{
    document.getElementById('secTitleFilters').innerText = t.secTitleFilters;
    document.getElementById('resetFiltersBtn').innerText = t.resetFilters;
    document.getElementById('lblFilterTarget').innerText = t.lblFilterTarget;
    document.getElementById('btnFilterBg').innerText = t.btnFilterBg;
    document.getElementById('btnFilterFace').innerText = t.btnFilterFace;
    document.getElementById('btnFilterAcc').innerText = t.btnFilterAcc;
    document.getElementById('lblFilterPresets').innerText = t.lblFilterPresets;
    document.getElementById('presetNormal').innerText = t.presetNormal;
    document.getElementById('presetBw').innerText = t.presetBw;
    document.getElementById('presetSepia').innerText = t.presetSepia;
    document.getElementById('presetInvert').innerText = t.presetInvert;
    document.getElementById('presetShift').innerText = t.presetShift;
    document.getElementById('presetVivid').innerText = t.presetVivid;
    document.getElementById('presetCyber').innerText = t.presetCyber;
    document.getElementById('presetWarm').innerText = t.presetWarm;
    document.getElementById('lblFilterHue').innerText = t.lblFilterHue;
    document.getElementById('lblFilterBw').innerText = t.lblFilterBw;
    document.getElementById('lblFilterBrightness').innerText = t.lblFilterBrightness;
    document.getElementById('lblFilterContrast').innerText = t.lblFilterContrast;
    document.getElementById('lblFilterSaturate').innerText = t.lblFilterSaturate;
  }}
  syncFilterUI();
  updateTopbarToolOptions();
  syncLayersUI();
}}

function makeDefaultFilters() {{
  return {{
    hue: 0,
    grayscale: 0,
    brightness: 100,
    contrast: 100,
    saturate: 100,
    invert: 0,
    sepia: 0
  }};
}}

function getFilterString(f) {{
  if (!f) return 'none';
  const parts = [];
  if (f.grayscale) parts.push('grayscale(' + f.grayscale + '%)');
  if (f.sepia) parts.push('sepia(' + f.sepia + '%)');
  if (f.invert) parts.push('invert(' + f.invert + '%)');
  if (f.hue) parts.push('hue-rotate(' + f.hue + 'deg)');
  if (f.brightness !== undefined && f.brightness !== 100) parts.push('brightness(' + f.brightness + '%)');
  if (f.contrast !== undefined && f.contrast !== 100) parts.push('contrast(' + f.contrast + '%)');
  if (f.saturate !== undefined && f.saturate !== 100) parts.push('saturate(' + f.saturate + '%)');
  return parts.length ? parts.join(' ') : 'none';
}}

function makeFaceLayer(faceIndex, x, y, scale, z) {{
  return {{
    id: 'layer_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
    faceIndex: faceIndex !== undefined ? faceIndex : 0,
    x: x !== undefined ? x : 0,
    y: y !== undefined ? y : -50,
    scale: scale !== undefined ? scale : 1.0,
    scaleX: scale !== undefined ? scale : 1.0,
    scaleY: scale !== undefined ? scale : 1.0,
    rotation: 0,
    flipH: 1,
    opacity: 1.0,
    maskShape: 'square',
    customImg: null,
    filters: makeDefaultFilters(),
    z: z !== undefined ? z : ++layerZCounter
  }};
}}

// DEFAULT STATE
const state = {{
  facesOnCanvas: [],
  selectedFaceIdx: -1,

  bgType: 'template',
  bgTemplateId: 'suit',
  bgCustomImg: null,
  bgIsGif: false,
  bgGifFrames: [],
  bgGifIndex: 0,
  bgFilters: makeDefaultFilters(),

  canvasSizeMode: 'true_size',

  texts: [],
  selectedTextIdx: -1,

  accessoriesOnCanvas: [],
  selectedAccIdx: -1,

  animation: 'none',

  activeTransformTarget: null,
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
  const availW = Math.max(260, vp.clientWidth - pad);
  const availH = Math.max(260, vp.clientHeight - pad);
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

// --- ACTIVE LAYER GETTER (WITH NON-UNIFORM STRETCH SUPPORT) ---
function getActiveLayerData() {{
  const t = state.activeTransformTarget;
  if (!t) return null;
  if (t.type === 'face' && state.facesOnCanvas[t.idx]) {{
    const face = state.facesOnCanvas[t.idx];
    let img = face.customImg || loadedFaces[face.faceIndex];
    const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
    const sx = face.scaleX !== undefined ? face.scaleX : (face.scale || 1.0);
    const sy = face.scaleY !== undefined ? face.scaleY : (face.scale || 1.0);
    const baseW = 200;
    const baseH = 200 * aspect;
    const hw = (baseW * sx) / 2;
    const hh = (baseH * sy) / 2;
    return {{
      type: 'face',
      idx: t.idx,
      obj: face,
      cx: canvas.width / 2 + face.x,
      cy: canvas.height / 2 + face.y,
      hw: hw,
      hh: hh,
      baseW: baseW,
      baseH: baseH,
      rotation: face.rotation || 0,
      scaleX: sx,
      scaleY: sy
    }};
  }}
  if (t.type === 'acc' && state.accessoriesOnCanvas[t.idx]) {{
    const acc = state.accessoriesOnCanvas[t.idx];
    const aspect = (acc.img && acc.img.naturalHeight) ? (acc.img.naturalHeight / acc.img.naturalWidth) : 1.0;
    const sx = acc.scaleX !== undefined ? acc.scaleX : (acc.scale || 1.0);
    const sy = acc.scaleY !== undefined ? acc.scaleY : (acc.scale || 1.0);
    const baseW = 180;
    const baseH = 180 * aspect;
    const hw = (baseW * sx) / 2;
    const hh = (baseH * sy) / 2;
    return {{
      type: 'acc',
      idx: t.idx,
      obj: acc,
      cx: canvas.width / 2 + acc.x,
      cy: canvas.height / 2 + acc.y,
      hw: hw,
      hh: hh,
      baseW: baseW,
      baseH: baseH,
      rotation: acc.rotation || 0,
      scaleX: sx,
      scaleY: sy
    }};
  }}
  if (t.type === 'text' && state.texts[t.idx]) {{
    const txt = state.texts[t.idx];
    const fontFam = txt.font || 'Impact, sans-serif';
    ctx.font = '900 ' + txt.size + 'px ' + fontFam;
    const metrics = ctx.measureText(txt.text || ' ');
    const sx = txt.scaleX !== undefined ? txt.scaleX : 1.0;
    const sy = txt.scaleY !== undefined ? txt.scaleY : 1.0;
    const bw = (metrics.width + 24) * sx;
    const bh = (txt.size + 14) * sy;
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
      bw: metrics.width + 24,
      bh: txt.size + 14,
      rotation: txt.rotation || 0,
      scaleX: sx,
      scaleY: sy
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

// Hit test handles & bounding box
function testHandlesHit(mx, my, layerData) {{
  if (!layerData) return null;
  const {{ cx, cy, hw, hh, rotation }} = layerData;
  const {{ lx, ly }} = toLocal(mx, my, cx, cy, rotation);

  // 1. Rotation handle: at (0, -hh - 18)
  const rotDist = Math.hypot(lx - 0, ly - (-hh - 18));
  if (rotDist <= 14) {{
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
    if (Math.abs(lx - c.x) <= 12 && Math.abs(ly - c.y) <= 12) {{
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
  const active = getActiveLayerData();
  if (active) {{
    const h = testHandlesHit(mx, my, active);
    if (h) return {{ handle: h, layer: active }};
  }}

  const all = getAllLayers();
  for (let item of all) {{
    const {{ layerType, idx, obj }} = item;
    let hw = 50, hh = 50, cx = canvas.width / 2 + obj.x, cy = canvas.height / 2 + obj.y, rot = obj.rotation || 0;
    if (layerType === 'face') {{
      let img = obj.customImg || loadedFaces[obj.faceIndex];
      const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
      const sx = obj.scaleX !== undefined ? obj.scaleX : (obj.scale || 1.0);
      const sy = obj.scaleY !== undefined ? obj.scaleY : (obj.scale || 1.0);
      hw = (200 * sx) / 2;
      hh = (200 * aspect * sy) / 2;
    }} else if (layerType === 'acc') {{
      const aspect = (obj.img && obj.img.naturalHeight) ? (obj.img.naturalHeight / obj.img.naturalWidth) : 1.0;
      const sx = obj.scaleX !== undefined ? obj.scaleX : (obj.scale || 1.0);
      const sy = obj.scaleY !== undefined ? obj.scaleY : (obj.scale || 1.0);
      hw = (180 * sx) / 2;
      hh = (180 * aspect * sy) / 2;
    }} else if (layerType === 'text') {{
      const fontFam = obj.font || 'Impact, sans-serif';
      ctx.font = '900 ' + obj.size + 'px ' + fontFam;
      const metrics = ctx.measureText(obj.text || ' ');
      const sx = obj.scaleX !== undefined ? obj.scaleX : 1.0;
      const sy = obj.scaleY !== undefined ? obj.scaleY : 1.0;
      hw = ((metrics.width + 24) * sx) / 2;
      hh = ((obj.size + 14) * sy) / 2;
    }}

    const {{ lx, ly }} = toLocal(mx, my, cx, cy, rot);
    if (Math.abs(lx) <= hw && Math.abs(ly) <= hh) {{
      return {{ handle: 'body', layer: {{ type: layerType, idx: idx }} }};
    }}
  }}

  return null;
}}

// Get all layers unified and sorted by Z (top to bottom)
function getAllLayers() {{
  const all = [];
  state.facesOnCanvas.forEach((f, i) => all.push({{ layerType: 'face', idx: i, obj: f, z: f.z || 1 }}));
  state.accessoriesOnCanvas.forEach((a, i) => all.push({{ layerType: 'acc', idx: i, obj: a, z: a.z || 1 }}));
  state.texts.forEach((t, i) => all.push({{ layerType: 'text', idx: i, obj: t, z: t.z || 1 }}));
  all.sort((a, b) => (b.z || 1) - (a.z || 1));
  return all;
}}

// --- RENDER CANVAS ---
function render(offsetObj) {{
  const animOff = offsetObj || {{ x: 0, y: 0, rot: 0, scale: 1.0 }};

  let bgImg = null;
  if (state.bgType === 'custom' && state.bgCustomImg) {{
    bgImg = state.bgCustomImg;
  }} else if (state.bgIsGif && state.bgGifFrames.length > 0) {{
    bgImg = state.bgGifFrames[state.bgGifIndex];
  }} else if (state.bgType === 'template' && loadedTemplates[state.bgTemplateId]) {{
    bgImg = loadedTemplates[state.bgTemplateId];
  }}

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
  ctx.save();
  ctx.filter = getFilterString(state.bgFilters);
  if (bgImg) {{
    ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);
  }} else {{
    ctx.fillStyle = '#060608';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
  }}
  ctx.restore();

  // 2. Render Layers in exact Z order (back to front)
  const drawList = getAllLayers().reverse();
  drawList.forEach(item => {{
    const {{ layerType, obj }} = item;

    if (layerType === 'face') {{
      let img = obj.customImg || loadedFaces[obj.faceIndex];
      if (!img) return;

      ctx.save();
      ctx.filter = getFilterString(obj.filters);
      const cx = canvas.width / 2 + obj.x + animOff.x;
      const cy = canvas.height / 2 + obj.y + animOff.y;
      ctx.translate(cx, cy);
      ctx.rotate(((obj.rotation + animOff.rot) * Math.PI) / 180);
      ctx.scale(obj.flipH || 1, 1);
      ctx.globalAlpha = obj.opacity !== undefined ? obj.opacity : 1.0;

      const aspect = (img.naturalHeight || 1) / (img.naturalWidth || 1);
      const sx = obj.scaleX !== undefined ? obj.scaleX : (obj.scale || 1.0);
      const sy = obj.scaleY !== undefined ? obj.scaleY : (obj.scale || 1.0);
      const baseW = 200;
      const baseH = 200 * aspect;
      const w = baseW * sx * animOff.scale;
      const h = baseH * sy * animOff.scale;

      if (obj.maskShape === 'oval') {{
        ctx.beginPath();
        ctx.ellipse(0, 0, w / 2, h / 2, 0, 0, Math.PI * 2);
        ctx.closePath();
        ctx.clip();
      }}

      ctx.drawImage(img, -w / 2, -h / 2, w, h);
      ctx.restore();
    }} else if (layerType === 'acc') {{
      if (!obj.img) return;
      ctx.save();
      ctx.filter = getFilterString(obj.filters);
      const cx = canvas.width / 2 + obj.x;
      const cy = canvas.height / 2 + obj.y;
      ctx.translate(cx, cy);
      ctx.rotate((obj.rotation * Math.PI) / 180);
      ctx.scale(obj.flipH || 1, 1);
      ctx.globalAlpha = obj.opacity !== undefined ? obj.opacity : 1.0;

      const aspect = (obj.img.naturalHeight || 1) / (obj.img.naturalWidth || 1);
      const sx = obj.scaleX !== undefined ? obj.scaleX : (obj.scale || 1.0);
      const sy = obj.scaleY !== undefined ? obj.scaleY : (obj.scale || 1.0);
      const baseW = 180;
      const baseH = 180 * aspect;
      const w = baseW * sx;
      const h = baseH * sy;

      ctx.drawImage(obj.img, -w / 2, -h / 2, w, h);
      ctx.restore();
    }} else if (layerType === 'text') {{
      ctx.save();
      const cx = canvas.width / 2 + obj.x;
      const cy = canvas.height / 2 + obj.y;
      ctx.translate(cx, cy);
      ctx.rotate((obj.rotation * Math.PI) / 180);
      const sx = obj.scaleX !== undefined ? obj.scaleX : 1.0;
      const sy = obj.scaleY !== undefined ? obj.scaleY : 1.0;
      ctx.scale(sx, sy);

      const fontFam = obj.font || 'Impact, sans-serif';
      ctx.font = '900 ' + obj.size + 'px ' + fontFam;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.lineWidth = Math.max(5, Math.round(obj.size / 6.5));
      ctx.strokeStyle = '#000000';
      ctx.fillStyle = obj.color || '#ffffff';

      ctx.strokeText(obj.text, 0, 0);
      ctx.fillText(obj.text, 0, 0);
      ctx.restore();
    }}
  }});

  // 3. Draw Refined Compact Free Transform Bounding Box & Handles
  const active = getActiveLayerData();
  if (active) {{
    const {{ cx, cy, hw, hh, rotation }} = active;
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((rotation * Math.PI) / 180);

    // Slim dashed bounding rectangle
    ctx.strokeStyle = '#0084ff';
    ctx.lineWidth = 1.5;
    ctx.setLineDash([4, 4]);
    ctx.strokeRect(-hw, -hh, hw * 2, hh * 2);

    // Short stem line to rotation handle
    ctx.setLineDash([]);
    ctx.beginPath();
    ctx.moveTo(0, -hh);
    ctx.lineTo(0, -hh - 18);
    ctx.stroke();

    // Small circular rotation handle
    ctx.fillStyle = '#ffffff';
    ctx.strokeStyle = '#0084ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(0, -hh - 18, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // 4 Small corner square handles (8x8)
    const corners = [
      [-hw, -hh],
      [hw, -hh],
      [-hw, hh],
      [hw, hh]
    ];
    corners.forEach(([kx, ky]) => {{
      ctx.fillStyle = '#ffffff';
      ctx.strokeStyle = '#0084ff';
      ctx.lineWidth = 1.5;
      ctx.fillRect(kx - 4, ky - 4, 8, 8);
      ctx.strokeRect(kx - 4, ky - 4, 8, 8);
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
    nameBadge.innerText = i18n[currentLang].noLayer;
    actionGroup.style.display = 'none';
    return;
  }}

  actionGroup.style.display = 'inline-flex';
  let title = 'Layer';
  if (active.type === 'face') {{
    const f = faces[active.obj.faceIndex];
    title = f ? f.name : (currentLang === 'ar' ? 'فاكهة مخصصة' : 'Custom Face');
    const sx = Math.round((active.obj.scaleX || active.obj.scale || 1.0) * 100);
    const sy = Math.round((active.obj.scaleY || active.obj.scale || 1.0) * 100);
    scaleVal.innerText = sx === sy ? (sx + '%') : (sx + '% × ' + sy + '%');
    rotVal.innerText = Math.round(active.obj.rotation || 0) + '°';
  }} else if (active.type === 'acc') {{
    title = currentLang === 'ar' ? 'ملصق' : 'Sticker / Acc';
    const sx = Math.round((active.obj.scaleX || active.obj.scale || 1.0) * 100);
    const sy = Math.round((active.obj.scaleY || active.obj.scale || 1.0) * 100);
    scaleVal.innerText = sx === sy ? (sx + '%') : (sx + '% × ' + sy + '%');
    rotVal.innerText = Math.round(active.obj.rotation || 0) + '°';
  }} else if (active.type === 'text') {{
    title = '"' + active.obj.text.substring(0, 14) + '"';
    scaleVal.innerText = active.obj.size + 'px';
    rotVal.innerText = Math.round(active.obj.rotation || 0) + '°';
  }}
  nameBadge.innerText = title;
}}

// --- INTERACTIVE DRAG & FREE TRANSFORM EVENTS (WITH SHIFT-STRETCH) ---
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
        origObjState = {{ x: obj.x, y: obj.y, scale: obj.scale || 1.0, scaleX: obj.scaleX || obj.scale || 1.0, scaleY: obj.scaleY || obj.scale || 1.0, rotation: obj.rotation || 0 }};
      }} else if (hit.layer.type === 'acc') {{
        state.activeTransformTarget = {{ type: 'acc', idx: hit.layer.idx }};
        state.selectedAccIdx = hit.layer.idx;
        const obj = state.accessoriesOnCanvas[hit.layer.idx];
        origObjState = {{ x: obj.x, y: obj.y, scale: obj.scale || 1.0, scaleX: obj.scaleX || obj.scale || 1.0, scaleY: obj.scaleY || obj.scale || 1.0, rotation: obj.rotation || 0 }};
      }} else if (hit.layer.type === 'text') {{
        state.activeTransformTarget = {{ type: 'text', idx: hit.layer.idx }};
        state.selectedTextIdx = hit.layer.idx;
        const obj = state.texts[hit.layer.idx];
        origObjState = {{ x: obj.x, y: obj.y, size: obj.size, scaleX: obj.scaleX || 1.0, scaleY: obj.scaleY || 1.0, rotation: obj.rotation || 0 }};
        document.getElementById('activeTextInput').value = obj.text;
        document.getElementById('fontFamilySelect').value = obj.font || 'Impact, sans-serif';
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
      // CORNER SCALE OR SHIFT-STRETCH
      if (e.shiftKey) {{
        // Non-uniform STRETCH
        const {{ lx, ly }} = toLocal(mx, my, active.cx, active.cy, active.rotation);
        let newHw = Math.max(12, Math.abs(lx));
        let newHh = Math.max(12, Math.abs(ly));

        if (active.type === 'face') {{
          let img = active.obj.customImg || loadedFaces[active.obj.faceIndex];
          const aspect = (img && img.naturalHeight) ? (img.naturalHeight / img.naturalWidth) : 1.0;
          active.obj.scaleX = Number((newHw / 100).toFixed(2));
          active.obj.scaleY = Number((newHh / (100 * aspect)).toFixed(2));
          active.obj.scale = (active.obj.scaleX + active.obj.scaleY) / 2;
        }} else if (active.type === 'acc') {{
          const aspect = (active.obj.img && active.obj.img.naturalHeight) ? (active.obj.img.naturalHeight / active.obj.img.naturalWidth) : 1.0;
          active.obj.scaleX = Number((newHw / 90).toFixed(2));
          active.obj.scaleY = Number((newHh / (90 * aspect)).toFixed(2));
          active.obj.scale = (active.obj.scaleX + active.obj.scaleY) / 2;
        }} else if (active.type === 'text') {{
          active.obj.scaleX = Number((newHw / (active.bw / 2)).toFixed(2));
          active.obj.scaleY = Number((newHh / (active.bh / 2)).toFixed(2));
        }}
        render();
      }} else {{
        // Uniform proportional scale
        const initialDist = Math.hypot(startX - active.cx, startY - active.cy);
        const currentDist = Math.hypot(mx - active.cx, my - active.cy);
        const factor = currentDist / Math.max(initialDist, 1);
        
        if (active.type === 'text') {{
          active.obj.size = Math.max(16, Math.min(130, Math.round(origObjState.size * factor)));
        }} else {{
          const s = Math.max(0.15, Math.min(3.5, Number((origObjState.scale * factor).toFixed(2))));
          active.obj.scale = s;
          active.obj.scaleX = s;
          active.obj.scaleY = s;
        }}
        render();
      }}
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
      const s = Math.max(0.2, Math.min(3.5, Number(((active.obj.scale || 1.0) + delta).toFixed(2))));
      active.obj.scale = s;
      active.obj.scaleX = s;
      active.obj.scaleY = s;
    }}
    render();
  }}, {{ passive: false }});
}}

// --- POPULATE SIDEBARS & EVENTS ---
function initUIEvents() {{
  // 1. Templates Grid (SHORTER COMPACT 60px CARDS)
  const bgGrid = document.getElementById('bgPresetsRow');
  bgGrid.innerHTML = '';
  templates.forEach(t => {{
    const card = document.createElement('div');
    card.className = 'grid-card-template' + (t.id === 'suit' ? ' active' : '');
    card.innerHTML = `<img src="${{t.src}}" alt="${{t.name}}"><span>${{t.name}}</span>`;
    card.onclick = () => {{
      document.querySelectorAll('#bgPresetsRow .grid-card-template').forEach(c => c.classList.remove('active'));
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

  // 2. Populate Fruits Faces Grid
  const facesGrid = document.getElementById('facesGrid');
  facesGrid.innerHTML = '';
  if (faces.length === 0) {{
    const emptyNotice = document.createElement('div');
    emptyNotice.id = 'emptyFacesNotice';
    emptyNotice.style.cssText = 'grid-column: 1 / -1; padding: 14px 10px; text-align: center; color: var(--ps-text-muted); font-size: 11.5px; border: 1px dashed var(--ps-border); border-radius: 6px; background: rgba(255,255,255,0.02); line-height: 1.5;';
    emptyNotice.innerText = currentLang === 'ar' ? 'لا توجد وجوه افتراضية. ارفع فاكهة أو صورة مخصصة بالأعلى للبدء!' : 'No default faces. Upload a custom fruit or photo above to start!';
    facesGrid.appendChild(emptyNotice);
  }} else {{
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
  }}

  // Add Face Button
  document.getElementById('addFaceBtn').onclick = () => {{
    if (faces.length === 0) {{
      document.getElementById('faceFileInput').click();
      return;
    }}
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

  // Mask Shape Toggles (Sticker circle removed)
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

  // Face Opacity Slider
  document.getElementById('faceOpacitySlider').oninput = (e) => {{
    const val = parseFloat(e.target.value);
    document.getElementById('faceOpacityVal').innerText = Math.round(val * 100) + '%';
    const active = getActiveLayerData();
    if (active && active.type === 'face') {{
      active.obj.opacity = val;
      render();
    }}
  }};

  // 3. Text Controls (Top, Bottom, Custom)
  document.getElementById('addTopTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'TOP TEXT', x: 0, y: -Math.round(canvas.height * 0.35), size: 52, color: '#ffffff', font: document.getElementById('fontFamilySelect').value, rotation: 0, z: ++layerZCounter }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'TOP TEXT';
    render();
    syncLayersUI();
  }};
  document.getElementById('addBottomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'BOTTOM TEXT', x: 0, y: Math.round(canvas.height * 0.35), size: 52, color: '#ffffff', font: document.getElementById('fontFamilySelect').value, rotation: 0, z: ++layerZCounter }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'BOTTOM TEXT';
    render();
    syncLayersUI();
  }};
  document.getElementById('addCustomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'YOUR TEXT', x: 0, y: 0, size: 52, color: '#ffffff', font: document.getElementById('fontFamilySelect').value, rotation: 0, z: ++layerZCounter }});
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
          font: document.getElementById('fontFamilySelect').value,
          rotation: 0,
          z: ++layerZCounter
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

  // Font Selection Change
  document.getElementById('fontFamilySelect').onchange = (e) => {{
    const active = getActiveLayerData();
    if (active && active.type === 'text') {{
      active.obj.font = e.target.value;
      render();
    }}
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

  // Text Colors (including Color Wheel)
  document.querySelectorAll('#textColorGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      if (btn.id === 'colorWheelBtn') {{
        document.getElementById('nativeColorPicker').click();
        return;
      }}
      document.querySelectorAll('#textColorGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const active = getActiveLayerData();
      if (active && active.type === 'text') {{
        active.obj.color = btn.dataset.color;
        render();
      }}
    }};
  }});

  // Native Color Picker Wheel Input
  document.getElementById('nativeColorPicker').oninput = (e) => {{
    const color = e.target.value;
    const wheelBtn = document.getElementById('colorWheelBtn');
    document.querySelectorAll('#textColorGroup .btn-toggle').forEach(b => b.classList.remove('active'));
    wheelBtn.classList.add('active');
    wheelBtn.style.color = color;
    wheelBtn.style.borderColor = color;

    const active = getActiveLayerData();
    if (active && active.type === 'text') {{
      active.obj.color = color;
      render();
    }}
  }};

  // --- COLOR FILTERS & ADJUSTMENTS CONTROLLER ---
  let currentFilterTarget = 'bg';

  window.getActiveFilterTargetObj = function() {{
    if (currentFilterTarget === 'bg') {{
      if (!state.bgFilters) state.bgFilters = makeDefaultFilters();
      return state.bgFilters;
    }}
    if (currentFilterTarget === 'face') {{
      const active = getActiveLayerData();
      if (active && active.type === 'face') {{
        if (!active.obj.filters) active.obj.filters = makeDefaultFilters();
        return active.obj.filters;
      }}
      if (state.facesOnCanvas.length > 0) {{
        const f0 = state.facesOnCanvas[0];
        if (!f0.filters) f0.filters = makeDefaultFilters();
        return f0.filters;
      }}
      return null;
    }}
    if (currentFilterTarget === 'acc') {{
      const active = getActiveLayerData();
      if (active && active.type === 'acc') {{
        if (!active.obj.filters) active.obj.filters = makeDefaultFilters();
        return active.obj.filters;
      }}
      if (state.accessoriesOnCanvas.length > 0) {{
        const a0 = state.accessoriesOnCanvas[0];
        if (!a0.filters) a0.filters = makeDefaultFilters();
        return a0.filters;
      }}
      return null;
    }}
    return null;
  }};

  window.syncFilterUI = function() {{
    const f = getActiveFilterTargetObj();
    const box = document.getElementById('filterSlidersBox');
    const notice = document.getElementById('filterNoTargetNotice');
    if (!f) {{
      if (box) box.style.opacity = '0.35';
      if (notice) {{
        notice.style.display = 'block';
        notice.innerText = currentFilterTarget === 'face'
          ? (currentLang === 'ar' ? '⚠️ لا يوجد وجه على الكانفاس. أضف وجهاً أولاً!' : '⚠️ No face layer on canvas. Add a face first!')
          : (currentLang === 'ar' ? '⚠️ لا يوجد ملصق على الكانفاس. ارفع ملصقاً أولاً!' : '⚠️ No sticker on canvas. Upload a sticker first!');
      }}
      return;
    }}
    if (box) box.style.opacity = '1.0';
    if (notice) notice.style.display = 'none';

    document.getElementById('sliderFilterHue').value = f.hue || 0;
    document.getElementById('valFilterHue').innerText = (f.hue || 0) + '°';

    document.getElementById('sliderFilterBw').value = f.grayscale || 0;
    document.getElementById('valFilterBw').innerText = (f.grayscale || 0) + '%';

    document.getElementById('sliderFilterBrightness').value = f.brightness !== undefined ? f.brightness : 100;
    document.getElementById('valFilterBrightness').innerText = (f.brightness !== undefined ? f.brightness : 100) + '%';

    document.getElementById('sliderFilterContrast').value = f.contrast !== undefined ? f.contrast : 100;
    document.getElementById('valFilterContrast').innerText = (f.contrast !== undefined ? f.contrast : 100) + '%';

    document.getElementById('sliderFilterSaturate').value = f.saturate !== undefined ? f.saturate : 100;
    document.getElementById('valFilterSaturate').innerText = (f.saturate !== undefined ? f.saturate : 100) + '%';
  }};

  const filterPresetDefs = {{
    normal: {{ hue: 0, grayscale: 0, brightness: 100, contrast: 100, saturate: 100, invert: 0, sepia: 0 }},
    bw: {{ hue: 0, grayscale: 100, brightness: 100, contrast: 110, saturate: 100, invert: 0, sepia: 0 }},
    sepia: {{ hue: 0, grayscale: 0, brightness: 95, contrast: 100, saturate: 90, invert: 0, sepia: 85 }},
    invert: {{ hue: 0, grayscale: 0, brightness: 100, contrast: 100, saturate: 100, invert: 100, sepia: 0 }},
    shift: {{ hue: 180, grayscale: 0, brightness: 100, contrast: 100, saturate: 120, invert: 0, sepia: 0 }},
    vivid: {{ hue: 0, grayscale: 0, brightness: 105, contrast: 130, saturate: 160, invert: 0, sepia: 0 }},
    cyber: {{ hue: 280, grayscale: 0, brightness: 110, contrast: 135, saturate: 170, invert: 0, sepia: 0 }},
    warm: {{ hue: 25, grayscale: 0, brightness: 105, contrast: 105, saturate: 130, invert: 0, sepia: 20 }}
  }};

  document.querySelectorAll('#filterPresetsGrid .ps-opt-btn').forEach(btn => {{
    btn.onclick = () => {{
      const presetKey = btn.getAttribute('data-preset');
      const f = getActiveFilterTargetObj();
      if (!f || !filterPresetDefs[presetKey]) return;
      Object.assign(f, filterPresetDefs[presetKey]);
      document.querySelectorAll('#filterPresetsGrid .ps-opt-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      syncFilterUI();
      render();
    }};
  }});

  ['bg', 'face', 'acc'].forEach(tgt => {{
    const btn = document.getElementById('btnFilter' + tgt.charAt(0).toUpperCase() + tgt.slice(1));
    if (btn) {{
      btn.onclick = () => {{
        currentFilterTarget = tgt;
        document.querySelectorAll('#filterTargetGroup .btn-toggle').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        syncFilterUI();
      }};
    }}
  }});

  document.getElementById('sliderFilterHue').oninput = (e) => {{
    const f = getActiveFilterTargetObj();
    if (!f) return;
    f.hue = parseInt(e.target.value);
    document.getElementById('valFilterHue').innerText = f.hue + '°';
    render();
  }};

  document.getElementById('sliderFilterBw').oninput = (e) => {{
    const f = getActiveFilterTargetObj();
    if (!f) return;
    f.grayscale = parseInt(e.target.value);
    document.getElementById('valFilterBw').innerText = f.grayscale + '%';
    render();
  }};

  document.getElementById('sliderFilterBrightness').oninput = (e) => {{
    const f = getActiveFilterTargetObj();
    if (!f) return;
    f.brightness = parseInt(e.target.value);
    document.getElementById('valFilterBrightness').innerText = f.brightness + '%';
    render();
  }};

  document.getElementById('sliderFilterContrast').oninput = (e) => {{
    const f = getActiveFilterTargetObj();
    if (!f) return;
    f.contrast = parseInt(e.target.value);
    document.getElementById('valFilterContrast').innerText = f.contrast + '%';
    render();
  }};

  document.getElementById('sliderFilterSaturate').oninput = (e) => {{
    const f = getActiveFilterTargetObj();
    if (!f) return;
    f.saturate = parseInt(e.target.value);
    document.getElementById('valFilterSaturate').innerText = f.saturate + '%';
    render();
  }};

  document.getElementById('resetFiltersBtn').onclick = () => {{
    const f = getActiveFilterTargetObj();
    if (!f) return;
    Object.assign(f, makeDefaultFilters());
    document.querySelectorAll('#filterPresetsGrid .ps-opt-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('presetNormal').classList.add('active');
    syncFilterUI();
    render();
  }};

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
          scaleX: 1.0,
          scaleY: 1.0,
          rotation: 0,
          flipH: 1,
          opacity: 1.0,
          filters: makeDefaultFilters(),
          z: ++layerZCounter
        }});
        state.activeTransformTarget = {{ type: 'acc', idx: state.accessoriesOnCanvas.length - 1 }};
        render();
        syncLayersUI();
      }};
    }};
    reader.readAsDataURL(file);
  }};

  // 5. Discord Animation Grid Chips
  document.querySelectorAll('#animGrid .anim-chip').forEach(card => {{
    card.onclick = () => {{
      document.querySelectorAll('#animGrid .anim-chip').forEach(c => c.classList.remove('active'));
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

  // 7. Topbar Export Buttons & Language Switcher
  document.getElementById('btnExportPng').onclick = exportPng;
  document.getElementById('btnExportGif').onclick = exportGif;
  document.getElementById('btnCopyDiscord').onclick = copyToClipboard;

  document.getElementById('btnLangToggle').onclick = () => {{
    const nextLang = currentLang === 'en' ? 'ar' : 'en';
    applyLanguage(nextLang);
  }};

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
      status.innerText = '⚠️ Please enter a fruit name and select an image.';
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
      status.innerText = '✅ Fruit face added locally!';

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
  syncFilterUI();
}}

// Sync Admin Catalog List
function renderAdminCatalog() {{
  const list = document.getElementById('adminFacesCatalogList');
  if (!list) return;
  list.innerHTML = '';
  if (faces.length === 0) {{
    const emptyRow = document.createElement('div');
    emptyRow.style = 'color:var(--ps-text-muted); font-size:12px; text-align:center; padding:12px;';
    emptyRow.innerText = 'Catalog is empty. Add new fruit faces using the form above!';
    list.appendChild(emptyRow);
  }}
  faces.forEach((f, idx) => {{
    const row = document.createElement('div');
    row.style = 'display:flex; justify-content:space-between; align-items:center; background:#111217; padding:7px 10px; border-radius:6px; border:1px solid #1f2028;';
    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px;">
        <img src="${{f.src}}" style="width:30px; height:30px; border-radius:4px; object-fit:cover;">
        <span style="font-size:12.5px; font-weight:700; color:#fff;">${{f.name}}</span>
      </div>
      <button class="ps-opt-btn danger" style="padding:4px 8px; font-size:11px;" onclick="deleteAdminFace(${{idx}})">Remove</button>
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

  const filePath = 'assets/' + filename;
  const putUrl = `https://api.github.com/repos/${{repo}}/contents/${{filePath}}`;
  
  await fetch(putUrl, {{
    method: 'PUT',
    headers: {{
      'Authorization': 'token ' + GITHUB_TOKEN,
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify({{
      message: 'Add fruit face: ' + faceName,
      content: cleanB64,
      branch: branch
    }})
  }});
}}

// Reorder layer in stack
window.moveLayerZ = function(layerType, idx, dir) {{
  const all = getAllLayers();
  const currentPos = all.findIndex(item => item.layerType === layerType && item.idx === idx);
  if (currentPos === -1) return;
  const targetPos = currentPos + dir;
  if (targetPos < 0 || targetPos >= all.length) return;

  const currentObj = all[currentPos].obj;
  const targetObj = all[targetPos].obj;

  const tempZ = currentObj.z || 1;
  currentObj.z = targetObj.z || 1;
  targetObj.z = tempZ;

  if (currentObj.z === targetObj.z) {{
    currentObj.z += (dir < 0 ? 1 : -1);
  }}

  render();
  syncLayersUI();
}};

// Sync active layers inspector in right sidebar with thumbnails & reorder controls
function syncLayersUI() {{
  const list = document.getElementById('layersList');
  if (!list) return;
  list.innerHTML = '';

  const active = getActiveLayerData();
  const all = getAllLayers();

  if (all.length === 0) {{
    list.innerHTML = `<div style="color:var(--ps-text-muted); font-size:12px; text-align:center; padding:10px 0;">${{i18n[currentLang].noLayers}}</div>`;
    return;
  }}

  all.forEach((item, pos) => {{
    const {{ layerType, idx, obj }} = item;
    const isAct = active && active.type === layerType && active.idx === idx;
    const row = document.createElement('div');
    row.className = 'layer-item' + (isAct ? ' active' : '');

    let thumbHtml = '';
    let titleStr = '';

    if (layerType === 'face') {{
      const faceImg = obj.customImg ? obj.customImg.src : (faces[obj.faceIndex] ? faces[obj.faceIndex].src : '');
      thumbHtml = `<img src="${{faceImg}}" class="layer-thumb" alt="Face">`;
      const fObj = faces[obj.faceIndex];
      titleStr = fObj ? fObj.name : (currentLang === 'ar' ? 'فاكهة مخصصة' : 'Custom Fruit');
    }} else if (layerType === 'acc') {{
      const accImg = obj.img ? obj.img.src : '';
      thumbHtml = `<img src="${{accImg}}" class="layer-thumb" alt="Sticker">`;
      titleStr = (currentLang === 'ar' ? 'ملصق #' : 'Sticker #') + (idx + 1);
    }} else if (layerType === 'text') {{
      thumbHtml = `<span class="layer-text-badge">T</span>`;
      titleStr = '"' + (obj.text || 'Text').substring(0, 14) + '"';
    }}

    const canMoveUp = pos > 0;
    const canMoveDown = pos < all.length - 1;

    row.innerHTML = `
      <div class="layer-left">
        ${{thumbHtml}}
        <span class="layer-title-text">${{titleStr}}</span>
      </div>
      <div class="layer-actions">
        <button class="layer-action-btn" title="Move Up" style="${{canMoveUp ? '' : 'opacity:0.3; pointer-events:none;'}}" onclick="event.stopPropagation(); moveLayerZ('${{layerType}}', ${{idx}}, -1)">▲</button>
        <button class="layer-action-btn" title="Move Down" style="${{canMoveDown ? '' : 'opacity:0.3; pointer-events:none;'}}" onclick="event.stopPropagation(); moveLayerZ('${{layerType}}', ${{idx}}, 1)">▼</button>
        <button class="layer-action-btn" title="Delete Layer" onclick="event.stopPropagation(); deleteSpecificLayer('${{layerType}}', ${{idx}})">🗑️</button>
      </div>
    `;

    row.onclick = () => {{
      state.activeTransformTarget = {{ type: layerType, idx: idx }};
      if (layerType === 'face') state.selectedFaceIdx = idx;
      if (layerType === 'acc') state.selectedAccIdx = idx;
      if (layerType === 'text') {{
        state.selectedTextIdx = idx;
        document.getElementById('activeTextInput').value = obj.text;
        document.getElementById('fontFamilySelect').value = obj.font || 'Impact, sans-serif';
      }}
      render();
      syncLayersUI();
    }};

    list.appendChild(row);
  }});
}}

window.deleteSpecificLayer = function(layerType, idx) {{
  if (layerType === 'face') {{
    state.facesOnCanvas.splice(idx, 1);
  }} else if (layerType === 'acc') {{
    state.accessoriesOnCanvas.splice(idx, 1);
  }} else if (layerType === 'text') {{
    state.texts.splice(idx, 1);
    document.getElementById('activeTextInput').value = '';
  }}
  state.activeTransformTarget = null;
  render();
  syncLayersUI();
}};

// --- EXPORT FUNCTIONS ---
function exportPng() {{
  const prevTarget = state.activeTransformTarget;
  state.activeTransformTarget = null;
  render();

  const link = document.createElement('a');
  link.download = 'frutisator_meme.png';
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
        alert(i18n[currentLang].copiedAlert);
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

// FIXED: Exact Aspect Ratio & High Color Fidelity
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

  const aspect = canvas.width / canvas.height;
  let gifW = 480;
  let gifH = Math.round(gifW / aspect);
  if (gifH > 480) {{
    gifH = 480;
    gifW = Math.round(gifH * aspect);
  }}
  gifW = Math.round(gifW / 2) * 2;
  gifH = Math.round(gifH / 2) * 2;

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

  progText.innerText = 'Encoding Discord GIF (High Quality)...';
  window.gifshot.createGIF({{
    images: frameImages,
    gifWidth: gifW,
    gifHeight: gifH,
    interval: 0.06,
    numWorkers: 4,
    sampleInterval: 2,
    progressCallback: (captureProgress) => {{
      progBar.style.width = Math.round(captureProgress * 100) + '%';
      progText.innerText = 'Encoding GIF: ' + Math.round(captureProgress * 100) + '%';
    }}
  }}, (obj) => {{
    if (!obj.error) {{
      const link = document.createElement('a');
      link.download = 'frutisator_meme.gif';
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

# Render embedded Frutisator Studio
components.html(html_app, height=1000, scrolling=False)
