# 🍉 Frutisator — Photoshop-Style Pro Meme Studio & GIF Maker

A powerful Photoshop-style browser & Streamlit studio to slap Fruit faces, stickers, animations, color filters, and custom meme captions onto any picture, template, or GIF!

---

## ✨ Features
1. **Photoshop-Style Pro Dark Studio**:
   - Ultra-compact, dark-themed `#000000` / `#18181b` canvas interface.
   - Zero outer-page scrollbars with dynamic canvas scaling (`🔍 Fit Screen`).
   - Interactive on-canvas transform handles: drag, resize, rotate, and `Shift`-stretch!
2. **Backdrop & Popular Meme Templates**:
   - Upload any custom background image, meme template, or animated GIF.
   - Instant aspect ratio switches: **Square 1:1**, **Portrait 9:16**, **Landscape 16:9**, or **📐 True Size**.
   - Built-in classic templates (*Suit & Tie*, *Gigachad*, *King Throne*, *Space*).
3. **🍉 Fruits Faces & Custom Uploads**:
   - Upload custom face/photo with interactive cutout options: **Full Frame** or **Oval Face**.
   - Empty catalog by default for clean startup, ready for instant custom uploads.
   - Admin locked catalog manager (`🔒`) to dynamically manage fruit presets.
4. **🎨 Color Filters & Adjustments (New!)**:
   - Apply independent color filters to **Backdrop**, **Faces**, or **Stickers**.
   - 8 one-click presets: **Normal**, **🖤 B&W**, **📜 Sepia**, **🔮 Invert**, **🌈 Shift**, **⚡ Vivid**, **🌆 Cyber**, and **🔥 Warm**.
   - Fine-tuned sliders: **Hue Shift** (0-360°), **B&W / Grayscale** (0-100%), **Brightness**, **Contrast**, and **Saturation**.
5. **✍️ Pro Meme Text Engine**:
   - Quick **+ Top**, **+ Bottom**, or **+ Custom** text buttons.
   - Font family picker: *Impact*, *Arial Black*, *Comic Sans*, *Tahoma*, *Courier New*, *Trebuchet MS*, *Georgia*.
   - Color presets (White, Yellow, Red, Cyan, Green) + native **🎨 Color Wheel**.
   - Adjustable font sizes and thick meme outlines.
6. **🕺 Discord Fit Effects & Animations (GIF)**:
   - 6 compact animations: **Bob**, **Shake**, **Speen (360°)**, **Pulse**, **Heartbeat**, **Wobble**, and **Disco**.
   - High-fidelity GIF export with precise color palettes and correct aspect ratio framing.
7. **🌐 Full English & Arabic (العربية) Support**:
   - Clean topbar language switcher (`🌐 العربية` / `🌐 English`).
   - **Bigger & bolder typography** with Google Font Cairo for Arabic characters.
   - Pure textual localization maintaining exact Photoshop-style LTR desktop layout.
8. **Direct Discord Export**:
   - **📋 Copy Image**: Instantly copies the canvas to clipboard for direct `Ctrl+V` pasting into Discord!
   - **⬇️ Save PNG** & **⬇️ Export GIF** (`frutisator_meme.png`, `frutisator_meme.gif`).

---

## 🔒 Private Repository for Photos / Faces (Keep Your Pictures Safe)
You can keep the code public on GitHub while keeping your private pictures in a completely **Private GitHub Repository**:

1. Create a new private repository on GitHub (e.g. `your-username/frutisator-private-faces`).
2. Add a folder named `faces/` inside it and upload your private photos (`.png`, `.jpg`, `.webp`).
3. Generate a GitHub Personal Access Token (classic) with `repo:read` scope at: [github.com/settings/tokens](https://github.com/settings/tokens).
4. In your Streamlit Cloud dashboard, go to your app settings **⚙️ Settings → Secrets**, and add:
   ```toml
   GITHUB_TOKEN = "ghp_yourPersonalAccessTokenHere"
   PRIVATE_FACES_REPO = "your-username/frutisator-private-faces"
   PRIVATE_FACES_FOLDER = "faces"
   ```
5. Frutisator will automatically and securely fetch your private photos on the server and load them into the studio without exposing your photos or token to the public!

---

## 🚀 Running Locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```
Open your browser at `http://localhost:8501`.
