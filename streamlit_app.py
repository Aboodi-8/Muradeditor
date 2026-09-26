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

# Custom minimal styles to remove extra padding
st.markdown("""
<style>
    #MainMenu, header, footer { visibility: hidden; }
    .block-container {
        padding-top: 0.25rem;
        padding-bottom: 0.5rem;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
        max-width: 100%;
    }
    .stApp {
        background-color: #1e1f22;
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

# --- EMBEDDED CANVA-STYLE STUDIO HTML5 APP ---
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
    --border-hover: rgba(255, 255, 255, 0.18);
    --blurple: #5865F2;
    --blurple-hover: #4752C4;
    --text-main: #f2f3f5;
    --text-muted: #949ba4;
    --green: #23a55a;
    --green-hover: #1f9350;
    --danger: #da373c;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    background: var(--bg-dark);
    color: var(--text-main);
    overflow-x: hidden;
    padding: 4px 8px;
  }}

  /* STUDIO MAIN CONTAINER */
  .studio-container {{
    display: grid;
    grid-template-columns: 370px 1fr;
    gap: 16px;
    width: 100%;
    max-width: 100%;
    margin: 0 auto;
    align-items: start;
    min-height: 92vh;
  }}

  /* STUDIO SIDEBAR (Rail + Panel) */
  .studio-sidebar {{
    display: flex;
    background: var(--bg-sidebar);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
    height: 88vh;
    box-shadow: 0 8px 24px rgba(0,0,0,0.3);
  }}

  /* TABS RAIL (Left Icon Strip) */
  .studio-tabs-rail {{
    width: 68px;
    background: #18191c;
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 10px 0;
    gap: 6px;
    border-right: 1px solid var(--border);
    flex-shrink: 0;
  }}
  .rail-tab {{
    width: 54px;
    height: 52px;
    background: transparent;
    border: none;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    color: var(--text-muted);
    transition: all 0.15s ease;
    gap: 3px;
    padding: 4px;
  }}
  .rail-tab:hover {{
    background: rgba(255,255,255,0.06);
    color: var(--text-main);
  }}
  .rail-tab.active {{
    background: rgba(88, 101, 242, 0.18);
    color: #fff;
    border-left: 3px solid var(--blurple);
    border-radius: 0 8px 8px 0;
  }}
  .rail-icon {{
    font-size: 18px;
    line-height: 1;
  }}
  .rail-label {{
    font-size: 9.5px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.3px;
  }}

  /* ACTIVE TAB PANEL */
  .studio-panel {{
    flex: 1;
    padding: 14px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
  }}
  .tab-pane {{
    display: none;
    flex-direction: column;
    gap: 12px;
  }}
  .tab-pane.active {{
    display: flex;
  }}

  .pane-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}
  .pane-title {{
    font-size: 14px;
    font-weight: 700;
    color: #fff;
  }}
  .pane-desc {{
    font-size: 11px;
    color: var(--text-muted);
    margin-top: 2px;
  }}

  /* BUTTONS & CONTROLS */
  .btn-primary-sm {{
    background: var(--blurple);
    color: #fff;
    border: none;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: background 0.15s ease;
  }}
  .btn-primary-sm:hover {{ background: var(--blurple-hover); }}

  .btn-upload-box {{
    display: block;
    background: rgba(88, 101, 242, 0.1);
    border: 1px dashed var(--blurple);
    border-radius: 8px;
    padding: 10px;
    text-align: center;
    color: #fff;
    font-size: 11.5px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-upload-box:hover {{
    background: rgba(88, 101, 242, 0.2);
    border-color: #fff;
  }}
  .btn-upload-box input {{ display: none; }}

  .section-label {{
    font-size: 10.5px;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.4px;
    display: block;
    margin-bottom: 4px;
  }}

  /* LAYERS CHIPS STRIP */
  .layers-strip {{
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
    align-items: center;
  }}
  .layer-pill {{
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
  }}
  .layer-pill.active {{
    border-color: var(--blurple);
    background: rgba(88, 101, 242, 0.25);
    color: #fff;
  }}
  .layer-pill img {{
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
    width: 14px;
    height: 14px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    font-size: 9px;
    background: transparent;
    border: none;
    cursor: pointer;
  }}
  .pill-del-btn:hover {{ background: var(--danger); color: #fff; }}

  /* FACES GRID */
  .faces-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    max-height: 240px;
    overflow-y: auto;
    padding-right: 2px;
  }}
  .face-btn {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .face-btn:hover {{
    border-color: var(--border-hover);
    transform: translateY(-1px);
  }}
  .face-btn.active {{
    border-color: var(--blurple);
    background: rgba(88, 101, 242, 0.2);
  }}
  .face-btn img {{
    width: 52px;
    height: 52px;
    border-radius: 6px;
    object-fit: cover;
    margin-bottom: 4px;
  }}
  .face-btn span {{
    font-size: 10px;
    color: var(--text-main);
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    width: 100%;
  }}

  /* PRESET BUTTONS ROW */
  .presets-row {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 5px;
  }}
  .preset-btn {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 6px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
    text-align: left;
    transition: all 0.15s ease;
  }}
  .preset-btn:hover {{ border-color: var(--blurple); }}
  .preset-btn.active {{
    background: rgba(88, 101, 242, 0.2);
    border-color: var(--blurple);
    color: #fff;
  }}

  /* BUTTON GROUPS & TOGGLES */
  .btn-group {{
    display: flex;
    background: var(--bg-input);
    border-radius: 6px;
    padding: 2px;
    border: 1px solid var(--border);
    gap: 2px;
  }}
  .btn-toggle {{
    flex: 1;
    background: transparent;
    border: none;
    color: var(--text-muted);
    font-size: 10.5px;
    font-weight: 600;
    padding: 5px 6px;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    text-align: center;
  }}
  .btn-toggle.active {{
    background: var(--blurple);
    color: #fff;
  }}

  /* ACCORDION */
  .accordion {{
    background: rgba(0,0,0,0.25);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 10px;
  }}
  .accordion summary {{
    font-size: 11px;
    font-weight: 700;
    color: var(--text-muted);
    cursor: pointer;
    outline: none;
    user-select: none;
  }}
  .accordion-content {{
    margin-top: 8px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }}

  /* SLIDER GROUPS */
  .slider-group {{
    display: flex;
    flex-direction: column;
    gap: 3px;
  }}
  .slider-group label {{
    font-size: 10.5px;
    color: var(--text-muted);
    display: flex;
    justify-content: space-between;
  }}
  .slider-group input[type="range"] {{
    width: 100%;
    accent-color: var(--blurple);
    cursor: pointer;
  }}

  /* ITEM EDIT CARD */
  .item-edit-card {{
    background: rgba(0,0,0,0.25);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 10px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .edit-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
  }}
  .edit-title {{
    font-size: 11px;
    font-weight: 700;
    color: var(--blurple);
  }}
  .btn-danger-xs {{
    background: var(--danger);
    color: #fff;
    border: none;
    border-radius: 4px;
    padding: 2px 7px;
    font-size: 10px;
    font-weight: 700;
    cursor: pointer;
  }}
  .btn-ghost-xs {{
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text-muted);
    font-size: 10px;
    padding: 2px 6px;
    border-radius: 4px;
    cursor: pointer;
  }}
  .btn-preset-text {{
    flex: 1;
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: var(--text-main);
    padding: 6px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    cursor: pointer;
  }}
  .pane-input {{
    width: 100%;
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: #fff;
    font-size: 12px;
    padding: 7px 10px;
    border-radius: 6px;
    outline: none;
  }}
  .empty-prompt {{
    padding: 14px 10px;
    text-align: center;
    color: var(--text-muted);
    font-size: 11px;
    background: rgba(0,0,0,0.15);
    border-radius: 8px;
    border: 1px dashed var(--border);
  }}

  /* ANIMATION GRID */
  .anim-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
  }}
  .anim-card {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 8px 4px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .anim-card:hover {{ border-color: var(--border-hover); }}
  .anim-card.active {{
    background: rgba(88, 101, 242, 0.2);
    border-color: var(--blurple);
  }}
  .anim-icon {{ font-size: 18px; line-height: 1; }}
  .anim-name {{ font-size: 10px; font-weight: 600; color: var(--text-main); text-align: center; }}

  /* ========================================================
     STAGE AREA (RIGHT COLUMN)
     ======================================================== */
  .studio-stage {{
    display: flex;
    flex-direction: column;
    gap: 8px;
    position: sticky;
    top: 4px;
    align-items: center;
  }}

  /* FLOATING CONTEXT BAR (TOP OF CANVAS) */
  .context-bar {{
    width: 100%;
    max-width: 680px;
    background: #232428;
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 6px 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.25);
  }}
  .context-info {{
    display: flex;
    align-items: center;
    gap: 8px;
    overflow: hidden;
  }}
  .context-badge {{
    background: rgba(88, 101, 242, 0.2);
    color: #5865F2;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 700;
    white-space: nowrap;
  }}
  .context-hint {{
    font-size: 10.5px;
    color: var(--text-muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }}
  .context-actions {{
    display: flex;
    gap: 3px;
    align-items: center;
  }}
  .btn-tool {{
    background: var(--bg-input);
    border: 1px solid var(--border);
    color: var(--text-main);
    width: 28px;
    height: 28px;
    border-radius: 5px;
    font-size: 12px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-tool:hover {{
    background: rgba(255,255,255,0.08);
    border-color: #fff;
  }}
  .btn-tool.danger:hover {{
    background: var(--danger);
    color: #fff;
    border-color: var(--danger);
  }}

  /* CANVAS VIEWPORT */
  .canvas-viewport {{
    width: 100%;
    max-width: 680px;
    background: #111214;
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    box-shadow: inset 0 2px 10px rgba(0,0,0,0.5);
  }}
  #mainCanvas {{
    max-width: 100%;
    max-height: 64vh;
    object-fit: contain;
    border-radius: 6px;
    cursor: grab;
    display: block;
    user-select: none;
    -webkit-user-select: none;
  }}
  #mainCanvas:active {{
    cursor: grabbing;
  }}

  /* STAGE FOOTER & DOWNLOAD BUTTONS */
  .stage-footer {{
    width: 100%;
    max-width: 680px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }}
  .action-buttons-row {{
    display: grid;
    grid-template-columns: 2fr 1fr 1fr;
    gap: 8px;
  }}
  .btn-download-gif {{
    background: var(--blurple);
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: 13px;
    font-weight: 700;
    padding: 10px;
    cursor: pointer;
    transition: background 0.15s ease;
    box-shadow: 0 4px 12px rgba(88,101,242,0.3);
  }}
  .btn-download-gif:hover {{ background: var(--blurple-hover); }}

  .btn-download-png {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: #fff;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 10px;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-download-png:hover {{ border-color: #fff; background: rgba(255,255,255,0.08); }}

  .btn-copy-png {{
    background: var(--bg-card);
    border: 1px solid var(--border);
    color: #fff;
    border-radius: 8px;
    font-size: 12px;
    font-weight: 600;
    padding: 10px;
    cursor: pointer;
    transition: all 0.15s ease;
  }}
  .btn-copy-png:hover {{ border-color: var(--green); color: var(--green); }}

  .filename-bar {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 4px 10px;
  }}
  .filename-label {{ font-size: 11px; color: var(--text-muted); font-weight: 600; }}
  .filename-bar input {{
    flex: 1;
    background: transparent;
    border: none;
    color: #fff;
    font-size: 11.5px;
    outline: none;
  }}
  .filename-suffix {{
    font-size: 10px;
    color: var(--blurple);
    background: rgba(88,101,242,0.15);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }}

  /* PROGRESS BAR */
  .progress-wrap {{
    width: 100%;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 10px;
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

  @media (max-width: 900px) {{
    .studio-container {{
      grid-template-columns: 1fr;
    }}
    .studio-sidebar {{
      height: auto;
      max-height: 480px;
    }}
    .studio-stage {{
      position: static;
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

<div class="studio-container">

  <!-- LEFT: TAB NAVIGATION & CONTROLS DRAWER -->
  <div class="studio-sidebar">

    <!-- Rail of Tabs (Icons) -->
    <div class="studio-tabs-rail">
      <button class="rail-tab active" data-tab="faces" title="Murad Faces">
        <span class="rail-icon">🎭</span>
        <span class="rail-label">Faces</span>
      </button>
      <button class="rail-tab" data-tab="bg" title="Background Image or Meme">
        <span class="rail-icon">🖼️</span>
        <span class="rail-label">Backdrop</span>
      </button>
      <button class="rail-tab" data-tab="text" title="Custom Movable Text">
        <span class="rail-icon">💬</span>
        <span class="rail-label">Text</span>
      </button>
      <button class="rail-tab" data-tab="stickers" title="Custom Uploaded Stickers">
        <span class="rail-icon">🎀</span>
        <span class="rail-label">Stickers</span>
      </button>
      <button class="rail-tab" data-tab="anim" title="Discord GIF Effects">
        <span class="rail-icon">✨</span>
        <span class="rail-label">Animate</span>
      </button>
    </div>

    <!-- Active Panel Content -->
    <div class="studio-panel">

      <!-- TAB 1: FACES -->
      <div class="tab-pane active" id="pane-faces">
        <div class="pane-header">
          <div>
            <h3 class="pane-title">Choose Face</h3>
            <p class="pane-desc">Pick Murad's face to slap on the meme</p>
          </div>
          <button id="addFaceLayerBtn" type="button" class="btn-primary-sm" title="Add another face layer">➕ Add Face</button>
        </div>

        <div class="layers-strip" id="faceLayersContainer"></div>

        <label class="btn-upload-box">
          <span>📸 Upload Your Own Photo / Face</span>
          <input type="file" id="faceFileInput" accept="image/*">
        </label>

        <label class="section-label">Default Faces</label>
        <div class="faces-grid" id="facesGrid"></div>

        <div class="panel-section">
          <label class="section-label">Cutout Shape</label>
          <div class="btn-group" id="maskGroup">
            <button class="btn-toggle active" data-mask="square">Full Frame</button>
            <button class="btn-toggle" data-mask="circle">Sticker Circle</button>
            <button class="btn-toggle" data-mask="oval">Oval Face</button>
          </div>
        </div>

        <details class="accordion">
          <summary>⚙️ Face Opacity & Color Filters</summary>
          <div class="accordion-content">
            <div class="slider-group">
              <label>Face Opacity: <b id="opacityVal">100%</b></label>
              <input type="range" id="faceOpacity" min="0.2" max="1.0" step="0.05" value="1.0">
            </div>
            <label class="section-label" style="margin-top:6px;">Color Filter</label>
            <div class="btn-group" id="faceFilterGroup">
              <button class="btn-toggle active" data-filter="none">Normal</button>
              <button class="btn-toggle" data-filter="bw">B&W</button>
              <button class="btn-toggle" data-filter="deepfried">Deep Fried 🔥</button>
              <button class="btn-toggle" data-filter="invert">Invert</button>
            </div>
          </div>
        </details>
      </div>

      <!-- TAB 2: BACKGROUND -->
      <div class="tab-pane" id="pane-bg">
        <div class="pane-header">
          <div>
            <h3 class="pane-title">Background & Backdrop</h3>
            <p class="pane-desc">Upload a picture, meme, or GIF</p>
          </div>
        </div>

        <label class="btn-upload-box">
          <span>📁 Upload Picture / Meme / Animated GIF</span>
          <input type="file" id="bgFileInput" accept="image/*,.gif">
        </label>

        <label class="section-label">Popular Body Templates</label>
        <div class="presets-row" id="bgPresetsRow"></div>

        <div class="panel-section">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <label class="section-label">Canvas Format</label>
            <span id="canvasDimsBadge" style="font-size:10px; color:#5865F2; background:rgba(88,101,242,0.15); padding:1px 6px; border-radius:4px;">500x500</span>
          </div>
          <div class="btn-group" id="canvasSizeGroup">
            <button class="btn-toggle active" data-size="true_size">📐 True Size</button>
            <button class="btn-toggle" data-size="square">⏹️ 1:1 Square</button>
            <button class="btn-toggle" data-size="landscape">🖼️ 16:9</button>
            <button class="btn-toggle" data-size="portrait">📱 9:16</button>
          </div>
        </div>

        <details class="accordion">
          <summary>✂️ Background Zoom & Framing</summary>
          <div class="accordion-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
              <span style="font-size:11px; color:var(--text-muted);">Fit Mode:</span>
              <button id="resetBgCropBtn" class="btn-ghost-xs">🔄 Reset Crop</button>
            </div>
            <div class="btn-group" id="bgFitGroup" style="margin-bottom:6px;">
              <button class="btn-toggle active" data-fit="cover">✂️ Fill & Crop</button>
              <button class="btn-toggle" data-fit="fit">🔍 Fit Whole Image</button>
            </div>
            <div class="slider-group">
              <label>Background Zoom: <b id="bgZoomVal">100%</b></label>
              <input type="range" id="bgZoomSlider" min="0.4" max="2.5" step="0.05" value="1.0">
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; margin-top:6px;">
              <div>
                <span style="font-size:10px; color:var(--text-muted);">Pan Left/Right:</span>
                <input type="range" id="bgPanXSlider" min="-300" max="300" step="2" value="0" style="width:100%;">
              </div>
              <div>
                <span style="font-size:10px; color:var(--text-muted);">Pan Up/Down:</span>
                <input type="range" id="bgPanYSlider" min="-300" max="300" step="2" value="0" style="width:100%;">
              </div>
            </div>
          </div>
        </details>
      </div>

      <!-- TAB 3: TEXT -->
      <div class="tab-pane" id="pane-text">
        <div class="pane-header">
          <div>
            <h3 class="pane-title">Meme Text</h3>
            <p class="pane-desc">Add movable text anywhere</p>
          </div>
          <button id="addMovableTextBtn" type="button" class="btn-primary-sm">➕ Add Text</button>
        </div>

        <div style="display:flex; gap:6px;">
          <button id="addTopPresetTextBtn" class="btn-preset-text">➕ Top Text</button>
          <button id="addBottomPresetTextBtn" class="btn-preset-text">➕ Bottom Text</button>
        </div>

        <div class="layers-strip" id="textLayersContainer"></div>

        <div id="textControlsBox" class="item-edit-card" style="display:none;">
          <div class="edit-header">
            <span id="selectedTextTitle" class="edit-title">Text Layer</span>
            <button id="deleteTextBtn" class="btn-danger-xs">🗑️ Delete</button>
          </div>
          <input type="text" id="activeTextInput" class="pane-input" placeholder="Type text here...">
          <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
            <div class="slider-group">
              <label>Size: <b id="textSizeVal">38px</b></label>
              <input type="range" id="textSizeSlider" min="14" max="90" step="2" value="38">
            </div>
            <div class="slider-group">
              <label>Rotate: <b id="textRotVal">0°</b></label>
              <input type="range" id="textRotSlider" min="-180" max="180" step="5" value="0">
            </div>
          </div>
          <label class="section-label" style="margin-top:4px;">Color</label>
          <div class="btn-group" id="textColorGroup">
            <button class="btn-toggle active" data-color="#ffffff">White</button>
            <button class="btn-toggle" data-color="#facc15" style="color:#facc15;">Yellow</button>
            <button class="btn-toggle" data-color="#ef4444" style="color:#ef4444;">Red</button>
            <button class="btn-toggle" data-color="#22d3ee" style="color:#22d3ee;">Cyan</button>
            <button class="btn-toggle" data-color="#4ade80" style="color:#4ade80;">Green</button>
          </div>
        </div>

        <div id="noTextPrompt" class="empty-prompt">
          <span>Click <b>"➕ Add Text"</b> above to slap movable captions onto the meme!</span>
        </div>
      </div>

      <!-- TAB 4: STICKERS -->
      <div class="tab-pane" id="pane-stickers">
        <div class="pane-header">
          <div>
            <h3 class="pane-title">Custom Stickers</h3>
            <p class="pane-desc">Upload accessories, logos or stickers</p>
          </div>
        </div>

        <label class="btn-upload-box">
          <span>📁 Upload Custom Sticker / PNG</span>
          <input type="file" id="accFileInput" accept="image/*,.gif">
        </label>

        <div class="layers-strip" id="accLayersContainer"></div>

        <div id="accControlsBox" class="item-edit-card" style="display:none;">
          <div class="edit-header">
            <span id="selectedAccTitle" class="edit-title">Sticker Layer</span>
            <button id="deleteAccBtn" class="btn-danger-xs">🗑️ Delete</button>
          </div>
          <div class="slider-group">
            <label>Size: <b id="accScaleVal">100%</b></label>
            <input type="range" id="accScale" min="0.1" max="3.0" step="0.05" value="1.0">
          </div>
          <div class="slider-group">
            <label>Rotate: <b id="accRotVal">0°</b></label>
            <input type="range" id="accRot" min="-180" max="180" step="5" value="0">
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
            <span style="font-size:11px; color:var(--text-muted); font-weight:600;">Flip:</span>
            <div class="btn-group" style="display:flex; gap:4px;">
              <button class="btn-toggle" id="accFlipHBtn">↔️ Flip H</button>
              <button class="btn-toggle" id="accFlipVBtn">↕️ Flip V</button>
            </div>
          </div>
          <div class="slider-group" style="margin-top:6px;">
            <label>Opacity: <b id="accOpacityVal">100%</b></label>
            <input type="range" id="accOpacity" min="0.1" max="1.0" step="0.05" value="1.0">
          </div>
        </div>

        <div id="noAccPrompt" class="empty-prompt">
          <span>Upload any accessory, sunglasses, hat, or sticker above to freely place & drag on the meme!</span>
        </div>
      </div>

      <!-- TAB 5: ANIMATE -->
      <div class="tab-pane" id="pane-anim">
        <div class="pane-header">
          <div>
            <h3 class="pane-title">Discord GIF Effects</h3>
            <p class="pane-desc">Choose motion effect for your meme</p>
          </div>
        </div>

        <div class="anim-grid" id="animGrid">
          <button class="anim-card active" data-anim="none">
            <span class="anim-icon">🖼️</span>
            <span class="anim-name">Still Image</span>
          </button>
          <button class="anim-card" data-anim="bob">
            <span class="anim-icon">🕺</span>
            <span class="anim-name">Head Bob</span>
          </button>
          <button class="anim-card" data-anim="shake">
            <span class="anim-icon">💢</span>
            <span class="anim-name">Shake Meme</span>
          </button>
          <button class="anim-card" data-anim="spin">
            <span class="anim-icon">🌀</span>
            <span class="anim-name">Speen 360°</span>
          </button>
          <button class="anim-card" data-anim="petpet">
            <span class="anim-icon">👋</span>
            <span class="anim-name">Petpet Hand</span>
          </button>
          <button class="anim-card" data-anim="zoom">
            <span class="anim-icon">💥</span>
            <span class="anim-name">Bass Pulse</span>
          </button>
          <button class="anim-card" data-anim="pulse">
            <span class="anim-icon">💓</span>
            <span class="anim-name">Heartbeat</span>
          </button>
          <button class="anim-card" data-anim="wobble">
            <span class="anim-icon">🌊</span>
            <span class="anim-name">Wobble</span>
          </button>
          <button class="anim-card" data-anim="disco">
            <span class="anim-icon">🪩</span>
            <span class="anim-name">Disco Party</span>
          </button>
        </div>
      </div>

    </div>
  </div>

  <!-- RIGHT: BIG CLEAN STAGE & EXPORT -->
  <div class="studio-stage">

    <!-- Floating Context Inspector Bar -->
    <div class="context-bar" id="contextBar">
      <div id="contextInfo" class="context-info">
        <span class="context-badge" id="contextBadge">🎭 Murad Face</span>
        <span class="context-hint">Click & drag on canvas to position</span>
      </div>
      <div class="context-actions" id="contextActions">
        <button id="quickZoomIn" class="btn-tool" title="Enlarge (+)">🔍+</button>
        <button id="quickZoomOut" class="btn-tool" title="Shrink (-)">🔍-</button>
        <button id="quickRotLeft" class="btn-tool" title="Rotate left 15°">↺</button>
        <button id="quickRotRight" class="btn-tool" title="Rotate right 15°">↻</button>
        <button id="quickFlipH" class="btn-tool" title="Flip horizontally">↔️</button>
        <button id="quickCenter" class="btn-tool" title="Center on canvas">🎯</button>
        <button id="quickDelete" class="btn-tool danger" title="Delete element">🗑️</button>
      </div>
    </div>

    <!-- The Canvas Viewport -->
    <div class="canvas-viewport" id="canvasBox">
      <canvas id="mainCanvas" width="500" height="500"></canvas>
    </div>

    <!-- Export Action Row -->
    <div class="stage-footer">
      <div class="action-buttons-row">
        <button id="downloadGifBtn" class="btn-download-gif">⬇️ Download .GIF</button>
        <button id="downloadPngBtn" class="btn-download-png">⬇️ Download .PNG</button>
        <button id="copyPngBtn" class="btn-copy-png" title="Copy to clipboard for instant Discord paste">📋 Copy</button>
      </div>

      <div class="filename-bar">
        <span class="filename-label">File Name:</span>
        <input type="text" id="customFilenameInput" value="murad_meme" placeholder="filename">
        <span class="filename-suffix">+ random letters</span>
      </div>

      <div class="progress-wrap" id="progressWrap" style="display:none;">
        <div class="progress-track"><div class="progress-bar" id="progressBar"></div></div>
        <div class="progress-text" id="progressText">Encoding Discord GIF...</div>
      </div>
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
  dragTarget: null, // type: 'face' or 'acc' or 'text'
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

// Update Context Inspector Banner
function updateContextBar() {{
  const badge = document.getElementById('contextBadge');
  const deleteBtn = document.getElementById('quickDelete');

  if (state.selectedTextIdx >= 0 && state.textsOnCanvas[state.selectedTextIdx]) {{
    const cur = state.textsOnCanvas[state.selectedTextIdx];
    badge.innerText = `💬 "${{cur.text.slice(0, 10)}}${{cur.text.length > 10 ? '...' : ''}}"`;
    if (deleteBtn) deleteBtn.style.display = 'inline-flex';
    return;
  }}

  if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
    const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
    badge.innerText = `🎀 ${{cur.name || 'Sticker'}}`;
    if (deleteBtn) deleteBtn.style.display = 'inline-flex';
    return;
  }}

  if (state.selectedFaceIdx >= 0 && state.facesOnCanvas[state.selectedFaceIdx]) {{
    const cur = state.facesOnCanvas[state.selectedFaceIdx];
    const faceObj = faces[cur.faceIndex];
    badge.innerText = `🎭 ${{faceObj ? faceObj.name.split(' ')[0] : 'Face'}}`;
    if (deleteBtn) deleteBtn.style.display = state.facesOnCanvas.length > 1 ? 'inline-flex' : 'none';
    return;
  }}

  badge.innerText = '🖼️ Background';
  if (deleteBtn) deleteBtn.style.display = 'none';
}}

function syncControlsToSelectedFace() {{
  const cur = getSelectedFace();
  if (!cur) return;

  document.querySelectorAll('.face-btn').forEach((b, idx) => {{
    b.classList.toggle('active', idx === cur.faceIndex);
  }});

  document.querySelectorAll('#maskGroup .btn-toggle').forEach(b => {{
    b.classList.toggle('active', b.dataset.mask === cur.mask);
  }});

  const opacitySlider = document.getElementById('faceOpacity');
  if (opacitySlider) opacitySlider.value = cur.opacity !== undefined ? cur.opacity : 1.0;
  const opacityVal = document.getElementById('opacityVal');
  if (opacityVal) opacityVal.innerText = Math.round((cur.opacity !== undefined ? cur.opacity : 1.0) * 100) + '%';

  document.querySelectorAll('#faceFilterGroup .btn-toggle').forEach(b => {{
    b.classList.toggle('active', b.dataset.filter === (cur.filter || 'none'));
  }});
}}

function renderFaceLayersUI() {{
  const container = document.getElementById('faceLayersContainer');
  if (!container) return;
  container.innerHTML = '';

  state.facesOnCanvas.forEach((fLayer, idx) => {{
    const pill = document.createElement('div');
    const isAct = (idx === state.selectedFaceIdx && state.selectedAccIdx === -1 && state.selectedTextIdx === -1);
    pill.className = 'layer-pill' + (isAct ? ' active' : '');
    const faceObj = faces[fLayer.faceIndex] || {{ name: 'Murad', src: '' }};
    const cleanName = faceObj.name.replace(/[^a-zA-Z0-9 ]/g, '').trim().split(' ')[0] || ('Face #' + (idx+1));
    const thumbHtml = faceObj.src ? `<img src="${{faceObj.src}}">` : `<span>🎭</span>`;
    
    pill.innerHTML = `
      ${{thumbHtml}}
      <span>${{cleanName}}</span>
      ${{state.facesOnCanvas.length > 1 ? '<button class="pill-del-btn" title="Remove" type="button">✕</button>' : ''}}
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
      updateContextBar();
      draw();
    }};

    container.appendChild(pill);
  }});
  updateContextBar();
}}

function deleteFaceLayer(idx) {{
  if (state.facesOnCanvas.length <= 1) return;
  state.facesOnCanvas.splice(idx, 1);
  if (state.selectedFaceIdx >= state.facesOnCanvas.length) {{
    state.selectedFaceIdx = state.facesOnCanvas.length - 1;
  }}
  syncControlsToSelectedFace();
  renderFaceLayersUI();
  updateContextBar();
  draw();
}}

function syncControlsToSelectedAcc() {{
  const box = document.getElementById('accControlsBox');
  const prompt = document.getElementById('noAccPrompt');
  const cur = getSelectedAcc();

  if (!cur || !box) {{
    if (box) box.style.display = 'none';
    if (prompt) prompt.style.display = 'block';
    return;
  }}
  box.style.display = 'flex';
  if (prompt) prompt.style.display = 'none';

  const title = document.getElementById('selectedAccTitle');
  if (title) title.innerText = cur.name || 'Sticker';

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
    pill.className = 'layer-pill' + (isAct ? ' active' : '');
    const imgEl = acc.img && acc.img.src ? `<img src="${{acc.img.src}}">` : `<span>🎀</span>`;
    pill.innerHTML = `
      ${{imgEl}}
      <span style="overflow:hidden; text-overflow:ellipsis; max-width:80px;">${{acc.name || ('Sticker #' + (idx+1))}}</span>
      <button class="pill-del-btn" title="Remove" type="button">✕</button>
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
      updateContextBar();
      draw();
    }};

    container.appendChild(pill);
  }});
  syncControlsToSelectedAcc();
  updateContextBar();
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
  updateContextBar();
  draw();
}}

function syncControlsToSelectedText() {{
  const box = document.getElementById('textControlsBox');
  const prompt = document.getElementById('noTextPrompt');
  const cur = getSelectedText();

  if (!cur || !box) {{
    if (box) box.style.display = 'none';
    if (prompt) prompt.style.display = 'block';
    return;
  }}
  box.style.display = 'flex';
  if (prompt) prompt.style.display = 'none';

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
    pill.className = 'layer-pill' + (isAct ? ' active' : '');
    const displayText = txt.text || ('Text #' + (idx+1));
    pill.innerHTML = `
      <span>💬</span>
      <span style="overflow:hidden; text-overflow:ellipsis; max-width:85px;">${{displayText}}</span>
      <button class="pill-del-btn" title="Remove" type="button">✕</button>
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
      updateContextBar();
      draw();
    }};

    container.appendChild(pill);
  }});
  syncControlsToSelectedText();
  updateContextBar();
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
  updateContextBar();
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
  updateContextBar();
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
        updateContextBar();
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
  updateContextBar();

  // Rail Tab Switching
  document.querySelectorAll('.rail-tab').forEach(tabBtn => {{
    tabBtn.onclick = () => {{
      document.querySelectorAll('.rail-tab').forEach(b => b.classList.remove('active'));
      document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      tabBtn.classList.add('active');
      const targetPane = document.getElementById('pane-' + tabBtn.dataset.tab);
      if (targetPane) targetPane.classList.add('active');
    }};
  }});

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
      updateContextBar();
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

  // Canvas Format
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
            updateContextBar();
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
            updateContextBar();
            draw();
          }};
          img.src = evt.target.result;
        }};
        reader.readAsDataURL(file);
      }}
    }};
  }}

  // Sticker Controls
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

  // Movable Text Buttons & Controls
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
      updateContextBar();
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

  // Context Bar Quick Tools
  document.getElementById('quickZoomIn').onclick = () => {{
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
    draw();
  }};

  document.getElementById('quickZoomOut').onclick = () => {{
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
    draw();
  }};

  document.getElementById('quickRotLeft').onclick = () => {{
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
    draw();
  }};

  document.getElementById('quickRotRight').onclick = () => {{
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
    draw();
  }};

  document.getElementById('quickFlipH').onclick = () => {{
    if (state.selectedAccIdx >= 0 && state.accessoriesOnCanvas[state.selectedAccIdx]) {{
      const cur = state.accessoriesOnCanvas[state.selectedAccIdx];
      cur.flipH = !cur.flipH;
      syncControlsToSelectedAcc();
      draw();
      return;
    }}
    const cur = getSelectedFace();
    if (!cur) return;
    cur.flipH = !cur.flipH;
    draw();
  }};

  document.getElementById('quickCenter').onclick = () => {{
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

  document.getElementById('quickDelete').onclick = () => {{
    if (state.selectedTextIdx >= 0) {{
      deleteText(state.selectedTextIdx);
      return;
    }}
    if (state.selectedAccIdx >= 0) {{
      deleteAcc(state.selectedAccIdx);
      return;
    }}
    if (state.selectedFaceIdx >= 0 && state.facesOnCanvas.length > 1) {{
      deleteFaceLayer(state.selectedFaceIdx);
    }}
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
    draw();
  }}, {{ passive: false }});

  document.querySelectorAll('#animGrid .anim-card').forEach(btn => {{
    btn.onclick = () => {{
      document.querySelectorAll('#animGrid .anim-card').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.anim = btn.dataset.anim;
      state.frame = 0;
      state.totalFrames = state.anim === 'none' ? 1 : (state.anim === 'petpet' ? 8 : (state.anim === 'disco' ? 16 : 12));
      state.fps = state.anim === 'petpet' ? 14 : 12;
      draw();
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

    // 1. Check text first
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
      updateContextBar();
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
      updateContextBar();
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
      updateContextBar();
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
      // Full Frame (Natural aspect ratio)
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

# --- TOP ADMIN PANEL (TOP RIGHT) ---
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
                        with c_img:
                            face_p = ASSETS_DIR / item.get("file", "")
                            if face_p.exists():
                                st.image(str(face_p), width=45)
                            else:
                                st.write("🖼️")
                        with c_name:
                            st.markdown(f"**{item.get('name', 'Face')}**")
                            st.caption(f"`{item.get('file', '')}`")
                        with c_action:
                            if st.button("🗑️ Remove", key=f"del_face_{idx}_{item.get('id', '')}"):
                                current_manifest.pop(idx)
                                manifest_bytes = json.dumps(current_manifest, indent=2).encode("utf-8")
                                with open(MANIFEST_FILE, "wb") as f:
                                    f.write(manifest_bytes)

                                # If image not referenced by any other entry, remove file
                                other_refs = [x for x in current_manifest if x.get("file") == item.get("file")]
                                if not other_refs:
                                    img_to_del = ASSETS_DIR / item.get("file", "")
                                    if img_to_del.exists():
                                        img_to_del.unlink()

                                if gh_token:
                                    with st.spinner("Deleting face from GitHub repository..."):
                                        if not other_refs:
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

# Embed the interactive Canva-style studio HTML5 component
components.html(html_app, height=920, scrolling=True)
