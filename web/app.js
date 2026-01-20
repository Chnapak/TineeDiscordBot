const apiBaseInput = document.getElementById("apiBase");
const apiTokenInput = document.getElementById("apiToken");
const connectBtn = document.getElementById("connectBtn");
const refreshBtn = document.getElementById("refreshBtn");
const guildSelect = document.getElementById("guildSelect");
const statusEl = document.getElementById("status");
const saveBtn = document.getElementById("saveBtn");

const aiEnabled = document.getElementById("aiEnabled");
const aiTrigger = document.getElementById("aiTrigger");
const aiKeyword = document.getElementById("aiKeyword");
const allowAllChannels = document.getElementById("allowAllChannels");
const channelsList = document.getElementById("channelsList");
const autoplay = document.getElementById("autoplay");
const volumeRange = document.getElementById("volumeRange");
const volumeNumber = document.getElementById("volumeNumber");

let currentGuildId = null;
let currentChannels = [];

const storedApiBase = localStorage.getItem("tineeApiBase");
const storedToken = localStorage.getItem("tineeApiToken");
if (storedApiBase) {
  apiBaseInput.value = storedApiBase;
}
if (storedToken) {
  apiTokenInput.value = storedToken;
}

function setStatus(message, type = "") {
  statusEl.textContent = message;
  statusEl.className = "status";
  if (type) {
    statusEl.classList.add(type);
  }
}

function getApiBase() {
  return apiBaseInput.value.trim().replace(/\/+$/, "");
}

function getApiToken() {
  return apiTokenInput.value.trim();
}

async function apiFetch(path, options = {}) {
  const apiBase = getApiBase();
  if (!apiBase) {
    throw new Error("API base URL is required.");
  }
  const headers = Object.assign(
    { "Content-Type": "application/json" },
    options.headers || {}
  );
  const token = getApiToken();
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const response = await fetch(`${apiBase}${path}`, {
    ...options,
    headers,
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status}).`);
  }
  return response.json();
}

async function loadGuilds() {
  setStatus("Loading servers...");
  const data = await apiFetch("/guilds");
  const guilds = data.guilds || [];
  guildSelect.innerHTML = "<option value=\"\">Select a server...</option>";
  guilds.forEach((guild) => {
    const option = document.createElement("option");
    option.value = guild.id;
    option.textContent = guild.name;
    guildSelect.appendChild(option);
  });
  refreshBtn.disabled = !guilds.length;
  saveBtn.disabled = true;
  setStatus(guilds.length ? "Servers loaded." : "No servers found.", "ok");
}

function renderChannels(channels, selectedIds) {
  channelsList.innerHTML = "";
  channels.forEach((channel) => {
    const label = document.createElement("label");
    label.className = "toggle";
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.dataset.id = channel.id;
    checkbox.checked = selectedIds.has(channel.id);
    const span = document.createElement("span");
    span.textContent = `#${channel.name}`;
    label.appendChild(checkbox);
    label.appendChild(span);
    channelsList.appendChild(label);
  });
}

function getSelectedChannelIds() {
  if (allowAllChannels.checked) {
    return [];
  }
  return Array.from(channelsList.querySelectorAll("input[type=\"checkbox\"]"))
    .filter((checkbox) => checkbox.checked)
    .map((checkbox) => Number(checkbox.dataset.id));
}

function syncVolumeInputs(value) {
  volumeRange.value = value;
  volumeNumber.value = value;
}

async function loadConfig(guildId) {
  setStatus("Loading config...");
  const [configData, channelsData] = await Promise.all([
    apiFetch(`/config/${guildId}`),
    apiFetch(`/guilds/${guildId}/channels`),
  ]);
  const config = configData.config || {};
  currentChannels = channelsData.channels || [];

  aiEnabled.checked = Boolean(config.ai_enabled);
  aiTrigger.value = config.ai_trigger || "keyword";
  aiKeyword.value = config.ai_keyword || "tinee";
  autoplay.checked = Boolean(config.autoplay);
  syncVolumeInputs(config.volume ?? 100);

  const selected = new Set((config.ai_channels || []).map(Number));
  allowAllChannels.checked = selected.size === 0;
  renderChannels(currentChannels, selected);
  toggleChannelInputs(allowAllChannels.checked);

  saveBtn.disabled = false;
  setStatus("Config loaded.", "ok");
}

function toggleChannelInputs(disabled) {
  const inputs = channelsList.querySelectorAll("input[type=\"checkbox\"]");
  inputs.forEach((checkbox) => {
    checkbox.disabled = disabled;
    if (disabled) {
      checkbox.checked = false;
    }
  });
}

async function saveConfig() {
  if (!currentGuildId) {
    return;
  }
  setStatus("Saving...");
  const payload = {
    ai_enabled: aiEnabled.checked,
    ai_trigger: aiTrigger.value,
    ai_keyword: aiKeyword.value.trim() || "tinee",
    ai_channels: getSelectedChannelIds(),
    autoplay: autoplay.checked,
    volume: Number(volumeNumber.value || 100),
  };
  await apiFetch(`/config/${currentGuildId}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
  setStatus("Saved.", "ok");
}

connectBtn.addEventListener("click", async () => {
  try {
    const apiBase = getApiBase();
    if (!apiBase) {
      setStatus("Enter the API base URL.", "error");
      return;
    }
    localStorage.setItem("tineeApiBase", apiBase);
    localStorage.setItem("tineeApiToken", getApiToken());
    await loadGuilds();
  } catch (error) {
    setStatus(error.message, "error");
  }
});

refreshBtn.addEventListener("click", async () => {
  if (!currentGuildId) {
    return;
  }
  try {
    await loadConfig(currentGuildId);
  } catch (error) {
    setStatus(error.message, "error");
  }
});

guildSelect.addEventListener("change", async (event) => {
  currentGuildId = event.target.value;
  if (!currentGuildId) {
    saveBtn.disabled = true;
    return;
  }
  try {
    await loadConfig(currentGuildId);
  } catch (error) {
    setStatus(error.message, "error");
  }
});

allowAllChannels.addEventListener("change", () => {
  toggleChannelInputs(allowAllChannels.checked);
});

volumeRange.addEventListener("input", () => {
  syncVolumeInputs(volumeRange.value);
});

volumeNumber.addEventListener("input", () => {
  syncVolumeInputs(volumeNumber.value);
});

saveBtn.addEventListener("click", async () => {
  try {
    await saveConfig();
  } catch (error) {
    setStatus(error.message, "error");
  }
});

setStatus("Idle");
