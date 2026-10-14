const state = { config: null, status: null, documents: [] };
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

function formatBytes(value) {
  if (value == null) return "Non disponibile";
  const units = ["B", "KB", "MB", "GB"];
  let size = Number(value), unit = 0;
  while (size >= 1024 && unit < units.length - 1) { size /= 1024; unit += 1; }
  return `${size.toFixed(unit > 1 ? 1 : 0)} ${units[unit]}`;
}

function switchView(name) {
  $$(".view").forEach(node => node.classList.toggle("active", node.id === `view-${name}`));
  $$(".nav-item").forEach(node => node.classList.toggle("active", node.dataset.view === name));
  history.replaceState(null, "", `#${name}`);
}

function renderStatus() {
  const status = state.status;
  if (!status) return;
  const online = status.llm_online;
  $(".connection").classList.toggle("online", online);
  $("#connection-label").textContent = online ? "Motore AI online" : "Motore AI non avviato";
  const memoryUsed = status.memory.total && status.memory.available ? status.memory.total - status.memory.available : null;
  $("#metrics").innerHTML = [
    [online ? "Online" : "Offline", "Servizio AI"],
    [status.documents, "Documenti"],
    [status.indexed_chunks, "Frammenti RAG"],
    [formatBytes(memoryUsed), "RAM utilizzata"],
  ].map(([value, label]) => `<div class="metric"><b>${value}</b><span>${label}</span></div>`).join("");
  $("#index-count").textContent = status.indexed_chunks;
  const rows = {
    "Motore AI": online ? "Online" : "Offline",
    "Modello configurato": status.model,
    "Personaggio attivo": status.active_character_id,
    "RAM totale": formatBytes(status.memory.total),
    "RAM disponibile": formatBytes(status.memory.available),
    "Spazio libero": formatBytes(status.disk.free),
    "Carico sistema": status.load_average?.join(" · ") || "Non disponibile",
    "Ingresso audio": status.audio.input_device || "Non configurato",
    "STT": status.audio.stt_provider,
    "TTS": status.audio.tts_provider,
    "Autenticazione": "Disattivata",
    "Documenti indicizzati": status.indexed_chunks,
  };
  $("#status-detail").innerHTML = Object.entries(rows).map(([key, value]) => `<div class="status-item"><span>${key}</span><b>${value}</b></div>`).join("");
}

function renderCharacters() {
  const activeId = state.config.active_character_id;
  const characters = state.config.characters;
  $("#character-list").innerHTML = characters.map(character => `
    <article class="character-card ${character.id === activeId ? "active" : ""}" data-id="${character.id}">
      <span class="badge">${character.id === activeId ? "In uso" : "Disponibile"}</span>
      <h3>${escapeHtml(character.name)}</h3>
      <p class="muted">${escapeHtml(character.description || "Nessuna descrizione")}</p>
      <small>Voce: ${escapeHtml(character.voice_id)}</small>
      <footer>
        ${character.id !== activeId ? '<button class="secondary activate-character">Attiva</button>' : ""}
        <button class="secondary edit-character">Modifica</button>
        ${characters.length > 1 ? '<button class="secondary delete-character">Elimina</button>' : ""}
      </footer>
    </article>`).join("");
  const active = characters.find(item => item.id === activeId);
  $("#active-name").textContent = active?.name || "—";
  $("#active-description").textContent = active?.description || "Nessuna descrizione";
  const child = state.config.child;
  const form = $("#child-form");
  form.elements.display_name.value = child.display_name || "";
  form.elements.age_range.value = child.age_range || "6-8";
  form.elements.story_preferences.value = child.story_preferences || "";
  $("#document-characters").innerHTML = characters.map(item => `<label><input type="checkbox" name="character_ids" value="${item.id}"> ${escapeHtml(item.name)}</label>`).join("");
}

function renderDocuments() {
  const root = $("#document-list");
  if (!state.documents.length) {
    root.innerHTML = '<div class="empty">Nessun contenuto. Scrivi una storia o carica un file UTF-8.</div>';
    return;
  }
  root.innerHTML = state.documents.map(item => `
    <article class="document-row" data-id="${item.id}">
      <div><h3>${escapeHtml(item.title)}</h3><small>${item.character_count} caratteri · ${item.character_ids?.length ? item.character_ids.join(", ") : "tutti i personaggi"}</small></div>
      <div><button class="secondary edit-document">Modifica</button><button class="secondary delete-document">Elimina</button></div>
    </article>`).join("");
}

function escapeHtml(value) {
  const node = document.createElement("span");
  node.textContent = String(value ?? "");
  return node.innerHTML;
}

