/**
 * Murad Face Slapper - Discord Meme & GIF Generator
 * Simple, fast, and hilarious: Slap Murad's face on any picture or meme!
 */

// Global State
const appState = {
  // Base background
  bgType: 'preset', // 'preset' or 'custom'
  presetBgId: 'suit',
  customBgImg: null,

  // Selected Murad Face
  activeFaceIndex: 0,
  cropShape: 'circle', // 'circle', 'oval', 'square'

  // Face Placement & Transform
  faceX: 0, // relative offset from center
  faceY: -20,
  faceScale: 1.0,
  faceRotation: 0, // in degrees

  // Animation & GIF
  animType: 'none', // 'none', 'bob', 'shake', 'spin', 'petpet', 'zoom'
  currentFrame: 0,
  totalFrames: 12,
  fps: 12,
  isPlaying: true,

  // Captions
  caption: '',

  // Mouse / Touch Dragging
  isDragging: false,
  dragStartX: 0,
  dragStartY: 0,
  initialFaceX: 0,
  initialFaceY: 0,
};

// Murad's Real Faces Catalog
const MURAD_FACES = [
  {
    id: 'murad_wide',
    name: 'Wide Cam 📸',
    src: 'assets/murad_wide.png',
  },
  {
    id: 'murad_scream',
    name: 'Scream 😱',
    src: 'assets/murad_scream.png',
  },
  {
    id: 'murad_purple',
    name: 'Purple Grin 😈',
    src: 'assets/murad_purple.png',
  },
  {
    id: 'murad_pixel',
    name: 'Pixel Smirk 👾',
    src: 'assets/murad_pixel.png',
  },
  {
    id: 'murad_serious',
    name: 'Serious 🤨',
    src: 'assets/murad_serious.png',
  },
  {
    id: 'murad_laser',
    name: 'Laser Scream ⚡',
    src: 'assets/murad_laser.png',
  },
];

// Preloaded images cache
const faceImages = [];
let mainCanvas, ctx;
let discordSimCanvas;
let animInterval = null;

// PASSWORD GATE LOGIC
const APP_PASSWORD = "Muradismurad";

function checkPasswordAuth() {
  const modal = document.getElementById('passwordGateModal');
  if (sessionStorage.getItem('murad_auth') === 'true') {
    if (modal) modal.style.display = 'none';
  } else {
    if (modal) modal.style.display = 'flex';
  }
}

function verifyPassword() {
  const input = document.getElementById('passwordInput');
  const error = document.getElementById('passwordError');
  const modal = document.getElementById('passwordGateModal');

  if (input && input.value === APP_PASSWORD) {
    sessionStorage.setItem('murad_auth', 'true');
    if (error) error.style.display = 'none';
    if (modal) modal.style.display = 'none';
  } else {
    if (error) error.style.display = 'block';
    if (input) {
      input.value = '';
      input.focus();
    }
  }
}

// Initialize on Load
document.addEventListener('DOMContentLoaded', () => {
  checkPasswordAuth();

  mainCanvas = document.getElementById('mainCanvas');
  ctx = mainCanvas.getContext('2d');

  // Discord simulator mirror canvas
  discordSimCanvas = document.createElement('canvas');
  discordSimCanvas.width = 140;
  discordSimCanvas.height = 140;
  document.getElementById('discordEmbedWrap').appendChild(discordSimCanvas);

  loadMuradFaces();
  initUI();
  setupCanvasDragging();
  startAnimationLoop();
});

// Load Murad's photos into memory and UI
function loadMuradFaces() {
  const container = document.getElementById('facesGrid');
  container.innerHTML = '';

  MURAD_FACES.forEach((face, index) => {
    const img = new Image();
    img.src = face.src;
    img.crossOrigin = 'Anonymous';
    faceImages.push(img);

    const div = document.createElement('div');
    div.className = `face-item ${index === appState.activeFaceIndex ? 'active' : ''}`;
    div.innerHTML = `
      <img src="${face.src}" class="face-thumb" alt="${face.name}">
      <div class="face-title">${face.name}</div>
    `;

    div.addEventListener('click', () => {
      appState.activeFaceIndex = index;
      document.querySelectorAll('.face-item').forEach((el, i) => {
        el.classList.toggle('active', i === index);
      });
      // Update discord PFP
      document.getElementById('discordPfp').src = face.src;
      draw();
    });

    container.appendChild(div);
  });
}

