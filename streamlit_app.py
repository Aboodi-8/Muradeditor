import os
import hashlib
import hmac
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
        if ext == "gif":
            mime = "image/gif"
        elif ext == "png":
            mime = "image/png"
        elif ext == "webp":
            mime = "image/webp"
        else:
            mime = "image/jpeg"
        return f"data:{mime};base64,{encoded}"

# Helper: load faces dynamically from storage repo with self-healing auto-discovery
def load_faces_catalog():
    faces_list = []

    # 1. Private GitHub Storage Repository via Streamlit Secrets
    try:
        if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets and "PRIVATE_FACES_REPO" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            repo_name = st.secrets["PRIVATE_FACES_REPO"]
            user_folder = st.secrets.get("PRIVATE_FACES_FOLDER", "Faces")

            for folder_candidate in [user_folder, user_folder.capitalize(), user_folder.lower(), "Faces", "faces"]:
                folder_api_url = f"https://api.github.com/repos/{repo_name}/contents/{folder_candidate}"
                folder_files = []
                try:
                    f_req = urllib.request.Request(folder_api_url, headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Frutisator-App"
                    })
                    with urllib.request.urlopen(f_req, timeout=6) as f_resp:
                        folder_files = json.loads(f_resp.read().decode("utf-8"))
                except Exception:
                    continue

                if not isinstance(folder_files, list) or len(folder_files) == 0:
                    continue

                # Load manifest.json if exists
                manifest_items = []
                manifest_sha = None
                m_url = f"https://api.github.com/repos/{repo_name}/contents/{folder_candidate}/manifest.json"
                try:
                    m_req = urllib.request.Request(m_url, headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Frutisator-App"
                    })
                    with urllib.request.urlopen(m_req, timeout=5) as m_resp:
                        m_data = json.loads(m_resp.read().decode("utf-8"))
                        manifest_sha = m_data.get("sha")
                        m_content = base64.b64decode(m_data["content"].replace("\n", "")).decode("utf-8")
                        manifest_items = json.loads(m_content)
                except Exception:
                    manifest_items = []

                # Load base64 data for all items with strict deduplication
                seen_files = set()
                seen_ids = set()
                for item in manifest_items:
                    fname = item.get("file") or item.get("filename")
                    if not fname:
                        continue
                    fname_lower = fname.lower()
                    item_id = item.get("id") or Path(fname).stem
                    item_id_lower = item_id.lower() if item_id else ""
                    if fname_lower in seen_files or (item_id_lower and item_id_lower in seen_ids):
                        continue
                    seen_files.add(fname_lower)
                    if item_id_lower:
                        seen_ids.add(item_id_lower)

                    file_url = f"https://api.github.com/repos/{repo_name}/contents/{folder_candidate}/{fname}"
                    try:
                        f_req = urllib.request.Request(
                            file_url,
                            headers={
                                "Authorization": f"Bearer {token}",
                                "Accept": "application/vnd.github.v3.raw",
                                "User-Agent": "Frutisator-App"
                            }
                        )
                        with urllib.request.urlopen(f_req, timeout=5) as f_resp:
                            b64 = base64.b64encode(f_resp.read()).decode("utf-8")
                            mime = "image/gif" if fname.lower().endswith(".gif") else ("image/webp" if fname.lower().endswith(".webp") else ("image/png" if fname.lower().endswith(".png") else "image/jpeg"))
                            item_name = item.get("name") or item.get("label") or (Path(fname).stem.replace("_", " ").title() + " 🍉")
                            faces_list.append({
                                "id": item.get("id", Path(fname).stem),
                                "name": item_name,
                                "file": fname,
                                "src": f"data:{mime};base64,{b64}"
                            })
                    except Exception:
                        pass
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
    tpl_list = []

    # 1. Load from private storage repo Templates/manifest.json via Streamlit secrets with self-healing
    try:
        if hasattr(st, "secrets") and "GITHUB_TOKEN" in st.secrets and "PRIVATE_FACES_REPO" in st.secrets:
            token = st.secrets["GITHUB_TOKEN"]
            repo_name = st.secrets["PRIVATE_FACES_REPO"]
            for tpl_folder in ["Templates", "templates"]:
                folder_api_url = f"https://api.github.com/repos/{repo_name}/contents/{tpl_folder}"
                folder_files = []
                try:
                    f_req = urllib.request.Request(folder_api_url, headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/vnd.github.v3+json",
                        "User-Agent": "Frutisator-App"
                    })
                    with urllib.request.urlopen(f_req, timeout=6) as f_resp:
                        folder_files = json.loads(f_resp.read().decode("utf-8"))
                except Exception:
                    continue

                if not isinstance(folder_files, list) or len(folder_files) == 0:
                    continue

                manifest_items = []
                manifest_sha = None
                m_url = f"https://api.github.com/repos/{repo_name}/contents/{tpl_folder}/manifest.json"
                try:
                    m_req = urllib.request.Request(
                        m_url,
                        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3+json", "User-Agent": "Frutisator-App"}
                    )
                    with urllib.request.urlopen(m_req, timeout=5) as m_resp:
                        m_data = json.loads(m_resp.read().decode("utf-8"))
                        manifest_sha = m_data.get("sha")
                        m_content = base64.b64decode(m_data["content"].replace("\n", "")).decode("utf-8")
                        manifest_items = json.loads(m_content)
                except Exception:
                    manifest_items = []

                for item in manifest_items:
                    fname = item.get("file") or item.get("filename")
                    if not fname:
                        continue
                    file_url = f"https://api.github.com/repos/{repo_name}/contents/{tpl_folder}/{fname}"
                    try:
                        f_req = urllib.request.Request(
                            file_url,
                            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github.v3.raw", "User-Agent": "Frutisator-App"}
                        )
                        with urllib.request.urlopen(f_req, timeout=5) as f_resp:
                            b64 = base64.b64encode(f_resp.read()).decode("utf-8")
                            mime = "image/gif" if fname.lower().endswith(".gif") else ("image/webp" if fname.lower().endswith(".webp") else ("image/png" if fname.lower().endswith(".png") else "image/jpeg"))
                            item_name = item.get("name") or item.get("label") or Path(fname).stem.replace("_", " ").title()
                            tpl_list.append({
                                "id": item.get("id") or ("tpl_" + Path(fname).stem),
                                "name": item_name,
                                "file": fname,
                                "src": f"data:{mime};base64,{b64}"
                            })
                    except Exception:
                        pass
                if tpl_list:
                    return tpl_list
    except Exception:
        pass

    # 2. Local fallback
    tpl_defs = [
        {"id": "suit", "name": "🤵 Fancy Tux", "file": "tux.jpg"},
        {"id": "gigachad", "name": "🗿 Gigachad", "file": "gigachad.webp"},
        {"id": "throne", "name": "👑 King Throne", "file": "king_throne.jpg"},
        {"id": "astronaut", "name": "🚀 Space", "file": "space.jpg"},
    ]
    for t in tpl_defs:
        img_p = TEMPLATES_DIR / t["file"]
        if img_p.exists():
            tpl_list.append({
                "id": t["id"],
                "name": t["name"],
                "file": t["file"],
                "src": get_base64_data_uri(img_p)
            })

    # Strict deduplication by ID and file
    seen_tpl_keys = set()
    unique_tpls = []
    for t in tpl_list:
        tid = (t.get("id") or "").lower().strip()
        tfile = (t.get("file") or "").lower().strip()
        key = tid or tfile
        if key and key not in seen_tpl_keys:
            seen_tpl_keys.add(key)
            unique_tpls.append(t)
    return unique_tpls

# Load GIF libraries
gifshot_path = ASSETS_DIR / "gifshot.min.js"
gifshot_script = ""
if gifshot_path.exists():
    with open(gifshot_path, "r", encoding="utf-8") as f:
        gifshot_script = f.read()

gifuct_path = ASSETS_DIR / "gifuct-js.min.js"
if not gifuct_path.exists():
    gifuct_path = ASSETS_DIR / "gifuct-js.js"
gifuct_script = ""
if gifuct_path.exists():
    with open(gifuct_path, "r", encoding="utf-8") as f:
        gifuct_script = f.read()

def encrypt_vault_payload(data_obj, passwords):
    plaintext = json.dumps(data_obj).encode("utf-8")
    salt = os.urandom(16)
    master_key = os.urandom(32)

    has_crypto = False
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        has_crypto = True
    except Exception:
        has_crypto = False

    norm_passwords = []
    seen = set()
    for p in passwords:
        if p and isinstance(p, str):
            clean_p = p.strip()
            if clean_p and clean_p not in seen:
                seen.add(clean_p)
                norm_passwords.append(clean_p)

    if has_crypto:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        slots = []
        for p in norm_passwords:
            dk = hashlib.pbkdf2_hmac("sha256", p.encode("utf-8"), salt, 10000, 32)
            s_nonce = os.urandom(12)
            s_ct = AESGCM(dk).encrypt(s_nonce, master_key, None)
            slots.append({
                "nonce": base64.b64encode(s_nonce).decode("utf-8"),
                "ct": base64.b64encode(s_ct).decode("utf-8")
            })
        p_nonce = os.urandom(12)
        p_ct = AESGCM(master_key).encrypt(p_nonce, plaintext, None)
        return {
            "algo": "AES-GCM",
            "salt": base64.b64encode(salt).decode("utf-8"),
            "slots": slots,
            "nonce": base64.b64encode(p_nonce).decode("utf-8"),
            "ct": base64.b64encode(p_ct).decode("utf-8")
        }
    else:
        slots = []
        for p in norm_passwords:
            dk = hashlib.pbkdf2_hmac("sha256", p.encode("utf-8"), salt, 10000, 32)
            s_nonce = os.urandom(16)
            mask_input = dk + s_nonce
            mask = hashlib.sha256(mask_input).digest()
            s_ct = bytes(a ^ b for a, b in zip(master_key, mask))
            tag = hmac.new(dk, s_nonce + s_ct, "sha256").digest()
            slots.append({
                "nonce": base64.b64encode(s_nonce).decode("utf-8"),
                "ct": base64.b64encode(s_ct).decode("utf-8"),
                "tag": base64.b64encode(tag).decode("utf-8")
            })
        p_nonce = os.urandom(16)
        num_blocks = (len(plaintext) + 31) // 32
        keystream = bytearray()
        for i in range(num_blocks):
            keystream.extend(hashlib.sha256(master_key + p_nonce + i.to_bytes(4, "big")).digest())
        p_ct = bytes(a ^ b for a, b in zip(plaintext, keystream[:len(plaintext)]))
        tag = hmac.new(master_key, p_nonce + p_ct, "sha256").digest()
        return {
            "algo": "SHA256-CTR",
            "salt": base64.b64encode(salt).decode("utf-8"),
            "slots": slots,
            "nonce": base64.b64encode(p_nonce).decode("utf-8"),
            "ct": base64.b64encode(p_ct).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8")
        }

faces_data = load_faces_catalog()

templates_data = load_templates_catalog()
templates_json = json.dumps(templates_data)

token_secret = ""
try:
    token_secret = st.secrets.get("GITHUB_TOKEN", "")
except Exception:
    pass

private_repo_secret = ""
try:
    private_repo_secret = st.secrets.get("PRIVATE_FACES_REPO", "")
except Exception:
    pass

private_folder_secret = "Faces" if private_repo_secret else "assets"

expected_pwd = ""
try:
    expected_pwd = st.secrets.get("ADMIN_PASSWORD", "")
except Exception:
    pass
if not expected_pwd:
    expected_pwd = "MuradAdmin"

vault_pwd_secret = ""
try:
    vault_pwd_secret = st.secrets.get("CATALOG_PASSWORD", st.secrets.get("VAULT_PASSWORD", "fruit"))
except Exception:
    vault_pwd_secret = "fruit"
if not vault_pwd_secret:
    vault_pwd_secret = "fruit"

valid_vault_passwords = [vault_pwd_secret, expected_pwd, "fruit", "fruits"]
encrypted_vault_pkg = encrypt_vault_payload(faces_data, valid_vault_passwords)
encrypted_vault_json = json.dumps(encrypted_vault_pkg)

