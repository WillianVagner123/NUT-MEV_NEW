const STATUS_URL = "/api/synthesis/releases";
const PREPARE_URL = "/api/synthesis/releases/prepare";
const STAGE_OPERATION = "STAGE_RECOMMENDATION_ADOPTION";
const DECIDE_OPERATION = "DECIDE_RECOMMENDATION_ADOPTION";

const qs = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));

async function request(url, options={}) {
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || data.message || `HTTP ${response.status}`);
  return data;
}

function post(payload) {
  return request(PREPARE_URL, {
    method: "POST",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload),
  });
}

function badge(text) { return `<span class="status-pill">${esc(text)}</span>`; }

function renderKpis(data) {
  const counts = data.recommendation_adoption_counts || {};
  qs("#adoptionKpis").innerHTML = [
    ["PENDING", counts.PENDING || 0],
    ["ADOPTED SCOPE", counts.ADOPT_FOR_DEFINED_SCOPE || 0],
    ["REJECT", counts.REJECT || 0],
    ["RETURN", counts.RETURN_FOR_REVISION || 0],
  ].map(([label,value]) => `<div class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong></div>`).join("");
}

function renderDevelopments(data) {
  const items = data.finalized_recommendation_developments || [];
  const root = qs("#developmentRecords");
  if (!items.length) { root.innerHTML = `<div class="empty-state">Nenhum Recommendation Development finalizado.</div>`; return; }
  root.innerHTML = items.map((item) => {
    const status = item.recommendation_adoption_status || "NOT_STAGED";
    const canStage = status === "NOT_STAGED";
    return `<article class="adoption-card" data-development-id="${esc(item.development_id)}">
      <h3>${esc(item.proposed_recommendation_text || item.development_id)}</h3>
      <div class="adoption-meta">${badge(`development ${item.development_id}`)}${badge(`strength ${item.recommendation_strength || "not_evaluated"}`)}${badge(`adoption ${status}`)}</div>
      <p><strong>Population/scope:</strong> ${esc(item.population_scope || "—")}</p>
      ${canStage ? `<div class="adoption-form">
        <input class="stage-by" placeholder="Quem está abrindo o gate de governance">
        <textarea class="stage-scope" rows="3" placeholder="Defina exatamente o adoption scope (mín. 30 caracteres)"></textarea>
        <textarea class="stage-purpose" rows="3" placeholder="Governance purpose (mín. 30 caracteres)"></textarea>
        <button class="stage-adoption" type="button">Abrir Adoption Case PENDING</button>
      </div>` : `<p>Este development já possui Adoption Case. Nenhuma nova decisão é inferida.</p>`}
    </article>`;
  }).join("");

  root.querySelectorAll(".stage-adoption").forEach((button) => button.addEventListener("click", async () => {
    const card = button.closest(".adoption-card");
    button.disabled = true;
    try {
      await post({
        operation: STAGE_OPERATION,
        recommendation_development_id: card.dataset.developmentId,
        staged_by: card.querySelector(".stage-by").value.trim(),
        adoption_scope: card.querySelector(".stage-scope").value.trim(),
        governance_purpose: card.querySelector(".stage-purpose").value.trim(),
      });
      await load();
    } catch (error) { alert(error.message); button.disabled = false; }
  }));
}

