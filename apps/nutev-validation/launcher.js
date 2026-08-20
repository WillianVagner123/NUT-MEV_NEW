const app = document.querySelector('#app')

function shell(content) {
  return `
    <div class="shell">
      <header class="topbar">
        <div class="brand"><div class="brand-mark">N</div><div><h1>NutEV Validation</h1><small>blind human relevance assessment</small></div></div>
        <div class="userbar"><span class="badge">MVP</span></div>
      </header>
      <main>${content}<div class="footer-note">O modo local não envia dados para servidor. O modo online será ativado quando o backend dedicado estiver disponível.</div></main>
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
  app.innerHTML = shell(`
    <div class="grid two" style="align-items:stretch;margin-top:2rem">
      <section class="card mode-card featured">
        <span class="badge">funciona agora</span>
        <h2 style="margin-top:.8rem">Modo local cego</h2>
        <p>Para começar sem Supabase. Cada avaliador usa seu próprio navegador, carrega somente o próprio packet e trabalha com salvamento automático local.</p>
        <ul>
          <li>valida SHA-256 do <code>QUESTIONS.csv</code> e do packet;</li>
          <li>rejeita score, rank, taxonomia e origem do sistema;</li>
          <li>salva progresso em IndexedDB e permite retomar depois;</li>
          <li>exporta o CSV preenchido no mesmo schema do benchmark.</li>
        </ul>
        <button class="btn primary" id="localBtn">Abrir modo local</button>
      </section>
      <section class="card mode-card">
        <span class="badge">para depois</span>
        <h2 style="margin-top:.8rem">Modo online multiusuário</h2>
        <p>Usa Supabase para login, sincronização, isolamento A/B por RLS e adjudicação centralizada. O código já existe, mas o backend dedicado será provisionado depois.</p>
        <button class="btn" id="onlineBtn">Ver configuração online</button>
      </section>
    </div>
    <div class="notice" style="margin-top:1rem"><strong>Recomendação atual:</strong> use o modo local apenas para testar a experiência e, se necessário, iniciar avaliações em dispositivos separados. Para o estudo definitivo com dois avaliadores, o backend online continua sendo a opção mais robusta para custódia e auditoria.</div>`)
  document.querySelector('#localBtn').addEventListener('click', () => launch('local'))
  document.querySelector('#onlineBtn').addEventListener('click', () => launch('online'))
}

const requested = new URL(location.href).searchParams.get('mode')
if (requested === 'local' || requested === 'online') launch(requested)
else renderChooser()