gh_token_json = json.dumps(token_secret)
gh_repo_json = json.dumps(private_repo_secret)
gh_folder_json = json.dumps(private_folder_secret)
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

  
  /* 1x1 TEXT COLOR SWATCH BOXES */
  .color-swatch-box {{
    width: 26px;
    height: 26px;
    min-width: 26px;
    min-height: 26px;
    aspect-ratio: 1 / 1;
    border-radius: 6px;
    border: 2px solid #282c3c;
    cursor: pointer;
    padding: 0;
    outline: none;
    transition: transform 0.12s ease, border-color 0.12s ease, box-shadow 0.12s ease;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.5);
    display: inline-block;
    box-sizing: border-box;
  }}
  .color-swatch-box:hover {{
    transform: scale(1.18);
    border-color: #ffffff;
    z-index: 2;
  }}
  .color-swatch-box.active {{
    border-color: #ffffff !important;
    box-shadow: 0 0 0 2px var(--ps-blue), 0 2px 8px rgba(0, 132, 255, 0.5) !important;
    transform: scale(1.1);
  }}

  
  /* BOTTOM TIPS & STATUS BAR */
  .ps-statusbar {{
    height: 24px;
    min-height: 24px;
    background: #090a0e;
    border-top: 1px solid #1a1c26;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 14px;
    font-size: 11px;
    color: #7b8092;
    z-index: 50;
    flex-shrink: 0;
    user-select: none;
    box-sizing: border-box;
  }}
  .statusbar-tips {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .statusbar-tips #txtShiftTip {{
    color: #60c5ff;
    font-weight: 600;
    letter-spacing: 0.2px;
  }}
  .statusbar-shortcuts {{
    display: flex;
    align-items: center;
    gap: 8px;
    color: #5d6275;
    font-size: 10.5px;
  }}
  .statusbar-shortcuts kbd {{
    background: #151722;
    border: 1px solid #282c3c;
    border-radius: 3px;
    padding: 1px 4px;
    font-family: inherit;
    font-size: 10px;
    color: #9da3ba;
  }}
  .statusbar-sep {{
    opacity: 0.35;
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

  .export-filename-wrap {{
    display: inline-flex;
    align-items: center;
    background: rgba(0, 0, 0, 0.45);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 6px;
    padding: 4px 8px;
    gap: 5px;
    transition: all 0.2s ease;
  }}
  .export-filename-wrap:focus-within {{
    border-color: var(--ps-blue);
    box-shadow: 0 0 8px rgba(0, 132, 255, 0.35);
  }}
  .export-file-icon {{
    font-size: 13px;
    user-select: none;
    line-height: 1;
  }}
  .export-filename-input {{
    background: transparent;
    border: none;
    outline: none;
    color: #4df0a0;
    font-family: 'Inter', -apple-system, sans-serif;
    font-size: 12px;
    font-weight: 700;
    width: 135px;
    min-width: 95px;
    max-width: 165px;
    text-overflow: ellipsis;
  }}
  .export-filename-input::placeholder {{
    color: rgba(255, 255, 255, 0.35);
  }}
  .export-file-ext {{
    font-size: 11px;
    font-weight: 800;
    color: var(--ps-text-muted);
    user-select: none;
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
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid #2b2f42;
    border-radius: 5px;
    color: #a0a6be;
    cursor: pointer;
    padding: 3px 8px;
    font-size: 11px;
    font-weight: 700;
    gap: 5px;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }}
  .admin-lock-btn:hover {{
    background: rgba(0, 132, 255, 0.16);
    border-color: var(--ps-blue);
    color: #fff;
    transform: translateY(-1px);
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
  
  #filterPresetsGrid {{
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr)) !important;
    gap: 3px !important;
    width: 100% !important;
    box-sizing: border-box !important;
  }}
  #filterPresetsGrid .ps-opt-btn {{
    min-width: 0 !important;
    max-width: 100% !important;
    padding: 5px 1px !important;
    font-size: 10px !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
    justify-content: center !important;
    text-align: center !important;
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

  /* DISCORD ANIMATION DROPDOWN */
  .anim-select-container {{
    position: relative;
    width: 100%;
  }}
  .anim-dropdown {{
    width: 100%;
    background-color: var(--ps-card);
    border: 1px solid var(--ps-border);
    border-radius: 7px;
    color: #f1f3f7;
    font-size: 13px;
    font-weight: 600;
    padding: 9px 34px 9px 12px;
    outline: none;
    cursor: pointer;
    transition: all 0.18s ease;
    appearance: none;
    -webkit-appearance: none;
    -moz-appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='14' height='14' viewBox='0 0 24 24' fill='none' stroke='%238a94a6' stroke-width='2.5' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    background-size: 14px;
    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.25);
  }}
  .anim-dropdown:hover {{
    background-color: var(--ps-card-hover);
    border-color: var(--ps-border-light);
  }}
  .anim-dropdown:focus {{
    border-color: var(--ps-blue);
    box-shadow: 0 0 0 2px rgba(0, 132, 255, 0.35);
  }}
  .anim-dropdown option {{
    background: #181b22;
    color: #f1f3f7;
    padding: 8px 10px;
    font-size: 13px;
  }}
  .anim-badge {{
    font-size: 10px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 12px;
    background: rgba(0, 132, 255, 0.15);
    color: #60a5fa;
    border: 1px solid rgba(0, 132, 255, 0.3);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }}
  .lang-ar .anim-dropdown {{
    padding: 9px 12px 9px 34px;
    background-position: left 12px center;
    direction: rtl;
    text-align: right;
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
    width: 460px;
    max-width: 94vw;
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

  /* SPINNER & LIVE SYNCING INDICATORS */
  @keyframes ps-spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
  }}
  .ps-spinner {{
    display: inline-block;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.2);
    border-top-color: #3b82f6;
    border-radius: 50%;
    animation: ps-spin 0.75s linear infinite;
    vertical-align: middle;
    flex-shrink: 0;
  }}
  .ps-spinner.danger, .ps-spinner-danger {{
    border-top-color: #ef4444 !important;
  }}
  .ps-spinner.success, .ps-spinner-success {{
    border-top-color: #10b981 !important;
  }}
  .ps-spinner-lg {{
    width: 22px;
    height: 22px;
    border-width: 2.5px;
  }}
  .card-syncing-overlay {{
    position: absolute;
    inset: 0;
    background: rgba(11, 12, 16, 0.88);
    backdrop-filter: blur(5px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 6px;
    border-radius: inherit;
    z-index: 25;
    pointer-events: none;
    animation: fadeIn 0.15s ease-out;
  }}
  .card-syncing-text {{
    font-size: 10.5px;
    font-weight: 700;
    color: #93c5fd;
    text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    text-align: center;
    padding: 0 4px;
  }}
  .item-syncing-row {{
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(59, 130, 246, 0.08);
    border: 1px dashed rgba(59, 130, 246, 0.4);
    padding: 7px 10px;
    border-radius: 6px;
    font-size: 12px;
    color: #93c5fd;
  }}
  .cloud-sync-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    padding: 3px 8px;
    border-radius: 4px;
    background: #111217;
    border: 1px solid #1f2028;
    color: var(--ps-text-muted);
  }}
  .cloud-sync-pill.syncing {{
    color: #93c5fd;
    border-color: rgba(59, 130, 246, 0.4);
    background: rgba(59, 130, 246, 0.08);
  }}
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
<script src="https://cdn.jsdelivr.net/npm/gifshot@0.4.5/build/gifshot.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/gifuct-js@2.1.2/dist/gifuct-js.min.js"></script>
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
      <button id="btnResetCanvas" class="ps-opt-btn" title="Reset Canvas (Clear all layers and refresh canvas)">🔄 Reset Canvas</button>
      <button id="btnSyncCloud" class="ps-opt-btn" title="Live Sync with Cloud Storage (Instantly fetch new faces &amp; templates)"><span class="ps-spinner" id="cloudSyncSpinner" style="display:none; width:12px; height:12px; margin-right:4px;"></span><span id="cloudSyncLabel">☁️ Sync</span></button>
      <span class="ps-opt-label" id="lblTransform">Transform:</span>
      <span class="ps-opt-badge" id="optLayerName">No layer selected</span>
      <div class="ps-opt-group" id="optActionGroup" style="display:none;">
        <span class="ps-opt-label" id="optScaleVal">100%</span>
        <span class="ps-opt-label" id="optRotVal">0°</span>
        <button id="optFlipBtn" class="ps-opt-btn" title="Flip Horizontal">↔️ Flip</button>
        <button id="optCenterBtn" class="ps-opt-btn" title="Center on Canvas">🎯 Center</button>
        <button id="optDeleteBtn" class="ps-opt-btn danger" title="Delete Layer">🗑️ Delete</button>
      </div>
      
    </div>

    <!-- EXPORT ACTIONS + ARABIC LANGUAGE SWITCHER -->
    <div class="ps-actions">
      <div class="export-filename-wrap" title="Dynamic export file name (click to edit)">
        <span class="export-file-icon">🏷️</span>
        <input type="text" id="exportFileNameInput" class="export-filename-input" placeholder="frutisator-meme" value="frutisator-meme">
        <span class="export-file-ext">.gif</span>
      </div>
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
          <button id="adminTplLockBtn" class="admin-lock-btn" title="Admin Templates Settings">⚙️ <span class="txtAdminLabel">Admin</span></button>
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

        <!-- 1. DEFAULT FRUITS TEMPLATES (MOVED TO TOP) -->
        <div style="display:flex; flex-direction:column; gap:5px;">
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span class="section-label" id="lblPopularTemplates">Default Fruits Templates:</span>
            <button id="btnSyncTemplatesQuick" class="ps-opt-btn" style="padding:2px 7px; font-size:11px;" title="Sync Templates from Cloud">🔄</button>
          </div>
          <div class="grid-cards-faces" id="bgPresetsRow" style="max-height:160px; overflow-y:auto;"></div>
        </div>

        <!-- 2. CANVAS FORMAT BUTTONS (MOVED TO BOTTOM) -->
        <div style="display:flex; flex-direction:column; gap:5px; margin-top:3px;">
          <span class="section-label" id="lblCanvasFormat">Canvas Format:</span>
          <div class="btn-group-grid btn-group-4" id="canvasSizeGroup">
            <button class="btn-toggle active" data-size="true_size" id="btnTrueSize">📐 True Size</button>
            <button class="btn-toggle" data-size="square">⏹️ 1:1</button>
            <button class="btn-toggle" data-size="landscape">🖼️ 16:9</button>
            <button class="btn-toggle" data-size="portrait">📱 9:16</button>
          </div>
        </div>
      </div>

      <!-- 2. SECTION: FRUITS FACES -->
      <div class="ps-panel-section" id="section-faces">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleFaces">🍉 Fruits Faces</span>
          <!-- DISCRETE CORNER ADMIN LOCK BUTTON -->
          <button id="adminLockBtn" class="admin-lock-btn" title="Admin Fruits Catalog Settings">⚙️ <span class="txtAdminLabel">Admin</span></button>
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
          <div style="display:flex; gap:6px; align-items:center;">
            <button id="lockVaultBtn" class="ps-opt-btn" style="padding:3px 7px; font-size:12px; display:none;" title="Exit Vault">🚪</button>
            <button id="btnSyncFacesQuick" class="ps-opt-btn" style="padding:3px 7px; font-size:11px;" title="Sync Faces from Cloud">🔄</button>
            <button id="addFaceBtn" class="ps-opt-btn" style="background:var(--ps-blue); border-color:var(--ps-blue); color:#fff; padding:4px 10px;">➕ Add Face</button>
          </div>
        </div>

        <!-- VAULT CONTAINER WITH BLUR GATE -->
        <div id="facesVaultWrapper" style="position:relative; min-height:85px; max-height:240px; border-radius:6px; overflow:hidden;">
          <div class="grid-cards-faces" id="facesGrid" style="max-height:240px; overflow-y:auto; filter:blur(7px); opacity:0.25; pointer-events:none; transition:filter 0.3s, opacity 0.3s;"></div>

          <!-- VAULT GATE OVERLAY -->
          <div id="vaultGateOverlay" style="position:absolute; inset:0; background:rgba(11,12,16,0.88); backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px); display:flex; flex-direction:column; align-items:center; justify-content:center; padding:12px; gap:8px; border-radius:6px; border:1px solid var(--ps-border); z-index:10;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="font-size:16px;">🔐</span>
              <span style="font-size:12px; font-weight:800; color:#fff;" id="lblVaultTitle">Private Faces Vault</span>
            </div>
            <div style="display:flex; gap:5px; width:100%; max-width:240px;">
              <input type="password" id="vaultPwdInput" class="ps-input" style="flex:1; padding:6px 9px; font-size:12px;" placeholder="Password / كلمة المرور...">
              <button id="btnUnlockVault" class="ps-opt-btn" style="background:var(--ps-blue); border-color:var(--ps-blue); color:#fff; padding:6px 12px; font-size:11.5px; font-weight:800;">🔓 Unlock</button>
            </div>
            <div id="vaultErrorNotice" style="display:none; color:var(--ps-red); font-size:11px; font-weight:700;">Incorrect word / كلمة مرور غير صحيحة</div>
          </div>
        </div>

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

        <!-- CURRENT SELECTED LAYER TARGET BADGE -->
        <div id="filterActiveTargetBadge" style="display:flex; align-items:center; justify-content:space-between; background:var(--ps-card); border:1px solid var(--ps-border); border-radius:6px; padding:6px 10px; font-size:11.5px; font-weight:700; color:#fff;">
          <span id="lblFilterTargetText">Selected Layer:</span>
          <span id="valFilterTargetName" style="color:var(--ps-blue); font-weight:800;">🖼️ Backdrop</span>
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

          <!-- 1x1 COLOR SWATCH BOXES WITH EMBEDDED COLOR PICKER -->
          <div style="display:flex; flex-direction:column; gap:5px;">
            <span class="section-label" id="lblTextColor">Text Color:</span>
            <div class="color-swatches-row" id="textColorGroup" style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin-top:2px;">
              <button class="color-swatch-box active" data-color="#ffffff" title="White" style="background:#ffffff; border:2px solid #555;"></button>
              <button class="color-swatch-box" data-color="#facc15" title="Yellow" style="background:#facc15;"></button>
              <button class="color-swatch-box" data-color="#ef4444" title="Red" style="background:#ef4444;"></button>
              <button class="color-swatch-box" data-color="#22d3ee" title="Cyan" style="background:#22d3ee;"></button>
              <button class="color-swatch-box" data-color="#4ade80" title="Green" style="background:#4ade80;"></button>
              <button class="color-swatch-box" data-color="#a855f7" title="Purple" style="background:#a855f7;"></button>
              <button class="color-swatch-box" data-color="#000000" title="Black" style="background:#000000; border:2px solid #444;"></button>
              <div class="color-swatch-box color-wheel-wrapper" id="colorWheelBtn" data-color="wheel" title="Choose Custom Color" style="position:relative; background:conic-gradient(from 0deg, red, yellow, lime, aqua, blue, magenta, red); display:flex; align-items:center; justify-content:center; overflow:hidden; cursor:pointer;">
                <input type="color" id="nativeColorPicker" value="#ffffff" style="position:absolute; top:0; left:0; width:100%; height:100%; opacity:0; cursor:pointer; padding:0; border:none; margin:0; z-index:5;">
              </div>
            </div>
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

      <!-- 5. SECTION: DISCORD GIF EFFECTS DROPDOWN -->
      <div class="ps-panel-section" id="section-anim">
        <div class="panel-section-header">
          <span class="panel-section-title" id="secTitleAnim">✨ Discord GIF Effects</span>
          <span class="anim-badge" id="animActiveBadge">Still</span>
        </div>

        <div class="anim-select-container">
          <select id="animEffectSelect" class="ps-select anim-dropdown">
            <option value="none">🖼️ Still (No Animation)</option>
            <option value="bob">🕺 Bob Up &amp; Down</option>
            <option value="bounce">🏀 Energetic Bounce</option>
            <option value="shake">💢 Shake</option>
            <option value="earthquake">🌋 Severe Earthquake</option>
            <option value="petpet">👋 Petpet Squish</option>
            <option value="jelly">🍮 Jelly Wobble</option>
            <option value="spin">🌀 Spin 360°</option>
            <option value="spin_fast">⚡ Hyper Spin</option>
            <option value="disco">🪩 Disco Dance</option>
            <option value="headbang">🎸 Headbang (Metal)</option>
            <option value="wobble">🌊 Side Wobble</option>
            <option value="swing">🕰️ Pendulum Swing</option>
            <option value="float">🛸 Dreamy Hover</option>
            <option value="orbit">🪐 3D Orbit</option>
            <option value="heart">💓 Heartbeat</option>
            <option value="zoom">💥 Pulse &amp; Zoom</option>
            <option value="breathe">🫁 Slow Breathing</option>
            <option value="roll">🛞 Barrel Roll</option>
            <option value="dizzy">🥴 Drunk &amp; Dizzy</option>
            <option value="peekaboo">🙈 Peek-a-boo</option>
            <option value="jitter">⚡ Glitch Jitter</option>
            <option value="chaos">🤯 Hyper Chaos</option>
          </select>
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

    <!-- BOTTOM TIPS & STATUS BAR -->
  <footer class="ps-statusbar" id="psStatusBar">
    <div class="statusbar-tips">
      <span id="txtShiftTip">💡 Hold Shift while dragging corners to Stretch!</span>
    </div>
    <div class="statusbar-shortcuts">
      <span>⌨️ <kbd>Del</kbd> / <kbd>Backspace</kbd>: Remove Layer</span>
      <span class="statusbar-sep">•</span>
      <span>⌨️ <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>A</kbd>: Admin</span>
    </div>
  </footer>

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

      <!-- STEP 2: CATALOG MANAGEMENT (FACES & TEMPLATES) -->
      <div class="admin-modal-body" id="adminManageBody" style="display:none;">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <span style="color:var(--ps-green); font-weight:800; font-size:12px;">✅ Admin Access Granted</span>
          <button id="adminLockOutBtn" class="ps-opt-btn" style="font-size:11px;">🚪 Exit Admin</button>
        </div>

        <!-- TABS: FACES vs TEMPLATES -->
        <div class="btn-group-grid btn-group-2" id="adminTabsGroup" style="margin-top:4px;">
          <button class="btn-toggle active" id="adminTabFacesBtn">🍉 Fruit Faces</button>
          <button class="btn-toggle" id="adminTabTemplatesBtn">🖼️ Templates & Backdrops</button>
        </div>

        <!-- TAB 1: FACES MANAGEMENT -->
        <div id="adminTabFacesPanel" style="display:flex; flex-direction:column; gap:10px;">
          <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
            <span style="font-size:12px; font-weight:800; color:#fff;">➕ ADD NEW FRUIT FACE TO CATALOG:</span>
            <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
              <input type="text" id="adminNewFaceName" class="ps-input" placeholder="Fruit Name & Emoji (e.g. Watermelon 🍉)">
              <input type="file" id="adminNewFaceFile" accept="image/*,.gif" class="ps-input" style="padding:6px;">
              <button id="adminUploadBtn" class="ps-btn ps-btn-primary" style="justify-content:center; gap:8px;">
                <svg class="upload-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <span>Push to Faces Catalog</span>
              </button>
              <div id="adminUploadStatus" style="font-size:11.5px; text-align:center;"></div>
            </div>
          </div>

          <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
            <span style="font-size:12px; font-weight:800; color:#fff;">🗑️ MANAGE DEFAULT FRUITS:</span>
            <div id="adminFacesCatalogStatus" style="font-size:11.5px; margin-top:4px; margin-bottom:4px; min-height:16px; font-weight:600; text-align:center;"></div>
            <div id="adminFacesCatalogList" style="display:flex; flex-direction:column; gap:5px; max-height:250px; overflow-y:auto; margin-top:6px;"></div>
          </div>
        </div>

        <!-- TAB 2: TEMPLATES MANAGEMENT -->
        <div id="adminTabTemplatesPanel" style="display:none; flex-direction:column; gap:10px;">
          <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
            <span style="font-size:12px; font-weight:800; color:#fff;">➕ ADD NEW TEMPLATE TO CATALOG:</span>
            <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
              <input type="text" id="adminNewTplName" class="ps-input" placeholder="Template Name & Emoji (e.g. 🏖️ Summer Beach)">
              <input type="file" id="adminNewTplFile" accept="image/*,.gif" class="ps-input" style="padding:6px;">
              <button id="adminUploadTplBtn" class="ps-btn ps-btn-primary" style="justify-content:center; gap:8px;">
                <svg class="upload-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                  <polyline points="17 8 12 3 7 8"></polyline>
                  <line x1="12" y1="3" x2="12" y2="15"></line>
                </svg>
                <span>Push to Templates Catalog</span>
              </button>
              <div id="adminUploadTplStatus" style="font-size:11.5px; text-align:center;"></div>
            </div>
          </div>

          <div style="border-top:1px solid var(--ps-border); padding-top:10px;">
            <span style="font-size:12px; font-weight:800; color:#fff;">🗑️ MANAGE DEFAULT TEMPLATES:</span>
            <div id="adminTplCatalogStatus" style="font-size:11.5px; margin-top:4px; margin-bottom:4px; min-height:16px; font-weight:600; text-align:center;"></div>
            <div id="adminTemplatesCatalogList" style="display:flex; flex-direction:column; gap:5px; max-height:250px; overflow-y:auto; margin-top:6px;"></div>
          </div>
        </div>
      </div>
    </div>
  </div>

</div>

<script>
const encryptedFacesVault = {encrypted_vault_json};
let faces = [];
let isVaultUnlocked = false;
let templates = {templates_json};
const GITHUB_TOKEN = {gh_token_json};
const GITHUB_REPO = {gh_repo_json};
const GITHUB_FOLDER = {gh_folder_json};
const EXPECTED_ADMIN_PWD = {admin_pwd_json};

let layerZCounter = 1;
let currentLang = 'en';

