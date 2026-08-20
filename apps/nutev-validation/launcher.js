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

function renderChooser() {
  const onlineConfigured = Boolean(localStorage.getItem(ONLINE_CONFIG_KEY))
  app.innerHTML = shell(`
    <section class="card validation-hero">
      <span class="eyebrow">fluxo científico</span>
      <h2>Validar o NutEV sem sair do NutEV</h2>
      <p>O coordenador acompanha a rodada; os avaliadores A e B julgam referências cegamente; depois entram adjudicação, gold standard e métricas. O usuário não precisa lidar com a arquitetura técnica para entender o processo.</p>
      <div class="status-note"><span class="status-dot"></span><span>O benchmark congelado e o external test continuam separados da busca comum.</span></div>
    </section>

    <section class="validation-flow" aria-label="Etapas da validação científica">
      <div class="flow-step"><div class="step-number">1</div><strong>Rodada</strong><span>Selecionar a rodada científica congelada e os dois avaliadores.</span></div>
      <div class="flow-step"><div class="step-number">2</div><strong>Avaliação A/B</strong><span>Cada avaliador julga apenas o próprio conjunto, sem score, rank ou decisão do outro.</span></div>
      <div class="flow-step"><div class="step-number">3</div><strong>Adjudicação</strong><span>Depois dos dois envios, somente os conflitos são resolvidos.</span></div>
      <div class="flow-step"><div class="step-number">4</div><strong>Resultado</strong><span>Gold validado, métricas calculadas e decisão científica exibida.</span></div>
    </section>

    <div class="grid two" style="align-items:stretch">
      <section class="card mode-card featured">
        <span class="eyebrow">disponível agora</span>
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
      <p>O modo local mantém os dados no navegador e serve para avaliação cega em dispositivos/perfis separados. O modo multiusuário adiciona login, isolamento por usuário e adjudicação centralizada quando o backend dedicado for ativado.</p>
    </details>`)
  document.querySelector('#localBtn').addEventListener('click', () => launch('local'))
  document.querySelector('#onlineBtn').addEventListener('click', () => launch('online'))
}

const requested = new URL(location.href).searchParams.get('mode')
if (requested === 'local' || requested === 'online') launch(requested)
else renderChooser()