async function loadAll() {
  const [config, status, documents, voices] = await Promise.all([
    api("/api/config"), api("/api/status"), api("/api/documents"), api("/api/voices"),
  ]);
  state.config = config; state.status = status; state.documents = documents.items;
  renderStatus(); renderCharacters(); renderDocuments();
  $("#voice-list").innerHTML = voices.items.map(item => `<div class="status-item"><span>${escapeHtml(item.name)}</span><b>${item.available ? "Disponibile" : "Da configurare"}</b></div>`).join("") + `<p class="muted">${escapeHtml(voices.note)}</p>`;
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
  form.elements.id.disabled = Boolean(character);
  $("#character-dialog-title").textContent = character ? "Modifica personaggio" : "Nuovo personaggio";
  $("#character-dialog").showModal();
}

async function openDocument(id = null) {
  const form = $("#document-form");
  form.reset();
  let document = null;
  if (id) document = await api(`/api/documents/${id}`);
  form.elements.id.value = document?.id || "";
  form.elements.title.value = document?.title || "";
  form.elements.text.value = document?.text || "";
  $$("input[name=character_ids]", form).forEach(node => node.checked = document?.character_ids?.includes(node.value) || false);
  $("#document-dialog-title").textContent = document ? "Modifica testo" : "Nuovo testo";
  $("#document-dialog").showModal();
}

document.addEventListener("click", async event => {
  const closeButton = event.target.closest("[data-close-dialog]");
  if (closeButton) document.getElementById(closeButton.dataset.closeDialog).close();
  const navigation = event.target.closest("[data-view], [data-go]");
  if (navigation) switchView(navigation.dataset.view || navigation.dataset.go);
  if (event.target.id === "new-character") openCharacter();
  if (event.target.id === "new-document") await openDocument();
  if (event.target.id === "refresh-status") { state.status = await api("/api/status"); renderStatus(); toast("Stato aggiornato"); }
  const characterCard = event.target.closest(".character-card");
  if (characterCard && event.target.matches(".edit-character")) openCharacter(state.config.characters.find(item => item.id === characterCard.dataset.id));
  if (characterCard && event.target.matches(".activate-character")) {
    await api(`/api/characters/${characterCard.dataset.id}/activate`, { method: "POST" }); await loadAll(); toast("Personaggio attivato");
  }
  if (characterCard && event.target.matches(".delete-character") && confirm("Eliminare questo personaggio?")) {
    await api(`/api/characters/${characterCard.dataset.id}`, { method: "DELETE" }); await loadAll(); toast("Personaggio eliminato");
  }
  const documentRow = event.target.closest(".document-row");
  if (documentRow && event.target.matches(".edit-document")) await openDocument(documentRow.dataset.id);
  if (documentRow && event.target.matches(".delete-document") && confirm("Eliminare questo testo?")) {
    await api(`/api/documents/${documentRow.dataset.id}`, { method: "DELETE" }); await loadAll(); toast("Testo eliminato");
  }
  if (event.target.id === "rebuild-index") {
    event.target.disabled = true; event.target.textContent = "Indicizzazione…";
    try { const result = await api("/api/index/rebuild", { method: "POST" }); await loadAll(); toast(`${result.chunks} frammenti indicizzati`); }
    catch (error) { toast(error.message, true); }
    finally { event.target.disabled = false; event.target.textContent = "Ricostruisci indice"; }
  }
});

$("#character-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const body = Object.fromEntries(new FormData(form));
  const original = body.original_id; delete body.original_id;
  try {
    await api(original ? `/api/characters/${original}` : "/api/characters", jsonOptions(original ? "PUT" : "POST", body));
    $("#character-dialog").close(); await loadAll(); toast("Personaggio salvato");
  } catch (error) { toast(error.message, true); }
});

$("#document-form").addEventListener("submit", async event => {
  event.preventDefault();
  const form = event.currentTarget;
  const data = new FormData(form);
  const id = data.get("id");
  const body = { title: data.get("title"), text: data.get("text"), character_ids: data.getAll("character_ids") };
  try {
    await api(id ? `/api/documents/${id}` : "/api/documents", jsonOptions(id ? "PUT" : "POST", body));
    $("#document-dialog").close(); await loadAll(); toast("Testo salvato. Ricostruisci l’indice per applicarlo.");
  } catch (error) { toast(error.message, true); }
});

$("#child-form").addEventListener("submit", async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.currentTarget));
  state.config.child = data;
  try { state.config.child = await api("/api/child", jsonOptions("PUT", data)); renderCharacters(); toast("Impostazioni salvate"); }
  catch (error) { toast(error.message, true); }
});

$("#file-upload").addEventListener("change", async event => {
  if (!event.target.files.length) return;
  const data = new FormData(); data.append("file", event.target.files[0]);
  try { await api("/api/documents/upload", { method: "POST", body: data }); await loadAll(); toast("File caricato"); }
  catch (error) { toast(error.message, true); }
  finally { event.target.value = ""; }
});

window.addEventListener("unhandledrejection", event => toast(event.reason?.message || "Errore inatteso", true));
switchView(location.hash.slice(1) || "dashboard");
loadAll().catch(error => toast(error.message, true));