// BILINGUAL ARABIC & ENGLISH TRANSLATIONS
const i18n = {{
  en: {{
    langBtn: '🌐 العربية',
    appTitle: 'Frutisator',
    fitScreen: '🔍 Fit Screen',
    resetCanvas: '🔄 Reset Canvas',
    syncCloud: '☁️ Sync',
    lblVaultTitle: 'Private Faces Vault',
    vaultPlaceholder: 'Password / كلمة المرور...',
    btnUnlockVault: '🔓 Unlock',
    lockVaultBtn: '🚪',
    vaultError: 'Incorrect word / كلمة مرور غير صحيحة',
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
    trueSize: '📐 True Size',
    lblPopularTemplates: 'Default Fruits Templates:',

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
    txtAdminLabel: 'Admin',
    adminLockOutBtn: '🚪 Exit Admin',

    secTitleStickers: '🎀 Custom Stickers',
    txtUploadSticker: 'Upload Custom PNG / Sticker',
    lblStickerOpacity: 'Opacity:',

    secTitleAnim: '✨ Discord GIF Effects',
    animBadgeStill: 'Still',
    animNone: '🖼️ Still (No Animation)',
    animBob: '🕺 Bob Up & Down',
    animBounce: '🏀 Energetic Bounce',
    animShake: '💢 Shake',
    animEarthquake: '🌋 Severe Earthquake',
    animPetpet: '👋 Petpet Squish',
    animJelly: '🍮 Jelly Wobble',
    animSpin: '🌀 Spin 360°',
    animSpinFast: '⚡ Hyper Spin',
    animDisco: '🪩 Disco Dance',
    animHeadbang: '🎸 Headbang (Metal)',
    animWobble: '🌊 Side Wobble',
    animSwing: '🕰️ Pendulum Swing',
    animFloat: '🛸 Dreamy Hover',
    animOrbit: '🪐 3D Orbit',
    animHeart: '💓 Heartbeat',
    animZoom: '💥 Pulse & Zoom',
    animBreathe: '🫁 Slow Breathing',
    animRoll: '🛞 Barrel Roll',
    animDizzy: '🥴 Drunk & Dizzy',
    animPeekaboo: '🙈 Peek-a-boo',
    animJitter: '⚡ Glitch Jitter',
    animChaos: '🤯 Hyper Chaos',

    secTitleLayers: '📑 Active Layers',
    noLayers: 'No active layers on canvas',

    secTitleFilters: '🎨 Color & Filters',
    resetFilters: '🔄 Reset',
    lblFilterTargetText: 'Selected Layer:',
    lblFilterTarget: 'Switch Target:',
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
    resetCanvas: '🔄 إعادة تعيين',
    syncCloud: '☁️ مزامنة السحابة',
    lblVaultTitle: 'خزنة الوجوه الخاصة',
    vaultPlaceholder: 'أدخل كلمة المرور...',
    btnUnlockVault: '🔓 فتح',
    lockVaultBtn: '🚪',
    vaultError: 'كلمة المرور غير صحيحة',
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
    trueSize: '📐 الحجم الأصلي',
    lblPopularTemplates: 'قوالب الفواكه الافتراضية:',

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
    txtAdminLabel: 'المشرف',
    adminLockOutBtn: '🚪 خروج',

    secTitleStickers: '🎀 ملصقات مخصصة',
    txtUploadSticker: 'رفع ملصق PNG مخصص',
    lblStickerOpacity: 'الشفافية:',

    secTitleAnim: '✨ تأثيرات ديسكورد المتحركة',
    animBadgeStill: 'ثابت',
    animNone: '🖼️ ثابت (بدون حركة)',
    animBob: '🕺 تمايل للأعلى والأسفل',
    animBounce: '🏀 قفز ارتدادي ممتع',
    animShake: '💢 اهتزاز سريع',
    animEarthquake: '🌋 زلزال عنيف',
    animPetpet: '👋 تربيت سريع (Petpet)',
    animJelly: '🍮 تموج الجيلي المطاطي',
    animSpin: '🌀 دوران 360 درجة',
    animSpinFast: '⚡ دوران فائق السرعة',
    animDisco: '🪩 رقص ديسكو',
    animHeadbang: '🎸 هز الرأس (ميتال)',
    animWobble: '🌊 تموج جانبي',
    animSwing: '🕰️ تأرجح البندول',
    animFloat: '🛸 طفو عائم ناعم',
    animOrbit: '🪐 مدار ثلاثي الأبعاد',
    animHeart: '💓 نبض القلب',
    animZoom: '💥 نبض وتكبير متفجر',
    animBreathe: '🫁 تنفس هادئ',
    animRoll: '🛞 دحرجة برميلية',
    animDizzy: '🥴 دوخة وترنح',
    animPeekaboo: '🙈 تلصص واختفاء',
    animJitter: '⚡ تشويش وجليتش',
    animChaos: '🤯 فوضى ميم خارقة',

    secTitleLayers: '📑 الطبقات النشطة',
    noLayers: 'لا توجد طبقات نشطة على الكانفاس',

    secTitleFilters: '🎨 فلاتر وتعديل الألوان',
    resetFilters: '🔄 إعادة ضبط',
    lblFilterTargetText: 'الطبقة المحددة:',
    lblFilterTarget: 'تبديل الهدف:',
    btnFilterBg: '🖼️ الخلفية',
    btnFilterFace: '🍉 الوجه',
    btnFilterAcc: '🎀 الملصق',
    lblFilterPresets: 'فلاتر سريعة جاهزة:',
    presetNormal: 'عادي',
    presetBw: '🖤 أحادي',
    presetSepia: '📜 بني',
    presetInvert: '🔮 عكس',
    presetShift: '🌈 تدوير',
    presetVivid: '⚡ مشبع',
    presetCyber: '🌆 نيون',
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
  try {{ localStorage.setItem('frutisator_lang', lang); }} catch(e) {{}}
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
  if (document.getElementById('btnResetCanvas')) document.getElementById('btnResetCanvas').innerText = t.resetCanvas;
  if (document.getElementById('btnSyncCloud')) document.getElementById('btnSyncCloud').innerText = t.syncCloud || '☁️ Sync';
  if (document.getElementById('lblVaultTitle')) document.getElementById('lblVaultTitle').innerText = t.lblVaultTitle;
  if (document.getElementById('vaultPwdInput')) document.getElementById('vaultPwdInput').placeholder = t.vaultPlaceholder;
  if (document.getElementById('btnUnlockVault')) document.getElementById('btnUnlockVault').innerText = t.btnUnlockVault;
  if (document.getElementById('lockVaultBtn')) document.getElementById('lockVaultBtn').innerText = t.lockVaultBtn;
  if (document.getElementById('vaultErrorNotice')) document.getElementById('vaultErrorNotice').innerText = t.vaultError;
  document.getElementById('lblTransform').innerText = t.lblTransform;
  document.getElementById('txtShiftTip').innerText = t.shiftTip;
  document.getElementById('btnExportGif').innerText = t.exportGif;
  document.getElementById('btnExportPng').innerText = t.exportPng;
  document.getElementById('btnCopyDiscord').innerText = t.copyDiscord;
  document.getElementById('optFlipBtn').innerText = t.flip;
  document.getElementById('optCenterBtn').innerText = t.center;
  document.getElementById('optDeleteBtn').innerText = t.delete;

  document.querySelectorAll('.txtAdminLabel').forEach(el => el.innerText = t.txtAdminLabel || 'Admin');
  if (document.getElementById('adminLockOutBtn')) document.getElementById('adminLockOutBtn').innerText = t.adminLockOutBtn || '🚪 Exit Admin';
  document.getElementById('secTitleBackdrop').innerText = t.secTitleBackdrop;
  document.getElementById('txtUploadBg').innerText = t.txtUploadBg;
  document.getElementById('lblCanvasFormat').innerText = t.lblCanvasFormat;
  if (document.getElementById('btnTrueSize')) document.getElementById('btnTrueSize').innerText = t.btnTrueSize || t.trueSize;
  if (document.getElementById('lblPopularTemplates')) document.getElementById('lblPopularTemplates').innerText = t.lblPopularTemplates;

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
  // colorWheelBtn is a 1x1 graphic swatch with embedded native picker

  document.getElementById('secTitleStickers').innerText = t.secTitleStickers;
  document.getElementById('txtUploadSticker').innerText = t.txtUploadSticker;
  document.getElementById('lblStickerOpacity').innerText = t.lblStickerOpacity;

  document.getElementById('secTitleAnim').innerText = t.secTitleAnim;
  const animSelect = document.getElementById('animEffectSelect');
  if (animSelect) {{
    const animMap = {{
      none: t.animNone,
      bob: t.animBob,
      bounce: t.animBounce,
      shake: t.animShake,
      earthquake: t.animEarthquake,
      petpet: t.animPetpet,
      jelly: t.animJelly,
      spin: t.animSpin,
      spin_fast: t.animSpinFast,
      disco: t.animDisco,
      headbang: t.animHeadbang,
      wobble: t.animWobble,
      swing: t.animSwing,
      float: t.animFloat,
      orbit: t.animOrbit,
      heart: t.animHeart,
      zoom: t.animZoom,
      breathe: t.animBreathe,
      roll: t.animRoll,
      dizzy: t.animDizzy,
      peekaboo: t.animPeekaboo,
      jitter: t.animJitter,
      chaos: t.animChaos
    }};
    for (let i = 0; i < animSelect.options.length; i++) {{
      const opt = animSelect.options[i];
      if (animMap[opt.value]) {{
        opt.innerText = animMap[opt.value];
      }}
    }}
    const badge = document.getElementById('animActiveBadge');
    if (badge) {{
      const currentOpt = animSelect.options[animSelect.selectedIndex];
      if (currentOpt) {{
        badge.innerText = currentOpt.value === 'none' ? t.animBadgeStill : (currentOpt.text.split(' ')[1] || currentOpt.text);
      }}
    }}
  }}

  document.getElementById('secTitleLayers').innerText = t.secTitleLayers;
  const emptyNotice = document.getElementById('emptyFacesNotice');
  if (emptyNotice) {{
    emptyNotice.innerText = lang === 'ar' ? 'لا توجد وجوه افتراضية. ارفع فاكهة أو صورة مخصصة بالأعلى للبدء!' : 'No default faces. Upload a custom fruit or photo above to start!';
  }}

  // Filters section translations
  if (document.getElementById('secTitleFilters')) {{
    document.getElementById('secTitleFilters').innerText = t.secTitleFilters;
    document.getElementById('resetFiltersBtn').innerText = t.resetFilters;
    document.getElementById('lblFilterTargetText').innerText = t.lblFilterTargetText;
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
  if (typeof renderAdminCatalog === 'function') renderAdminCatalog();
  if (typeof renderAdminTemplatesCatalog === 'function') renderAdminTemplatesCatalog();
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

// DEDUPLICATE FACES ARRAY (Guarantees zero duplicate cards in grid)
function deduplicateFaces(list) {{
  if (!Array.isArray(list)) return [];
  const seenIds = new Set();
  const seenFiles = new Set();
  const seenSrcs = new Set();
  const unique = [];

  for (const f of list) {{
    if (!f) continue;
    const idLower = (f.id || '').trim().toLowerCase();
    const fileLower = (f.file || f.filename || '').trim().toLowerCase();
    const srcKey = (f.src && typeof f.src === 'string' && f.src.length > 50) ? f.src.substring(0, 80) : '';

    if (idLower && seenIds.has(idLower)) continue;
    if (fileLower && seenFiles.has(fileLower)) continue;
    if (srcKey && seenSrcs.has(srcKey)) continue;

    if (idLower) seenIds.add(idLower);
    if (fileLower) seenFiles.add(fileLower);
    if (srcKey) seenSrcs.add(srcKey);
    unique.push(f);
  }}
  return unique;
}}

// RESOLVE FACE LAYER IMAGE BY ID, FILE, OR OBJECT (Fixes "one is behind" off-by-one bug)
function getFaceLayerImg(faceObj) {{
  if (!faceObj) return null;
  if (faceObj.customImg) return faceObj.customImg;
  if (faceObj.isGif && faceObj.gifFrames && faceObj.gifFrames.length > 0) {{
    const frameIdx = (faceObj.gifIndex !== undefined ? faceObj.gifIndex : 0) % faceObj.gifFrames.length;
    return faceObj.gifFrames[frameIdx];
  }}

  // 1. Direct ID lookup in loadedFaces
  if (faceObj.faceId && loadedFaces[faceObj.faceId]) {{
    return loadedFaces[faceObj.faceId];
  }}
  // 2. Direct File lookup in loadedFaces
  const fFileLower = (faceObj.faceFile || '').toLowerCase();
  if (fFileLower && loadedFaces[fFileLower]) {{
    return loadedFaces[fFileLower];
  }}
  // 3. Find matching face in faces array
  const match = faces.find(f => (faceObj.faceId && f.id === faceObj.faceId) || (fFileLower && f.file && f.file.toLowerCase() === fFileLower));
  if (match) {{
    if (match.img && match.img.complete) return match.img;
    if (loadedFaces[match.id]) return loadedFaces[match.id];
    if (match.src) {{
      const newImg = new Image();
      newImg.src = match.src;
      match.img = newImg;
      loadedFaces[match.id] = newImg;
      if (match.file) loadedFaces[match.file.toLowerCase()] = newImg;
      newImg.onload = () => {{ render(); }};
      return newImg;
    }}
  }}
  // 4. Fallback numeric index
  if (faceObj.faceIndex !== undefined && loadedFaces[faceObj.faceIndex]) {{
    return loadedFaces[faceObj.faceIndex];
  }}
  if (faceObj.faceIndex !== undefined && faces[faceObj.faceIndex]) {{
    const f = faces[faceObj.faceIndex];
    return f.img || loadedFaces[f.id] || null;
  }}
  return null;
}}

function makeFaceLayer(faceIndexOrId, x, y, scale, z) {{
  let targetId = null;
  let targetFile = '';
  let targetName = '';
  let targetIdx = 0;

  if (typeof faceIndexOrId === 'string') {{
    targetId = faceIndexOrId;
    const found = faces.find(f => f.id === targetId || (f.file && f.file.toLowerCase() === targetId.toLowerCase()));
    if (found) {{
      targetFile = found.file || '';
      targetName = found.name || '';
      targetIdx = faces.indexOf(found);
    }}
  }} else if (typeof faceIndexOrId === 'number') {{
    targetIdx = faceIndexOrId;
    const found = faces[targetIdx];
    if (found) {{
      targetId = found.id || '';
      targetFile = found.file || '';
      targetName = found.name || '';
    }}
  }}

  return {{
    id: 'layer_' + Date.now() + '_' + Math.floor(Math.random() * 1000),
    faceId: targetId,
    faceFile: targetFile,
    faceIndex: targetIdx,
    customName: targetName,
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
    isGif: false,
    gifFrames: [],
    gifIndex: 0,
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
  bgCustomName: '',
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

// VAULT DECRYPTION HELPER (AES-GCM & SHA256-CTR)
function b64ToUint8(b64) {{
  return Uint8Array.from(atob(b64), c => c.charCodeAt(0));
}}

async function decryptVault(password) {{
  const pkg = encryptedFacesVault;
  if (!pkg || !pkg.slots || !pkg.slots.length) return [];
  const enc = new TextEncoder();
  const salt = b64ToUint8(pkg.salt);

  if (pkg.algo === 'AES-GCM') {{
    const pwdKeyMaterial = await crypto.subtle.importKey(
      'raw', enc.encode(password), 'PBKDF2', false, ['deriveKey']
    );
    const derivedKey = await crypto.subtle.deriveKey(
      {{ name: 'PBKDF2', salt: salt, iterations: 10000, hash: 'SHA-256' }},
      pwdKeyMaterial,
      {{ name: 'AES-GCM', length: 256 }},
      false,
      ['decrypt']
    );

    let masterKeyRaw = null;
    for (const slot of pkg.slots) {{
      try {{
        const slotNonce = b64ToUint8(slot.nonce);
        const slotCt = b64ToUint8(slot.ct);
        const decrypted = await crypto.subtle.decrypt(
          {{ name: 'AES-GCM', iv: slotNonce }},
          derivedKey,
          slotCt
        );
        masterKeyRaw = decrypted;
        break;
      }} catch (e) {{}}
    }}
    if (!masterKeyRaw) throw new Error('Incorrect password');

    const masterKey = await crypto.subtle.importKey(
      'raw', masterKeyRaw, 'AES-GCM', false, ['decrypt']
    );
    const pNonce = b64ToUint8(pkg.nonce);
    const pCt = b64ToUint8(pkg.ct);
    const decryptedPayload = await crypto.subtle.decrypt(
      {{ name: 'AES-GCM', iv: pNonce }},
      masterKey,
      pCt
    );
    return JSON.parse(new TextDecoder().decode(decryptedPayload));
  }} else if (pkg.algo === 'SHA256-CTR') {{
    const pwdKeyMaterial = await crypto.subtle.importKey(
      'raw', enc.encode(password), 'PBKDF2', false, ['deriveBits']
    );
    const dkBuffer = await crypto.subtle.deriveBits(
      {{ name: 'PBKDF2', salt: salt, iterations: 10000, hash: 'SHA-256' }},
      pwdKeyMaterial,
      256
    );
    const dk = new Uint8Array(dkBuffer);

    let masterKey = null;
    for (const slot of pkg.slots) {{
      const sNonce = b64ToUint8(slot.nonce);
      const sCt = b64ToUint8(slot.ct);
      const expectedTag = b64ToUint8(slot.tag);

      const hmacKey = await crypto.subtle.importKey(
        'raw', dk, {{ name: 'HMAC', hash: 'SHA-256' }}, false, ['verify']
      );
      const toSign = new Uint8Array(sNonce.length + sCt.length);
      toSign.set(sNonce, 0);
      toSign.set(sCt, sNonce.length);
      const valid = await crypto.subtle.verify('HMAC', hmacKey, expectedTag, toSign);
      if (valid) {{
        const maskInput = new Uint8Array(dk.length + sNonce.length);
        maskInput.set(dk, 0);
        maskInput.set(sNonce, dk.length);
        const maskBuf = await crypto.subtle.digest('SHA-256', maskInput);
        const mask = new Uint8Array(maskBuf);
        masterKey = new Uint8Array(32);
        for (let i = 0; i < 32; i++) masterKey[i] = sCt[i] ^ mask[i];
        break;
      }}
    }}
    if (!masterKey) throw new Error('Incorrect password');

    const pNonce = b64ToUint8(pkg.nonce);
    const pCt = b64ToUint8(pkg.ct);
    const expectedTag = b64ToUint8(pkg.tag);

    const masterHmacKey = await crypto.subtle.importKey(
      'raw', masterKey, {{ name: 'HMAC', hash: 'SHA-256' }}, false, ['verify']
    );
    const payloadToSign = new Uint8Array(pNonce.length + pCt.length);
    payloadToSign.set(pNonce, 0);
    payloadToSign.set(pCt, pNonce.length);
    const tagValid = await crypto.subtle.verify('HMAC', masterHmacKey, expectedTag, payloadToSign);
    if (!tagValid) throw new Error('Corrupt vault data');

    const numBlocks = Math.ceil(pCt.length / 32);
    const decryptedBytes = new Uint8Array(pCt.length);
    for (let i = 0; i < numBlocks; i++) {{
      const counterBytes = new Uint8Array(4);
      new DataView(counterBytes.buffer).setUint32(0, i, false);
      const blockInput = new Uint8Array(masterKey.length + pNonce.length + 4);
      blockInput.set(masterKey, 0);
      blockInput.set(pNonce, masterKey.length);
      blockInput.set(counterBytes, masterKey.length + pNonce.length);

      const blockHash = new Uint8Array(await crypto.subtle.digest('SHA-256', blockInput));
      const start = i * 32;
      const end = Math.min(start + 32, pCt.length);
      for (let j = start; j < end; j++) {{
        decryptedBytes[j] = pCt[j] ^ blockHash[j - start];
      }}
    }}
    return JSON.parse(new TextDecoder().decode(decryptedBytes));
  }}
  return [];
}}

// SAFE DATA-URI / URL TO ARRAYBUFFER HELPER
async function dataUriOrUrlToArrayBuffer(src) {{
  if (typeof src === 'string' && src.startsWith('data:')) {{
    const commaIdx = src.indexOf(',');
    if (commaIdx !== -1) {{
      const b64 = src.slice(commaIdx + 1);
      const binary = atob(b64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) {{
        bytes[i] = binary.charCodeAt(i);
      }}
      return bytes.buffer;
    }}
  }}
  const res = await fetch(src);
  return await res.arrayBuffer();
}}

// Active operation trackers to show live spinners and prevent resurrection
const deletingItemIds = new Set();
const deletedItemFiles = new Set();
const uploadingItemIds = new Set();

// UNIVERSAL GIF FRAME DECODER (Multi-frame & disposal support)
async function parseGifFrames(arrayBuffer) {{
  try {{
    let rawFrames = null;
    let fullW = 0, fullH = 0;
    if (window.GIF) {{
      try {{
        const g = new window.GIF(arrayBuffer);
        rawFrames = g.decompressFrames(true);
        if (g.raw && g.raw.lsd) {{
          fullW = g.raw.lsd.width || 0;
          fullH = g.raw.lsd.height || 0;
        }}
      }} catch (e1) {{
        if (typeof window.GIF.decompressFrames === 'function') {{
          rawFrames = window.GIF.decompressFrames(arrayBuffer, true);
        }}
      }}
    }}
    if (!rawFrames && window.gifuct) {{
      try {{
        if (typeof window.gifuct.parseGIF === 'function') {{
          const parsed = window.gifuct.parseGIF(arrayBuffer);
          rawFrames = window.gifuct.decompressFrames(parsed, true);
          if (parsed && parsed.lsd) {{
            fullW = parsed.lsd.width || 0;
            fullH = parsed.lsd.height || 0;
          }}
        }} else if (typeof window.gifuct.decompressFrames === 'function') {{
          rawFrames = window.gifuct.decompressFrames(arrayBuffer, true);
        }}
      }} catch (e2) {{}}
    }}

    if (!rawFrames || rawFrames.length === 0) return null;

    if (!fullW || !fullH) {{
      rawFrames.forEach(f => {{
        if (f.dims) {{
          const r = (f.dims.left || 0) + (f.dims.width || 0);
          const b = (f.dims.top || 0) + (f.dims.height || 0);
          if (r > fullW) fullW = r;
          if (b > fullH) fullH = b;
        }}
      }});
      if (!fullW) fullW = 400;
      if (!fullH) fullH = 400;
    }}

    const tmpCanv = document.createElement('canvas');
    tmpCanv.width = fullW;
    tmpCanv.height = fullH;
    const tmpCtx = tmpCanv.getContext('2d');

    const loadedFrames = [];
    const frameDelays = [];
    for (let i = 0; i < rawFrames.length; i++) {{
      const f = rawFrames[i];
      let d = f.delay;
      // In GIF format, delay is in ms (or 10ms units converted by parser).
      // Standard browser playback treats 0 or < 20ms as 100ms (10 fps).
      if (!d || d < 20) d = 100;
      frameDelays.push(d);

      if (f.disposalType === 2) {{
        tmpCtx.clearRect(0, 0, fullW, fullH);
      }}
      if (f.patch && f.dims && f.dims.width > 0 && f.dims.height > 0) {{
        const patchCanv = document.createElement('canvas');
        patchCanv.width = f.dims.width;
        patchCanv.height = f.dims.height;
        const patchCtx = patchCanv.getContext('2d');
        const patchData = patchCtx.createImageData(f.dims.width, f.dims.height);
        patchData.data.set(f.patch);
        patchCtx.putImageData(patchData, 0, 0);

        tmpCtx.drawImage(patchCanv, f.dims.left || 0, f.dims.top || 0);
      }}
      const img = new Image();
      img.src = tmpCanv.toDataURL('image/png');
      await new Promise(r => {{ img.onload = r; img.onerror = r; }});
      loadedFrames.push(img);
    }}
    loadedFrames.delays = frameDelays;
    loadedFrames.totalDuration = frameDelays.reduce((a, b) => a + b, 0);
    return loadedFrames;
  }} catch (err) {{
    console.warn('parseGifFrames error:', err);
    return null;
  }}
}}

// DYNAMIC EXPORT FILE NAME GENERATOR
function updateDynamicFileName() {{
  const input = document.getElementById('exportFileNameInput');
  if (!input) return;

  const parts = [];

  // 1. Background / Template name
  if (state.bgType === 'template' && state.bgTemplateId) {{
    const tpl = templates.find(t => t.id === state.bgTemplateId);
    let stem = tpl ? (tpl.name || tpl.file || '') : state.bgTemplateId;
    stem = stem.replace(/[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]|[\\u2600-\\u27BF]/g, '').trim().toLowerCase();
    const cleanStem = stem.replace(/[^a-z0-9]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    if (cleanStem) parts.push(cleanStem.substring(0, 10));
  }} else if (state.bgType === 'custom' && state.bgCustomName) {{
    const clean = state.bgCustomName.replace(/\\.[^/.]+$/, '').replace(/[^a-z0-9]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '').toLowerCase();
    if (clean) parts.push(clean.substring(0, 10));
  }}

  // 2. Faces on canvas
  state.facesOnCanvas.forEach((f, idx) => {{
    let fName = '';
    if (f.customName) {{
      fName = f.customName;
    }} else if (faces[f.faceIndex]) {{
      fName = faces[f.faceIndex].name || faces[f.faceIndex].file || '';
    }}
    fName = fName.replace(/[\\uD800-\\uDBFF][\\uDC00-\\uDFFF]|[\\u2600-\\u27BF]/g, '').trim().toLowerCase();
    let clean = fName.replace(/[^a-z0-9]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    if (!clean) clean = 'face' + (idx + 1);
    parts.push(clean.substring(0, 10));
  }});

  // 3. Text snippet
  if (state.texts.length > 0 && state.texts[0].text) {{
    const txt = state.texts[0].text.trim().toLowerCase();
    const clean = txt.replace(/[^a-z0-9]/gi, '-').replace(/-+/g, '-').replace(/^-|-$/g, '');
    if (clean) parts.push(clean.substring(0, 10));
  }}

  let finalName = parts.slice(0, 4).join('-');
  if (!finalName) finalName = 'frutisator-meme';
  if (finalName.length > 30) finalName = finalName.substring(0, 30).replace(/-$/, '');

  input.placeholder = finalName;
  if (!input.dataset.userEdited) {{
    input.value = finalName;
  }}
}}

const canvas = document.getElementById('mainCanvas');
const ctx = canvas.getContext('2d');
canvas.width = 800;
canvas.height = 800;

// Preload face images (only executed when vault is unlocked)
let loadedFaces = {{}};
function preloadFaces() {{
  if (!isVaultUnlocked) return;
  faces = deduplicateFaces(faces);
  faces.forEach((f, idx) => {{
    const fId = f.id || ('face_' + idx);
    const fFile = (f.file || '').toLowerCase();

    let img = loadedFaces[fId] || (fFile && loadedFaces[fFile]);
    if (!img || !img.src) {{
      img = new Image();
      img.src = f.src;
      img.onload = () => {{
        render();
      }};
    }}
    f.img = img;
    loadedFaces[fId] = img;
    if (fFile) loadedFaces[fFile] = img;
    loadedFaces[idx] = img;
  }});
}}

// --- DEDUPLICATION & TEMPLATE PRELOADING ---
function deduplicateTemplates(list) {{
  if (!Array.isArray(list)) return [];
  const seenIds = new Set();
  const seenFiles = new Set();
  const seenSrcs = new Set();
  const unique = [];

  for (const t of list) {{
    if (!t) continue;
    const tId = (t.id || '').toLowerCase().trim();
    const tFile = (t.file || t.filename || '').toLowerCase().trim();
    const tSrc = (t.src || '').slice(0, 100);

    if (tId && seenIds.has(tId)) continue;
    if (tFile && seenFiles.has(tFile)) continue;
    if (tSrc && seenSrcs.has(tSrc)) continue;

    if (tId) seenIds.add(tId);
    if (tFile) seenFiles.add(tFile);
    if (tSrc) seenSrcs.add(tSrc);
    unique.push(t);
  }}
  return unique;
}}

let loadedTemplates = {{}};

function getBgTemplateImg(tplId) {{
  if (!tplId) return null;
  if (loadedTemplates[tplId]) return loadedTemplates[tplId];
  const tplIdLower = String(tplId).toLowerCase();
  if (loadedTemplates[tplIdLower]) return loadedTemplates[tplIdLower];
  if (templates) {{
    const match = templates.find(t => t.id === tplId || (t.file && t.file.toLowerCase() === tplIdLower));
    if (match) {{
      return match.img || loadedTemplates[match.id] || (match.file ? loadedTemplates[match.file.toLowerCase()] : null);
    }}
  }}
  return null;
}}

function preloadTemplates() {{
  templates = deduplicateTemplates(templates);
  templates.forEach(t => {{
    if (!t) return;
    const tId = t.id;
    const tFile = (t.file || '').toLowerCase();
    if (!loadedTemplates[tId]) {{
      const img = new Image();
      img.src = t.src;
      img.onload = () => {{ render(); }};
      t.img = img;
      loadedTemplates[tId] = img;
      if (tFile) loadedTemplates[tFile] = img;
    }}
  }});
}}
preloadTemplates();

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
  if (t.type === 'bg') {{
    return {{
      type: 'bg',
      idx: 0,
      obj: {{ filters: state.bgFilters }},
      name: currentLang === 'ar' ? 'الخلفية 🖼️' : 'Backdrop 🖼️'
    }};
  }}
  if (t.type === 'face' && state.facesOnCanvas[t.idx]) {{
    const face = state.facesOnCanvas[t.idx];
    let img = getFaceLayerImg(face);
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
      let img = getFaceLayerImg(obj);
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
  if (state.bgIsGif && state.bgGifFrames && state.bgGifFrames.length > 0) {{
    const fIdx = (state.bgGifIndex !== undefined ? state.bgGifIndex : 0) % state.bgGifFrames.length;
    bgImg = state.bgGifFrames[fIdx];
  }} else if (state.bgType === 'custom' && state.bgCustomImg) {{
    bgImg = state.bgCustomImg;
  }} else if (state.bgType === 'template') {{
    bgImg = getBgTemplateImg(state.bgTemplateId);
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
      let img = getFaceLayerImg(obj);
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
      const scaleXMult = animOff.scaleX !== undefined ? animOff.scaleX : (animOff.scale !== undefined ? animOff.scale : 1.0);
      const scaleYMult = animOff.scaleY !== undefined ? animOff.scaleY : (animOff.scale !== undefined ? animOff.scale : 1.0);
      const w = baseW * sx * scaleXMult;
      const h = baseH * sy * scaleYMult;

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
  if (active && active.type !== 'bg') {{
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
  document.getElementById('optDeleteBtn').style.display = 'inline-block';
  document.getElementById('optCenterBtn').style.display = 'inline-block';
  document.getElementById('optFlipBtn').style.display = 'inline-block';

  if (active.type === 'bg') {{
    nameBadge.innerText = currentLang === 'ar' ? '🖼️ الخلفية (مثبتة)' : '🖼️ Backdrop (Locked)';
    document.getElementById('optDeleteBtn').style.display = 'none';
    document.getElementById('optCenterBtn').style.display = 'none';
    scaleVal.innerText = '100%';
    rotVal.innerText = '0°';
    return;
  }}

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
      syncFilterUI();
    }} else {{
      state.activeTransformTarget = null;
      render();
      syncLayersUI();
      syncFilterUI();
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
          let img = getFaceLayerImg(active.obj);
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

// --- POPULATE TEMPLATES & FACES GRIDS ---
function renderTemplatesGrid() {{
  const bgGrid = document.getElementById('bgPresetsRow');
  if (!bgGrid) return;
  bgGrid.innerHTML = '';
  templates = deduplicateTemplates(templates);
  templates.forEach(t => {{
    const card = document.createElement('div');
    card.className = 'grid-card-template' + (state.bgTemplateId === t.id ? ' active' : '');
    card.setAttribute('data-tpl-id', t.id || '');
    card.setAttribute('data-tpl-file', t.file || '');
    card.innerHTML = `<img src="${{t.src}}" alt="${{t.name}}"><span>${{t.name}}</span>`;

    // Live sync and deletion indicator on cards
    const tFile = (t.file || '').toLowerCase();
    if (deletingItemIds.has(t.id) || (tFile && deletingItemIds.has(tFile))) {{
      const overlay = document.createElement('div');
      overlay.className = 'card-syncing-overlay';
      overlay.innerHTML = '<div class="ps-spinner ps-spinner-danger"></div><span class="card-syncing-text">Deleting...</span>';
      card.appendChild(overlay);
    }} else if (uploadingItemIds.has(t.id)) {{
      const overlay = document.createElement('div');
      overlay.className = 'card-syncing-overlay';
      overlay.innerHTML = '<div class="ps-spinner"></div><span class="card-syncing-text">Syncing...</span>';
      card.appendChild(overlay);
    }}

    card.onclick = async () => {{
      const targetFile = (t.file || '').toLowerCase();
      if (deletingItemIds.has(t.id) || (targetFile && deletingItemIds.has(targetFile))) return;
      document.querySelectorAll('#bgPresetsRow .grid-card-template').forEach(c => c.classList.remove('active'));
      card.classList.add('active');
      state.bgType = 'template';
      state.bgTemplateId = t.id;
      state.bgCustomImg = null;
      state.bgCustomName = '';
      state.bgIsGif = false;
      state.bgGifFrames = [];

      const isGif = (t.file && t.file.toLowerCase().endsWith('.gif')) || (t.src && t.src.startsWith('data:image/gif'));
      if (isGif && t.src) {{
        if (t.gifFrames && t.gifFrames.length > 0) {{
          state.bgIsGif = true;
          state.bgGifFrames = t.gifFrames;
          state.bgGifIndex = 0;
          state.bgCustomImg = t.gifFrames[0];
          render();
        }} else {{
          const tempSpin = document.createElement('div');
          tempSpin.className = 'card-syncing-overlay';
          tempSpin.innerHTML = '<div class="ps-spinner"></div><span class="card-syncing-text">Loading GIF...</span>';
          card.appendChild(tempSpin);
          try {{
            const buf = await dataUriOrUrlToArrayBuffer(t.src);
            const frames = await parseGifFrames(buf);
            if (frames && frames.length > 0) {{
              t.gifFrames = frames;
              state.bgIsGif = true;
              state.bgGifFrames = frames;
              state.bgGifDelays = frames.delays || [];
              state.bgGifTotalDuration = frames.totalDuration || (frames.length * 100);
              state.bgGifIndex = 0;
              state.bgCustomImg = frames[0];
              bgElapsedMs = 0;
            }}
          }} catch(e) {{
            console.warn('Template GIF parse error:', e);
          }} finally {{
            if (card.contains(tempSpin)) card.removeChild(tempSpin);
          }}
        }}
      }}
      render();
      syncLayersUI();
      updateDynamicFileName();
    }};
    bgGrid.appendChild(card);
  }});
}}

function renderFacesGrid() {{
  const facesGrid = document.getElementById('facesGrid');
  if (!facesGrid) return;
  facesGrid.innerHTML = '';
  // ABSOLUTE SECURITY: NEVER render private faces into DOM if vault is locked!
  if (!isVaultUnlocked) {{
    return;
  }}
  faces = deduplicateFaces(faces);
  if (faces.length === 0) {{
    const emptyNotice = document.createElement('div');
    emptyNotice.id = 'emptyFacesNotice';
    emptyNotice.style.cssText = 'grid-column: 1 / -1; padding: 14px 10px; text-align: center; color: var(--ps-text-muted); font-size: 11.5px; border: 1px dashed var(--ps-border); border-radius: 6px; background: rgba(255,255,255,0.02); line-height: 1.5;';
    emptyNotice.innerText = currentLang === 'ar' ? 'لا توجد وجوه افتراضية. ارفع فاكهة أو صورة مخصصة بالأعلى للبدء!' : 'No default faces. Upload a custom fruit or photo above to start!';
    facesGrid.appendChild(emptyNotice);
  }} else {{
    const activeData = getActiveLayerData();
    const activeFaceId = (activeData && activeData.type === 'face' && activeData.obj) ? (activeData.obj.faceId || (faces[activeData.obj.faceIndex] || {{}}).id) : null;

    faces.forEach((f, idx) => {{
      const fId = f.id || ('face_' + idx);
      const fFile = (f.file || '').toLowerCase();
      const isActive = activeFaceId ? (f.id === activeFaceId || (activeData.obj.faceFile && fFile === activeData.obj.faceFile.toLowerCase())) : (idx === 0);

      const card = document.createElement('div');
      card.className = 'grid-card' + (isActive ? ' active' : '');
      card.setAttribute('data-face-id', fId);
      card.setAttribute('data-face-file', f.file || '');
      card.innerHTML = `<img src="${{f.src}}" alt="${{f.name}}"><span>${{f.name}}</span>`;

      // Live sync and deletion indicator on cards
      if (deletingItemIds.has(f.id) || (fFile && deletingItemIds.has(fFile))) {{
        const overlay = document.createElement('div');
        overlay.className = 'card-syncing-overlay';
        overlay.innerHTML = '<div class="ps-spinner ps-spinner-danger"></div><span class="card-syncing-text">Deleting...</span>';
        card.appendChild(overlay);
      }} else if (uploadingItemIds.has(f.id)) {{
        const overlay = document.createElement('div');
        overlay.className = 'card-syncing-overlay';
        overlay.innerHTML = '<div class="ps-spinner"></div><span class="card-syncing-text">Syncing...</span>';
        card.appendChild(overlay);
      }}

      card.onclick = async () => {{
        if (deletingItemIds.has(f.id) || (fFile && deletingItemIds.has(fFile))) return;
        document.querySelectorAll('#facesGrid .grid-card').forEach(c => c.classList.remove('active'));
        card.classList.add('active');
        let targetLayer = null;
        const active = getActiveLayerData();
        if (active && active.type === 'face') {{
          active.obj.faceId = f.id;
          active.obj.faceFile = f.file;
          active.obj.faceIndex = faces.findIndex(item => item.id === f.id || (f.file && item.file === f.file));
          active.obj.customImg = null;
          active.obj.customName = f.name;
          active.obj.isGif = false;
          active.obj.gifFrames = [];
          targetLayer = active.obj;
        }} else {{
          targetLayer = makeFaceLayer(f.id || idx, 0, 0, 1.0);
          targetLayer.faceId = f.id;
          targetLayer.faceFile = f.file;
          targetLayer.customName = f.name;
          state.facesOnCanvas.push(targetLayer);
          state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
        }}
        const isGif = (f.file && f.file.toLowerCase().endsWith('.gif')) || (f.src && f.src.startsWith('data:image/gif'));
        if (isGif && f.src) {{
          if (f.gifFrames && f.gifFrames.length > 0) {{
            targetLayer.isGif = true;
            targetLayer.gifFrames = f.gifFrames;
            targetLayer.gifIndex = 0;
            render();
          }} else {{
            const tempSpin = document.createElement('div');
            tempSpin.className = 'card-syncing-overlay';
            tempSpin.innerHTML = '<div class="ps-spinner"></div><span class="card-syncing-text">Loading GIF...</span>';
            card.appendChild(tempSpin);
            try {{
              const buf = await dataUriOrUrlToArrayBuffer(f.src);
              const frames = await parseGifFrames(buf);
              if (frames && frames.length > 0) {{
                f.gifFrames = frames;
                targetLayer.isGif = true;
                targetLayer.gifFrames = frames;
                targetLayer.gifIndex = 0;
              }}
            }} catch(e) {{
              console.warn('Face GIF parse warning:', e);
            }} finally {{
              if (card.contains(tempSpin)) card.removeChild(tempSpin);
            }}
          }}
        }}
        render();
        syncLayersUI();
        updateDynamicFileName();
      }};
      facesGrid.appendChild(card);
    }});
  }}
}}

// --- POPULATE SIDEBARS & EVENTS ---
function initUIEvents() {{
  // 1. Templates Grid
  renderTemplatesGrid();

  // Backdrop Custom File Upload
  document.getElementById('bgFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;
    state.bgCustomName = file.name;

    const isGif = file.name.toLowerCase().endsWith('.gif') || file.type === 'image/gif';
    if (isGif) {{
      const reader = new FileReader();
      reader.onload = async (ev) => {{
        try {{
          const frames = await parseGifFrames(ev.target.result);
          if (frames && frames.length > 0) {{
            state.bgType = 'custom';
            state.bgIsGif = true;
            state.bgGifFrames = frames;
            state.bgGifDelays = frames.delays || [];
            state.bgGifTotalDuration = frames.totalDuration || (frames.length * 100);
            state.bgGifIndex = 0;
            state.bgCustomImg = frames[0];
            bgElapsedMs = 0;
            render();
            syncLayersUI();
            updateDynamicFileName();
            return;
          }}
        }} catch (err) {{
          console.error('Backdrop GIF decode notice:', err);
        }}
        const img = new Image();
        img.src = URL.createObjectURL(file);
        img.onload = () => {{
          state.bgType = 'custom';
          state.bgCustomImg = img;
          state.bgIsGif = false;
          state.bgGifFrames = [];
          render();
          syncLayersUI();
          updateDynamicFileName();
        }};
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
          syncLayersUI();
          updateDynamicFileName();
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

  // Cloud Sync Buttons
  const syncMainBtn = document.getElementById('btnSyncCloud');
  if (syncMainBtn) syncMainBtn.onclick = () => syncCloudCatalog(true);
  const syncFacesBtn = document.getElementById('btnSyncFacesQuick');
  if (syncFacesBtn) syncFacesBtn.onclick = () => syncCloudCatalog(true);
  const syncTplsBtn = document.getElementById('btnSyncTemplatesQuick');
  if (syncTplsBtn) syncTplsBtn.onclick = () => syncCloudCatalog(true);

  // Dynamic Filename Input listener
  const expInput = document.getElementById('exportFileNameInput');
  if (expInput) {{
    expInput.oninput = (e) => {{
      if (e.target.value.trim()) {{
        expInput.dataset.userEdited = 'true';
      }} else {{
        expInput.dataset.userEdited = '';
        updateDynamicFileName();
      }}
    }};
  }}

  // 2. Populate Fruits Faces Grid
  renderFacesGrid();

  // Add Face Button
  document.getElementById('addFaceBtn').onclick = () => {{
    if (!isVaultUnlocked) {{
      const vInput = document.getElementById('vaultPwdInput');
      if (vInput) {{
        vInput.focus();
        vInput.classList.add('ps-input-glow');
        setTimeout(() => vInput.classList.remove('ps-input-glow'), 1200);
      }}
      return;
    }}
    if (faces.length === 0) {{
      document.getElementById('faceFileInput').click();
      return;
    }}
    const firstFace = faces[0];
    const newFaceLayer = makeFaceLayer(firstFace ? firstFace.id : 0, Math.floor((Math.random() - 0.5) * 80), Math.floor((Math.random() - 0.5) * 80), 1.0);
    if (firstFace) {{
      newFaceLayer.faceId = firstFace.id;
      newFaceLayer.faceFile = firstFace.file;
      newFaceLayer.customName = firstFace.name;
    }}
    state.facesOnCanvas.push(newFaceLayer);
    state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
    render();
    syncLayersUI();
    updateDynamicFileName();
  }};

  // Custom Face Upload
  document.getElementById('faceFileInput').onchange = (e) => {{
    const file = e.target.files[0];
    if (!file) return;

    if (file.name.toLowerCase().endsWith('.gif')) {{
      const reader = new FileReader();
      reader.onload = async (ev) => {{
        const newLayer = makeFaceLayer(0, 0, 0, 1.0);
        newLayer.customName = file.name.replace(/\\.[^/.]+$/, '');
        try {{
          const frames = await parseGifFrames(ev.target.result);
          if (frames && frames.length > 0) {{
            newLayer.isGif = true;
            newLayer.gifFrames = frames;
            newLayer.gifIndex = 0;
            newLayer.customImg = frames[0];
          }} else {{
            const img = new Image();
            img.src = URL.createObjectURL(file);
            newLayer.customImg = img;
          }}
        }} catch (err) {{
          const img = new Image();
          img.src = URL.createObjectURL(file);
          newLayer.customImg = img;
        }}
        state.facesOnCanvas.push(newLayer);
        state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
        render();
        syncLayersUI();
        updateDynamicFileName();
      }};
      reader.readAsArrayBuffer(file);
    }} else {{
      const reader = new FileReader();
      reader.onload = (ev) => {{
        const img = new Image();
        img.src = ev.target.result;
        img.onload = () => {{
          const newLayer = makeFaceLayer(0, 0, 0, 1.0);
          newLayer.customName = file.name.replace(/\\.[^/.]+$/, '');
          newLayer.customImg = img;
          state.facesOnCanvas.push(newLayer);
          state.activeTransformTarget = {{ type: 'face', idx: state.facesOnCanvas.length - 1 }};
          render();
          syncLayersUI();
          updateDynamicFileName();
        }};
      }};
      reader.readAsDataURL(file);
    }}
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
    updateDynamicFileName();
  }};
  document.getElementById('addBottomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'BOTTOM TEXT', x: 0, y: Math.round(canvas.height * 0.35), size: 52, color: '#ffffff', font: document.getElementById('fontFamilySelect').value, rotation: 0, z: ++layerZCounter }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'BOTTOM TEXT';
    render();
    syncLayersUI();
    updateDynamicFileName();
  }};
  document.getElementById('addCustomTextBtn').onclick = () => {{
    state.texts.push({{ id: 't_' + Date.now(), text: 'YOUR TEXT', x: 0, y: 0, size: 52, color: '#ffffff', font: document.getElementById('fontFamilySelect').value, rotation: 0, z: ++layerZCounter }});
    state.activeTransformTarget = {{ type: 'text', idx: state.texts.length - 1 }};
    state.selectedTextIdx = state.texts.length - 1;
    document.getElementById('activeTextInput').value = 'YOUR TEXT';
    render();
    syncLayersUI();
    updateDynamicFileName();
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
        updateDynamicFileName();
      }}
      return;
    }}
    active.obj.text = e.target.value.toUpperCase();
    render();
    syncLayersUI();
    updateDynamicFileName();
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

  // Text Color Swatches (1x1 Boxes & Under-Button Native Color Picker)
  document.querySelectorAll('#textColorGroup .color-swatch-box').forEach(btn => {{
    btn.onclick = () => {{
      if (btn.id === 'colorWheelBtn') return; // Handled directly by native color picker input overlay
      document.querySelectorAll('#textColorGroup .color-swatch-box').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const active = getActiveLayerData();
      if (active && active.type === 'text') {{
        active.obj.color = btn.dataset.color;
        render();
      }}
    }};
  }});

  // Native Color Picker Input (Opens directly under the color wheel box)
  document.getElementById('nativeColorPicker').oninput = (e) => {{
    const color = e.target.value;
    const wheelBtn = document.getElementById('colorWheelBtn');
    document.querySelectorAll('#textColorGroup .color-swatch-box').forEach(b => b.classList.remove('active'));
    wheelBtn.classList.add('active');
    wheelBtn.style.borderColor = '#ffffff';
    wheelBtn.style.boxShadow = '0 0 0 2px ' + color + ', 0 2px 8px rgba(0, 0, 0, 0.6)';

    const active = getActiveLayerData();
    if (active && active.type === 'text') {{
      active.obj.color = color;
      render();
    }}
  }};

  // --- COLOR FILTERS & ADJUSTMENTS CONTROLLER ---
  let currentFilterTarget = 'bg';

  window.getActiveFilterTargetObj = function() {{
    const active = getActiveLayerData();
    if (active) {{
      if (active.type === 'bg') {{
        if (!state.bgFilters) state.bgFilters = makeDefaultFilters();
        return state.bgFilters;
      }}
      if (active.type === 'face') {{
        if (!active.obj.filters) active.obj.filters = makeDefaultFilters();
        return active.obj.filters;
      }}
      if (active.type === 'acc') {{
        if (!active.obj.filters) active.obj.filters = makeDefaultFilters();
        return active.obj.filters;
      }}
    }}

    // If explicit target pill was chosen
    if (currentFilterTarget === 'bg') {{
      if (!state.bgFilters) state.bgFilters = makeDefaultFilters();
      return state.bgFilters;
    }}
    if (currentFilterTarget === 'face') {{
      if (state.facesOnCanvas.length > 0) {{
        const f0 = state.facesOnCanvas[0];
        if (!f0.filters) f0.filters = makeDefaultFilters();
        return f0.filters;
      }}
      return null;
    }}
    if (currentFilterTarget === 'acc') {{
      if (state.accessoriesOnCanvas.length > 0) {{
        const a0 = state.accessoriesOnCanvas[0];
        if (!a0.filters) a0.filters = makeDefaultFilters();
        return a0.filters;
      }}
      return null;
    }}
    if (!state.bgFilters) state.bgFilters = makeDefaultFilters();
    return state.bgFilters;
  }};

  window.syncFilterUI = function() {{
    const active = getActiveLayerData();
    const effectiveType = active ? active.type : currentFilterTarget;
    currentFilterTarget = effectiveType;

    // Update target switcher pills active state
    document.querySelectorAll('#filterTargetGroup .btn-toggle').forEach(b => {{
      b.classList.toggle('active', b.getAttribute('data-target') === effectiveType);
    }});

    // Update Selected Layer Target Badge in Filter section
    const badgeName = document.getElementById('valFilterTargetName');
    if (badgeName) {{
      if (effectiveType === 'face') {{
        const fObj = active ? faces[active.obj.faceIndex] : null;
        badgeName.innerText = '🍉 ' + (fObj ? fObj.name : (currentLang === 'ar' ? 'فاكهة مخصصة' : 'Custom Face'));
        badgeName.style.color = '#ff6b8b';
      }} else if (effectiveType === 'acc') {{
        const idx = active ? (active.idx + 1) : 1;
        badgeName.innerText = '🎀 ' + (currentLang === 'ar' ? 'ملصق #' + idx : 'Sticker #' + idx);
        badgeName.style.color = '#a78bfa';
      }} else {{
        badgeName.innerText = '🖼️ ' + (currentLang === 'ar' ? 'الخلفية' : 'Backdrop');
        badgeName.style.color = 'var(--ps-blue)';
      }}
    }}

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
        if (tgt === 'bg') {{
          state.activeTransformTarget = {{ type: 'bg' }};
        }} else if (tgt === 'face' && state.facesOnCanvas.length > 0) {{
          state.activeTransformTarget = {{ type: 'face', idx: 0 }};
        }} else if (tgt === 'acc' && state.accessoriesOnCanvas.length > 0) {{
          state.activeTransformTarget = {{ type: 'acc', idx: 0 }};
        }}
        render();
        syncLayersUI();
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

  // 5. Discord Animation Dropdown
  const animSelect = document.getElementById('animEffectSelect');
  if (animSelect) {{
    animSelect.onchange = () => {{
      state.animation = animSelect.value;
      const badge = document.getElementById('animActiveBadge');
      if (badge) {{
        const opt = animSelect.options[animSelect.selectedIndex];
        badge.innerText = opt ? (opt.value === 'none' ? (i18n[currentLang].animBadgeStill || 'Still') : (opt.text.split(' ')[1] || opt.text)) : state.animation;
      }}
      render();
    }};
  }}

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

  function deleteActiveLayer() {{
    const active = getActiveLayerData();
    if (!active) return;
    if (active.type === 'face') {{
      state.facesOnCanvas.splice(active.idx, 1);
    }} else if (active.type === 'acc') {{
      state.accessoriesOnCanvas.splice(active.idx, 1);
    }} else if (active.type === 'text') {{
      state.texts.splice(active.idx, 1);
      const ti = document.getElementById('activeTextInput');
      if (ti) ti.value = '';
    }} else if (active.type === 'bg') {{
      state.bgType = 'color';
      state.bgCustomImg = null;
      state.bgTemplateId = null;
      state.bgIsGif = false;
      state.bgGifFrames = [];
      state.bgCustomName = '';
    }}
    state.activeTransformTarget = null;
    render();
    syncLayersUI();
    updateDynamicFileName();
  }}

  document.getElementById('optDeleteBtn').onclick = deleteActiveLayer;

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
    let isUnlocked = false;
    try {{ isUnlocked = localStorage.getItem('frutisator_admin_unlocked') === 'true'; }} catch(e) {{}}
    if (isUnlocked) {{
      adminAuthBody.style.display = 'none';
      adminManageBody.style.display = 'flex';
      renderAdminCatalog();
      renderAdminTemplatesCatalog();
    }} else {{
      adminAuthBody.style.display = 'block';
      adminManageBody.style.display = 'none';
      adminPwdInput.focus();
    }}
  }}

  function switchAdminTab(tabName) {{
    const isFaces = tabName === 'faces';
    document.getElementById('adminTabFacesBtn').classList.toggle('active', isFaces);
    document.getElementById('adminTabTemplatesBtn').classList.toggle('active', !isFaces);
    document.getElementById('adminTabFacesPanel').style.display = isFaces ? 'flex' : 'none';
    document.getElementById('adminTabTemplatesPanel').style.display = !isFaces ? 'flex' : 'none';
    if (isFaces) renderAdminCatalog();
    else renderAdminTemplatesCatalog();
  }}

  document.getElementById('adminTabFacesBtn').onclick = () => switchAdminTab('faces');
  document.getElementById('adminTabTemplatesBtn').onclick = () => switchAdminTab('templates');

  adminLockBtn.onclick = () => {{
    openAdminModal();
    switchAdminTab('faces');
  }};

  const adminTplLockBtn = document.getElementById('adminTplLockBtn');
  if (adminTplLockBtn) {{
    adminTplLockBtn.onclick = () => {{
      openAdminModal();
      switchAdminTab('templates');
    }};
  }}

  adminModalClose.onclick = () => {{ adminModal.style.display = 'none'; }};

  async function attemptAdminUnlock() {{
    if (adminPwdInput.value === EXPECTED_ADMIN_PWD) {{
      adminAuthBody.style.display = 'none';
      adminManageBody.style.display = 'flex';
      try {{ localStorage.setItem('frutisator_admin_unlocked', 'true'); }} catch(e) {{}}
      if (!isVaultUnlocked) {{
        await unlockVaultUI(adminPwdInput.value, false);
      }}
      renderAdminCatalog();
      renderAdminTemplatesCatalog();
    }} else {{
      adminAuthError.style.display = 'block';
    }}
  }}

  adminUnlockBtn.onclick = attemptAdminUnlock;
  adminPwdInput.onkeydown = (e) => {{
    if (e.key === 'Enter') attemptAdminUnlock();
  }};

  adminLockOutBtn.onclick = () => {{
    try {{ localStorage.removeItem('frutisator_admin_unlocked'); }} catch(e) {{}}
    adminManageBody.style.display = 'none';
    adminAuthBody.style.display = 'block';
    adminModal.style.display = 'none';
  }};

  // Secret Hotkey Ctrl+Shift+A & Delete/Backspace for Canvas Layers
  window.addEventListener('keydown', (e) => {{
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'a') {{
      openAdminModal();
      return;
    }}
    const tag = (e.target && e.target.tagName) ? e.target.tagName.toLowerCase() : '';
    if (tag === 'input' || tag === 'textarea' || tag === 'select' || (e.target && e.target.isContentEditable)) return;
    if (e.key === 'Delete' || e.key === 'Backspace') {{
      deleteActiveLayer();
    }}
  }});

  // Admin upload to GitHub
  // Template upload handler with live loading circle & syncing indicator
  const adminUploadTplBtn = document.getElementById('adminUploadTplBtn');
  if (adminUploadTplBtn) {{
    adminUploadTplBtn.onclick = () => {{
      const name = (document.getElementById('adminNewTplName').value || '').trim();
      const file = document.getElementById('adminNewTplFile').files[0];
      const status = document.getElementById('adminUploadTplStatus');

      if (!name || !file) {{
        status.style.color = 'var(--ps-danger)';
        status.innerText = '⚠️ Please enter a template name and select an image.';
        return;
      }}

      adminUploadTplBtn.disabled = true;
      const origBtnHtml = adminUploadTplBtn.innerHTML;
      adminUploadTplBtn.innerHTML = '<span class="ps-spinner"></span> <span>Syncing to Cloud...</span>';

      status.style.color = 'var(--ps-blue)';
      status.innerHTML = '<span class="ps-spinner"></span> <span>Processing & syncing template to storage repo...</span>';

      const isGif = file.name.toLowerCase().endsWith('.gif') || file.type === 'image/gif';
      const reader = new FileReader();
      reader.onload = async (e) => {{
        const b64 = e.target.result;
        const filename = file.name.replace(/[^a-zA-Z0-9._-]/g, '_');
        const imgId = 'tpl_' + Date.now();

        // Show live loading placeholder card in templates grid
        uploadingItemIds.add(imgId);
        renderTemplatesGrid();

        // Show live uploading row in admin list
        const tplList = document.getElementById('adminTemplatesCatalogList');
        if (tplList) {{
          const syncRow = document.createElement('div');
          syncRow.id = `tempSyncRow_${{imgId}}`;
          syncRow.className = 'item-syncing-row';
          syncRow.innerHTML = `<div class="ps-spinner"></div> <span>Syncing "${{name}}" to Templates storage...</span>`;
          tplList.prepend(syncRow);
        }}

        try {{
          let uploadedFilename = filename;
          if (GITHUB_TOKEN) {{
            const res = await syncTemplateToGitHub(name, filename, b64);
            if (res && res.file) uploadedFilename = res.file;
          }}

          let parsedFrames = null;
          if (isGif) {{
            try {{
              const buf = await dataUriOrUrlToArrayBuffer(b64);
              parsedFrames = await parseGifFrames(buf);
            }} catch(err) {{}}
          }}

          const newTplObj = {{
            id: imgId,
            name: name,
            file: uploadedFilename,
            src: b64,
            isGif: isGif,
            gifFrames: parsedFrames
          }};
          const newImg = new Image();
          newImg.src = b64;
          newTplObj.img = newImg;

          const upTplFileLower = (uploadedFilename || '').toLowerCase();
          templates = templates.filter(t => t.id !== imgId && (t.file || '').toLowerCase() !== upTplFileLower);
          templates.push(newTplObj);
          templates = deduplicateTemplates(templates);

          loadedTemplates[imgId] = newImg;
          if (uploadedFilename) loadedTemplates[upTplFileLower] = newImg;

          uploadingItemIds.delete(imgId);
          renderTemplatesGrid();
          renderAdminTemplatesCatalog();

          status.style.color = 'var(--ps-green)';
          status.innerText = '✅ Template successfully added & synced!';
          document.getElementById('adminNewTplName').value = '';
          document.getElementById('adminNewTplFile').value = '';
        }} catch (err) {{
          uploadingItemIds.delete(imgId);
          const tempRow = document.getElementById(`tempSyncRow_${{imgId}}`);
          if (tempRow) tempRow.remove();
          renderTemplatesGrid();
          status.style.color = 'var(--ps-yellow)';
          status.innerText = '⚠️ Template sync error: ' + err.message;
        }} finally {{
          adminUploadTplBtn.disabled = false;
          adminUploadTplBtn.innerHTML = origBtnHtml;
        }}
      }};
      reader.readAsDataURL(file);
    }};
  }}

  // Fruit face upload handler with live loading circle & syncing indicator
  document.getElementById('adminUploadBtn').onclick = () => {{
    const name = document.getElementById('adminNewFaceName').value.trim();
    const file = document.getElementById('adminNewFaceFile').files[0];
    const status = document.getElementById('adminUploadStatus');
    const uploadBtn = document.getElementById('adminUploadBtn');

    if (!name || !file) {{
      status.style.color = 'var(--ps-danger)';
      status.innerText = '⚠️ Please enter a fruit name and select an image.';
      return;
    }}

    uploadBtn.disabled = true;
    const origBtnHtml = uploadBtn.innerHTML;
    uploadBtn.innerHTML = '<span class="ps-spinner"></span> <span>Syncing to Cloud...</span>';

    status.style.color = 'var(--ps-blue)';
    status.innerHTML = '<span class="ps-spinner"></span> <span>Encoding and syncing to GitHub repo...</span>';

    const isGif = file.name.toLowerCase().endsWith('.gif') || file.type === 'image/gif';
    const reader = new FileReader();
    reader.onload = async (ev) => {{
      const b64 = ev.target.result;
      const ext = isGif ? '.gif' : (file.name.toLowerCase().endsWith('.webp') ? '.webp' : (file.name.toLowerCase().endsWith('.jpg') ? '.jpg' : '.png'));
      const imgId = name.toLowerCase().replace(/[^a-z0-9]/g, '_') + '_' + Date.now();
      const filename = name.toLowerCase().replace(/[^a-z0-9]/g, '_') + ext;

      // Show live loading placeholder card in faces grid
      uploadingItemIds.add(imgId);
      renderFacesGrid();

      // Show live uploading row in admin list
      const adminList = document.getElementById('adminFacesCatalogList');
      if (adminList) {{
        const syncRow = document.createElement('div');
        syncRow.id = `tempSyncRow_${{imgId}}`;
        syncRow.className = 'item-syncing-row';
        syncRow.innerHTML = `<div class="ps-spinner"></div> <span>Syncing "${{name}}" to Faces storage...</span>`;
        adminList.prepend(syncRow);
      }}

      try {{
        let uploadedFilename = filename;
        if (GITHUB_TOKEN) {{
          uploadedFilename = await syncFaceToGitHub(name, filename, b64);
        }}

        let parsedFrames = null;
        if (isGif) {{
          try {{
            const buf = await dataUriOrUrlToArrayBuffer(b64);
            parsedFrames = await parseGifFrames(buf);
          }} catch(err) {{}}
        }}

        const targetUpFile = uploadedFilename || filename;
        const upFaceFileLower = (targetUpFile || '').toLowerCase();
        const newFaceObj = {{
          id: imgId,
          name: name,
          file: targetUpFile,
          src: b64,
          isGif: isGif,
          gifFrames: parsedFrames
        }};
        const newImg = new Image();
        newImg.src = b64;
        newFaceObj.img = newImg;

        faces = faces.filter(f => f.id !== imgId && (f.file || '').toLowerCase() !== upFaceFileLower);
        faces.push(newFaceObj);
        faces = deduplicateFaces(faces);

        loadedFaces[imgId] = newImg;
        if (upFaceFileLower) loadedFaces[upFaceFileLower] = newImg;
        loadedFaces[faces.length - 1] = newImg;

        uploadingItemIds.delete(imgId);
        renderFacesGrid();
        renderAdminCatalog();

        status.style.color = 'var(--ps-green)';
        status.innerText = '✅ Fruit face successfully added & synced!';
        document.getElementById('adminNewFaceName').value = '';
        document.getElementById('adminNewFaceFile').value = '';
      }} catch (err) {{
        uploadingItemIds.delete(imgId);
        const tempRow = document.getElementById(`tempSyncRow_${{imgId}}`);
        if (tempRow) tempRow.remove();
        renderFacesGrid();
        status.style.color = 'var(--ps-yellow)';
        status.innerText = '⚠️ GitHub sync error: ' + err.message;
      }} finally {{
        uploadBtn.disabled = false;
        uploadBtn.innerHTML = origBtnHtml;
      }}
    }};
    reader.readAsDataURL(file);
  }};

  // --- RESET CANVAS ACTION ---
  document.getElementById('btnResetCanvas').onclick = () => {{
    if (state.facesOnCanvas.length > 0 || state.accessoriesOnCanvas.length > 0 || state.texts.length > 0 || state.bgType === 'custom') {{
      const confirmMsg = currentLang === 'ar' ? 'هل تريد بالتأكيد إعادة تعيين الكانفاس ومسح جميع الطبقات؟' : 'Reset canvas and clear all layers?';
      if (!confirm(confirmMsg)) return;
    }}
    state.facesOnCanvas = [];
    state.accessoriesOnCanvas = [];
    state.texts = [];
    state.selectedFaceIdx = -1;
    state.selectedAccIdx = -1;
    state.selectedTextIdx = -1;
    state.activeTransformTarget = null;

    state.bgType = 'template';
    state.bgTemplateId = 'suit';
    state.bgCustomImg = null;
    state.bgIsGif = false;
    state.bgGifFrames = [];
    state.bgGifIndex = 0;
    state.canvasSizeMode = 'true_size';
    state.bgFilters = makeDefaultFilters();
    state.animation = 'none';

    const animSelect = document.getElementById('animEffectSelect');
    if (animSelect) animSelect.value = 'none';
    const animBadge = document.getElementById('animActiveBadge');
    if (animBadge) animBadge.innerText = i18n[currentLang].animBadgeStill || 'Still';
    document.getElementById('activeTextInput').value = '';

    render();
    syncLayersUI();
    syncFilterUI();
    fitCanvasToScreen();
  }};

  // --- PRIVATE FACES VAULT UNLOCK & REMEMBER SYSTEM ---
  const vaultOverlay = document.getElementById('vaultGateOverlay');
  const facesGridEl = document.getElementById('facesGrid');
  const lockVaultBtn = document.getElementById('lockVaultBtn');
  const vaultPwdInput = document.getElementById('vaultPwdInput');
  const btnUnlockVault = document.getElementById('btnUnlockVault');
  const vaultErrorNotice = document.getElementById('vaultErrorNotice');

  async function unlockVaultUI(pwd, persist = true) {{
    try {{
      const decrypted = await decryptVault(pwd);
      if (faces && faces.length > 0) {{
        faces = deduplicateFaces([...decrypted, ...faces]);
      }} else {{
        faces = deduplicateFaces(decrypted);
      }}
      isVaultUnlocked = true;
      preloadFaces();
      if (vaultOverlay) vaultOverlay.style.display = 'none';
      if (facesGridEl) {{
        facesGridEl.style.filter = 'none';
        facesGridEl.style.opacity = '1.0';
        facesGridEl.style.pointerEvents = 'auto';
      }}
      if (lockVaultBtn) lockVaultBtn.style.display = 'inline-block';
      if (vaultErrorNotice) vaultErrorNotice.style.display = 'none';
      if (persist) {{
        try {{
          localStorage.setItem('frutisator_vault_pwd', pwd);
          localStorage.setItem('frutisator_vault_unlocked', 'true');
        }} catch(e) {{}}
      }}
      renderFacesGrid();
      syncCloudCatalog(false);
      return true;
    }} catch(err) {{
      if (vaultErrorNotice) vaultErrorNotice.style.display = 'block';
      return false;
    }}
  }}

  function lockVaultUI() {{
    isVaultUnlocked = false;
    faces = [];
    for (const k of Object.keys(loadedFaces)) {{
      delete loadedFaces[k];
    }}
    if (facesGridEl) {{
      facesGridEl.innerHTML = '';
      facesGridEl.style.filter = 'blur(7px)';
      facesGridEl.style.opacity = '0.25';
      facesGridEl.style.pointerEvents = 'none';
    }}
    if (vaultOverlay) vaultOverlay.style.display = 'flex';
    if (lockVaultBtn) lockVaultBtn.style.display = 'none';
    if (vaultPwdInput) vaultPwdInput.value = '';
    if (vaultErrorNotice) vaultErrorNotice.style.display = 'none';
    try {{
      localStorage.removeItem('frutisator_vault_pwd');
      localStorage.removeItem('frutisator_vault_unlocked');
    }} catch(e) {{}}
    render();
  }}

  async function attemptUnlockVault() {{
    const val = (vaultPwdInput.value || '').trim();
    if (!val) {{
      if (vaultErrorNotice) vaultErrorNotice.style.display = 'block';
      return;
    }}
    const origHtml = btnUnlockVault.innerHTML;
    btnUnlockVault.disabled = true;
    btnUnlockVault.innerHTML = '<span class="ps-spinner"></span>';
    const ok = await unlockVaultUI(val, true);
    btnUnlockVault.disabled = false;
    btnUnlockVault.innerHTML = origHtml;
  }}

  btnUnlockVault.onclick = attemptUnlockVault;
  vaultPwdInput.onkeydown = (e) => {{
    if (e.key === 'Enter') attemptUnlockVault();
  }};
  lockVaultBtn.onclick = lockVaultUI;

  // Restore saved states from localStorage
  try {{
    const savedVaultPwd = localStorage.getItem('frutisator_vault_pwd');
    const isUnlocked = localStorage.getItem('frutisator_vault_unlocked') === 'true';
    if (isUnlocked && savedVaultPwd) {{
      unlockVaultUI(savedVaultPwd, false);
    }} else {{
      lockVaultUI();
    }}
    const savedLang = localStorage.getItem('frutisator_lang');
    if (savedLang === 'ar') {{
      applyLanguage('ar');
    }}
  }} catch(e) {{
    lockVaultUI();
  }}

  fitCanvasToScreen();
  syncLayersUI();
  syncFilterUI();
}}

// Sync Admin Catalog List with Live Deletion & Renaming
function renderAdminCatalog() {{
  const list = document.getElementById('adminFacesCatalogList');
  if (!list) return;
  list.innerHTML = '';
  if (faces.length === 0) {{
    const emptyRow = document.createElement('div');
    emptyRow.style = 'color:var(--ps-text-muted); font-size:12px; text-align:center; padding:12px;';
    emptyRow.innerText = currentLang === 'ar' ? 'الكتالوج فارغ. أضف وجوه جديدة أعلاه!' : 'Catalog is empty. Add new fruit faces using the form above!';
    list.appendChild(emptyRow);
  }}
  faces.forEach((f, idx) => {{
    const isDeleting = deletingItemIds.has(f.id) || (f.file && deletingItemIds.has(f.file.toLowerCase()));
    const row = document.createElement('div');
    row.id = `adminFaceRow_${{idx}}`;
    row.style = 'display:flex; justify-content:space-between; align-items:center; background:#111217; padding:7px 10px; border-radius:6px; border:1px solid #1f2028; transition:all 0.2s ease;' + (isDeleting ? ' opacity:0.5;' : '');
    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0; overflow:hidden;">
        <img src="${{f.src}}" style="width:30px; height:30px; border-radius:4px; object-fit:cover; flex-shrink:0;">
        <span style="font-size:12.5px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" id="adminFaceName_${{idx}}" title="${{f.name}}">${{f.name}}</span>
      </div>
      <div style="display:flex; align-items:center; gap:5px; flex-shrink:0; margin-left:8px;">
        <button class="ps-opt-btn" id="adminFaceRenameBtn_${{idx}}" style="padding:4px 8px; font-size:11px; display:inline-flex; align-items:center; gap:4px;" ${{isDeleting ? 'disabled' : ''}} onclick="startRenameAdminFace(${{idx}})">
          <span>✏️</span> <span>${{currentLang === 'ar' ? 'تعديل' : 'Rename'}}</span>
        </button>
        <button class="ps-opt-btn danger" id="adminFaceDelBtn_${{idx}}" style="padding:4px 8px; font-size:11px; display:inline-flex; align-items:center; gap:5px;" ${{isDeleting ? 'disabled' : ''}} onclick="deleteAdminFace(${{idx}}, this)">
          ${{isDeleting ? '<span class="ps-spinner ps-spinner-danger"></span> <span>' + (currentLang === 'ar' ? 'جاري الحذف...' : 'Deleting...') + '</span>' : (currentLang === 'ar' ? 'حذف' : 'Remove')}}
        </button>
      </div>
    `;
    list.appendChild(row);
  }});
}}

window.startRenameAdminFace = function(idx) {{
  const f = faces[idx];
  if (!f) return;
  const row = document.getElementById(`adminFaceRow_${{idx}}`);
  if (!row) return;

  const currentName = f.name || '';
  row.innerHTML = `
    <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0; margin-right:8px;">
      <img src="${{f.src}}" style="width:30px; height:30px; border-radius:4px; object-fit:cover; flex-shrink:0;">
      <input type="text" class="ps-input" id="adminFaceRenameInput_${{idx}}" style="padding:4px 8px; font-size:12px; height:28px; width:100%; border-color:var(--ps-blue); background:#181920; color:#fff;" placeholder="${{currentLang === 'ar' ? 'اسم الفاكهة...' : 'Fruit Name...'}}">
    </div>
    <div style="display:flex; align-items:center; gap:5px; flex-shrink:0;">
      <button class="ps-opt-btn primary" id="adminFaceSaveBtn_${{idx}}" style="padding:4px 8px; font-size:11px; display:inline-flex; align-items:center; gap:4px; background:var(--ps-blue); border-color:var(--ps-blue); color:#fff;" onclick="saveRenameAdminFace(${{idx}})">
        <span>💾</span> <span>${{currentLang === 'ar' ? 'حفظ' : 'Save'}}</span>
      </button>
      <button class="ps-opt-btn" id="adminFaceCancelBtn_${{idx}}" style="padding:4px 8px; font-size:11px;" onclick="renderAdminCatalog()">
        ${{currentLang === 'ar' ? 'إلغاء' : 'Cancel'}}
      </button>
    </div>
  `;

  const input = document.getElementById(`adminFaceRenameInput_${{idx}}`);
  if (input) {{
    input.value = currentName;
    input.focus();
    input.select();
    input.onkeydown = (e) => {{
      if (e.key === 'Enter') saveRenameAdminFace(idx);
      if (e.key === 'Escape') renderAdminCatalog();
    }};
  }}
}};

window.saveRenameAdminFace = async function(idx) {{
  const f = faces[idx];
  if (!f) return;
  const input = document.getElementById(`adminFaceRenameInput_${{idx}}`);
  if (!input) return;
  const newName = input.value.trim();
  if (!newName) {{
    input.style.borderColor = 'var(--ps-danger)';
    input.focus();
    return;
  }}
  const oldName = f.name;
  if (newName === oldName) {{
    renderAdminCatalog();
    return;
  }}

  const saveBtn = document.getElementById(`adminFaceSaveBtn_${{idx}}`);
  const cancelBtn = document.getElementById(`adminFaceCancelBtn_${{idx}}`);
  if (saveBtn) {{
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="ps-spinner ps-spinner-sm"></span> <span>${{currentLang === 'ar' ? 'جاري الحفظ...' : 'Saving...'}}</span>`;
  }}
  if (cancelBtn) cancelBtn.disabled = true;
  input.disabled = true;

  const status = document.getElementById('adminFacesCatalogStatus');
  if (status) {{
    status.style.color = 'var(--ps-blue)';
    status.innerHTML = `<span class="ps-spinner ps-spinner-sm"></span> <span>${{currentLang === 'ar' ? 'جاري حفظ الاسم في السحابة...' : 'Saving face name to cloud storage...'}}</span>`;
  }}

  try {{
    if (GITHUB_TOKEN) {{
      const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
      const folder = 'Faces';
      const manifestPath = `${{folder}}/manifest.json`;
      const branch = 'main';
      const targetFileLower = (f.file || f.filename || '').toLowerCase();
      const faceId = f.id;

      let manifestUpdated = false;
      for (let attempt = 0; attempt < 3; attempt++) {{
        try {{
          const mRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}?ref=${{branch}}&_t=${{Date.now()}}`, {{
            headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
          }});
          if (mRes.ok) {{
            const mData = await mRes.json();
            const decoded = decodeURIComponent(escape(atob(mData.content.replace(/\\s/g, ''))));
            let manifestList = JSON.parse(decoded);
            let found = false;
            for (const item of manifestList) {{
              const ifile = (item.file || item.filename || '').toLowerCase();
              if ((faceId && item.id === faceId) || (targetFileLower && ifile === targetFileLower)) {{
                item.name = newName;
                found = true;
                break;
              }}
            }}
            if (!found) {{
              manifestList.push({{
                id: faceId || ('face_' + Date.now()),
                name: newName,
                file: f.file || (newName.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png')
              }});
            }}
            const updatedB64 = btoa(unescape(encodeURIComponent(JSON.stringify(manifestList, null, 2))));
            const putRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}`, {{
              method: 'PUT',
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{
                message: `Rename face: "${{oldName}}" -> "${{newName}}"`,
                content: updatedB64,
                sha: mData.sha,
                branch: branch
              }})
            }});
            if (putRes.ok) {{
              manifestUpdated = true;
              break;
            }}
          }}
        }} catch (err) {{
          if (attempt === 2) throw err;
        }}
      }}
      if (!manifestUpdated) {{
        throw new Error('Failed to update Faces/manifest.json on GitHub');
      }}
    }}

    // Update in-memory state
    f.name = newName;

    // Update any canvas layer referencing this face
    state.facesOnCanvas.forEach(fc => {{
      if ((fc.faceId && fc.faceId === f.id) || (fc.faceFile && f.file && fc.faceFile.toLowerCase() === f.file.toLowerCase()) || fc.faceIndex === idx) {{
        fc.customName = newName;
      }}
    }});

    syncLayersUI();
    renderFacesGrid();
    renderAdminCatalog();

    if (status) {{
      status.style.color = 'var(--ps-green)';
      status.innerText = currentLang === 'ar' ? `✅ تم تغيير الاسم إلى "${{newName}}" بنجاح!` : `✅ Face renamed to "${{newName}}" successfully!`;
      setTimeout(() => {{
        if (status.innerText.includes(newName)) status.innerText = '';
      }}, 4000);
    }}
  }} catch (err) {{
    console.error('Rename error:', err);
    if (status) {{
      status.style.color = 'var(--ps-danger)';
      status.innerText = (currentLang === 'ar' ? '❌ خطأ أثناء تعديل الاسم: ' : '❌ Error renaming face: ') + err.message;
    }}
    if (saveBtn) {{
      saveBtn.disabled = false;
      saveBtn.innerHTML = `<span>💾</span> <span>${{currentLang === 'ar' ? 'حفظ' : 'Save'}}</span>`;
    }}
    if (cancelBtn) cancelBtn.disabled = false;
    input.disabled = false;
  }}
}};

window.deleteAdminFace = async function(idx, btn) {{
  const f = faces[idx];
  if (!f) return;
  const targetFile = f.file || f.filename || '';
  const targetFileLower = targetFile.toLowerCase();
  const faceId = f.id || ('face_' + idx);
  const faceName = f.name || targetFile;

  const status = document.getElementById('adminFacesCatalogStatus');
  if (status) {{
    status.style.color = 'var(--ps-blue)';
    status.innerHTML = `<span class="ps-spinner ps-spinner-sm"></span> <span>` + (currentLang === 'ar' ? 'جاري حذف ' + faceName + ' من التخزين السحابي...' : 'Deleting "' + faceName + '" from cloud storage...') + `</span>`;
  }}

  // 1. Show immediate loading feedback on button and row
  if (btn) {{
    btn.disabled = true;
    btn.innerHTML = '<span class="ps-spinner ps-spinner-danger"></span> <span>' + (currentLang === 'ar' ? 'جاري الحذف...' : 'Deleting...') + '</span>';
  }}
  const row = document.getElementById(`adminFaceRow_${{idx}}`);
  if (row) row.style.opacity = '0.5';

  deletingItemIds.add(faceId);
  if (targetFileLower) deletingItemIds.add(targetFileLower);
  renderFacesGrid();

  const syncSpinner = document.getElementById('cloudSyncSpinner');
  const syncLabel = document.getElementById('cloudSyncLabel');
  if (syncSpinner) syncSpinner.style.display = 'inline-block';
  if (syncLabel) syncLabel.innerText = currentLang === 'ar' ? '☁️ حذف من السحابة...' : '☁️ Deleting...';

  try {{
    if (GITHUB_TOKEN) {{
      const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
      const folder = 'Faces'; // Always exact 'Faces' casing
      const manifestPath = `${{folder}}/manifest.json`;

      // Step A: Find matching file by live directory listing and DELETE it
      if (targetFileLower) {{
        const listRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}?ref=main&_t=${{Date.now()}}`, {{
          headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
        }});
        if (listRes.ok) {{
          const folderFiles = await listRes.json();
          const matchingFile = folderFiles.find(item => (item.name || '').toLowerCase() === targetFileLower);
          if (matchingFile && matchingFile.sha) {{
            const delRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}/${{encodeURIComponent(matchingFile.name)}}`, {{
              method: 'DELETE',
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ message: 'Delete face file: ' + faceName, sha: matchingFile.sha, branch: 'main' }})
            }});
            if (!delRes.ok) {{
              const errObj = await delRes.json().catch(() => ({{}}));
              console.warn('Physical face file deletion warning:', errObj);
            }}
          }}
        }} else {{
          const errObj = await listRes.json().catch(() => ({{}}));
          throw new Error('Could not access Faces folder: ' + (errObj.message || listRes.status));
        }}
      }}

      // Step B: Update manifest.json with retry
      let manifestUpdated = false;
      for (let attempt = 0; attempt < 3; attempt++) {{
        try {{
          const mRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}?ref=main&_t=${{Date.now()}}`, {{
            headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
          }});
          if (mRes.ok) {{
            const mData = await mRes.json();
            const decoded = decodeURIComponent(escape(atob(mData.content.replace(/\s/g, ''))));
            let manifestList = JSON.parse(decoded);
            manifestList = manifestList.filter(item => {{
              const ifile = (item.file || item.filename || '').toLowerCase();
              return item.id !== faceId && ifile !== targetFileLower;
            }});
            const updatedB64 = btoa(unescape(encodeURIComponent(JSON.stringify(manifestList, null, 2))));
            const putRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}`, {{
              method: 'PUT',
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ message: 'Remove face from manifest: ' + faceName, content: updatedB64, sha: mData.sha, branch: 'main' }})
            }});
            if (putRes.ok) {{
              manifestUpdated = true;
              break;
            }}
          }}
        }} catch (manErr) {{
          if (attempt === 2) throw manErr;
        }}
      }}
      if (!manifestUpdated) {{
        throw new Error('Could not update Faces/manifest.json on GitHub');
      }}
    }}

    // Step C: Clean up local array & state
    const removeIdx = faces.findIndex(item => item.id === faceId || (item.file && item.file.toLowerCase() === targetFileLower));
    const finalIdx = removeIdx !== -1 ? removeIdx : idx;

    faces = faces.filter(item => {{
      if (faceId && item.id === faceId) return false;
      if (targetFileLower && (item.file || '').toLowerCase() === targetFileLower) return false;
      return true;
    }});
    faces = deduplicateFaces(faces);

    delete loadedFaces[faceId];
    if (targetFileLower) delete loadedFaces[targetFileLower];
    delete loadedFaces[finalIdx];

    for (const k of Object.keys(loadedFaces)) {{
      delete loadedFaces[k];
    }}
    faces.forEach((item, i) => {{
      if (item.src) {{
        const img = (item.img && item.img.complete) ? item.img : new Image();
        if (!img.src) img.src = item.src;
        item.img = img;
        loadedFaces[item.id] = img;
        if (item.file) loadedFaces[item.file.toLowerCase()] = img;
        loadedFaces[i] = img;
      }}
    }});

    state.facesOnCanvas = state.facesOnCanvas.filter(fc => {{
      if (faceId && fc.faceId === faceId) return false;
      if (targetFileLower && fc.faceFile && fc.faceFile.toLowerCase() === targetFileLower) return false;
      if (fc.faceIndex === finalIdx) return false;
      return true;
    }});
    state.facesOnCanvas.forEach(fc => {{
      const matchIdx = faces.findIndex(f => (fc.faceId && f.id === fc.faceId) || (fc.faceFile && f.file && f.file.toLowerCase() === fc.faceFile.toLowerCase()));
      if (matchIdx !== -1) fc.faceIndex = matchIdx;
      else if (fc.faceIndex > finalIdx) fc.faceIndex -= 1;
    }});
    if (state.activeTransformTarget && !state.facesOnCanvas.includes(state.activeTransformTarget)) {{
      state.activeTransformTarget = null;
    }}

    if (targetFileLower) deletedItemFiles.add(targetFileLower);
    if (faceId) deletedItemFiles.add(faceId.toLowerCase());

    if (status) {{
      status.style.color = 'var(--ps-green)';
      status.innerText = currentLang === 'ar' ? '✅ تم حذف "' + faceName + '" بنجاح من التخزين!' : '✅ "' + faceName + '" permanently deleted from storage!';
      setTimeout(() => {{ if (status) status.innerText = ''; }}, 5000);
    }}

  }} catch (err) {{
    console.error('Delete face error:', err);
    if (status) {{
      status.style.color = 'var(--ps-danger)';
      status.innerText = '❌ ' + (err.message || 'Error deleting from storage');
    }}
    if (btn) {{
      btn.disabled = false;
      btn.innerText = currentLang === 'ar' ? 'حذف' : 'Remove';
    }}
    if (row) row.style.opacity = '1.0';
  }} finally {{
    deletingItemIds.delete(faceId);
    if (targetFileLower) deletingItemIds.delete(targetFileLower);

    if (syncSpinner) syncSpinner.style.display = 'none';
    if (syncLabel) syncLabel.innerText = currentLang === 'ar' ? '☁️ متزامن' : '☁️ Synced';

    renderFacesGrid();
    renderAdminCatalog();
    syncLayersUI();
    updateDynamicFileName();
    render();
  }}
}};