// Setup User Interface Controls
function initUI() {
  // 1. Background Presets
  document.querySelectorAll('.bg-preset-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.bg-preset-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      appState.bgType = 'preset';
      appState.presetBgId = btn.getAttribute('data-bg');
      appState.customBgImg = null;
      draw();
    });
  });

  // 1. Background Image Upload
  const bgUpload = document.getElementById('bgUploadInput');
  bgUpload.addEventListener('change', (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      const reader = new FileReader();
      reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
          appState.customBgImg = img;
          appState.bgType = 'custom';
          document.querySelectorAll('.bg-preset-btn').forEach(b => b.classList.remove('active'));
          draw();
        };
        img.src = event.target.result;
      };
      reader.readAsDataURL(file);
    }
  });

  // 2. Cutout shape
  document.querySelectorAll('#cropTypeGroup .btn-toggle').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('#cropTypeGroup .btn-toggle').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      appState.cropShape = btn.getAttribute('data-crop');
      draw();
    });
  });

  // 3. Face sliders
  const scaleSlider = document.getElementById('faceScale');
  scaleSlider.addEventListener('input', (e) => {
    appState.faceScale = parseFloat(e.target.value);
    document.getElementById('sizeVal').textContent = `${Math.round(appState.faceScale * 100)}%`;
    draw();
  });

  const rotSlider = document.getElementById('faceRotate');
  rotSlider.addEventListener('input', (e) => {
    appState.faceRotation = parseInt(e.target.value, 10);
    document.getElementById('rotVal').textContent = `${appState.faceRotation}°`;
    draw();
  });

  const posXSlider = document.getElementById('facePosX');
  posXSlider.addEventListener('input', (e) => {
    appState.faceX = parseInt(e.target.value, 10);
    draw();
  });

  const posYSlider = document.getElementById('facePosY');
  posYSlider.addEventListener('input', (e) => {
    appState.faceY = parseInt(e.target.value, 10);
    draw();
  });

  document.getElementById('resetFaceBtn').addEventListener('click', () => {
    appState.faceX = 0;
    appState.faceY = -20;
    appState.faceScale = 1.0;
    appState.faceRotation = 0;
    scaleSlider.value = 1.0;
    rotSlider.value = 0;
    posXSlider.value = 0;
    posYSlider.value = -20;
    document.getElementById('sizeVal').textContent = '100%';
    document.getElementById('rotVal').textContent = '0°';
    draw();
  });

  // 4. Animation modes
  document.querySelectorAll('.anim-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('.anim-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      appState.animType = btn.getAttribute('data-anim');
      appState.currentFrame = 0;
      if (appState.animType === 'none') {
        appState.totalFrames = 1;
      } else if (appState.animType === 'petpet') {
        appState.totalFrames = 8;
        appState.fps = 14;
      } else {
        appState.totalFrames = 12;
        appState.fps = 12;
      }
      draw();
    });
  });

  // 4. Caption Input
  const captionInput = document.getElementById('memeCaption');
  captionInput.addEventListener('input', (e) => {
    appState.caption = e.target.value;
    const discordText = document.getElementById('discordCaptionPreview');
    discordText.textContent = appState.caption || 'Look at this new meme I made 💀';
    draw();
  });

  // Export Buttons
  document.getElementById('exportGifBtn').addEventListener('click', () => {
    exportGif();
  });

  document.getElementById('downloadPngBtn').addEventListener('click', () => {
    downloadPng();
  });

  document.getElementById('copyGifLinkBtn').addEventListener('click', () => {
    copyGif();
  });
}

