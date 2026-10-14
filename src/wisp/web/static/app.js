const state = { config: null, status: null, documents: [], voices: [], accessUrl: "", elevenlabs: null, setup: null };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const body = response.status === 204 ? null : await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body?.error || `HTTP ${response.status}`);
  return body;
}

function jsonOptions(method, body) {
  return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
}

function toast(message, error = false) {
  const node = $("#toast");
  node.textContent = message;
  node.style.background = error ? "#8b342c" : "";
  node.classList.add("show");
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => node.classList.remove("show"), 2800);
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

function switchView(name) {
  $$(".view").forEach(node => node.classList.toggle("active", node.id === `view-${name}`));
  $$(".nav-item").forEach(node => node.classList.toggle("active", node.dataset.view === name));
  history.replaceState(null, "", `#${name}`);
}

function voiceName(voiceId) {
  if (!voiceId || voiceId === "disabled") return "Nessuna voce";
  return state.voices.find(item => item.id === voiceId)?.name || voiceId;
}

function renderStatus() {
  const online = Boolean(state.status?.llm_online);
  $(".connection").classList.toggle("online", online);
  $("#connection-label").textContent = online ? "WISP è pronto" : "WISP si sta svegliando";
  $("#index-count").textContent = state.status?.indexed_chunks ?? "—";
}

function renderCharacters() {
  const activeId = state.config.active_character_id;
  const characters = state.config.characters;
  $("#character-list").innerHTML = characters.map(character => `
    <article class="character-card ${character.id === activeId ? "active" : ""}" data-id="${escapeHtml(character.id)}">
      <span class="badge">${character.id === activeId ? "Parla ora" : "Amico"}</span>
      <h3>${escapeHtml(character.name)}</h3>
      <p class="muted">${escapeHtml(character.description || "Un nuovo amico di WISP")}</p>
      <small>Voce: ${escapeHtml(voiceName(character.voice_id))}</small>
      <footer>
        ${character.id !== activeId ? '<button class="primary activate-character">Scegli</button>' : ""}
        <button class="secondary edit-character">Modifica</button>
        ${characters.length > 1 ? '<button class="secondary delete-character">Elimina</button>' : ""}
      </footer>
    </article>`).join("");
  const active = characters.find(item => item.id === activeId);
  $("#active-name").textContent = active?.name || "—";
  $("#active-description").textContent = active?.description || "Un nuovo amico di WISP";
  $("#document-characters").innerHTML = characters.map(item => `<label><input type="checkbox" name="character_ids" value="${escapeHtml(item.id)}"> ${escapeHtml(item.name)}</label>`).join("");
}

function renderDocuments() {
  const root = $("#document-list");
  if (!state.documents.length) {
    root.innerHTML = '<div class="empty">Nessuna storia. Scrivine una oppure porta un file.</div>';
    return;
  }
  root.innerHTML = state.documents.map(item => `
    <article class="document-row" data-id="${escapeHtml(item.id)}">
      <div><h3>${escapeHtml(item.title)}</h3><small>${item.character_count} caratteri · ${item.character_ids?.length ? item.character_ids.join(", ") : "tutti gli amici"}</small></div>
      <div><button class="secondary edit-document">Modifica</button><button class="secondary delete-document">Elimina</button></div>
    </article>`).join("");
}

function renderVoices() {
  $("#voice-list").innerHTML = state.voices.map(item => `
    <article class="voice-card" data-id="${escapeHtml(item.id)}">
      <div class="voice-face" aria-hidden="true">${item.name.slice(0, 1)}</div>
      <div><p class="eyebrow">${item.kind === "elevenlabs" ? "ELEVENLABS · ONLINE" : "PIPER · OFFLINE"}</p><h2>${escapeHtml(item.name)}</h2><p class="muted">${escapeHtml(item.description)}</p></div>
      <button class="${item.available ? "secondary preview-voice" : "primary install-voice"}">${item.available ? "Ascolta" : "Installa"}</button>
    </article>`).join("");

  const select = $("#character-form select[name=voice_id]");
  const current = select.value;
  select.innerHTML = '<option value="disabled">Senza voce</option>' + state.voices.map(item =>
    `<option value="${escapeHtml(item.id)}" ${item.available ? "" : "disabled"}>${escapeHtml(item.name)}${item.available ? "" : " — da installare"}</option>`
  ).join("");
  select.value = [...select.options].some(option => option.value === current) ? current : "disabled";
}

