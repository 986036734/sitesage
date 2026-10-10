const $ = (id) => document.getElementById(id);
let sessionId = null;

function setStatus(t) { $("status").textContent = t; }

$("loadBtn").onclick = loadPage;
$("url").addEventListener("keydown", (e) => { if (e.key === "Enter") loadPage(); });
$("askBtn").onclick = ask;
$("question").addEventListener("keydown", (e) => { if (e.key === "Enter") ask(); });

async function loadPage() {
  const url = $("url").value.trim();
  if (!url) return;
  setStatus("Fetching page…");
  $("loadBtn").disabled = true;
  try {
    const r = await fetch("/api/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    const d = await r.json();
    sessionId = d.session_id;
    $("pageTitle").textContent = d.title;
    $("pageUrl").textContent = d.url;
    $("pageStats").textContent = `${d.chunks} sections · ${(d.chars / 1000).toFixed(1)}k chars`;
    $("pageSummary").textContent = d.summary || "Summary unavailable.";
    const sug = $("suggested");
    sug.innerHTML = "";
    (d.suggested || []).forEach((q) => {
      const b = document.createElement("button");
      b.className = "chip"; b.textContent = q;
      b.onclick = () => { $("question").value = q; ask(); };
      sug.appendChild(b);
    });
    $("pageCard").classList.remove("hidden");
    $("chatCard").classList.remove("hidden");
    $("chatLog").innerHTML = "";
    setStatus("Ready — ask anything below.");
  } catch (e) {
    setStatus("Error: " + e.message);
  } finally {
    $("loadBtn").disabled = false;
  }
}

function addMsg(text, who, model) {
  const div = document.createElement("div");
  div.className = "msg " + who;
  div.textContent = text;
  if (model) {
    const m = document.createElement("span");
    m.className = "model";
    m.textContent = "via " + model.split("/").pop();
    div.appendChild(m);
  }
  $("chatLog").appendChild(div);
  $("chatLog").scrollTop = $("chatLog").scrollHeight;
  return div;
}

async function ask() {
  const q = $("question").value.trim();
  if (!q || !sessionId) return;
  $("question").value = "";
  addMsg(q, "user");
  const typing = addMsg("Thinking…", "bot");
  typing.classList.add("typing");
  $("askBtn").disabled = true;
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, question: q, mode: $("mode").value }),
    });
    if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
    const d = await r.json();
    typing.remove();
    addMsg(d.answer, "bot", d.model);
  } catch (e) {
    typing.remove();
    addMsg("Error: " + e.message, "bot");
  } finally {
    $("askBtn").disabled = false;
  }
}

fetch("/api/health").then((r) => r.json()).then((h) => {
  if (!h.llm_configured) setStatus("Note: server has no NEBIUS_API_KEY yet — Q&A disabled until configured.");
});
