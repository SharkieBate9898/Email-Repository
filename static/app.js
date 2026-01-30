const statusEl = document.getElementById("status");
const toggleBtn = document.getElementById("toggle");
const logList = document.getElementById("log-list");

async function fetchStatus() {
  const response = await fetch("/status");
  const data = await response.json();
  return data.running;
}

function updateStatus(running) {
  statusEl.textContent = running ? "Running" : "Stopped";
  toggleBtn.textContent = running ? "Stop Assistant" : "Start Assistant";
  toggleBtn.classList.toggle("stop", running);
}

async function toggleWorker() {
  const running = await fetchStatus();
  const endpoint = running ? "/stop" : "/start";
  await fetch(endpoint, { method: "POST" });
  const newStatus = await fetchStatus();
  updateStatus(newStatus);
}

async function loadLogs() {
  const response = await fetch("/logs");
  const data = await response.json();
  logList.innerHTML = "";
  data.logs.slice().reverse().forEach((entry) => {
    const item = document.createElement("li");
    item.textContent = entry;
    logList.appendChild(item);
  });
}

toggleBtn.addEventListener("click", async () => {
  toggleBtn.disabled = true;
  await toggleWorker();
  await loadLogs();
  toggleBtn.disabled = false;
});

async function init() {
  const running = await fetchStatus();
  updateStatus(running);
  await loadLogs();
  setInterval(loadLogs, 5000);
}

init();