// --- ROBUST REMOTE MANIFEST SYNC WITH CONFLICT RETRY & SELF-HEALING ---
async function updateRemoteManifestWithRetry(folder, newItem, maxRetries = 3) {{
  const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
  const branch = 'main';
  const manifestPath = `${{folder}}/manifest.json`;

  for (let attempt = 0; attempt < maxRetries; attempt++) {{
    try {{
      // 1. Fetch latest manifest with cache-busting timestamp
      let manifestList = [];
      let manifestSha = null;
      const mRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}?ref=${{branch}}&_t=${{Date.now()}}`, {{
        headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
      }});
      if (mRes.ok) {{
        const mData = await mRes.json();
        manifestSha = mData.sha;
        const decoded = decodeURIComponent(escape(atob(mData.content.replace(/\\s/g, ''))));
        manifestList = JSON.parse(decoded);
      }}

      // 3. Merge or remove newItem
      if (newItem) {{
        manifestList = manifestList.filter(item => item.file !== newItem.file && item.id !== newItem.id);
        manifestList.push(newItem);
      }}

      // 4. PUT updated manifest to GitHub
      const updatedB64 = btoa(unescape(encodeURIComponent(JSON.stringify(manifestList, null, 2))));
      const putBody = {{
        message: 'Sync ' + manifestPath + (newItem ? (' for ' + newItem.name) : ' (self-healing auto-repair)'),
        content: updatedB64,
        branch: branch
      }};
      if (manifestSha) putBody.sha = manifestSha;

      const putRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}`, {{
        method: 'PUT',
        headers: {{
          'Authorization': 'Bearer ' + GITHUB_TOKEN,
          'Content-Type': 'application/json'
        }},
        body: JSON.stringify(putBody)
      }});

      if (putRes.ok) {{
        return manifestList;
      }}

      if (putRes.status === 409 && attempt < maxRetries - 1) {{
        // SHA conflict: wait and retry with fresh SHA
        await new Promise(r => setTimeout(r, 400 * (attempt + 1)));
        continue;
      }}

      const errData = await putRes.json().catch(() => ({{}}));
      throw new Error(errData.message || ('Manifest update HTTP ' + putRes.status));
    }} catch (err) {{
      if (attempt >= maxRetries - 1) throw err;
      await new Promise(r => setTimeout(r, 400));
    }}
  }}
}}

