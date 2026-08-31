import {
  $, esc, fmt, pct, fetchJson, readFilters, writeFilters, linkTo,
  activeFilterChips, renderState, provenanceLine
} from './workspace.js';

// Every number on this dashboard comes from verified runtime aggregates. Nothing is hardcoded,
// and no chart is a dead end: each segment navigates to the documents that produced it.
const state = {
  filters: readFilters(),
  overview: null,
  timeline: null,
  health: null,
  workbench: null,
  radar: null,
  series: ['all', 'B-NORM', 'C-STRUCT']
};

const providerLabels = {
  pubmed: 'PubMed', europepmc: 'Europe PMC', europe_pmc: 'Europe PMC', openalex: 'OpenAlex',
  crossref: 'Crossref', doaj: 'DOAJ', semantic_scholar: 'Semantic Scholar',
  lilacs_bvs: 'LILACS / BVS', lilacs_bvs_native: 'LILACS / BVS', scielo: 'SciELO',
  scielo_native: 'SciELO', scopus: 'Scopus', wos: 'Web of Science'
};
const extractionLabels = {
  xml_text: 'XML', pdf_text: 'PDF', html_text: 'HTML', direct_text: 'Direct text',
  abstract_only: 'Abstract only', unavailable: 'Unavailable'
};
const statusClass = (done, pending = false) => done ? 'done' : pending ? 'pending' : 'locked';

/**
 * PRESS is PASS only when the recorded status *is* PASS. A substring match would read
 * "NOT_YET_RECORDED_AS_PASS" as a pass and silently open a gate the master keeps closed.
 */
const pressIsPass = value => /^(PRESS[ _-]?)?PASS$/.test(String(value || '').trim().toUpperCase());

function setFilter(key, value) {
  if (!value || value === 'all') delete state.filters[key];
  else state.filters[key] = String(value);
  writeFilters(state.filters);
  load();
}

