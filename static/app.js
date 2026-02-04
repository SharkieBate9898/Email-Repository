const statusEl = document.getElementById("status");
const toggleBtn = document.getElementById("toggle");
const logList = document.getElementById("log-list");
const locationInput = document.getElementById("location");
const industryInput = document.getElementById("industry");
const saveSettingsBtn = document.getElementById("save-settings");

async function fetchStatus() {
  const response = await fetch("/status");
  const data = await response.json();
  return data;
}

function updateStatus(running) {
  statusEl.textContent = running ? "Running" : "Stopped";
  toggleBtn.textContent = running ? "Stop Assistant" : "Start Assistant";
  toggleBtn.classList.toggle("stop", running);
}

async function toggleWorker() {
  const status = await fetchStatus();
  const endpoint = status.running ? "/stop" : "/start";
  await fetch(endpoint, { method: "POST" });
  const newStatus = await fetchStatus();
  updateStatus(newStatus.running);
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

saveSettingsBtn.addEventListener("click", async () => {
  saveSettingsBtn.disabled = true;
  await fetch("/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      location: locationInput.value,
      industry: industryInput.value,
    }),
  });
  const status = await fetchStatus();
  locationInput.value = status.location || "";
  industryInput.value = status.industry || "";
  saveSettingsBtn.disabled = false;
});

async function init() {
  const status = await fetchStatus();
  updateStatus(status.running);
  locationInput.value = status.location || "";
  industryInput.value = status.industry || "";
  await loadLogs();
  setInterval(loadLogs, 5000);
}

init();