// GitHub API template sync helper
async function syncTemplateToGitHub(tplName, filename, base64Data) {{
  const cleanB64 = base64Data.split(',')[1];
  const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
  const folder = 'Templates';
  const branch = 'main';

  // 1. Check existing files in Templates/
  let existingFiles = [];
  try {{
    const listRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}?ref=${{branch}}`, {{
      headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
    }});
    if (listRes.ok) existingFiles = await listRes.json();
  }} catch (e) {{}}

  // 2. Duplicate avoidance
  const existingNames = new Set(existingFiles.map(f => (f.name || '').toLowerCase()));
  let uniqueFilename = filename;
  const dotIdx = filename.lastIndexOf('.');
  const baseName = dotIdx !== -1 ? filename.substring(0, dotIdx) : filename;
  const ext = dotIdx !== -1 ? filename.substring(dotIdx) : '';
  let counter = 1;
  while (existingNames.has(uniqueFilename.toLowerCase())) {{
    uniqueFilename = `${{baseName}}_${{counter}}${{ext}}`;
    counter++;
  }}

  // 3. Upload image
  const filePutUrl = `https://api.github.com/repos/${{repo}}/contents/${{folder}}/${{uniqueFilename}}`;
  const filePutRes = await fetch(filePutUrl, {{
    method: 'PUT',
    headers: {{
      'Authorization': 'Bearer ' + GITHUB_TOKEN,
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify({{
      message: 'Add template image: ' + uniqueFilename,
      content: cleanB64,
      branch: branch
    }})
  }});
  if (!filePutRes.ok) {{
    const errObj = await filePutRes.json().catch(() => ({{}}));
    throw new Error(errObj.message || ('Upload failed with HTTP ' + filePutRes.status));
  }}

  // 4. Update Templates/manifest.json with conflict retry
  const tplId = 'tpl_' + Date.now();
  await updateRemoteManifestWithRetry('Templates', {{
    id: tplId,
    name: tplName,
    file: uniqueFilename
  }});

  return {{ id: tplId, name: tplName, file: uniqueFilename }};
}}

function renderAdminTemplatesCatalog() {{
  const list = document.getElementById('adminTemplatesCatalogList');
  if (!list) return;
  list.innerHTML = '';
  if (templates.length === 0) {{
    const emptyRow = document.createElement('div');
    emptyRow.style = 'color:var(--ps-text-muted); font-size:12px; text-align:center; padding:12px;';
    emptyRow.innerText = currentLang === 'ar' ? 'كتالوج القوالب فارغ. أضف قوالب جديدة أعلاه!' : 'Templates catalog is empty. Add new templates using the form above!';
    list.appendChild(emptyRow);
  }}
  templates.forEach((t, idx) => {{
    const isDeleting = deletingItemIds.has(t.id) || (t.file && deletingItemIds.has(t.file.toLowerCase()));
    const row = document.createElement('div');
    row.id = `adminTplRow_${{idx}}`;
    row.style = 'display:flex; justify-content:space-between; align-items:center; background:#111217; padding:7px 10px; border-radius:6px; border:1px solid #1f2028; transition:all 0.2s ease;' + (isDeleting ? ' opacity:0.5;' : '');
    row.innerHTML = `
      <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0; overflow:hidden;">
        <img src="${{t.src}}" style="width:30px; height:30px; border-radius:4px; object-fit:cover; flex-shrink:0;">
        <span style="font-size:12.5px; font-weight:700; color:#fff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;" id="adminTplName_${{idx}}" title="${{t.name}}">${{t.name}}</span>
      </div>
      <div style="display:flex; align-items:center; gap:5px; flex-shrink:0; margin-left:8px;">
        <button class="ps-opt-btn" id="adminTplRenameBtn_${{idx}}" style="padding:4px 8px; font-size:11px; display:inline-flex; align-items:center; gap:4px;" ${{isDeleting ? 'disabled' : ''}} onclick="startRenameAdminTemplate(${{idx}})">
          <span>✏️</span> <span>${{currentLang === 'ar' ? 'تعديل' : 'Rename'}}</span>
        </button>
        <button class="ps-opt-btn danger" id="adminTplDelBtn_${{idx}}" style="padding:4px 8px; font-size:11px; display:inline-flex; align-items:center; gap:5px;" ${{isDeleting ? 'disabled' : ''}} onclick="deleteAdminTemplate(${{idx}}, this)">
          ${{isDeleting ? '<span class="ps-spinner ps-spinner-danger"></span> <span>' + (currentLang === 'ar' ? 'جاري الحذف...' : 'Deleting...') + '</span>' : (currentLang === 'ar' ? 'حذف' : 'Remove')}}
        </button>
      </div>
    `;
    list.appendChild(row);
  }});
}}

window.startRenameAdminTemplate = function(idx) {{
  const t = templates[idx];
  if (!t) return;
  const row = document.getElementById(`adminTplRow_${{idx}}`);
  if (!row) return;

  const currentName = t.name || '';
  row.innerHTML = `
    <div style="display:flex; align-items:center; gap:8px; flex:1; min-width:0; margin-right:8px;">
      <img src="${{t.src}}" style="width:30px; height:30px; border-radius:4px; object-fit:cover; flex-shrink:0;">
      <input type="text" class="ps-input" id="adminTplRenameInput_${{idx}}" style="padding:4px 8px; font-size:12px; height:28px; width:100%; border-color:var(--ps-blue); background:#181920; color:#fff;" placeholder="${{currentLang === 'ar' ? 'اسم القالب...' : 'Template Name...'}}">
    </div>
    <div style="display:flex; align-items:center; gap:5px; flex-shrink:0;">
      <button class="ps-opt-btn primary" id="adminTplSaveBtn_${{idx}}" style="padding:4px 8px; font-size:11px; display:inline-flex; align-items:center; gap:4px; background:var(--ps-blue); border-color:var(--ps-blue); color:#fff;" onclick="saveRenameAdminTemplate(${{idx}})">
        <span>💾</span> <span>${{currentLang === 'ar' ? 'حفظ' : 'Save'}}</span>
      </button>
      <button class="ps-opt-btn" id="adminTplCancelBtn_${{idx}}" style="padding:4px 8px; font-size:11px;" onclick="renderAdminTemplatesCatalog()">
        ${{currentLang === 'ar' ? 'إلغاء' : 'Cancel'}}
      </button>
    </div>
  `;

  const input = document.getElementById(`adminTplRenameInput_${{idx}}`);
  if (input) {{
    input.value = currentName;
    input.focus();
    input.select();
    input.onkeydown = (e) => {{
      if (e.key === 'Enter') saveRenameAdminTemplate(idx);
      if (e.key === 'Escape') renderAdminTemplatesCatalog();
    }};
  }}
}};

window.saveRenameAdminTemplate = async function(idx) {{
  const t = templates[idx];
  if (!t) return;
  const input = document.getElementById(`adminTplRenameInput_${{idx}}`);
  if (!input) return;
  const newName = input.value.trim();
  if (!newName) {{
    input.style.borderColor = 'var(--ps-danger)';
    input.focus();
    return;
  }}
  const oldName = t.name;
  if (newName === oldName) {{
    renderAdminTemplatesCatalog();
    return;
  }}

  const saveBtn = document.getElementById(`adminTplSaveBtn_${{idx}}`);
  const cancelBtn = document.getElementById(`adminTplCancelBtn_${{idx}}`);
  if (saveBtn) {{
    saveBtn.disabled = true;
    saveBtn.innerHTML = `<span class="ps-spinner ps-spinner-sm"></span> <span>${{currentLang === 'ar' ? 'جاري الحفظ...' : 'Saving...'}}</span>`;
  }}
  if (cancelBtn) cancelBtn.disabled = true;
  input.disabled = true;

  const status = document.getElementById('adminTplCatalogStatus');
  if (status) {{
    status.style.color = 'var(--ps-blue)';
    status.innerHTML = `<span class="ps-spinner ps-spinner-sm"></span> <span>${{currentLang === 'ar' ? 'جاري حفظ اسم القالب في السحابة...' : 'Saving template name to cloud storage...'}}</span>`;
  }}

  try {{
    if (GITHUB_TOKEN) {{
      const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
      const folder = 'Templates';
      const manifestPath = `${{folder}}/manifest.json`;
      const branch = 'main';
      const targetFileLower = (t.file || t.filename || '').toLowerCase();
      const tplId = t.id;

      let manifestUpdated = false;
      for (let attempt = 0; attempt < 3; attempt++) {{
        try {{
          const mRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}?ref=${{branch}}&_t=${{Date.now()}}`, {{
            headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
          }});
          if (mRes.ok) {{
            const mData = await mRes.json();
            const decoded = decodeURIComponent(escape(atob(mData.content.replace(/\\s/g, ''))));
            let manifestList = JSON.parse(decoded);
            let found = false;
            for (const item of manifestList) {{
              const ifile = (item.file || item.filename || '').toLowerCase();
              if ((tplId && item.id === tplId) || (targetFileLower && ifile === targetFileLower)) {{
                item.name = newName;
                found = true;
                break;
              }}
            }}
            if (!found) {{
              manifestList.push({{
                id: tplId || ('tpl_' + Date.now()),
                name: newName,
                file: t.file || (newName.toLowerCase().replace(/[^a-z0-9]/g, '_') + '.png')
              }});
            }}
            const updatedB64 = btoa(unescape(encodeURIComponent(JSON.stringify(manifestList, null, 2))));
            const putRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}`, {{
              method: 'PUT',
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{
                message: `Rename template: "${{oldName}}" -> "${{newName}}"`,
                content: updatedB64,
                sha: mData.sha,
                branch: branch
              }})
            }});
            if (putRes.ok) {{
              manifestUpdated = true;
              break;
            }}
          }}
        }} catch (err) {{
          if (attempt === 2) throw err;
        }}
      }}
      if (!manifestUpdated) {{
        throw new Error('Failed to update Templates/manifest.json on GitHub');
      }}
    }}

    t.name = newName;
    renderTemplatesGrid();
    renderAdminTemplatesCatalog();

    if (status) {{
      status.style.color = 'var(--ps-green)';
      status.innerText = currentLang === 'ar' ? `✅ تم تغيير اسم القالب إلى "${{newName}}" بنجاح!` : `✅ Template renamed to "${{newName}}" successfully!`;
      setTimeout(() => {{
        if (status.innerText.includes(newName)) status.innerText = '';
      }}, 4000);
    }}
  }} catch (err) {{
    console.error('Template rename error:', err);
    if (status) {{
      status.style.color = 'var(--ps-danger)';
      status.innerText = (currentLang === 'ar' ? '❌ خطأ أثناء تعديل الاسم: ' : '❌ Error renaming template: ') + err.message;
    }}
    if (saveBtn) {{
      saveBtn.disabled = false;
      saveBtn.innerHTML = `<span>💾</span> <span>${{currentLang === 'ar' ? 'حفظ' : 'Save'}}</span>`;
    }}
    if (cancelBtn) cancelBtn.disabled = false;
    input.disabled = false;
  }}
}};