function renderIntegrations() {
  const integration = state.elevenlabs;
  const status = $("#elevenlabs-status");
  const disconnect = $("#disconnect-elevenlabs");
  disconnect.hidden = !integration?.configured;
  if (!integration?.configured) status.textContent = "Non collegato";
  else if (integration.error) status.textContent = `${integration.key_hint} · ${integration.error}`;
  else status.textContent = `${integration.key_hint} · Collegato${integration.tier ? ` · Piano ${integration.tier}` : ""}`;
  $("#first-run").hidden = Boolean(state.setup?.complete);
}

async function loadAll() {
  const [config, status, documents, voices, access, elevenlabs, setup] = await Promise.all([
    api("/api/config"), api("/api/status"), api("/api/documents"), api("/api/voices"), api("/api/access"), api("/api/elevenlabs"), api("/api/setup"),
  ]);
  state.config = config;
  state.status = status;
  state.documents = documents.items;
  state.elevenlabs = elevenlabs;
  state.setup = setup;
  state.voices = [...voices.items, ...(elevenlabs.items || [])];
  state.accessUrl = access.url;
  const accessLink = $("#access-url");
  accessLink.textContent = access.url;
  accessLink.href = access.url;
  renderStatus();
  renderIntegrations();
  renderVoices();
  renderCharacters();
  renderDocuments();
}

function openCharacter(character = null) {
  const form = $("#character-form");
  form.reset();
  form.elements.original_id.value = character?.id || "";
  form.elements.id.value = character?.id || "";
  form.elements.name.value = character?.name || "";
  form.elements.description.value = character?.description || "";
  form.elements.instructions.value = character?.instructions || "";
  form.elements.voice_id.value = character?.voice_id || "disabled";
  $("#character-dialog-title").textContent = character ? "Modifica amico" : "Nuovo amico";
  $("#character-dialog").showModal();
}

async function openDocument(id = null) {
  const form = $("#document-form");
  form.reset();
  const documentItem = id ? await api(`/api/documents/${id}`) : null;
  form.elements.id.value = documentItem?.id || "";
  form.elements.title.value = documentItem?.title || "";
  form.elements.text.value = documentItem?.text || "";
  $$("input[name=character_ids]", form).forEach(node => node.checked = documentItem?.character_ids?.includes(node.value) || false);
  $("#document-dialog-title").textContent = documentItem ? "Modifica storia" : "Nuova storia";
  $("#document-dialog").showModal();
}

async function previewVoice(voiceId) {
  const response = await fetch(`/api/voices/${voiceId}/preview`, jsonOptions("POST", { text: "Ciao! Sono pronto per una nuova avventura." }));
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  const player = $("#voice-preview");
  if (player.src) URL.revokeObjectURL(player.src);
  player.src = URL.createObjectURL(await response.blob());
  player.hidden = false;
  await player.play();
}

async function copyAccessUrl() {
  if (navigator.clipboard) await navigator.clipboard.writeText(state.accessUrl);
  else {
    const field = document.createElement("textarea");
    field.value = state.accessUrl;
    document.body.append(field);
    field.select();
    document.execCommand("copy");
    field.remove();
  }
  toast("Indirizzo copiato");
}

