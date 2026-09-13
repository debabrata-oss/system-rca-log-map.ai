function getApiKey() {
  let key = localStorage.getItem("rca_api_key");
  if (!key) {
    key = prompt("Enter the RCA web API key:") || "";
    localStorage.setItem("rca_api_key", key);
  }
  return key;
}

async function apiFetch(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: {
      ...(options.headers || {}),
      "X-API-Key": getApiKey(),
      "Content-Type": "application/json",
    },
  });
  if (response.status === 401) {
    localStorage.removeItem("rca_api_key");
  }
  return response;
}

async function loadHosts() {
  const select = document.getElementById("host");
  const response = await apiFetch("api/hosts");
  if (!response.ok) {
    setStatus("Failed to load hosts. Refresh to re-enter your API key.", true);
    return;
  }
  const hosts = await response.json();
  select.innerHTML = "";
  for (const host of hosts) {
    const option = document.createElement("option");
    option.value = host.alias;
    option.textContent = `${host.alias} (${host.hostname})`;
    select.appendChild(option);
  }
}

function setStatus(message, isError = false) {
  const status = document.getElementById("status");
  status.textContent = message;
  status.className = isError ? "error" : "";
}

function renderTranscript(transcript) {
  const container = document.getElementById("transcript");
  container.innerHTML = "";
  for (const event of transcript) {
    const div = document.createElement("div");
    div.className = "tool-event";
    if (event.type === "tool_call") {
      div.innerHTML = `<strong>${event.name}</strong>(${JSON.stringify(event.input || {})})`;
    } else {
      const pre = document.createElement("pre");
      pre.textContent = event.output || "";
      div.innerHTML = `<strong>${event.name} output:</strong>`;
      div.appendChild(pre);
    }
    container.appendChild(div);
  }
}

function renderReport(report) {
  const container = document.getElementById("report");
  const evidence = report.evidence.map((e) => `<li>${e}</li>`).join("");
  const actions = report.recommended_actions.map((a) => `<li>${a}</li>`).join("");
  container.innerHTML = `
    <div class="report-card">
      <p><span class="confidence confidence-${report.confidence}">${report.confidence} confidence</span></p>
      <p><strong>Summary:</strong> ${report.summary}</p>
      <p><strong>Likely root cause:</strong> ${report.likely_root_cause}</p>
      <p><strong>Evidence:</strong></p>
      <ul>${evidence}</ul>
      <p><strong>Recommended actions:</strong></p>
      <ul>${actions}</ul>
      <p><strong>Tools used:</strong> ${report.tools_used.join(", ") || "(none)"}</p>
    </div>
  `;
}

document.getElementById("investigate-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const host = document.getElementById("host").value;
  const question = document.getElementById("question").value;
  const submitBtn = document.getElementById("submit-btn");

  document.getElementById("transcript").innerHTML = "";
  document.getElementById("report").innerHTML = "";
  submitBtn.disabled = true;
  setStatus("Investigating... this can take a while.");

  try {
    const response = await apiFetch("api/investigate", {
      method: "POST",
      body: JSON.stringify({ host, question }),
    });
    const data = await response.json();
    if (!response.ok) {
      setStatus(data.detail || "Investigation failed.", true);
      return;
    }
    setStatus("Done.");
    renderTranscript(data.transcript);
    renderReport(data.report);
  } catch (err) {
    setStatus(`Request failed: ${err}`, true);
  } finally {
    submitBtn.disabled = false;
  }
});

loadHosts();