window.deleteAdminTemplate = async function(idx, btn) {{
  const t = templates[idx];
  if (!t) return;
  const targetFile = t.file || t.filename || '';
  const targetFileLower = targetFile.toLowerCase();
  const tplId = t.id || ('tpl_' + idx);
  const tplName = t.name || targetFile;

  const status = document.getElementById('adminTplCatalogStatus');
  if (status) {{
    status.style.color = 'var(--ps-blue)';
    status.innerHTML = `<span class="ps-spinner ps-spinner-sm"></span> <span>` + (currentLang === 'ar' ? 'جاري حذف ' + tplName + ' من السحابة...' : 'Deleting "' + tplName + '" from cloud storage...') + `</span>`;
  }}

  // 1. Show immediate loading feedback on button and row
  if (btn) {{
    btn.disabled = true;
    btn.innerHTML = '<span class="ps-spinner ps-spinner-danger"></span> <span>' + (currentLang === 'ar' ? 'جاري الحذف...' : 'Deleting...') + '</span>';
  }}
  const row = document.getElementById(`adminTplRow_${{idx}}`);
  if (row) row.style.opacity = '0.5';

  deletingItemIds.add(tplId);
  if (targetFileLower) deletingItemIds.add(targetFileLower);
  renderTemplatesGrid();

  const syncSpinner = document.getElementById('cloudSyncSpinner');
  const syncLabel = document.getElementById('cloudSyncLabel');
  if (syncSpinner) syncSpinner.style.display = 'inline-block';
  if (syncLabel) syncLabel.innerText = currentLang === 'ar' ? '☁️ حذف من السحابة...' : '☁️ Deleting...';

  try {{
    if (GITHUB_TOKEN) {{
      const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
      const folder = 'Templates'; // Always exact 'Templates' casing
      const manifestPath = `${{folder}}/manifest.json`;

      // Step A: Find matching file by live directory listing and DELETE it
      if (targetFileLower) {{
        const listRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}?ref=main&_t=${{Date.now()}}`, {{
          headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
        }});
        if (listRes.ok) {{
          const folderFiles = await listRes.json();
          const matchingFile = folderFiles.find(item => (item.name || '').toLowerCase() === targetFileLower);
          if (matchingFile && matchingFile.sha) {{
            const delRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}/${{encodeURIComponent(matchingFile.name)}}`, {{
              method: 'DELETE',
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ message: 'Delete template file: ' + tplName, sha: matchingFile.sha, branch: 'main' }})
            }});
            if (!delRes.ok) {{
              const errObj = await delRes.json().catch(() => ({{}}));
              console.warn('Physical template file deletion warning:', errObj);
            }}
          }}
        }} else {{
          const errObj = await listRes.json().catch(() => ({{}}));
          throw new Error('Could not access Templates folder: ' + (errObj.message || listRes.status));
        }}
      }}

      // Step B: Update manifest.json with retry
      let manifestUpdated = false;
      for (let attempt = 0; attempt < 3; attempt++) {{
        try {{
          const mRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}?ref=main&_t=${{Date.now()}}`, {{
            headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
          }});
          if (mRes.ok) {{
            const mData = await mRes.json();
            const decoded = decodeURIComponent(escape(atob(mData.content.replace(/\s/g, ''))));
            let manifestList = JSON.parse(decoded);
            manifestList = manifestList.filter(item => {{
              const ifile = (item.file || item.filename || '').toLowerCase();
              return item.id !== tplId && ifile !== targetFileLower;
            }});
            const updatedB64 = btoa(unescape(encodeURIComponent(JSON.stringify(manifestList, null, 2))));
            const putRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{manifestPath}}`, {{
              method: 'PUT',
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN, 'Content-Type': 'application/json' }},
              body: JSON.stringify({{ message: 'Remove template from manifest: ' + tplName, content: updatedB64, sha: mData.sha, branch: 'main' }})
            }});
            if (putRes.ok) {{
              manifestUpdated = true;
              break;
            }}
          }}
        }} catch (manErr) {{
          if (attempt === 2) throw manErr;
        }}
      }}
      if (!manifestUpdated) {{
        throw new Error('Could not update Templates/manifest.json on GitHub');
      }}
    }}

    // 3. Clean up local state
    templates = templates.filter(item => {{
      if (tplId && item.id === tplId) return false;
      if (targetFileLower && (item.file || item.filename || '').toLowerCase() === targetFileLower) return false;
      return true;
    }});
    templates = deduplicateTemplates(templates);

    delete loadedTemplates[tplId];
    if (targetFileLower) delete loadedTemplates[targetFileLower];

    if (state.bgType === 'template' && (state.bgTemplateId === tplId || (targetFileLower && String(state.bgTemplateId).toLowerCase() === targetFileLower))) {{
      state.bgType = 'color';
      state.bgTemplateId = null;
      state.bgCustomImg = null;
      state.bgIsGif = false;
      state.bgGifFrames = [];
    }}

    if (targetFileLower) deletedItemFiles.add(targetFileLower);
    if (tplId) deletedItemFiles.add(tplId.toLowerCase());

    if (status) {{
      status.style.color = 'var(--ps-green)';
      status.innerText = currentLang === 'ar' ? '✅ تم حذف "' + tplName + '" بنجاح من التخزين!' : '✅ "' + tplName + '" permanently deleted from storage!';
      setTimeout(() => {{ if (status) status.innerText = ''; }}, 5000);
    }}

  }} catch (err) {{
    console.error('Delete template error:', err);
    if (status) {{
      status.style.color = 'var(--ps-danger)';
      status.innerText = '❌ ' + (err.message || 'Error deleting from storage');
    }}
    if (btn) {{
      btn.disabled = false;
      btn.innerText = currentLang === 'ar' ? 'حذف' : 'Remove';
    }}
    if (row) row.style.opacity = '1.0';
  }} finally {{
    deletingItemIds.delete(tplId);
    if (targetFileLower) deletingItemIds.delete(targetFileLower);

    if (syncSpinner) syncSpinner.style.display = 'none';
    if (syncLabel) syncLabel.innerText = currentLang === 'ar' ? '☁️ متزامن' : '☁️ Synced';

    renderTemplatesGrid();
    renderAdminTemplatesCatalog();
    syncLayersUI();
    updateDynamicFileName();
    render();
  }}
}};