document.addEventListener("click", async event => {
  const closeButton = event.target.closest("[data-close-dialog]");
  if (closeButton) document.getElementById(closeButton.dataset.closeDialog).close();
  const navigation = event.target.closest("[data-view], [data-go]");
  if (navigation) switchView(navigation.dataset.view || navigation.dataset.go);
  if (event.target.id === "new-character") openCharacter();
  if (event.target.id === "new-document") await openDocument();
  if (event.target.id === "copy-access") await copyAccessUrl();
  if (event.target.id === "disconnect-elevenlabs") {
    await api("/api/elevenlabs", { method: "DELETE" });
    await loadAll();
    toast("ElevenLabs scollegato");
  }
  if (event.target.id === "install-requirements") {
    event.target.disabled = true;
    event.target.textContent = "Installazione in corso…";
    try { await api("/api/setup/install", { method: "POST" }); await loadAll(); toast("Componenti installati"); }
    catch (error) { toast(error.message, true); event.target.disabled = false; event.target.textContent = "Installa componenti"; }
  }

  const voiceCard = event.target.closest(".voice-card");
  if (voiceCard && event.target.matches(".install-voice")) {
    event.target.disabled = true;
    event.target.textContent = "Installazione…";
    try { await api(`/api/voices/${voiceCard.dataset.id}/install`, { method: "POST" }); await loadAll(); toast("Voce installata"); }
    catch (error) { toast(error.message, true); event.target.disabled = false; event.target.textContent = "Installa"; }
  }
  if (voiceCard && event.target.matches(".preview-voice")) {
    try { await previewVoice(voiceCard.dataset.id); }
    catch (error) { toast(error.message, true); }
  }

  const characterCard = event.target.closest(".character-card");
  if (characterCard && event.target.matches(".edit-character")) openCharacter(state.config.characters.find(item => item.id === characterCard.dataset.id));
  if (characterCard && event.target.matches(".activate-character")) {
    await api(`/api/characters/${characterCard.dataset.id}/activate`, { method: "POST" }); await loadAll(); toast("Amico scelto");
  }
  if (characterCard && event.target.matches(".delete-character") && confirm("Eliminare questo amico?")) {
    await api(`/api/characters/${characterCard.dataset.id}`, { method: "DELETE" }); await loadAll(); toast("Amico eliminato");
  }

  const documentRow = event.target.closest(".document-row");
  if (documentRow && event.target.matches(".edit-document")) await openDocument(documentRow.dataset.id);
  if (documentRow && event.target.matches(".delete-document") && confirm("Eliminare questa storia?")) {
    await api(`/api/documents/${documentRow.dataset.id}`, { method: "DELETE" }); await loadAll(); toast("Storia eliminata");
  }
  if (event.target.id === "rebuild-index") {
    event.target.disabled = true;
    event.target.textContent = "Preparazione…";
    try { const result = await api("/api/index/rebuild", { method: "POST" }); await loadAll(); toast(`${result.chunks} pezzi pronti`); }
    catch (error) { toast(error.message, true); }
    finally { event.target.disabled = false; event.target.textContent = "Prepara le storie"; }
  }
});

$("#character-form").addEventListener("submit", async event => {
  event.preventDefault();
  const body = Object.fromEntries(new FormData(event.currentTarget));
  const original = body.original_id;
  delete body.original_id;
  try {
    await api(original ? `/api/characters/${original}` : "/api/characters", jsonOptions(original ? "PUT" : "POST", body));
    $("#character-dialog").close();
    await loadAll();
    toast(original ? "Amico aggiornato" : "Nuovo amico creato");
  } catch (error) { toast(error.message, true); }
});

$("#elevenlabs-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const submit = form.querySelector('button[type="submit"]');
  submit.disabled = true;
  submit.textContent = "Verifica…";
  try {
    const result = await api("/api/elevenlabs", jsonOptions("POST", { api_key: form.elements.api_key.value }));
    form.reset();
    state.elevenlabs = result;
    state.voices = [...state.voices.filter(item => item.kind !== "elevenlabs"), ...(result.items || [])];
    renderIntegrations();
    renderVoices();
    renderCharacters();
    toast("ElevenLabs collegato");
  } catch (error) { toast(error.message, true); }
  finally { submit.disabled = false; submit.textContent = "Salva e verifica"; }
});

$("#document-form").addEventListener("submit", async event => {
  event.preventDefault();
  const data = new FormData(event.currentTarget);
  const id = data.get("id");
  const body = { title: data.get("title"), text: data.get("text"), character_ids: data.getAll("character_ids") };
  try {
    await api(id ? `/api/documents/${id}` : "/api/documents", jsonOptions(id ? "PUT" : "POST", body));
    $("#document-dialog").close();
    await loadAll();
    toast("Storia salvata");
  } catch (error) { toast(error.message, true); }
});

$("#file-upload").addEventListener("change", async event => {
  if (!event.target.files.length) return;
  const data = new FormData();
  data.append("file", event.target.files[0]);
  try { await api("/api/documents/upload", { method: "POST", body: data }); await loadAll(); toast("Storia aggiunta"); }
  catch (error) { toast(error.message, true); }
  finally { event.target.value = ""; }
});

window.addEventListener("unhandledrejection", event => toast(event.reason?.message || "Errore inatteso", true));
switchView(["dashboard", "characters", "knowledge", "voices"].includes(location.hash.slice(1)) ? location.hash.slice(1) : "dashboard");
loadAll().catch(error => toast(error.message, true));
