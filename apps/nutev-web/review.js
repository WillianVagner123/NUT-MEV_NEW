import {
  $, esc, fmt, pct, fetchJson, readFilters, writeFilters, linkTo,
  activeFilterChips, renderState, provenanceLine
} from './workspace.js';

const state = {
  filters: readFilters(),
  reviewerId: localStorage.getItem('nutev.reviewer_id') || '',
  status: null,
  queueOffset: 0,
  tab: 'queue'
};

const ROUTE_LABELS = {
  'B-NORM': 'B-NORM', 'C-STRUCT': 'C-STRUCT',
  overlap: 'Overlap (B-NORM + C-STRUCT)', unrouted: 'Não roteados'
};
const STATUS_LABELS = {
  NOT_STARTED: 'Não revisado', IN_REVIEW: 'Em revisão', REVIEWED: 'Revisado',
  CONFLICT: 'Conflito', ADJUDICATION_REQUIRED: 'Adjudicação pendente', RESOLVED: 'Resolvido'
};
const DECISION_LABELS = {
  READ: 'Lido', NEEDS_FULL_TEXT: 'Precisa de texto completo',
  NEEDS_SECOND_REVIEWER: 'Precisa de segundo revisor',
  OPERATIONAL_SIGNAL_CONFIRMED: 'Sinal operacional confirmado',
  NO_OPERATIONAL_SIGNAL: 'Sem sinal operacional', DEFER: 'Adiado'
};

const statusPill = value =>
  `<span class="review-status ${esc(value)}">${esc(STATUS_LABELS[value] || value)}</span>`;

function fillSelect(node, options, selected) {
  const first = node.querySelector('option');
  node.innerHTML = first ? first.outerHTML : '';
  for (const [value, label] of options) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    node.append(option);
  }
  node.value = selected || '';
}

function syncControls(status) {
  $('#routeFilter').value = state.filters.route || 'all';
  $('#fullTextFilter').value = state.filters.full_text_status || '';
  $('#reviewerInput').value = state.reviewerId;
  fillSelect(
    $('#statusFilter'),
    (status?.vocabulary?.statuses || []).map(key => [key, STATUS_LABELS[key] || key]),
    state.filters.review_status
  );
  fillSelect(
    $('#classFilter'),
    (status?.by_document_class || []).map(item => [item.key, item.label]),
    state.filters.document_class
  );
  $('#openMap').href = linkTo('/evidence-map.html', state.filters);
}

function setFilter(key, value) {
  if (!value || value === 'all') delete state.filters[key];
  else state.filters[key] = String(value);
  writeFilters(state.filters);
  load();
}

function renderKpis(status) {
  const totals = status.totals || {};
  const counts = totals.counts || {};
  const rows = [
    ['Total na fila', fmt(totals.queue), 'conjunto Tier A perfilado · fila de leitura'],
    ['Não revisados', fmt(counts.NOT_STARTED), pct(counts.NOT_STARTED, totals.queue)],
    ['Em revisão', fmt(counts.IN_REVIEW), 'leitura iniciada'],
    ['Revisados', fmt(counts.REVIEWED), 'lidos por um humano — não é inclusão'],
    ['Conflitos', fmt(counts.CONFLICT), 'revisores independentes divergem'],
    ['Adjudicação pendente', fmt(counts.ADJUDICATION_REQUIRED), 'aguarda terceiro revisor'],
    ['Resolvidos', fmt(counts.RESOLVED), 'adjudicação concluída']
  ];
  $('#reviewKpis').innerHTML = rows.map(([label, value, note]) =>
    `<article class="card metric-card"><span class="metric-label">${esc(label)}</span>` +
    `<strong class="metric-value">${esc(value)}</strong><span class="metric-note">${esc(note)}</span></article>`
  ).join('');
}

function progressRow(label, done, total) {
  const width = total ? Math.max(1, Math.round(100 * done / total)) : 0;
  return `<div class="progress-row"><span>${esc(label)}</span>` +
    `<span class="progress-track"><span class="progress-fill" style="width:${width}%"></span></span>` +
    `<small>${fmt(done)} / ${fmt(total)} lidos</small></div>`;
}