// GitHub API face sync helper
async function syncFaceToGitHub(faceName, filename, base64Data) {{
  const cleanB64 = base64Data.split(',')[1];
  const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
  const folder = 'Faces';
  const branch = 'main';

  // 1. Fetch current folder contents to check duplicate filenames
  let existingFiles = [];
  try {{
    const listRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}?ref=${{branch}}`, {{
      headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
    }});
    if (listRes.ok) {{
      existingFiles = await listRes.json();
    }}
  }} catch (e) {{}}

  // 2. Duplicate avoidance
  const existingNames = new Set(existingFiles.map(f => (f.name || '').toLowerCase()));
  let uniqueFilename = filename;
  const dotIdx = filename.lastIndexOf('.');
  const baseName = dotIdx !== -1 ? filename.substring(0, dotIdx) : filename;
  const ext = dotIdx !== -1 ? filename.substring(dotIdx) : '';
  let counter = 1;
  while (existingNames.has(uniqueFilename.toLowerCase())) {{
    uniqueFilename = `${{baseName}}_${{counter}}${{ext}}`;
    counter++;
  }}

  // 3. Upload the image file
  const filePutUrl = `https://api.github.com/repos/${{repo}}/contents/${{folder}}/${{uniqueFilename}}`;
  const filePutRes = await fetch(filePutUrl, {{
    method: 'PUT',
    headers: {{
      'Authorization': 'Bearer ' + GITHUB_TOKEN,
      'Content-Type': 'application/json',
    }},
    body: JSON.stringify({{
      message: 'Add face image: ' + uniqueFilename,
      content: cleanB64,
      branch: branch
    }})
  }});
  if (!filePutRes.ok) {{
    const errObj = await filePutRes.json().catch(() => ({{}}));
    throw new Error(errObj.message || ('Upload failed with HTTP ' + filePutRes.status));
  }}

  // 4. Update manifest.json with conflict retry
  const faceId = 'face_' + Date.now();
  await updateRemoteManifestWithRetry(folder, {{
    id: faceId,
    name: faceName,
    file: uniqueFilename
  }});

  return uniqueFilename;
}}

// LIVE CLOUD CATALOG SYNC (Real-time updates for all users on website)
let isSyncingCatalog = false;
async function syncCloudCatalog(showNotice = false) {{
  if (isSyncingCatalog || !GITHUB_TOKEN) return;
  isSyncingCatalog = true;

  const repo = GITHUB_REPO || 'Aboodi-8/Muradeditorstorage';
  const folder = 'Faces';

  const syncSpinner = document.getElementById('cloudSyncSpinner');
  const syncLabel = document.getElementById('cloudSyncLabel');
  if (syncSpinner) syncSpinner.style.display = 'inline-block';
  if (syncLabel) syncLabel.innerText = currentLang === 'ar' ? 'جاري المزامنة...' : 'Syncing...';

  // 1. Sync Faces from Cloud (ONLY IF VAULT IS UNLOCKED)
  if (isVaultUnlocked) {{
    try {{
      const mRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}/manifest.json?_t=${{Date.now()}}`, {{
        headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
      }});
    if (mRes.ok) {{
      const mData = await mRes.json();
      const decoded = decodeURIComponent(escape(atob(mData.content.replace(/\\s/g, ''))));
      const cloudFaces = JSON.parse(decoded);

      const existingFiles = new Set(faces.map(f => (f.file || f.filename || '').toLowerCase()).filter(Boolean));
      const existingIds = new Set(faces.map(f => (f.id || '').toLowerCase()).filter(Boolean));
      let newFacesAdded = false;

      for (const cf of cloudFaces) {{
        const cfile = cf.file || cf.filename;
        if (!cfile) continue;
        const cfileLower = cfile.toLowerCase();
        const cidLower = (cf.id || '').toLowerCase();
        // NEVER resurrect files that were deleted or are actively deleting in this session
        if (deletedItemFiles.has(cfileLower) || deletingItemIds.has(cfileLower) || (cf.id && deletingItemIds.has(cf.id))) continue;

        // If face already exists in memory, sync updated name from cloud manifest
        const existingFace = faces.find(f => (cidLower && (f.id || '').toLowerCase() === cidLower) || (cfileLower && (f.file || '').toLowerCase() === cfileLower));
        if (existingFace) {{
          if (cf.name && existingFace.name !== cf.name) {{
            existingFace.name = cf.name;
            state.facesOnCanvas.forEach(fc => {{
              if ((fc.faceId && fc.faceId === existingFace.id) || (fc.faceFile && existingFace.file && fc.faceFile.toLowerCase() === existingFace.file.toLowerCase())) {{
                fc.customName = cf.name;
              }}
            }});
            newFacesAdded = true;
          }}
          continue;
        }}

        if (!existingFiles.has(cfileLower) && (!cidLower || !existingIds.has(cidLower))) {{
          try {{
            const fRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/${{folder}}/${{cfile}}?_t=${{Date.now()}}`, {{
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
            }});
            if (fRes.ok) {{
              const fData = await fRes.json();
              const isGif = cfileLower.endsWith('.gif');
              const mime = isGif ? 'image/gif' : (cfileLower.endsWith('.webp') ? 'image/webp' : (cfileLower.endsWith('.png') ? 'image/png' : 'image/jpeg'));
              const src = `data:${{mime}};base64,${{fData.content.replace(/\\s/g, '')}}`;
              const faceId = cf.id || ('face_' + Date.now());
              const img = new Image();
              img.src = src;
              const newFace = {{
                id: faceId,
                name: cf.name || cf.label || cfile,
                file: cfile,
                src: src,
                img: img,
                isGif: isGif
              }};
              faces.push(newFace);
              loadedFaces[faceId] = img;
              loadedFaces[cfileLower] = img;
              loadedFaces[faces.length - 1] = img;
              existingFiles.add(cfileLower);
              if (cidLower) existingIds.add(cidLower);
              newFacesAdded = true;
            }}
          }} catch (e) {{}}
        }}
      }}

      if (newFacesAdded) {{
        faces = deduplicateFaces(faces);
        renderFacesGrid();
        renderAdminCatalog();
      }}
    }}
  }} catch (err) {{
    console.warn('Faces cloud sync notice:', err);
  }}
  }}

  // 2. Sync Templates from Cloud
  try {{
    const tmRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/Templates/manifest.json?_t=${{Date.now()}}`, {{
      headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
    }});
    if (tmRes.ok) {{
      const tmData = await tmRes.json();
      const decoded = decodeURIComponent(escape(atob(tmData.content.replace(/\\s/g, ''))));
      const cloudTemplates = JSON.parse(decoded);

      const existingTplIds = new Set(templates.map(t => (t.id || t.file || '').toLowerCase()));
      const existingTplFiles = new Set(templates.map(t => (t.file || '').toLowerCase()));
      let newTplsAdded = false;

      for (const ct of cloudTemplates) {{
        const ctfile = ct.file || ct.filename;
        if (!ctfile) continue;
        const ctfileLower = ctfile.toLowerCase();
        const tId = ct.id || ctfile;
        const tIdLower = tId.toLowerCase();
        // NEVER resurrect templates that were deleted or are actively deleting
        if (deletedItemFiles.has(ctfileLower) || deletingItemIds.has(ctfileLower) || deletingItemIds.has(tId)) continue;

        // If template already exists in memory, sync updated name from cloud manifest
        const existingTpl = templates.find(t => (tIdLower && (t.id || '').toLowerCase() === tIdLower) || (ctfileLower && (t.file || '').toLowerCase() === ctfileLower));
        if (existingTpl) {{
          if (ct.name && existingTpl.name !== ct.name) {{
            existingTpl.name = ct.name;
            newTplsAdded = true;
          }}
          continue;
        }}

        if (!existingTplIds.has(tIdLower) && !existingTplFiles.has(ctfileLower)) {{
          try {{
            const fRes = await fetch(`https://api.github.com/repos/${{repo}}/contents/Templates/${{ctfile}}?_t=${{Date.now()}}`, {{
              headers: {{ 'Authorization': 'Bearer ' + GITHUB_TOKEN }}
            }});
            if (fRes.ok) {{
              const fData = await fRes.json();
              const isGif = ctfileLower.endsWith('.gif');
              const mime = isGif ? 'image/gif' : (ctfileLower.endsWith('.webp') ? 'image/webp' : (ctfileLower.endsWith('.png') ? 'image/png' : 'image/jpeg'));
              const src = `data:${{mime}};base64,${{fData.content.replace(/\\s/g, '')}}`;
              templates.push({{
                id: tId,
                name: ct.name || ct.label || ctfile,
                file: ctfile,
                src: src,
                isGif: isGif
              }});
              const img = new Image();
              img.src = src;
              loadedTemplates[tId] = img;
              existingTplIds.add(tIdLower);
              existingTplFiles.add(ctfileLower);
              newTplsAdded = true;
            }}
          }} catch (e) {{}}
        }}
      }}

      if (newTplsAdded) {{
        templates = deduplicateTemplates(templates);
        renderTemplatesGrid();
        renderAdminTemplatesCatalog();
      }}
    }}
  }} catch (err) {{
    console.warn('Templates cloud sync notice:', err);
  }} finally {{
    isSyncingCatalog = false;
    if (syncSpinner) syncSpinner.style.display = 'none';
    if (syncLabel) syncLabel.innerText = currentLang === 'ar' ? '☁️ متزامن' : '☁️ Synced';
    if (showNotice) {{
      const syncBtn = document.getElementById('btnSyncCloud');
      if (syncBtn) {{
        const oldTxt = syncBtn.innerText;
        syncBtn.innerText = '✅ Synced';
        setTimeout(() => {{ syncBtn.innerText = oldTxt; }}, 2000);
      }}
    }}
  }}
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
    const emptyNotice = document.createElement('div');
    emptyNotice.style.cssText = 'color:var(--ps-text-muted); font-size:12px; text-align:center; padding:10px 0;';
    emptyNotice.innerText = i18n[currentLang].noLayers;
    list.appendChild(emptyNotice);
  }}

  all.forEach((item, pos) => {{
    const {{ layerType, idx, obj }} = item;
    const isAct = active && active.type === layerType && active.idx === idx;
    const row = document.createElement('div');
    row.className = 'layer-item' + (isAct ? ' active' : '');

    let thumbHtml = '';
    let titleStr = '';

    if (layerType === 'face') {{
      const fImgObj = getFaceLayerImg(obj);
      const faceImg = fImgObj ? fImgObj.src : '';
      thumbHtml = `<img src="${{faceImg}}" class="layer-thumb" alt="Face">`;
      const fObj = faces.find(f => (obj.faceId && f.id === obj.faceId) || (obj.faceFile && f.file && f.file.toLowerCase() === obj.faceFile.toLowerCase())) || faces[obj.faceIndex];
      titleStr = obj.customName || (fObj ? fObj.name : (currentLang === 'ar' ? 'فاكهة مخصصة' : 'Custom Fruit'));
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
      syncFilterUI();
    }};

    list.appendChild(row);
  }});

  // ALWAYS APPEND BACKGROUND LAYER AT BOTTOM OF LAYERS LIST (CANNOT BE REMOVED OR REORDERED)
  const isBgAct = active && active.type === 'bg';
  const bgRow = document.createElement('div');
  bgRow.className = 'layer-item' + (isBgAct ? ' active' : '');
  bgRow.style.cssText = 'border-top: 1px solid rgba(255,255,255,0.06); background: ' + (isBgAct ? 'var(--ps-card-hover)' : 'rgba(0,0,0,0.25)') + ';';

  let bgImg = null;
  if (state.bgType === 'custom' && state.bgCustomImg) bgImg = state.bgCustomImg;
  else if (state.bgType === 'template') bgImg = getBgTemplateImg(state.bgTemplateId);

  let bgThumbHtml = bgImg && bgImg.src ? `<img src="${{bgImg.src}}" class="layer-thumb" alt="Backdrop">` : `<span style="font-size:16px; margin:0 4px;">🖼️</span>`;
  let bgTitle = currentLang === 'ar' ? 'الخلفية والقوالب' : 'Backdrop & Template';

  bgRow.innerHTML = `
    <div class="layer-left">
      ${{bgThumbHtml}}
      <span class="layer-title-text">${{bgTitle}}</span>
    </div>
    <div class="layer-actions">
      <button class="layer-action-btn" title="${{currentLang === 'ar' ? 'إعادة ضبط الخلفية' : 'Reset Backdrop'}}" onclick="event.stopPropagation(); deleteSpecificLayer('bg', 0)">🔄</button>
    </div>
  `;

  bgRow.onclick = () => {{
    state.activeTransformTarget = {{ type: 'bg' }};
    render();
    syncLayersUI();
    syncFilterUI();
  }};

  list.appendChild(bgRow);
}}

