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

async function loadGold(round) {
  if (!round || round.error) return null
  try {
    const response = await fetch('/api/validation/gold', { cache: 'no-store' })
    if (response.status === 404) return null
    const payload = await response.json()
    if (!response.ok) return { error: payload.message || payload.error || 'gold indisponível' }
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

function goldHtml(round, gold) {
  if (round.status === 'adjudication_complete') {
    return `<div class="notice" style="margin-top:1rem"><strong>Adjudicação encerrada.</strong> O próximo gate é construir o ledger bruto, o gold final e executar o validator canônico. Nenhuma métrica será calculada nesta etapa.<div class="actions" style="margin-top:.7rem"><button class="btn primary" id="buildGold">Construir e validar gold standard</button><a class="btn" href="/validation/adjudicate.html">Ver adjudicação</a></div></div>`
  }
  if (round.status !== 'gold_validated') return ''
  if (!gold || gold.error || !gold.validated) {
    return `<div class="notice danger" style="margin-top:1rem"><strong>Gold marcado como validado, mas o relatório canônico não pôde ser confirmado.</strong><div class="small">${esc(gold?.error || 'Relatório ausente ou inconsistente.')}</div></div>`
  }
  const agreementPct = gold.raw_exact_agreement_fraction == null ? '—' : `${Math.round(Number(gold.raw_exact_agreement_fraction) * 1000) / 10}%`
  return `<section class="card" style="margin-top:1rem"><div class="section-head"><div><span class="eyebrow">gate canônico</span><h2>Gold standard validado</h2></div><span class="badge success">PASS</span></div><div class="grid" style="grid-template-columns:repeat(4,minmax(0,1fr));margin-top:1rem"><div class="kpi"><strong>${Number(gold.final_labels || 0)}</strong><span>labels finais</span></div><div class="kpi"><strong>${Number(gold.unanimous_groups || 0)}</strong><span>concordâncias</span></div><div class="kpi"><strong>${Number(gold.conflict_groups || 0)}</strong><span>conflitos resolvidos</span></div><div class="kpi"><strong>${agreementPct}</strong><span>acordo bruto</span></div></div><div class="notice success" style="margin-top:1rem"><strong>Cobertura do pool: 100%.</strong> O PASS confirma cobertura, cegamento e consistência da adjudicação. Ainda não confirma desempenho científico do NutEV.</div><div class="notice" style="margin-top:.7rem"><strong>Próxima etapa:</strong> calcular as métricas pré-especificadas da camada <em>validation</em>. O <code>external_test</code> continua selado.</div></section>`
}

function roundHtml(round, readiness, gold) {
  if (round?.error) return `<section class="card"><h2>Coordenação local</h2><div class="notice warn">${esc(round.error)}</div><p class="muted small">Abra esta tela no navegador da máquina que está executando o NutEV para preparar e acompanhar a rodada. Os links privados dos avaliadores podem ser abertos em outros dispositivos que alcancem este servidor.</p></section>`
  if (!round) {
    return `<section class="card featured"><span class="eyebrow">etapa 1</span><h2>Preparar rodada</h2><p>O NutEV criará automaticamente duas sessões isoladas e os links privados dos avaliadores. Nenhum avaliador precisa carregar arquivos.</p><button class="btn primary" id="prepareRound" ${readiness.ready ? '' : 'disabled'}>Preparar rodada científica</button>${readiness.ready ? '' : '<p class="small muted">O botão será liberado quando a checagem científica acima estiver pronta.</p>'}</section>`
  }
  const reviewers = (round.reviewers || []).map((reviewer, index) => {
    const total = Number(reviewer.total_items || 0), done = Number(reviewer.completed_items || 0)
    const pct = total ? Math.round(done / total * 100) : 0
    const label = reviewer.assessor_id || `Avaliador ${index + 1}`
    const link = reviewLink(reviewer.token)
    return `<div class="card"><div class="section-head"><div><span class="eyebrow">sessão privada</span><h3>${esc(label)}</h3></div><span class="badge ${reviewer.submitted ? 'success' : ''}">${reviewer.submitted ? 'enviado e travado' : `${pct}%`}</span></div><div class="progress-wrap"><div class="progress"><span style="width:${pct}%"></span></div><strong>${done}/${total}</strong></div><p class="small muted">O coordenador acompanha somente progresso e status de envio; as decisões iniciais não aparecem aqui.</p><div class="actions"><button class="btn primary copy-link" data-link="${esc(link)}">Copiar link privado</button></div></div>`
  }).join('')
  const adjudicationActive = ['ready_for_adjudication','adjudicating'].includes(round.status)
  const adjudicationComplete = round.status === 'adjudication_complete'
  const goldValidated = round.status === 'gold_validated'
  const completed = adjudicationActive || adjudicationComplete || goldValidated
  const roundBadge = goldValidated ? 'gold validado' : adjudicationComplete ? 'adjudicação concluída' : adjudicationActive ? 'A/B concluídos' : 'em avaliação'
  const adjudicationAction = adjudicationActive ? `<div class="notice success" style="margin-top:1rem"><strong>Avaliação inicial concluída.</strong> Os dois envios estão travados. Agora o adjudicador verá somente as discordâncias.<div class="actions" style="margin-top:.7rem"><a class="btn primary" href="/validation/adjudicate.html">Resolver conflitos</a></div></div>` : ''
  return `<section class="card"><div class="section-head"><div><span class="eyebrow">rodada ativa</span><h2>Avaliação A/B</h2></div><span class="badge ${completed ? 'success' : ''}">${roundBadge}</span></div><p>Distribua cada link somente ao avaliador correspondente. Nunca envie os dois links à mesma pessoa.</p></section><div class="grid two" style="margin-top:1rem">${reviewers}</div>${adjudicationAction}${goldHtml(round, gold)}`
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

async function buildGold() {
  const button = document.querySelector('#buildGold')
  if (button) { button.disabled = true; button.textContent = 'Validando…' }
  try {
    const response = await fetch('/api/validation/gold/build', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' })
    const payload = await response.json()
    if (!response.ok) throw new Error(payload.message || payload.error || 'Falha na validação do gold')
    await renderChooser()
  } catch (error) {
    alert(error.message || String(error))
    if (button) { button.disabled = false; button.textContent = 'Construir e validar gold standard' }
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
  const gold = await loadGold(round)
  app.innerHTML = shell(`
    <section class="card validation-hero"><span class="eyebrow">fluxo científico</span><h2>Validar o NutEV sem arquivos para o avaliador</h2><p>O coordenador prepara a rodada uma vez. Cada avaliador recebe um link privado, julga somente o próprio conjunto e envia. Depois entram adjudicação, gold standard e métricas.</p><div class="status-note"><span class="status-dot"></span><span>O benchmark congelado e o external test continuam separados da busca comum.</span></div>${readinessHtml(readiness)}</section>
    <section class="validation-flow" aria-label="Etapas da validação científica"><div class="flow-step"><div class="step-number">1</div><strong>Preparar</strong><span>O servidor verifica a rodada e cria dois links privados.</span></div><div class="flow-step"><div class="step-number">2</div><strong>Avaliar A/B</strong><span>Cada pessoa abre seu link, marca 0/1/2 e justifica.</span></div><div class="flow-step"><div class="step-number">3</div><strong>Adjudicar</strong><span>Depois dos dois envios travados, somente conflitos são mostrados.</span></div><div class="flow-step"><div class="step-number">4</div><strong>Resultado</strong><span>Gold validado, métricas calculadas e decisão científica exibida.</span></div></section>
    <div id="roundPanel">${roundHtml(round, readiness, gold)}</div>
    <details class="technical"><summary>Configuração avançada e contingência</summary><p>A sessão principal acima salva as decisões no servidor local privado e usa links com tokens que não entram nos logs HTTP. O SQLite e os artefatos científicos ficam dentro de <code>project_output_reference</code>, fora do Git. O modo antigo baseado no navegador permanece apenas como contingência. O backend multiusuário dedicado continua adiado.</p><div class="actions"><button class="btn" id="legacyLocal">Abrir modo local legado</button>${onlineConfigured ? '<button class="btn" id="onlineBtn">Abrir backend multiusuário configurado</button>' : ''}</div></details>`)

  document.querySelector('#prepareRound')?.addEventListener('click', prepareRound)
  document.querySelector('#buildGold')?.addEventListener('click', buildGold)
  document.querySelectorAll('.copy-link').forEach(button => button.addEventListener('click', () => copyPrivateLink(button)))
  document.querySelector('#legacyLocal')?.addEventListener('click', () => launch('local'))
  document.querySelector('#onlineBtn')?.addEventListener('click', () => launch('online'))
  clearInterval(refreshTimer)
  if (round && !round.error && round.status === 'assessment') refreshTimer = setInterval(renderChooser, 5000)
}

const requested = new URL(location.href).searchParams.get('mode')
if (requested === 'local' || requested === 'online') launch(requested)
else renderChooser()