function renderProgress(status) {
  $('#routeProgress').innerHTML = Object.entries(status.by_route || {})
    .map(([key, value]) => progressRow(ROUTE_LABELS[key] || key, value.reviewed, value.queue))
    .join('') || '<p class="small-state">Sem filas nesta seleção.</p>';

  $('#classProgress').innerHTML = (status.by_document_class || [])
    .map(item => progressRow(
      item.label,
      (item.counts?.REVIEWED || 0) + (item.counts?.RESOLVED || 0),
      item.queue
    )).join('') || '<p class="small-state">Sem classes nesta seleção.</p>';

  const reviewers = status.by_reviewer || [];
  $('#reviewerBoard').innerHTML = reviewers.length
    ? reviewers.map(item => {
        const detail = Object.entries(item.counts || {})
          .map(([key, value]) => `${STATUS_LABELS[key] || key} ${value}`).join(' · ');
        return `<div class="provider-line"><div><strong>${esc(item.reviewer_id)}</strong>` +
          `<small>${esc(detail)}</small></div><span class="mini-pill">${fmt(item.documents)} documentos</span></div>`;
      }).join('')
    : '<p class="small-state">Nenhum evento humano registrado ainda.</p>';
}

function reviewerSummary(review) {
  const reviewers = review?.reviewers || [];
  if (!reviewers.length) return 'sem evento humano registrado';
  return reviewers.map(item =>
    `${item.reviewer_id}: ${STATUS_LABELS[item.status] || item.status}` +
    (item.decision ? ` (${DECISION_LABELS[item.decision] || item.decision})` : '')
  ).join(' · ');
}

function queueItem(doc) {
  const review = doc.review || { status: 'NOT_STARTED' };
  const meta = [
    doc.year || 'ano n/d',
    doc.document_class_label || doc.document_class,
    doc.source_provider || 'fonte n/d',
    `texto: ${doc.full_text_status}`
  ].join(' · ');
  const domains = (doc.domains || []).map(value =>
    `<span class="mini-pill">${esc(String(value).replaceAll('_', ' '))}</span>`).join('');
  return `<article class="queue-item" data-document-id="${esc(doc.document_id)}">
    <div>
      <strong>${esc(doc.title || 'Sem título')}</strong>
      <small>${esc(meta)}</small>
      <div class="detail-chips">${(doc.routes || []).map(route =>
        `<span class="mini-pill">${esc(route)}</span>`).join('')}${domains}</div>
      <small>${esc(reviewerSummary(review))}</small>
    </div>
    <div class="queue-side">
      ${statusPill(review.status || 'NOT_STARTED')}
      <a class="chip-button" href="${esc(linkTo('/articles.html', state.filters, { document_id: doc.document_id }))}">Abrir dossiê</a>
      <div class="queue-actions">
        <button class="chip-button" type="button" data-record="IN_REVIEW">Em revisão</button>
        <button class="chip-button" type="button" data-record="REVIEWED">Marcar lido</button>
        <button class="chip-button" type="button" data-record="ADJUDICATION_REQUIRED">Pedir adjudicação</button>
      </div>
    </div>
  </article>`;
}

function renderQueue(payload, { append = false } = {}) {
  const html = (payload.documents || []).map(queueItem).join('');
  if (append) $('#queueList').insertAdjacentHTML('beforeend', html);
  else $('#queueList').innerHTML = html ||
    '<p class="small-state">Nenhum documento nesta fila. Isso é um recorte vazio, não ausência de literatura.</p>';
  $('#queueMeta').textContent =
    `${fmt(payload.total_filtered)} documentos · página de ${fmt(payload.page_size)} · ` +
    'fila rank-blind: sem Bank rank, score, tier ou relevância de máquina.';
  state.queueOffset = payload.next_offset;
  $('#queueMore').classList.toggle('hidden', payload.next_offset === null || payload.next_offset === undefined);
}

function renderConflicts(payload) {
  const rows = payload.conflicts || [];
  $('#conflictList').innerHTML = rows.length ? rows.map(row => `
    <article class="conflict-card">
      <div><strong>${esc(row.title || row.document_id)}</strong> ${statusPill(row.status)}
        <small> · ${esc(row.year || 'ano n/d')} · ${esc((row.routes || []).join(' / ') || 'sem rota')}</small></div>
      <div class="conflict-grid">${(row.reviewers || []).map(item => `
        <div class="conflict-side">
          <strong>${esc(item.reviewer_id)}</strong>
          <div>${esc(STATUS_LABELS[item.status] || item.status)}${item.decision ? ` · ${esc(DECISION_LABELS[item.decision] || item.decision)}` : ''}</div>
          <div>${esc(item.reason_code || '')}</div>
          <div>${esc(item.reason_text || 'sem justificativa registrada')}</div>
          <small>${esc(item.updated_at || '')}</small>
        </div>`).join('')}</div>
      <div class="queue-actions">
        <a class="chip-button" href="${esc(linkTo('/articles.html', {}, { document_id: row.document_id }))}">Abrir dossiê</a>
        <button class="chip-button" type="button" data-adjudicate="${esc(row.document_id)}">Registrar resolução</button>
      </div>
    </article>`).join('')
    : '<p class="small-state">Nenhum conflito registrado. Conflitos aparecem quando revisores independentes divergem.</p>';
}

