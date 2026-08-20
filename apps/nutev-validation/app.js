import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.112.3/+esm'
import Papa from 'https://cdn.jsdelivr.net/npm/papaparse@5.6.0/+esm'

const APP_VERSION = '0.1.0-mvp'
const CONFIG_KEY = 'nutev_validation_supabase_config_v1'
const EXPECTED_RUNTIME_SHA = '6aa7a5fe6009776e611ca3e1506486606b05f4f6'
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

const state = {
  supabase: null,
  session: null,
  profile: null,
  view: null,
  round: null,
  assignments: [],
  references: new Map(),
  questions: new Map(),
  index: 0,
  drafts: new Map(),
  adjudication: null,
}

const $app = document.querySelector('#app')

function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;').replaceAll("'", '&#039;')
}

function formatDate(value) {
  if (!value) return '—'
  try { return new Date(value).toLocaleString('pt-BR') } catch { return value }
}

function toast(message, type = 'notice') {
  const el = document.createElement('div')
  el.className = `notice ${type}`
  el.textContent = message
  el.style.position = 'fixed'
  el.style.right = '1rem'
  el.style.bottom = '1rem'
  el.style.maxWidth = '420px'
  el.style.zIndex = '999'
  document.body.appendChild(el)
  setTimeout(() => el.remove(), 4200)
}

function getConfig() {
  try { return JSON.parse(localStorage.getItem(CONFIG_KEY) || 'null') } catch { return null }
}

function saveConfig(config) {
  localStorage.setItem(CONFIG_KEY, JSON.stringify(config))
}

function clearConfig() {
  localStorage.removeItem(CONFIG_KEY)
  location.reload()
}

function initSupabase() {
  const config = getConfig()
  if (!config?.url || !config?.publishableKey) return false
  state.supabase = createClient(config.url, config.publishableKey, {
    auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: true },
  })
  return true
}

function shell(content) {
  const user = state.session?.user
  const role = state.profile?.role
  return `
    <div class="shell">
      <header class="topbar">
        <div class="brand"><div class="brand-mark">N</div><div><h1>NutEV Validation</h1><small>blind relevance assessment · ${APP_VERSION}</small></div></div>
        <div class="userbar">
          ${user ? `<span class="badge">${escapeHtml(user.email || 'authenticated')}</span>` : ''}
          ${role ? `<span class="badge">role: ${escapeHtml(role)}</span>` : ''}
          ${user ? `<button class="btn ghost" id="logoutBtn">Sair</button>` : ''}
        </div>
      </header>
      <main>${content}<div class="footer-note">NutEV Validation mantém score, rank, taxonomia e origem do sistema fora da interface de julgamento humano.</div></main>
    </div>`
}

function renderConfig() {
  $app.innerHTML = shell(`
    <div class="card" style="max-width:720px;margin:3rem auto">
      <h2>Configurar backend seguro</h2>
      <p>Informe o URL do projeto Supabase e a <strong>Publishable key</strong>. Essa chave é própria para clientes públicos; nunca use <code>service_role</code> ou uma secret key no navegador.</p>
      <form id="configForm">
        <div class="form-row"><label>Supabase URL</label><input name="url" type="url" placeholder="https://xxxx.supabase.co" required></div>
        <div class="form-row"><label>Publishable key</label><input name="key" type="text" placeholder="sb_publishable_..." required></div>
        <button class="btn primary">Salvar configuração neste navegador</button>
      </form>
      <p class="help">A configuração fica somente no localStorage deste navegador. O banco continua protegido por RLS.</p>
    </div>`)
  document.querySelector('#configForm').addEventListener('submit', (event) => {
    event.preventDefault()
    const fd = new FormData(event.currentTarget)
    const url = String(fd.get('url') || '').trim().replace(/\/$/, '')
    const publishableKey = String(fd.get('key') || '').trim()
    if (!url.startsWith('https://') || !publishableKey) return toast('Configuração inválida.', 'danger')
    saveConfig({ url, publishableKey })
    location.reload()
  })
}

function renderLogin() {
  $app.innerHTML = shell(`
    <div class="grid two" style="align-items:start;margin-top:2rem">
      <section class="card">
        <h2>Acesso do avaliador</h2>
        <p>Entre por magic link. Contas novas não são criadas automaticamente: o administrador precisa cadastrar o avaliador antes.</p>
        <form id="loginForm">
          <div class="form-row"><label>E-mail</label><input name="email" type="email" autocomplete="email" required></div>
          <button class="btn primary" id="loginBtn">Enviar magic link</button>
        </form>
        <div class="actions" style="margin-top:1rem"><button class="btn ghost" id="changeConfigBtn">Trocar backend</button></div>
      </section>
      <aside class="card">
        <h3>Blindagem metodológica</h3>
        <ul>
          <li>cada assessor vê somente suas próprias atribuições;</li>
          <li>nenhum score/rank/taxonomia/origem NutEV é armazenado nas referências do app;</li>
          <li>decisões dos outros assessores ficam inacessíveis durante <code>assessment</code>;</li>
          <li>o MVP aceita apenas o split <code>validation</code>; external-test continua fora daqui.</li>
        </ul>
      </aside>
    </div>`)
  document.querySelector('#changeConfigBtn').addEventListener('click', clearConfig)
  document.querySelector('#loginForm').addEventListener('submit', async (event) => {
    event.preventDefault()
    const button = document.querySelector('#loginBtn')
    button.disabled = true
    const email = String(new FormData(event.currentTarget).get('email') || '').trim()
    const redirectTo = `${location.origin}${location.pathname}`
    const { error } = await state.supabase.auth.signInWithOtp({
      email,
      options: { shouldCreateUser: false, emailRedirectTo: redirectTo },
    })
    button.disabled = false
    if (error) return toast(`Falha no login: ${error.message}`, 'danger')
    toast('Magic link enviado. Verifique seu e-mail.', 'success')
  })
}

