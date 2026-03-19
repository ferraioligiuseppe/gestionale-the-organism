let stream = null;
let mpCamera = null;
let faceMesh = null;
let sampleIndex = 0;
let blinkCount = 0;
let lastBlinkTs = null;
let sessionStartTs = null;
let gazeHistory = [];
let samples = [];
let patientId = null;
let patientLabel = "";
let protocolName = "free_observation";

const MAX_SAMPLES = 1500;
const SEND_EVERY_N_FRAMES = 4;
let frameCounter = 0;

const videoEl = document.getElementById("video");
const canvasEl = document.getElementById("canvas");
const canvasCtx = canvasEl.getContext("2d");
const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");
const patientInfo = document.getElementById("patientInfo");
const overlayText = document.getElementById("overlayText");
const debugInfo = document.getElementById("debugInfo");

const fields = [
  "gaze_direction","head_tilt_deg","mouth_open_ratio","blink_index",
  "left_eye_open_ratio","right_eye_open_ratio","palpebral_asymmetry","head_yaw_deg",
  "oral_instability_index","oculo_postural_index","facial_balance_index","gaze_stability_index"
].reduce((acc, id) => { acc[id] = document.getElementById(id); return acc; }, {});

let componentValue = {
  component_status: "idle",
  patient_id: null,
  patient_label: "",
  protocol_name: "free_observation",
  sample_count: 0,
  samples: [],
  metrics: {},
  pnev_indexes: {},
  meta: {},
};

function setFrameHeight() {
  Streamlit.setFrameHeight(document.body.scrollHeight + 20);
}

function setStatus(text, ok=false) {
  statusText.textContent = text;
  componentValue.component_status = text;
  statusDot.classList.toggle("ok", ok);
  setFrameHeight();
}

function updateField(id, value, digits=3, suffix="") {
  const el = fields[id];
  if (!el) return;
  if (value === null || value === undefined || Number.isNaN(value)) {
    el.textContent = "--";
  } else if (typeof value === "number") {
    el.textContent = value.toFixed(digits) + suffix;
  } else {
    el.textContent = String(value);
  }
}

function debug(text) {
  debugInfo.textContent = text;
}

function dist(a, b, w, h) {
  const dx = (a.x - b.x) * w;
  const dy = (a.y - b.y) * h;
  return Math.sqrt(dx * dx + dy * dy);
}

function eyeRatio(landmarks, top, bottom, left, right, w, h) {
  const v = dist(landmarks[top], landmarks[bottom], w, h);
  const hori = dist(landmarks[left], landmarks[right], w, h);
  return hori ? v / hori : 0;
}

function mouthRatio(landmarks, top, bottom, left, right, w, h) {
  const v = dist(landmarks[top], landmarks[bottom], w, h);
  const hori = dist(landmarks[left], landmarks[right], w, h);
  return hori ? v / hori : 0;
}

function headTiltDeg(landmarks) {
  const leftEye = landmarks[33];
  const rightEye = landmarks[263];
  return Math.atan2(rightEye.y - leftEye.y, rightEye.x - leftEye.x) * 180 / Math.PI;
}

function headYawDeg(landmarks) {
  const nose = landmarks[1];
  const leftCheek = landmarks[234];
  const rightCheek = landmarks[454];
  const leftD = Math.abs(nose.x - leftCheek.x);
  const rightD = Math.abs(rightCheek.x - nose.x);
  const sum = leftD + rightD;
  if (!sum) return 0;
  return ((rightD - leftD) / sum) * 45.0;
}

function computeGazeDirection(landmarks) {
  const leftIris = landmarks[468] || landmarks[159];
  const rightIris = landmarks[473] || landmarks[386];
  const leftEyeOuter = landmarks[33], leftEyeInner = landmarks[133];
  const rightEyeInner = landmarks[362], rightEyeOuter = landmarks[263];
  if (!leftIris || !rightIris) return "center";
  const leftRatio = (leftIris.x - leftEyeOuter.x) / Math.max((leftEyeInner.x - leftEyeOuter.x), 0.0001);
  const rightRatio = (rightEyeOuter.x - rightIris.x) / Math.max((rightEyeOuter.x - rightEyeInner.x), 0.0001);
  const horiz = (leftRatio + rightRatio) / 2;
  const eyeTop = (landmarks[159].y + landmarks[386].y)/2;
  const eyeBottom = (landmarks[145].y + landmarks[374].y)/2;
  const irisY = (leftIris.y + rightIris.y)/2;
  const vert = (irisY - eyeTop) / Math.max((eyeBottom - eyeTop), 0.0001);
  if (horiz < 0.38) return "left";
  if (horiz > 0.62) return "right";
  if (vert < 0.38) return "up";
  if (vert > 0.62) return "down";
  return "center";
}