async function recordEvent(documentId, status, extra = {}) {
  const reviewerId = state.reviewerId.trim();
  if (!reviewerId) {
    renderState($('#reviewState'), 'partial',
      'Informe o identificador do revisor antes de registrar um estado.',
      'O evento humano é sempre atribuído a uma pessoa identificada.');
    $('#reviewerInput').focus();
    return;
  }
  try {
    const response = await fetch('/api/review/event', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ document_id: documentId, reviewer_id: reviewerId, status, ...extra })
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) {
      throw new Error(payload?.message || payload?.error || `HTTP ${response.status}`);
    }
    await load();
  } catch (error) {
    renderState($('#reviewState'), 'error', 'Não foi possível registrar o evento de revisão.', error.message);
  }
}

function selectTab(tab) {
  state.tab = tab;
  for (const name of ['queue', 'progress', 'conflicts']) {
    const button = $(`#tab-${name}`);
    button.setAttribute('aria-selected', String(name === tab));
    $(`#panel-${name}`).classList.toggle('hidden', name !== tab);
  }
}

async function loadQueue({ append = false } = {}) {
  const params = new URLSearchParams(state.filters);
  params.set('limit', '50');
  if (append && state.queueOffset) params.set('offset', state.queueOffset);
  renderQueue(await fetchJson(`/api/review/queue?${params}`), { append });
}

async function load() {
  renderState($('#reviewState'), 'loading', 'Carregando estado da revisão…');
  $('#reviewContent').classList.add('hidden');
  try {
    const [status, conflicts] = await Promise.all([
      fetchJson(`/api/review/status?${new URLSearchParams(state.filters)}`),
      fetchJson('/api/review/conflicts')
    ]);
    state.status = status;
    $('#reviewHealth').textContent = 'contexto verificado';
    $('#reviewHealth').className = 'status-pill ok';
    syncControls(status);
    activeFilterChips($('#activeFilters'), state.filters, key => setFilter(key, ''), () => {
      state.filters = {};
      writeFilters(state.filters);
      load();
    });
    renderKpis(status);
    renderProgress(status);
    renderConflicts(conflicts);
    state.queueOffset = 0;
    await loadQueue();
    $('#reviewProvenance').textContent = provenanceLine(status.provenance) || 'sem proveniência registrada';
    $('#reviewState').classList.add('hidden');
    $('#reviewContent').classList.remove('hidden');
    selectTab(state.tab);
  } catch (error) {
    $('#reviewHealth').textContent = 'contexto indisponível';
    $('#reviewHealth').className = 'status-pill bad';
    renderState($('#reviewState'), error.status === 503 ? 'partial' : 'error',
      error.status === 503 ? 'Contexto do Article 1 ainda não materializado.' : 'Review Control Center indisponível.',
      error.message);
  }
}

$('#queueList').addEventListener('click', event => {
  const button = event.target.closest('[data-record]');
  if (!button) return;
  const item = button.closest('[data-document-id]');
  const status = button.dataset.record;
  const extra = status === 'REVIEWED' ? { decision: 'READ' } : {};
  if (status === 'ADJUDICATION_REQUIRED') extra.stage = 'adjudication';
  recordEvent(item.dataset.documentId, status, extra);
});
$('#conflictList').addEventListener('click', event => {
  const button = event.target.closest('[data-adjudicate]');
  if (button) recordEvent(button.dataset.adjudicate, 'RESOLVED', { stage: 'adjudication' });
});
$('#queueMore').addEventListener('click', () => loadQueue({ append: true }));
$('#clearFilters').addEventListener('click', () => {
  state.filters = {};
  writeFilters(state.filters);
  load();
});
$('#reviewerInput').addEventListener('change', () => {
  state.reviewerId = $('#reviewerInput').value.trim();
  localStorage.setItem('nutev.reviewer_id', state.reviewerId);
});
document.querySelectorAll('[data-filter]').forEach(node => {
  node.addEventListener('change', () => setFilter(node.dataset.filter, node.value));
});
document.querySelectorAll('[data-tab]').forEach(button => {
  button.addEventListener('click', () => selectTab(button.dataset.tab));
});
window.addEventListener('popstate', () => { state.filters = readFilters(); load(); });

syncControls(null);
load();