function renderPending(data) {
  const items = (data.recommendation_adoption_cases || []).filter((item) => item.status === "PENDING");
  const root = qs("#pendingAdoptions");
  if (!items.length) { root.innerHTML = `<div class="empty-state">Nenhum Adoption Case PENDING.</div>`; return; }
  root.innerHTML = items.map((item) => `<article class="adoption-card" data-adoption-id="${esc(item.adoption_id)}">
    <h3>${esc(item.proposed_recommendation_text || item.adoption_id)}</h3>
    <div class="adoption-meta">${badge("PENDING")}${badge(`strength ${item.recommendation_strength || "not_evaluated"}`)}</div>
    <p><strong>Adoption scope:</strong> ${esc(item.adoption_scope)}</p>
    <p><strong>Governance purpose:</strong> ${esc(item.governance_purpose)}</p>
    <div class="adoption-form">
      <select class="decision"><option value="">Selecione uma decisão humana…</option><option value="ADOPT_FOR_DEFINED_SCOPE">ADOPT_FOR_DEFINED_SCOPE</option><option value="REJECT">REJECT</option><option value="RETURN_FOR_REVISION">RETURN_FOR_REVISION</option></select>
      <input class="governor" placeholder="Governor responsável">
      <textarea class="rationale" rows="4" placeholder="Rationale da decisão (mín. 50 caracteres)"></textarea>
      <textarea class="revision" rows="3" placeholder="Revision instructions — somente RETURN_FOR_REVISION" disabled></textarea>
      <div class="adoption-confirmations">
        <label><input type="checkbox" class="c-human"> A decisão foi inserida explicitamente por humano.</label>
        <label><input type="checkbox" class="c-scope"> ADOPT, se escolhido, vale somente para o escopo definido.</label>
        <label><input type="checkbox" class="c-strength"> A decisão não infere recommendation strength, certainty ou GRADE.</label>
        <label><input type="checkbox" class="c-clinical"> A decisão não cria clinical/guideline recommendation automaticamente.</label>
        <label><input type="checkbox" class="c-immutable"> Recommendation Development e upstream permanecem imutáveis.</label>
      </div>
      <button class="decide-adoption" type="button">Registrar decisão de governance</button>
    </div>
  </article>`).join("");

  root.querySelectorAll(".adoption-card").forEach((card) => {
    const decision = card.querySelector(".decision");
    const revision = card.querySelector(".revision");
    decision.addEventListener("change", () => {
      const enabled = decision.value === "RETURN_FOR_REVISION";
      revision.disabled = !enabled;
      if (!enabled) revision.value = "";
    });
    card.querySelector(".decide-adoption").addEventListener("click", async (event) => {
      const button = event.currentTarget;
      button.disabled = true;
      try {
        await post({
          operation: DECIDE_OPERATION,
          adoption_id: card.dataset.adoptionId,
          decision: decision.value,
          governor: card.querySelector(".governor").value.trim(),
          rationale: card.querySelector(".rationale").value.trim(),
          revision_instructions: revision.value.trim(),
          decision_human_entered_confirmed: card.querySelector(".c-human").checked,
          defined_scope_only_confirmed: card.querySelector(".c-scope").checked,
          no_strength_or_certainty_inference_confirmed: card.querySelector(".c-strength").checked,
          not_clinical_or_guideline_recommendation_confirmed: card.querySelector(".c-clinical").checked,
          upstream_immutable_confirmed: card.querySelector(".c-immutable").checked,
        });
        await load();
      } catch (error) { alert(error.message); button.disabled = false; }
    });
  });
}

function renderFinalized(data) {
  const items = data.finalized_recommendation_adoptions || [];
  const root = qs("#finalizedAdoptions");
  if (!items.length) { root.innerHTML = `<div class="empty-state">Nenhuma decisão canônica de adoption.</div>`; return; }
  root.innerHTML = items.map((item) => `<article class="adoption-card">
    <h3>${esc(item.decision)}</h3>
    <div class="adoption-meta">${badge(item.adopted_for_defined_scope ? "SCOPE-LIMITED ADOPTION" : "NOT ADOPTED")}${badge(`strength ${item.recommendation_strength}`)}${badge(`certainty ${item.certainty_assessed ? "ASSESSED" : "NOT ASSESSED"}`)}</div>
    <p><strong>Scope:</strong> ${esc(item.adoption_scope)}</p>
    <p><strong>Governor:</strong> ${esc(item.governor)}</p>
    <p><strong>Rationale:</strong> ${esc(item.rationale)}</p>
    ${item.revision_instructions ? `<p><strong>Revision instructions:</strong> ${esc(item.revision_instructions)}</p>` : ""}
    <p><strong>Clinical recommendation created:</strong> NO · <strong>Guideline recommendation created:</strong> NO</p>
  </article>`).join("");
}

async function load() {
  qs("#adoptionState").classList.remove("hidden");
  try {
    const data = await request(STATUS_URL);
    qs("#adoptionHealth").textContent = "local-only · ready";
    renderKpis(data); renderDevelopments(data); renderPending(data); renderFinalized(data);
    qs("#adoptionContent").classList.remove("hidden");
    qs("#adoptionState").classList.add("hidden");
  } catch (error) {
    qs("#adoptionHealth").textContent = "erro";
    qs("#adoptionState").textContent = error.message;
  }
}

qs("#refreshAdoption").addEventListener("click", load);
load();
