const DECISION_PANEL_ID = 'validationDecisionPanel'
let renderingDecision = false

function decisionEsc(value) {
  return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')
}

async function decisionApi(path, options = {}) {
  const response = await fetch(path, {
    cache: 'no-store',
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.message || payload.error || 'Falha no lock da decisão')
  return payload
}

function updateRoundBadge(status) {
  const panel = document.querySelector('#roundPanel')
  const badge = panel?.querySelector(':scope > section.card .section-head .badge')
  if (!badge) return
  if (status === 'validation_decision_continue') {
    badge.textContent = 'decisão: continuar'
    badge.classList.add('success')
  } else if (status === 'validation_decision_stop') {
    badge.textContent = 'decisão: parar em B'
    badge.classList.add('danger')
  }
}

function unlockedHtml() {
  return `<section class="card" id="${DECISION_PANEL_ID}" style="margin-top:1rem">
    <div class="section-head"><div><span class="eyebrow">lock pré-external</span><h2>Bloquear decisão de validation</h2></div><span class="badge">pendente</span></div>
    <p>A decisão não será escolhida manualmente. O NutEV verificará novamente hashes, gold PASS, par primário, split e o resultado da comparação pré-especificada.</p>
    <div class="notice"><strong>Regra determinística:</strong> <code>CONTINUATION_CRITERIA_PASS</code> → <code>CONTINUE_TO_EXTERNAL</code>; <code>CONTINUATION_CRITERIA_FAIL</code> → <code>STOP_AT_B</code>.</div>
    <div class="actions" style="margin-top:.8rem"><button class="btn primary" id="lockValidationDecision">Bloquear decisão de validation</button></div>
    <p class="small muted" style="margin-top:.55rem">Este botão não abre, importa nem calcula o <code>external_test</code>.</p>
  </section>`
}

function lockedHtml(decision) {
  const continueExternal = decision.decision === 'CONTINUE_TO_EXTERNAL'
  return `<section class="card" id="${DECISION_PANEL_ID}" style="margin-top:1rem">
    <div class="section-head"><div><span class="eyebrow">decisão de validation bloqueada</span><h2>${continueExternal ? 'CONTINUE_TO_EXTERNAL' : 'STOP_AT_B'}</h2></div><span class="badge ${continueExternal ? 'success' : 'danger'}">LOCKED</span></div>
    <div class="notice ${continueExternal ? 'success' : 'danger'}"><strong>${continueExternal ? 'Os critérios pré-especificados permitem avançar para a etapa externa.' : 'O candidato permanece em B — DEMOTE neste ciclo.'}</strong></div>
    <div class="grid" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-top:1rem">
      <div class="kpi"><strong>${decisionEsc(decision.validation_evidence_status || '—')}</strong><span>gate de validation</span></div>
      <div class="kpi"><strong>${decision.validation_continuation_pass === true ? 'SIM' : 'NÃO'}</strong><span>continuação</span></div>
      <div class="kpi"><strong>NÃO</strong><span>external liberado</span></div>
    </div>
    <div class="notice" style="margin-top:1rem"><strong>External test continua selado.</strong> O lock apenas registra a decisão. Qualquer liberação do conjunto externo é uma ação posterior e separada do custodiante.</div>
    <div class="small muted" style="margin-top:.55rem">Bloqueado em ${decisionEsc(decision.locked_at || '—')}.</div>
  </section>`
}

async function lockDecision(button) {
  button.disabled = true
  button.textContent = 'Verificando e bloqueando…'
  try {
    await decisionApi('/api/validation/decision/lock', { method:'POST', body:'{}' })
    await renderDecisionPanel()
  } catch (error) {
    alert(error.message || String(error))
    button.disabled = false
    button.textContent = 'Bloquear decisão de validation'
  }
}

async function renderDecisionPanel() {
  if (renderingDecision) return
  const roundPanel = document.querySelector('#roundPanel')
  if (!roundPanel) return
  renderingDecision = true
  try {
    const roundResponse = await fetch('/api/validation/round', { cache:'no-store' })
    if (!roundResponse.ok) return
    const round = await roundResponse.json()
    const relevant = ['validation_metrics_complete','validation_decision_continue','validation_decision_stop'].includes(round.status)
    document.querySelector(`#${DECISION_PANEL_ID}`)?.remove()
    if (!relevant) return

    const decision = await decisionApi('/api/validation/decision')
    if (decision.locked) {
      roundPanel.insertAdjacentHTML('beforeend', lockedHtml(decision))
      updateRoundBadge(round.status)
      return
    }
    if (round.status === 'validation_metrics_complete' && decision.ready) {
      roundPanel.insertAdjacentHTML('beforeend', unlockedHtml())
      document.querySelector('#lockValidationDecision')?.addEventListener('click', event => lockDecision(event.currentTarget))
    }
  } catch {
    // The decision layer is supplementary; the main validation panel remains usable.
  } finally {
    renderingDecision = false
  }
}

const appRoot = document.querySelector('#app')
const observer = new MutationObserver(() => queueMicrotask(renderDecisionPanel))
if (appRoot) observer.observe(appRoot, { childList:true, subtree:true })
renderDecisionPanel()