window.deleteSpecificLayer = function(layerType, idx) {{
  if (layerType === 'face') {{
    state.facesOnCanvas.splice(idx, 1);
  }} else if (layerType === 'acc') {{
    state.accessoriesOnCanvas.splice(idx, 1);
  }} else if (layerType === 'text') {{
    state.texts.splice(idx, 1);
    const ti = document.getElementById('activeTextInput');
    if (ti) ti.value = '';
  }} else if (layerType === 'bg') {{
    state.bgType = 'color';
    state.bgCustomImg = null;
    state.bgTemplateId = null;
    state.bgIsGif = false;
    state.bgGifFrames = [];
    state.bgCustomName = '';
  }}
  state.activeTransformTarget = null;
  render();
  syncLayersUI();
  updateDynamicFileName();
}};

// --- EXPORT FUNCTIONS ---
function exportPng() {{
  const prevTarget = state.activeTransformTarget;
  state.activeTransformTarget = null;
  render();

  const expInput = document.getElementById('exportFileNameInput');
  const baseName = (expInput && expInput.value.trim()) ? expInput.value.trim().replace(/[^a-zA-Z0-9_-]/g, '_') : 'frutisator_meme';

  const link = document.createElement('a');
  link.download = baseName + '.png';
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

  // Calculate native GIF playback speed so saved GIF is NEVER too fast
  let exportInterval = 0.10; // Default 100ms (10 fps)
  let numExportFrames = 18;

  if (state.bgIsGif && state.bgGifFrames && state.bgGifFrames.length > 0) {{
    const rawFrames = state.bgGifFrames;
    const rawCount = rawFrames.length;
    const delays = state.bgGifDelays || rawFrames.delays || [];
    const totalMs = state.bgGifTotalDuration || rawFrames.totalDuration || (rawCount * 100);
    const avgDelayMs = totalMs / rawCount;

    if (rawCount <= 36) {{
      numExportFrames = rawCount;
      exportInterval = avgDelayMs / 1000;
    }} else {{
      numExportFrames = 30;
      exportInterval = (totalMs / numExportFrames) / 1000;
    }}
  }} else {{
    const gifFace = state.facesOnCanvas.find(f => f.isGif && f.gifFrames && f.gifFrames.length > 0);
    if (gifFace) {{
      const rawCount = gifFace.gifFrames.length;
      const delays = gifFace.gifDelays || gifFace.gifFrames.delays || [];
      const totalMs = gifFace.gifTotalDuration || gifFace.gifFrames.totalDuration || (rawCount * 100);
      const avgDelayMs = totalMs / rawCount;
      if (rawCount <= 36) {{
        numExportFrames = rawCount;
        exportInterval = avgDelayMs / 1000;
      }} else {{
        numExportFrames = 26;
        exportInterval = (totalMs / numExportFrames) / 1000;
      }}
    }} else if (state.animation !== 'none') {{
      numExportFrames = 20;
      exportInterval = 0.08;
    }}
  }}

  // Guarantee interval is within standard GIF browser range [0.04s .. 0.25s]
  exportInterval = Math.max(0.04, Math.min(0.25, Number(exportInterval.toFixed(3))));

  const frameImages = [];

  for (let i = 0; i < numExportFrames; i++) {{
    const timeMs = i * (exportInterval * 1000);
    const p = i / numExportFrames;

    // 1. Sync Background GIF Frame to exact timeline timestamp
    if (state.bgIsGif && state.bgGifFrames && state.bgGifFrames.length > 0) {{
      const delays = state.bgGifDelays || state.bgGifFrames.delays || [];
      const totalDur = state.bgGifTotalDuration || state.bgGifFrames.totalDuration || (state.bgGifFrames.length * 100);
      const curTime = timeMs % Math.max(1, totalDur);
      let acc = 0;
      let targetIdx = 0;
      for (let f = 0; f < state.bgGifFrames.length; f++) {{
        const d = delays[f] || 100;
        if (curTime >= acc && curTime < acc + d) {{
          targetIdx = f;
          break;
        }}
        acc += d;
      }}
      state.bgGifIndex = targetIdx;
    }}

    // 2. Sync Face GIF Frames to exact timeline timestamp
    state.facesOnCanvas.forEach(f => {{
      if (f.isGif && f.gifFrames && f.gifFrames.length > 0) {{
        const delays = f.gifDelays || f.gifFrames.delays || [];
        const totalDur = f.gifTotalDuration || f.gifFrames.totalDuration || (f.gifFrames.length * 100);
        const curTime = timeMs % Math.max(1, totalDur);
        let acc = 0;
        let targetIdx = 0;
        for (let fi = 0; fi < f.gifFrames.length; fi++) {{
          const d = delays[fi] || 100;
          if (curTime >= acc && curTime < acc + d) {{
            targetIdx = fi;
            break;
          }}
          acc += d;
        }}
        f.gifIndex = targetIdx;
      }}
    }});

    const off = getAnimOffset(state.animation, p);
    render(off);
    frameImages.push(canvas.toDataURL('image/png'));
  }}

  state.activeTransformTarget = prevTarget;
  render();

  progText.innerText = 'Encoding Discord GIF (matching native speed)...';
  window.gifshot.createGIF({{
    images: frameImages,
    gifWidth: gifW,
    gifHeight: gifH,
    interval: exportInterval,
    numWorkers: 4,
    sampleInterval: 2,
    progressCallback: (captureProgress) => {{
      progBar.style.width = Math.round(captureProgress * 100) + '%';
      progText.innerText = 'Encoding GIF: ' + Math.round(captureProgress * 100) + '%';
    }}
  }}, (obj) => {{
    if (!obj.error) {{
      const expInput = document.getElementById('exportFileNameInput');
      const baseName = (expInput && expInput.value.trim()) ? expInput.value.trim().replace(/[^a-zA-Z0-9_-]/g, '_') : 'frutisator_meme';
      const link = document.createElement('a');
      link.download = baseName + '.gif';
      link.href = obj.image;
      link.click();
    }}
    progWrap.style.display = 'none';
  }});
}}

function getAnimOffset(anim, progress) {{
  const t = progress * Math.PI * 2;
  if (anim === 'bob') {{
    return {{ x: 0, y: Math.sin(t) * 20, rot: 0, scale: 1.0 }};
  }}
  if (anim === 'bounce') {{
    const b = Math.abs(Math.sin(t));
    return {{
      x: 0,
      y: -b * 30,
      rot: Math.sin(t) * 4,
      scaleX: 1.0 + (1 - b) * 0.22,
      scaleY: 1.0 - (1 - b) * 0.20
    }};
  }}
  if (anim === 'shake') {{
    return {{
      x: (Math.random() - 0.5) * 20,
      y: (Math.random() - 0.5) * 20,
      rot: (Math.random() - 0.5) * 14,
      scale: 1.0
    }};
  }}
  if (anim === 'earthquake') {{
    return {{
      x: (Math.random() - 0.5) * 40,
      y: (Math.random() - 0.5) * 40,
      rot: (Math.random() - 0.5) * 25,
      scale: 1.0 + (Math.random() - 0.5) * 0.15
    }};
  }}
  if (anim === 'petpet') {{
    const squish = Math.abs(Math.sin(t * 2));
    return {{
      x: 0,
      y: squish * 18,
      rot: 0,
      scaleX: 1.0 + squish * 0.18,
      scaleY: 1.0 - squish * 0.28
    }};
  }}
  if (anim === 'jelly') {{
    return {{
      x: Math.sin(t) * 8,
      y: Math.cos(t) * 6,
      rot: Math.sin(t) * 12,
      scaleX: 1.0 + Math.sin(t * 2) * 0.22,
      scaleY: 1.0 - Math.sin(t * 2) * 0.22
    }};
  }}
  if (anim === 'spin') {{
    return {{ x: 0, y: 0, rot: progress * 360, scale: 1.0 }};
  }}
  if (anim === 'spin_fast') {{
    return {{ x: 0, y: 0, rot: progress * 720, scale: 1.0 }};
  }}
  if (anim === 'disco') {{
    return {{
      x: Math.sin(t) * 16,
      y: Math.cos(t) * 16,
      rot: Math.sin(t) * 22,
      scale: 1.0 + Math.sin(t) * 0.18
    }};
  }}
  if (anim === 'headbang') {{
    const hb = Math.pow(Math.max(0, Math.sin(t)), 1.5);
    return {{
      x: 0,
      y: hb * 28,
      rot: hb * 22,
      scaleX: 1.0 + hb * 0.12,
      scaleY: 1.0 - hb * 0.16
    }};
  }}
  if (anim === 'wobble') {{
    return {{ x: Math.sin(t) * 18, y: 0, rot: Math.sin(t) * 20, scale: 1.0 }};
  }}
  if (anim === 'swing') {{
    return {{
      x: Math.sin(t) * 24,
      y: (1 - Math.cos(t)) * 12,
      rot: Math.sin(t) * 30,
      scale: 1.0
    }};
  }}
  if (anim === 'float') {{
    return {{
      x: Math.sin(t) * 16,
      y: Math.sin(t * 2) * 12,
      rot: Math.sin(t) * 7,
      scale: 1.0
    }};
  }}
  if (anim === 'orbit') {{
    return {{
      x: Math.cos(t) * 28,
      y: Math.sin(t) * 12,
      rot: -Math.sin(t) * 10,
      scale: 1.0 + Math.sin(t) * 0.24
    }};
  }}
  if (anim === 'heart') {{
    const hPhase = progress % 0.5;
    const hBeat = Math.sin(hPhase * Math.PI * 2) * (hPhase < 0.25 ? 0.22 : 0.08);
    return {{ x: 0, y: -hBeat * 8, rot: 0, scale: 1.0 + Math.max(0, hBeat) }};
  }}
  if (anim === 'zoom') {{
    return {{ x: 0, y: 0, rot: 0, scale: 1.0 + Math.sin(t) * 0.26 }};
  }}
  if (anim === 'breathe') {{
    const br = (Math.sin(t) + 1) / 2;
    return {{
      x: 0,
      y: -br * 8,
      rot: 0,
      scaleX: 1.0 + br * 0.12,
      scaleY: 1.0 + br * 0.16
    }};
  }}
  if (anim === 'roll') {{
    return {{ x: Math.sin(t) * 24, y: 0, rot: Math.sin(t) * 45, scale: 1.0 }};
  }}
  if (anim === 'dizzy') {{
    return {{
      x: Math.sin(t) * 20 + Math.cos(t * 2) * 8,
      y: Math.cos(t) * 14,
      rot: Math.sin(t * 1.5) * 26,
      scale: 1.0 + Math.sin(t * 3) * 0.12
    }};
  }}
  if (anim === 'peekaboo') {{
    const pk = Math.sin(t);
    return {{
      x: 0,
      y: pk < 0 ? (-pk) * 55 : 0,
      rot: pk < 0 ? 0 : Math.sin(t * 4) * 8,
      scale: 1.0
    }};
  }}
  if (anim === 'jitter') {{
    return {{
      x: (Math.random() - 0.5) * 12,
      y: (Math.random() - 0.5) * 12,
      rot: (Math.random() - 0.5) * 8,
      scale: 1.0 + (Math.random() - 0.5) * 0.08
    }};
  }}
  if (anim === 'chaos') {{
    return {{
      x: (Math.random() - 0.5) * 36 + Math.sin(t * 3) * 16,
      y: (Math.random() - 0.5) * 36 + Math.cos(t * 3) * 16,
      rot: (Math.random() - 0.5) * 50 + t * 45,
      scale: 0.85 + Math.random() * 0.4
    }};
  }}
  return {{ x: 0, y: 0, rot: 0, scale: 1.0 }};
}}

// Live preview loop with accurate millisecond timing synced to native GIF speed
let lastFrameTime = 0;
let animProgress = 0;
let bgElapsedMs = 0;
function animLoop(timestamp) {{
  if (!lastFrameTime) lastFrameTime = timestamp;
  const dtMs = Math.min(100, timestamp - lastFrameTime);
  const dt = dtMs / 1000;
  lastFrameTime = timestamp;

  const hasGifFace = state.facesOnCanvas.some(f => f.isGif && f.gifFrames && f.gifFrames.length > 0);
  if (state.animation !== 'none' || state.bgIsGif || hasGifFace) {{
    // Steady 1.0s loop for CSS transform effects (Bob, Spin, Bounce, etc.)
    animProgress = (animProgress + dt * 1.0) % 1.0;

    // Background GIF: advance frames based on exact native frame delays
    if (state.bgIsGif && state.bgGifFrames && state.bgGifFrames.length > 0) {{
      bgElapsedMs += dtMs;
      const delays = state.bgGifDelays || state.bgGifFrames.delays || [];
      const totalDur = state.bgGifTotalDuration || state.bgGifFrames.totalDuration || (state.bgGifFrames.length * 100);
      const curTime = bgElapsedMs % Math.max(1, totalDur);

      let acc = 0;
      let targetIdx = 0;
      for (let i = 0; i < state.bgGifFrames.length; i++) {{
        const d = delays[i] || 100;
        if (curTime >= acc && curTime < acc + d) {{
          targetIdx = i;
          break;
        }}
        acc += d;
      }}
      state.bgGifIndex = targetIdx;
    }}

    // Face GIFs: advance frames based on exact native frame delays
    state.facesOnCanvas.forEach(f => {{
      if (f.isGif && f.gifFrames && f.gifFrames.length > 0) {{
        f.elapsedMs = (f.elapsedMs || 0) + dtMs;
        const delays = f.gifDelays || f.gifFrames.delays || [];
        const totalDur = f.gifTotalDuration || f.gifFrames.totalDuration || (f.gifFrames.length * 100);
        const curTime = f.elapsedMs % Math.max(1, totalDur);

        let acc = 0;
        let targetIdx = 0;
        for (let fi = 0; fi < f.gifFrames.length; fi++) {{
          const d = delays[fi] || 100;
          if (curTime >= acc && curTime < acc + d) {{
            targetIdx = fi;
            break;
          }}
          acc += d;
        }}
        f.gifIndex = targetIdx;
      }}
    }});

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
  updateDynamicFileName();

  // If default selected template is a GIF, decode and start animation immediately
  if (state.bgType === 'template' && state.bgTemplateId) {{
    const initialTpl = templates.find(t => t.id === state.bgTemplateId);
    if (initialTpl && ((initialTpl.file && initialTpl.file.toLowerCase().endsWith('.gif')) || (initialTpl.src && initialTpl.src.startsWith('data:image/gif')))) {{
      dataUriOrUrlToArrayBuffer(initialTpl.src).then(parseGifFrames).then(frames => {{
        if (frames && frames.length > 0) {{
          initialTpl.gifFrames = frames;
          state.bgIsGif = true;
          state.bgGifFrames = frames;
          state.bgGifIndex = 0;
          state.bgCustomImg = frames[0];
          render();
        }}
      }}).catch(() => {{}});
    }}
  }}

  render();
  requestAnimationFrame(animLoop);
  setTimeout(() => syncCloudCatalog(false), 1500);
  setInterval(() => syncCloudCatalog(false), 25000);
}};
</script>
</body>
</html>
"""

# Render embedded Frutisator Studio
components.html(html_app, height=1000, scrolling=False)
