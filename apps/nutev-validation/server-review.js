const root = document.querySelector('#reviewApp')
const TOKEN_KEY = 'nutev_validation_private_token_v1'
const QUICK_REASONS = {
  0: ['Fora do escopo da pergunta', 'População/intervenção não aplicável', 'Não responde ao construto de interesse'],
  1: ['Relevante como contexto ou apoio', 'Aplicação parcial à pergunta', 'Útil, mas não é referência central'],
  2: ['Diretamente aplicável à pergunta', 'Referência central para a pergunta', 'Evidência-chave para o construto'],
}
const state = { token: '', data: null, index: 0, saveTimer: null, saving: false }

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;')
}

function acquireToken() {
  const hash = location.hash.startsWith('#') ? location.hash.slice(1) : ''
  const fromHash = new URLSearchParams(hash).get('token') || ''
  if (fromHash) {
    sessionStorage.setItem(TOKEN_KEY, fromHash)
    history.replaceState({}, '', location.pathname + location.search)
    return fromHash
  }
  return sessionStorage.getItem(TOKEN_KEY) || ''
}

async function api(path, options = {}) {
  const headers = { ...(options.headers || {}), Authorization: `Bearer ${state.token}` }
  if (options.body && !headers['Content-Type']) headers['Content-Type'] = 'application/json'
  const response = await fetch(path, { ...options, headers, cache: 'no-store' })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.message || payload.error || 'Falha na validação')
  return payload
}

function pageShell(content) {
  return `<div class="review-shell">
    <header class="review-topbar">
      <div class="review-brand"><div class="review-mark">N</div><div><strong>NutEV Validation</strong><span>avaliação cega independente</span></div></div>
      <div class="review-status"><span class="badge">${esc(state.data?.assessor_id || '')}</span><span class="badge">sem score · sem rank</span></div>
    </header>
    <main class="review-main">${content}</main>
  </div>`
}

function contextHtml(context) {
  const labels = {
    population_context: 'População', intervention_exposure: 'Intervenção/exposição', comparator: 'Comparador',
    outcome_construct: 'Desfecho/construto', time_window: 'Janela temporal', languages: 'Idiomas', document_types: 'Tipos de documento',
  }
  const entries = Object.entries(context || {}).filter(([, value]) => value)
  if (!entries.length) return ''
  return `<div class="context-list">${entries.map(([key, value]) => `<div><strong>${esc(labels[key] || key)}</strong>${esc(value)}</div>`).join('')}</div>`
}

function referenceLink(item) {
  let href = item.url || ''
  if (item.doi) href = `https://doi.org/${String(item.doi).replace(/^https?:\/\/doi\.org\//i, '').replace(/^doi:/i, '')}`
  else if (!href && item.pmid) href = `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(item.pmid)}/`
  return href ? `<div class="ref-link"><a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Abrir referência ↗</a></div>` : ''
}

function current() { return state.data?.assignments?.[state.index] }

function completedCount() {
  return (state.data?.assignments || []).filter(item => item.relevance_grade !== null && item.relevance_grade !== undefined && String(item.reason || '').trim()).length
}

function firstIncompleteIndex() {
  const index = (state.data?.assignments || []).findIndex(item => item.relevance_grade === null || item.relevance_grade === undefined || !String(item.reason || '').trim())
  return index >= 0 ? index : 0
}

