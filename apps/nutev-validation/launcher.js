const app = document.querySelector('#app')
const ONLINE_CONFIG_KEY = 'nutev_validation_supabase_config_v1'
let refreshTimer = null

function esc(value) {
  return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')
}

function shell(content) {
  return `
    <div class="unified-shell">
      <aside class="product-sidebar">
        <div class="product-brand"><div class="product-brand-mark">N</div><div><strong>NutEV</strong><span>Evidence Engine</span></div></div>
        <nav class="product-nav">
          <a href="/">⌕ <span>Buscar evidências</span></a>
          <a href="/?view=history">◷ <span>Minhas buscas</span></a>
          <a class="active" href="/validation/">✓ <span>Validação científica</span></a>
        </nav>
        <div class="product-sidebar-note">A validação científica é separada da busca normal e preserva o cegamento do benchmark.</div>
      </aside>
      <section class="workspace">
        <header class="workspace-header">
          <div><h1>Validação científica</h1><p>Do julgamento humano ao resultado do benchmark, sem misturar score ou rank com os avaliadores.</p></div>
          <div class="workspace-userbar"><span class="badge">benchmark cego</span></div>
        </header>
        <main class="workspace-body">${content}</main>
      </section>
    </div>`
}

async function launch(mode) {
  clearInterval(refreshTimer)
  const url = new URL(location.href)
  url.searchParams.set('mode', mode)
  history.replaceState({}, '', url)
  if (mode === 'local') return import('./local-mode.js')
  if (mode === 'online') return import('./app.js')
}

async function loadReadiness() {
  try {
    const response = await fetch('/api/validation/readiness', { cache: 'no-store' })
    if (!response.ok) throw new Error('readiness unavailable')
    return await response.json()
  } catch {
    return { status: 'unavailable', ready: false, message: 'Não foi possível verificar a rodada pelo servidor.' }
  }
}

async function loadRound() {
  try {
    const response = await fetch('/api/validation/round', { cache: 'no-store' })
    if (response.status === 404) return null
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.message || payload.error || 'status indisponível')
    return payload
  } catch (error) {
    return { error: error.message || String(error) }
  }
}

function readinessHtml(readiness) {
  const status = readiness.status || 'unavailable'
  const label = status === 'ready' ? 'rodada científica verificada' : status === 'invalid' ? 'rodada inválida' : status === 'waiting_for_private_packets' ? 'aguardando materiais privados' : 'status indisponível'
  const badgeClass = status === 'ready' ? 'success' : status === 'invalid' ? 'danger' : 'warn'
  const counts = readiness.ready ? `${Number(readiness.assessor_count || 0)} avaliadores · ${Number(readiness.packet_rows || 0)} itens privados verificados` : ''
  return `<div class="notice ${badgeClass}" style="margin-top:1rem"><strong>${esc(label)}</strong><div class="small" style="margin-top:.25rem">${esc(readiness.message || '')}</div>${counts ? `<div class="small" style="margin-top:.25rem">${esc(counts)}</div>` : ''}</div>`
}

function reviewLink(token) {
  return `${location.origin}/validation/review.html#token=${encodeURIComponent(token)}`
}

function roundHtml(round, readiness) {
  if (round?.error) return `<section class="card"><h2>Coordenação local</h2><div class="notice warn">${esc(round.error)}</div><p class="muted small">Abra esta tela no navegador da máquina que está executando o NutEV para preparar e acompanhar a rodada. Os links privados dos avaliadores podem ser abertos em outros dispositivos que alcancem este servidor.</p></section>`
  if (!round) {
    return `<section class="card featured"><span class="eyebrow">etapa 1</span><h2>Preparar rodada</h2><p>O NutEV criará automaticamente duas sessões isoladas e os links privados dos avaliadores. Nenhum avaliador precisa carregar arquivos.</p><button class="btn primary" id="prepareRound" ${readiness.ready ? '' : 'disabled'}>Preparar rodada científica</button>${readiness.ready ? '' : '<p class="small muted">O botão será liberado quando a checagem científica acima estiver pronta.</p>'}</section>`
  }
  const reviewers = (round.reviewers || []).map((reviewer, index) => {
    const total = Number(reviewer.total_items || 0), done = Number(reviewer.completed_items || 0)
    const pct = total ? Math.round(done / total * 100) : 0
    const label = reviewer.assessor_id || `Avaliador ${index + 1}`
    const link = reviewLink(reviewer.token)
    return `<div class="card">
      <div class="section-head"><div><span class="eyebrow">sessão privada</span><h3>${esc(label)}</h3></div><span class="badge ${reviewer.submitted ? 'success' : ''}">${reviewer.submitted ? 'enviado e travado' : `${pct}%`}</span></div>
      <div class="progress-wrap"><div class="progress"><span style="width:${pct}%"></span></div><strong>${done}/${total}</strong></div>
      <p class="small muted">O coordenador acompanha somente progresso e status de envio; as decisões iniciais não aparecem aqui.</p>
      <div class="actions"><button class="btn primary copy-link" data-link="${esc(link)}">Copiar link privado</button></div>
    </div>`
  }).join('')
  const adjudicationOpen = ['ready_for_adjudication','adjudicating','adjudication_complete'].includes(round.status)
  const adjudicationComplete = round.status === 'adjudication_complete'
  const roundBadge = adjudicationComplete ? 'adjudicação concluída' : adjudicationOpen ? 'A/B concluídos' : 'em avaliação'
  const action = adjudicationOpen ? `<div class="notice ${adjudicationComplete ? 'success' : ''}" style="margin-top:1rem"><strong>${adjudicationComplete ? 'Adjudicação encerrada.' : 'Avaliação inicial concluída.'}</strong> ${adjudicationComplete ? 'A próxima etapa é construir e validar o gold standard.' : 'Os dois envios estão travados. Agora o adjudicador verá somente as discordâncias.'}<div class="actions" style="margin-top:.7rem"><a class="btn primary" href="/validation/adjudicate.html">${adjudicationComplete ? 'Ver adjudicação' : 'Resolver conflitos'}</a></div></div>` : ''
  return `<section class="card"><div class="section-head"><div><span class="eyebrow">rodada ativa</span><h2>Avaliação A/B</h2></div><span class="badge ${adjudicationOpen ? 'success' : ''}">${roundBadge}</span></div><p>Distribua cada link somente ao avaliador correspondente. Nunca envie os dois links à mesma pessoa.</p></section><div class="grid two" style="margin-top:1rem">${reviewers}</div>${action}`
}

