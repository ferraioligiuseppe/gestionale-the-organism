from __future__ import annotations

import json


def get_webcam_browser_v3_html(
    paziente_id: int | None = None,
    paziente_label: str | None = None,
) -> str:
    paziente_id_js = "null" if paziente_id is None else str(paziente_id)
    paziente_label_js = json.dumps(paziente_label or "", ensure_ascii=False)

    return f"""
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>The Organism • Webcam AI V3</title>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
  <style>
    :root {{
      --bg: #0f172a; --panel: #111827; --card: #1f2937; --text: #f8fafc;
      --muted: #cbd5e1; --line: #334155; --accent: #10b981;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: var(--bg); color: var(--text); padding: 10px; }}
    .app {{ min-height: 100vh; }}
    .topbar {{ display: flex; justify-content: space-between; gap: 12px; align-items: flex-start; margin-bottom: 12px; flex-wrap: wrap; }}
    .topbar h1 {{ margin: 0 0 4px 0; font-size: 24px; }}
    .topbar p {{ margin: 0; color: var(--muted); }}
    .actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    button {{ background: var(--accent); color: #062b1f; border: none; padding: 10px 14px; border-radius: 10px; font-weight: 700; cursor: pointer; }}
    .layout {{ display: grid; grid-template-columns: 2fr 1fr; gap: 14px; }}
    .stage {{ position: relative; background: #020617; border: 1px solid var(--line); border-radius: 16px; overflow: hidden; aspect-ratio: 4 / 3; }}
    video, canvas {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
    canvas {{ z-index: 2; }}
    video {{ z-index: 1; object-fit: cover; }}
    .statusbar {{ margin-top: 10px; padding: 10px 12px; background: var(--panel); border: 1px solid var(--line); border-radius: 12px; color: var(--muted); }}
    .panel {{ display: flex; flex-direction: column; gap: 12px; }}
    .card {{ background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 14px; }}
    .card h2 {{ margin: 0 0 12px 0; font-size: 18px; }}
    label {{ display: block; font-size: 13px; color: var(--muted); margin: 10px 0 6px; }}
    input, select, textarea {{ width: 100%; padding: 10px 12px; border-radius: 10px; border: 1px solid #475569; background: #fff; color: #111827; }}
    .metrics {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    .metric {{ background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 10px; }}
    .metric span {{ display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }}
    .metric strong {{ font-size: 16px; }}
    pre {{ background: #020617; color: #dbeafe; padding: 12px; border-radius: 12px; overflow: auto; max-height: 260px; white-space: pre-wrap; word-break: break-word; }}
    .note {{ font-size: 12px; color: var(--muted); margin-top: 8px; }}
    @media (max-width: 1100px) {{ .layout {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <div class="app">
    <header class="topbar">
      <div>
        <h1>The Organism • Webcam AI V3</h1>
        <p>Integrata nel gestionale: volto, occhi, bocca, asse del capo, stima sguardo, export JSON e snapshot overlay.</p>
      </div>
      <div class="actions">
        <button id="startBtn">Avvia webcam</button>
        <button id="stopBtn">Ferma webcam</button>
        <button id="snapshotBtn">Scarica overlay</button>
        <button id="exportBtn">Esporta JSON</button>
      </div>
    </header>

    <main class="layout">
      <section class="viewer">
        <div class="stage">
          <video id="video" width="960" height="720" autoplay muted playsinline></video>
          <canvas id="canvas" width="960" height="720"></canvas>
        </div>
        <div class="statusbar"><span id="statusText">In attesa di avvio...</span></div>
      </section>

      <aside class="panel">
        <div class="card">
          <h2>Contesto</h2>
          <label>Paziente</label>
          <input id="patientLabel" type="text" />
          <label>Operatore</label>
          <input id="operatorLabel" type="text" placeholder="Operatore" />
          <label>Protocollo</label>
          <select id="protocolSelect">
            <option value="reading_standard">Reading standard</option>
            <option value="visual_attention">Visual attention</option>
            <option value="oculomotor_screening">Oculomotor screening</option>
            <option value="binocularity_basic">Binocularity basic</option>
          </select>
          <label>Note</label>
          <textarea id="notes" rows="4" placeholder="Note cliniche"></textarea>
          <div class="note">Il paziente è precompilato dal gestionale quando disponibile.</div>
        </div>

        <div class="card">
          <h2>Metriche live</h2>
          <div class="metrics">
            <div class="metric"><span>Gaze</span><strong id="gazeLabel">-</strong></div>
            <div class="metric"><span>Head tilt</span><strong id="headTilt">-</strong></div>
            <div class="metric"><span>Oral state</span><strong id="oralState">-</strong></div>
            <div class="metric"><span>Mouth ratio</span><strong id="mouthRatio">-</strong></div>
            <div class="metric"><span>L eye open</span><strong id="leftEyeOpen">-</strong></div>
            <div class="metric"><span>R eye open</span><strong id="rightEyeOpen">-</strong></div>
            <div class="metric"><span>Palpebral asym</span><strong id="palpebralAsym">-</strong></div>
            <div class="metric"><span>Blink index</span><strong id="blinkIndex">-</strong></div>
          </div>
        </div>

        <div class="card">
          <h2>Indici sintetici</h2>
          <div class="metrics">
            <div class="metric"><span>Oral instability</span><strong id="oralInstability">-</strong></div>
            <div class="metric"><span>Oculo-postural</span><strong id="oculoPostural">-</strong></div>
            <div class="metric"><span>Facial balance</span><strong id="facialBalance">-</strong></div>
            <div class="metric"><span>Gaze stability</span><strong id="gazeStability">-</strong></div>
          </div>
        </div>

        <div class="card">
          <h2>Ultimo JSON</h2>
          <pre id="jsonOutput">{{}}</pre>
        </div>
      </aside>
    </main>
  </div>

  <script>
    const INITIAL_CONTEXT = {{ paziente_id: {paziente_id_js}, paziente_label: {paziente_label_js} }};
    const video = document.getElementById("video");
    const canvas = document.getElementById("canvas");
    const ctx = canvas.getContext("2d");
    const statusText = document.getElementById("statusText");
    const startBtn = document.getElementById("startBtn");
    const stopBtn = document.getElementById("stopBtn");
    const snapshotBtn = document.getElementById("snapshotBtn");
    const exportBtn = document.getElementById("exportBtn");
    const patientLabelEl = document.getElementById("patientLabel");
    const operatorLabelEl = document.getElementById("operatorLabel");
    const protocolSelectEl = document.getElementById("protocolSelect");
    const notesEl = document.getElementById("notes");
    const jsonOutputEl = document.getElementById("jsonOutput");
    const gazeLabelEl = document.getElementById("gazeLabel");
    const headTiltEl = document.getElementById("headTilt");
    const oralStateEl = document.getElementById("oralState");
    const mouthRatioEl = document.getElementById("mouthRatio");
    const leftEyeOpenEl = document.getElementById("leftEyeOpen");
    const rightEyeOpenEl = document.getElementById("rightEyeOpen");
    const palpebralAsymEl = document.getElementById("palpebralAsym");
    const blinkIndexEl = document.getElementById("blinkIndex");
    const oralInstabilityEl = document.getElementById("oralInstability");
    const oculoPosturalEl = document.getElementById("oculoPostural");
    const facialBalanceEl = document.getElementById("facialBalance");
    const gazeStabilityEl = document.getElementById("gazeStability");
    let stream = null;
    let camera = null;
    let lastAnalysis = {};

    if (INITIAL_CONTEXT && INITIAL_CONTEXT.paziente_label) patientLabelEl.value = INITIAL_CONTEXT.paziente_label;

    const LEFT_IRIS = [474, 475, 476, 477];
    const RIGHT_IRIS = [469, 470, 471, 472];
    const LEFT_EYE_OUTER = 33;
    const LEFT_EYE_INNER = 133;
    const RIGHT_EYE_INNER = 362;
    const RIGHT_EYE_OUTER = 263;
    const LEFT_UPPER_LID = 159;
    const LEFT_LOWER_LID = 145;
    const RIGHT_UPPER_LID = 386;
    const RIGHT_LOWER_LID = 374;
    const UPPER_LIP = 13;
    const LOWER_LIP = 14;
    const FOREHEAD = 10;
    const CHIN = 152;

    function setStatus(text) {{ statusText.textContent = text; }}
    function meanPoint(landmarks, ids) {{
      const pts = ids.map(i => landmarks[i]).filter(Boolean);
      if (!pts.length) return null;
      return {{ x: pts.reduce((s, p) => s + p.x, 0) / pts.length, y: pts.reduce((s, p) => s + p.y, 0) / pts.length }};
    }}
    function dist(a, b) {{ if (!a || !b) return null; return Math.hypot(a.x - b.x, a.y - b.y); }}
    function horizontalRatio(center, outer, inner) {{
      const width = inner.x - outer.x;
      if (Math.abs(width) < 1e-6) return 0;
      return ((center.x - outer.x) / width) - 0.5;
    }}
    function computeMetrics(landmarks) {{
      const leftIris = meanPoint(landmarks, LEFT_IRIS);
      const rightIris = meanPoint(landmarks, RIGHT_IRIS);
      const leftOuter = landmarks[LEFT_EYE_OUTER];
      const leftInner = landmarks[LEFT_EYE_INNER];
      const rightInner = landmarks[RIGHT_EYE_INNER];
      const rightOuter = landmarks[RIGHT_EYE_OUTER];
      const leftUpper = landmarks[LEFT_UPPER_LID];
      const leftLower = landmarks[LEFT_LOWER_LID];
      const rightUpper = landmarks[RIGHT_UPPER_LID];
      const rightLower = landmarks[RIGHT_LOWER_LID];
      const mouthUp = landmarks[UPPER_LIP];
      const mouthLow = landmarks[LOWER_LIP];
      const forehead = landmarks[FOREHEAD];
      const chin = landmarks[CHIN];
      const faceHeight = dist(forehead, chin);
      const mouthOpen = dist(mouthUp, mouthLow);
      const leftEyeWidth = dist(leftOuter, leftInner);
      const rightEyeWidth = dist(rightInner, rightOuter);
      const leftEyeOpen = dist(leftUpper, leftLower);
      const rightEyeOpen = dist(rightUpper, rightLower);
      const mouthOpenRatio = faceHeight && mouthOpen ? +(mouthOpen / faceHeight).toFixed(4) : null;
      const leftEyeOpenRatio = leftEyeWidth && leftEyeOpen ? +(leftEyeOpen / leftEyeWidth).toFixed(4) : null;
      const rightEyeOpenRatio = rightEyeWidth && rightEyeOpen ? +(rightEyeOpen / rightEyeWidth).toFixed(4) : null;
      const palpebralAsymmetry = leftEyeOpenRatio != null && rightEyeOpenRatio != null ? +Math.abs(leftEyeOpenRatio - rightEyeOpenRatio).toFixed(4) : null;
      let headTiltDeg = null;
      if (forehead && chin) {{
        const dx = chin.x - forehead.x;
        const dy = chin.y - forehead.y;
        headTiltDeg = +(Math.atan2(dx, dy) * 180 / Math.PI).toFixed(2);
      }}
      let oralState = "chiusa";
      if (mouthOpenRatio != null) {{
        if (mouthOpenRatio >= 0.09) oralState = "aperta";
        else if (mouthOpenRatio >= 0.05) oralState = "semiaperta";
      }}
      let gazeDirection = "non_determinabile";
      let horizontalScore = null;
      let verticalScore = null;
      if (leftIris && rightIris && leftOuter && leftInner && rightInner && rightOuter) {{
        const leftH = horizontalRatio(leftIris, leftOuter, leftInner);
        const rightH = horizontalRatio(rightIris, rightInner, rightOuter);
        horizontalScore = +((leftH + rightH) / 2).toFixed(4);
        const leftMidY = (leftOuter.y + leftInner.y) / 2;
        const rightMidY = (rightOuter.y + rightInner.y) / 2;
        verticalScore = +((((leftIris.y - leftMidY) + (rightIris.y - rightMidY)) / 2) / 0.03).toFixed(4);
        gazeDirection = "centrale";
        if (horizontalScore < -0.08) gazeDirection = "sinistra";
        else if (horizontalScore > 0.08) gazeDirection = "destra";
        if (verticalScore < -0.12) gazeDirection = gazeDirection !== "centrale" ? `${gazeDirection}-alto` : "alto";
        else if (verticalScore > 0.12) gazeDirection = gazeDirection !== "centrale" ? `${gazeDirection}-basso` : "basso";
      }}
      const blinkDetected = leftEyeOpenRatio != null && rightEyeOpenRatio != null && leftEyeOpenRatio < 0.12 && rightEyeOpenRatio < 0.12;
      const blinkIndex = blinkDetected ? "blink" : "open";
      const oralInstability = mouthOpenRatio != null && palpebralAsymmetry != null ? +((mouthOpenRatio * 100) + (palpebralAsymmetry * 40)).toFixed(2) : null;
      const oculoPostural = palpebralAsymmetry != null && headTiltDeg != null ? +((Math.abs(headTiltDeg) * 0.7) + (palpebralAsymmetry * 100)).toFixed(2) : null;
      const facialBalance = palpebralAsymmetry != null && headTiltDeg != null ? +(Math.max(0, 100 - (Math.abs(headTiltDeg) * 2.5) - (palpebralAsymmetry * 120))).toFixed(2) : null;
      let gazeStability = 50;
      if (gazeDirection === "centrale") gazeStability = 85;
      else if (["sinistra","destra","alto","basso"].includes(gazeDirection)) gazeStability = 65;
      else if (gazeDirection !== "non_determinabile") gazeStability = 55;
      return {{
        gaze_direction_label: gazeDirection, gaze_horizontal_score: horizontalScore, gaze_vertical_score: verticalScore,
        head_tilt_deg: headTiltDeg, oral_state: oralState, mouth_open_ratio: mouthOpenRatio,
        left_eye_open_ratio: leftEyeOpenRatio, right_eye_open_ratio: rightEyeOpenRatio,
        palpebral_asymmetry: palpebralAsymmetry, blink_index: blinkIndex,
        oral_instability_index: oralInstability, oculo_postural_index: oculoPostural,
        facial_balance_index: facialBalance, gaze_stability_index: gazeStability,
      }};
    }}
    function updatePanel(metrics) {{
      gazeLabelEl.textContent = metrics.gaze_direction_label ?? "-";
      headTiltEl.textContent = metrics.head_tilt_deg ?? "-";
      oralStateEl.textContent = metrics.oral_state ?? "-";
      mouthRatioEl.textContent = metrics.mouth_open_ratio ?? "-";
      leftEyeOpenEl.textContent = metrics.left_eye_open_ratio ?? "-";
      rightEyeOpenEl.textContent = metrics.right_eye_open_ratio ?? "-";
      palpebralAsymEl.textContent = metrics.palpebral_asymmetry ?? "-";
      blinkIndexEl.textContent = metrics.blink_index ?? "-";
      oralInstabilityEl.textContent = metrics.oral_instability_index ?? "-";
      oculoPosturalEl.textContent = metrics.oculo_postural_index ?? "-";
      facialBalanceEl.textContent = metrics.facial_balance_index ?? "-";
      gazeStabilityEl.textContent = metrics.gaze_stability_index ?? "-";
    }}
    function currentContext() {{
      return {{
        paziente_id: INITIAL_CONTEXT.paziente_id ?? null,
        patient_label: patientLabelEl.value || "",
        operator_name: operatorLabelEl.value || "",
        protocol_name: protocolSelectEl.value || "reading_standard",
        notes: notesEl.value || "",
        timestamp: new Date().toISOString(),
        source: "gestionale_browser_v3",
      }};
    }}
    function updateJson(metrics) {{
      lastAnalysis = {{ context: currentContext(), metrics }};
      jsonOutputEl.textContent = JSON.stringify(lastAnalysis, null, 2);
    }}
    function drawOverlay(results, metrics) {{
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!results.multiFaceLandmarks || !results.multiFaceLandmarks.length) return;
      const landmarks = results.multiFaceLandmarks[0];
      drawConnectors(ctx, landmarks, FACEMESH_TESSELATION, {{ color: "#10b981", lineWidth: 1 }});
      drawConnectors(ctx, landmarks, FACEMESH_LEFT_EYE, {{ color: "#38bdf8", lineWidth: 2 }});
      drawConnectors(ctx, landmarks, FACEMESH_RIGHT_EYE, {{ color: "#38bdf8", lineWidth: 2 }});
      drawConnectors(ctx, landmarks, FACEMESH_LIPS, {{ color: "#fb923c", lineWidth: 2 }});
      drawConnectors(ctx, landmarks, FACEMESH_LEFT_IRIS, {{ color: "#facc15", lineWidth: 2 }});
      drawConnectors(ctx, landmarks, FACEMESH_RIGHT_IRIS, {{ color: "#facc15", lineWidth: 2 }});
      ctx.fillStyle = "#ffffff";
      ctx.font = "18px Arial";
      ctx.fillText(`Gaze: ${metrics.gaze_direction_label ?? "-"}`, 16, 28);
      ctx.fillText(`Head tilt: ${metrics.head_tilt_deg ?? "-"}`, 16, 52);
      ctx.fillText(`Oral: ${metrics.oral_state ?? "-"}`, 16, 76);
    }}
    const faceMesh = new FaceMesh({{ locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}` }});
    faceMesh.setOptions({{ maxNumFaces: 1, refineLandmarks: true, minDetectionConfidence: 0.5, minTrackingConfidence: 0.5 }});
    faceMesh.onResults((results) => {{
      if (!results.multiFaceLandmarks || !results.multiFaceLandmarks.length) {{
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        setStatus("Nessun volto rilevato.");
        return;
      }}
      const metrics = computeMetrics(results.multiFaceLandmarks[0]);
      drawOverlay(results, metrics);
      updatePanel(metrics);
      updateJson(metrics);
      setStatus(`Tracking attivo • ${metrics.gaze_direction_label || "gaze ?"}`);
    }});
    async function startCamera() {{
      try {{
        if (stream) return;
        stream = await navigator.mediaDevices.getUserMedia({{ video: {{ width: 960, height: 720 }} }});
        video.srcObject = stream;
        camera = new Camera(video, {{
          onFrame: async () => {{ await faceMesh.send({{ image: video }}); }},
          width: 960, height: 720
        }});
        camera.start();
        setStatus("Webcam attiva.");
      }} catch (err) {{
        console.error(err);
        setStatus("Errore apertura webcam.");
        alert("Impossibile aprire la webcam. Controlla permessi browser e fotocamera.");
      }}
    }}
    function stopCamera() {{
      try {{ if (camera && camera.stop) camera.stop(); }} catch (e) {{}}
      if (stream) stream.getTracks().forEach(track => track.stop());
      stream = null; camera = null; video.srcObject = null;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      setStatus("Webcam fermata.");
    }}
    function exportJson() {{
      const blob = new Blob([JSON.stringify(lastAnalysis, null, 2)], {{ type: "application/json" }});
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `the_organism_webcam_ai_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(a.href);
    }}
    function saveSnapshot() {{
      const a = document.createElement("a");
      a.href = canvas.toDataURL("image/png");
      a.download = `the_organism_webcam_overlay_${Date.now()}.png`;
      a.click();
    }}
    startBtn.addEventListener("click", startCamera);
    stopBtn.addEventListener("click", stopCamera);
    exportBtn.addEventListener("click", exportJson);
    snapshotBtn.addEventListener("click", saveSnapshot);
    setStatus("Premi 'Avvia webcam' per iniziare.");
  </script>
</body>
</html>
"""