async function loadProfile() {
  const userId = state.session?.user?.id
  if (!userId) return null
  const { data, error } = await state.supabase.from('validation_profiles').select('id,display_name,role').eq('id', userId).single()
  if (error) throw error
  state.profile = data
  return data
}

async function refreshSession() {
  const { data, error } = await state.supabase.auth.getSession()
  if (error) throw error
  state.session = data.session
}

async function logout() {
  await state.supabase.auth.signOut()
  state.session = null
  state.profile = null
  renderLogin()
}

function bindShell() {
  document.querySelector('#logoutBtn')?.addEventListener('click', logout)
}

async function fetchAccessibleRounds() {
  const { data, error } = await state.supabase.from('validation_rounds').select('*').order('created_at', { ascending: false })
  if (error) throw error
  return data || []
}

async function openReviewerRound(round) {
  state.round = round
  const uid = state.session.user.id
  const [{ data: assignments, error: aErr }, { data: references, error: rErr }, { data: questions, error: qErr }] = await Promise.all([
    state.supabase.from('validation_assignments').select('*').eq('round_id', round.id).eq('assessor_user_id', uid).order('assessor_order'),
    state.supabase.from('validation_references').select('*').eq('round_id', round.id),
    state.supabase.from('validation_questions').select('*').eq('round_id', round.id),
  ])
  if (aErr || rErr || qErr) throw (aErr || rErr || qErr)
  state.assignments = assignments || []
  state.references = new Map((references || []).map((row) => [row.pool_item_id, row]))
  state.questions = new Map((questions || []).map((row) => [row.question_id, row]))
  state.index = Math.max(0, state.assignments.findIndex((x) => x.relevance_grade === null))
  if (state.index < 0) state.index = 0
  renderReviewer()
}

function reviewStats() {
  const total = state.assignments.length
  const completed = state.assignments.filter((x) => x.relevance_grade !== null).length
  const flagged = state.assignments.filter((x) => x.review_later).length
  return { total, completed, flagged, pct: total ? Math.round((completed / total) * 100) : 0 }
}

function currentDraft() {
  const item = state.assignments[state.index]
  if (!item) return null
  if (!state.drafts.has(item.id)) {
    state.drafts.set(item.id, {
      grade: item.relevance_grade,
      reason: item.reason || '',
      reviewLater: Boolean(item.review_later),
      blind: item.blind_to_nutev !== false,
      notes: item.notes || '',
    })
  }
  return state.drafts.get(item.id)
}

function renderReviewer() {
  const roundsHtml = !state.round ? '' : ''
  const item = state.assignments[state.index]
  if (!item) {
    $app.innerHTML = shell(`<div class="card"><h2>Nenhuma atribuição disponível</h2><p>O administrador ainda não atribuiu itens a este usuário.</p><button class="btn" id="backRounds">Atualizar</button></div>`)
    bindShell()
    document.querySelector('#backRounds').addEventListener('click', reviewerHome)
    return
  }
  const ref = state.references.get(item.pool_item_id) || {}
  const q = state.questions.get(item.question_id) || {}
  const draft = currentDraft()
  const stats = reviewStats()
  const externalLink = ref.doi || ref.pmid || ref.url
  const linkHref = ref.doi?.startsWith('http') ? ref.doi : (ref.doi ? `https://doi.org/${ref.doi.replace(/^doi:/i,'')}` : ref.url)
  $app.innerHTML = shell(`
    <div class="review-layout">
      <section class="card reference-card">
        <div class="question-box"><strong>${escapeHtml(item.question_id)}</strong><div>${escapeHtml(q.question_text || 'Pergunta não carregada')}</div>${q.eligibility_context ? `<details><summary>Contexto de elegibilidade</summary><pre style="white-space:pre-wrap">${escapeHtml(JSON.stringify(q.eligibility_context, null, 2))}</pre></details>` : ''}</div>
        <div class="muted small">Referência ${state.index + 1} de ${state.assignments.length}</div>
        <h2 class="ref-title">${escapeHtml(ref.title || '(sem título)')}</h2>
        <div class="meta"><span>${escapeHtml(ref.journal || '—')}</span><span>${escapeHtml(ref.year || '—')}</span><span>${escapeHtml(ref.reference_id || '')}</span></div>
        ${externalLink ? `<p><a href="${escapeHtml(linkHref || ref.url || '#')}" target="_blank" rel="noopener noreferrer">Abrir DOI / fonte ↗</a></p>` : ''}
        <h3>Resumo</h3><div class="abstract">${escapeHtml(ref.abstract || 'Abstract indisponível.')}</div>
        <h3 style="margin-top:1rem">Relevância para a pergunta</h3>
        <div class="grade-grid">
          <button class="grade ${draft.grade === 0 ? 'selected' : ''}" data-grade="0"><strong>0</strong><br>Irrelevante</button>
          <button class="grade ${draft.grade === 1 ? 'selected' : ''}" data-grade="1"><strong>1</strong><br>Relevante / periférica</button>
          <button class="grade ${draft.grade === 2 ? 'selected' : ''}" data-grade="2"><strong>2</strong><br>Diretamente relevante / chave</button>
        </div>
        <div class="form-row"><label>Justificativa</label><textarea id="reasonInput" placeholder="Justificativa curta e auditável...">${escapeHtml(draft.reason)}</textarea><div class="quick-reasons" id="quickReasons"></div></div>
        <div class="form-row"><label><input id="reviewLater" type="checkbox" style="width:auto" ${draft.reviewLater ? 'checked' : ''}> Revisar este item depois</label></div>
        <div class="form-row"><label><input id="blindCheck" type="checkbox" style="width:auto" ${draft.blind ? 'checked' : ''}> Permaneci cego ao score/rank/taxonomia/origem NutEV e à decisão do outro avaliador</label><div class="help">Se a cegueira foi quebrada, desmarque. O benchmark-grade posterior deve rejeitar essa evidência.</div></div>
        <div class="actions"><button class="btn" id="prevBtn">← Anterior</button><button class="btn primary" id="saveNextBtn">Salvar e próxima →</button><button class="btn" id="nextPendingBtn">Próxima pendente</button></div>
        <p class="help">Atalhos: 0/1/2 = nota · S = salvar/próxima · J/K = próxima/anterior.</p>
      </section>
      <aside class="card">
        <h3>Progresso</h3>
        <div class="progress-wrap"><div class="progress"><span style="width:${stats.pct}%"></span></div><strong>${stats.pct}%</strong></div>
        <div class="sidebar-list" style="margin-top:1rem"><div class="kpi"><span class="muted small">Concluídos</span><strong>${stats.completed} / ${stats.total}</strong></div><div class="kpi"><span class="muted small">Revisar depois</span><strong>${stats.flagged}</strong></div><div class="kpi"><span class="muted small">Round</span><strong style="font-size:1rem">${escapeHtml(state.round.name)}</strong><span class="muted small">${escapeHtml(state.round.status)}</span></div></div>
        <div class="actions" style="margin-top:1rem"><button class="btn" id="roundsBtn">Trocar round</button></div>
      </aside>
    </div>${roundsHtml}`)
  bindShell()
  bindReviewerEvents()
}

