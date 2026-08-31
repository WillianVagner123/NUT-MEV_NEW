import {
  $, esc, fmt, pct, fetchJson, readFilters, writeFilters, linkTo,
  activeFilterChips, renderState, provenanceLine
} from './workspace.js';

const state = { filters: readFilters(), map: null, cell: null, cellOffset: 0 };

const PROVIDER_OPTIONS = [
  ['pubmed', 'PubMed'], ['europepmc', 'Europe PMC'], ['openalex', 'OpenAlex'],
  ['crossref', 'Crossref'], ['doaj', 'DOAJ'], ['semantic_scholar', 'Semantic Scholar'],
  ['lilacs_bvs_native', 'LILACS / BVS'], ['scielo_native', 'SciELO']
];
const FULL_TEXT_LABELS = {
  retrieved: 'Recuperado', partial: 'Parcial', unavailable: 'Indisponível',
  not_retrieved: 'Não recuperado', not_attempted: 'Ainda não buscado', unknown: 'Não informado'
};
const FULL_TEXT_OPTIONS = Object.entries(FULL_TEXT_LABELS).filter(([key]) => key !== 'unknown');

/** Six-step single-hue scale. Steps encode document count and nothing else. */
function heatClass(value, max) {
  if (!value) return 'heat-0';
  if (max <= 1) return 'heat-5';
  const ratio = value / max;
  if (ratio <= 0.08) return 'heat-1';
  if (ratio <= 0.22) return 'heat-2';
  if (ratio <= 0.45) return 'heat-3';
  if (ratio <= 0.72) return 'heat-4';
  return 'heat-5';
}

function fillSelect(node, options, selected) {
  const first = node.querySelector('option');
  node.innerHTML = first ? first.outerHTML : '';
  for (const [value, label] of options) {
    const option = document.createElement('option');
    option.value = value;
    option.textContent = label;
    node.append(option);
  }
  node.value = selected || node.querySelector('option').value;
}

function syncControls(map) {
  $('#routeFilter').value = state.filters.route || 'all';
  fillSelect($('#providerFilter'), PROVIDER_OPTIONS, state.filters.source_provider);
  fillSelect($('#fullTextFilter'), FULL_TEXT_OPTIONS, state.filters.full_text_status);
  if (map) {
    fillSelect(
      $('#classFilter'),
      (map.document_classes || []).map(item => [item.key, item.label]),
      state.filters.document_class
    );
    fillSelect(
      $('#domainFilter'),
      (map.domains || []).map(item => [item.key, item.label]),
      state.filters.domain
    );
  }
  $('#yearFrom').value = state.filters.year_from || '';
  $('#yearTo').value = state.filters.year_to || '';
  $('#openCorpus').href = linkTo('/articles.html', state.filters);
}

function setFilter(key, value) {
  if (!value || value === 'all') delete state.filters[key];
  else state.filters[key] = String(value);
  writeFilters(state.filters);
  closeCell();
  load();
}

function clearFilters() {
  state.filters = {};
  writeFilters(state.filters);
  closeCell();
  load();
}

function renderKpis(map) {
  const universe = map.universe || {};
  const rows = [
    ['Documentos no recorte', fmt(universe.filtered_documents), `de ${fmt(universe.documents)} no Tier A perfilado`],
    ['Atribuições domínio × classe', fmt(universe.cell_assignments), 'um documento conta em cada domínio que carrega'],
    ['Multi-domínio', fmt(universe.multi_domain_documents), 'documentos com mais de um domínio'],
    ['Domínios × classes', `${fmt((map.domains || []).length)} × ${fmt((map.document_classes || []).length)}`, 'dimensões presentes no recorte']
  ];
  $('#mapKpis').innerHTML = rows.map(([label, value, note]) =>
    `<article class="card metric-card"><span class="metric-label">${esc(label)}</span>` +
    `<strong class="metric-value">${esc(value)}</strong><span class="metric-note">${esc(note)}</span></article>`
  ).join('');
}

function cellTooltip(cell, domainLabel, classLabel) {
  const routes = cell.routes || {};
  const full = cell.full_text || {};
  return [
    `${domainLabel} × ${classLabel}`,
    `Documentos: ${cell.documents}`,
    `Rotas: B-NORM ${routes['B-NORM'] || 0} · C-STRUCT ${routes['C-STRUCT'] || 0} · overlap ${routes.overlap || 0} · não roteados ${routes.unrouted || 0}`,
    `Texto completo disponível: ${full.available || 0} (retrieved ${full.retrieved || 0} · partial ${full.partial || 0})`,
    'Contagem de documentos. Não é qualidade nem força da evidência.'
  ].join('\n');
}