// Canvas Direct Drag & Drop for Murad's Face
function setupCanvasDragging() {
  const getPos = (e) => {
    const rect = mainCanvas.getBoundingClientRect();
    const scaleX = mainCanvas.width / rect.width;
    const scaleY = mainCanvas.height / rect.height;
    const clientX = e.touches ? e.touches[0].clientX : e.clientX;
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const startDrag = (e) => {
    const pos = getPos(e);
    appState.isDragging = true;
    appState.dragStartX = pos.x;
    appState.dragStartY = pos.y;
    appState.initialFaceX = appState.faceX;
    appState.initialFaceY = appState.faceY;
  };

  const onDrag = (e) => {
    if (!appState.isDragging) return;
    e.preventDefault();
    const pos = getPos(e);
    const dx = pos.x - appState.dragStartX;
    const dy = pos.y - appState.dragStartY;
    appState.faceX = Math.round(appState.initialFaceX + dx);
    appState.faceY = Math.round(appState.initialFaceY + dy);

    // Update sliders
    document.getElementById('facePosX').value = appState.faceX;
    document.getElementById('facePosY').value = appState.faceY;

    draw();
  };

  const stopDrag = () => {
    appState.isDragging = false;
  };

  mainCanvas.addEventListener('mousedown', startDrag);
  window.addEventListener('mousemove', onDrag);
  window.addEventListener('mouseup', stopDrag);

  mainCanvas.addEventListener('touchstart', startDrag, { passive: false });
  window.addEventListener('touchmove', onDrag, { passive: false });
  window.addEventListener('touchend', stopDrag);
}

// Draw the Preset Base Meme Bodies
function drawPresetBackground(targetCtx, w, h, id) {
  targetCtx.save();

  if (id === 'suit') {
    // Elegant Body in Suit & Red Tie
    targetCtx.fillStyle = '#1e293b';
    targetCtx.fillRect(0, 0, w, h);

    // Shoulders & Suit Jacket
    targetCtx.fillStyle = '#0f172a';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.1, h);
    targetCtx.lineTo(w * 0.2, h * 0.55);
    targetCtx.lineTo(w * 0.35, h * 0.52);
    targetCtx.lineTo(w * 0.5, h * 0.75);
    targetCtx.lineTo(w * 0.65, h * 0.52);
    targetCtx.lineTo(w * 0.8, h * 0.55);
    targetCtx.lineTo(w * 0.9, h);
    targetCtx.closePath();
    targetCtx.fill();

    // White Shirt V
    targetCtx.fillStyle = '#ffffff';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.35, h * 0.52);
    targetCtx.lineTo(w * 0.5, h * 0.82);
    targetCtx.lineTo(w * 0.65, h * 0.52);
    targetCtx.closePath();
    targetCtx.fill();

    // Red Tie
    targetCtx.fillStyle = '#dc2626';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.46, h * 0.54);
    targetCtx.lineTo(w * 0.54, h * 0.54);
    targetCtx.lineTo(w * 0.56, h * 0.62);
    targetCtx.lineTo(w * 0.58, h * 0.92);
    targetCtx.lineTo(w * 0.5, h * 0.98);
    targetCtx.lineTo(w * 0.42, h * 0.92);
    targetCtx.lineTo(w * 0.44, h * 0.62);
    targetCtx.closePath();
    targetCtx.fill();

    // Suit Lapels
    targetCtx.strokeStyle = '#334155';
    targetCtx.lineWidth = 4;
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.32, h * 0.52);
    targetCtx.lineTo(w * 0.45, h * 0.82);
    targetCtx.moveTo(w * 0.68, h * 0.52);
    targetCtx.lineTo(w * 0.55, h * 0.82);
    targetCtx.stroke();

  } else if (id === 'gigachad') {
    // Gigachad muscular body
    targetCtx.fillStyle = '#374151';
    targetCtx.fillRect(0, 0, w, h);

    // Buff neck and chest
    targetCtx.fillStyle = '#b45309';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.3, h * 0.45);
    targetCtx.lineTo(w * 0.2, h);
    targetCtx.lineTo(w * 0.8, h);
    targetCtx.lineTo(w * 0.7, h * 0.45);
    targetCtx.closePath();
    targetCtx.fill();

    // Pec definitions
    targetCtx.strokeStyle = '#78350f';
    targetCtx.lineWidth = 6;
    targetCtx.beginPath();
    targetCtx.arc(w * 0.38, h * 0.72, w * 0.14, 0.2, Math.PI * 0.9);
    targetCtx.stroke();
    targetCtx.beginPath();
    targetCtx.arc(w * 0.62, h * 0.72, w * 0.14, 0.1, Math.PI * 0.8);
    targetCtx.stroke();

  } else if (id === 'astronaut') {
    // Space Astronaut Suit
    targetCtx.fillStyle = '#090d16';
    targetCtx.fillRect(0, 0, w, h);

    // Stars in background
    targetCtx.fillStyle = '#ffffff';
    for (let i = 0; i < 30; i++) {
      targetCtx.fillRect((i * 47) % w, (i * 73) % h, 2, 2);
    }

    // Space helmet ring
    targetCtx.fillStyle = '#cbd5e1';
    targetCtx.beginPath();
    targetCtx.ellipse(w * 0.5, h * 0.42, w * 0.36, h * 0.36, 0, 0, Math.PI * 2);
    targetCtx.fill();

    // Visor dark background where face goes
    targetCtx.fillStyle = '#0f172a';
    targetCtx.beginPath();
    targetCtx.ellipse(w * 0.5, h * 0.42, w * 0.3, h * 0.3, 0, 0, Math.PI * 2);
    targetCtx.fill();

    // Suit shoulders
    targetCtx.fillStyle = '#f8fafc';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.1, h);
    targetCtx.lineTo(w * 0.2, h * 0.68);
    targetCtx.lineTo(w * 0.8, h * 0.68);
    targetCtx.lineTo(w * 0.9, h);
    targetCtx.closePath();
    targetCtx.fill();

  } else if (id === 'doge') {
    // Doge Body
    targetCtx.fillStyle = '#fef3c7';
    targetCtx.fillRect(0, 0, w, h);

    // Doge fluffy chest
    targetCtx.fillStyle = '#d97706';
    targetCtx.beginPath();
    targetCtx.arc(w * 0.5, h * 0.85, w * 0.35, 0, Math.PI * 2);
    targetCtx.fill();

    targetCtx.fillStyle = '#fffbeb';
    targetCtx.beginPath();
    targetCtx.ellipse(w * 0.5, h * 0.8, w * 0.18, h * 0.25, 0, 0, Math.PI * 2);
    targetCtx.fill();

  } else if (id === 'buff') {
    // Buff Guy Gym Tank
    targetCtx.fillStyle = '#18181b';
    targetCtx.fillRect(0, 0, w, h);

    // Massive traps and neck
    targetCtx.fillStyle = '#f59e0b';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.25, h * 0.5);
    targetCtx.lineTo(w * 0.05, h * 0.65);
    targetCtx.lineTo(w * 0.1, h);
    targetCtx.lineTo(w * 0.9, h);
    targetCtx.lineTo(w * 0.95, h * 0.65);
    targetCtx.lineTo(w * 0.75, h * 0.5);
    targetCtx.closePath();
    targetCtx.fill();

    // Tank top
    targetCtx.fillStyle = '#dc2626';
    targetCtx.beginPath();
    targetCtx.moveTo(w * 0.35, h * 0.65);
    targetCtx.lineTo(w * 0.3, h);
    targetCtx.lineTo(w * 0.7, h);
    targetCtx.lineTo(w * 0.65, h * 0.65);
    targetCtx.closePath();
    targetCtx.fill();
  }

  targetCtx.restore();
}