function bindReviewerEvents() {
  const draft = currentDraft()
  const reason = document.querySelector('#reasonInput')
  const quick = document.querySelector('#quickReasons')
  function paintQuickReasons() {
    quick.innerHTML = draft.grade === null || draft.grade === undefined ? '' : QUICK_REASONS[draft.grade].map((x) => `<button type="button" class="btn" data-reason="${escapeHtml(x)}">${escapeHtml(x)}</button>`).join('')
    quick.querySelectorAll('[data-reason]').forEach((b) => b.addEventListener('click', () => { reason.value = b.dataset.reason; draft.reason = b.dataset.reason }))
  }
  paintQuickReasons()
  document.querySelectorAll('.grade').forEach((button) => button.addEventListener('click', () => {
    draft.grade = Number(button.dataset.grade)
    document.querySelectorAll('.grade').forEach((x) => x.classList.toggle('selected', x === button))
    paintQuickReasons()
  }))
  reason.addEventListener('input', () => { draft.reason = reason.value })
  document.querySelector('#reviewLater').addEventListener('change', (e) => { draft.reviewLater = e.target.checked })
  document.querySelector('#blindCheck').addEventListener('change', (e) => { draft.blind = e.target.checked })
  document.querySelector('#prevBtn').addEventListener('click', () => moveReviewer(-1))
  document.querySelector('#saveNextBtn').addEventListener('click', saveAndNext)
  document.querySelector('#nextPendingBtn').addEventListener('click', nextPending)
  document.querySelector('#roundsBtn').addEventListener('click', reviewerHome)
  window.onkeydown = (event) => {
    if (event.target.matches('textarea,input,select')) return
    if (['0','1','2'].includes(event.key)) {
      event.preventDefault(); document.querySelector(`.grade[data-grade="${event.key}"]`)?.click()
    } else if (event.key.toLowerCase() === 's') { event.preventDefault(); saveAndNext() }
    else if (event.key.toLowerCase() === 'j') { event.preventDefault(); moveReviewer(1) }
    else if (event.key.toLowerCase() === 'k') { event.preventDefault(); moveReviewer(-1) }
  }
}

function moveReviewer(delta) {
  const next = Math.min(Math.max(state.index + delta, 0), state.assignments.length - 1)
  state.index = next
  renderReviewer()
}

function nextPending() {
  const start = state.index
  for (let i = 1; i <= state.assignments.length; i += 1) {
    const idx = (start + i) % state.assignments.length
    if (state.assignments[idx].relevance_grade === null || state.assignments[idx].review_later) {
      state.index = idx; renderReviewer(); return
    }
  }
  toast('Não há itens pendentes.', 'success')
}