function render() {
  if (!state.data) return
  if (state.data.locked) {
    root.innerHTML = pageShell(`<section class="card locked-card"><h2>Avaliação enviada e travada ✓</h2><p class="muted">Suas decisões foram submetidas. Este link agora é somente leitura.</p><p><strong>${state.data.completed_items}/${state.data.total_items}</strong> itens concluídos.</p></section>`)
    return
  }
  const item = current()
  if (!item) {
    root.innerHTML = pageShell('<section class="card"><h2>Nenhum item disponível</h2></section>')
    return
  }
  const done = completedCount(), total = state.data.assignments.length
  const pct = total ? Math.round(done / total * 100) : 0
  root.innerHTML = pageShell(`
    <div class="review-layout">
      <section class="card reference-card">
        <div class="question-box"><strong>Pergunta ${esc(item.question_id)}</strong><div style="margin-top:.3rem">${esc(item.question_text)}</div>${contextHtml(item.eligibility_context)}</div>
        <div class="meta"><span>${esc(item.journal || '—')}</span><span>${esc(item.year || '—')}</span>${item.pmid ? `<span>PMID ${esc(item.pmid)}</span>` : ''}${item.doi ? `<span>DOI ${esc(item.doi)}</span>` : ''}</div>
        <h2 class="ref-title">${esc(item.title || '(sem título)')}</h2>
        ${item.abstract ? `<div class="abstract">${esc(item.abstract)}</div>` : '<div class="notice">Resumo não disponível no packet assessor-safe.</div>'}
        ${referenceLink(item)}

        <h3 style="margin-top:1.2rem">Relevância para esta pergunta</h3>
        <div class="grade-grid">
          <button class="grade ${item.relevance_grade === 0 ? 'selected' : ''}" data-grade="0">0 · Irrelevante</button>
          <button class="grade ${item.relevance_grade === 1 ? 'selected' : ''}" data-grade="1">1 · Relevante/periférica</button>
          <button class="grade ${item.relevance_grade === 2 ? 'selected' : ''}" data-grade="2">2 · Diretamente relevante</button>
        </div>
        <div id="quickReasons" class="quick-reasons"></div>
        <div class="form-row"><label for="reason">Justificativa</label><textarea id="reason" placeholder="Explique brevemente por que esta referência recebeu essa nota.">${esc(item.reason || '')}</textarea></div>
        <div class="form-row"><label class="blind-check"><input id="blind" type="checkbox" ${item.blind_to_nutev !== false ? 'checked' : ''}><span><strong>Permaneço cego ao sistema NutEV</strong><br><span class="small muted">Não vi rank, score, origem do sistema ou decisão do outro avaliador para este item.</span></span></label></div>
        <div class="form-row"><label class="review-later"><input id="reviewLater" type="checkbox" ${item.review_later ? 'checked' : ''}> Revisar novamente depois</label></div>
        <div class="form-row"><label for="notes">Notas opcionais</label><textarea id="notes" style="min-height:65px">${esc(item.notes || '')}</textarea></div>
        <div class="review-nav"><button class="btn" id="prevBtn" ${state.index === 0 ? 'disabled' : ''}>← Anterior</button><span class="save-state" id="saveState">salvo</span><button class="btn primary" id="nextBtn">${state.index + 1 >= total ? 'Salvar' : 'Próxima →'}</button></div>
      </section>

      <aside class="card review-side">
        <h3>Progresso</h3>
        <div class="progress-wrap"><div class="progress"><span style="width:${pct}%"></span></div><strong>${pct}%</strong></div>
        <div class="progress-note">${done} de ${total} com nota + justificativa.</div>
        <div class="grid" style="margin-top:1rem">
          <div class="kpi"><strong>${state.index + 1}</strong><span>item atual</span></div>
          <div class="kpi"><strong>${(state.data.assignments || []).filter(x => x.review_later).length}</strong><span>marcados para revisar</span></div>
        </div>
        <button class="btn" id="jumpIncomplete" style="width:100%;margin-top:1rem">Ir para próximo incompleto</button>
        <div class="submit-box"><button class="btn primary" id="submitBtn" style="width:100%" ${done === total ? '' : 'disabled'}>Enviar avaliação</button><p class="small muted">Depois de enviar, suas decisões ficam travadas.</p></div>
      </aside>
    </div>`)
  bind()
  renderQuickReasons()
}

function syncCurrentFromForm() {
  const item = current(); if (!item) return
  const checked = document.querySelector('.grade.selected')
  item.relevance_grade = checked ? Number(checked.dataset.grade) : null
  item.reason = document.querySelector('#reason')?.value || ''
  item.blind_to_nutev = Boolean(document.querySelector('#blind')?.checked)
  item.review_later = Boolean(document.querySelector('#reviewLater')?.checked)
  item.notes = document.querySelector('#notes')?.value || ''
}

function renderQuickReasons() {
  const item = current(), target = document.querySelector('#quickReasons')
  if (!item || !target || ![0,1,2].includes(item.relevance_grade)) { if (target) target.innerHTML = ''; return }
  target.innerHTML = QUICK_REASONS[item.relevance_grade].map(reason => `<button class="btn" data-reason="${esc(reason)}">${esc(reason)}</button>`).join('')
  target.querySelectorAll('[data-reason]').forEach(button => button.addEventListener('click', () => {
    const textarea = document.querySelector('#reason'); if (!textarea) return
    textarea.value = button.dataset.reason || ''; syncCurrentFromForm(); scheduleSave()
  }))
}