// Master Render to Canvas
function renderTo(targetCtx, w, h, frameIndex = 0) {
  targetCtx.clearRect(0, 0, w, h);

  // 1. Draw Background (Custom upload OR Preset)
  if (appState.bgType === 'custom' && appState.customBgImg) {
    const img = appState.customBgImg;
    // Scale aspect fit/cover to fill canvas nicely
    const scale = Math.max(w / img.width, h / img.height);
    const drawW = img.width * scale;
    const drawH = img.height * scale;
    const drawX = (w - drawW) / 2;
    const drawY = (h - drawH) / 2;
    targetCtx.drawImage(img, drawX, drawY, drawW, drawH);
  } else {
    drawPresetBackground(targetCtx, w, h, appState.presetBgId);
  }

  // 2. Compute Animation Transform for Murad's Face
  let animOffsetX = 0;
  let animOffsetY = 0;
  let animScale = 1.0;
  let animRotation = 0;

  const anim = appState.animType;
  const progress = (frameIndex / appState.totalFrames) * Math.PI * 2;

  if (anim === 'bob') {
    // Vibing Head Bob
    animOffsetY = Math.sin(progress) * 14;
    animRotation = Math.cos(progress) * 0.08;
  } else if (anim === 'shake') {
    // Meme Intense Shake
    animOffsetX = (Math.random() - 0.5) * 12;
    animOffsetY = (Math.random() - 0.5) * 12;
  } else if (anim === 'spin') {
    // Speeen 360
    animRotation = (frameIndex / appState.totalFrames) * Math.PI * 2;
  } else if (anim === 'zoom') {
    // Pulse Zoom
    animScale = 1 + Math.sin(progress) * 0.18;
  } else if (anim === 'petpet') {
    // Squish for petpet
    const squish = Math.sin((frameIndex % 5) / 5 * Math.PI);
    animScale = 1 - squish * 0.2;
    animOffsetY = squish * 12;
  }

  // 3. Draw Murad's Cutout Face
  const faceImg = faceImages[appState.activeFaceIndex];
  if (faceImg && faceImg.complete) {
    targetCtx.save();

    const centerX = w / 2 + appState.faceX + animOffsetX;
    const centerY = h / 2 + appState.faceY + animOffsetY;

    targetCtx.translate(centerX, centerY);
    targetCtx.rotate((appState.faceRotation * Math.PI / 180) + animRotation);
    targetCtx.scale(appState.faceScale * animScale, appState.faceScale * (anim === 'petpet' ? animScale : animScale));

    const faceSize = w * 0.45;

    // Apply Clipping Cutout Mask
    targetCtx.beginPath();
    if (appState.cropShape === 'circle') {
      targetCtx.arc(0, 0, faceSize / 2, 0, Math.PI * 2);
    } else if (appState.cropShape === 'oval') {
      targetCtx.ellipse(0, 0, faceSize * 0.42, faceSize * 0.55, 0, 0, Math.PI * 2);
    } else {
      // Rounded Rectangle
      const r = 12;
      targetCtx.rect(-faceSize / 2, -faceSize / 2, faceSize, faceSize);
    }
    targetCtx.clip();

    // Draw the face image centered
    const aspect = faceImg.width / faceImg.height;
    let fw = faceSize;
    let fh = faceSize;
    if (aspect > 1) {
      fw = faceSize * aspect;
    } else {
      fh = faceSize / aspect;
    }
    targetCtx.drawImage(faceImg, -fw / 2, -fh / 2, fw, fh);

    targetCtx.restore();

    // Subtle sticker border outline if circle/oval
    if (appState.cropShape !== 'square') {
      targetCtx.save();
      targetCtx.translate(centerX, centerY);
      targetCtx.rotate((appState.faceRotation * Math.PI / 180) + animRotation);
      targetCtx.scale(appState.faceScale * animScale, appState.faceScale * animScale);
      targetCtx.strokeStyle = 'rgba(255, 255, 255, 0.4)';
      targetCtx.lineWidth = 3;
      targetCtx.beginPath();
      if (appState.cropShape === 'circle') {
        targetCtx.arc(0, 0, faceSize / 2, 0, Math.PI * 2);
      } else {
        targetCtx.ellipse(0, 0, faceSize * 0.42, faceSize * 0.55, 0, 0, Math.PI * 2);
      }
      targetCtx.stroke();
      targetCtx.restore();
    }
  }

  // 4. Draw Petting Hand for Petpet
  if (anim === 'petpet') {
    const squish = Math.sin((frameIndex % 5) / 5 * Math.PI);
    const handY = h * 0.2 + squish * (h * 0.12);
    const handX = w * 0.5;

    targetCtx.save();
    targetCtx.translate(handX, handY);

    // Cute animated hand stroke
    targetCtx.fillStyle = '#fff4e6';
    targetCtx.strokeStyle = '#1e1f22';
    targetCtx.lineWidth = 4;
    targetCtx.beginPath();
    targetCtx.moveTo(-40, -10);
    targetCtx.bezierCurveTo(-45, 12, -40, 28, -25, 32);
    targetCtx.bezierCurveTo(-15, 36, 0, 38, 15, 32);
    targetCtx.bezierCurveTo(28, 26, 32, 12, 25, -5);
    targetCtx.closePath();
    targetCtx.fill();
    targetCtx.stroke();

    // Sleeve
    targetCtx.fillStyle = '#5865F2';
    targetCtx.beginPath();
    targetCtx.moveTo(-50, -40);
    targetCtx.lineTo(25, -30);
    targetCtx.lineTo(20, -5);
    targetCtx.lineTo(-45, -10);
    targetCtx.closePath();
    targetCtx.fill();
    targetCtx.stroke();

    targetCtx.restore();
  }

  // 5. Draw Caption if any
  if (appState.caption && appState.caption.trim()) {
    targetCtx.save();
    targetCtx.font = `900 ${Math.max(16, Math.floor(w * 0.08))}px Impact, -apple-system, sans-serif`;
    targetCtx.textAlign = 'center';
    targetCtx.textBaseline = 'top';
    targetCtx.fillStyle = '#ffffff';
    targetCtx.strokeStyle = '#000000';
    targetCtx.lineWidth = Math.max(4, Math.floor(w * 0.02));
    targetCtx.lineJoin = 'miter';

    const text = appState.caption.toUpperCase();
    targetCtx.strokeText(text, w / 2, 12, w - 16);
    targetCtx.fillText(text, w / 2, 12, w - 16);
    targetCtx.restore();
  }
}

