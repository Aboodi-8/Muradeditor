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
    page_title="Murad Meme Studio | Discord GIF & Meme Maker",
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
        min-height: 92vh !important;
        height: 95vh !important;
        border: none !important;
    }
    .stApp {
        background-color: #121315;
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

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            pass
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

def delete_file_from_github(repo_owner: str, repo_name: str, file_path: str, commit_message: str, token: str) -> tuple[bool, str]:
    clean_token = token.strip()
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "MuradMemeAdmin",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    sha = None
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                sha = data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, ""
        err_body = e.read().decode("utf-8", errors="replace")
        try:
            msg = json.loads(err_body).get("message", err_body)
        except Exception:
            msg = err_body
        return False, f"HTTP {e.code}: {msg}"
    except Exception as e:
        return False, f"Network error: {str(e)}"

    if not sha:
        return True, ""

    payload = {
        "message": commit_message,
        "sha": sha
    }

    del_req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={**headers, "Content-Type": "application/json"},
        method="DELETE"
    )
    try:
        with urllib.request.urlopen(del_req) as resp:
            if resp.status in (200, 204):
                return True, ""
            return False, f"Unexpected response HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return True, ""
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

# --- EMBEDDED CANVAS-FIRST STUDIO APPLICATION ---
html_app = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  :root {{
    --bg-base: #121315;
    --bg-surface: rgba(30, 31, 34, 0.88);
    --bg-drawer: rgba(26, 27, 30, 0.95);
    --bg-input: #111214;
    --border: rgba(255, 255, 255, 0.1);
    --border-hover: rgba(255, 255, 255, 0.25);
    --blurple: #5865F2;
    --blurple-hover: #4752C4;
    --text-main: #f2f3f5;
    --text-muted: #949ba4;
    --green: #23a55a;
    --danger: #da373c;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: radial-gradient(circle at 50% 20%, #1e2024 0%, #121315 100%);
    color: var(--text-main);
    overflow: hidden;
    height: 100vh;
    width: 100vw;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    user-select: none;
    -webkit-user-select: none;
  }}

  /* FULL-BLEED WORKSPACE */
  .workspace {{
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 48px 8px 74px 8px; /* Room for top context pill and bottom floating dock */
  }}

  /* CONTEXT ACTION PILL (HOVERS ABOVE CANVAS) */
  .context-pill {{
    position: absolute;
    top: 10px;
    background: var(--bg-surface);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border: 1px solid var(--border);
    border-radius: 30px;
    padding: 5px 14px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.45);
    z-index: 50;
    max-width: calc(100vw - 20px);
    transition: all 0.2s ease;
  }}
  .pill-badge {{
    background: rgba(88, 101, 242, 0.2);
    color: var(--blurple);
    font-size: 11px;
    font-weight: 700;
    padding: 3px 8px;
    border-radius: 20px;
    white-space: nowrap;
  }}
  .pill-hint {{
    font-size: 11px;
    color: var(--text-muted);
    white-space: nowrap;
  }}
  .pill-tools {{
    display: flex;
    gap: 4px;
    align-items: center;
    border-left: 1px solid var(--border);
    padding-left: 8px;
    flex-shrink: 0;
  }}
  .pill-btn {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 4px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    white-space: nowrap;
    touch-action: manipulation;
  }}
  .pill-btn:hover {{
    border-color: #fff;
    background: rgba(255,255,255,0.08);
  }}
  .pill-btn.danger:hover {{
    background: var(--danger);
    color: #fff;
    border-color: var(--danger);
  }}

  /* BIG DYNAMIC CANVAS STAGE */
  .canvas-stage {{
    position: relative;
    max-width: 96vw;
    max-height: calc(100vh - 128px);
    display: flex;
    align-items: center;
    justify-content: center;
  }}
  #mainCanvas {{
    max-width: 100%;
    max-height: calc(100vh - 128px);
    border-radius: 12px;
    box-shadow: 0 25px 60px rgba(0, 0, 0, 0.65), 0 0 0 1px rgba(255, 255, 255, 0.08);
    cursor: grab;
    display: block;
    object-fit: contain;
    background: #000;
    transition: box-shadow 0.2s ease;
  }}
  #mainCanvas:active {{
    cursor: grabbing;
  }}

  /* FLOATING BOTTOM DOCK */
  .floating-dock-wrap {{
    position: fixed;
    bottom: 12px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    align-items: center;
    z-index: 100;
    width: auto;
    max-width: calc(100vw - 12px);
    pointer-events: none;
  }}

  .floating-dock {{
    background: var(--bg-surface);
    backdrop-filter: blur(28px);
    -webkit-backdrop-filter: blur(28px);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 6px 10px;
    display: flex;
    align-items: center;
    gap: 6px;
    box-shadow: 0 16px 40px rgba(0,0,0,0.6);
    pointer-events: auto;
    max-width: 100%;
    box-sizing: border-box;
  }}

  .dock-tab {{
    background: transparent;
    border: none;
    color: var(--text-muted);
    padding: 7px 10px;
    border-radius: 10px;
    cursor: pointer;
    font-size: 12px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
    white-space: nowrap;
    touch-action: manipulation;
  }}
  .dock-tab:hover {{
    color: #fff;
    background: rgba(255,255,255,0.06);
  }}
  .dock-tab.active {{
    background: var(--blurple);
    color: #fff;
    box-shadow: 0 4px 14px rgba(88,101,242,0.4);
  }}

  .dock-sep {{
    width: 1px;
    height: 20px;
    background: var(--border);
    margin: 0 2px;
    flex-shrink: 0;
  }}

  /* EXPORT BUTTONS ON DOCK */
  .dock-export-gif {{
    background: linear-gradient(135deg, #5865F2, #7289da);
    color: #fff;
    border: none;
    border-radius: 10px;
    padding: 7px 13px;
    font-size: 11.5px;
    font-weight: 800;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    box-shadow: 0 4px 15px rgba(88,101,242,0.35);
    transition: all 0.15s ease;
    white-space: nowrap;
    flex-shrink: 0;
    touch-action: manipulation;
  }}
  .dock-export-gif:hover {{
    transform: translateY(-1px);
    box-shadow: 0 6px 20px rgba(88,101,242,0.5);
  }}
  .dock-export-png {{
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border);
    color: #fff;
    border-radius: 10px;
    padding: 7px 11px;
    font-size: 11.5px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    transition: all 0.15s ease;
    white-space: nowrap;
    flex-shrink: 0;
    touch-action: manipulation;
  }}
  .dock-export-png:hover {{
    border-color: #fff;
    background: rgba(255,255,255,0.15);
  }}
  .dock-copy {{
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border);
    color: #fff;
    border-radius: 10px;
    padding: 7px 10px;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
    white-space: nowrap;
    flex-shrink: 0;
    touch-action: manipulation;
  }}
  .dock-copy:hover {{
    border-color: var(--green);
    color: var(--green);
  }}

  /* SLIDE-UP GLASS DRAWER */
  .glass-drawer {{
    position: absolute;
    bottom: 64px;
    width: 440px;
    max-width: calc(100vw - 20px);
    background: var(--bg-drawer);
    backdrop-filter: blur(32px);
    -webkit-backdrop-filter: blur(32px);
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 14px;
    box-shadow: 0 20px 50px rgba(0,0,0,0.7);
    display: none;
    flex-direction: column;
    gap: 10px;
    max-height: calc(100vh - 120px);
    overflow-y: auto;
    animation: drawerPop 0.18s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    pointer-events: auto;
    box-sizing: border-box;
  }}
  .glass-drawer.open {{
    display: flex;
  }}

  @keyframes drawerPop {{
    0% {{ opacity: 0; transform: translateY(12px) scale(0.97); }}
    100% {{ opacity: 1; transform: translateY(0) scale(1); }}
  }}

  .drawer-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
    padding-bottom: 8px;
  }}
  .drawer-title {{
    font-size: 14px;
    font-weight: 800;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .drawer-close {{
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 14px;
    cursor: pointer;
    font-weight: bold;
    padding: 2px 6px;
    border-radius: 4px;
  }}
  .drawer-close:hover {{ color: #fff; background: rgba(255,255,255,0.1); }}

  /* UPLOAD DROP ZONE */
  .drop-zone {{
    display: block;
    background: rgba(88, 101, 242, 0.08);
    border: 1.5px dashed var(--blurple);
    border-radius: 10px;
    padding: 12px;
    text-align: center;
    color: #fff;
    font-size: 12px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .drop-zone:hover {{
    background: rgba(88, 101, 242, 0.18);
    border-color: #fff;
  }}
  .drop-zone input {{ display: none; }}

  /* GRID OF THUMBNAILS */
  .grid-cards {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }}
  .grid-card {{
    background: rgba(255,255,255,0.04);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .grid-card:hover {{
    border-color: var(--border-hover);
    transform: translateY(-1px);
    background: rgba(255,255,255,0.08);
  }}
  .grid-card.active {{
    border-color: var(--blurple);
    background: rgba(88, 101, 242, 0.2);
  }}
  .grid-card img {{
    width: 60px;
    height: 60px;
    border-radius: 6px;
    object-fit: cover;
    margin-bottom: 4px;
  }}
  .grid-card span {{
    font-size: 10.5px;
    font-weight: 600;
    color: var(--text-main);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  }}

  /* TOGGLE BUTTON GROUPS */
  .btn-group {{
    display: flex;
    background: var(--bg-input);
    border-radius: 8px;
    padding: 3px;
    border: 1px solid var(--border);
    gap: 3px;
    flex-wrap: wrap;
  }}
  .btn-toggle {{
    flex: 1 1 auto;
    min-width: 50px;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    font-weight: 700;
    padding: 6px 8px;
    border-radius: 6px;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: center;
    white-space: nowrap;
    touch-action: manipulation;
  }}
  .btn-toggle.active {{
    background: var(--blurple);
    color: #fff;
  }}

  /* SLIDERS */
  .slider-row {{
    display: flex;
    flex-direction: column;
    gap: 4px;
  }}
  .slider-row label {{
    font-size: 11px;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
    font-weight: 600;
  }}
  .slider-row input[type="range"] {{
    width: 100%;
    accent-color: var(--blurple);
    cursor: pointer;
  }}

  /* INPUTS */
  .text-input-field {{
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: #fff;
    font-size: 12.5px;
    padding: 8px 12px;
    border-radius: 8px;
    outline: none;
  }}
  .text-input-field:focus {{ border-color: var(--blurple); }}

  /* PROGRESS BAR */
  .progress-wrap {{
    position: absolute;
    bottom: 80px;
    background: var(--bg-surface);
    backdrop-filter: blur(24px);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px 18px;
    width: 320px;
    box-shadow: 0 16px 40px rgba(0,0,0,0.6);
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

  /* RESPONSIVE SCALING - GUARANTEE ALL BUTTONS FIT ON ALL SCREENS */
  @media (max-width: 768px) {{
    .workspace {{
      padding: 44px 6px 68px 6px;
    }}
    .context-pill {{
      top: 6px;
      padding: 4px 10px;
      gap: 6px;
    }}
    .pill-hint {{
      display: none; /* Hide instruction text on mobile/tablet so all 7 tools fit */
    }}
    .pill-tools {{
      gap: 3px;
      padding-left: 6px;
    }}
    .pill-btn {{
      padding: 4px 6px;
      font-size: 10px;
    }}
    .floating-dock {{
      padding: 5px 8px;
      gap: 4px;
      border-radius: 16px;
    }}
    .dock-tab {{
      padding: 6px 8px;
      font-size: 11px;
      gap: 4px;
    }}
    .dock-export-gif {{
      padding: 6px 9px;
      font-size: 11px;
    }}
    .dock-export-png {{
      padding: 6px 8px;
      font-size: 11px;
    }}
    .dock-copy {{
      padding: 6px 8px;
      font-size: 11px;
    }}
  }}

  @media (max-width: 540px) {{
    .context-pill {{
      gap: 4px;
      padding: 3px 6px;
      max-width: calc(100vw - 12px);
    }}
    .pill-badge {{
      font-size: 9.5px;
      padding: 2px 5px;
    }}
    .pill-tools {{
      gap: 2px;
      padding-left: 4px;
    }}
    .pill-btn {{
      padding: 3px 5px;
      font-size: 9.5px;
    }}
    /* Hide dock text labels on small screens so all buttons fit neatly in 1 bar */
    .tab-label {{
      display: none;
    }}
    .dock-tab {{
      padding: 7px 8px;
      font-size: 14px;
    }}
    .exp-icon {{
      display: none;
    }}
    .dock-export-gif {{
      padding: 7px 9px;
      font-size: 11px;
      font-weight: 800;
    }}
    .dock-export-png {{
      padding: 7px 8px;
      font-size: 11px;
    }}
    .dock-copy {{
      padding: 7px 8px;
      font-size: 12px;
    }}
    .glass-drawer {{
      bottom: 58px;
      padding: 12px;
    }}
  }}

  @media (max-width: 380px) {{
    .floating-dock {{
      padding: 4px 5px;
      gap: 2px;
    }}
    .dock-tab {{
      padding: 5px 6px;
      font-size: 13px;
    }}
    .dock-export-gif {{
      padding: 5px 6px;
      font-size: 10px;
    }}
    .dock-export-png {{
      padding: 5px 6px;
      font-size: 10px;
    }}
    .dock-copy {{
      padding: 5px 6px;
      font-size: 11px;
    }}
    .dock-sep {{
      margin: 0 1px;
    }}
    .pill-btn {{
      padding: 3px 4px;
      font-size: 9px;
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

<div class="workspace" id="workspace">

  <!-- DYNAMIC CONTEXT PILL (TOP) -->
  <div class="context-pill" id="contextPill">
    <span class="pill-badge" id="contextBadge">🎭 Face Layer</span>
    <span class="pill-hint" id="contextHint">Drag on canvas to position • Scroll wheel to zoom</span>
    <div class="pill-tools" id="contextTools">
      <button id="toolZoomIn" class="pill-btn" title="Zoom in">🔍+</button>
      <button id="toolZoomOut" class="pill-btn" title="Zoom out">🔍-</button>
      <button id="toolRotLeft" class="pill-btn" title="Rotate left">↺</button>
      <button id="toolRotRight" class="pill-btn" title="Rotate right">↻</button>
      <button id="toolFlipH" class="pill-btn" title="Flip horizontal">↔️</button>
      <button id="toolCenter" class="pill-btn" title="Center">🎯</button>
      <button id="toolDelete" class="pill-btn danger" title="Delete">🗑️</button>
    </div>
  </div>

  <!-- BIG CENTERED CANVAS -->
  <div class="canvas-stage" id="canvasStage">
    <canvas id="mainCanvas" width="500" height="500"></canvas>
  </div>

  <!-- FLOATING DOCK WRAPPER -->
  <div class="floating-dock-wrap">

    <!-- SLIDE-UP GLASS DRAWER CONTAINER -->
    <!-- 1. FACES DRAWER -->
    <div class="glass-drawer" id="drawer-faces">
      <div class="drawer-header">
        <span class="drawer-title">🎭 Murad Faces</span>
        <button class="drawer-close" onclick="closeAllDrawers()">✕</button>
      </div>

      <label class="drop-zone">
        <span>📸 Upload Real Photo / Custom Face</span>
        <input type="file" id="faceFileInput" accept="image/*">
      </label>

      <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-size:11px; color:var(--text-muted); font-weight:700;">DEFAULT FACES:</span>
        <button id="addFaceBtn" class="pill-btn" style="background:var(--blurple); border-color:var(--blurple); color:#fff;">➕ Add Face</button>
      </div>
      <div class="grid-cards" id="facesGrid" style="max-height:180px; overflow-y:auto;"></div>

      <div style="display:flex; flex-direction:column; gap:4px; margin-top:4px;">
        <span style="font-size:11px; color:var(--text-muted); font-weight:700;">CUTOUT SHAPE:</span>
        <div class="btn-group" id="maskGroup">
          <button class="btn-toggle active" data-mask="square">Full Frame</button>
          <button class="btn-toggle" data-mask="circle">Sticker Circle</button>
          <button class="btn-toggle" data-mask="oval">Oval</button>
        </div>
      </div>
    </div>

    <!-- 2. BACKDROP DRAWER -->
    <div class="glass-drawer" id="drawer-bg">
      <div class="drawer-header">
        <span class="drawer-title">🖼️ Backdrop & Templates</span>
        <button class="drawer-close" onclick="closeAllDrawers()">✕</button>
      </div>

      <label class="drop-zone">
        <span>📁 Upload Image, Meme or Animated GIF</span>
        <input type="file" id="bgFileInput" accept="image/*,.gif">
      </label>

      <div style="display:flex; flex-direction:column; gap:4px;">
        <span style="font-size:11px; color:var(--text-muted); font-weight:700;">CANVAS RATIO:</span>
        <div class="btn-group" id="canvasSizeGroup">
          <button class="btn-toggle active" data-size="true_size">📐 True Size</button>
          <button class="btn-toggle" data-size="square">⏹️ 1:1</button>
          <button class="btn-toggle" data-size="landscape">🖼️ 16:9</button>
          <button class="btn-toggle" data-size="portrait">📱 9:16</button>
        </div>
      </div>

      <span style="font-size:11px; color:var(--text-muted); font-weight:700; margin-top:4px;">POPULAR TEMPLATES:</span>
      <div class="grid-cards" id="bgPresetsRow" style="grid-template-columns: repeat(2, 1fr);"></div>
    </div>

    <!-- 3. TEXT DRAWER -->
    <div class="glass-drawer" id="drawer-text">
      <div class="drawer-header">
        <span class="drawer-title">💬 Movable Text</span>
        <button class="drawer-close" onclick="closeAllDrawers()">✕</button>
      </div>

      <div style="display:flex; gap:6px; flex-wrap:wrap;">
        <button id="addTopTextBtn" class="pill-btn" style="flex:1 1 80px; padding:8px;">➕ Top Text</button>
        <button id="addBottomTextBtn" class="pill-btn" style="flex:1 1 80px; padding:8px;">➕ Bottom Text</button>
        <button id="addCustomTextBtn" class="pill-btn" style="flex:1 1 80px; padding:8px; background:var(--blurple); color:#fff; border-color:var(--blurple);">➕ Custom</button>
      </div>

      <div id="textEditorBox" style="display:flex; flex-direction:column; gap:8px; margin-top:4px;">
        <span style="font-size:11px; color:var(--text-muted); font-weight:700;">EDIT TEXT:</span>
        <input type="text" id="activeTextInput" class="text-input-field" placeholder="Type text here...">
        
        <div class="slider-row">
          <label>Font Size: <b id="textSizeVal">38px</b></label>
          <input type="range" id="textSizeSlider" min="14" max="90" step="2" value="38">
        </div>

        <div style="display:flex; flex-direction:column; gap:4px;">
          <span style="font-size:11px; color:var(--text-muted); font-weight:700;">COLOR:</span>
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

    <!-- 4. STICKERS DRAWER -->
    <div class="glass-drawer" id="drawer-stickers">
      <div class="drawer-header">
        <span class="drawer-title">🎀 Custom Stickers</span>
        <button class="drawer-close" onclick="closeAllDrawers()">✕</button>
      </div>

      <label class="drop-zone">
        <span>📁 Upload Custom PNG / Sticker</span>
        <input type="file" id="accFileInput" accept="image/*,.gif">
      </label>

      <div id="accEditorBox" style="display:none; flex-direction:column; gap:8px;">
        <div class="slider-row">
          <label>Sticker Size: <b id="accScaleVal">100%</b></label>
          <input type="range" id="accScale" min="0.1" max="3.0" step="0.05" value="1.0">
        </div>
        <div class="slider-row">
          <label>Opacity: <b id="accOpacityVal">100%</b></label>
          <input type="range" id="accOpacity" min="0.1" max="1.0" step="0.05" value="1.0">
        </div>
      </div>
    </div>

    <!-- 5. ANIMATE DRAWER -->
    <div class="glass-drawer" id="drawer-anim">
      <div class="drawer-header">
        <span class="drawer-title">✨ Discord GIF Effects</span>
        <button class="drawer-close" onclick="closeAllDrawers()">✕</button>
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

    <!-- THE FLOATING GLASS DOCK (ICONS + EXPORT) -->
    <div class="floating-dock">
      <button class="dock-tab" data-target="faces" title="Murad Faces"><span class="tab-icon">🎭</span><span class="tab-label">Faces</span></button>
      <button class="dock-tab" data-target="bg" title="Backdrop & Templates"><span class="tab-icon">🖼️</span><span class="tab-label">Backdrop</span></button>
      <button class="dock-tab" data-target="text" title="Meme Text"><span class="tab-icon">💬</span><span class="tab-label">Text</span></button>
      <button class="dock-tab" data-target="stickers" title="Custom Stickers"><span class="tab-icon">🎀</span><span class="tab-label">Stickers</span></button>
      <button class="dock-tab" data-target="anim" title="Discord GIF Effects"><span class="tab-icon">✨</span><span class="tab-label">Animate</span></button>

      <div class="dock-sep"></div>

      <button id="downloadGifBtn" class="dock-export-gif" title="Export Animated GIF"><span class="exp-icon">⬇️</span><span class="exp-label">GIF</span></button>
      <button id="downloadPngBtn" class="dock-export-png" title="Export High-Res PNG"><span class="exp-icon">⬇️</span><span class="exp-label">PNG</span></button>
      <button id="copyPngBtn" class="dock-copy" title="Copy to clipboard for Discord paste"><span class="exp-icon">📋</span></button>
    </div>

    <!-- PROGRESS BAR OVERLAY -->
    <div class="progress-wrap" id="progressWrap" style="display:none;">
      <div class="progress-track"><div class="progress-bar" id="progressBar"></div></div>
      <div class="progress-text" id="progressText">Encoding Discord GIF...</div>
    </div>

  </div>

</div>

<script>
const faces = {faces_json};
const templates = {templates_json};

function makeFaceLayer(faceIndex, x, y, scale) {{
  return {{
    id: 'layer_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
    faceIndex: faceIndex !== undefined ? faceIndex : 0,
    x: x !== undefined ? x : 0,
    y: y !== undefined ? y : -65,
    scale: scale !== undefined ? scale : 1.0,
    rot: 0,
    flipH: false,
    flipV: false,
    opacity: 1.0,
    filter: 'none',
    mask: 'square'
  }};
}}

const state = {{
  facesOnCanvas: [
    makeFaceLayer(0, 0, -65, 1.0)
  ],
  selectedFaceIdx: 0,
  accessoriesOnCanvas: [],
  selectedAccIdx: -1,
  textsOnCanvas: [],
  selectedTextIdx: -1,
  dragTarget: null,
  dragStartX: 0,
  dragStartY: 0,
  initialTargetX: 0,
  initialTargetY: 0,
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
  anim: 'none',
  frame: 0,
  totalFrames: 12,
  fps: 12,
  isDragging: false
}};

// Preload Images
const loadedFaces = [];
faces.forEach((f) => {{
  const img = new Image();
  img.src = f.src;
  loadedFaces.push(img);
}});

const loadedTemplates = {{}};
templates.forEach((t) => {{
  const img = new Image();
  img.src = t.src;
  loadedTemplates[t.id] = img;
}});

const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');

function updateCanvasDimensions(natW, natH) {{
  if (natW && natH) {{
    state.lastNatW = natW;
    state.lastNatH = natH;
  }} else {{
    natW = state.lastNatW || 500;
    natH = state.lastNatH || 500;
  }}

  let w = 500;
  let h = 500;
  const ratio = state.canvasSizeRatio;

  if (ratio === 'true_size') {{
    const aspect = natW / natH;
    if (aspect >= 1) {{
      w = 640;
      h = Math.round(640 / aspect);
    }} else {{
      h = 640;
      w = Math.round(640 * aspect);
    }}
  }} else if (ratio === 'square') {{
    w = 540;
    h = 540;
  }} else if (ratio === 'landscape') {{
    w = 640;
    h = 360;
  }} else if (ratio === 'portrait') {{
    w = 360;
    h = 640;
  }}

  canvas.width = w;
  canvas.height = h;
}}

function getSelectedFace() {{
  if (!state.facesOnCanvas || state.facesOnCanvas.length === 0) return null;
  if (state.selectedFaceIdx < 0 || state.selectedFaceIdx >= state.facesOnCanvas.length) {{
    state.selectedFaceIdx = 0;
  }}
  return state.facesOnCanvas[state.selectedFaceIdx];
}}

function getSelectedAcc() {{
  if (!state.accessoriesOnCanvas || state.accessoriesOnCanvas.length === 0) return null;
  if (state.selectedAccIdx < 0 || state.selectedAccIdx >= state.accessoriesOnCanvas.length) {{
    return null;
  }}
  return state.accessoriesOnCanvas[state.selectedAccIdx];
}}

function getSelectedText() {{
  if (!state.textsOnCanvas || state.textsOnCanvas.length === 0) return null;
  if (state.selectedTextIdx < 0 || state.selectedTextIdx >= state.textsOnCanvas.length) {{
    return null;
  }}
  return state.textsOnCanvas[state.selectedTextIdx];
}}

function closeAllDrawers() {{
  document.querySelectorAll('.glass-drawer').forEach(d => d.classList.remove('open'));
  document.querySelectorAll('.dock-tab').forEach(t => t.classList.remove('active'));
}}

function toggleDrawer(name) {{
  const target = document.getElementById('drawer-' + name);
  const tab = document.querySelector(`.dock-tab[data-target="${{name}}"]`);
  const isOpen = target && target.classList.contains('open');

  closeAllDrawers();
  if (!isOpen && target) {{
    target.classList.add('open');
    if (tab) tab.classList.add('active');
  }}
}}

// Update Context Pill
function updateContextPill() {{
  const badge = document.getElementById('contextBadge');
  const deleteBtn = document.getElementById('toolDelete');

  if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
    const cur = state.textsOnCanvas[state.selectedTextIdx];
    badge.innerText = `💬 "${{cur.text.slice(0, 12)}}${{cur.text.length > 12 ? '...' : ''}}"`;
    if (deleteBtn) deleteBtn.style.display = 'inline-flex';
    syncTextEditor();
    return;
  }}

  if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
    const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
    badge.innerText = `🎀 ${{cur.name || 'Sticker'}}`;
    if (deleteBtn) deleteBtn.style.display = 'inline-flex';
    syncAccEditor();
    return;
  }}

  if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
    const cur = state.facesOnCanvas[state.selectedFaceIdx];
    const faceObj = faces[cur.faceIndex];
    badge.innerText = `🎭 ${{faceObj ? faceObj.name.split(' ')[0] : 'Face'}}`;
    if (deleteBtn) deleteBtn.style.display = state.facesOnCanvas.length > 1 ? 'inline-flex' : 'none';
    syncFaceEditor();
    return;
  }}

  badge.innerText = '🖼️ Backdrop';
  if (deleteBtn) deleteBtn.style.display = 'none';
}}

function syncFaceEditor() {{
  const cur = getSelectedFace();
  if (!cur) return;
  document.querySelectorAll('.grid-card[data-face]').forEach((b, idx) => {{
    b.classList.toggle('active', idx === cur.faceIndex);
  }});
  document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => {{
    b.classList.toggle('active', b.dataset.mask === cur.mask);
  }});
}}

function syncTextEditor() {{
  const cur = getSelectedText();
  const input = document.getElementById('activeTextInput');
  if (cur && input && input !== document.activeElement) {{
    input.value = cur.text;
  }}
  const sizeVal = document.getElementById('textSizeVal');
  const sizeSlider = document.getElementById('textSizeSlider');
  if (cur && sizeVal && sizeSlider) {{
    sizeVal.innerText = cur.size + 'px';
    sizeSlider.value = cur.size;
  }}
}}

function syncAccEditor() {{
  const box = document.getElementById('accEditorBox');
  const cur = getSelectedAcc();
  if (cur && box) {{
    box.style.display = 'flex';
    const scaleVal = document.getElementById('accScaleVal');
    const scaleSlider = document.getElementById('accScale');
    if (scaleVal && scaleSlider) {{
      scaleVal.innerText = Math.round(cur.scale * 100) + '%';
      scaleSlider.value = cur.scale;
    }}
  }} else if (box) {{
    box.style.display = 'none';
  }}
}}

function buildTemplatesUI() {{
  const container = document.getElementById('bgPresetsRow');
  if (!container) return;
  container.innerHTML = '';
  templates.forEach((t, idx) => {{
    const card = document.createElement('div');
    card.className = 'grid-card' + (idx === 0 ? ' active' : '');
    card.innerHTML = `<img src="${{t.src}}"><span>${{t.name}}</span>`;
    card.onclick = () => {{
      document.querySelectorAll('#bgPresetsRow .grid-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.isBgGif = false;
      state.bgGifFrames = [];
      state.bgType = 'preset';
      state.presetBg = t.id;
      state.customBgImg = null;
      const cur = getSelectedFace();
      if (cur) {{
        if (t.id === 'suit') {{ cur.x = 0; cur.y = -65; cur.scale = 1.0; }}
        else if (t.id === 'gigachad') {{ cur.x = 0; cur.y = -60; cur.scale = 0.95; }}
        else if (t.id === 'throne') {{ cur.x = 0; cur.y = -50; cur.scale = 0.85; }}
        else if (t.id === 'astronaut') {{ cur.x = 0; cur.y = -35; cur.scale = 0.85; }}
        else if (t.id === 'doge') {{ cur.x = 0; cur.y = -35; cur.scale = 0.9; }}
      }}

      const tplImg = loadedTemplates[t.id];
      if (tplImg && tplImg.naturalWidth) {{
        updateCanvasDimensions(tplImg.naturalWidth, tplImg.naturalHeight);
      }} else {{
        updateCanvasDimensions(500, 500);
      }}
      draw();
    }};
    container.appendChild(card);
  }});
}}

function buildFacesUI() {{
  const container = document.getElementById('facesGrid');
  if (!container) return;
  container.innerHTML = '';
  faces.forEach((f, idx) => {{
    const card = document.createElement('div');
    const cur = getSelectedFace();
    const isAct = cur ? (cur.faceIndex === idx) : (idx === 0);
    card.className = 'grid-card' + (isAct ? ' active' : '');
    card.dataset.face = idx;
    card.innerHTML = `<img src="${{f.src}}"><span>${{f.name}}</span>`;
    card.onclick = () => {{
      const cFace = getSelectedFace();
      if (cFace) {{
        cFace.faceIndex = idx;
        syncFaceEditor();
        updateContextPill();
        draw();
      }}
    }};
    container.appendChild(card);
  }});
}}

function addMovableText(defaultText, defaultY) {{
  const id = 'txt_' + Date.now();
  state.textsOnCanvas.push({{
    id: id,
    text: defaultText || 'MEME TEXT',
    x: 0,
    y: defaultY !== undefined ? defaultY : 0,
    size: 38,
    color: '#ffffff',
    strokeColor: '#000000',
    rot: 0
  }});
  state.selectedTextIdx = state.textsOnCanvas.length - 1;
  state.selectedAccIdx = -1;
  state.selectedFaceIdx = -1;
  updateContextPill();
  draw();
  const input = document.getElementById('activeTextInput');
  if (input) {{
    input.focus();
    input.select();
  }}
}}

function setupEvents() {{
  buildTemplatesUI();
  buildFacesUI();
  updateContextPill();

  // Dock Tabs
  document.querySelectorAll('.dock-tab').forEach(tab => {{
    tab.onclick = (e) => {{
      e.stopPropagation();
      toggleDrawer(tab.dataset.target);
    }};
  }});

  // Close drawers when clicking canvas or workspace
  document.getElementById('workspace').onclick = (e) => {{
    if (!e.target.closest('.floating-dock-wrap') && !e.target.closest('.context-pill')) {{
      closeAllDrawers();
    }}
  }};

  // Add face button
  document.getElementById('addFaceBtn').onclick = () => {{
    state.facesOnCanvas.push(makeFaceLayer(0, 20, -50, 0.9));
    state.selectedFaceIdx = state.facesOnCanvas.length - 1;
    state.selectedAccIdx = -1;
    state.selectedTextIdx = -1;
    updateContextPill();
    draw();
  }};

  // Custom Face Upload
  const faceFileInput = document.getElementById('faceFileInput');
  if (faceFileInput) {{
    faceFileInput.onchange = (e) => {{
      if (e.target.files && e.target.files[0]) {{
        const reader = new FileReader();
        reader.onload = (evt) => {{
          const img = new Image();
          img.onload = () => {{
            loadedFaces.unshift(img);
            faces.unshift({{
              id: 'custom_' + Date.now(),
              name: 'My Photo 📸',
              src: evt.target.result
            }});
            state.facesOnCanvas.forEach(fl => {{ fl.faceIndex += 1; }});
            const cur = getSelectedFace();
            if (cur) cur.faceIndex = 0;
            buildFacesUI();
            updateContextPill();
            draw();
          }};
          img.src = evt.target.result;
        }};
        reader.readAsDataURL(e.target.files[0]);
      }}
    }};
  }}

  // Cutout masks
  document.querySelectorAll('#maskGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      const cur = getSelectedFace();
      if (!cur) return;
      document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      cur.mask = btn.dataset.mask;
      draw();
    }};
  }});

  // Background file upload
  const bgFileInput = document.getElementById('bgFileInput');
  if (bgFileInput) {{
    bgFileInput.onchange = async (e) => {{
      if (e.target.files && e.target.files[0]) {{
        const file = e.target.files[0];
        const isGif = file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif');
        if (isGif) {{
          const buffer = await file.arrayBuffer();
          const ok = await parseAndLoadGif(buffer);
          if (ok) {{ draw(); return; }}
        }}
        const reader = new FileReader();
        reader.onload = (evt) => {{
          const img = new Image();
          img.onload = () => {{
            state.isBgGif = false;
            state.bgGifFrames = [];
            state.bgType = 'custom';
            state.customBgImg = img;
            updateCanvasDimensions(img.naturalWidth, img.naturalHeight);
            draw();
          }};
          img.src = evt.target.result;
        }};
        reader.readAsDataURL(file);
      }}
    }};
  }}

  // Canvas Size
  document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.canvasSizeRatio = btn.dataset.size;
      updateCanvasDimensions();
      draw();
    }};
  }});

  // Text Buttons
  document.getElementById('addTopTextBtn').onclick = () => addMovableText('TOP TEXT', -Math.round(canvas.height * 0.38));
  document.getElementById('addBottomTextBtn').onclick = () => addMovableText('BOTTOM TEXT', Math.round(canvas.height * 0.38));
  document.getElementById('addCustomTextBtn').onclick = () => addMovableText('MEME TEXT', 0);

  document.getElementById('activeTextInput').oninput = (e) => {{
    const cur = getSelectedText();
    if (!cur) return;
    cur.text = e.target.value;
    updateContextPill();
    draw();
  }};

  document.getElementById('textSizeSlider').oninput = (e) => {{
    const cur = getSelectedText();
    if (!cur) return;
    cur.size = parseInt(e.target.value);
    document.getElementById('textSizeVal').innerText = cur.size + 'px';
    draw();
  }};

  document.querySelectorAll('#textColorGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      const cur = getSelectedText();
      if (!cur) return;
      document.querySelectorAll('#textColorGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      cur.color = btn.dataset.color;
      draw();
    }};
  }});

  // Custom Sticker Upload
  const accFileInput = document.getElementById('accFileInput');
  if (accFileInput) {{
    accFileInput.onchange = (e) => {{
      if (e.target.files && e.target.files[0]) {{
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (evt) => {{
          const img = new Image();
          img.onload = () => {{
            state.accessoriesOnCanvas.push({{
              id: 'acc_' + Date.now(),
              name: file.name.split('.')[0].slice(0, 10),
              img: img,
              x: 0,
              y: 0,
              scale: 1.0,
              rot: 0,
              flipH: false,
              flipV: false,
              opacity: 1.0
            }});
            state.selectedAccIdx = state.accessoriesOnCanvas.length - 1;
            state.selectedFaceIdx = -1;
            state.selectedTextIdx = -1;
            updateContextPill();
            draw();
          }};
          img.src = evt.target.result;
        }};
        reader.readAsDataURL(file);
      }}
    }};
  }}

  // Context Pill Quick Tools
  document.getElementById('toolZoomIn').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas[state.selectedTextIdx].size = Math.min(90, state.textsOnCanvas[state.selectedTextIdx].size + 4);
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].scale = Math.min(3.0, state.accessoriesOnCanvas[state.selectedAccIdx].scale + 0.15);
    }} else if (getSelectedFace()) {{
      getSelectedFace().scale = Math.min(2.5, getSelectedFace().scale + 0.15);
    }}
    updateContextPill();
    draw();
  }};

  document.getElementById('toolZoomOut').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas[state.selectedTextIdx].size = Math.max(14, state.textsOnCanvas[state.selectedTextIdx].size - 4);
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].scale = Math.max(0.1, state.accessoriesOnCanvas[state.selectedAccIdx].scale - 0.15);
    }} else if (getSelectedFace()) {{
      getSelectedFace().scale = Math.max(0.3, getSelectedFace().scale - 0.15);
    }}
    updateContextPill();
    draw();
  }};

  document.getElementById('toolRotLeft').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas[state.selectedTextIdx].rot = (state.textsOnCanvas[state.selectedTextIdx].rot - 15) % 360;
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].rot = (state.accessoriesOnCanvas[state.selectedAccIdx].rot - 15) % 360;
    }} else if (getSelectedFace()) {{
      getSelectedFace().rot = (getSelectedFace().rot - 15) % 360;
    }}
    draw();
  }};

  document.getElementById('toolRotRight').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas[state.selectedTextIdx].rot = (state.textsOnCanvas[state.selectedTextIdx].rot + 15) % 360;
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].rot = (state.accessoriesOnCanvas[state.selectedAccIdx].rot + 15) % 360;
    }} else if (getSelectedFace()) {{
      getSelectedFace().rot = (getSelectedFace().rot + 15) % 360;
    }}
    draw();
  }};

  document.getElementById('toolFlipH').onclick = () => {{
    if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].flipH = !state.accessoriesOnCanvas[state.selectedAccIdx].flipH;
    }} else if (getSelectedFace()) {{
      getSelectedFace().flipH = !getSelectedFace().flipH;
    }}
    draw();
  }};

  document.getElementById('toolCenter').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas[state.selectedTextIdx].x = 0;
      state.textsOnCanvas[state.selectedTextIdx].y = 0;
      state.textsOnCanvas[state.selectedTextIdx].rot = 0;
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].x = 0;
      state.accessoriesOnCanvas[state.selectedAccIdx].y = 0;
      state.accessoriesOnCanvas[state.selectedAccIdx].rot = 0;
    }} else if (getSelectedFace()) {{
      getSelectedFace().x = 0;
      getSelectedFace().y = -35;
      getSelectedFace().rot = 0;
    }}
    draw();
  }};

  document.getElementById('toolDelete').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas.splice(state.selectedTextIdx, 1);
      state.selectedTextIdx = -1;
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas.splice(state.selectedAccIdx, 1);
      state.selectedAccIdx = -1;
    }} else if (state.selectedFaceIdx >= 0 && state.facesOnCanvas.length > 1) {{
      state.facesOnCanvas.splice(state.selectedFaceIdx, 1);
      state.selectedFaceIdx = 0;
    }}
    updateContextPill();
    draw();
  }};

  // Canvas Wheel Zoom
  canvas.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.05 : -0.05;
    if (state.selectedTextIdx >= 0) {{
      state.textsOnCanvas[state.selectedTextIdx].size = Math.max(14, Math.min(90, state.textsOnCanvas[state.selectedTextIdx].size + (e.deltaY < 0 ? 2 : -2)));
      syncTextEditor();
    }} else if (state.selectedAccIdx >= 0) {{
      state.accessoriesOnCanvas[state.selectedAccIdx].scale = Math.max(0.1, Math.min(3.0, state.accessoriesOnCanvas[state.selectedAccIdx].scale + delta));
      syncAccEditor();
    }} else if (getSelectedFace()) {{
      getSelectedFace().scale = Math.max(0.3, Math.min(2.5, getSelectedFace().scale + delta));
    }}
    draw();
  }}, {{ passive: false }});

  // Anim presets
  document.querySelectorAll('#animGrid .grid-card').forEach(card => {{
    card.onclick = () => {{
      document.querySelectorAll('#animGrid .grid-card').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.anim = card.dataset.anim;
      state.frame = 0;
      state.totalFrames = state.anim === 'none' ? 1 : (state.anim === 'petpet' ? 8 : (state.anim === 'disco' ? 16 : 12));
      state.fps = state.anim === 'petpet' ? 14 : 12;
      draw();
    }};
  }});

  document.getElementById('downloadPngBtn').onclick = downloadPng;
  document.getElementById('downloadGifBtn').onclick = exportGif;
  document.getElementById('copyPngBtn').onclick = copyToClipboard;
}}