function clearFilters() {
  state.filters = {};
  writeFilters(state.filters);
  load();
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

function syncControls(overview) {
  $('#routeFilter').value = state.filters.route || 'all';
  $('#fullTextFilter').value = state.filters.full_text_status || '';
  $('#yearFrom').value = state.filters.year_from || '';
  $('#yearTo').value = state.filters.year_to || '';
  if (overview) {
    fillSelect($('#classFilter'), (overview.document_classes || []).map(item => [item.key, item.label]), state.filters.document_class);
    fillSelect($('#domainFilter'), (overview.domains || []).map(item => [item.key, item.label]), state.filters.domain);
    fillSelect($('#providerFilter'), (overview.providers || []).map(item => [item.key, providerLabels[item.key] || item.key]), state.filters.source_provider);
  }
  $('#openMap').href = linkTo('/evidence-map.html', state.filters);
}

async function load() {
  renderState($('#dashboardState'), 'loading', 'Carregando estado científico verificado…');
  $('#dashboardState').classList.remove('hidden');
  $('#dashboardContent').classList.add('hidden');
  const query = new URLSearchParams(state.filters).toString();
  const requests = await Promise.allSettled([
    fetchJson('/api/health'),
    fetchJson('/api/articles/status'),
    fetchJson(`/api/dashboard/overview${query ? `?${query}` : ''}`),
    fetchJson(`/api/timeline?${new URLSearchParams({ ...state.filters, series: state.series.join(',') })}`),
    fetchJson('/api/radar')
  ]);
  const [health, workbench, overview, timeline, radar] = requests;
  state.health = health.status === 'fulfilled' ? health.value : null;
  state.workbench = workbench.status === 'fulfilled' ? workbench.value : null;
  state.overview = overview.status === 'fulfilled' ? overview.value : null;
  state.timeline = timeline.status === 'fulfilled' ? timeline.value : null;
  state.radar = radar.status === 'fulfilled' ? radar.value : null;

  $('#dashboardHealth').textContent = state.health?.status === 'ok' ? 'engine conectado' : 'engine parcial';
  $('#dashboardHealth').className = `status-pill ${state.health?.status === 'ok' ? 'ok' : 'bad'}`;

  if (!state.overview && !state.workbench) {
    const reasons = requests.filter(item => item.status === 'rejected')
      .map(item => item.reason?.message).filter(Boolean);
    renderState($('#dashboardState'), 'error', 'Dashboard ainda sem contexto suficiente.',
      `${reasons.join(' · ') || 'Workbench e contexto do Artigo 1 indisponíveis.'} — o painel não usa números demonstrativos.`);
    return;
  }
  if (!state.overview) {
    renderState($('#dashboardState'), 'partial',
      'Contexto do Article 1 indisponível: agregados por domínio, classe e rota não podem ser calculados.',
      overview.status === 'rejected' ? String(overview.reason?.message || '') : '');
  }
  render();
}

function render() {
  const overview = state.overview || {};
  const workbench = state.workbench || {};
  const runtime = overview.runtime || {};
  const formal = overview.formal_search || {};
  const deep = runtime.deepening || {};
  const routes = overview.routes || {};
  const universe = overview.universe || {};

  syncControls(state.overview);
  activeFilterChips($('#activeFilters'), state.filters, key => setFilter(key, ''), clearFilters);

  $('#projectQuestion').textContent = overview.question || 'Article 1 — contexto científico do NutEV';
  const chips = [
    ['Discovery', String(overview.master_status || '').includes('DISCOVERY_CLOSED')],
    ['Tier A deepening', String(deep.status || '').toUpperCase() === 'COMPLETE'],
    ['PRESS', pressIsPass(formal.press_status)],
    ['GF-10', formal.gf10_authorized === true]
  ];
  $('#heroStatuses').innerHTML = chips.map(([label, done], index) =>
    `<span class="state-chip ${done ? 'done' : index < 2 ? 'pending' : 'locked'}">${esc(label)} · ${
      done ? 'complete' : index < 2 ? 'partial' : 'pending'}</span>`).join('');

  const tierA = Number(universe.filtered_documents || 0);
  const fullText = overview.full_text || {};
  const available = Number(fullText.available || 0);
  renderKpis(workbench, tierA, available, routes, universe);
  renderPipeline(overview, workbench);
  renderFunnel(workbench, tierA, routes);
  renderFullText(fullText, tierA);
  renderExtraction(deep.extraction_method_counts || {});
  renderRoutes(routes);
  renderBars($('#classChart'), (overview.document_classes || []).slice(0, 12),
    item => linkTo('/articles.html', { ...state.filters, document_class: item.key }));
  renderBars($('#domainChart'), (overview.domains || []).slice(0, 12),
    item => linkTo('/evidence-map.html', { ...state.filters, domain: item.key }));
  renderTimeline();
  renderProviders(state.radar);
  renderReadiness(formal);
  renderProvenance(overview);

  if (state.overview) $('#dashboardState').classList.add('hidden');
  $('#dashboardContent').classList.remove('hidden');
}

function metricCard(label, value, note, href) {
  const body = `<span class="metric-label">${esc(label)}</span>` +
    `<strong class="metric-value">${esc(value)}</strong><span class="metric-note">${esc(note)}</span>`;
  return href
    ? `<a class="card metric-card drill" href="${esc(href)}">${body}</a>`
    : `<article class="card metric-card">${body}</article>`;
}

function renderKpis(workbench, tierA, available, routes, universe) {
  const bank = Number(workbench?.articles || 0);
  const cards = [
    metricCard('Bank', fmt(bank), 'artigos indexados · presença no Bank ≠ inclusão', '/articles.html'),
    metricCard('Tier A no recorte', fmt(tierA), 'conjunto aprofundado e perfilado · não é a busca formal',
      linkTo('/articles.html', state.filters)),
    metricCard('Cobertura full text', pct(available, tierA), `${fmt(available)} / ${fmt(tierA)} · recuperação ≠ elegibilidade`,
      linkTo('/articles.html', { ...state.filters, full_text_status: 'retrieved' })),
    metricCard('Roteados', fmt(routes.union || 0), 'B-NORM e/ou C-STRUCT', linkTo('/review.html', state.filters)),
    metricCard('B-NORM', fmt(routes['B-NORM'] || 0), 'rota normativa', linkTo('/review.html', { ...state.filters, route: 'B-NORM' })),
    metricCard('C-STRUCT', fmt(routes['C-STRUCT'] || 0), 'rota estrutural', linkTo('/review.html', { ...state.filters, route: 'C-STRUCT' }))
  ];
  $('#kpiGrid').innerHTML = cards.join('');
}

function renderPipeline(overview, workbench) {
  const runtime = overview.runtime || {};
  const formal = overview.formal_search || {};
  const stages = [
    ['Discovery', String(overview.master_status || '').includes('DISCOVERY_CLOSED'), 'harvest fechado'],
    ['Bank', workbench?.status === 'ready', 'índice ativo'],
    ['Deepening', String(runtime.deepening?.status || '').toUpperCase() === 'COMPLETE', 'Tier A'],
    ['Profiles', runtime.review_profiles?.present === true, 'perfil v2'],
    ['Routes', String(runtime.article1_routes?.status || '').toUpperCase() === 'PASS', 'B-NORM/C-STRUCT'],
    ['PRESS', pressIsPass(formal.press_status), 'revisão da estratégia'],
    ['GF-10', formal.gf10_authorized === true, 'gate formal'],
    ['Freeze', formal.query_freeze_complete === true, 'query versionada'],
    ['Formal search', formal.formal_provider_search_executed === true, 'não inferir'],
    ['PRISMA', formal.prisma_search_event_emitted === true, 'evento formal']
  ];
  $('#pipeline').innerHTML = stages.map(([label, done, note], index) =>
    `<div class="pipeline-step ${statusClass(done, index === 5)}"><span class="step-dot"></span>` +
    `<strong>${esc(label)}</strong><small>${esc(done ? 'concluído' : index === 5 ? 'pendente' : index > 5 ? 'bloqueado/pendente' : note)}</small></div>`
  ).join('');
}

function renderFunnel(workbench, tierA, routes) {
  const stages = [
    ['Bank', Number(workbench?.articles || 0), '/articles.html'],
    ['Tier A', tierA, linkTo('/articles.html', state.filters)],
    ['Com texto completo', Number(state.overview?.full_text?.available || 0),
      linkTo('/articles.html', { ...state.filters, full_text_status: 'retrieved' })],
    ['Roteados', Number(routes.union || 0), linkTo('/review.html', state.filters)]
  ];
  $('#funnel').innerHTML = stages.map(([label, value, href], index) =>
    `${index ? '<span class="funnel-arrow">→</span>' : ''}` +
    `<a class="funnel-stage drill" href="${esc(href)}"><strong>${fmt(value)}</strong><span>${esc(label)}</span></a>`
  ).join('');
}

function renderFullText(fullText, tierA) {
  const retrieved = Number(fullText.retrieved || 0);
  const partial = Number(fullText.partial || 0);
  const missing = Math.max(0, tierA - retrieved - partial);
  const total = Math.max(1, tierA);
  const first = 100 * retrieved / total;
  const second = 100 * (retrieved + partial) / total;
  const donut = $('#fullTextDonut');
  donut.style.background =
    `conic-gradient(var(--dashboard-primary) 0 ${first}%,#d6a321 ${first}% ${second}%,#d9dfdc ${second}% 100%)`;
  donut.innerHTML = `<div class="donut-center"><strong>${pct(retrieved + partial, tierA)}</strong><span>retrieved + partial</span></div>`;
  const rows = [
    ['Retrieved', retrieved, '', 'retrieved'],
    ['Partial', partial, 'partial', 'partial'],
    ['Not retrieved / other', missing, 'missing', 'not_retrieved']
  ];
  $('#fullTextLegend').innerHTML = rows.map(([label, value, klass, status]) =>
    `<a class="legend-item drill" href="${esc(linkTo('/articles.html', { ...state.filters, full_text_status: status }))}">` +
    `<span class="legend-dot ${klass}"></span><span>${esc(label)}</span><strong>${fmt(value)}</strong></a>`
  ).join('');
}

/** Bars are links: "which documents form this number?" is always one click away. */
function renderBars(node, entries, hrefFor, labelMap = null, limit = 12) {
  const rows = entries.slice(0, limit);
  const max = Math.max(1, ...rows.map(item => Number(item.documents || 0)));
  node.innerHTML = rows.length
    ? `<div class="chart-stack">${rows.map(item => {
        const label = item.label || labelMap?.[item.key] || item.key;
        const href = hrefFor(item);
        return `<a class="bar-row drill" href="${esc(href)}" title="${esc(label)}">` +
          `<span class="bar-label">${esc(label)}</span>` +
          `<span class="bar-track" aria-hidden="true"><span class="bar-fill" style="width:${
            Math.max(1, 100 * Number(item.documents || 0) / max)}%"></span></span>` +
          `<strong class="bar-value">${fmt(item.documents)}</strong></a>`;
      }).join('')}</div>`
    : '<div class="small-state">Dados ainda não disponíveis neste recorte.</div>';
}

function renderExtraction(counts) {
  const entries = Object.entries(counts)
    .map(([key, value]) => ({ key, label: extractionLabels[key] || key, documents: value }))
    .sort((a, b) => b.documents - a.documents);
  renderBars($('#extractionChart'), entries, () => linkTo('/articles.html', state.filters), null, 8);
}

function renderRoutes(routes) {
  const cards = [
    ['B-NORM', routes['B-NORM'] || 0, 'documentos na rota normativa', 'B-NORM'],
    ['C-STRUCT', routes['C-STRUCT'] || 0, 'documentos na rota estrutural', 'C-STRUCT']
  ];
  const minis = [
    ['overlap', routes.overlap || 0, 'overlap'],
    ['union', routes.union || 0, ''],
    ['unrouted', routes.unrouted || 0, 'unrouted']
  ];
  $('#routesChart').innerHTML = `<div class="route-layout">${
    cards.map(([label, value, note, route]) =>
      `<a class="route-card drill" href="${esc(linkTo('/review.html', { ...state.filters, route }))}">` +
      `<span>${esc(label)}</span><strong>${fmt(value)}</strong><small>${esc(note)}</small></a>`).join('')
  }<div class="route-overlap">${
    minis.map(([label, value, route]) =>
      `<a class="route-mini drill" href="${esc(linkTo('/review.html', route ? { ...state.filters, route } : state.filters))}">` +
      `<strong>${fmt(value)}</strong><span>${esc(label)}</span></a>`).join('')
  }</div></div>`;
}

function renderTimeline() {
  const timeline = state.timeline;
  const chart = $('#timelineChart');
  const seriesNode = $('#timelineSeries');
  if (!timeline) {
    chart.innerHTML = '<div class="small-state">Série temporal indisponível neste recorte.</div>';
    $('#timelineAxis').innerHTML = '';
    seriesNode.innerHTML = '';
    return;
  }
  seriesNode.innerHTML = (timeline.available_series || []).map(item =>
    `<button type="button" class="chip-button${state.series.includes(item.key) ? ' active' : ''}" ` +
    `data-series="${esc(item.key)}" aria-pressed="${state.series.includes(item.key)}">${esc(item.label)}</button>`
  ).join('');

  const years = timeline.years || [];
  if (!years.length) {
    chart.innerHTML = '<div class="small-state">Ano de publicação ainda não disponível neste recorte.</div>';
    $('#timelineAxis').innerHTML = '';
    $('#timelineNote').textContent = timeline.guardrail || '';
    return;
  }
  const primary = (timeline.series || [])[0] || { points: [] };
  const max = Math.max(1, ...(timeline.series || []).flatMap(item => item.points.map(point => point.documents)));
  chart.innerHTML = primary.points.map(point => {
    const tooltip = (timeline.series || [])
      .map(item => `${item.label}: ${item.points.find(entry => entry.year === point.year)?.documents ?? 0}`)
      .join(' · ');
    return `<a class="timeline-bar drill" style="height:${Math.max(3, 100 * point.documents / max)}%" ` +
      `href="${esc(linkTo('/articles.html', { ...state.filters, year_from: point.year, year_to: point.year }))}" ` +
      `title="${esc(`${point.year} — ${tooltip}`)}" aria-label="${esc(`${point.year}: ${tooltip}`)}"></a>`;
  }).join('');
  $('#timelineAxis').innerHTML =
    `<span>${years[0]}</span><span>${years[Math.floor(years.length / 2)]}</span><span>${years.at(-1)}</span>`;
  const legend = (timeline.series || []).map(item => `${item.label} ${fmt(item.documents)}`).join(' · ');
  $('#timelineNote').textContent =
    `${legend}${timeline.undated_documents ? ` · ${fmt(timeline.undated_documents)} sem ano` : ''} — ${timeline.guardrail || ''}`;
}

function renderProviders(radar) {
  const providers = radar?.providers || [];
  $('#providerBoard').innerHTML = providers.length
    ? providers.map(item => {
        const stateValue = item.state || 'unknown';
        const details = Object.entries(item.status_counts || {})
          .map(([key, value]) => `${key} ${value}`).join(' · ') || 'sem execução registrada';
        return `<div class="provider-line"><div><strong>${esc(providerLabels[item.provider] || item.provider)}</strong>` +
          `<small>${esc(details)}</small></div><span class="provider-state ${esc(stateValue)}">${esc(stateValue)}</span></div>`;
      }).join('')
    : '<div class="small-state">Estado operacional de providers indisponível neste snapshot. Gap de provider não significa ausência de literatura.</div>';
}

function renderReadiness(formal) {
  const rows = [
    ['PRESS', pressIsPass(formal.press_status), 'PASS', 'PENDING'],
    ['GF-10', formal.gf10_authorized === true, 'AUTHORIZED', 'LOCKED'],
    ['Query freeze', formal.query_freeze_complete === true, 'COMPLETE', 'NOT COMPLETE'],
    ['Formal search', formal.formal_provider_search_executed === true, 'EXECUTED', 'NOT EXECUTED']
  ];
  $('#readinessGrid').innerHTML = rows.map(([label, done, yes, no]) =>
    `<div class="readiness-item"><span>${esc(label)}</span><strong>${esc(done ? yes : no)}</strong></div>`).join('');
  $('#nextAction').innerHTML =
    `<strong>NEXT REQUIRED ACTION</strong><br>${esc(formal.next_gate || 'Verificar o master da busca antes de avançar.')}`;
}

function renderProvenance(overview) {
  const provenance = overview.provenance || {};
  const items = [
    ['Search ID', provenance.search_id || '—'],
    ['Context version', provenance.context_version || '—'],
    ['Context created', provenance.context_created_at || '—'],
    ['Article summaries SHA-256', provenance.article_summaries_sha256 || '—'],
    ['Workbench SHA-256', provenance.workbench_database_sha256 || '—'],
    ['Manifest status', provenance.context_status || '—']
  ];
  $('#provenance').innerHTML = items.map(([label, value]) =>
    `<div class="provider-line"><div><strong>${esc(label)}</strong><small>${esc(value)}</small></div></div>`).join('') +
    `<div class="small-state">${esc(provenanceLine(provenance))}</div>`;
}

$('#refreshDashboard').addEventListener('click', load);
$('#clearFilters').addEventListener('click', clearFilters);
document.querySelectorAll('[data-filter]').forEach(node => {
  node.addEventListener('change', () => setFilter(node.dataset.filter, node.value));
});
$('#timelineSeries').addEventListener('click', async event => {
  const button = event.target.closest('[data-series]');
  if (!button) return;
  const key = button.dataset.series;
  const next = state.series.includes(key)
    ? state.series.filter(value => value !== key)
    : [...state.series, key];
  if (!next.length) return;
  if (next.length > (state.timeline?.max_series || 6)) return;
  state.series = next;
  try {
    state.timeline = await fetchJson(
      `/api/timeline?${new URLSearchParams({ ...state.filters, series: state.series.join(',') })}`);
  } catch {
    state.timeline = null;
  }
  renderTimeline();
});
$('#presentationToggle').addEventListener('click', () => {
  document.body.classList.toggle('presentation-mode');
  $('#presentationToggle').textContent = document.body.classList.contains('presentation-mode')
    ? 'Sair da apresentação' : 'Presentation View';
});
window.addEventListener('popstate', () => { state.filters = readFilters(); load(); });

syncControls(null);
load();
