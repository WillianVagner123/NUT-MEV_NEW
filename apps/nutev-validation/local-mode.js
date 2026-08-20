import Papa from 'https://cdn.jsdelivr.net/npm/papaparse@5.6.0/+esm'

const APP_VERSION = '0.2.0-local'
const DB_NAME = 'nutev-validation-local-v1'
const STORE = 'sessions'
const EXPECTED_QUESTIONS_SHA = '55a0f654e49cb5a9b10249c373df168cac585167a245b828d667c7724fb64589'
const REQUIRED_PACKET_COLUMNS = [
  'question_id', 'pool_item_id', 'assessor_order', 'reference_id', 'title', 'abstract',
  'journal', 'year', 'doi', 'pmid', 'pmcid', 'url', 'assessor_id', 'relevance_grade',
  'reason', 'decision_timestamp', 'blind_to_nutev', 'notes',
]
const PROHIBITED_PACKET_COLUMNS = new Set([
  'reference_score', 'reference_rank', 'taxonomy_primary', 'taxonomy_secondary',
  'taxonomy_groups', 'taxonomy_group_scores', 'system', 'systems', 'system_origin',
  'nutev_score', 'nutev_rank', 'score', 'rank',
])
const QUICK_REASONS = {
  0: ['Fora do escopo da pergunta', 'População/intervenção não aplicável', 'Não responde ao construto de interesse'],
  1: ['Relevante como contexto ou apoio', 'Aplicação parcial à pergunta', 'Útil, mas não é referência central'],
  2: ['Diretamente aplicável à pergunta', 'Referência central para população/intervenção/desfecho', 'Evidência-chave para o construto'],
}

const state = { sessions: [], session: null, index: 0 }
const app = document.querySelector('#app')

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;')
}

function toast(message, type = 'notice') {
  const el = document.createElement('div')
  el.className = `notice ${type}`
  el.textContent = message
  el.style.position = 'fixed'; el.style.right = '1rem'; el.style.bottom = '1rem'; el.style.maxWidth = '430px'; el.style.zIndex = '999'
  document.body.appendChild(el)
  setTimeout(() => el.remove(), 4200)
}

function shell(content) {
  return `
    <div class="shell">
      <header class="topbar">
        <div class="brand"><div class="brand-mark">N</div><div><h1>NutEV Validation</h1><small>modo local cego · ${APP_VERSION}</small></div></div>
        <div class="userbar"><span class="badge">sem servidor</span><button class="btn ghost" id="homeBtn">Início</button></div>
      </header>
      <main>${content}<div class="footer-note">Dados do modo local ficam apenas neste navegador. Não use o mesmo perfil de navegador para os dois assessores.</div></main>
    </div>`
}

function bindHome() {
  document.querySelector('#homeBtn')?.addEventListener('click', () => { state.session = null; renderHome() })
}

function openDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, 1)
    req.onupgradeneeded = () => {
      const db = req.result
      if (!db.objectStoreNames.contains(STORE)) db.createObjectStore(STORE, { keyPath: 'id' })
    }
    req.onsuccess = () => resolve(req.result)
    req.onerror = () => reject(req.error)
  })
}

async function dbGetAll() {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readonly')
    const req = tx.objectStore(STORE).getAll()
    req.onsuccess = () => resolve(req.result || [])
    req.onerror = () => reject(req.error)
  })
}

async function dbPut(value) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).put(value)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

async function dbDelete(id) {
  const db = await openDb()
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE, 'readwrite')
    tx.objectStore(STORE).delete(id)
    tx.oncomplete = () => resolve()
    tx.onerror = () => reject(tx.error)
  })
}

function parseCsvFile(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, {
      header: true, skipEmptyLines: 'greedy', worker: false,
      complete: (result) => result.errors?.length ? reject(new Error(result.errors.slice(0, 3).map((x) => x.message).join('; '))) : resolve(result),
      error: reject,
    })
  })
}

