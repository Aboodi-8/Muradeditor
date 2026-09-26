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
    page_title="Meme Editor & GIF Maker",
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

def delete_file_from_github(repo_owner: str, repo_name: str, file_path: str, commit_message: str, token: str) -> tuple[bool, str]:
    clean_token = token.strip()
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    headers = {
        "Authorization": f"Bearer {clean_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "MuradMemeAdmin",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Fetch current file sha
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
    grid-template-columns: minmax(560px, 680px) 1fr;
    gap: 20px;
    max-width: 100%;
    width: 100%;
    margin: 0 auto;
    align-items: start;
    padding: 4px 8px;
  }}
  .sidebar-col {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .sidebar-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
    align-items: start;
  }}
  .sidebar-subcol {{
    display: flex;
    flex-direction: column;
    gap: 10px;
  }}
  .card-step5 {{
    margin-bottom: 0 !important;
  }}
  .step5-body {{
    display: grid;
    grid-template-columns: 1.15fr 1fr;
    gap: 14px;
    margin-top: 6px;
    align-items: start;
  }}
  .btn-add-face {{
    background: var(--blurple);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }}
  .btn-add-face:hover {{
    background: var(--blurple-hover);
  }}
  .face-layers-bar {{
    background: rgba(0,0,0,0.35);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 7px 10px;
    margin-bottom: 8px;
  }}
  .face-layer-pill {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
    max-width: 140px;
    white-space: nowrap;
    overflow: hidden;
  }}
  .face-layer-pill img {{
    width: 22px;
    height: 22px;
    border-radius: 50%;
    object-fit: cover;
    flex-shrink: 0;
    display: inline-block;
  }}
  .face-layer-pill span {{
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .face-layer-pill:hover {{
    border-color: rgba(88,101,242,0.5);
  }}
  .face-layer-pill.active {{
    background: rgba(88,101,242,0.3);
    border-color: var(--blurple);
    color: #fff;
    box-shadow: 0 0 8px rgba(88,101,242,0.4);
  }}
  .pill-del {{
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 11px;
    cursor: pointer;
    padding: 0 2px;
    line-height: 1;
    font-weight: 700;
  }}
  .pill-del:hover {{
    color: #ef4444;
  }}
  @media (max-width: 1240px) {{
    .app-container {{
      grid-template-columns: minmax(480px, 560px) 1fr;
      gap: 16px;
    }}
  }}
  @media (max-width: 980px) {{
    .sidebar-grid {{
      grid-template-columns: 1fr;
    }}
    .step5-body {{
      grid-template-columns: 1fr;
    }}
    .app-container {{
      grid-template-columns: 1fr;
    }}
    .canvas-stage {{
      position: static !important;
    }}
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
  .acc-layer-pill, .text-layer-pill {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    transition: all 0.15s ease;
    max-width: 150px;
    white-space: nowrap;
  }}
  .acc-layer-pill.active, .text-layer-pill.active {{
    border-color: var(--blurple);
    background: rgba(88, 101, 242, 0.2);
    color: #fff;
  }}
  .acc-layer-pill img {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    object-fit: cover;
    flex-shrink: 0;
  }}
  .pill-del-btn {{
    color: var(--text-muted);
    font-weight: bold;
    border-radius: 50%;
    width: 15px;
    height: 15px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 10px;
    background: transparent;
    border: none;
    cursor: pointer;
    line-height: 1;
  }}
  .pill-del-btn:hover {{
    background: #da373c;
    color: #fff;
  }}
  .item-box {{
    background: rgba(0,0,0,0.25);
    border-radius: 6px;
    padding: 8px;
    border: 1px solid rgba(255,255,255,0.05);
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

  .canvas-stage {{
    display: flex;
    flex-direction: column;
    align-items: stretch;
    width: 100%;
    position: sticky;
    top: 8px;
    z-index: 10;
  }}
  .canvas-header {{
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
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
    max-width: 100%;
    min-height: 480px;
    background: #111214;
    border: 2px solid rgba(88,101,242,0.5);
    border-radius: 14px;
    overflow: hidden;
    position: relative;
    box-shadow: 0 12px 40px rgba(0,0,0,0.6);
    touch-action: none;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 10px;
  }}
  #mainCanvas {{
    max-width: 100%;
    width: auto;
    height: auto;
    max-height: 68vh;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    display: block;
    cursor: grab;
    transition: max-height 0.2s ease;
  }}
  #mainCanvas:active {{
    cursor: grabbing;
  }}
  .quick-tools {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin-top: 10px;
    width: 100%;
    justify-content: center;
  }}
  .quick-btn {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 11px;
    padding: 6px 12px;
    border-radius: 6px;
    cursor: pointer;
    font-weight: 600;
    transition: all 0.15s ease;
  }}
  .quick-btn:hover {{ color: #fff; border-color: var(--blurple); }}
  .action-row {{
    width: 100%;
    display: flex;
    gap: 8px;
    margin-top: 10px;
  }}
  .filename-row {{
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 10px;
    width: 100%;
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
    <div class="sidebar-grid">
      <!-- Left Sub-column -->
      <div class="sidebar-subcol">
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

        <!-- 3. Custom Accessories & Stickers -->
        <div class="card">
          <div class="card-title">
            <span class="step-badge">3</span>
            <span>Custom Accessories & Stickers</span>
          </div>
          <div class="hint">Upload any stickers or images and drag them freely:</div>

          <label class="btn-upload" style="margin-bottom:8px; padding:6px 10px; font-size:11px;">
            <span>📁 Upload Custom Accessory / Sticker</span>
            <input type="file" id="accFileInput" accept="image/*,.gif">
          </label>

          <div id="accLayersContainer" style="display:flex; gap:5px; flex-wrap:wrap; margin-bottom:8px;">
            <!-- Dynamically populated accessory pills -->
          </div>

          <div id="accControlsBox" class="item-box" style="display:none;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <span id="selectedAccTitle" style="font-size:11px; font-weight:700; color:#5865F2;">Accessory #1</span>
              <button id="deleteAccBtn" type="button" style="background:#da373c; color:#fff; border:none; border-radius:4px; padding:2px 7px; font-size:10px; font-weight:700; cursor:pointer;">🗑️ Remove</button>
            </div>
            <div class="slider-control">
              <label>Size: <span id="accScaleVal">100%</span></label>
              <input type="range" id="accScale" min="0.1" max="3.0" step="0.05" value="1.0">
            </div>
            <div class="slider-control">
              <label>Rotation: <span id="accRotVal">0°</span></label>
              <input type="range" id="accRot" min="-180" max="180" step="5" value="0">
            </div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
              <span style="font-size:11px; color:var(--text-muted); font-weight:600;">Flip:</span>
              <div class="btn-group" style="display:flex; gap:3px;">
                <button class="btn-toggle" id="accFlipHBtn" title="Flip horizontally">↔️ Flip H</button>
                <button class="btn-toggle" id="accFlipVBtn" title="Flip vertically">↕️ Flip V</button>
              </div>
            </div>
            <div class="slider-control" style="margin-top:6px;">
              <label>Opacity: <span id="accOpacityVal">100%</span></label>
              <input type="range" id="accOpacity" min="0.1" max="1.0" step="0.05" value="1.0">
            </div>
          </div>
        </div>
      </div>

      <!-- Right Sub-column -->
      <div class="sidebar-subcol">
        <!-- 2. Choose fruits Faces -->
        <div class="card">
          <div class="card-title">
            <span class="step-badge">2</span>
            <span>Choose fruits Faces</span>
          </div>
          <div class="hint">Pick a face or upload your own to slap on the meme:</div>

          <!-- Face Layers Bar (Multi-face manager) -->
          <div class="face-layers-bar">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
              <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:10px; font-weight:700; color:var(--text-muted);">ACTIVE FACE LAYERS:</span>
                <span id="faceLayersCount" style="font-size:10px; color:#5865F2; font-weight:700;">1 face</span>
              </div>
              <button id="addFaceLayerBtn" type="button" class="btn-add-face" title="Add another face layer to slap on the meme">➕ Add Face</button>
            </div>
            <div id="faceLayersContainer" style="display:flex; gap:5px; flex-wrap:wrap; align-items:center;">
              <!-- Dynamically populated face pills -->
            </div>
          </div>
          
          <label class="btn-upload" style="margin-bottom:8px; padding:6px 10px; font-size:11px;">
            <span>📸 Upload Custom Face / Sticker</span>
            <input type="file" id="faceFileInput" accept="image/*">
          </label>

          <div class="faces-grid" id="facesGrid"></div>
          
          <div class="row-flex">
            <span style="font-size: 11px; color: var(--text-muted);">Cutout Shape:</span>
            <div class="btn-group" id="maskGroup">
              <button class="btn-toggle active" data-mask="square">Full Frame (True Size)</button>
              <button class="btn-toggle" data-mask="circle">Sticker Circle</button>
              <button class="btn-toggle" data-mask="oval">Oval Face</button>
            </div>
          </div>
        </div>

        <!-- 4. Face Sizing, Flip & Filters -->
        <div class="card">
          <div class="card-title">
            <span class="step-badge">4</span>
            <span>Face Sizing, Flip & FX</span>
          </div>
          <div class="slider-control">
            <label>Size: <span id="sizeVal">100%</span></label>
            <input type="range" id="faceScale" min="0.3" max="2.5" step="0.05" value="1.0">
          </div>
          <div class="slider-control">
            <label>Rotation: <span id="rotVal">0°</span></label>
            <input type="range" id="faceRot" min="-180" max="180" step="5" value="0">
          </div>

          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
            <span style="font-size:11px; color:var(--text-muted); font-weight:600;">Flip Face:</span>
            <div class="btn-group" id="flipGroup" style="display:flex; gap:3px;">
              <button class="btn-toggle" id="flipHBtn" title="Mirror / Flip horizontally">↔️ Flip H</button>
              <button class="btn-toggle" id="flipVBtn" title="Flip vertically">↕️ Flip V</button>
            </div>
          </div>

          <div class="slider-control" style="margin-top:8px;">
            <label>Face Opacity: <span id="opacityVal">100%</span></label>
            <input type="range" id="faceOpacity" min="0.2" max="1.0" step="0.05" value="1.0">
          </div>

          <div style="margin-top:6px;">
            <label style="font-size:11px; color:var(--text-muted); display:block; margin-bottom:4px; font-weight:600;">Face Color FX:</label>
            <div class="btn-group" id="faceFilterGroup" style="display:flex; flex-wrap:wrap; gap:3px;">
              <button class="btn-toggle active" data-filter="none">Normal</button>
              <button class="btn-toggle" data-filter="grayscale">Noir B&W</button>
              <button class="btn-toggle" data-filter="deepfried">Deep Fried 🔥</button>
              <button class="btn-toggle" data-filter="invert">Invert ⚡</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 5. Discord GIF Animation & Text (Full width spanning both columns) -->
    <div class="card card-step5">
      <div class="card-title">
        <span class="step-badge">5</span>
        <span>Discord GIF Animation & Text</span>
      </div>
      <div class="step5-body">
        <div>
          <span style="font-size:11px; color:var(--text-muted); font-weight:600; display:block; margin-bottom:4px;">GIF Animation Preset:</span>
          <div class="anim-grid" id="animGrid">
            <button class="anim-btn active" data-anim="none"><span>🖼️</span><span>Still</span></button>
            <button class="anim-btn" data-anim="bob"><span>🕺</span><span>Head Bob</span></button>
            <button class="anim-btn" data-anim="shake"><span>💢</span><span>Shake</span></button>
            <button class="anim-btn" data-anim="spin"><span>🌀</span><span>Speen</span></button>
            <button class="anim-btn" data-anim="petpet"><span>👋</span><span>Petpet</span></button>
            <button class="anim-btn" data-anim="zoom"><span>💥</span><span>Zoom</span></button>
            <button class="anim-btn" data-anim="pulse"><span>💓</span><span>Pulse</span></button>
            <button class="anim-btn" data-anim="wobble"><span>🌊</span><span>Wobble</span></button>
            <button class="anim-btn" data-anim="disco"><span>🪩</span><span>Disco</span></button>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; justify-content:space-between;">
          <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:5px;">
              <span style="font-size:11px; color:var(--text-muted); font-weight:600;">Custom Movable Text:</span>
              <button id="addMovableTextBtn" type="button" class="btn-add-face" title="Add a movable text box anywhere on the canvas">➕ Add Text</button>
            </div>

            <div style="display:flex; gap:4px; margin-bottom:6px;">
              <button id="addTopPresetTextBtn" type="button" style="flex:1; background:var(--bg-input); border:1px solid var(--border); color:var(--text-muted); padding:3px 6px; border-radius:4px; font-size:10px; cursor:pointer; font-weight:600;">➕ Top Text</button>
              <button id="addBottomPresetTextBtn" type="button" style="flex:1; background:var(--bg-input); border:1px solid var(--border); color:var(--text-muted); padding:3px 6px; border-radius:4px; font-size:10px; cursor:pointer; font-weight:600;">➕ Bottom Text</button>
            </div>

            <div id="textLayersContainer" style="display:flex; gap:5px; flex-wrap:wrap; margin-bottom:6px;">
              <!-- Dynamically populated text pills -->
            </div>

            <div id="textControlsBox" class="item-box" style="display:none;">
              <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                <span id="selectedTextTitle" style="font-size:10px; font-weight:700; color:#5865F2;">Text #1</span>
                <button id="deleteTextBtn" type="button" style="background:#da373c; color:#fff; border:none; border-radius:4px; padding:2px 6px; font-size:10px; font-weight:700; cursor:pointer;">🗑️ Remove</button>
              </div>
              <input type="text" id="activeTextInput" class="caption-input" placeholder="Type text here..." style="margin-top:0; margin-bottom:6px; font-size:12px; padding:6px 8px;">
              
              <div style="display:grid; grid-template-columns: 1fr 1fr; gap:6px; margin-bottom:6px;">
                <div>
                  <span style="font-size:10px; color:var(--text-muted);">Size: <b id="textSizeVal" style="color:#fff;">36px</b></span>
                  <input type="range" id="textSizeSlider" min="14" max="90" step="2" value="36" style="width:100%;">
                </div>
                <div>
                  <span style="font-size:10px; color:var(--text-muted);">Rotate: <b id="textRotVal" style="color:#fff;">0°</b></span>
                  <input type="range" id="textRotSlider" min="-180" max="180" step="5" value="0" style="width:100%;">
                </div>
              </div>

              <div style="display:flex; align-items:center; justify-content:space-between;">
                <span style="font-size:10px; color:var(--text-muted); font-weight:600;">Color:</span>
                <div class="btn-group" id="textColorGroup" style="display:flex; gap:3px;">
                  <button class="btn-toggle active" data-color="#ffffff" style="color:#ffffff; font-size:10px; padding:2px 5px;">White</button>
                  <button class="btn-toggle" data-color="#facc15" style="color:#facc15; font-size:10px; padding:2px 5px;">Yellow</button>
                  <button class="btn-toggle" data-color="#ef4444" style="color:#ef4444; font-size:10px; padding:2px 5px;">Red</button>
                  <button class="btn-toggle" data-color="#22d3ee" style="color:#22d3ee; font-size:10px; padding:2px 5px;">Cyan</button>
                  <button class="btn-toggle" data-color="#4ade80" style="color:#4ade80; font-size:10px; padding:2px 5px;">Green</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

  </div>

  <!-- Stage Column -->
  <div class="canvas-stage">
    <div class="canvas-header">
      <div style="display:flex; align-items:center; gap:8px;">
        <div class="drag-badge">🖱️ CLICK & DRAG TO MOVE ANY FACE, STICKER OR TEXT!</div>
        <span style="font-size: 11px; color: var(--text-muted);">Scroll wheel = Zoom</span>
      </div>
      <div style="display:flex; align-items:center; gap:6px;">
        <span style="font-size: 11px; color: var(--text-muted); font-weight:600;">Preview Size:</span>
        <div class="btn-group" id="previewScaleGroup" style="display:flex; gap:3px;">
          <button class="btn-toggle active" data-scale="fit" title="Fit comfortably in screen height">📐 Auto-Fit</button>
          <button class="btn-toggle" data-scale="large" title="Enlarged 1.3x view">🔍 Large</button>
          <button class="btn-toggle" data-scale="max" title="Full size theater view">🌟 Max</button>
        </div>
      </div>
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

    <!-- Filename Input with Random Letters Suffix -->
    <div class="filename-row">
      <span style="font-size:11px; color:var(--text-muted); font-weight:600; white-space:nowrap;">Save As:</span>
      <input type="text" id="customFilenameInput" placeholder="murad_meme" value="murad_meme" style="flex:1; background:var(--bg-input); border:1px solid var(--border); color:#fff; font-size:11px; padding:6px 10px; border-radius:6px; outline:none;">
      <span style="font-size:10px; color:#5865F2; background:rgba(88,101,242,0.15); padding:3px 6px; border-radius:4px; font-family:monospace;" title="Random letters are automatically attached to avoid duplicates">+ random letters</span>
    </div>

    <div class="action-row">
      <button id="downloadGifBtn" class="btn-action-primary">⬇️ Download .GIF</button>
      <button id="downloadPngBtn" class="btn-action-secondary">⬇️ Download .PNG</button>
      <button id="copyPngBtn" class="btn-action-secondary" title="Copy image to clipboard for instant pasting in Discord">📋 Copy</button>
    </div>

    <!-- Progress bar -->
    <div class="progress-wrap" id="progressWrap">
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

  // Custom User Accessories & Stickers
  accessoriesOnCanvas: [],
  selectedAccIdx: -1,

  // Custom Movable Text Layers
  textsOnCanvas: [],
  selectedTextIdx: -1,

  // Active Drag
  isDragging: false,
  dragTarget: null, // type: 'face' or 'acc' or 'text'
  dragStartX: 0,
  dragStartY: 0,
  initialTargetX: 0,
  initialTargetY: 0,

  // Background
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

  // Animation
  anim: 'none',
  frame: 0,
  totalFrames: 12,
  fps: 12
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

  const badge = document.getElementById('canvasDimsBadge');
  if (badge) badge.innerText = `${{w}}x${{h}}`;
}}

function getSelectedFace() {{
  if (!state.facesOnCanvas || state.facesOnCanvas.length === 0) return null;
  if (state.selectedFaceIdx < 0 || state.selectedFaceIdx >= state.facesOnCanvas.length) {{
    state.selectedFaceIdx = 0;
  }}
  return state.facesOnCanvas[state.selectedFaceIdx];
}}

function syncControlsToSelectedFace() {{
  const cur = getSelectedFace();
  if (!cur) return;

  // Face Grid active thumbnail
  document.querySelectorAll('.face-btn').forEach((b, idx) => {{
    b.classList.toggle('active', idx === cur.faceIndex);
  }});

  // Cutout Mask
  document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => {{
    b.classList.toggle('active', b.dataset.mask === cur.mask);
  }});

  // Scale & Rot
  const scaleSlider = document.getElementById('faceScale');
  if (scaleSlider) scaleSlider.value = cur.scale;
  const sizeVal = document.getElementById('sizeVal');
  if (sizeVal) sizeVal.innerText = Math.round(cur.scale * 100) + '%';

  const rotSlider = document.getElementById('faceRot');
  if (rotSlider) rotSlider.value = cur.rot;
  const rotVal = document.getElementById('rotVal');
  if (rotVal) rotVal.innerText = cur.rot + '°';

  // Flip
  const flipHBtn = document.getElementById('flipHBtn');
  if (flipHBtn) flipHBtn.classList.toggle('active', !!cur.flipH);
  const flipVBtn = document.getElementById('flipVBtn');
  if (flipVBtn) flipVBtn.classList.toggle('active', !!cur.flipV);

  // Opacity
  const opacitySlider = document.getElementById('faceOpacity');
  if (opacitySlider) opacitySlider.value = cur.opacity !== undefined ? cur.opacity : 1.0;
  const opacityVal = document.getElementById('opacityVal');
  if (opacityVal) opacityVal.innerText = Math.round((cur.opacity !== undefined ? cur.opacity : 1.0) * 100) + '%';

  // Filter
  document.querySelectorAll('#faceFilterGroup .btn-toggle').forEach(b => {{
    b.classList.toggle('active', b.dataset.filter === (cur.filter || 'none'));
  }});
}}

function renderFaceLayersUI() {{
  const container = document.getElementById('faceLayersContainer');
  const countEl = document.getElementById('faceLayersCount');
  if (!container) return;
  container.innerHTML = '';
  if (countEl) {{
    countEl.innerText = state.facesOnCanvas.length + (state.facesOnCanvas.length === 1 ? ' face' : ' faces');
  }}

  state.facesOnCanvas.forEach((fLayer, idx) => {{
    const pill = document.createElement('div');
    const isAct = (idx === state.selectedFaceIdx && state.selectedAccIdx === -1 && state.selectedTextIdx === -1);
    pill.className = 'face-layer-pill' + (isAct ? ' active' : '');
    const faceObj = faces[fLayer.faceIndex] || {{ name: 'Murad', src: '' }};
    const cleanName = faceObj.name.replace(/[^a-zA-Z0-9 ]/g, '').trim().split(' ')[0] || ('Face #' + (idx+1));
    const thumbHtml = faceObj.src ? `<img src="${{faceObj.src}}">` : `<span>🎭</span>`;
    
    pill.innerHTML = `
      ${{thumbHtml}}
      <span>${{cleanName}}</span>
      ${{state.facesOnCanvas.length > 1 ? '<button class="pill-del-btn" title="Remove this face" type="button">✕</button>' : ''}}
    `;

    pill.onclick = (e) => {{
      if (e.target.classList.contains('pill-del-btn')) {{
        e.stopPropagation();
        deleteFaceLayer(idx);
        return;
      }}
      state.selectedFaceIdx = idx;
      state.selectedAccIdx = -1;
      state.selectedTextIdx = -1;
      syncControlsToSelectedFace();
      renderFaceLayersUI();
      renderAccLayersUI();
      renderTextLayersUI();
      draw();
    }};

    container.appendChild(pill);
  }});
}}

function deleteFaceLayer(idx) {{
  if (state.facesOnCanvas.length <= 1) return;
  state.facesOnCanvas.splice(idx, 1);
  if (state.selectedFaceIdx >= state.facesOnCanvas.length) {{
    state.selectedFaceIdx = state.facesOnCanvas.length - 1;
  }}
  syncControlsToSelectedFace();
  renderFaceLayersUI();
  draw();
}}

// -------------------------------------------------------------
// CUSTOM USER ACCESSORIES / STICKERS HELPERS
// -------------------------------------------------------------
function getSelectedAcc() {{
  if (!state.accessoriesOnCanvas || state.accessoriesOnCanvas.length === 0) return null;
  if (state.selectedAccIdx < 0 || state.selectedAccIdx >= state.accessoriesOnCanvas.length) {{
    return null;
  }}
  return state.accessoriesOnCanvas[state.selectedAccIdx];
}}

function syncControlsToSelectedAcc() {{
  const box = document.getElementById('accControlsBox');
  const cur = getSelectedAcc();
  if (!cur || !box) {{
    if (box) box.style.display = 'none';
    return;
  }}
  box.style.display = 'block';
  const title = document.getElementById('selectedAccTitle');
  if (title) title.innerText = cur.name || 'Accessory';

  const scaleInput = document.getElementById('accScale');
  if (scaleInput) scaleInput.value = cur.scale;
  const scaleVal = document.getElementById('accScaleVal');
  if (scaleVal) scaleVal.innerText = Math.round(cur.scale * 100) + '%';

  const rotInput = document.getElementById('accRot');
  if (rotInput) rotInput.value = cur.rot;
  const rotVal = document.getElementById('accRotVal');
  if (rotVal) rotVal.innerText = cur.rot + '°';

  const flipHBtn = document.getElementById('accFlipHBtn');
  if (flipHBtn) flipHBtn.classList.toggle('active', !!cur.flipH);
  const flipVBtn = document.getElementById('accFlipVBtn');
  if (flipVBtn) flipVBtn.classList.toggle('active', !!cur.flipV);

  const opInput = document.getElementById('accOpacity');
  if (opInput) opInput.value = cur.opacity !== undefined ? cur.opacity : 1.0;
  const opVal = document.getElementById('accOpacityVal');
  if (opVal) opVal.innerText = Math.round((cur.opacity !== undefined ? cur.opacity : 1.0) * 100) + '%';
}}

function renderAccLayersUI() {{
  const container = document.getElementById('accLayersContainer');
  if (!container) return;
  container.innerHTML = '';

  state.accessoriesOnCanvas.forEach((acc, idx) => {{
    const pill = document.createElement('div');
    const isAct = (idx === state.selectedAccIdx);
    pill.className = 'acc-layer-pill' + (isAct ? ' active' : '');
    const imgEl = acc.img && acc.img.src ? `<img src="${{acc.img.src}}">` : `<span>🎀</span>`;
    pill.innerHTML = `
      ${{imgEl}}
      <span style="overflow:hidden; text-overflow:ellipsis; max-width:80px;">${{acc.name || ('Sticker #' + (idx+1))}}</span>
      <button class="pill-del-btn" title="Remove accessory" type="button">✕</button>
    `;

    pill.onclick = (e) => {{
      if (e.target.classList.contains('pill-del-btn')) {{
        e.stopPropagation();
        deleteAcc(idx);
        return;
      }}
      state.selectedAccIdx = idx;
      state.selectedFaceIdx = -1;
      state.selectedTextIdx = -1;
      renderAccLayersUI();
      syncControlsToSelectedAcc();
      renderFaceLayersUI();
      renderTextLayersUI();
      draw();
    }};

    container.appendChild(pill);
  }});
  syncControlsToSelectedAcc();
}}

function deleteAcc(idx) {{
  state.accessoriesOnCanvas.splice(idx, 1);
  if (state.selectedAccIdx === idx) {{
    state.selectedAccIdx = state.accessoriesOnCanvas.length - 1;
  }} else if (state.selectedAccIdx > idx) {{
    state.selectedAccIdx--;
  }}
  renderAccLayersUI();
  syncControlsToSelectedAcc();
  draw();
}}

// -------------------------------------------------------------
// CUSTOM MOVABLE TEXT HELPERS
// -------------------------------------------------------------
function getSelectedText() {{
  if (!state.textsOnCanvas || state.textsOnCanvas.length === 0) return null;
  if (state.selectedTextIdx < 0 || state.selectedTextIdx >= state.textsOnCanvas.length) {{
    return null;
  }}
  return state.textsOnCanvas[state.selectedTextIdx];
}}

function syncControlsToSelectedText() {{
  const box = document.getElementById('textControlsBox');
  const cur = getSelectedText();
  if (!cur || !box) {{
    if (box) box.style.display = 'none';
    return;
  }}
  box.style.display = 'block';

  const title = document.getElementById('selectedTextTitle');
  if (title) title.innerText = cur.text ? `"${{cur.text.slice(0, 10)}}${{cur.text.length > 10 ? '...' : ''}}"` : 'Text';

  const textInput = document.getElementById('activeTextInput');
  if (textInput && textInput !== document.activeElement) textInput.value = cur.text;

  const sizeInput = document.getElementById('textSizeSlider');
  if (sizeInput) sizeInput.value = cur.size;
  const sizeVal = document.getElementById('textSizeVal');
  if (sizeVal) sizeVal.innerText = cur.size + 'px';

  const rotInput = document.getElementById('textRotSlider');
  if (rotInput) rotInput.value = cur.rot;
  const rotVal = document.getElementById('textRotVal');
  if (rotVal) rotVal.innerText = cur.rot + '°';

  document.querySelectorAll('#textColorGroup .btn-toggle').forEach(btn => {{
    btn.classList.toggle('active', btn.dataset.color === cur.color);
  }});
}}

function renderTextLayersUI() {{
  const container = document.getElementById('textLayersContainer');
  if (!container) return;
  container.innerHTML = '';

  state.textsOnCanvas.forEach((txt, idx) => {{
    const pill = document.createElement('div');
    const isAct = (idx === state.selectedTextIdx);
    pill.className = 'text-layer-pill' + (isAct ? ' active' : '');
    const displayText = txt.text || ('Text #' + (idx+1));
    pill.innerHTML = `
      <span>💬</span>
      <span style="overflow:hidden; text-overflow:ellipsis; max-width:85px;">${{displayText}}</span>
      <button class="pill-del-btn" title="Remove text" type="button">✕</button>
    `;

    pill.onclick = (e) => {{
      if (e.target.classList.contains('pill-del-btn')) {{
        e.stopPropagation();
        deleteText(idx);
        return;
      }}
      state.selectedTextIdx = idx;
      state.selectedAccIdx = -1;
      state.selectedFaceIdx = -1;
      renderTextLayersUI();
      syncControlsToSelectedText();
      renderFaceLayersUI();
      renderAccLayersUI();
      draw();
    }};

    container.appendChild(pill);
  }});
  syncControlsToSelectedText();
}}

function addMovableText(defaultText, defaultY) {{
  const id = 'txt_' + Date.now() + '_' + Math.floor(Math.random() * 1000);
  const newTxt = {{
    id: id,
    text: defaultText || 'MEME TEXT',
    x: 0,
    y: defaultY !== undefined ? defaultY : 0,
    size: 38,
    color: '#ffffff',
    strokeColor: '#000000',
    rot: 0
  }};
  state.textsOnCanvas.push(newTxt);
  state.selectedTextIdx = state.textsOnCanvas.length - 1;
  state.selectedAccIdx = -1;
  state.selectedFaceIdx = -1;
  renderTextLayersUI();
  syncControlsToSelectedText();
  renderFaceLayersUI();
  renderAccLayersUI();
  draw();
  const input = document.getElementById('activeTextInput');
  if (input) {{
    input.focus();
    input.select();
  }}
}}

function deleteText(idx) {{
  state.textsOnCanvas.splice(idx, 1);
  if (state.selectedTextIdx === idx) {{
    state.selectedTextIdx = state.textsOnCanvas.length - 1;
  }} else if (state.selectedTextIdx > idx) {{
    state.selectedTextIdx--;
  }}
  renderTextLayersUI();
  syncControlsToSelectedText();
  draw();
}}

// Decode Animated GIF Background
async function parseAndLoadGif(arrayBuffer) {{
  if (typeof window.GIF === 'undefined') {{
    console.error('gifuct-js is not loaded');
    return false;
  }}
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
      const cur = getSelectedFace();
      if (cur) {{
        if (t.id === 'suit') {{ cur.x = 0; cur.y = -65; cur.scale = 1.0; }}
        else if (t.id === 'gigachad') {{ cur.x = 0; cur.y = -60; cur.scale = 0.95; }}
        else if (t.id === 'throne') {{ cur.x = 0; cur.y = -50; cur.scale = 0.85; }}
        else if (t.id === 'astronaut') {{ cur.x = 0; cur.y = -35; cur.scale = 0.85; }}
        else if (t.id === 'doge') {{ cur.x = 0; cur.y = -35; cur.scale = 0.9; }}
        syncControlsToSelectedFace();
      }}

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
  if (!container) return;
  container.innerHTML = '';
  faces.forEach((f, idx) => {{
    const btn = document.createElement('div');
    const cur = getSelectedFace();
    const isAct = cur ? (cur.faceIndex === idx) : (idx === 0);
    btn.className = 'face-btn' + (isAct ? ' active' : '');
    btn.innerHTML = `<img src="${{f.src}}"><span>${{f.name}}</span>`;
    btn.onclick = () => {{
      const cFace = getSelectedFace();
      if (cFace) {{
        cFace.faceIndex = idx;
        syncControlsToSelectedFace();
        renderFaceLayersUI();
        draw();
      }}
    }};
    container.appendChild(btn);
  }});
}}

function setupEvents() {{
  buildTemplatesUI();
  buildFacesUI();
  renderFaceLayersUI();
  syncControlsToSelectedFace();
  renderAccLayersUI();
  renderTextLayersUI();

  // Multi-face add layer
  const addFaceBtn = document.getElementById('addFaceLayerBtn');
  if (addFaceBtn) {{
    addFaceBtn.onclick = () => {{
      const newLayer = makeFaceLayer(0, 20, -50, 0.9);
      state.facesOnCanvas.push(newLayer);
      state.selectedFaceIdx = state.facesOnCanvas.length - 1;
      state.selectedAccIdx = -1;
      state.selectedTextIdx = -1;
      syncControlsToSelectedFace();
      renderFaceLayersUI();
      renderAccLayersUI();
      renderTextLayersUI();
      draw();
    }};
  }}

  // Background file input
  const bgFileInput = document.getElementById('bgFileInput');
  if (bgFileInput) {{
    bgFileInput.onchange = async (e) => {{
      if (e.target.files && e.target.files[0]) {{
        const file = e.target.files[0];
        const isGif = file.type === 'image/gif' || file.name.toLowerCase().endsWith('.gif');
        document.querySelectorAll('#bgPresetsRow .preset-btn').forEach(b => b.classList.remove('active'));

        if (isGif) {{
          const buffer = await file.arrayBuffer();
          const ok = await parseAndLoadGif(buffer);
          if (ok) {{
            draw();
            return;
          }}
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

  // Canvas Size & Ratio buttons
  document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#canvasSizeGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.canvasSizeRatio = btn.dataset.size;
      updateCanvasDimensions();
      draw();
    }};
  }});

  // Background Fit Mode
  document.querySelectorAll('#bgFitGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#bgFitGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.bgFitMode = btn.dataset.fit;
      draw();
    }};
  }});

  // Background Zoom Slider
  const bgZoomSlider = document.getElementById('bgZoomSlider');
  if (bgZoomSlider) {{
    bgZoomSlider.oninput = (e) => {{
      state.bgScale = parseFloat(e.target.value);
      document.getElementById('bgZoomVal').innerText = Math.round(state.bgScale * 100) + '%';
      draw();
    }};
  }}

  // Background Pan Sliders
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
              id: 'custom_upload_' + Date.now(),
              name: 'My Upload 📸',
              src: evt.target.result
            }});
            state.facesOnCanvas.forEach(fl => {{
              fl.faceIndex += 1;
            }});
            const cur = getSelectedFace();
            if (cur) {{
              cur.faceIndex = 0;
              cur.mask = 'square';
            }}
            buildFacesUI();
            syncControlsToSelectedFace();
            renderFaceLayersUI();
            draw();
          }};
          img.src = evt.target.result;
        }};
        reader.readAsDataURL(e.target.files[0]);
      }}
    }};
  }}

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

  // Custom Accessory Upload
  const accFileInput = document.getElementById('accFileInput');
  if (accFileInput) {{
    accFileInput.onchange = (e) => {{
      if (e.target.files && e.target.files[0]) {{
        const file = e.target.files[0];
        const reader = new FileReader();
        reader.onload = (evt) => {{
          const img = new Image();
          img.onload = () => {{
            const rawName = file.name.split('.')[0];
            state.accessoriesOnCanvas.push({{
              id: 'acc_' + Date.now(),
              name: rawName.slice(0, 12),
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
            renderAccLayersUI();
            renderFaceLayersUI();
            renderTextLayersUI();
            draw();
          }};
          img.src = evt.target.result;
        }};
        reader.readAsDataURL(file);
      }}
    }};
  }}

  // Accessory Controls
  const accScale = document.getElementById('accScale');
  if (accScale) {{
    accScale.oninput = (e) => {{
      const cur = getSelectedAcc();
      if (!cur) return;
      cur.scale = parseFloat(e.target.value);
      document.getElementById('accScaleVal').innerText = Math.round(cur.scale * 100) + '%';
      draw();
    }};
  }}

  const accRot = document.getElementById('accRot');
  if (accRot) {{
    accRot.oninput = (e) => {{
      const cur = getSelectedAcc();
      if (!cur) return;
      cur.rot = parseInt(e.target.value);
      document.getElementById('accRotVal').innerText = cur.rot + '°';
      draw();
    }};
  }}

  const accFlipHBtn = document.getElementById('accFlipHBtn');
  if (accFlipHBtn) {{
    accFlipHBtn.onclick = () => {{
      const cur = getSelectedAcc();
      if (!cur) return;
      cur.flipH = !cur.flipH;
      accFlipHBtn.classList.toggle('active', cur.flipH);
      draw();
    }};
  }}

  const accFlipVBtn = document.getElementById('accFlipVBtn');
  if (accFlipVBtn) {{
    accFlipVBtn.onclick = () => {{
      const cur = getSelectedAcc();
      if (!cur) return;
      cur.flipV = !cur.flipV;
      accFlipVBtn.classList.toggle('active', cur.flipV);
      draw();
    }};
  }}

  const accOpacity = document.getElementById('accOpacity');
  if (accOpacity) {{
    accOpacity.oninput = (e) => {{
      const cur = getSelectedAcc();
      if (!cur) return;
      cur.opacity = parseFloat(e.target.value);
      document.getElementById('accOpacityVal').innerText = Math.round(cur.opacity * 100) + '%';
      draw();
    }};
  }}

  const deleteAccBtn = document.getElementById('deleteAccBtn');
  if (deleteAccBtn) {{
    deleteAccBtn.onclick = () => {{
      if (state.selectedAccIdx >= 0) {{
        deleteAcc(state.selectedAccIdx);
      }}
    }};
  }}

  // Custom Movable Text Buttons & Controls
  const addMovableTextBtn = document.getElementById('addMovableTextBtn');
  if (addMovableTextBtn) {{
    addMovableTextBtn.onclick = () => {{
      addMovableText('MEME TEXT', 0);
    }};
  }}

  const addTopPresetTextBtn = document.getElementById('addTopPresetTextBtn');
  if (addTopPresetTextBtn) {{
    addTopPresetTextBtn.onclick = () => {{
      addMovableText('TOP TEXT', -Math.round(canvas.height * 0.38));
    }};
  }}

  const addBottomPresetTextBtn = document.getElementById('addBottomPresetTextBtn');
  if (addBottomPresetTextBtn) {{
    addBottomPresetTextBtn.onclick = () => {{
      addMovableText('BOTTOM TEXT', Math.round(canvas.height * 0.38));
    }};
  }}

  const activeTextInput = document.getElementById('activeTextInput');
  if (activeTextInput) {{
    activeTextInput.oninput = (e) => {{
      const cur = getSelectedText();
      if (!cur) return;
      cur.text = e.target.value;
      const title = document.getElementById('selectedTextTitle');
      if (title) title.innerText = cur.text ? `"${{cur.text.slice(0, 10)}}${{cur.text.length > 10 ? '...' : ''}}"` : 'Text';
      renderTextLayersUI();
      draw();
    }};
  }}

  const textSizeSlider = document.getElementById('textSizeSlider');
  if (textSizeSlider) {{
    textSizeSlider.oninput = (e) => {{
      const cur = getSelectedText();
      if (!cur) return;
      cur.size = parseInt(e.target.value);
      document.getElementById('textSizeVal').innerText = cur.size + 'px';
      draw();
    }};
  }}

  const textRotSlider = document.getElementById('textRotSlider');
  if (textRotSlider) {{
    textRotSlider.oninput = (e) => {{
      const cur = getSelectedText();
      if (!cur) return;
      cur.rot = parseInt(e.target.value);
      document.getElementById('textRotVal').innerText = cur.rot + '°';
      draw();
    }};
  }}

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

  const deleteTextBtn = document.getElementById('deleteTextBtn');
  if (deleteTextBtn) {{
    deleteTextBtn.onclick = () => {{
      if (state.selectedTextIdx >= 0) {{
        deleteText(state.selectedTextIdx);
      }}
    }};
  }}

  // Face Flip Horizontal & Vertical
  const flipHBtn = document.getElementById('flipHBtn');
  if (flipHBtn) {{
    flipHBtn.onclick = () => {{
      const cur = getSelectedFace();
      if (!cur) return;
      cur.flipH = !cur.flipH;
      flipHBtn.classList.toggle('active', cur.flipH);
      draw();
    }};
  }}

  const flipVBtn = document.getElementById('flipVBtn');
  if (flipVBtn) {{
    flipVBtn.onclick = () => {{
      const cur = getSelectedFace();
      if (!cur) return;
      cur.flipV = !cur.flipV;
      flipVBtn.classList.toggle('active', cur.flipV);
      draw();
    }};
  }}

  // Face Opacity
  const faceOpacitySlider = document.getElementById('faceOpacity');
  if (faceOpacitySlider) {{
    faceOpacitySlider.oninput = (e) => {{
      const cur = getSelectedFace();
      if (!cur) return;
      cur.opacity = parseFloat(e.target.value);
      document.getElementById('opacityVal').innerText = Math.round(cur.opacity * 100) + '%';
      draw();
    }};
  }}

  // Face Filter Group
  document.querySelectorAll('#faceFilterGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      const cur = getSelectedFace();
      if (!cur) return;
      document.querySelectorAll('#faceFilterGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      cur.filter = btn.dataset.filter;
      draw();
    }};
  }});

  document.getElementById('faceScale').oninput = (e) => {{
    const cur = getSelectedFace();
    if (!cur) return;
    cur.scale = parseFloat(e.target.value);
    document.getElementById('sizeVal').innerText = Math.round(cur.scale * 100) + '%';
    draw();
  }};

  document.getElementById('faceRot').oninput = (e) => {{
    const cur = getSelectedFace();
    if (!cur) return;
    cur.rot = parseInt(e.target.value);
    document.getElementById('rotVal').innerText = cur.rot + '°';
    draw();
  }};

  // Quick tools apply to active selected element (Text, Accessory, or Face!)
  document.getElementById('zoomInBtn').onclick = () => {{
    if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
      const cur = state.textsOnCanvas[state.selectedTextIdx];
      cur.size = Math.min(90, cur.size + 4);
      syncControlsToSelectedText();
      draw();
      return;
    }}
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.scale = Math.min(3.0, cur.scale + 0.15);
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.scale = Math.min(2.5, cur.scale + 0.15);
    document.getElementById('faceScale').value = cur.scale;
    document.getElementById('sizeVal').innerText = Math.round(cur.scale * 100) + '%';
    draw();
  }};

  document.getElementById('zoomOutBtn').onclick = () => {{
    if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
      const cur = state.textsOnCanvas[state.selectedTextIdx];
      cur.size = Math.max(14, cur.size - 4);
      syncControlsToSelectedText();
      draw();
      return;
    }}
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.scale = Math.max(0.1, cur.scale - 0.15);
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.scale = Math.max(0.3, cur.scale - 0.15);
    document.getElementById('faceScale').value = cur.scale;
    document.getElementById('sizeVal').innerText = Math.round(cur.scale * 100) + '%';
    draw();
  }};

  document.getElementById('rotLeftBtn').onclick = () => {{
    if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
      const cur = state.textsOnCanvas[state.selectedTextIdx];
      cur.rot = (cur.rot - 15) % 360;
      syncControlsToSelectedText();
      draw();
      return;
    }}
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.rot = (cur.rot - 15) % 360;
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.rot = (cur.rot - 15) % 360;
    document.getElementById('faceRot').value = cur.rot;
    document.getElementById('rotVal').innerText = cur.rot + '°';
    draw();
  }};

  document.getElementById('rotRightBtn').onclick = () => {{
    if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
      const cur = state.textsOnCanvas[state.selectedTextIdx];
      cur.rot = (cur.rot + 15) % 360;
      syncControlsToSelectedText();
      draw();
      return;
    }}
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.rot = (cur.rot + 15) % 360;
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.rot = (cur.rot + 15) % 360;
    document.getElementById('faceRot').value = cur.rot;
    document.getElementById('rotVal').innerText = cur.rot + '°';
    draw();
  }};

  document.getElementById('recenterBtn').onclick = () => {{
    if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
      const cur = state.textsOnCanvas[state.selectedTextIdx];
      cur.x = 0; cur.y = 0; cur.rot = 0;
      syncControlsToSelectedText();
      draw();
      return;
    }}
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.x = 0; cur.y = 0; cur.rot = 0;
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.x = 0;
    cur.y = -35;
    cur.rot = 0;
    cur.scale = 1.0;
    cur.flipH = false;
    cur.flipV = false;
    syncControlsToSelectedFace();
    draw();
  }};

  canvas.addEventListener('wheel', (e) => {{
    e.preventDefault();
    const delta = e.deltaY < 0 ? 0.05 : -0.05;
    if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
      const cur = state.textsOnCanvas[state.selectedTextIdx];
      cur.size = Math.max(14, Math.min(90, cur.size + (e.deltaY < 0 ? 2 : -2)));
      syncControlsToSelectedText();
      draw();
      return;
    }}
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.scale = Math.max(0.1, Math.min(3.0, cur.scale + delta));
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.scale = Math.max(0.3, Math.min(2.5, cur.scale + delta));
    document.getElementById('faceScale').value = cur.scale;
    document.getElementById('sizeVal').innerText = Math.round(cur.scale * 100) + '%';
    draw();
  }}, {{ passive: false }});

  document.querySelectorAll('#animGrid .anim-btn').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#animGrid .anim-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.anim = btn.dataset.anim;
      state.frame = 0;
      state.totalFrames = state.anim === 'none' ? 1 : (state.anim === 'petpet' ? 8 : (state.anim === 'disco' ? 16 : 12));
      state.fps = state.anim === 'petpet' ? 14 : 12;
      draw();
    }};
  }});

  document.querySelectorAll('#previewScaleGroup .btn-toggle').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#previewScaleGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const scale = btn.dataset.scale;
      const canvasEl = document.getElementById('mainCanvas');
      if (scale === 'fit') {{
        canvasEl.style.maxHeight = '68vh';
        canvasEl.style.width = 'auto';
      }} else if (scale === 'large') {{
        canvasEl.style.maxHeight = '82vh';
        canvasEl.style.width = 'auto';
      }} else if (scale === 'max') {{
        canvasEl.style.maxHeight = '94vh';
        canvasEl.style.width = '100%';
      }}
    }};
  }});

  document.getElementById('downloadPngBtn').onclick = downloadPng;
  document.getElementById('downloadGifBtn').onclick = exportGif;
  const copyBtn = document.getElementById('copyPngBtn');
  if (copyBtn) copyBtn.onclick = copyToClipboard;
}}

