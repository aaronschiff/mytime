const NOTIFY_THRESHOLD_MS = 4 * 3600 * 1000;
let _notifiedSince = null;

function tick() {
  const now = Date.now();
  let total = 0;
  let runningLive = null;
  let runningSince = null;
  document.querySelectorAll(".elapsed").forEach(el => {
    let secs = parseInt(el.dataset.base, 10);
    if (el.dataset.running === "1" && el.dataset.since) {
      secs += Math.floor((now - Date.parse(el.dataset.since)) / 1000);
      runningLive = secs;
      runningSince = el.dataset.since;
      el.textContent = fmtHms(secs);
    }
    total += secs;
  });
  const totalEl = document.querySelector("[data-total-seconds]");
  if (totalEl) totalEl.textContent = fmtHms(total);
  document.title = runningLive !== null ? "▶ " + fmtHms(runningLive) + " — mytime" : "mytime";
  if (runningSince) _checkNotification(runningSince, now);
}

function fmtHms(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return h + ":" + String(m).padStart(2, "0") + ":" + String(x).padStart(2, "0");
}

function _checkNotification(sinceIso, now) {
  if (!("Notification" in window)) return;
  if (Notification.permission === "default") { Notification.requestPermission(); return; }
  if (Notification.permission !== "granted") return;
  if (_notifiedSince === sinceIso) return;
  if ((now - Date.parse(sinceIso)) >= NOTIFY_THRESHOLD_MS) {
    _notifiedSince = sinceIso;
    new Notification("mytime: timer still running", {
      body: "A timer has been running for over 4 hours — did you forget to stop it?",
    });
  }
}

setInterval(tick, 1000);
document.body.addEventListener("htmx:afterSwap", function() {
  _notifiedSince = null;  // reset after HTMX swap so we re-check
  tick();
});
tick();
