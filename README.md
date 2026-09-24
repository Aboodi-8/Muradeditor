# 🎭 Murad Face Slapper — Discord Meme & GIF Maker

A meme generator built specifically for **Murad** to slap his real faces onto any picture or meme, and export animated GIFs for Discord!

Supports both **Streamlit Cloud (`*.streamlit.app`)** and a standalone web app.

---

## 📸 Real Faces of Murad (6 Presets)
- 📸 **Wide Cam**: Murad's stretched webcam close-up.
- 😱 **Scream**: Murad's profile hype screaming face.
- 😈 **Purple Grin**: Murad's smiling purple-lit face.
- 👾 **Pixel Smirk**: Smirking wide face.
- 🤨 **Serious**: Intense/serious gaze reaction face.
- ⚡ **Laser Scream**: Glowing laser-eyes scream face.
- ➕ **Upload Custom Face**: Upload any additional photo of Murad.

---

## 🚀 How to Run with Streamlit

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app.py
   ```
   Open your browser at **`http://localhost:8501`**.

### ☁️ Deploy to Streamlit Cloud (`streamlit.app`)
1. Push this folder to your GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io).
3. Connect your repository and set the main file path to:
   ```
   streamlit_app.py
   ```
4. Click **Deploy**! Your app will be live at `https://<your-name>-murad-meme.streamlit.app`.

---

## ✨ Features
1. **Instant Access**: Opens directly to the meme creator (no login required).
2. **Background / Meme Source**: Upload any image or choose a body preset (*Suit & Tie*, *Gigachad*, *Space Suit*, *Doge*, *Buff Guy*).
3. **Face Cutout & Placement**:
   - Cutout shape: **Circle**, **Oval Face**, or **Square**.
   - Sliders for **Face Size (%)**, **Rotation (°)**, **Move X**, and **Move Y**.
4. **Discord Animations (GIF)**:
   - 🖼️ Still Image (PNG)
   - 🕺 Head Bob (Vibing up and down)
   - 💢 Shake Meme (Intense camera shake)
   - 🌀 Speen (360° spin)
   - 👋 Petpet Hand (Squishy hand petting Murad's head)
   - 💥 Pulse Zoom
5. **Discord Simulator & Direct Export**:
   - Preview how your meme looks inside a Discord chat bubble with Murad's username.
   - One-click **Download Discord GIF (.GIF)** or **Download (.PNG)**.

---

## 📂 Repository Structure
- `streamlit_app.py`: Streamlit application entry point
- `app.py`: Alias entry point for Streamlit Cloud
- `requirements.txt`: Python dependencies (`streamlit`, `Pillow`)
- `.streamlit/config.toml`: Discord dark theme configuration
- `assets/`: Murad's 6 real face photos
- `index.html`, `style.css`, `app.js`: Standalone browser version
