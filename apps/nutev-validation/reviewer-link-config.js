const REVIEW_BASE_KEY = 'nutev_validation_reviewer_base_v1'
const REVIEW_PANEL_ID = 'reviewerLinkAddressPanel'
let renderingReviewerLinks = false

function reviewEsc(value) {
  return String(value ?? '').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#039;')
}

function isLocalOnlyHost(hostname) {
  const value = String(hostname || '').toLowerCase()
  return value === 'localhost' || value === '127.0.0.1' || value === '0.0.0.0' || value === '::1' || value === '[::1]'
}

function normalizeReviewerBase(raw) {
  const value = String(raw || '').trim()
  if (!value) return ''
  let parsed
  try {
    parsed = new URL(value)
  } catch {
    throw new Error('Informe uma URL completa, por exemplo http://192.168.1.50:8765')
  }
  if (!['http:', 'https:'].includes(parsed.protocol)) {
    throw new Error('O endereço dos avaliadores precisa usar http:// ou https://')
  }
  if (parsed.username || parsed.password) {
    throw new Error('Não inclua usuário ou senha na URL dos avaliadores.')
  }
  if (parsed.search || parsed.hash) {
    throw new Error('Não inclua parâmetros ou fragmentos na URL base dos avaliadores.')
  }
  const path = parsed.pathname.replace(/\/+$/, '')
  return `${parsed.origin}${path}`
}

function storedReviewerBase() {
  const saved = localStorage.getItem(REVIEW_BASE_KEY)
  if (saved) {
    try { return normalizeReviewerBase(saved) } catch { localStorage.removeItem(REVIEW_BASE_KEY) }
  }
  if (!isLocalOnlyHost(location.hostname)) return location.origin
  return ''
}

function tokenFromPrivateLink(value) {
  try {
    const parsed = new URL(String(value || ''), location.href)
    return new URLSearchParams(parsed.hash.replace(/^#/, '')).get('token') || ''
  } catch {
    return ''
  }
}

function privateReviewLink(base, token) {
  return `${base.replace(/\/+$/, '')}/validation/review.html#token=${encodeURIComponent(token)}`
}

function rewritePrivateLinks(base) {
  if (!base) return 0
  let changed = 0
  document.querySelectorAll('.copy-link[data-link]').forEach(button => {
    const token = tokenFromPrivateLink(button.dataset.link)
    if (!token) return
    const next = privateReviewLink(base, token)
    if (button.dataset.link !== next) {
      button.dataset.link = next
      changed += 1
    }
  })
  return changed
}

function updateCopyButtons(base) {
  const blocked = !base && isLocalOnlyHost(location.hostname)
  document.querySelectorAll('.copy-link[data-link]').forEach(button => {
    if (blocked) {
      if (!button.dataset.reviewOriginalLabel) button.dataset.reviewOriginalLabel = button.textContent || 'Copiar link privado'
      button.dataset.reviewLinkBlocked = 'true'
      button.disabled = true
      button.textContent = 'Configure endereço primeiro'
      return
    }
    if (button.dataset.reviewLinkBlocked === 'true') {
      button.disabled = false
      button.textContent = button.dataset.reviewOriginalLabel || 'Copiar link privado'
      delete button.dataset.reviewLinkBlocked
    }
  })
}

function panelHtml(base) {
  const needsAddress = !base
  const defaultHint = isLocalOnlyHost(location.hostname)
    ? 'A coordenação está em um endereço local. Informe o endereço LAN/HTTPS que os avaliadores conseguem abrir.'
    : 'Por padrão, os links usam o mesmo endereço desta página.'
  return `<section class="card" id="${REVIEW_PANEL_ID}" data-review-base-state="${reviewEsc(base || 'missing')}" style="margin-top:1rem">
    <div class="section-head"><div><span class="eyebrow">acesso dos avaliadores</span><h2>Endereço dos avaliadores</h2></div><span class="badge ${needsAddress ? 'warn' : 'success'}">${needsAddress ? 'configurar' : 'pronto'}</span></div>
    <p>${reviewEsc(defaultHint)}</p>
    ${base ? `<div class="notice success"><strong>Links privados usarão:</strong> <code>${reviewEsc(base)}</code></div>` : '<div class="notice warn"><strong>Os links ainda apontariam para localhost/0.0.0.0.</strong> Configure um endereço acessível antes de enviá-los. Os botões de cópia ficam bloqueados até isso ser resolvido.</div>'}
    <div class="actions" style="margin-top:.8rem;align-items:center;flex-wrap:wrap">
      <input id="reviewerBaseInput" type="url" inputmode="url" autocomplete="off" spellcheck="false" value="${reviewEsc(base)}" placeholder="http://192.168.1.50:8765" style="min-width:min(100%,28rem);flex:1" />
      <button class="btn primary" id="saveReviewerBase">Salvar endereço</button>
      ${base ? '<button class="btn" id="clearReviewerBase">Limpar configuração</button>' : ''}
    </div>
    <p class="small muted" style="margin-top:.55rem">Somente a URL base é salva no navegador. Os tokens continuam individuais e ficam no fragmento <code>#token=...</code>, que não é enviado nos logs HTTP.</p>
  </section>`
}

function bindPanelEvents() {
  document.querySelector('#saveReviewerBase')?.addEventListener('click', () => {
    const input = document.querySelector('#reviewerBaseInput')
    try {
      const base = normalizeReviewerBase(input?.value || '')
      if (!base) throw new Error('Informe o endereço que os avaliadores conseguem abrir.')
      localStorage.setItem(REVIEW_BASE_KEY, base)
      document.querySelector(`#${REVIEW_PANEL_ID}`)?.remove()
      renderReviewerLinkConfig()
    } catch (error) {
      alert(error.message || String(error))
    }
  })
  document.querySelector('#clearReviewerBase')?.addEventListener('click', () => {
    localStorage.removeItem(REVIEW_BASE_KEY)
    document.querySelector(`#${REVIEW_PANEL_ID}`)?.remove()
    renderReviewerLinkConfig()
  })
}

function insertPanel(base) {
  const roundPanel = document.querySelector('#roundPanel')
  if (!roundPanel || !roundPanel.querySelector('.copy-link[data-link]')) return
  const existing = document.querySelector(`#${REVIEW_PANEL_ID}`)
  const desiredState = base || 'missing'
  if (existing?.dataset.reviewBaseState === desiredState) return
  existing?.remove()
  roundPanel.insertAdjacentHTML('afterend', panelHtml(base))
  bindPanelEvents()
}

function renderReviewerLinkConfig() {
  if (renderingReviewerLinks) return
  renderingReviewerLinks = true
  try {
    const base = storedReviewerBase()
    rewritePrivateLinks(base)
    updateCopyButtons(base)
    insertPanel(base)
  } finally {
    renderingReviewerLinks = false
  }
}

const reviewerConfigRoot = document.querySelector('#app')
const reviewerConfigObserver = new MutationObserver(() => queueMicrotask(renderReviewerLinkConfig))
if (reviewerConfigRoot) reviewerConfigObserver.observe(reviewerConfigRoot, { childList:true, subtree:true })
renderReviewerLinkConfig()