async function sha256File(file) {
  const digest = await crypto.subtle.digest('SHA-256', await file.arrayBuffer())
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

function validatePacket(parsed) {
  const fields = parsed.meta.fields || []
  const missing = REQUIRED_PACKET_COLUMNS.filter((x) => !fields.includes(x))
  if (missing.length) throw new Error(`Packet sem colunas obrigatórias: ${missing.join(', ')}`)
  const leaked = fields.filter((x) => PROHIBITED_PACKET_COLUMNS.has(x))
  if (leaked.length) throw new Error(`Packet contém campos proibidos de cegamento: ${leaked.join(', ')}`)
  if (!parsed.data.length) throw new Error('Packet vazio.')
  for (const [i, row] of parsed.data.entries()) {
    if (!row.question_id || !row.pool_item_id || !row.reference_id || !row.title || !row.assessor_id) throw new Error(`Identidade incompleta no packet, linha ${i + 2}`)
    if (String(row.blind_to_nutev).trim().toLowerCase() !== 'true') throw new Error(`Packet não inicia cego na linha ${i + 2}`)
    if (String(row.relevance_grade || '').trim() || String(row.reason || '').trim() || String(row.decision_timestamp || '').trim()) throw new Error(`Packet já contém decisão humana na linha ${i + 2}`)
  }
  const assessorIds = new Set(parsed.data.map((x) => x.assessor_id))
  if (assessorIds.size !== 1) throw new Error('O modo local aceita exatamente um assessor por packet.')
}

function questionContext(row) {
  return {
    sampling_stratum: row.sampling_stratum || '', population_context: row.population_context || '',
    intervention_exposure: row.intervention_exposure || '', comparator: row.comparator || '',
    outcome_construct: row.outcome_construct || '', time_window: row.time_window || '',
    languages: row.languages || '', document_types: row.document_types || '',
  }
}

async function importSession() {
  const qFile = document.querySelector('#questionsFile').files[0]
  const packetFile = document.querySelector('#packetFile').files[0]
  const manifestFile = document.querySelector('#manifestFile').files[0]
  if (!qFile || !packetFile || !manifestFile) return toast('Selecione QUESTIONS.csv, o manifest e um packet de assessor.', 'warn')
  try {
    toast('Validando arquivos localmente...')
    const [qParsed, packetParsed, qSha, packetSha, manifestText] = await Promise.all([
      parseCsvFile(qFile), parseCsvFile(packetFile), sha256File(qFile), sha256File(packetFile), manifestFile.text(),
    ])
    validatePacket(packetParsed)
    if (qSha !== EXPECTED_QUESTIONS_SHA) throw new Error(`QUESTIONS.csv não corresponde ao freeze atual. SHA recebido: ${qSha}`)
    let manifest
    try { manifest = JSON.parse(manifestText) } catch { throw new Error('Manifest JSON inválido.') }
    if (manifest.label_blind !== true || manifest.independent_order_per_assessor !== true) throw new Error('Manifest não confirma label_blind + ordem independente.')
    const assessorId = packetParsed.data[0].assessor_id
    const output = (manifest.outputs || []).find((x) => x.assessor_id === assessorId)
    if (!output?.sha256 || output.sha256 !== packetSha) throw new Error('SHA-256 do packet não confere com o manifest.')
    if (Number(manifest.pool_rows) !== packetParsed.data.length) throw new Error('Contagem do packet diverge de pool_rows no manifest.')
    const qFields = qParsed.meta.fields || []
    for (const name of ['question_id', 'question_text', 'split']) if (!qFields.includes(name)) throw new Error(`QUESTIONS.csv sem ${name}.`)
    const validationQuestions = qParsed.data.filter((x) => x.split === 'validation')
    const qIds = new Set(validationQuestions.map((x) => x.question_id))
    if (packetParsed.data.some((x) => !qIds.has(x.question_id))) throw new Error('Packet contém pergunta fora do split validation congelado.')
    const questions = Object.fromEntries(validationQuestions.map((q) => [q.question_id, { question_text: q.question_text, eligibility_context: questionContext(q) }]))
    const now = new Date().toISOString()
    const session = {
      id: `local:${packetSha}`,
      assessorId,
      packetSha,
      questionsSha: qSha,
      manifestDigest: await sha256Text(manifestText),
      importedAt: now,
      updatedAt: now,
      rows: packetParsed.data.map((row) => ({ ...row, assessor_order: Number(row.assessor_order), relevance_grade: null, reason: '', decision_timestamp: '', blind_to_nutev: true, review_later: false, _draft: null })),
      questions,
    }
    await dbPut(session)
    state.session = session
    state.index = 0
    toast(`Packet validado: ${session.rows.length} itens para ${assessorId}.`, 'success')
    renderReview()
  } catch (error) {
    toast(`Import bloqueado: ${error.message}`, 'danger')
  }
}

async function sha256Text(text) {
  const bytes = new TextEncoder().encode(text)
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

function stats(session) {
  const total = session.rows.length
  const completed = session.rows.filter((x) => x.relevance_grade !== null).length
  const flagged = session.rows.filter((x) => x.review_later).length
  return { total, completed, flagged, pct: total ? Math.round(completed * 100 / total) : 0 }
}

function linkFor(row) {
  if (row.doi) return row.doi.startsWith('http') ? row.doi : `https://doi.org/${row.doi.replace(/^doi:/i, '')}`
  if (row.pmid) return `https://pubmed.ncbi.nlm.nih.gov/${encodeURIComponent(row.pmid)}/`
  return row.url || ''
}

function draftFor(row) {
  if (row._draft) return row._draft
  return {
    grade: row.relevance_grade,
    reason: row.reason || '',
    reviewLater: Boolean(row.review_later),
    blind: row.blind_to_nutev !== false,
  }
}

async function persistDraft(row, draft) {
  row._draft = { ...draft }
  state.session.updatedAt = new Date().toISOString()
  await dbPut(state.session)
}

function renderReview() {
  const session = state.session
  const row = session.rows[state.index]
  const q = session.questions[row.question_id] || {}
  const s = stats(session)
  const draft = draftFor(row)
  const href = linkFor(row)
  app.innerHTML = shell(`
    <div class="review-layout">
      <section class="card reference-card">
        <div class="question-box"><strong>${escapeHtml(row.question_id)}</strong><div>${escapeHtml(q.question_text || 'Pergunta não encontrada')}</div><details><summary>Contexto de elegibilidade</summary><pre class="eligibility-pre">${escapeHtml(JSON.stringify(q.eligibility_context || {}, null, 2))}</pre></details></div>
        <div class="muted small">Item ${state.index + 1} de ${session.rows.length} · assessor ${escapeHtml(session.assessorId)}</div>
        <h2 class="ref-title">${escapeHtml(row.title)}</h2>
        <div class="meta"><span>${escapeHtml(row.journal || '—')}</span><span>${escapeHtml(row.year || '—')}</span><span>${escapeHtml(row.reference_id)}</span></div>
        ${href ? `<p><a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">Abrir fonte ↗</a></p>` : ''}
        <h3>Resumo</h3><div class="abstract">${escapeHtml(row.abstract || 'Abstract indisponível.')}</div>
        <h3 style="margin-top:1rem">Qual a relevância para a pergunta?</h3>
        <div class="grade-grid">
          <button class="grade ${draft.grade === 0 ? 'selected' : ''}" data-grade="0"><strong>0</strong><br>Irrelevante</button>
          <button class="grade ${draft.grade === 1 ? 'selected' : ''}" data-grade="1"><strong>1</strong><br>Relevante / periférica</button>
          <button class="grade ${draft.grade === 2 ? 'selected' : ''}" data-grade="2"><strong>2</strong><br>Diretamente relevante / chave</button>
        </div>
        <div class="form-row"><label>Justificativa</label><textarea id="reasonInput" placeholder="Justificativa curta e auditável...">${escapeHtml(draft.reason)}</textarea><div class="quick-reasons" id="quickReasons"></div></div>
        <div class="form-row"><label><input id="reviewLater" type="checkbox" style="width:auto" ${draft.reviewLater ? 'checked' : ''}> Revisar depois</label></div>
        <div class="form-row"><label><input id="blindCheck" type="checkbox" style="width:auto" ${draft.blind ? 'checked' : ''}> Permaneci cego ao score/rank/taxonomia/origem NutEV e à decisão do outro assessor</label></div>
        <div class="actions"><button class="btn" id="prevBtn">← Anterior</button><button class="btn primary" id="saveBtn">Salvar e próxima →</button><button class="btn" id="pendingBtn">Próxima pendente</button></div>
        <p class="help">Autosave de rascunho: alterações são salvas neste navegador. Atalhos: 0/1/2, S, J/K.</p>
      </section>
      <aside class="card">
        <h3>Progresso</h3>
        <div class="progress-wrap"><div class="progress"><span style="width:${s.pct}%"></span></div><strong>${s.pct}%</strong></div>
        <div class="sidebar-list" style="margin-top:1rem">
          <div class="kpi"><span class="muted small">Concluídos</span><strong>${s.completed} / ${s.total}</strong></div>
          <div class="kpi"><span class="muted small">Revisar depois</span><strong>${s.flagged}</strong></div>
          <div class="kpi"><span class="muted small">Packet SHA</span><code class="hash">${escapeHtml(session.packetSha.slice(0, 16))}…</code></div>
        </div>
        <div class="actions vertical-actions" style="margin-top:1rem"><button class="btn" id="exportBtn">Exportar CSV atual</button><button class="btn" id="backupBtn">Backup local JSON</button></div>
        <div class="notice warn" style="margin-top:1rem"><strong>Importante:</strong> não abra o packet do outro assessor neste mesmo perfil de navegador.</div>
      </aside>
    </div>`)
  bindHome()
  bindReviewEvents(row, draft)
}

function bindReviewEvents(row, draft) {
  const reason = document.querySelector('#reasonInput')
  const quick = document.querySelector('#quickReasons')
  let timer = null
  const scheduleDraftSave = () => {
    clearTimeout(timer)
    timer = setTimeout(() => persistDraft(row, draft), 180)
  }
  function paintQuick() {
    quick.innerHTML = [0,1,2].includes(draft.grade) ? QUICK_REASONS[draft.grade].map((x) => `<button class="btn" type="button" data-reason="${escapeHtml(x)}">${escapeHtml(x)}</button>`).join('') : ''
    quick.querySelectorAll('[data-reason]').forEach((b) => b.addEventListener('click', () => { draft.reason = b.dataset.reason; reason.value = draft.reason; scheduleDraftSave() }))
  }
  paintQuick()
  document.querySelectorAll('.grade').forEach((button) => button.addEventListener('click', () => {
    draft.grade = Number(button.dataset.grade)
    document.querySelectorAll('.grade').forEach((x) => x.classList.toggle('selected', x === button))
    paintQuick(); scheduleDraftSave()
  }))
  reason.addEventListener('input', () => { draft.reason = reason.value; scheduleDraftSave() })
  document.querySelector('#reviewLater').addEventListener('change', (e) => { draft.reviewLater = e.target.checked; scheduleDraftSave() })
  document.querySelector('#blindCheck').addEventListener('change', (e) => { draft.blind = e.target.checked; scheduleDraftSave() })
  document.querySelector('#prevBtn').addEventListener('click', () => move(-1))
  document.querySelector('#saveBtn').addEventListener('click', () => finalizeRow(row, draft))
  document.querySelector('#pendingBtn').addEventListener('click', nextPending)
  document.querySelector('#exportBtn').addEventListener('click', exportCurrent)
  document.querySelector('#backupBtn').addEventListener('click', exportBackup)
  window.onkeydown = (event) => {
    if (event.target.matches('textarea,input,select')) return
    if (['0','1','2'].includes(event.key)) { event.preventDefault(); document.querySelector(`.grade[data-grade="${event.key}"]`)?.click() }
    else if (event.key.toLowerCase() === 's') { event.preventDefault(); finalizeRow(row, draft) }
    else if (event.key.toLowerCase() === 'j') { event.preventDefault(); move(1) }
    else if (event.key.toLowerCase() === 'k') { event.preventDefault(); move(-1) }
  }
}

async function finalizeRow(row, draft) {
  if (![0,1,2].includes(draft.grade)) return toast('Escolha 0, 1 ou 2.', 'warn')
  if (!draft.reason.trim()) return toast('A justificativa é obrigatória.', 'warn')
  row.relevance_grade = draft.grade
  row.reason = draft.reason.trim()
  row.review_later = Boolean(draft.reviewLater)
  row.blind_to_nutev = Boolean(draft.blind)
  row.decision_timestamp = new Date().toISOString()
  row._draft = null
  state.session.updatedAt = new Date().toISOString()
  await dbPut(state.session)
  const next = state.session.rows.findIndex((x, i) => i > state.index && x.relevance_grade === null)
  if (next >= 0) state.index = next
  else if (state.index < state.session.rows.length - 1) state.index += 1
  renderReview()
}

function move(delta) {
  state.index = Math.min(Math.max(state.index + delta, 0), state.session.rows.length - 1)
  renderReview()
}

function nextPending() {
  const rows = state.session.rows
  for (let offset = 1; offset <= rows.length; offset += 1) {
    const idx = (state.index + offset) % rows.length
    if (rows[idx].relevance_grade === null || rows[idx].review_later) { state.index = idx; renderReview(); return }
  }
  toast('Não há itens pendentes.', 'success')
}

function download(filename, blob) {
  const url = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = url; anchor.download = filename; anchor.click()
  URL.revokeObjectURL(url)
}

function exportCurrent() {
  const rows = state.session.rows.map((row) => Object.fromEntries(REQUIRED_PACKET_COLUMNS.map((field) => [field, field === 'blind_to_nutev' ? String(Boolean(row[field])).toLowerCase() : (row[field] ?? '')])))
  const csv = Papa.unparse(rows, { columns: REQUIRED_PACKET_COLUMNS, newline: '\r\n' })
  download(`ASSESSOR_${safeName(state.session.assessorId)}_completed.csv`, new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' }))
}

function exportBackup() {
  download(`ASSESSOR_${safeName(state.session.assessorId)}_local_backup.json`, new Blob([JSON.stringify(state.session, null, 2)], { type: 'application/json' }))
}

function safeName(value) { return String(value || 'assessor').replace(/[^A-Za-z0-9_.-]+/g, '_') }

async function openSession(id) {
  state.sessions = await dbGetAll()
  state.session = state.sessions.find((x) => x.id === id)
  if (!state.session) return renderHome()
  const firstPending = state.session.rows.findIndex((x) => x.relevance_grade === null)
  state.index = firstPending >= 0 ? firstPending : 0
  renderReview()
}

async function deleteSession(id) {
  if (!confirm('Apagar este progresso local deste navegador? Faça um backup antes se precisar preservar as decisões.')) return
  await dbDelete(id)
  toast('Sessão local apagada.', 'success')
  renderHome()
}

async function renderHome() {
  window.onkeydown = null
  state.sessions = (await dbGetAll()).sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
  app.innerHTML = shell(`
    <div class="grid two" style="align-items:start">
      <section class="card">
        <span class="badge">novo packet</span>
        <h2 style="margin-top:.8rem">Carregar avaliação cega</h2>
        <p>Use somente o packet do assessor deste navegador. Os arquivos são lidos localmente e não são enviados a servidor.</p>
        <div class="form-row"><label>QUESTIONS.csv congelado</label><input id="questionsFile" type="file" accept=".csv,text/csv"></div>
        <div class="form-row"><label>VALIDATION_ASSESSOR_PACKETS_MANIFEST.json</label><input id="manifestFile" type="file" accept=".json,application/json"></div>
        <div class="form-row"><label>ASSESSOR_*.csv</label><input id="packetFile" type="file" accept=".csv,text/csv"></div>
        <button class="btn primary" id="importBtn">Validar e iniciar</button>
        <p class="help">O modo local exige o SHA do question-set congelado e confere o SHA do packet contra o manifest.</p>
      </section>
      <section class="card">
        <h2>Avaliações salvas neste navegador</h2>
        ${state.sessions.length ? state.sessions.map((session) => sessionCard(session)).join('') : '<p class="muted">Nenhuma sessão local ainda.</p>'}
      </section>
    </div>
    <div class="notice warn" style="margin-top:1rem"><strong>Limitação:</strong> este modo não sincroniza dispositivos nem impede que alguém com acesso físico ao navegador veja os dados locais. Para o estudo definitivo, use perfis/dispositivos separados por assessor e preserve os arquivos exportados.</div>`)
  bindHome()
  document.querySelector('#importBtn').addEventListener('click', importSession)
  document.querySelectorAll('[data-open]').forEach((b) => b.addEventListener('click', () => openSession(b.dataset.open)))
  document.querySelectorAll('[data-delete]').forEach((b) => b.addEventListener('click', () => deleteSession(b.dataset.delete)))
}

function sessionCard(session) {
  const s = stats(session)
  return `<div class="notice session-card"><div class="actions" style="justify-content:space-between"><div><strong>${escapeHtml(session.assessorId)}</strong><div class="muted small">${s.completed}/${s.total} · ${s.pct}% · atualizado ${escapeHtml(new Date(session.updatedAt).toLocaleString('pt-BR'))}</div></div><div class="actions"><button class="btn primary" data-open="${escapeHtml(session.id)}">Continuar</button><button class="btn danger" data-delete="${escapeHtml(session.id)}">Apagar</button></div></div></div>`
}

renderHome().catch((error) => {
  app.innerHTML = shell(`<div class="card"><h2>Falha no modo local</h2><div class="notice danger">${escapeHtml(error.message)}</div></div>`)
  bindHome()
})
