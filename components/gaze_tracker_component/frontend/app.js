const video = document.getElementById("video");
const statusEl = document.getElementById("status");

async function startCamera() {
  try {
    statusEl.textContent = "Richiesta accesso webcam…";
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: "user",
        width: { ideal: 1280 },
        height: { ideal: 720 }
      },
      audio: false
    });
    video.srcObject = stream;
    statusEl.textContent = "Webcam attiva";
  } catch (err) {
    console.error("Errore webcam:", err);
    statusEl.textContent = "Errore webcam: " + (err && err.message ? err.message : err);
  }
}

if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  startCamera();
} else {
  statusEl.textContent = "Browser non compatibile con getUserMedia";
}