async function saveAndNext() {
  const item = state.assignments[state.index]
  const draft = currentDraft()
  if (![0,1,2].includes(draft.grade)) return toast('Escolha uma nota 0, 1 ou 2.', 'warn')
  if (!draft.reason.trim()) return toast('A justificativa é obrigatória.', 'warn')
  const decisionTimestamp = new Date().toISOString()
  const { data, error } = await state.supabase.from('validation_assignments').update({
    relevance_grade: draft.grade,
    reason: draft.reason.trim(),
    decision_timestamp: decisionTimestamp,
    blind_to_nutev: Boolean(draft.blind),
    review_later: Boolean(draft.reviewLater),
    notes: draft.notes || null,
  }).eq('id', item.id).select().single()
  if (error) return toast(`Falha ao salvar: ${error.message}`, 'danger')
  Object.assign(item, data)
  state.drafts.delete(item.id)
  const next = state.assignments.findIndex((x, idx) => idx > state.index && x.relevance_grade === null)
  if (next >= 0) state.index = next
  else if (state.index < state.assignments.length - 1) state.index += 1
  renderReviewer()
}

async function reviewerHome() {
  window.onkeydown = null
  const rounds = await fetchAccessibleRounds()
  $app.innerHTML = shell(`<div class="card"><h2>Seus rounds de avaliação</h2>${rounds.length ? `<div class="grid two">${rounds.map((r) => `<button class="btn roundChoice" data-id="${r.id}" style="text-align:left"><strong>${escapeHtml(r.name)}</strong><br><span class="muted small">${escapeHtml(r.status)} · ${escapeHtml(r.split)}</span></button>`).join('')}</div>` : '<p>Nenhum round atribuído.</p>'}</div>`)
  bindShell()
  document.querySelectorAll('.roundChoice').forEach((b) => b.addEventListener('click', () => openReviewerRound(rounds.find((r) => r.id === b.dataset.id))))
}

async function adminHome() {
  const [rounds, profiles] = await Promise.all([
    fetchAccessibleRounds(),
    state.supabase.from('validation_profiles').select('id,display_name,role,created_at').order('created_at').then(({ data, error }) => { if (error) throw error; return data || [] }),
  ])
  const progressByRound = new Map()
  for (const round of rounds) {
    const { data } = await state.supabase.from('validation_progress').select('*').eq('round_id', round.id)
    progressByRound.set(round.id, data || [])
  }
  $app.innerHTML = shell(`
    <div class="tabs"><button class="tab active">Admin</button><button class="tab" id="refreshAdmin">Atualizar</button></div>
    <div class="grid two">
      <section class="card">
        <h2>Novo round de validation</h2>
        <form id="roundForm">
          <div class="form-row"><label>Nome</label><input name="name" value="NutEV validation round 01" required></div>
          <div class="form-row"><label>Candidate runtime SHA</label><input name="runtime" value="${EXPECTED_RUNTIME_SHA}" required></div>
          <div class="form-row"><label>Question-set SHA-256</label><input name="questions" value="${EXPECTED_QUESTIONS_SHA}" required></div>
          <button class="btn primary">Criar em estado draft</button>
        </form>
      </section>
      <aside class="card">
        <h2>Usuários</h2>
        <div class="table-wrap"><table><thead><tr><th>Nome</th><th>Role</th><th>User ID</th></tr></thead><tbody>${profiles.map((p) => `<tr><td>${escapeHtml(p.display_name || '—')}</td><td>${escapeHtml(p.role)}</td><td><code>${escapeHtml(p.id)}</code></td></tr>`).join('')}</tbody></table></div>
        <p class="help">Novos usuários entram como <code>assessor</code>. Promova admin/adjudicator via SQL Editor conforme README.</p>
      </aside>
    </div>
    <section class="card"><h2>Rounds</h2>${rounds.length ? rounds.map((r) => roundAdminCard(r, progressByRound.get(r.id), profiles)).join('') : '<p>Nenhum round.</p>'}</section>`)
  bindShell()
  document.querySelector('#refreshAdmin').addEventListener('click', adminHome)
  document.querySelector('#roundForm').addEventListener('submit', createRound)
  bindAdminRoundEvents(rounds, profiles)
}

function roundAdminCard(round, progress, profiles) {
  const assessors = profiles.filter((p) => p.role === 'assessor')
  return `<div class="notice" style="margin-bottom:1rem">
    <div class="actions" style="justify-content:space-between"><div><strong>${escapeHtml(round.name)}</strong><div class="muted small">${escapeHtml(round.status)} · ${escapeHtml(round.id)}</div></div><div class="actions">${round.status === 'draft' ? `<button class="btn primary importBtn" data-id="${round.id}">Importar packets</button>` : ''}${round.status === 'assessment' ? `<button class="btn primary adjudicateBtn" data-id="${round.id}">Fechar avaliação → adjudicação</button>` : ''}${round.status === 'locked' ? `<button class="btn exportBtn" data-id="${round.id}">Exportar final</button>` : ''}</div></div>
    <div class="grid two" style="margin-top:.8rem"><div>${(progress || []).map((p) => `<div class="kpi"><span class="small muted">${escapeHtml(p.assessor_id)}</span><strong>${p.completed_items} / ${p.total_items}</strong><span class="small muted">flagged ${p.flagged_items}</span></div>`).join('') || '<span class="muted">Sem assignments.</span>'}</div><div><span class="small muted">runtime</span><br><code>${escapeHtml(round.candidate_runtime_sha)}</code><br><span class="small muted">questions</span><br><code>${escapeHtml(round.questions_sha256)}</code></div></div>
    ${round.status === 'draft' ? `<div id="import-${round.id}" class="hidden" style="margin-top:1rem"><div class="grid two"><div><label>Assessor A</label><select id="assessorA-${round.id}"><option value="">Selecione...</option>${assessors.map((p) => `<option value="${p.id}">${escapeHtml(p.display_name || p.id)}</option>`).join('')}</select></div><div><label>Assessor B</label><select id="assessorB-${round.id}"><option value="">Selecione...</option>${assessors.map((p) => `<option value="${p.id}">${escapeHtml(p.display_name || p.id)}</option>`).join('')}</select></div></div><div class="grid two" style="margin-top:.8rem"><div><label>QUESTIONS.csv</label><input id="questionsFile-${round.id}" type="file" accept=".csv,text/csv"></div><div><label>Packets manifest JSON</label><input id="packetManifest-${round.id}" type="file" accept=".json,application/json"></div><div><label>ASSESSOR A.csv</label><input id="packetA-${round.id}" type="file" accept=".csv,text/csv"></div><div><label>ASSESSOR B.csv</label><input id="packetB-${round.id}" type="file" accept=".csv,text/csv"></div></div><div class="actions" style="margin-top:.8rem"><button class="btn primary doImportBtn" data-id="${round.id}">Validar, importar e iniciar assessment</button></div><div class="help">Os packets são validados no navegador. Campos proibidos causam rejeição antes de qualquer insert.</div></div>` : ''}
  </div>`
}