function renderMatrix(map) {
  const classes = map.document_classes || [];
  const rows = map.rows || [];
  const max = Math.max(0, ...rows.flatMap(row => row.cells.map(cell => cell.documents)));
  const head = `<thead><tr><th class="corner" scope="col">Domínio operacional</th>${
    classes.map(item => `<th scope="col">${esc(item.label)}</th>`).join('')
  }<th scope="col">Documentos</th></tr></thead>`;
  const body = `<tbody>${rows.map(row => `<tr><th scope="row">${esc(row.label)}</th>${
    row.cells.map(cell => {
      const classLabel = classes.find(item => item.key === cell.document_class)?.label || cell.document_class;
      const empty = cell.documents ? '0' : '1';
      return `<td class="${heatClass(cell.documents, max)}"><button class="map-cell" type="button" data-empty="${empty}"` +
        `${cell.documents ? '' : ' disabled'} data-domain="${esc(cell.domain)}" data-class="${esc(cell.document_class)}"` +
        ` title="${esc(cellTooltip(cell, row.label, classLabel))}"` +
        ` aria-label="${esc(`${row.label} × ${classLabel}: ${cell.documents} documentos`)}">${fmt(cell.documents)}</button></td>`;
    }).join('')
  }<td class="map-total-row"><strong>${fmt(map.row_totals?.[row.domain] || 0)}</strong></td></tr>`).join('')}</tbody>`;
  const foot = `<tfoot><tr><th scope="row">Documentos por classe</th>${
    classes.map(item => `<td class="map-total-row">${fmt(map.column_totals?.[item.key] || 0)}</td>`).join('')
  }<td class="map-total-row">${fmt(map.universe?.filtered_documents || 0)}</td></tr></tfoot>`;
  $('#evidenceMatrix').innerHTML =
    '<caption class="visually-hidden">Contagem de documentos por domínio operacional e classe documental.</caption>' +
    head + body + foot;

  // Mobile: the matrix becomes a domain -> classes list instead of a squeezed grid.
  $('#mapMobile').innerHTML = rows.map(row => {
    const chips = row.cells.filter(cell => cell.documents).map(cell => {
      const classLabel = classes.find(item => item.key === cell.document_class)?.label || cell.document_class;
      return `<button class="chip-button" type="button" data-domain="${esc(cell.domain)}" data-class="${esc(cell.document_class)}">` +
        `${esc(classLabel)} · ${fmt(cell.documents)}</button>`;
    }).join('');
    return `<div class="map-mobile-group"><h3>${esc(row.label)} · ${fmt(map.row_totals?.[row.domain] || 0)}</h3>` +
      `<div class="chip-row">${chips || '<span class="small-state">Sem documentos neste recorte.</span>'}</div></div>`;
  }).join('');
}

function renderCell(payload, { append = false } = {}) {
  const drawer = $('#cellDrawer');
  drawer.classList.remove('hidden');
  $('#cellTitle').textContent = `${payload.domain.label} × ${payload.document_class.label}`;
  const routes = payload.routes || {};
  $('#cellMeta').textContent =
    `${fmt(payload.total_filtered)} documentos · B-NORM ${fmt(routes['B-NORM'])} · C-STRUCT ${fmt(routes['C-STRUCT'])} · ` +
    `overlap ${fmt(routes.overlap)} · texto completo ${fmt(payload.full_text?.available || 0)} ` +
    `(${pct(payload.full_text?.available || 0, payload.total_filtered)})`;
  $('#cellCorpusLink').href = linkTo('/articles.html', {
    ...state.filters,
    domain: payload.domain.key,
    document_class: payload.document_class.key
  });
  const html = (payload.documents || []).map(doc => {
    const meta = [doc.year || 'ano n/d', doc.source_provider || 'fonte n/d',
      doc.doi ? `DOI ${doc.doi}` : '', doc.pmid ? `PMID ${doc.pmid}` : ''].filter(Boolean).join(' · ');
    return `<a class="cell-doc" href="${esc(linkTo('/articles.html', state.filters, { document_id: doc.document_id }))}">` +
      `<div><strong>${esc(doc.title || 'Sem título')}</strong><small>${esc(meta)}</small></div>` +
      `<div class="cell-doc-side">${(doc.routes || []).map(route => `<span class="mini-pill">${esc(route)}</span>`).join('')}` +
      `<span class="mini-pill">${esc(FULL_TEXT_LABELS[doc.full_text_status] || doc.full_text_status)}</span></div></a>`;
  }).join('');
  if (append) $('#cellDocs').insertAdjacentHTML('beforeend', html);
  else $('#cellDocs').innerHTML = html ||
    '<p class="small-state">Nenhum documento nesta célula com os filtros atuais. Isso é um recorte vazio, não ausência de literatura.</p>';
  state.cellOffset = payload.next_offset;
  $('#cellMore').classList.toggle('hidden', payload.next_offset === null || payload.next_offset === undefined);
  $('#cellGuardrail').textContent = payload.guardrail || '';
  if (!append) drawer.focus();
}

