# modules/gaze_tracking/webcam_browser_v3_embed.py

from __future__ import annotations

import json


def get_webcam_browser_v3_html(paziente_id=None, paziente_label="") -> str:
    patient_id_json = json.dumps(paziente_id)
    patient_label_json = json.dumps(paziente_label or "")

    html = """
<!DOCTYPE html>
<html lang="it">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/camera_utils/camera_utils.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/drawing_utils/drawing_utils.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/face_mesh.js"></script>
  <style>
    :root {
      --bg: #0f172a; --panel: #111827; --card: #1f2937; --line: #334155; --text: #e5e7eb;
      --muted: #94a3b8; --ok: #22c55e; --warn: #f59e0b; --accent: #16a34a; --danger: #ef4444;
      --cyan: #38bdf8; --amber: #f59e0b; --pink: #f472b6;
    }
    * { box-sizing: border-box; font-family: Arial, Helvetica, sans-serif; }
    body { margin: 0; padding: 0; background: var(--bg); color: var(--text); }
    .wrap { width: 100%; padding: 14px; background: linear-gradient(180deg, #0f172a 0%, #111827 100%); }
    .header { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 12px; padding: 12px 14px; background: rgba(255,255,255,0.04); border: 1px solid var(--line); border-radius: 14px; }
    .title { font-size: 18px; font-weight: 700; color: white; }
    .subtitle { font-size: 12px; color: var(--muted); }
    .patient { font-size: 13px; color: #d1fae5; }
    .status { display: inline-flex; align-items: center; gap: 8px; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--line); background: rgba(255,255,255,0.03); font-size: 12px; color: var(--muted); }
    .dot { width: 10px; height: 10px; border-radius: 999px; background: var(--warn); box-shadow: 0 0 8px rgba(245, 158, 11, 0.6); }
    .dot.ok { background: var(--ok); box-shadow: 0 0 8px rgba(34, 197, 94, 0.6); }
    .main-grid { display: grid; grid-template-columns: 1.35fr 0.95fr; gap: 14px; }
    .card { background: rgba(255,255,255,0.04); border: 1px solid var(--line); border-radius: 16px; overflow: hidden; backdrop-filter: blur(4px); }
    .card-head { padding: 10px 14px; border-bottom: 1px solid var(--line); font-size: 14px; font-weight: 700; color: #f8fafc; background: rgba(255,255,255,0.03); }
    .viewer { padding: 12px; }
    .video-stage { position: relative; width: 100%; aspect-ratio: 16 / 9; background: #020617; border-radius: 14px; overflow: hidden; border: 1px solid #1e293b; }
    video, canvas { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; transform: scaleX(-1); }
    video { opacity: 0.16; }
    canvas { z-index: 2; }
    .controls { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px; border-top: 1px solid var(--line); background: rgba(255,255,255,0.025); }
    button { border: 1px solid #166534; background: linear-gradient(180deg, #16a34a 0%, #15803d 100%); color: white; padding: 10px 14px; border-radius: 12px; font-size: 13px; font-weight: 700; cursor: pointer; transition: 0.18s ease; }
    button:hover { transform: translateY(-1px); filter: brightness(1.05); }
    button.secondary { background: linear-gradient(180deg, #334155 0%, #1f2937 100%); border: 1px solid #475569; color: #e5e7eb; }
    button.danger { background: linear-gradient(180deg, #dc2626 0%, #b91c1c 100%); border: 1px solid #ef4444; }
    .toggle { display: inline-flex; align-items: center; gap: 6px; padding: 10px 12px; border-radius: 12px; background: rgba(255,255,255,0.03); border: 1px solid #475569; }
    .right-panel { display: grid; grid-template-rows: auto auto auto 1fr; gap: 14px; }
    .metrics-grid, .indexes-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; padding: 12px; }
    .metric { background: rgba(255,255,255,0.035); border: 1px solid #334155; border-radius: 14px; padding: 12px; min-height: 76px; }
    .metric-label { font-size: 11px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin-bottom: 6px; }
    .metric-value { font-size: 20px; font-weight: 800; color: white; line-height: 1.1; }
    .metric-sub { margin-top: 4px; font-size: 11px; color: #cbd5e1; }
    .index-box { background: rgba(22, 163, 74, 0.08); border: 1px solid rgba(34, 197, 94, 0.28); border-radius: 14px; padding: 12px; }
    .index-label { font-size: 11px; text-transform: uppercase; color: #bbf7d0; margin-bottom: 6px; }
    .index-value { font-size: 22px; font-weight: 800; color: #dcfce7; }
    .json-wrap { padding: 12px; }
    .info-box { padding: 12px; font-size: 12px; color: #cbd5e1; }
    pre { margin: 0; max-height: 360px; overflow: auto; background: #020617; color: #dbeafe; border: 1px solid #1e293b; border-radius: 14px; padding: 12px; font-size: 12px; line-height: 1.4; white-space: pre-wrap; word-break: break-word; }
    .footer-note { padding: 10px 14px 14px; font-size: 11px; color: var(--muted); }
    @media (max-width: 980px) { .main-grid, .metrics-grid, .indexes-grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="wrap">
    <div class="header">
      <div>
        <div class="title">Eye Tracking / Webcam AI</div>
        <div class="subtitle">Modulo browser-based • MediaPipe FaceMesh • timeline sessione • overlay muscoli funzionali</div>
        <div class="patient" id="patientInfo"></div>
      </div>
      <div class="status"><span class="dot" id="statusDot"></span><span id="statusText">In attesa webcam</span></div>
    </div>
    <div class="main-grid">
      <div class="card">
        <div class="card-head">Acquisizione live</div>
        <div class="viewer"><div class="video-stage"><video id="video" autoplay playsinline muted></video><canvas id="overlay"></canvas></div></div>
        <div class="controls">
          <button id="btnStart">Avvia webcam</button>
          <button id="btnStop" class="secondary">Stop</button>
          <button id="btnSnapshot" class="secondary">Snapshot PNG</button>
          <button id="btnJson" class="secondary">Export JSON sequenza</button>
          <button id="btnReset" class="danger">Reset metriche</button>
          <label class="toggle"><input type="checkbox" id="toggleMuscles" checked /> Muscoli/aree funzionali</label>
        </div>
        <div class="footer-note">Suggerimento: per una misura più stabile resta abbastanza frontale. Se ruoti molto il volto, la precisione scende e la maschera passa in modalità ridotta.</div>
      </div>
      <div class="right-panel">
        <div class="card"><div class="card-head">Metriche live</div><div class="metrics-grid">
            <div class="metric"><div class="metric-label">Gaze direction</div><div class="metric-value" id="gaze_direction">--</div><div class="metric-sub">direzione prevalente dello sguardo</div></div>
            <div class="metric"><div class="metric-label">Head tilt</div><div class="metric-value" id="head_tilt_deg">--</div><div class="metric-sub">gradi di inclinazione del capo</div></div>
            <div class="metric"><div class="metric-label">Mouth open ratio</div><div class="metric-value" id="mouth_open_ratio">--</div><div class="metric-sub">stima apertura orale</div></div>
            <div class="metric"><div class="metric-label">Blink index</div><div class="metric-value" id="blink_index">--</div><div class="metric-sub">frequenza ammiccamento</div></div>
            <div class="metric"><div class="metric-label">Left eye open</div><div class="metric-value" id="left_eye_open_ratio">--</div><div class="metric-sub">apertura occhio sinistro</div></div>
            <div class="metric"><div class="metric-label">Right eye open</div><div class="metric-value" id="right_eye_open_ratio">--</div><div class="metric-sub">apertura occhio destro</div></div>
            <div class="metric"><div class="metric-label">Palpebral asymmetry</div><div class="metric-value" id="palpebral_asymmetry">--</div><div class="metric-sub">asimmetria palpebrale stimata</div></div>
            <div class="metric"><div class="metric-label">Face quality</div><div class="metric-value" id="face_quality">--</div><div class="metric-sub">frontale / laterale / assente</div></div>
        </div></div>
        <div class="card"><div class="card-head">Indici derivati PNEV</div><div class="indexes-grid">
            <div class="index-box"><div class="index-label">Oral instability index</div><div class="index-value" id="oral_instability_index">--</div></div>
            <div class="index-box"><div class="index-label">Oculo-postural index</div><div class="index-value" id="oculo_postural_index">--</div></div>
            <div class="index-box"><div class="index-label">Facial balance index</div><div class="index-value" id="facial_balance_index">--</div></div>
            <div class="index-box"><div class="index-label">Gaze stability index</div><div class="index-value" id="gaze_stability_index">--</div></div>
        </div></div>
        <div class="card"><div class="card-head">Muscoli / aree coinvolte (stima funzionale)</div><div class="info-box" id="muscleInfo">Attivo: orbicularis oculi, orbicularis oris, zygomatici, frontalis (overlay didattico-funzionale, non EMG).</div></div>
        <div class="card"><div class="card-head">JSON live</div><div class="json-wrap"><pre id="jsonOutput">{}</pre></div></div>
      </div>
    </div>
  </div>
  <script>
    const PATIENT_ID = __PATIENT_ID__;
    const PATIENT_LABEL = __PATIENT_LABEL__;
    const videoEl = document.getElementById("video");
    const canvasEl = document.getElementById("overlay");
    const canvasCtx = canvasEl.getContext("2d");
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    const patientInfo = document.getElementById("patientInfo");
    const jsonOutput = document.getElementById("jsonOutput");
    const toggleMuscles = document.getElementById("toggleMuscles");
    const uiFields = {
      gaze_direction: document.getElementById("gaze_direction"), head_tilt_deg: document.getElementById("head_tilt_deg"),
      mouth_open_ratio: document.getElementById("mouth_open_ratio"), blink_index: document.getElementById("blink_index"),
      left_eye_open_ratio: document.getElementById("left_eye_open_ratio"), right_eye_open_ratio: document.getElementById("right_eye_open_ratio"),
      palpebral_asymmetry: document.getElementById("palpebral_asymmetry"), oral_instability_index: document.getElementById("oral_instability_index"),
      oculo_postural_index: document.getElementById("oculo_postural_index"), facial_balance_index: document.getElementById("facial_balance_index"),
      gaze_stability_index: document.getElementById("gaze_stability_index"), face_quality: document.getElementById("face_quality")
    };
    patientInfo.textContent = "Paziente: " + (PATIENT_LABEL && PATIENT_LABEL.trim() ? PATIENT_LABEL : "non specificato") + (PATIENT_ID !== null && PATIENT_ID !== undefined ? " • ID: " + PATIENT_ID : "");
    let mpCamera = null, streamRef = null, lastBlinkTs = null, blinkCount = 0, frameCount = 0, gazeHistory = [], sessionStartTs = Date.now();
    let sequenceTimeline = [];
    let latestPayload = { patient_id: PATIENT_ID, patient_label: PATIENT_LABEL, session_started_at: new Date(sessionStartTs).toISOString(), metrics: {}, pnev_indexes: {}, meta: {}, timeline: [] };
    let previousLandmarks = null;

    function setStatus(text, ok) { statusText.textContent = text; ok ? statusDot.classList.add("ok") : statusDot.classList.remove("ok"); }
    function safeNum(v, digits = 3) { if (typeof v !== "number" || !isFinite(v)) return null; return Number(v.toFixed(digits)); }
    function clamp01(v) { if (!isFinite(v)) return 0; return Math.max(0, Math.min(1, v)); }
    function dist(a,b,w,h){ const dx=(a.x-b.x)*w; const dy=(a.y-b.y)*h; return Math.sqrt(dx*dx+dy*dy); }
    function setText(id, value, digits=3, suffix="") { const el = uiFields[id]; if (!el) return; if (value === null || value === undefined || Number.isNaN(value)) { el.textContent = "--"; return; } el.textContent = typeof value === "number" ? value.toFixed(digits)+suffix : String(value); }
    function eyeOpenRatio(landmarks, idxTop, idxBottom, idxLeft, idxRight, w, h) { const vertical = dist(landmarks[idxTop], landmarks[idxBottom], w, h); const horizontal = dist(landmarks[idxLeft], landmarks[idxRight], w, h); if (!horizontal) return 0; return vertical / horizontal; }
    function mouthOpenRatio(landmarks, idxTop, idxBottom, idxLeft, idxRight, w, h) { const vertical = dist(landmarks[idxTop], landmarks[idxBottom], w, h); const horizontal = dist(landmarks[idxLeft], landmarks[idxRight], w, h); if (!horizontal) return 0; return vertical / horizontal; }
    function computeHeadTiltDeg(landmarks) { const leftEyeOuter = landmarks[33]; const rightEyeOuter = landmarks[263]; const dx = rightEyeOuter.x - leftEyeOuter.x; const dy = rightEyeOuter.y - leftEyeOuter.y; return Math.atan2(dy, dx) * 180 / Math.PI; }
    function computeFaceYaw(landmarks) { const nose = landmarks[1]; const left = landmarks[234]; const right = landmarks[454]; if (!nose || !left || !right) return 0; const dl = Math.abs(nose.x - left.x); const dr = Math.abs(right.x - nose.x); const sum = dl + dr || 1; return (dr - dl) / sum; }
    function computeFaceQuality(yaw) { const ay = Math.abs(yaw); if (ay < 0.10) return "frontale"; if (ay < 0.22) return "lievemente laterale"; return "laterale"; }
    function computeGazeDirection(landmarks) { const noseTip = landmarks[1]; const leftEyeCenter = landmarks[468] || landmarks[159]; const rightEyeCenter = landmarks[473] || landmarks[386]; if (!noseTip || !leftEyeCenter || !rightEyeCenter) return "center"; const eyeMidX = (leftEyeCenter.x + rightEyeCenter.x) / 2; const eyeMidY = (leftEyeCenter.y + rightEyeCenter.y) / 2; const dx = noseTip.x - eyeMidX; const dy = noseTip.y - eyeMidY; if (dx > 0.02) return "left"; if (dx < -0.02) return "right"; if (dy > 0.03) return "up"; if (dy < -0.03) return "down"; return "center"; }
    function updateBlink(leftRatio,rightRatio){ const avg=(leftRatio+rightRatio)/2; const now=Date.now(); if(avg<0.18){ if(lastBlinkTs===null || now-lastBlinkTs>250){ blinkCount += 1; lastBlinkTs = now; } } return blinkCount; }
    function computeGazeStability(history) { if (!history.length) return 1; const counts={}; for (const item of history) counts[item]=(counts[item]||0)+1; let maxCount=0; for (const k in counts) maxCount=Math.max(maxCount, counts[k]); return maxCount/history.length; }
    function smoothLandmarks(landmarks) { if (!previousLandmarks || previousLandmarks.length !== landmarks.length) { previousLandmarks = landmarks.map(p => ({x:p.x, y:p.y, z:p.z||0})); return previousLandmarks; } const alpha = 0.65; previousLandmarks = landmarks.map((p,i)=>({ x: previousLandmarks[i].x*alpha + p.x*(1-alpha), y: previousLandmarks[i].y*alpha + p.y*(1-alpha), z: (previousLandmarks[i].z||0)*alpha + (p.z||0)*(1-alpha) })); return previousLandmarks; }
    function mirrorPoint(p, width, height) { return {x:(1-p.x)*width, y:p.y*height}; }
    function drawPolyline(indices, landmarks, width, height, color, lineWidth, fillColor) { if (!indices || !indices.length) return; canvasCtx.beginPath(); indices.forEach((idx, k)=>{ const pt = mirrorPoint(landmarks[idx], width, height); if (k===0) canvasCtx.moveTo(pt.x, pt.y); else canvasCtx.lineTo(pt.x, pt.y); }); canvasCtx.closePath(); if (fillColor) { canvasCtx.fillStyle = fillColor; canvasCtx.fill(); } canvasCtx.strokeStyle = color; canvasCtx.lineWidth = lineWidth; canvasCtx.stroke(); }
    function drawMuscleOverlay(landmarks, width, height) {
      if (!toggleMuscles.checked) return;
      drawPolyline([33,159,158,133,153,145], landmarks, width, height, 'rgba(56,189,248,0.9)', 1.2, 'rgba(56,189,248,0.14)');
      drawPolyline([362,386,385,263,373,374], landmarks, width, height, 'rgba(56,189,248,0.9)', 1.2, 'rgba(56,189,248,0.14)');
      drawPolyline([61,40,37,0,267,270,291,321,314,17,84,91], landmarks, width, height, 'rgba(245,158,11,0.9)', 1.2, 'rgba(245,158,11,0.14)');
      drawPolyline([70,63,105,66,107,55,65,52], landmarks, width, height, 'rgba(244,114,182,0.9)', 1.0, 'rgba(244,114,182,0.10)');
      drawPolyline([336,296,334,293,300,276,283,282], landmarks, width, height, 'rgba(244,114,182,0.9)', 1.0, 'rgba(244,114,182,0.10)');
      drawPolyline([50,101,205,187,147,116], landmarks, width, height, 'rgba(34,197,94,0.9)', 1.0, 'rgba(34,197,94,0.10)');
      drawPolyline([280,330,425,411,376,347], landmarks, width, height, 'rgba(34,197,94,0.9)', 1.0, 'rgba(34,197,94,0.10)');
    }
    function drawOverlay(landmarks, width, height, faceQuality) {
      canvasCtx.save(); canvasCtx.clearRect(0,0,width,height);
      if (faceQuality === 'laterale') {
        const important = [1,33,263,61,291,13,14,152];
        important.forEach(idx=>{ const p=mirrorPoint(landmarks[idx], width, height); canvasCtx.beginPath(); canvasCtx.arc(p.x,p.y,3.5,0,Math.PI*2); canvasCtx.fillStyle='#ffffff'; canvasCtx.fill(); });
      } else {
        FACEMESH_CONTOURS.forEach(conn=>{ const p1=mirrorPoint(landmarks[conn[0]], width, height); const p2=mirrorPoint(landmarks[conn[1]], width, height); canvasCtx.beginPath(); canvasCtx.moveTo(p1.x,p1.y); canvasCtx.lineTo(p2.x,p2.y); canvasCtx.strokeStyle='rgba(34,197,94,0.55)'; canvasCtx.lineWidth=1; canvasCtx.stroke(); });
        FACEMESH_LEFT_IRIS.forEach(conn=>{ const p1=mirrorPoint(landmarks[conn[0]], width, height); const p2=mirrorPoint(landmarks[conn[1]], width, height); canvasCtx.beginPath(); canvasCtx.moveTo(p1.x,p1.y); canvasCtx.lineTo(p2.x,p2.y); canvasCtx.strokeStyle='#38bdf8'; canvasCtx.lineWidth=1.2; canvasCtx.stroke(); });
        FACEMESH_RIGHT_IRIS.forEach(conn=>{ const p1=mirrorPoint(landmarks[conn[0]], width, height); const p2=mirrorPoint(landmarks[conn[1]], width, height); canvasCtx.beginPath(); canvasCtx.moveTo(p1.x,p1.y); canvasCtx.lineTo(p2.x,p2.y); canvasCtx.strokeStyle='#38bdf8'; canvasCtx.lineWidth=1.2; canvasCtx.stroke(); });
      }
      drawMuscleOverlay(landmarks, width, height);
      canvasCtx.restore();
    }
    function updateUI(payload) {
      const m = payload.metrics || {}; const p = payload.pnev_indexes || {};
      setText('gaze_direction', m.gaze_direction ?? '--', 3, ''); setText('head_tilt_deg', m.head_tilt_deg, 1, '°'); setText('mouth_open_ratio', m.mouth_open_ratio, 3, '');
      setText('blink_index', m.blink_index, 0, ''); setText('left_eye_open_ratio', m.left_eye_open_ratio, 3, ''); setText('right_eye_open_ratio', m.right_eye_open_ratio, 3, '');
      setText('palpebral_asymmetry', m.palpebral_asymmetry, 3, ''); setText('oral_instability_index', p.oral_instability_index, 3, '');
      setText('oculo_postural_index', p.oculo_postural_index, 3, ''); setText('facial_balance_index', p.facial_balance_index, 3, ''); setText('gaze_stability_index', p.gaze_stability_index, 3, '');
      setText('face_quality', (payload.meta || {}).face_quality || '--', 0, '');
      jsonOutput.textContent = JSON.stringify(payload, null, 2);
    }
    function buildPayload(landmarks, width, height) {
      const leftEye = eyeOpenRatio(landmarks, 159, 145, 33, 133, width, height);
      const rightEye = eyeOpenRatio(landmarks, 386, 374, 362, 263, width, height);
      const mouth = mouthOpenRatio(landmarks, 13, 14, 61, 291, width, height);
      const headTilt = computeHeadTiltDeg(landmarks); const gazeDirection = computeGazeDirection(landmarks);
      const asymmetry = Math.abs(leftEye-rightEye); const blinkIndex = updateBlink(leftEye, rightEye); const yaw = computeFaceYaw(landmarks); const faceQuality = computeFaceQuality(yaw);
      gazeHistory.push(gazeDirection); if (gazeHistory.length>90) gazeHistory.shift(); const gazeStability = computeGazeStability(gazeHistory);
      const oralInstability = clamp01(mouth*2.2); const oculoPostural = clamp01((Math.abs(headTilt)/25)*0.55 + (asymmetry*2.5)*0.45 + Math.abs(yaw)*0.25); const facialBalance = clamp01(1 - asymmetry*4 - Math.abs(yaw)*0.3); const gazeStabilityIndex = clamp01(gazeStability);
      frameCount += 1;
      const sample = {
        t_ms: Date.now()-sessionStartTs, gaze_direction: gazeDirection, head_tilt_deg: safeNum(headTilt,2), mouth_open_ratio: safeNum(mouth,4),
        left_eye_open_ratio: safeNum(leftEye,4), right_eye_open_ratio: safeNum(rightEye,4), palpebral_asymmetry: safeNum(asymmetry,4),
        face_yaw: safeNum(yaw,4), face_quality: faceQuality
      };
      sequenceTimeline.push(sample); if (sequenceTimeline.length > 900) sequenceTimeline.shift();
      latestPayload = {
        patient_id: PATIENT_ID, patient_label: PATIENT_LABEL, timestamp: new Date().toISOString(), session_started_at: new Date(sessionStartTs).toISOString(),
        metrics: { gaze_direction: gazeDirection, head_tilt_deg: safeNum(headTilt,2), mouth_open_ratio: safeNum(mouth,4), left_eye_open_ratio: safeNum(leftEye,4), right_eye_open_ratio: safeNum(rightEye,4), palpebral_asymmetry: safeNum(asymmetry,4), blink_index: blinkIndex },
        pnev_indexes: { oral_instability_index: safeNum(oralInstability,4), oculo_postural_index: safeNum(oculoPostural,4), facial_balance_index: safeNum(facialBalance,4), gaze_stability_index: safeNum(gazeStabilityIndex,4) },
        meta: { frame_count: frameCount, face_detected: true, image_width: width, image_height: height, face_yaw: safeNum(yaw,4), face_quality: faceQuality, muscles_overlay: !!toggleMuscles.checked },
        timeline: sequenceTimeline
      };
      return latestPayload;
    }
    function resetMetrics(){ lastBlinkTs=null; blinkCount=0; frameCount=0; gazeHistory=[]; sequenceTimeline=[]; sessionStartTs=Date.now(); previousLandmarks=null; latestPayload = { patient_id:PATIENT_ID, patient_label:PATIENT_LABEL, session_started_at:new Date(sessionStartTs).toISOString(), metrics:{}, pnev_indexes:{}, meta:{}, timeline:[] }; updateUI(latestPayload); }
    async function stopCamera(){ try { if (mpCamera && typeof mpCamera.stop === 'function') mpCamera.stop(); } catch(e) {} try { if (streamRef) streamRef.getTracks().forEach(t=>t.stop()); } catch(e) {} videoEl.srcObject=null; streamRef=null; setStatus('Webcam ferma', false); }
    function downloadText(filename, text, mimeType){ const blob=new Blob([text], {type:mimeType}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=filename; document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url); }
    function exportJson(){ const stamp=new Date().toISOString().replace(/[:.]/g,'-'); downloadText('gaze_sequence_'+stamp+'.json', JSON.stringify(latestPayload,null,2), 'application/json'); }
    function exportSnapshot(){ const stamp=new Date().toISOString().replace(/[:.]/g,'-'); const link=document.createElement('a'); link.download='gaze_snapshot_'+stamp+'.png'; link.href=canvasEl.toDataURL('image/png'); link.click(); }
    async function startCamera(){ await stopCamera(); if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) { setStatus('Browser non compatibile con webcam', false); alert('Il browser non supporta getUserMedia.'); return; }
      try {
        streamRef = await navigator.mediaDevices.getUserMedia({ video: { facingMode:'user', width:{ideal:1280}, height:{ideal:720} }, audio:false });
        videoEl.srcObject=streamRef; await videoEl.play();
        const faceMesh = new FaceMesh({ locateFile: (file) => 'https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/' + file });
        faceMesh.setOptions({ maxNumFaces:1, refineLandmarks:true, minDetectionConfidence:0.5, minTrackingConfidence:0.5 });
        faceMesh.onResults((results) => {
          const width = results.image.width, height = results.image.height; if (canvasEl.width !== width) canvasEl.width=width; if (canvasEl.height !== height) canvasEl.height=height; canvasCtx.clearRect(0,0,width,height);
          if (results.multiFaceLandmarks && results.multiFaceLandmarks.length > 0) {
            const landmarks = smoothLandmarks(results.multiFaceLandmarks[0]); const yaw = computeFaceYaw(landmarks); const quality = computeFaceQuality(yaw); drawOverlay(landmarks, width, height, quality); const payload = buildPayload(landmarks, width, height); updateUI(payload); setStatus(quality === 'laterale' ? 'Tracking attivo (profilo laterale ridotto)' : 'Tracking attivo', true);
          } else {
            latestPayload = { patient_id:PATIENT_ID, patient_label:PATIENT_LABEL, timestamp:new Date().toISOString(), session_started_at:new Date(sessionStartTs).toISOString(), metrics:{}, pnev_indexes:{}, meta:{ frame_count: frameCount, face_detected:false, face_quality:'assente', muscles_overlay:!!toggleMuscles.checked }, timeline:sequenceTimeline };
            updateUI(latestPayload); setStatus('Volto non rilevato', false);
          }
        });
        mpCamera = new Camera(videoEl, { onFrame: async () => { await faceMesh.send({image: videoEl}); }, width:1280, height:720 }); mpCamera.start(); setStatus('Webcam avviata', true);
      } catch (err) { console.error(err); setStatus('Errore accesso webcam', false); alert('Errore nell\'avvio webcam: ' + (err && err.message ? err.message : err)); }
    }
    document.getElementById('btnStart').addEventListener('click', startCamera);
    document.getElementById('btnStop').addEventListener('click', stopCamera);
    document.getElementById('btnSnapshot').addEventListener('click', exportSnapshot);
    document.getElementById('btnJson').addEventListener('click', exportJson);
    document.getElementById('btnReset').addEventListener('click', resetMetrics);
    updateUI(latestPayload);
  </script>
</body>
</html>
"""
    html = html.replace("__PATIENT_ID__", patient_id_json)
    html = html.replace("__PATIENT_LABEL__", patient_label_json)
    return html