async function prepareRound() {
  const button = document.querySelector('#prepareRound')
  if (button) { button.disabled = true; button.textContent = 'Preparando…' }
  try {
    const response = await fetch('/api/validation/round/prepare', { method: 'POST', headers: {'Content-Type':'application/json'}, body: '{}' })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.message || payload.error || 'Falha ao preparar rodada')
    await renderChooser()
  } catch (error) {
    alert(error.message || String(error))
    if (button) { button.disabled = false; button.textContent = 'Preparar rodada científica' }
  }
}

async function copyPrivateLink(button) {
  const link = button.dataset.link || ''
  try {
    await navigator.clipboard.writeText(link)
    const original = button.textContent; button.textContent = 'Link copiado ✓'; setTimeout(() => { button.textContent = original }, 1800)
  } catch {
    prompt('Copie o link privado:', link)
  }
}

async function renderChooser() {
  const onlineConfigured = Boolean(localStorage.getItem(ONLINE_CONFIG_KEY))
  const [readiness, round] = await Promise.all([loadReadiness(), loadRound()])
  app.innerHTML = shell(`
    <section class="card validation-hero">
      <span class="eyebrow">fluxo científico</span>
      <h2>Validar o NutEV sem arquivos para o avaliador</h2>
      <p>O coordenador prepara a rodada uma vez. Cada avaliador recebe um link privado, julga somente o próprio conjunto e envia. Depois entram adjudicação, gold standard e métricas.</p>
      <div class="status-note"><span class="status-dot"></span><span>O benchmark congelado e o external test continuam separados da busca comum.</span></div>
      ${readinessHtml(readiness)}
    </section>

    <section class="validation-flow" aria-label="Etapas da validação científica">
      <div class="flow-step"><div class="step-number">1</div><strong>Preparar</strong><span>O servidor verifica a rodada e cria dois links privados.</span></div>
      <div class="flow-step"><div class="step-number">2</div><strong>Avaliar A/B</strong><span>Cada pessoa abre seu link, marca 0/1/2 e justifica.</span></div>
      <div class="flow-step"><div class="step-number">3</div><strong>Adjudicar</strong><span>Depois dos dois envios travados, somente conflitos são mostrados.</span></div>
      <div class="flow-step"><div class="step-number">4</div><strong>Resultado</strong><span>Gold validado, métricas calculadas e decisão científica exibida.</span></div>
    </section>

    <div id="roundPanel">${roundHtml(round, readiness)}</div>

    <details class="technical">
      <summary>Configuração avançada e contingência</summary>
      <p>A sessão principal acima salva as decisões no servidor local privado e usa links com tokens que não entram nos logs HTTP. O SQLite fica dentro de <code>project_output_reference</code>, fora do Git. O modo antigo baseado no navegador permanece apenas como contingência. O backend multiusuário dedicado continua adiado.</p>
      <div class="actions"><button class="btn" id="legacyLocal">Abrir modo local legado</button>${onlineConfigured ? '<button class="btn" id="onlineBtn">Abrir backend multiusuário configurado</button>' : ''}</div>
    </details>`)

  document.querySelector('#prepareRound')?.addEventListener('click', prepareRound)
  document.querySelectorAll('.copy-link').forEach(button => button.addEventListener('click', () => copyPrivateLink(button)))
  document.querySelector('#legacyLocal')?.addEventListener('click', () => launch('local'))
  document.querySelector('#onlineBtn')?.addEventListener('click', () => launch('online'))
  clearInterval(refreshTimer)
  if (round && !round.error && round.status === 'assessment') refreshTimer = setInterval(renderChooser, 5000)
}

const requested = new URL(location.href).searchParams.get('mode')
if (requested === 'local' || requested === 'online') launch(requested)
else renderChooser()