async function openCell(domain, documentClass, { append = false } = {}) {
  state.cell = { domain, documentClass };
  const extra = { domain, document_class: documentClass, limit: 50 };
  if (append && state.cellOffset) extra.offset = state.cellOffset;
  const filters = { ...state.filters };
  delete filters.domain;
  delete filters.document_class;
  try {
    const payload = await fetchJson(`/api/evidence-map/cell?${new URLSearchParams({
      ...Object.fromEntries(Object.entries(filters)), ...extra
    })}`);
    renderCell(payload, { append });
  } catch (error) {
    $('#cellDrawer').classList.remove('hidden');
    $('#cellTitle').textContent = 'Célula indisponível';
    $('#cellMeta').textContent = error.message;
    $('#cellDocs').innerHTML = '';
  }
}

function closeCell() {
  state.cell = null;
  state.cellOffset = 0;
  $('#cellDrawer').classList.add('hidden');
}

async function load() {
  renderState($('#mapState'), 'loading', 'Carregando matriz verificada…');
  $('#mapContent').classList.add('hidden');
  try {
    const map = await fetchJson(`/api/evidence-map?${new URLSearchParams(state.filters)}`);
    state.map = map;
    $('#mapHealth').textContent = 'contexto verificado';
    $('#mapHealth').className = 'status-pill ok';
    syncControls(map);
    activeFilterChips($('#activeFilters'), state.filters, key => setFilter(key, ''), clearFilters);
    renderKpis(map);
    renderMatrix(map);
    $('#mapUniverse').textContent = map.universe?.label || '';
    $('#mapIntensityNote').textContent = map.intensity_semantics || '';
    $('#mapProvenance').textContent = provenanceLine(map.provenance) || 'sem proveniência registrada';
    $('#mapState').classList.add('hidden');
    $('#mapContent').classList.remove('hidden');
    if (!map.universe?.filtered_documents) {
      renderState($('#mapState'), 'empty',
        'Nenhum documento neste recorte.',
        'Isso reflete os filtros aplicados. Não significa ausência de literatura.');
    }
  } catch (error) {
    $('#mapHealth').textContent = 'contexto indisponível';
    $('#mapHealth').className = 'status-pill bad';
    const kind = error.status === 503 ? 'partial' : 'error';
    renderState($('#mapState'), kind,
      error.status === 503 ? 'Contexto do Article 1 ainda não materializado.' : 'Evidence Map indisponível.',
      error.message);
  }
}

$('#evidenceMatrix').addEventListener('click', event => {
  const button = event.target.closest('.map-cell');
  if (button && !button.disabled) openCell(button.dataset.domain, button.dataset.class);
});
$('#mapMobile').addEventListener('click', event => {
  const button = event.target.closest('[data-domain]');
  if (button) openCell(button.dataset.domain, button.dataset.class);
});
$('#cellMore').addEventListener('click', () => {
  if (state.cell) openCell(state.cell.domain, state.cell.documentClass, { append: true });
});
$('#closeCell').addEventListener('click', closeCell);
$('#clearFilters').addEventListener('click', clearFilters);
document.querySelectorAll('[data-filter]').forEach(node => {
  node.addEventListener('change', () => setFilter(node.dataset.filter, node.value));
});
window.addEventListener('popstate', () => { state.filters = readFilters(); load(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') closeCell(); });

syncControls(null);
load();
