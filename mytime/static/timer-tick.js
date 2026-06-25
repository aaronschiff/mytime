function tick() {
  const now = Date.now();
  let total = 0;
  let runningLive = null;
  document.querySelectorAll(".elapsed").forEach(el => {
    let secs = parseInt(el.dataset.base, 10);   // stored accumulated seconds
    if (el.dataset.running === "1" && el.dataset.since) {
      secs += Math.floor((now - Date.parse(el.dataset.since)) / 1000);
      runningLive = secs;
    }
    el.textContent = fmtHms(secs);
    total += secs;                              // sum live values across all rows
  });
  const totalEl = document.querySelector("[data-total-seconds]");
  if (totalEl) totalEl.textContent = fmtHms(total);
  document.title = runningLive !== null ? "▶ " + fmtHms(runningLive) + " — mytime" : "mytime";
}
function fmtHms(s) {
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60;
  return h + ":" + String(m).padStart(2, "0") + ":" + String(x).padStart(2, "0");
}
setInterval(tick, 1000);
document.body.addEventListener("htmx:afterSwap", tick);
tick();
