import io
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps, ImageFont
import streamlit as st

# Configure Streamlit page
st.set_page_config(
    page_title="Murad Face Slapper | Discord Meme & GIF Maker",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Discord CSS styling
st.markdown("""
<style>
    .stApp {
        background-color: #1e1f22;
        color: #f2f3f5;
    }
    .discord-badge {
        display: inline-block;
        background-color: rgba(88, 101, 242, 0.2);
        color: #8ea1e1;
        border: 1px solid rgba(88, 101, 242, 0.4);
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 700;
        font-size: 13px;
        margin-bottom: 12px;
    }
    .chat-bubble {
        background-color: #313338;
        border-radius: 8px;
        padding: 14px;
        border: 1px solid #232428;
        margin-top: 15px;
    }
    .chat-header {
        display: flex;
        align-items: baseline;
        gap: 8px;
        margin-bottom: 6px;
    }
    .chat-author {
        color: #ffffff;
        font-weight: 700;
        font-size: 14px;
    }
    .chat-bot-tag {
        background-color: #5865F2;
        color: white;
        font-size: 10px;
        font-weight: 700;
        padding: 1px 4px;
        border-radius: 3px;
    }
    .chat-time {
        color: #949ba4;
        font-size: 11px;
    }
    .lock-box {
        max-width: 440px;
        margin: 60px auto;
        padding: 30px;
        background-color: #2b2d31;
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# PASSWORD PROTECTION GATE
CORRECT_PASSWORD = "Muradismurad"

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    st.markdown("""
    <div class="lock-box">
        <h1 style="font-size: 40px; margin-bottom: 8px;">🔒</h1>
        <h2 style="color: #ffffff; margin-bottom: 6px;">Murad's Private Meme Lab</h2>
        <p style="color: #949ba4; font-size: 13px; margin-bottom: 20px;">
            This website is private. Please enter the password to continue.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        pwd_input = st.text_input("Enter Password:", type="password", key="login_pwd", placeholder="Password...")
        if st.button("Unlock Website 🔓", type="primary", use_container_width=True):
            if pwd_input == CORRECT_PASSWORD:
                st.session_state["authenticated"] = True
                st.success("Access Granted! Welcome Murad!")
                st.rerun()
            else:
                st.error("Incorrect password! Access denied.")
    st.stop()

# Assets directory
ASSETS_DIR = Path(__file__).parent / "assets"

MURAD_FACES = {
    "Wide Cam 📸": ASSETS_DIR / "murad_wide.png",
    "Scream 😱": ASSETS_DIR / "murad_scream.png",
    "Purple Grin 😈": ASSETS_DIR / "murad_purple.png",
    "Pixel Smirk 👾": ASSETS_DIR / "murad_pixel.png",
    "Serious 🤨": ASSETS_DIR / "murad_serious.png",
    "Laser Scream ⚡": ASSETS_DIR / "murad_laser.png",
}

# Helper: Create Preset Backgrounds using PIL
def create_preset_background(preset_name: str, width: int = 400, height: int = 400) -> Image.Image:
    bg = Image.new("RGBA", (width, height), (30, 41, 59, 255))
    draw = ImageDraw.Draw(bg)

    if preset_name == "Suit & Tie 🤵":
        jacket_points = [
            (int(width * 0.1), height),
            (int(width * 0.2), int(height * 0.55)),
            (int(width * 0.35), int(height * 0.52)),
            (int(width * 0.5), int(height * 0.75)),
            (int(width * 0.65), int(height * 0.52)),
            (int(width * 0.8), int(height * 0.55)),
            (int(width * 0.9), height),
        ]
        draw.polygon(jacket_points, fill=(15, 23, 42, 255))

        shirt_points = [
            (int(width * 0.35), int(height * 0.52)),
            (int(width * 0.5), int(height * 0.82)),
            (int(width * 0.65), int(height * 0.52)),
        ]
        draw.polygon(shirt_points, fill=(255, 255, 255, 255))

        tie_points = [
            (int(width * 0.46), int(height * 0.54)),
            (int(width * 0.54), int(height * 0.54)),
            (int(width * 0.56), int(height * 0.62)),
            (int(width * 0.58), int(height * 0.92)),
            (int(width * 0.50), int(height * 0.98)),
            (int(width * 0.42), int(height * 0.92)),
            (int(width * 0.44), int(height * 0.62)),
        ]
        draw.polygon(tie_points, fill=(220, 38, 38, 255))

    elif preset_name == "Gigachad 🗿":
        bg = Image.new("RGBA", (width, height), (55, 65, 81, 255))
        draw = ImageDraw.Draw(bg)
        points = [
            (int(width * 0.3), int(height * 0.45)),
            (int(width * 0.15), height),
            (int(width * 0.85), height),
            (int(width * 0.7), int(height * 0.45)),
        ]
        draw.polygon(points, fill=(180, 83, 9, 255))
        draw.arc([int(width * 0.24), int(height * 0.60), int(width * 0.52), int(height * 0.88)], 20, 160, fill=(120, 53, 15, 255), width=6)
        draw.arc([int(width * 0.48), int(height * 0.60), int(width * 0.76), int(height * 0.88)], 20, 160, fill=(120, 53, 15, 255), width=6)

    elif preset_name == "Space Suit 🚀":
        bg = Image.new("RGBA", (width, height), (9, 13, 22, 255))
        draw = ImageDraw.Draw(bg)
        for i in range(35):
            x = (i * 47) % width
            y = (i * 73) % height
            draw.rectangle([x, y, x + 2, y + 2], fill=(255, 255, 255, 255))
        draw.ellipse([int(width * 0.15), int(height * 0.08), int(width * 0.85), int(height * 0.78)], fill=(203, 213, 225, 255))
        draw.ellipse([int(width * 0.20), int(height * 0.13), int(width * 0.80), int(height * 0.73)], fill=(15, 23, 42, 255))
        draw.polygon([(0, height), (int(width * 0.15), int(height * 0.68)), (int(width * 0.85), int(height * 0.68)), (width, height)], fill=(248, 250, 252, 255))

    elif preset_name == "Doge 🐕":
        bg = Image.new("RGBA", (width, height), (254, 243, 199, 255))
        draw = ImageDraw.Draw(bg)
        draw.ellipse([int(width * 0.15), int(height * 0.50), int(width * 0.85), int(height * 1.20)], fill=(217, 119, 6, 255))
        draw.ellipse([int(width * 0.32), int(height * 0.55), int(width * 0.68), int(height * 1.05)], fill=(255, 251, 235, 255))

    elif preset_name == "Buff Guy 💪":
        bg = Image.new("RGBA", (width, height), (24, 24, 27, 255))
        draw = ImageDraw.Draw(bg)
        draw.polygon([(int(width * 0.25), int(height * 0.5)), (int(width * 0.05), int(height * 0.65)), (int(width * 0.1), height), (int(width * 0.9), height), (int(width * 0.95), int(height * 0.65)), (int(width * 0.75), int(height * 0.5))], fill=(245, 158, 11, 255))
        draw.polygon([(int(width * 0.35), int(height * 0.65)), (int(width * 0.3), height), (int(width * 0.7), height), (int(width * 0.65), int(height * 0.65))], fill=(220, 38, 38, 255))

    return bg

# Helper: Cut out face with selected shape
def cutout_face(face_img: Image.Image, shape: str, target_size: int) -> Image.Image:
    face_img = face_img.convert("RGBA")
    face_img = ImageOps.fit(face_img, (target_size, target_size), Image.Resampling.LANCZOS)

    mask = Image.new("L", (target_size, target_size), 0)
    draw = ImageDraw.Draw(mask)

    if shape == "Circle":
        draw.ellipse((0, 0, target_size, target_size), fill=255)
    elif shape == "Oval Face":
        margin_x = int(target_size * 0.08)
        margin_y = int(target_size * 0.02)
        draw.ellipse((margin_x, margin_y, target_size - margin_x, target_size - margin_y), fill=255)
    else:  # Square
        draw.rounded_rectangle((0, 0, target_size, target_size), radius=16, fill=255)

    face_cutout = Image.new("RGBA", (target_size, target_size), (0, 0, 0, 0))
    face_cutout.paste(face_img, (0, 0), mask=mask)
    return face_cutout

# Helper: Composite frame
def composite_frame(
    bg_img: Image.Image,
    face_cutout: Image.Image,
    pos_x: int,
    pos_y: int,
    scale: float,
    rotation: float,
    anim_type: str,
    frame_idx: int,
    total_frames: int,
    caption: str = "",
) -> Image.Image:
    w, h = bg_img.size
    frame = bg_img.copy()

    anim_x = 0
    anim_y = 0
    anim_scale = 1.0
    anim_rot = 0.0
    progress = (frame_idx / total_frames) * math.pi * 2 if total_frames > 0 else 0

    if anim_type == "Head Bob 🕺":
        anim_y = math.sin(progress) * 14
        anim_rot = math.cos(progress) * 5
    elif anim_type == "Shake Meme 💢":
        anim_x = random.randint(-8, 8)
        anim_y = random.randint(-8, 8)
    elif anim_type == "Speen 🌀":
        anim_rot = (frame_idx / total_frames) * 360
    elif anim_type == "Pulse Zoom 💥":
        anim_scale = 1.0 + math.sin(progress) * 0.18
    elif anim_type == "Petpet Hand 👋":
        squish = math.sin((frame_idx % 5) / 5 * math.pi)
        anim_scale = 1.0 - squish * 0.20
        anim_y = squish * 12

    current_scale = max(0.1, scale * anim_scale)
    face_w = int(face_cutout.width * current_scale)
    face_h = int(face_cutout.height * current_scale)

    if face_w > 0 and face_h > 0:
        scaled_face = face_cutout.resize((face_w, face_h), Image.Resampling.LANCZOS)
        total_rot = rotation + anim_rot
        if total_rot != 0:
            scaled_face = scaled_face.rotate(total_rot, expand=True, resample=Image.Resampling.BICUBIC)

        center_x = (w // 2) + pos_x + int(anim_x)
        center_y = (h // 2) + pos_y + int(anim_y)
        paste_x = center_x - (scaled_face.width // 2)
        paste_y = center_y - (scaled_face.height // 2)

        frame.paste(scaled_face, (paste_x, paste_y), scaled_face)

    # Petpet hand drawing
    if anim_type == "Petpet Hand 👋":
        squish = math.sin((frame_idx % 5) / 5 * math.pi)
        hand_y = int(h * 0.18 + squish * (h * 0.12))
        hand_x = int(w * 0.50)

        hand_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw_hand = ImageDraw.Draw(hand_layer)

        draw_hand.polygon(
            [(hand_x - 50, hand_y - 40), (hand_x + 30, hand_y - 30), (hand_x + 25, hand_y - 5), (hand_x - 45, hand_y - 10)],
            fill=(88, 101, 242, 255),
            outline=(30, 31, 34, 255),
        )
        draw_hand.ellipse(
            [hand_x - 45, hand_y - 15, hand_x + 28, hand_y + 35],
            fill=(255, 244, 230, 255),
            outline=(30, 31, 34, 255),
            width=3,
        )
        frame.paste(hand_layer, (0, 0), hand_layer)

    # Caption text
    if caption and caption.strip():
        draw = ImageDraw.Draw(frame)
        text = caption.strip().upper()
        font_size = max(18, int(w * 0.08))
        try:
            font = ImageFont.truetype("impact.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        tx = (w - text_w) // 2
        ty = 12

        stroke_w = max(2, int(w * 0.015))
        for ox in range(-stroke_w, stroke_w + 1):
            for oy in range(-stroke_w, stroke_w + 1):
                draw.text((tx + ox, ty + oy), text, font=font, fill=(0, 0, 0, 255))
        draw.text((tx, ty), text, font=font, fill=(255, 255, 255, 255))

    return frame

# --- MAIN STREAMLIT APP ---

header_col1, header_col2 = st.columns([4, 1])
with header_col1:
    st.title("🎭 Murad Face Slapper")
    st.markdown('<span class="discord-badge">⚡ Discord Animated GIF & Meme Maker</span>', unsafe_allow_html=True)
    st.caption("Upload any picture and slap Murad's face onto it for Discord chat or emojis!")

with header_col2:
    if st.button("Log Out 🔒"):
        st.session_state["authenticated"] = False
        st.rerun()

# Layout: Sidebar controls + Main stage
with st.sidebar:
    st.header("1. Background Picture / Meme")
    bg_choice = st.radio(
        "Choose Background Source:",
        ["Preset Body", "Upload My Picture / Meme"],
        horizontal=True
    )

    if bg_choice == "Upload My Picture / Meme":
        uploaded_bg = st.file_uploader(
            "Upload any image",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload the body or meme you want to slap Murad's face onto."
        )
        if uploaded_bg:
            bg_image = Image.open(uploaded_bg).convert("RGBA")
            bg_image = ImageOps.fit(bg_image, (400, 400), Image.Resampling.LANCZOS)
        else:
            bg_image = create_preset_background("Suit & Tie 🤵", 400, 400)
    else:
        preset_name = st.selectbox(
            "Pick a preset body:",
            ["Suit & Tie 🤵", "Gigachad 🗿", "Space Suit 🚀", "Doge 🐕", "Buff Guy 💪"]
        )
        bg_image = create_preset_background(preset_name, 400, 400)

    st.divider()

    st.header("2. Choose Murad's Face")
    face_choice = st.radio(
        "Select Face:",
        list(MURAD_FACES.keys()) + ["Upload Custom Face ➕"],
        index=0
    )

    if face_choice == "Upload Custom Face ➕":
        uploaded_face = st.file_uploader("Upload Murad's photo", type=["png", "jpg", "jpeg", "webp"])
        if uploaded_face:
            selected_face_img = Image.open(uploaded_face).convert("RGBA")
        else:
            selected_face_img = Image.open(MURAD_FACES["Wide Cam 📸"]).convert("RGBA")
    else:
        selected_face_img = Image.open(MURAD_FACES[face_choice]).convert("RGBA")

    cutout_shape = st.segmented_control(
        "Cutout Mask:",
        ["Circle", "Oval Face", "Square"],
        default="Circle"
    )

    st.divider()

    st.header("3. Adjust Murad's Face")
    face_scale = st.slider("Face Size (%)", min_value=30, max_value=250, value=100, step=5) / 100.0
    face_rot = st.slider("Rotate (°)", min_value=-180, max_value=180, value=0, step=5)
    pos_x = st.slider("Move Left / Right (X)", min_value=-200, max_value=200, value=0, step=2)
    pos_y = st.slider("Move Up / Down (Y)", min_value=-200, max_value=200, value=-25, step=2)

    st.divider()

    st.header("4. Discord Animation (GIF)")
    anim_type = st.selectbox(
        "Animation Effect:",
        ["Still Image (PNG) 🖼️", "Head Bob 🕺", "Shake Meme 💢", "Speen 🌀", "Petpet Hand 👋", "Pulse Zoom 💥"],
        index=0
    )

    caption_text = st.text_input("Top Caption (Optional):", placeholder="e.g. WHEN MURAD ENTERS VC...")

# Process Cutout
face_cutout = cutout_face(selected_face_img, cutout_shape, target_size=180)

# Main Stage Display
col_preview, col_discord = st.columns([1.2, 1.0])

with col_preview:
    st.subheader("🖼️ Live Meme Preview")

    if anim_type == "Still Image (PNG) 🖼️":
        rendered_frame = composite_frame(
            bg_image, face_cutout, pos_x, pos_y, face_scale, face_rot,
            anim_type="none", frame_idx=0, total_frames=1, caption=caption_text
        )

        st.image(rendered_frame, use_container_width=True)

        buf = io.BytesIO()
        rendered_frame.save(buf, format="PNG")
        png_bytes = buf.getvalue()

        st.download_button(
            label="⬇️ Download Discord Meme (.PNG)",
            data=png_bytes,
            file_name="murad_meme.png",
            mime="image/png",
            use_container_width=True,
            type="primary"
        )
    else:
        num_frames = 12 if "Petpet" not in anim_type else 8
        fps = 12 if "Petpet" not in anim_type else 14
        duration_ms = int(1000 / fps)

        frames = []
        for i in range(num_frames):
            f = composite_frame(
                bg_image, face_cutout, pos_x, pos_y, face_scale, face_rot,
                anim_type=anim_type, frame_idx=i, total_frames=num_frames, caption=caption_text
            )
            frames.append(f)

        gif_buf = io.BytesIO()
        frames[0].save(
            gif_buf,
            format="GIF",
            save_all=True,
            append_images=frames[1:],
            duration=duration_ms,
            loop=0,
            disposal=2
        )
        gif_bytes = gif_buf.getvalue()
        file_size_kb = len(gif_bytes) // 1024

        st.image(gif_bytes, use_container_width=True)
        st.success(f"GIF Size: **{file_size_kb} KB** — Discord Ready! 🚀")

        st.download_button(
            label="⬇️ Download Discord GIF (.GIF)",
            data=gif_bytes,
            file_name=f"murad_{anim_type.split()[0].lower()}_meme.gif",
            mime="image/gif",
            use_container_width=True,
            type="primary"
        )

with col_discord:
    st.subheader("💬 Discord Chat Simulator")
    st.markdown("""
    <div class="chat-bubble">
        <div class="chat-header">
            <span class="chat-author">Murad</span>
            <span class="chat-bot-tag">APP</span>
            <span class="chat-time">Today at 10:30 PM</span>
        </div>
        <div style="font-size: 13px; color: #dbdee1; margin-bottom: 8px;">
    """ + (caption_text if caption_text else "Look at this new Discord sticker I made 💀") + """
        </div>
    </div>
    """, unsafe_allow_html=True)

    if anim_type == "Still Image (PNG) 🖼️":
        st.image(rendered_frame, width=220)
    else:
        st.image(gif_bytes, width=220)

    st.info("💡 **Tip:** You can drag & drop the downloaded `.gif` directly into any Discord server or DM with no Nitro required!")