function updateBlink(leftRatio, rightRatio) {
  const avg = (leftRatio + rightRatio) / 2;
  const now = performance.now();
  if (avg < 0.18 && (lastBlinkTs === null || now - lastBlinkTs > 250)) {
    blinkCount += 1;
    lastBlinkTs = now;
  }
  return blinkCount;
}

function gazeStabilityValue() {
  if (!gazeHistory.length) return 1;
  const counts = {};
  gazeHistory.forEach(g => counts[g] = (counts[g] || 0) + 1);
  return Math.max(...Object.values(counts)) / gazeHistory.length;
}

function drawMuscleZones(landmarks, w, h) {
  const zones = [
    {name:"orbicularis_oculi_sx", idx:[33,133,159,145], color:"rgba(34,197,94,0.16)"},
    {name:"orbicularis_oculi_dx", idx:[362,263,386,374], color:"rgba(34,197,94,0.16)"},
    {name:"orbicularis_oris", idx:[61,13,291,14], color:"rgba(245,158,11,0.16)"},
    {name:"frontalis", idx:[70,63,105,66], color:"rgba(56,189,248,0.14)"},
  ];
  zones.forEach(zone => {
    canvasCtx.beginPath();
    zone.idx.forEach((id, i) => {
      const p = landmarks[id];
      if (!p) return;
      const x = p.x * w, y = p.y * h;
      if (i === 0) canvasCtx.moveTo(x, y); else canvasCtx.lineTo(x, y);
    });
    canvasCtx.closePath();
    canvasCtx.fillStyle = zone.color;
    canvasCtx.fill();
  });
}

function drawOverlay(landmarks, width, height) {
  canvasCtx.clearRect(0, 0, width, height);
  drawConnectors(canvasCtx, landmarks, FACEMESH_TESSELATION, { color: "rgba(34,197,94,0.18)", lineWidth: 0.5 });
  drawConnectors(canvasCtx, landmarks, FACEMESH_LEFT_EYE, { color: "#22c55e", lineWidth: 1.2 });
  drawConnectors(canvasCtx, landmarks, FACEMESH_RIGHT_EYE, { color: "#22c55e", lineWidth: 1.2 });
  drawConnectors(canvasCtx, landmarks, FACEMESH_LEFT_IRIS, { color: "#38bdf8", lineWidth: 1.2 });
  drawConnectors(canvasCtx, landmarks, FACEMESH_RIGHT_IRIS, { color: "#38bdf8", lineWidth: 1.2 });
  drawConnectors(canvasCtx, landmarks, FACEMESH_LIPS, { color: "#f59e0b", lineWidth: 1.2 });
  drawMuscleZones(landmarks, width, height);
}

function snapshotDataUrl() {
  try { return canvasEl.toDataURL("image/png"); } catch(e) { return null; }
}

function sendValue(force=false) {
  componentValue.sample_count = samples.length;
  componentValue.samples = samples;
  if (force || frameCounter % SEND_EVERY_N_FRAMES === 0) {
    Streamlit.setComponentValue(componentValue);
  }
}

function resetSession() {
  sampleIndex = 0;
  blinkCount = 0;
  lastBlinkTs = null;
  gazeHistory = [];
  samples = [];
  sessionStartTs = performance.now();
  componentValue = {
    component_status: "idle",
    patient_id: patientId,
    patient_label: patientLabel,
    protocol_name: protocolName,
    sample_count: 0,
    samples: [],
    metrics: {},
    pnev_indexes: {},
    meta: { session_started_at: new Date().toISOString() },
  };
  ["gaze_direction","head_tilt_deg","mouth_open_ratio","blink_index","left_eye_open_ratio","right_eye_open_ratio","palpebral_asymmetry","head_yaw_deg","oral_instability_index","oculo_postural_index","facial_balance_index","gaze_stability_index"].forEach(id => updateField(id, null));
  debug("Sessione resettata");
  sendValue(true);
}

