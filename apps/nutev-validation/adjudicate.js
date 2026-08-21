const root = document.querySelector('#adjudicationApp')
const ADJUDICATOR_STORAGE_ID = 'nutev_validation_adjudicator_id_v1'
const state = { data: null, index: 0, adjudicatorId: localStorage.getItem(ADJUDICATOR_STORAGE_ID) || '' }

function esc(value) {
  return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')
}

async function api(path, options = {}) {
  const response = await fetch(path, { cache: 'no-store', ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } })
  const payload = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(payload.message || payload.error || 'Falha na adjudicação')
  return payload
}

function shell(content) {
  return `<div class="unified-shell">
    <aside class="product-sidebar">
      <div class="product-brand"><div class="product-brand-mark">N</div><div><strong>NutEV</strong><span>Evidence Engine</span></div></div>
      <nav class="product-nav">
        <a href="/">⌕ <span>Buscar evidências</span></a>
        <a href="/?view=history">◷ <span>Minhas buscas</span></a>
        <a class="active" href="/validation/">✓ <span>Validação científica</span></a>
      </nav>
      <div class="product-sidebar-note">A adjudicação só é liberada depois que todos os julgamentos iniciais estiverem enviados e travados.</div>
    </aside>
    <section class="workspace"><main class="adjudication-main">${content}</main></section>
  </div>`
}

function current() { return state.data?.conflicts?.[state.index] }
function parseContext(value) { try { return typeof value === 'string' ? JSON.parse(value || '{}') : (value || {}) } catch { return {} } }

function contextHtml(item) {
  const context = parseContext(item.eligibility_context)
  const labels = { population_context:'População', intervention_exposure:'Intervenção/exposição', comparator:'Comparador', outcome_construct:'Desfecho/construto', time_window:'Janela temporal', languages:'Idiomas', document_types:'Tipos documentais' }
  const entries = Object.entries(context).filter(([, value]) => value)
  return `<div class="question-context"><strong>${esc(item.question_id)}</strong><div style="margin-top:.3rem">${esc(item.question_text)}</div>${entries.length ? `<div class="context-list">${entries.map(([key,value])=>`<div><strong>${esc(labels[key]||key)}</strong>${esc(value)}</div>`).join('')}</div>` : ''}</div>`
}

function referenceLink(item) {
  let href = item.url || ''
  if (item.doi) href = `https://doi.org/${String(item.doi).replace(/^https?:\/\/doi\.org\//i,'').replace(/^doi:/i,'')}`
  else if (!href && item.pmid) href = `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(item.pmid)}/`
  return href ? `<a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Abrir referência ↗</a>` : ''
}

function judgmentHtml(judgment) {
  return `<article class="judgment-card"><span class="eyebrow">${esc(judgment.assessor_id)}</span><div class="grade-value">${Number(judgment.relevance_grade)}</div><strong>Justificativa</strong><p>${esc(judgment.reason || '—')}</p><div class="small muted">Decisão inicial travada em ${esc(judgment.decision_timestamp || '—')}</div></article>`
}

