let coordinatorAvailable = false
let boundaryLoaded = false

async function loadCapabilities() {
  try {
    const response = await fetch('/api/capabilities', { cache: 'no-store' })
    if (!response.ok) throw new Error('capabilities unavailable')
    const payload = await response.json()
    coordinatorAvailable = payload.coordinator_available === true
  } catch {
    coordinatorAvailable = false
  } finally {
    boundaryLoaded = true
    applyBoundary()
  }
}

function applyBoundary() {
  if (!boundaryLoaded || coordinatorAvailable) return
  const coordinatorIds = ['prepareRound', 'buildGold', 'runMetrics', 'lockDecision']
  let changed = false
  for (const id of coordinatorIds) {
    const node = document.getElementById(id)
    if (!node) continue
    node.remove()
    changed = true
  }
  const workspace = document.querySelector('.workspace-body')
  if (!workspace || document.getElementById('publicCoordinatorBoundary')) return
  const notice = document.createElement('section')
  notice.id = 'publicCoordinatorBoundary'
  notice.className = 'card'
  notice.innerHTML = `
    <span class="eyebrow">limite de acesso</span>
    <h2>Coordenação disponível somente no ambiente autorizado</h2>
    <p>Este endereço público não executa preparação de rodada, adjudicação, gold, métricas ou lock de decisão. Fluxos remotos de avaliador continuam disponíveis apenas pelos links privados correspondentes.</p>
  `
  workspace.prepend(notice)
  if (changed) notice.dataset.coordinatorActionsHidden = 'true'
}

const observer = new MutationObserver(applyBoundary)
observer.observe(document.documentElement, { childList: true, subtree: true })
loadCapabilities()