async function createRound(event) {
  event.preventDefault()
  const fd = new FormData(event.currentTarget)
  const payload = {
    name: String(fd.get('name') || '').trim(), split: 'validation', status: 'draft',
    candidate_runtime_sha: String(fd.get('runtime') || '').trim(),
    questions_sha256: String(fd.get('questions') || '').trim(),
    created_by: state.session.user.id,
  }
  if (payload.candidate_runtime_sha !== EXPECTED_RUNTIME_SHA || payload.questions_sha256 !== EXPECTED_QUESTIONS_SHA) {
    if (!confirm('Os SHAs diferem do round congelado atual. Criar mesmo assim?')) return
  }
  const { error } = await state.supabase.from('validation_rounds').insert(payload)
  if (error) return toast(`Falha ao criar round: ${error.message}`, 'danger')
  toast('Round draft criado.', 'success'); adminHome()
}

function bindAdminRoundEvents(rounds) {
  document.querySelectorAll('.importBtn').forEach((b) => b.addEventListener('click', () => document.querySelector(`#import-${b.dataset.id}`).classList.toggle('hidden')))
  document.querySelectorAll('.doImportBtn').forEach((b) => b.addEventListener('click', () => importRoundData(rounds.find((r) => r.id === b.dataset.id))))
  document.querySelectorAll('.adjudicateBtn').forEach((b) => b.addEventListener('click', () => closeAssessment(rounds.find((r) => r.id === b.dataset.id))))
  document.querySelectorAll('.exportBtn').forEach((b) => b.addEventListener('click', () => exportRound(rounds.find((r) => r.id === b.dataset.id))))
}

function parseCsvFile(file) {
  return new Promise((resolve, reject) => {
    Papa.parse(file, { header: true, skipEmptyLines: 'greedy', worker: false,
      complete: (result) => result.errors?.length ? reject(new Error(result.errors.slice(0,3).map((x) => x.message).join('; '))) : resolve(result),
      error: reject,
    })
  })
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
    if (String(row.blind_to_nutev).toLowerCase() !== 'true') throw new Error(`Packet não inicia cego na linha ${i + 2}`)
    if (row.relevance_grade || row.reason || row.decision_timestamp) throw new Error(`Packet já contém decisão humana na linha ${i + 2}`)
  }
}

async function chunkInsert(table, rows, size = 150) {
  for (let i = 0; i < rows.length; i += size) {
    const { error } = await state.supabase.from(table).insert(rows.slice(i, i + size))
    if (error) throw new Error(`${table}: ${error.message}`)
  }
}