// Draw to main preview and mirror to Discord simulator
function draw() {
  if (!mainCanvas || !ctx) return;
  renderTo(ctx, mainCanvas.width, mainCanvas.height, appState.currentFrame);

  // Mirror to Discord simulator
  if (discordSimCanvas) {
    const sCtx = discordSimCanvas.getContext('2d');
    sCtx.clearRect(0, 0, 140, 140);
    sCtx.drawImage(mainCanvas, 0, 0, 140, 140);
  }
}

// Animation loop
function startAnimationLoop() {
  if (animInterval) clearInterval(animInterval);
  animInterval = setInterval(() => {
    if (appState.animType !== 'none') {
      appState.currentFrame = (appState.currentFrame + 1) % appState.totalFrames;
      draw();
    }
  }, Math.round(1000 / appState.fps));
}

// Download Static PNG Image
function downloadPng() {
  const link = document.createElement('a');
  link.download = `murad_meme.png`;
  link.href = mainCanvas.toDataURL('image/png');
  link.click();
}

// Export Animated GIF for Discord
function exportGif() {
  // If still image, download PNG directly or single frame GIF
  const progressBox = document.getElementById('progressBox');
  const progressFill = document.getElementById('progressFill');
  const progressLabel = document.getElementById('progressLabel');
  const resultBox = document.getElementById('gifResultBox');

  if (appState.animType === 'none') {
    downloadPng();
    return;
  }

  progressBox.style.display = 'block';
  resultBox.style.display = 'none';
  progressFill.style.width = '10%';
  progressLabel.textContent = 'Rendering GIF frames...';

  const exportSize = 256;
  const offscreen = document.createElement('canvas');
  offscreen.width = exportSize;
  offscreen.height = exportSize;
  const offCtx = offscreen.getContext('2d');

  const frames = [];
  for (let f = 0; f < appState.totalFrames; f++) {
    renderTo(offCtx, exportSize, exportSize, f);
    frames.push(offscreen.toDataURL('image/png'));
  }

  progressFill.style.width = '35%';
  progressLabel.textContent = 'Encoding Discord GIF...';

  if (window.gifshot) {
    window.gifshot.createGIF({
      images: frames,
      gifWidth: exportSize,
      gifHeight: exportSize,
      interval: 1 / appState.fps,
      numFrames: appState.totalFrames,
      sampleInterval: 8,
      numWorkers: 2,
      progressCallback: (pct) => {
        const p = Math.round(35 + pct * 60);
        progressFill.style.width = `${p}%`;
        progressLabel.textContent = `Encoding: ${p}%...`;
      }
    }, (obj) => {
      progressFill.style.width = '100%';
      progressLabel.textContent = 'Done!';

      if (!obj.error) {
        const gifUrl = obj.image;
        document.getElementById('gifResultImg').src = gifUrl;
        document.getElementById('downloadGifAnchor').href = gifUrl;
        document.getElementById('downloadGifAnchor').download = `murad_${appState.animType}_meme.gif`;
        resultBox.style.display = 'block';
        resultBox.scrollIntoView({ behavior: 'smooth' });
      } else {
        alert('GIF export error: ' + obj.errorMsg);
      }
    });
  } else {
    alert('GIF library loading. Please try again.');
  }
}

// Copy GIF to Clipboard
async function copyGif() {
  const gifImg = document.getElementById('gifResultImg');
  if (!gifImg || !gifImg.src) return;

  try {
    const res = await fetch(gifImg.src);
    const blob = await res.blob();
    await navigator.clipboard.write([
      new ClipboardItem({ 'image/gif': blob })
    ]);
    alert('✅ Animated GIF copied! You can paste it straight into Discord!');
  } catch (e) {
    await navigator.clipboard.writeText(gifImg.src);
    alert('📋 GIF Link copied to clipboard!');
  }
}