// -------------------------------------------------------------
// DRAGGING ENGINE
// -------------------------------------------------------------
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

  function findTextAt(canvasX, canvasY, w, h) {{
    for (let i = state.textsOnCanvas.length - 1; i >= 0; i--) {{
      const t = state.textsOnCanvas[i];
      if (!t.text) continue;
      const cx = w/2 + t.x;
      const cy = h/2 + t.y;
      const dx = canvasX - cx;
      const dy = canvasY - cy;
      const angle = -(t.rot * Math.PI / 180);
      const rx = dx * Math.cos(angle) - dy * Math.sin(angle);
      const ry = dx * Math.sin(angle) + dy * Math.cos(angle);

      ctx.save();
      ctx.font = `900 ${{t.size}}px Impact, sans-serif`;
      const tw = ctx.measureText(t.text).width;
      ctx.restore();
      const th = t.size * 1.1;

      if (Math.abs(rx) <= tw/2 + 12 && Math.abs(ry) <= th/2 + 12) {{
        return i;
      }}
    }}
    return -1;
  }}

  function findAccAt(canvasX, canvasY, w, h) {{
    for (let i = state.accessoriesOnCanvas.length - 1; i >= 0; i--) {{
      const acc = state.accessoriesOnCanvas[i];
      const img = acc.img;
      if (!img || !img.complete || img.naturalWidth === 0) continue;
      const cx = w/2 + acc.x;
      const cy = h/2 + acc.y;
      const baseSize = w * 0.35;
      const aspect = (img.naturalWidth || 1) / (img.naturalHeight || 1);
      let aw = aspect >= 1 ? baseSize : baseSize * aspect;
      let ah = aspect >= 1 ? baseSize / aspect : baseSize;
      aw *= acc.scale;
      ah *= acc.scale;

      const dx = canvasX - cx;
      const dy = canvasY - cy;
      const angle = -(acc.rot * Math.PI / 180);
      const rx = dx * Math.cos(angle) - dy * Math.sin(angle);
      const ry = dx * Math.sin(angle) + dy * Math.cos(angle);

      if (Math.abs(rx) <= aw/2 + 10 && Math.abs(ry) <= ah/2 + 10) {{
        return i;
      }}
    }}
    return -1;
  }}

  function findFaceAt(canvasX, canvasY, w, h) {{
    for (let i = state.facesOnCanvas.length - 1; i >= 0; i--) {{
      const f = state.facesOnCanvas[i];
      const img = loadedFaces[f.faceIndex];
      if (!img || !img.complete) continue;
      const cx = w/2 + f.x;
      const cy = h/2 + f.y;
      const baseSize = w * 0.44;
      const fAspect = (img.naturalWidth || img.width) / (img.naturalHeight || img.height);
      let fw = fAspect >= 1 ? baseSize : baseSize * fAspect;
      let fh = fAspect >= 1 ? baseSize / fAspect : baseSize;
      fw *= f.scale;
      fh *= f.scale;

      const dx = canvasX - cx;
      const dy = canvasY - cy;
      const angle = -(f.rot * Math.PI / 180);
      const rx = dx * Math.cos(angle) - dy * Math.sin(angle);
      const ry = dx * Math.sin(angle) + dy * Math.cos(angle);

      if (Math.abs(rx) <= fw/2 + 10 && Math.abs(ry) <= fh/2 + 10) {{
        return i;
      }}
    }}
    return -1;
  }}

  function onPointerDown(e) {{
    const pos = getCanvasPos(e);

    const hitText = findTextAt(pos.x, pos.y, canvas.width, canvas.height);
    if (hitText !== -1) {{
      state.selectedTextIdx = hitText;
      state.selectedAccIdx = -1;
      state.selectedFaceIdx = -1;
      state.dragTarget = {{ type: 'text', idx: hitText }};
      state.isDragging = true;
      state.dragStartX = pos.x;
      state.dragStartY = pos.y;
      state.initialTargetX = state.textsOnCanvas[hitText].x;
      state.initialTargetY = state.textsOnCanvas[hitText].y;
      updateContextPill();
      draw();
      return;
    }}

    const hitAcc = findAccAt(pos.x, pos.y, canvas.width, canvas.height);
    if (hitAcc !== -1) {{
      state.selectedAccIdx = hitAcc;
      state.selectedTextIdx = -1;
      state.selectedFaceIdx = -1;
      state.dragTarget = {{ type: 'acc', idx: hitAcc }};
      state.isDragging = true;
      state.dragStartX = pos.x;
      state.dragStartY = pos.y;
      state.initialTargetX = state.accessoriesOnCanvas[hitAcc].x;
      state.initialTargetY = state.accessoriesOnCanvas[hitAcc].y;
      updateContextPill();
      draw();
      return;
    }}

    const hitFace = findFaceAt(pos.x, pos.y, canvas.width, canvas.height);
    if (hitFace !== -1) {{
      state.selectedFaceIdx = hitFace;
      state.selectedAccIdx = -1;
      state.selectedTextIdx = -1;
      state.dragTarget = {{ type: 'face', idx: hitFace }};
      state.isDragging = true;
      state.dragStartX = pos.x;
      state.dragStartY = pos.y;
      state.initialTargetX = state.facesOnCanvas[hitFace].x;
      state.initialTargetY = state.facesOnCanvas[hitFace].y;
      updateContextPill();
      draw();
      return;
    }}

    state.isDragging = false;
    state.dragTarget = null;
    draw();
  }}

  function onPointerMove(e) {{
    if (!state.isDragging || !state.dragTarget) return;
    if (e.cancelable) e.preventDefault();
    const pos = getCanvasPos(e);
    const dx = pos.x - state.dragStartX;
    const dy = pos.y - state.dragStartY;

    if (state.dragTarget.type === 'text') {{
      const item = state.textsOnCanvas[state.dragTarget.idx];
      if (item) {{
        item.x = Math.round(state.initialTargetX + dx);
        item.y = Math.round(state.initialTargetY + dy);
        draw();
      }}
    }} else if (state.dragTarget.type === 'acc') {{
      const item = state.accessoriesOnCanvas[state.dragTarget.idx];
      if (item) {{
        item.x = Math.round(state.initialTargetX + dx);
        item.y = Math.round(state.initialTargetY + dy);
        draw();
      }}
    }} else if (state.dragTarget.type === 'face') {{
      const item = state.facesOnCanvas[state.dragTarget.idx];
      if (item) {{
        item.x = Math.round(state.initialTargetX + dx);
        item.y = Math.round(state.initialTargetY + dy);
        draw();
      }}
    }}
  }}

  function onPointerUp() {{
    if (state.isDragging) {{
      state.isDragging = false;
      state.dragTarget = null;
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

  if (!source) {{
    const grad = tCtx.createRadialGradient(w/2, h/2, 40, w/2, h/2, Math.max(w, h));
    grad.addColorStop(0, '#2b2d31');
    grad.addColorStop(1, '#111214');
    tCtx.fillStyle = grad;
    tCtx.fillRect(0, 0, w, h);
    return;
  }}

  tCtx.fillStyle = '#0a0a0c';
  tCtx.fillRect(0, 0, w, h);

  let drawW = w;
  let drawH = h;
  let drawX = 0;
  let drawY = 0;

  const canvasAspect = w / h;
  const srcAspect = srcW / srcH;

  if (state.bgFitMode === 'cover') {{
    if (srcAspect > canvasAspect) {{
      drawH = h;
      drawW = h * srcAspect;
      drawX = (w - drawW) / 2;
    }} else {{
      drawW = w;
      drawH = w / srcAspect;
      drawY = (h - drawH) / 2;
    }}
  }} else {{
    if (srcAspect > canvasAspect) {{
      drawW = w;
      drawH = w / srcAspect;
      drawY = (h - drawH) / 2;
    }} else {{
      drawH = h;
      drawW = h * srcAspect;
      drawX = (w - drawW) / 2;
    }}
  }}

  tCtx.save();
  tCtx.translate(w / 2 + state.bgPanX, h / 2 + state.bgPanY);
  tCtx.scale(state.bgScale, state.bgScale);
  tCtx.drawImage(source, drawX - w/2, drawY - h/2, drawW, drawH);
  tCtx.restore();
}}

// -------------------------------------------------------------
// MAIN RENDER PIPELINE
// -------------------------------------------------------------
function render(tCtx, w, h, frameIdx) {{
  tCtx.clearRect(0, 0, w, h);

  // 1. Background
  drawBackground(tCtx, w, h);

  // Animation transforms
  let animOffsetX = 0;
  let animOffsetY = 0;
  let animScale = 1.0;
  let animRot = 0;

  const progress = (frameIdx / state.totalFrames) * Math.PI * 2;

  if (state.anim === 'bob') {{
    animOffsetY = Math.sin(progress) * 14;
  }} else if (state.anim === 'shake') {{
    animOffsetX = (Math.random() - 0.5) * 12;
    animOffsetY = (Math.random() - 0.5) * 12;
  }} else if (state.anim === 'spin') {{
    animRot = (frameIdx / state.totalFrames) * 360;
  }} else if (state.anim === 'zoom') {{
    animScale = 1.0 + Math.sin(progress) * 0.16;
  }} else if (state.anim === 'pulse') {{
    animScale = 1.0 + Math.abs(Math.sin(progress * 2)) * 0.14;
  }} else if (state.anim === 'wobble') {{
    animRot = Math.sin(progress) * 18;
    animOffsetY = Math.cos(progress) * 8;
  }}

  // 2. Render each face layer
  state.facesOnCanvas.forEach((fLayer, idx) => {{
    const faceImg = loadedFaces[fLayer.faceIndex];
    if (!faceImg || !faceImg.complete) return;

    tCtx.save();
    const cx = w/2 + fLayer.x + animOffsetX;
    const cy = h/2 + fLayer.y + animOffsetY;
    tCtx.translate(cx, cy);
    tCtx.rotate((fLayer.rot + animRot) * Math.PI / 180);
    tCtx.scale((fLayer.flipH ? -1 : 1) * animScale, (fLayer.flipV ? -1 : 1) * animScale);
    tCtx.globalAlpha = fLayer.opacity !== undefined ? fLayer.opacity : 1.0;

    if (fLayer.filter === 'bw') {{
      tCtx.filter = 'grayscale(100%) contrast(120%)';
    }} else if (fLayer.filter === 'deepfried') {{
      tCtx.filter = 'contrast(240%) saturate(300%) brightness(110%)';
    }} else if (fLayer.filter === 'invert') {{
      tCtx.filter = 'invert(100%)';
    }} else {{
      tCtx.filter = 'none';
    }}

    const baseSize = w * 0.44;
    const fAspect = (faceImg.naturalWidth || faceImg.width) / (faceImg.naturalHeight || faceImg.height);
    let fw = fAspect >= 1 ? baseSize : baseSize * fAspect;
    let fh = fAspect >= 1 ? baseSize / fAspect : baseSize;
    fw *= fLayer.scale;
    fh *= fLayer.scale;

    if (fLayer.mask === 'circle') {{
      tCtx.shadowColor = 'rgba(0, 0, 0, 0.45)';
      tCtx.shadowBlur = 16;
      tCtx.beginPath();
      tCtx.arc(0, 0, Math.min(fw, fh) * 0.5, 0, Math.PI * 2);
      tCtx.save();
      tCtx.clip();
      tCtx.drawImage(faceImg, -fw/2, -fh/2, fw, fh);
      tCtx.restore();
      tCtx.strokeStyle = '#ffffff';
      tCtx.lineWidth = 4;
      tCtx.stroke();
    }} else if (fLayer.mask === 'oval') {{
      tCtx.shadowColor = 'rgba(0, 0, 0, 0.45)';
      tCtx.shadowBlur = 16;
      tCtx.beginPath();
      tCtx.ellipse(0, 0, fw * 0.42, fh * 0.55, 0, 0, Math.PI * 2);
      tCtx.save();
      tCtx.clip();
      tCtx.drawImage(faceImg, -fw/2, -fh/2, fw, fh);
      tCtx.restore();
      tCtx.strokeStyle = '#ffffff';
      tCtx.lineWidth = 4;
      tCtx.stroke();
    }} else {{
      tCtx.drawImage(faceImg, -fw/2, -fh/2, fw, fh);
    }}

    tCtx.filter = 'none';
    tCtx.globalAlpha = 1.0;

    const isSelected = (idx === state.selectedFaceIdx && state.selectedAccIdx === -1 && state.selectedTextIdx === -1);
    if (isSelected && (state.isDragging || state.facesOnCanvas.length > 1)) {{
      tCtx.save();
      tCtx.strokeStyle = '#5865F2';
      tCtx.lineWidth = 2.5;
      tCtx.setLineDash([5, 5]);
      tCtx.strokeRect(-fw/2 - 3, -fh/2 - 3, fw + 6, fh + 6);
      tCtx.restore();
    }}

    if (state.anim === 'disco') {{
      const hue = Math.floor((frameIdx / state.totalFrames) * 360);
      tCtx.save();
      tCtx.strokeStyle = `hsl(${{hue}}, 100%, 55%)`;
      tCtx.lineWidth = 6;
      tCtx.shadowColor = `hsl(${{hue}}, 100%, 55%)`;
      tCtx.shadowBlur = 18;
      tCtx.strokeRect(-fw/2 - 4, -fh/2 - 4, fw + 8, fh + 8);
      tCtx.restore();
    }}

    tCtx.restore();
  }});

  // Petpet Hand on Selected Face
  if (state.anim === 'petpet') {{
    const cur = getSelectedFace();
    const squish = Math.sin((frameIdx % 5) / 5 * Math.PI);
    const handX = cur ? (w * 0.5 + cur.x) : (w * 0.5);
    const handY = cur ? (h * 0.5 + cur.y - 45 + squish * (h * 0.08)) : (h * 0.16 + squish * (h * 0.12));
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

  // 3. Render Custom User Stickers
  state.accessoriesOnCanvas.forEach((acc, aIdx) => {{
    const img = acc.img;
    if (!img || !img.complete || img.naturalWidth === 0) return;
    tCtx.save();
    tCtx.translate(w/2 + acc.x, h/2 + acc.y);
    tCtx.rotate(acc.rot * Math.PI / 180);
    tCtx.scale(acc.flipH ? -1 : 1, acc.flipV ? -1 : 1);
    tCtx.globalAlpha = acc.opacity !== undefined ? acc.opacity : 1.0;

    const baseSize = w * 0.35;
    const aspect = (img.naturalWidth || 1) / (img.naturalHeight || 1);
    let aw = aspect >= 1 ? baseSize : baseSize * aspect;
    let ah = aspect >= 1 ? baseSize / aspect : baseSize;
    aw *= acc.scale;
    ah *= acc.scale;

    tCtx.drawImage(img, -aw/2, -ah/2, aw, ah);

    if (aIdx === state.selectedAccIdx) {{
      tCtx.strokeStyle = '#5865F2';
      tCtx.lineWidth = 2;
      tCtx.setLineDash([4, 4]);
      tCtx.strokeRect(-aw/2 - 4, -ah/2 - 4, aw + 8, ah + 8);
    }}
    tCtx.restore();
  }});

  // 4. Render Custom Movable Text Layers
  state.textsOnCanvas.forEach((txtItem, tIdx) => {{
    if (!txtItem.text || !txtItem.text.trim()) return;
    tCtx.save();
    tCtx.translate(w/2 + txtItem.x, h/2 + txtItem.y);
    tCtx.rotate(txtItem.rot * Math.PI / 180);
    tCtx.font = `900 ${{txtItem.size}}px Impact, sans-serif`;
    tCtx.textAlign = 'center';
    tCtx.textBaseline = 'middle';
    tCtx.lineJoin = 'round';
    tCtx.lineWidth = Math.max(3, Math.round(txtItem.size * 0.12));
    tCtx.strokeStyle = txtItem.strokeColor || '#000000';
    tCtx.strokeText(txtItem.text, 0, 0);
    tCtx.fillStyle = txtItem.color || '#ffffff';
    tCtx.fillText(txtItem.text, 0, 0);

    if (tIdx === state.selectedTextIdx) {{
      const textMetrics = tCtx.measureText(txtItem.text);
      const tw = textMetrics.width;
      const th = txtItem.size * 1.1;
      tCtx.strokeStyle = '#5865F2';
      tCtx.lineWidth = 2;
      tCtx.setLineDash([4, 4]);
      tCtx.strokeRect(-tw/2 - 6, -th/2 - 4, tw + 12, th + 8);
    }}
    tCtx.restore();
  }});
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

function getRandomLetters(len = 5) {{
  const chars = 'abcdefghijklmnopqrstuvwxyz0123456789';
  let s = '';
  for (let i = 0; i < len; i++) {{
    s += chars.charAt(Math.floor(Math.random() * chars.length));
  }}
  return s;
}}

function getDownloadFilename(ext) {{
  const customInput = document.getElementById('customFilenameInput');
  const raw = (customInput && customInput.value.trim()) ? customInput.value.trim() : 'murad_meme';
  const cleanBase = raw.replace(/[^a-zA-Z0-9_-]/g, '_');
  return `${{cleanBase}}_${{getRandomLetters(5)}}.${{ext}}`;
}}

function downloadPng() {{
  const link = document.createElement('a');
  link.download = getDownloadFilename('png');
  link.href = canvas.toDataURL('image/png');
  link.click();
}}

function copyToClipboard() {{
  const btn = document.getElementById('copyPngBtn');
  if (!canvas.toBlob || !navigator.clipboard) {{
    alert('Clipboard copying not supported in this browser. Please use Download .PNG.');
    return;
  }}
  canvas.toBlob(async (blob) => {{
    try {{
      await navigator.clipboard.write([
        new ClipboardItem({{ 'image/png': blob }})
      ]);
      const prev = btn.innerText;
      btn.innerText = '✅';
      setTimeout(() => {{ btn.innerText = prev; }}, 2000);
    }} catch (e) {{
      alert('Could not copy image to clipboard. Use Download .PNG instead.');
    }}
  }});
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
  txt.innerText = 'Preparing GIF frames...';

  const exportW = canvas.width;
  const exportH = canvas.height;
  const tempCanvas = document.createElement('canvas');
  tempCanvas.width = exportW;
  tempCanvas.height = exportH;
  const tempCtx = tempCanvas.getContext('2d');

  let framesToCapture = state.anim === 'none' ? 12 : state.totalFrames;
  if (state.isBgGif && state.bgGifFrames.length > 0) {{
    framesToCapture = Math.max(framesToCapture, Math.min(24, state.bgGifFrames.length));
  }}

  const capturedFrames = [];
  const origGifIdx = state.gifBgFrameIndex;

  for (let i = 0; i < framesToCapture; i++) {{
    if (state.isBgGif && state.bgGifFrames.length > 0) {{
      state.gifBgFrameIndex = i % state.bgGifFrames.length;
    }}
    render(tempCtx, exportW, exportH, i);
    capturedFrames.push(tempCanvas.toDataURL('image/png'));
  }}
  state.gifBgFrameIndex = origGifIdx;
  draw();

  bar.style.width = '35%';
  txt.innerText = 'Encoding Discord GIF...';

  gifshot.createGIF({{
    images: capturedFrames,
    gifWidth: exportW,
    gifHeight: exportH,
    interval: 1 / state.fps,
    numFrames: framesToCapture,
    progressCallback: (captureProgress) => {{
      const pct = Math.round(35 + captureProgress * 60);
      bar.style.width = pct + '%';
      txt.innerText = `Encoding GIF: ${{pct}}%`;
    }}
  }}, (obj) => {{
    if (!obj.error) {{
      bar.style.width = '100%';
      txt.innerText = 'GIF Ready! Downloading...';
      const a = document.createElement('a');
      a.download = getDownloadFilename('gif');
      a.href = obj.image;
      a.click();
      setTimeout(() => {{ wrap.style.display = 'none'; }}, 2000);
    }} else {{
      alert('GIF error: ' + obj.errorMsg);
      wrap.style.display = 'none';
    }}
  }});
}}

async function parseAndLoadGif(arrayBuffer) {{
  if (typeof window.GIF === 'undefined') return false;
  try {{
    const gif = new window.GIF(arrayBuffer);
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

      fullFrames.push({{ canvas: frameCanvas, delay: frame.delay || 100 }});
    }});

    state.isBgGif = true;
    state.bgGifFrames = fullFrames;
    state.gifBgFrameIndex = 0;
    state.bgType = 'custom';
    state.customBgImg = null;

    updateCanvasDimensions(gifW, gifH);
    return true;
  }} catch (err) {{
    return false;
  }}
}}

function init() {{
  updateCanvasDimensions();
  setupEvents();
  setupDragging();
  draw();
  startAnim();
}}

window.onload = init;
</script>
</body>
</html>
"""

# --- TOP MINIMALIST ADMIN PILL (TOP RIGHT) ---
_, col_head_right = st.columns([6, 1.2])
with col_head_right:
    admin_ui = st.popover("🔐 Admin", use_container_width=True) if hasattr(st, "popover") else st.expander("🔐 Admin")
    with admin_ui:
        st.markdown("### 🔐 Admin Settings")
        st.caption("Manage default faces or push new ones to GitHub.")

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

            token_secret = ""
            try:
                token_secret = st.secrets.get("GITHUB_TOKEN", "")
            except Exception:
                pass

            if token_secret:
                st.markdown("<small style='color: #23a55a; font-weight: 600;'>🟢 GitHub Auto-Sync: Active</small>", unsafe_allow_html=True)
                gh_token = token_secret
            else:
                gh_token = st.text_input(
                    "GitHub Personal Access Token:",
                    type="password",
                    placeholder="github_pat_... or ghp_...",
                )

            admin_tab_manage, admin_tab_add = st.tabs(["🗑️ Manage Faces", "➕ Add Face"])

            with admin_tab_manage:
                current_manifest = []
                if MANIFEST_FILE.exists():
                    try:
                        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                            current_manifest = json.load(f)
                    except Exception:
                        pass

                if not current_manifest:
                    st.info("No default faces found.")
                else:
                    for idx, item in enumerate(current_manifest):
                        c_img, c_name, c_action = st.columns([1, 2.8, 1.2])
                        with c_img:
                            face_p = ASSETS_DIR / item.get("file", "")
                            if face_p.exists():
                                st.image(str(face_p), width=40)
                            else:
                                st.write("🖼️")
                        with c_name:
                            st.markdown(f"**{item.get('name', 'Face')}**")
                        with c_action:
                            if st.button("🗑️", key=f"del_face_{idx}_{item.get('id', '')}"):
                                current_manifest.pop(idx)
                                manifest_bytes = json.dumps(current_manifest, indent=2).encode("utf-8")
                                with open(MANIFEST_FILE, "wb") as f:
                                    f.write(manifest_bytes)

                                other_refs = [x for x in current_manifest if x.get("file") == item.get("file")]
                                if not other_refs:
                                    img_to_del = ASSETS_DIR / item.get("file", "")
                                    if img_to_del.exists():
                                        img_to_del.unlink()

                                if gh_token:
                                    with st.spinner("Deleting face..."):
                                        if not other_refs:
                                            delete_file_from_github(
                                                "Aboodi-8", "Muradeditor", f"assets/{item.get('file', '')}",
                                                f"Delete face image: {item.get('name')}", gh_token
                                            )
                                        push_file_to_github(
                                            "Aboodi-8", "Muradeditor", "assets/manifest.json",
                                            manifest_bytes,
                                            f"Update manifest: remove {item.get('name')}", gh_token
                                        )
                                st.rerun()

            with admin_tab_add:
                new_face_name = st.text_input("Face Name & Emoji:", placeholder="e.g. Chill Murad 😎")
                new_face_file = st.file_uploader("Upload Image:", type=["png", "jpg", "jpeg", "webp"], key="top_face_file")

                if st.button("🚀 Push to Default Catalog", type="primary", use_container_width=True):
                    if new_face_name and new_face_file:
                        img_bytes = new_face_file.read()
                        clean_name = re.sub(r'[^a-zA-Z0-9_]', '_', new_face_name.split()[0].lower())
                        filename = f"murad_{clean_name}.png"
                        face_id = f"murad_{clean_name}"

                        local_path = ASSETS_DIR / filename
                        with open(local_path, "wb") as f:
                            f.write(img_bytes)

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

                        if gh_token:
                            with st.spinner("Pushing to GitHub..."):
                                push_file_to_github("Aboodi-8", "Muradeditor", f"assets/{filename}", img_bytes, f"Add {new_face_name}", gh_token)
                                push_file_to_github("Aboodi-8", "Muradeditor", "assets/manifest.json", manifest_bytes, f"Manifest for {new_face_name}", gh_token)
                        st.success(f"Added '{new_face_name}'!")
                        st.rerun()
        elif admin_pwd:
            st.error("❌ Incorrect Admin Password.")

# Embed the interactive Canva-style studio HTML5 component
components.html(html_app, height=920, scrolling=False)