// -------------------------------------------------------------
// REAL-TIME MOUSE / TOUCH DRAG & DROP FOR FACES, STICKERS & TEXT
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
    let ax = 0, ay = 0, as = 1.0;
    const progress = (state.frame / state.totalFrames) * Math.PI * 2;
    if (state.anim === 'bob') {{
      ay = Math.sin(progress) * 14;
    }} else if (state.anim === 'shake') {{
      ax = (Math.random() - 0.5) * 12;
      ay = (Math.random() - 0.5) * 12;
    }}

    for (let i = state.facesOnCanvas.length - 1; i >= 0; i--) {{
      const f = state.facesOnCanvas[i];
      const img = loadedFaces[f.faceIndex];
      if (!img || !img.complete) continue;
      const cx = w/2 + f.x + ax;
      const cy = h/2 + f.y + ay;
      const baseSize = w * 0.44;
      const fAspect = (img.naturalWidth || img.width) / (img.naturalHeight || img.height);
      let fw = fAspect >= 1 ? baseSize : baseSize * fAspect;
      let fh = fAspect >= 1 ? baseSize / fAspect : baseSize;
      fw *= f.scale * as;
      fh *= f.scale * as;

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

    // 1. Check text first (topmost)
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
      renderTextLayersUI();
      syncControlsToSelectedText();
      renderFaceLayersUI();
      renderAccLayersUI();
      draw();
      return;
    }}

    // 2. Check accessory second
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
      renderAccLayersUI();
      syncControlsToSelectedAcc();
      renderFaceLayersUI();
      renderTextLayersUI();
      draw();
      return;
    }}

    // 3. Check face third
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
      renderFaceLayersUI();
      syncControlsToSelectedFace();
      renderAccLayersUI();
      renderTextLayersUI();
      draw();
      return;
    }}

    // Clicked empty area
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
      tCtx.shadowOffsetX = 0;
      tCtx.shadowOffsetY = 6;
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
      tCtx.shadowOffsetX = 0;
      tCtx.shadowOffsetY = 6;
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
      // Full Frame (True natural aspect ratio)
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

    // Disco Rainbow Aura
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

  // 3. Render Custom User Accessories & Stickers
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

    // Dashed selection box
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

    // Dashed selection box
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
      btn.innerText = '✅ Copied!';
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