function render() {
  if (!state.data) return
  const conflicts = state.data.conflicts || []
  const complete = state.data.status === 'adjudication_complete'
  if (!conflicts.length) {
    root.innerHTML = shell(`<div class="adjudication-header"><div><span class="eyebrow">adjudicação</span><h1>Nenhum conflito</h1></div><a class="btn" href="/validation/">Voltar</a></div><section class="card completion-card"><h2>Os avaliadores concordaram em todos os pares ✓</h2><p>${state.data.agreed_pairs} pares com concordância direta.</p>${complete ? '<div class="notice success">Adjudicação encerrada. O sistema pode avançar para a construção/validação do gold standard.</div>' : '<button class="btn primary" id="finalizeBtn">Encerrar adjudicação</button>'}</section>`)
    document.querySelector('#finalizeBtn')?.addEventListener('click', finalize)
    return
  }
  state.index = Math.max(0, Math.min(state.index, conflicts.length - 1))
  const item = current()
  const decision = item.adjudication || null
  const pct = state.data.conflict_pairs ? Math.round(state.data.resolved_conflicts / state.data.conflict_pairs * 100) : 100
  root.innerHTML = shell(`
    <div class="adjudication-header"><div><span class="eyebrow">adjudicação humana</span><h1>Resolver discordâncias</h1><p class="muted">Somente conflitos são exibidos. Nenhuma decisão é escolhida automaticamente.</p></div><a class="btn" href="/validation/">Voltar ao painel</a></div>
    <div class="adjudication-grid">
      <section class="card">
        <div class="section-head"><div><span class="${decision ? 'resolved-mark' : 'unresolved-mark'}">${decision ? 'RESOLVIDO' : 'PENDENTE'}</span><h2>Conflito ${state.index + 1} de ${conflicts.length}</h2></div><span class="badge">${esc(item.reference_id)}</span></div>
        ${contextHtml(item)}
        <div class="meta"><span>${esc(item.journal || '—')}</span><span>${esc(item.year || '—')}</span>${item.pmid ? `<span>PMID ${esc(item.pmid)}</span>` : ''}${item.doi ? `<span>DOI ${esc(item.doi)}</span>` : ''}</div>
        <h3 class="conflict-title">${esc(item.title || '(sem título)')}</h3>
        ${item.abstract ? `<div class="abstract">${esc(item.abstract)}</div>` : '<div class="notice">Resumo não disponível.</div>'}
        <div style="margin-top:.6rem">${referenceLink(item)}</div>
        <div class="judgment-grid">${(item.judgments || []).map(judgmentHtml).join('')}</div>
        <div class="decision-box">
          <h3>Decisão final do adjudicador</h3>
          <p class="small muted">Escolha a relevância final após revisar a pergunta, a referência e as justificativas independentes.</p>
          <div class="grade-grid">
            <button class="grade ${decision?.relevance_grade === 0 ? 'selected' : ''}" data-grade="0">0 · Irrelevante</button>
            <button class="grade ${decision?.relevance_grade === 1 ? 'selected' : ''}" data-grade="1">1 · Relevante/periférica</button>
            <button class="grade ${decision?.relevance_grade === 2 ? 'selected' : ''}" data-grade="2">2 · Diretamente relevante</button>
          </div>
          <div class="form-row"><label for="adjudicatorId">Identificador do adjudicador</label><input id="adjudicatorId" value="${esc(decision?.adjudicator_id || state.adjudicatorId)}" placeholder="Ex.: adjudicator_01"></div>
          <div class="form-row"><label for="adjudicationNotes">Notas da adjudicação</label><textarea id="adjudicationNotes" placeholder="Racional opcional ou observação de auditoria.">${esc(decision?.notes || '')}</textarea></div>
          <button class="btn primary" id="saveDecision">Salvar decisão humana</button>
        </div>
        <div class="conflict-nav"><button class="btn" id="prevConflict" ${state.index === 0 ? 'disabled' : ''}>← Anterior</button><button class="btn" id="nextConflict" ${state.index + 1 >= conflicts.length ? 'disabled' : ''}>Próximo →</button></div>
      </section>
      <aside class="card adjudication-side"><h3>Progresso</h3><div class="progress-wrap"><div class="progress"><span style="width:${pct}%"></span></div><strong>${pct}%</strong></div><p class="small muted">${state.data.resolved_conflicts}/${state.data.conflict_pairs} conflitos resolvidos.</p><div class="grid"><div class="kpi"><strong>${state.data.agreed_pairs}</strong><span>concordâncias</span></div><div class="kpi"><strong>${state.data.conflict_pairs}</strong><span>conflitos</span></div></div><div class="notice" style="margin-top:1rem">As concordâncias serão registradas como <strong>AGREED</strong>. Estes conflitos só serão <strong>RESOLVED</strong> após decisão humana explícita.</div>${state.data.unresolved_conflicts === 0 && !complete ? '<button class="btn primary" id="finalizeBtn" style="width:100%;margin-top:1rem">Encerrar adjudicação</button>' : ''}${complete ? '<div class="notice success" style="margin-top:1rem">Adjudicação encerrada ✓</div>' : ''}</aside>
    </div>`)
  bind()
}

function bind() {
  document.querySelectorAll('.grade').forEach(button => button.addEventListener('click', () => { document.querySelectorAll('.grade').forEach(x => x.classList.remove('selected')); button.classList.add('selected') }))
  document.querySelector('#saveDecision')?.addEventListener('click', save)
  document.querySelector('#prevConflict')?.addEventListener('click', () => { state.index--; render() })
  document.querySelector('#nextConflict')?.addEventListener('click', () => { state.index++; render() })
  document.querySelector('#finalizeBtn')?.addEventListener('click', finalize)
}

async function save() {
  const item = current(); if (!item) return
  const selected = document.querySelector('.grade.selected')
  if (!selected) return alert('Escolha a nota final 0, 1 ou 2.')
  const adjudicatorId = document.querySelector('#adjudicatorId')?.value.trim() || ''
  if (!adjudicatorId) return alert('Identifique o adjudicador humano.')
  state.adjudicatorId = adjudicatorId; localStorage.setItem(ADJUDICATOR_STORAGE_ID, adjudicatorId)
  const payload = { question_id: item.question_id, reference_id: item.reference_id, relevance_grade: Number(selected.dataset.grade), adjudicator_id: adjudicatorId, notes: document.querySelector('#adjudicationNotes')?.value.trim() || '' }
  state.data = await api('/api/validation/adjudication/save', { method:'POST', body: JSON.stringify(payload) })
  const next = state.data.conflicts.findIndex(conflict => !conflict.adjudication)
  state.index = next >= 0 ? next : Math.min(state.index, state.data.conflicts.length - 1)
  render()
}

async function finalize() {
  if (state.data.unresolved_conflicts !== 0) return alert('Ainda existem conflitos sem decisão humana.')
  if (!confirm('Encerrar a adjudicação? Depois disso novas decisões de conflito serão bloqueadas.')) return
  state.data = await api('/api/validation/adjudication/finalize', { method:'POST', body:'{}' })
  render()
}

async function init() {
  try { state.data = await api('/api/validation/adjudication'); render() }
  catch (error) { root.innerHTML = shell(`<section class="card"><h1>Adjudicação indisponível</h1><div class="notice danger">${esc(error.message)}</div><p class="muted">Esta tela só abre no navegador local do coordenador, depois que todos os avaliadores tiverem enviado e travado suas avaliações.</p><a class="btn" href="/validation/">Voltar</a></section>`) }
}

init()
