const statusEl = document.getElementById("status");
const toggleBtn = document.getElementById("toggle");
const logList = document.getElementById("log-list");
const locationInput = document.getElementById("location");
const industryInput = document.getElementById("industry");
const saveSettingsBtn = document.getElementById("save-settings");
const emailSubjectInput = document.getElementById("email-subject");
const emailBodyInput = document.getElementById("email-body");
const followupSubjectInput = document.getElementById("followup-subject");
const followupBodyInput = document.getElementById("followup-body");
const contactList = document.getElementById("contact-list");

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

async function loadContacts() {
  const response = await fetch("/contacts");
  const data = await response.json();
  contactList.innerHTML = "";
  data.contacts.forEach((contact) => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${contact.name}</td>
      <td><a href="${contact.url}" target="_blank" rel="noreferrer">${contact.url}</a></td>
      <td>${contact.count}</td>
      <td>${contact.last_sent ? new Date(contact.last_sent).toLocaleString() : "-"}</td>
      <td>${contact.replied ? "Replied" : "Awaiting reply"}</td>
      <td>
        <button class="secondary small" data-name="${contact.name}" ${
          contact.replied ? "disabled" : ""
        }>Mark replied</button>
      </td>
    `;
    contactList.appendChild(row);
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
      email_subject_template: emailSubjectInput.value,
      email_body_template: emailBodyInput.value,
      followup_subject_template: followupSubjectInput.value,
      followup_body_template: followupBodyInput.value,
    }),
  });
  const status = await fetchStatus();
  locationInput.value = status.settings.location || "";
  industryInput.value = status.settings.industry || "";
  emailSubjectInput.value = status.settings.email_subject_template || "";
  emailBodyInput.value = status.settings.email_body_template || "";
  followupSubjectInput.value = status.settings.followup_subject_template || "";
  followupBodyInput.value = status.settings.followup_body_template || "";
  saveSettingsBtn.disabled = false;
});

contactList.addEventListener("click", async (event) => {
  const button = event.target.closest("button[data-name]");
  if (!button) return;
  const name = button.getAttribute("data-name");
  button.disabled = true;
  await fetch("/contacts/reply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  await loadContacts();
});

async function init() {
  const status = await fetchStatus();
  updateStatus(status.running);
  locationInput.value = status.settings.location || "";
  industryInput.value = status.settings.industry || "";
  emailSubjectInput.value = status.settings.email_subject_template || "";
  emailBodyInput.value = status.settings.email_body_template || "";
  followupSubjectInput.value = status.settings.followup_subject_template || "";
  followupBodyInput.value = status.settings.followup_body_template || "";
  await loadLogs();
  await loadContacts();
  setInterval(() => {
    loadLogs();
    loadContacts();
  }, 5000);
}

init();
