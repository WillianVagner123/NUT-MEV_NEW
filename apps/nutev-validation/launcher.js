const app = document.querySelector('#app')
const ONLINE_CONFIG_KEY = 'nutev_validation_supabase_config_v1'

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

function readinessHtml(readiness) {
  const status = readiness.status || 'unavailable'
  const label = status === 'ready' ? 'rodada pronta' : status === 'invalid' ? 'rodada inválida' : status === 'waiting_for_private_packets' ? 'aguardando preparação' : 'status indisponível'
  const badgeClass = status === 'ready' ? 'success' : status === 'invalid' ? 'danger' : 'warn'
  const counts = readiness.ready ? `<span>${Number(readiness.assessor_count || 0)} avaliadores · ${Number(readiness.packet_rows || 0)} itens privados verificados</span>` : ''
  return `<div class="notice ${badgeClass}" style="margin-top:1rem"><strong>${label}</strong><div class="small" style="margin-top:.25rem">${readiness.message || ''}</div>${counts ? `<div class="small" style="margin-top:.25rem">${counts}</div>` : ''}</div>`
}

async function renderChooser() {
  const onlineConfigured = Boolean(localStorage.getItem(ONLINE_CONFIG_KEY))
  const readiness = await loadReadiness()
  app.innerHTML = shell(`
    <section class="card validation-hero">
      <span class="eyebrow">fluxo científico</span>
      <h2>Validar o NutEV sem sair do NutEV</h2>
      <p>O coordenador acompanha a rodada; os avaliadores A e B julgam referências cegamente; depois entram adjudicação, gold standard e métricas. O usuário não precisa lidar com a arquitetura técnica para entender o processo.</p>
      <div class="status-note"><span class="status-dot"></span><span>O benchmark congelado e o external test continuam separados da busca comum.</span></div>
      ${readinessHtml(readiness)}
    </section>

    <section class="validation-flow" aria-label="Etapas da validação científica">
      <div class="flow-step"><div class="step-number">1</div><strong>Rodada</strong><span>Selecionar a rodada científica congelada e os dois avaliadores.</span></div>
      <div class="flow-step"><div class="step-number">2</div><strong>Avaliação A/B</strong><span>Cada avaliador julga apenas o próprio conjunto, sem score, rank ou decisão do outro.</span></div>
      <div class="flow-step"><div class="step-number">3</div><strong>Adjudicação</strong><span>Depois dos dois envios, somente os conflitos são resolvidos.</span></div>
      <div class="flow-step"><div class="step-number">4</div><strong>Resultado</strong><span>Gold validado, métricas calculadas e decisão científica exibida.</span></div>
    </section>

    <div class="grid two" style="align-items:stretch">
      <section class="card mode-card featured">
        <span class="eyebrow">avaliação</span>
        <h2>Avaliação cega</h2>
        <p>Abra o ambiente de julgamento. Cada avaliador trabalha no próprio navegador e recebe somente o pacote cego preparado para ele.</p>
        <button class="btn primary" id="localBtn">Abrir avaliação cega</button>
      </section>
      <section class="card mode-card">
        <span class="eyebrow">coordenação</span>
        <h2>Ambiente multiusuário</h2>
        <p>${onlineConfigured ? 'O backend deste navegador já está configurado. Entre para acompanhar rounds, progresso e adjudicação.' : 'A estrutura multiusuário já existe no código, mas o backend dedicado ainda não foi ativado neste navegador.'}</p>
        ${onlineConfigured ? '<button class="btn primary" id="onlineBtn">Abrir coordenação</button>' : '<button class="btn" id="onlineBtn">Ver ambiente multiusuário</button>'}
      </section>
    </div>

    <details class="technical">
      <summary>Configuração avançada e contingência</summary>
      <p>O modo local mantém os dados no navegador e serve para avaliação cega em dispositivos/perfis separados. O servidor verifica automaticamente o freeze das perguntas e, quando os pacotes privados estão no diretório de custódia configurado, também confere SHA-256, cegamento, esquema e ausência de decisões prévias. O modo multiusuário adiciona login, isolamento por usuário e adjudicação centralizada quando o backend dedicado for ativado.</p>
    </details>`)
  document.querySelector('#localBtn').addEventListener('click', () => launch('local'))
  document.querySelector('#onlineBtn').addEventListener('click', () => launch('online'))
}

const requested = new URL(location.href).searchParams.get('mode')
if (requested === 'local' || requested === 'online') launch(requested)
else renderChooser()