async function sha256File(file) {
  const bytes = await file.arrayBuffer()
  const digest = await crypto.subtle.digest('SHA-256', bytes)
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function importRoundData(round) {
  const aUser = document.querySelector(`#assessorA-${round.id}`).value
  const bUser = document.querySelector(`#assessorB-${round.id}`).value
  const qFile = document.querySelector(`#questionsFile-${round.id}`).files[0]
  const manifestFile = document.querySelector(`#packetManifest-${round.id}`).files[0]
  const aFile = document.querySelector(`#packetA-${round.id}`).files[0]
  const bFile = document.querySelector(`#packetB-${round.id}`).files[0]
  if (!aUser || !bUser || aUser === bUser || !qFile || !manifestFile || !aFile || !bFile) return toast('Selecione dois assessores diferentes, QUESTIONS.csv, manifest e os dois packets.', 'warn')
  try {
    toast('Validando packets cegos...')
    const [qParsed, aParsed, bParsed, uploadedQuestionsSha, aSha, bSha, manifestText] = await Promise.all([
      parseCsvFile(qFile), parseCsvFile(aFile), parseCsvFile(bFile), sha256File(qFile), sha256File(aFile), sha256File(bFile), manifestFile.text(),
    ])
    validatePacket(aParsed); validatePacket(bParsed)
    if (uploadedQuestionsSha !== round.questions_sha256) throw new Error(`QUESTIONS.csv SHA-256 divergente: ${uploadedQuestionsSha}`)
    let packetManifest
    try { packetManifest = JSON.parse(manifestText) } catch { throw new Error('Packets manifest não é JSON válido.') }
    if (packetManifest.label_blind !== true || packetManifest.independent_order_per_assessor !== true) throw new Error('Manifest não declara packets label-blind com ordem independente.')
    if (new Set(aParsed.data.map((r) => r.assessor_id)).size !== 1 || new Set(bParsed.data.map((r) => r.assessor_id)).size !== 1) throw new Error('Cada packet deve conter exatamente um assessor_id.')
    if (aParsed.data[0].assessor_id === bParsed.data[0].assessor_id) throw new Error('Packets A/B precisam ter assessor_id distintos.')
    const expectedPacketHashes = new Map((packetManifest.outputs || []).map((x) => [x.assessor_id, x.sha256]))
    if (expectedPacketHashes.get(aParsed.data[0].assessor_id) !== aSha) throw new Error('SHA-256 do packet A não confere com o manifest.')
    if (expectedPacketHashes.get(bParsed.data[0].assessor_id) !== bSha) throw new Error('SHA-256 do packet B não confere com o manifest.')
    if (Number(packetManifest.pool_rows) !== aParsed.data.length || Number(packetManifest.pool_rows) !== bParsed.data.length) throw new Error('Contagem dos packets não confere com pool_rows do manifest.')
    const qFields = qParsed.meta.fields || []
    if (!qFields.includes('question_id') || !qFields.includes('question_text') || !qFields.includes('split')) throw new Error('QUESTIONS.csv sem question_id/question_text/split.')
    const validationQuestions = qParsed.data.filter((x) => x.split === 'validation')
    const qIds = new Set(validationQuestions.map((x) => x.question_id))
    if (!qIds.size) throw new Error('Nenhuma pergunta validation encontrada em QUESTIONS.csv.')
    const key = (r) => `${r.question_id}\u0000${r.reference_id}`
    const aKeys = new Set(aParsed.data.map(key)); const bKeys = new Set(bParsed.data.map(key))
    if (aKeys.size !== aParsed.data.length || bKeys.size !== bParsed.data.length) throw new Error('Packet contém par question_id/reference_id duplicado.')
    if (aKeys.size !== bKeys.size || [...aKeys].some((x) => !bKeys.has(x))) throw new Error('Packets A/B não representam o mesmo common pool.')
    const bPoolByKey = new Map(bParsed.data.map((r) => [key(r), r.pool_item_id]))
    if (aParsed.data.some((r) => bPoolByKey.get(key(r)) !== r.pool_item_id)) throw new Error('Packets A/B discordam no pool_item_id para o mesmo par.')
    if ([...aParsed.data, ...bParsed.data].some((r) => !qIds.has(r.question_id))) throw new Error('Packet referencia question_id fora do split validation congelado.')
    const questionRows = validationQuestions.map((q) => ({ round_id: round.id, question_id: q.question_id, question_text: q.question_text,
      eligibility_context: { sampling_stratum: q.sampling_stratum || '', population_context: q.population_context || '', intervention_exposure: q.intervention_exposure || '', comparator: q.comparator || '', outcome_construct: q.outcome_construct || '', time_window: q.time_window || '', languages: q.languages || '', document_types: q.document_types || '' },
    }))
    const refByPool = new Map()
    for (const row of [...aParsed.data, ...bParsed.data]) {
      if (!refByPool.has(row.pool_item_id)) refByPool.set(row.pool_item_id, { round_id: round.id, pool_item_id: row.pool_item_id, question_id: row.question_id, reference_id: row.reference_id, title: row.title, abstract: row.abstract || null, journal: row.journal || null, year: row.year || null, doi: row.doi || null, pmid: row.pmid || null, pmcid: row.pmcid || null, url: row.url || null })
    }
    const assignments = []
    for (const [rows, uid] of [[aParsed.data, aUser], [bParsed.data, bUser]]) {
      for (const row of rows) assignments.push({ round_id: round.id, pool_item_id: row.pool_item_id, assessor_user_id: uid, assessor_id: row.assessor_id, assessor_order: Number(row.assessor_order), relevance_grade: null, reason: null, decision_timestamp: null, blind_to_nutev: true, review_later: false, notes: row.notes || null })
    }
    await chunkInsert('validation_questions', questionRows)
    await chunkInsert('validation_references', [...refByPool.values()])
    await chunkInsert('validation_assignments', assignments)
    const { error: statusError } = await state.supabase.from('validation_rounds').update({ status: 'assessment' }).eq('id', round.id)
    if (statusError) throw statusError
    toast(`Import concluído: ${refByPool.size} pool items × 2 assessores.`, 'success')
    adminHome()
  } catch (error) {
    try {
      await state.supabase.from('validation_assignments').delete().eq('round_id', round.id)
      await state.supabase.from('validation_references').delete().eq('round_id', round.id)
      await state.supabase.from('validation_questions').delete().eq('round_id', round.id)
    } catch { /* leave draft visible for explicit admin cleanup */ }
    toast(`Import bloqueado: ${error.message}`, 'danger')
  }
}

async function closeAssessment(round) {
  if (!confirm('Fechar assessment? Depois disso, decisões dos assessores ficam disponíveis para adjudicação e não podem mais ser alteradas.')) return
  const { error } = await state.supabase.from('validation_rounds').update({ status: 'adjudication' }).eq('id', round.id)
  if (error) return toast(`Não foi possível fechar: ${error.message}`, 'danger')
  toast('Assessment fechado. Adjudicação liberada.', 'success'); adminHome()
}

async function adjudicatorHome() {
  const rounds = (await fetchAccessibleRounds()).filter((r) => ['adjudication','locked'].includes(r.status))
  $app.innerHTML = shell(`<div class="card"><h2>Adjudicação</h2>${rounds.length ? rounds.map((r) => `<button class="btn roundChoice" data-id="${r.id}" style="display:block;width:100%;text-align:left;margin-bottom:.6rem"><strong>${escapeHtml(r.name)}</strong><br><span class="muted small">${escapeHtml(r.status)}</span></button>`).join('') : '<p>Nenhum round em adjudicação.</p>'}</div>`)
  bindShell()
  document.querySelectorAll('.roundChoice').forEach((b) => b.addEventListener('click', () => openAdjudication(rounds.find((r) => r.id === b.dataset.id))))
}

async function openAdjudication(round) {
  const [{ data: assignments, error: aErr }, { data: refs, error: rErr }, { data: questions, error: qErr }, { data: existing, error: eErr }] = await Promise.all([
    state.supabase.from('validation_assignments').select('*').eq('round_id', round.id),
    state.supabase.from('validation_references').select('*').eq('round_id', round.id),
    state.supabase.from('validation_questions').select('*').eq('round_id', round.id),
    state.supabase.from('validation_adjudications').select('*').eq('round_id', round.id),
  ])
  if (aErr || rErr || qErr || eErr) throw (aErr || rErr || qErr || eErr)
  const groups = new Map()
  for (const a of assignments) { if (!groups.has(a.pool_item_id)) groups.set(a.pool_item_id, []); groups.get(a.pool_item_id).push(a) }
  const conflicts = [...groups.entries()].filter(([, items]) => new Set(items.map((x) => x.relevance_grade)).size > 1)
  state.adjudication = { round, assignments, groups, conflicts, refs: new Map(refs.map((x) => [x.pool_item_id,x])), questions: new Map(questions.map((x) => [x.question_id,x])), existing: new Map(existing.map((x) => [x.pool_item_id,x])) }
  renderAdjudication()
}

function renderAdjudication() {
  const x = state.adjudication
  const resolved = x.conflicts.filter(([poolId]) => x.existing.has(poolId)).length
  $app.innerHTML = shell(`<div class="card"><div class="actions" style="justify-content:space-between"><div><h2 style="margin:0">${escapeHtml(x.round.name)}</h2><span class="muted">${x.conflicts.length} conflitos · ${resolved} resolvidos</span></div><div class="actions">${x.round.status === 'locked' ? '<button class="btn" id="exportAdj">Exportar CSVs finais</button>' : ''}${x.round.status === 'adjudication' ? '<button class="btn primary" id="lockRound">Finalizar/lock</button>' : ''}<button class="btn" id="backAdj">Voltar</button></div></div></div>
  <div style="margin-top:1rem">${x.conflicts.map(([poolId, items]) => conflictHtml(poolId, items, x)).join('') || '<div class="card"><p>Sem conflitos: todos os pares concordaram.</p></div>'}</div>`)
  bindShell()
  document.querySelector('#backAdj').addEventListener('click', adjudicatorHome)
  document.querySelector('#exportAdj')?.addEventListener('click', () => exportRound(x.round))
  document.querySelector('#lockRound')?.addEventListener('click', lockRound)
  document.querySelectorAll('.saveAdjudication').forEach((b) => b.addEventListener('click', () => saveAdjudication(b.dataset.pool)))
}

function conflictHtml(poolId, items, x) {
  const ref = x.refs.get(poolId) || {}; const q = x.questions.get(ref.question_id) || {}; const current = x.existing.get(poolId)
  return `<article class="card conflict"><div class="question-box"><strong>${escapeHtml(ref.question_id)}</strong> ${escapeHtml(q.question_text || '')}</div><h3>${escapeHtml(ref.title || ref.reference_id)}</h3><div class="conflict-decisions">${items.sort((a,b) => a.assessor_id.localeCompare(b.assessor_id)).map((a) => `<div class="decision"><strong>${escapeHtml(a.assessor_id)}: ${a.relevance_grade}</strong><p>${escapeHtml(a.reason)}</p><span class="muted small">${formatDate(a.decision_timestamp)}</span></div>`).join('')}</div><div class="grid two" style="margin-top:.8rem"><div><label>Nota final</label><select id="grade-${poolId}"><option value="">Selecione</option>${[0,1,2].map((g) => `<option value="${g}" ${current?.relevance_grade === g ? 'selected' : ''}>${g}</option>`).join('')}</select></div><div><label>Justificativa da adjudicação</label><textarea id="reason-${poolId}">${escapeHtml(current?.reason || '')}</textarea></div></div><button class="btn primary saveAdjudication" data-pool="${poolId}">Salvar resolução</button></article>`
}

async function saveAdjudication(poolId) {
  const x = state.adjudication
  const gradeRaw = document.querySelector(`#grade-${CSS.escape(poolId)}`).value
  const reason = document.querySelector(`#reason-${CSS.escape(poolId)}`).value.trim()
  if (!['0','1','2'].includes(gradeRaw) || !reason) return toast('Nota final e justificativa são obrigatórias.', 'warn')
  const payload = { round_id: x.round.id, pool_item_id: poolId, relevance_grade: Number(gradeRaw), adjudication_status: 'RESOLVED', adjudicator_id: state.session.user.id, reason, adjudication_timestamp: new Date().toISOString() }
  const existing = x.existing.get(poolId)
  let result
  if (existing) result = await state.supabase.from('validation_adjudications').update(payload).eq('id', existing.id).select().single()
  else result = await state.supabase.from('validation_adjudications').insert(payload).select().single()
  if (result.error) return toast(`Falha na adjudicação: ${result.error.message}`, 'danger')
  x.existing.set(poolId, result.data); renderAdjudication(); toast('Conflito resolvido.', 'success')
}

async function lockRound() {
  const x = state.adjudication
  if (!confirm('Finalizar o round? O banco bloqueará se existir conflito sem adjudicação.')) return
  const { error } = await state.supabase.from('validation_rounds').update({ status: 'locked' }).eq('id', x.round.id)
  if (error) return toast(`Não foi possível finalizar: ${error.message}`, 'danger')
  x.round.status = 'locked'; renderAdjudication(); toast('Round locked.', 'success')
}

function downloadCsv(filename, rows, columns) {
  const csv = Papa.unparse({ fields: columns, data: rows.map((r) => columns.map((c) => r[c] ?? '')) }, { newline: '\r\n' })
  const blob = new Blob([`\ufeff${csv}`], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url; a.download = filename; a.click(); URL.revokeObjectURL(url)
}

async function exportRound(round) {
  if (round.status !== 'locked') return toast('Export final disponível somente após o round ser locked.', 'warn')
  try {
    const [{ data: assignments, error:aErr }, { data: refs, error:rErr }, { data: adjudications, error:jErr }] = await Promise.all([
      state.supabase.from('validation_assignments').select('*').eq('round_id', round.id),
      state.supabase.from('validation_references').select('*').eq('round_id', round.id),
      state.supabase.from('validation_adjudications').select('*').eq('round_id', round.id),
    ])
    if (aErr || rErr || jErr) throw (aErr || rErr || jErr)
    const refMap = new Map(refs.map((x) => [x.pool_item_id,x]))
    const assessmentRows = assignments.map((a) => { const r = refMap.get(a.pool_item_id) || {}; return { question_id:r.question_id, pool_item_id:a.pool_item_id, assessor_order:a.assessor_order, reference_id:r.reference_id, title:r.title, abstract:r.abstract, journal:r.journal, year:r.year, doi:r.doi, pmid:r.pmid, pmcid:r.pmcid, url:r.url, assessor_id:a.assessor_id, relevance_grade:a.relevance_grade, reason:a.reason, decision_timestamp:a.decision_timestamp, blind_to_nutev:a.blind_to_nutev, notes:a.notes } })
    downloadCsv('VALIDATION_ASSESSMENTS.csv', assessmentRows, REQUIRED_PACKET_COLUMNS)
    const groups = new Map(); for (const a of assignments) { if (!groups.has(a.pool_item_id)) groups.set(a.pool_item_id,[]); groups.get(a.pool_item_id).push(a) }
    const adjMap = new Map(adjudications.map((x) => [x.pool_item_id,x])); const gold = []
    for (const [poolId, items] of groups) {
      const r = refMap.get(poolId) || {}; const grades = new Set(items.map((x) => x.relevance_grade));
      if (grades.size === 1) gold.push({ question_id:r.question_id, reference_id:r.reference_id, relevance_grade:[...grades][0], adjudication_status:'AGREED', adjudicator_id:'', adjudication_timestamp:'', reason:'unanimous assessors' })
      else { const j=adjMap.get(poolId); if (!j) continue; gold.push({ question_id:r.question_id, reference_id:r.reference_id, relevance_grade:j.relevance_grade, adjudication_status:'RESOLVED', adjudicator_id:j.adjudicator_id, adjudication_timestamp:j.adjudication_timestamp, reason:j.reason }) }
    }
    downloadCsv('VALIDATION_GOLD_STANDARD.csv', gold, ['question_id','reference_id','relevance_grade','adjudication_status','adjudicator_id','adjudication_timestamp','reason'])
    toast(`Exportados assessments (${assessmentRows.length}) e gold disponível (${gold.length}).`, 'success')
  } catch (error) { toast(`Falha no export: ${error.message}`, 'danger') }
}

async function routeByRole() {
  if (state.profile.role === 'assessor') return reviewerHome()
  if (state.profile.role === 'adjudicator') return adjudicatorHome()
  if (state.profile.role === 'admin') return adminHome()
  $app.innerHTML = shell(`<div class="card"><h2>Role não suportada</h2><p>Peça ao administrador para configurar sua role.</p></div>`); bindShell()
}

async function boot() {
  if (!initSupabase()) return renderConfig()
  try {
    await refreshSession()
    if (!state.session) return renderLogin()
    await loadProfile()
    await routeByRole()
    state.supabase.auth.onAuthStateChange(async (_event, session) => {
      state.session = session
      if (!session) return renderLogin()
    })
  } catch (error) {
    $app.innerHTML = shell(`<div class="card"><h2>Falha ao iniciar</h2><div class="notice danger">${escapeHtml(error.message)}</div><div class="actions" style="margin-top:1rem"><button class="btn" id="retryBtn">Tentar novamente</button><button class="btn" id="resetConfigBtn">Trocar backend</button></div></div>`)
    document.querySelector('#retryBtn').addEventListener('click', () => location.reload())
    document.querySelector('#resetConfigBtn').addEventListener('click', clearConfig)
  }
}

boot()