async function ensureFaceMesh() {
  if (faceMesh) return faceMesh;
  faceMesh = new FaceMesh({ locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}` });
  faceMesh.setOptions({ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 });
  faceMesh.onResults(onResults);
  return faceMesh;
}

function onResults(results) {
  frameCounter += 1;
  const width = results.image.width;
  const height = results.image.height;
  if (canvasEl.width !== width) canvasEl.width = width;
  if (canvasEl.height !== height) canvasEl.height = height;

  if (!results.multiFaceLandmarks || !results.multiFaceLandmarks.length) {
    overlayText.textContent = "Volto non rilevato: rimani frontale e ben illuminato";
    componentValue.meta = { ...componentValue.meta, face_detected: false, image_width: width, image_height: height };
    setStatus("no_face", false);
    sendValue();
    return;
  }

  const landmarks = results.multiFaceLandmarks[0];
  drawOverlay(landmarks, width, height);

  const leftEye = eyeRatio(landmarks, 159,145,33,133,width,height);
  const rightEye = eyeRatio(landmarks, 386,374,362,263,width,height);
  const mouth = mouthRatio(landmarks, 13,14,61,291,width,height);
  const tilt = headTiltDeg(landmarks);
  const yaw = headYawDeg(landmarks);
  const gaze = computeGazeDirection(landmarks);
  const asym = Math.abs(leftEye - rightEye);
  const blinkIdx = updateBlink(leftEye, rightEye);

  gazeHistory.push(gaze);
  if (gazeHistory.length > 90) gazeHistory.shift();
  const gazeStability = gazeStabilityValue();
  const oralInstability = Math.max(0, Math.min(1, mouth * 2.2));
  const oculoPostural = Math.max(0, Math.min(1, (Math.abs(tilt)/25)*0.4 + (Math.abs(yaw)/35)*0.35 + (asym*2.5)*0.25));
  const facialBalance = Math.max(0, Math.min(1, 1 - asym*4));

  const ts = Math.round(performance.now() - sessionStartTs);
  samples.push({
    ts_ms: ts,
    gaze_x: Number((((landmarks[468]?.x || landmarks[159].x) + (landmarks[473]?.x || landmarks[386].x))/2 * width).toFixed(2)),
    gaze_y: Number((((landmarks[468]?.y || landmarks[159].y) + (landmarks[473]?.y || landmarks[386].y))/2 * height).toFixed(2)),
    confidence: 1.0,
    fixation_flag: gaze === "center",
    saccade_flag: gaze !== "center",
    blink_flag: leftEye < 0.18 || rightEye < 0.18,
    eye_left_x: Number((landmarks[468]?.x || landmarks[159].x * width).toFixed ? (landmarks[468]?.x || landmarks[159].x) * width : landmarks[159].x * width),
    eye_left_y: Number((landmarks[468]?.y || landmarks[159].y) * height),
    eye_right_x: Number((landmarks[473]?.x || landmarks[386].x) * width),
    eye_right_y: Number((landmarks[473]?.y || landmarks[386].y) * height),
    target_label: protocolName,
    source_vendor: "browser_facemesh",
    source_format: "streamlit_component",
  });
  if (samples.length > MAX_SAMPLES) samples = samples.slice(-MAX_SAMPLES);

  componentValue.patient_id = patientId;
  componentValue.patient_label = patientLabel;
  componentValue.protocol_name = protocolName;
  componentValue.metrics = {
    gaze_direction: gaze,
    head_tilt_deg: Number(tilt.toFixed(2)),
    mouth_open_ratio: Number(mouth.toFixed(4)),
    left_eye_open_ratio: Number(leftEye.toFixed(4)),
    right_eye_open_ratio: Number(rightEye.toFixed(4)),
    palpebral_asymmetry: Number(asym.toFixed(4)),
    blink_index: blinkIdx,
    head_yaw_deg: Number(yaw.toFixed(2)),
  };
  componentValue.pnev_indexes = {
    oral_instability_index: Number(oralInstability.toFixed(4)),
    oculo_postural_index: Number(oculoPostural.toFixed(4)),
    facial_balance_index: Number(facialBalance.toFixed(4)),
    gaze_stability_index: Number(gazeStability.toFixed(4)),
  };
  componentValue.meta = {
    face_detected: true,
    frame_count: frameCounter,
    image_width: width,
    image_height: height,
    session_started_at: new Date(Date.now() - ts).toISOString(),
    snapshot_png_dataurl: snapshotDataUrl(),
    component_kind: "custom_streamlit_component",
  };

  updateField("gaze_direction", gaze);
  updateField("head_tilt_deg", tilt, 1, "°");
  updateField("mouth_open_ratio", mouth);
  updateField("blink_index", blinkIdx, 0, "");
  updateField("left_eye_open_ratio", leftEye);
  updateField("right_eye_open_ratio", rightEye);
  updateField("palpebral_asymmetry", asym);
  updateField("head_yaw_deg", yaw, 1, "°");
  updateField("oral_instability_index", oralInstability);
  updateField("oculo_postural_index", oculoPostural);
  updateField("facial_balance_index", facialBalance);
  updateField("gaze_stability_index", gazeStability);

  overlayText.textContent = `FaceMesh attivo • campioni: ${samples.length}`;
  debug(`Status: tracking\nSamples: ${samples.length}\nYaw: ${yaw.toFixed(1)}°\nTilt: ${tilt.toFixed(1)}°`);
  setStatus("tracking", true);
  sendValue();
}

async function startCamera() {
  try {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error("Browser non compatibile con webcam");
    overlayText.textContent = "Richiesta accesso webcam...";
    setStatus("requesting_camera", false);

    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user", width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    videoEl.srcObject = stream;
    await videoEl.play();
    await ensureFaceMesh();

    if (mpCamera && typeof mpCamera.stop === "function") {
      try { mpCamera.stop(); } catch(e) {}
    }

    resetSession();
    mpCamera = new Camera(videoEl, {
      onFrame: async () => { await faceMesh.send({ image: videoEl }); },
      width: 1280,
      height: 720,
    });
    mpCamera.start();
    overlayText.textContent = "Webcam attiva";
    setStatus("camera_on", true);
  } catch (err) {
    console.error(err);
    overlayText.textContent = "Errore accesso webcam";
    debug(String(err));
    setStatus("camera_error", false);
    sendValue(true);
  }
}

function stopCamera() {
  try {
    if (mpCamera && typeof mpCamera.stop === "function") mpCamera.stop();
    if (stream) stream.getTracks().forEach(t => t.stop());
    stream = null;
    videoEl.srcObject = null;
    overlayText.textContent = "Camera fermata";
    setStatus("stopped", false);
    sendValue(true);
  } catch (err) {
    console.error(err);
    debug(String(err));
    setStatus("stop_error", false);
  }
}

function snapshotPng() {
  const url = snapshotDataUrl();
  if (!url) return;
  const a = document.createElement("a");
  a.href = url;
  a.download = `gaze_snapshot_${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
  a.click();
}

function onRender(event) {
  const args = (event.detail && event.detail.args) || {};
  patientId = args.patient_id ?? null;
  patientLabel = args.patient_label || "";
  protocolName = args.protocol_name || "free_observation";
  patientInfo.textContent = `Paziente: ${patientLabel || "non specificato"}${patientId !== null && patientId !== undefined ? ` • ID: ${patientId}` : ""}`;
  componentValue.patient_id = patientId;
  componentValue.patient_label = patientLabel;
  componentValue.protocol_name = protocolName;
  Streamlit.setComponentReady();
  setFrameHeight();
}

document.getElementById("startBtn").addEventListener("click", startCamera);
document.getElementById("stopBtn").addEventListener("click", stopCamera);
document.getElementById("snapshotBtn").addEventListener("click", snapshotPng);
document.getElementById("resetBtn").addEventListener("click", resetSession);

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
setFrameHeight();
