const state = {
  args: { mode: "calibration", task: {} },
  samples: [],
  tracking: false,
  stream: null,
  targetIndex: 0,
  intervalId: null,
  startedAt: 0,
  currentPrediction: null,
};

const statusEl = document.getElementById("status");
const surfaceEl = document.getElementById("surface");
const dotEl = document.getElementById("gaze-dot");
const videoEl = document.getElementById("preview");
const startBtn = document.getElementById("start-btn");
const stopBtn = document.getElementById("stop-btn");
const clearBtn = document.getElementById("clear-btn");

function updateStatus(msg) {
  statusEl.textContent = msg;
}

function setFrameHeight(h) {
  const nextH = Math.max(500, Number(h || 760) - 110);
  document.getElementById("surface-wrap").style.height = `${nextH}px`;
  Streamlit.setFrameHeight(nextH + 130);
}

function getTargets() {
  return (state.args.task && state.args.task.targets) || [];
}

function clearTargets() {
  surfaceEl.innerHTML = "";
}

function drawTargets() {
  clearTargets();
  const targets = getTargets();
  targets.forEach((t, idx) => {
    const el = document.createElement("div");
    el.className = "target" + (idx === state.targetIndex ? " active" : "");
    el.style.left = `${t.x}px`;
    el.style.top = `${t.y}px`;
    el.title = t.label || `${idx + 1}`;
    surfaceEl.appendChild(el);
  });
}

function pushSample(data) {
  const ts = Math.round(performance.now() - state.startedAt);
  const target = getTargets()[state.targetIndex] || null;
  state.samples.push({
    ts_ms: ts,
    gaze_x: data ? Math.round(data.x) : null,
    gaze_y: data ? Math.round(data.y) : null,
    confidence: data ? 0.8 : 0.0,
    target_label: target ? (target.label || null) : null,
    tracking_ok: !!data,
  });
}

function publishPayload(final = false) {
  const payload = {
    mode: state.args.mode,
    final,
    sample_count: state.samples.length,
    samples: state.samples.slice(-6000),
    calibration_score: state.samples.length ? 0.75 : null,
    component_status: state.tracking ? "running" : "stopped",
    note: "Prototype WebGazer via CDN."
  };
  Streamlit.setComponentValue(payload);
}

function advanceTarget() {
  const targets = getTargets();
  if (!targets.length) return;
  state.targetIndex = (state.targetIndex + 1) % targets.length;
  drawTargets();
}

async function ensureCamera() {
  if (state.stream) return state.stream;
  const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  state.stream = stream;
  videoEl.srcObject = stream;
  return stream;
}

async function startTracking() {
  try {
    await ensureCamera();
    if (!window.webgazer) {
      updateStatus("WebGazer non disponibile.");
      return;
    }

    state.samples = [];
    state.targetIndex = 0;
    drawTargets();
    state.startedAt = performance.now();
    state.tracking = true;
    dotEl.style.display = "block";

    window.webgazer
      .showVideoPreview(false)
      .showFaceOverlay(false)
      .showPredictionPoints(false)
      .setGazeListener((data) => {
        state.currentPrediction = data;
        if (data && Number.isFinite(data.x) && Number.isFinite(data.y)) {
          dotEl.style.left = `${data.x}px`;
          dotEl.style.top = `${data.y}px`;
        }
      });

    await window.webgazer.begin();

    if (state.intervalId) clearInterval(state.intervalId);
    state.intervalId = setInterval(() => {
      pushSample(state.currentPrediction);
      if (state.args.mode === "calibration" || state.args.mode === "saccadi_orizzontali") {
        if (state.samples.length % 45 === 0) advanceTarget();
      }
      if (state.samples.length % 30 === 0) publishPayload(false);
    }, 33);

    updateStatus("Tracking attivo.");
  } catch (err) {
    console.error(err);
    updateStatus("Impossibile accedere alla webcam o inizializzare WebGazer.");
  }
}

function stopTracking() {
  state.tracking = false;
  if (state.intervalId) clearInterval(state.intervalId);
  state.intervalId = null;
  if (window.webgazer) {
    try { window.webgazer.pause(); } catch (e) {}
  }
  dotEl.style.display = "none";
  publishPayload(true);
  updateStatus(`Tracking fermato. Campioni: ${state.samples.length}`);
}

function clearTracking() {
  state.samples = [];
  state.targetIndex = 0;
  drawTargets();
  publishPayload(false);
  updateStatus("Campioni azzerati.");
}

startBtn.addEventListener("click", startTracking);
stopBtn.addEventListener("click", stopTracking);
clearBtn.addEventListener("click", clearTracking);

function onRender(event) {
  const { args, disabled, theme } = event.detail;
  state.args = args || { mode: "calibration", task: {} };
  setFrameHeight(args.height || 760);
  drawTargets();
  updateStatus(`Modalità: ${state.args.mode || "-"}`);
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, onRender);
Streamlit.setComponentReady();
Streamlit.setFrameHeight(820);