# --- TOP HEADER & ADMIN PANEL (TOP RIGHT) ---
_, col_head_right = st.columns([5.5, 1.5])
with col_head_right:
    admin_ui = st.popover("🔐 Admin Panel", use_container_width=True) if hasattr(st, "popover") else st.expander("🔐 Admin Panel")
    with admin_ui:
        st.markdown("### 🔐 Admin Panel")
        st.caption("Manage default faces or upload new ones for all users.")

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

            # GitHub Token verification / Secret detection
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

            admin_tab_manage, admin_tab_add = st.tabs(["🗑️ Manage / Remove Faces", "➕ Add New Face"])

            with admin_tab_manage:
                st.markdown("#### Default Faces Catalog")
                current_manifest = []
                if MANIFEST_FILE.exists():
                    try:
                        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                            current_manifest = json.load(f)
                    except Exception:
                        pass

                if not current_manifest:
                    st.info("No default faces found in catalog.")
                else:
                    st.caption(f"{len(current_manifest)} faces found. Click Delete to remove duplicates, spam, or unwanted faces.")
                    for idx, item in enumerate(current_manifest):
                        c_img, c_name, c_action = st.columns([1, 2.8, 1.2])
                        local_f = ASSETS_DIR / item.get("file", "")
                        with c_img:
                            if local_f.exists():
                                st.image(str(local_f), width=44)
                            else:
                                st.write("🖼️")
                        with c_name:
                            st.markdown(f"<div style='font-size: 13px; font-weight: 600;'>{item.get('name', 'Unnamed')}</div><div style='font-size: 11px; color: #949ba4;'><code>{item.get('file', '')}</code></div>", unsafe_allow_html=True)
                        with c_action:
                            if st.button("🗑️ Remove", key=f"del_face_{idx}_{item.get('id', 'face')}", use_container_width=True):
                                # 1. Create updated manifest excluding this entry
                                new_manifest = [x for i, x in enumerate(current_manifest) if i != idx]
                                manifest_bytes = json.dumps(new_manifest, indent=2).encode("utf-8")
                                with open(MANIFEST_FILE, "wb") as f:
                                    f.write(manifest_bytes)

                                # 2. Delete local image file only if no other entry uses it
                                file_still_used = any(x.get("file") == item.get("file") for i, x in enumerate(current_manifest) if i != idx)
                                if not file_still_used and local_f.exists():
                                    try:
                                        local_f.unlink()
                                    except Exception:
                                        pass

                                # 3. Sync deletion to GitHub if token present
                                if gh_token:
                                    with st.spinner(f"Syncing deletion to GitHub repo..."):
                                        if not file_still_used:
                                            delete_file_from_github(
                                                "Aboodi-8", "Muradeditor", f"assets/{item.get('file', '')}",
                                                f"Delete face image: {item.get('name')}", gh_token
                                            )
                                        ok_man, err_man = push_file_to_github(
                                            "Aboodi-8", "Muradeditor", "assets/manifest.json",
                                            manifest_bytes,
                                            f"Update manifest: remove {item.get('name')}", gh_token
                                        )
                                        if ok_man:
                                            st.success(f"Removed '{item.get('name')}' from GitHub and local catalog!")
                                        else:
                                            st.warning(f"Removed locally, but GitHub manifest sync returned: {err_man}")
                                else:
                                    st.success(f"Removed '{item.get('name')}' locally! (Provide token to sync to GitHub)")
                                st.rerun()

            with admin_tab_add:
                new_face_name = st.text_input("Face Display Name & Emoji:", placeholder="e.g. Gaming Murad 🎮")
                new_face_file = st.file_uploader("Upload Face Image (PNG / JPG / WebP):", type=["png", "jpg", "jpeg", "webp"], key="top_face_file")

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
                        if gh_token:
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
                        else:
                            st.success(f"🎉 Saved locally! '{new_face_name}' added. Provide GitHub token to sync to repository.")
                            st.rerun()
        elif admin_pwd:
            st.error("❌ Incorrect Admin Password.")

# Embed Interactive HTML5 Canvas Application with Real-Time Mouse Dragging
components.html(html_app, height=1220, scrolling=True)
