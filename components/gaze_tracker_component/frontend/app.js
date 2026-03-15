let stream = null;
let sampleTimer = null;
let samples = [];
let componentValue = {
  component_status: "idle",
  sample_count: 0,
  calibration_score: null,
  samples: [],
};

const videoEl = document.getElementById("video");
const statusEl = document.getElementById("status");
const infoEl = document.getElementById("info");
const overlayEl = document.getElementById("overlay");
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");

function setStatus(text) {
  statusEl.textContent = text;
  componentValue.component_status = text;
  sendValue();
}

function sendValue() {
  componentValue.sample_count = samples.length;
  componentValue.samples = samples.slice(-500);
  Streamlit.setComponentValue(componentValue);
}

function setFrameHeight() {
  Streamlit.setFrameHeight(document.body.scrollHeight + 20);
}

async function startCamera() {
  try {
    overlayEl.textContent = "Richiesta accesso webcam...";
    setStatus("requesting_camera");

    stream = await navigator.mediaDevices.getUserMedia({
      video: true,
      audio: false,
    });

    videoEl.srcObject = stream;
    overlayEl.textContent = "";
    infoEl.textContent = "Webcam attiva";
    setStatus("camera_on");

    samples = [];
    const t0 = performance.now();

    if (sampleTimer) {
      clearInterval(sampleTimer);
    }

    sampleTimer = setInterval(() => {
      const ts = Math.round(performance.now() - t0);

      samples.push({
        ts_ms: ts,
        gaze_x: null,
        gaze_y: null,
        confidence: 0.0,
        tracking_ok: true,
      });

      sendValue();
    }, 100);

    setFrameHeight();
  } catch (err) {
    console.error(err);
    overlayEl.textContent = "Errore accesso webcam";
    infoEl.textContent = String(err);
    setStatus("camera_error");
  }
}

function stopCamera() {
  try {
    if (sampleTimer) {
      clearInterval(sampleTimer);
      sampleTimer = null;
    }

    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
      stream = null;
    }

    videoEl.srcObject = null;
    overlayEl.textContent = "Camera fermata";
    infoEl.textContent = "Sessione fermata";
    setStatus("stopped");
    sendValue();
    setFrameHeight();
  } catch (err) {
    console.error(err);
    infoEl.textContent = String(err);
    setStatus("stop_error");
  }
}

startBtn.addEventListener("click", startCamera);
stopBtn.addEventListener("click", stopCamera);

function onRender(event) {
  const data = event.detail;
  const args = data.args || {};

  infoEl.textContent = `Mode: ${args.mode || "n/a"}`;
  setFrameHeight();
  Streamlit.setComponentReady();
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
setFrameHeight();