function scheduleSave() {
  syncCurrentFromForm()
  clearTimeout(state.saveTimer)
  const saveState = document.querySelector('#saveState'); if (saveState) saveState.textContent = 'alterado…'
  state.saveTimer = setTimeout(() => saveCurrent(false).catch(showError), 850)
}

async function saveCurrent(forcePartial) {
  syncCurrentFromForm()
  const item = current(); if (!item || state.saving) return
  const complete = [0,1,2].includes(item.relevance_grade) && String(item.reason || '').trim()
  if (!complete && !(forcePartial && item.review_later)) return
  state.saving = true
  const saveState = document.querySelector('#saveState'); if (saveState) saveState.textContent = 'salvando…'
  try {
    const updated = await api('/api/validation/reviewer/save', {
      method: 'POST',
      body: JSON.stringify({
        pool_item_id: item.pool_item_id,
        relevance_grade: complete ? item.relevance_grade : null,
        reason: complete ? item.reason : '',
        blind_to_nutev: item.blind_to_nutev === true,
        review_later: item.review_later === true,
        notes: item.notes || '',
      }),
    })
    state.data = updated
    if (saveState) saveState.textContent = 'salvo ✓'
  } finally { state.saving = false }
}

async function move(delta) {
  await saveCurrent(true)
  state.index = Math.max(0, Math.min(state.data.assignments.length - 1, state.index + delta))
  render()
}

async function submit() {
  await saveCurrent(true)
  if (completedCount() !== state.data.assignments.length) return showError(new Error('Complete todos os itens antes de enviar.'))
  if (!confirm('Enviar e travar sua avaliação? Depois disso as decisões não poderão ser alteradas.')) return
  state.data = await api('/api/validation/reviewer/submit', { method: 'POST', body: '{}' })
  render()
}

function bind() {
  document.querySelectorAll('.grade').forEach(button => button.addEventListener('click', () => {
    document.querySelectorAll('.grade').forEach(x => x.classList.remove('selected'))
    button.classList.add('selected'); syncCurrentFromForm(); renderQuickReasons(); scheduleSave()
  }))
  for (const selector of ['#reason','#blind','#reviewLater','#notes']) {
    const element = document.querySelector(selector)
    element?.addEventListener(element.tagName === 'TEXTAREA' ? 'input' : 'change', scheduleSave)
  }
  document.querySelector('#prevBtn')?.addEventListener('click', () => move(-1).catch(showError))
  document.querySelector('#nextBtn')?.addEventListener('click', () => move(1).catch(showError))
  document.querySelector('#jumpIncomplete')?.addEventListener('click', async () => { await saveCurrent(true); state.index = firstIncompleteIndex(); render() })
  document.querySelector('#submitBtn')?.addEventListener('click', () => submit().catch(showError))
}

function showError(error) {
  const prior = document.querySelector('#reviewError'); prior?.remove()
  const div = document.createElement('div'); div.id = 'reviewError'; div.className = 'notice danger'; div.textContent = error.message || String(error)
  div.style.position='fixed'; div.style.right='1rem'; div.style.bottom='1rem'; div.style.maxWidth='430px'; div.style.zIndex='999'
  document.body.appendChild(div); setTimeout(() => div.remove(), 5000)
}

async function init() {
  state.token = acquireToken()
  if (!state.token) {
    root.innerHTML = pageShell('<section class="card"><h2>Link privado ausente</h2><p>Abra exatamente o link fornecido pelo coordenador.</p></section>')
    return
  }
  try {
    state.data = await api('/api/validation/reviewer')
    state.index = firstIncompleteIndex()
    render()
  } catch (error) {
    sessionStorage.removeItem(TOKEN_KEY)
    root.innerHTML = pageShell(`<section class="card"><h2>Não foi possível abrir a avaliação</h2><p class="notice danger">${esc(error.message)}</p></section>`)
  }
}

window.addEventListener('keydown', event => {
  if (!state.data || state.data.locked || ['INPUT','TEXTAREA'].includes(document.activeElement?.tagName)) return
  if (['0','1','2'].includes(event.key)) document.querySelector(`.grade[data-grade="${event.key}"]`)?.click()
  if (event.key === 'ArrowRight') document.querySelector('#nextBtn')?.click()
  if (event.key === 'ArrowLeft') document.querySelector('#prevBtn')?.click()
})

init()
