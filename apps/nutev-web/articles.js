import {
  $, esc, fmt, fetchJson, readFilters, writeFilters, linkTo,
  activeFilterChips, renderState
} from './workspace.js';

const state = { cursor: null, loading: false, selected: null, debounce: null, filters: readFilters(), tab: 'overview' };

const kindLabels = {
  objective: 'Objetivo', method: 'Método / contexto', main_result: 'Resultado principal',
  secondary_result: 'Resultado secundário', conclusion: 'Conclusão', limitation: 'Limitação',
  disclosure: 'Financiamento / conflitos'
};
const classLabels = {
  food_based_dietary_guideline: 'Guia alimentar / FBDG', clinical_practice_guideline: 'Diretriz clínica',
  consensus_statement: 'Consenso', position_statement: 'Position / scientific statement',
  framework_model: 'Framework / modelo operacional', competency_curriculum: 'Competências / currículo',
  implementation_evaluation: 'Implementação / viabilidade', primary_randomized: 'Ensaio randomizado',
  primary_observational: 'Observacional', primary_qualitative: 'Qualitativo',
  evidence_synthesis: 'Síntese de evidência', review: 'Revisão', guidance: 'Diretriz / guidance',
  unclassified: 'Não classificado'
};
const domainLabels = {
  nutrition_assessment: 'Avaliação nutricional', dietary_counseling: 'Aconselhamento alimentar',
  nutrition_prescription: 'Prescrição nutricional', monitoring_follow_up: 'Monitoramento / seguimento',
  food_skills_competencies: 'Competências e habilidades alimentares', food_literacy: 'Food / nutrition literacy',
  social_context: 'Contexto social da alimentação', food_based_guidance: 'Orientação baseada em alimentos',
  nutrition_care_process: 'Nutrition Care Process', lifestyle_medicine: 'Medicina do Estilo de Vida',
  implementation_practice: 'Implementação na prática', no_operational_domain: 'Nenhum domínio detectado'
};
const providerLabels = {
  pubmed: 'PubMed', europepmc: 'Europe PMC', openalex: 'OpenAlex', crossref: 'Crossref',
  doaj: 'DOAJ', semantic_scholar: 'Semantic Scholar', lilacs_bvs_native: 'LILACS/BVS', scielo_native: 'SciELO'
};
const fullTextLabels = {
  retrieved: 'Texto completo', partial: 'Texto parcial', unavailable: 'Sem texto completo',
  not_attempted: 'Ainda não buscado', not_retrieved: 'Não recuperado'
};
const relevanceLabels = {
  high: 'aderência operacional alta', medium: 'aderência operacional média', low: 'aderência operacional baixa'
};
const reviewStatusLabels = {
  NOT_STARTED: 'Não revisado', IN_REVIEW: 'Em revisão', REVIEWED: 'Revisado',
  CONFLICT: 'Conflito', ADJUDICATION_REQUIRED: 'Adjudicação pendente', RESOLVED: 'Resolvido'
};
const decisionLabels = {
  READ: 'Lido', NEEDS_FULL_TEXT: 'Precisa de texto completo',
  NEEDS_SECOND_REVIEWER: 'Precisa de segundo revisor',
  OPERATIONAL_SIGNAL_CONFIRMED: 'Sinal operacional confirmado',
  NO_OPERATIONAL_SIGNAL: 'Sem sinal operacional', DEFER: 'Adiado'
};
const snapshotLabels = {
  objective: 'Objetivo', population: 'População', sample_size: 'Amostra', intervention: 'Intervenção',
  exposure: 'Exposição', comparator: 'Comparador', outcome: 'Outcomes', duration: 'Duração',
  follow_up: 'Seguimento', limitation: 'Limitações'
};
/** Method fields the pipeline does not extract today. Shown as "Not extracted", never invented. */
const NOT_EXTRACTED_METHOD_FIELDS = [
  'Study design', 'Setting', 'Country', 'Data collection', 'Dietary assessment method'
];

const fmtScore = value => value === null || value === undefined || value === ''
  ? '—' : Number(value).toLocaleString('pt-BR', { maximumFractionDigits: 2 });
const tierFromReference = value => (String(value || '').match(/^BANK_([ABCD])_PROCESSING_PRIORITY$/) || [])[1] || '';
const tierLabel = value => tierFromReference(value) ? `Tier ${tierFromReference(value)}` : '';

function currentParams(cursor = null) {
  const params = new URLSearchParams();
  const q = $('#articleQuery').value.trim();
  const tier = $('#tierFilter').value;
  const sort = $('#sortFilter').value || 'relevance';
  const parts = [];
  if (q) parts.push(q);
  if (tier) parts.push(`__nutev_tier:${tier}`);
  if (sort) parts.push(`__nutev_sort:${sort}`);
  if (parts.length) params.set('q', parts.join(' '));
  if (state.filters.source_provider) params.set('source_provider', state.filters.source_provider);
  if (state.filters.document_class) params.set('document_class', state.filters.document_class);
  if (state.filters.full_text_status) params.set('full_text_status', state.filters.full_text_status);
  if (state.filters.route) params.set('route', state.filters.route);
  if (state.filters.domain) params.set('domain', state.filters.domain);
  if (state.filters.review_status) params.set('review_status', state.filters.review_status);
  if (state.filters.year_from) params.set('year_from', state.filters.year_from);
  if (state.filters.year_to) params.set('year_to', state.filters.year_to);
  if (cursor) params.set('cursor', cursor);
  params.set('limit', '50');
  return params;
}

function syncControls() {
  $('#providerFilter').value = state.filters.source_provider || '';
  $('#classFilter').value = state.filters.document_class || '';
  $('#fullTextFilter').value = state.filters.full_text_status || '';
  $('#routeFilter').value = state.filters.route || 'all';
  $('#reviewStatusFilter').value = state.filters.review_status || '';
  $('#yearFrom').value = state.filters.year_from || '';
  $('#yearTo').value = state.filters.year_to || '';
  const domainSelect = $('#domainFilter');
  if (domainSelect.options.length <= 1) {
    for (const [key, label] of Object.entries(domainLabels)) {
      const option = document.createElement('option');
      option.value = key;
      option.textContent = label;
      domainSelect.append(option);
    }
  }
  domainSelect.value = state.filters.domain || '';
  activeFilterChips($('#activeFilters'), state.filters,
    key => { delete state.filters[key]; writeFilters(state.filters); resetAndLoad(); },
    () => { state.filters = {}; writeFilters(state.filters); resetAndLoad(); });
}

function setState(message, type = '') {
  const node = $('#workbenchState');
  node.textContent = message;
  node.className = `workbench-state ${type}`.trim();
}

function articleRow(article) {
  const full = fullTextLabels[article.full_text_status] || article.full_text_status || 'Texto não informado';
  const ids = [article.doi ? `DOI ${article.doi}` : '', article.pmid ? `PMID ${article.pmid}` : ''].filter(Boolean);
  return `<button class="article-row${state.selected === article.document_id ? ' active' : ''}" type="button" data-document-id="${esc(article.document_id)}">
    <div>
      <div class="article-title">${esc(article.title || 'Sem título')}</div>
      <div class="article-meta">
        <span>${esc(article.year || 'ano n/d')}</span>
        <span>${esc(classLabels[article.document_class] || article.document_class || 'tipo n/d')}</span>
        <span>${esc(providerLabels[article.source_provider] || article.source_provider || 'fonte n/d')}</span>
      </div>
      ${ids.length ? `<div class="article-identifiers">${ids.map(id => `<span>${esc(id)}</span>`).join('')}</div>` : ''}
    </div>
    <div class="article-row-side">
      <span class="mini-pill ${article.full_text_status === 'retrieved' ? 'good' : ''}">${esc(full)}</span>
      <span class="mini-pill">contexto IA ${fmt(article.llm_context_chars)} chars</span>
    </div>
  </button>`;
}

async function loadPage({ append = false } = {}) {
  if (state.loading) return;
  state.loading = true;
  $('#loadMore').disabled = true;
  if (!append) setState('Consultando índice…');
  try {
    const cursor = append ? state.cursor : null;
    const response = await fetch(`/api/articles?${currentParams(cursor)}`, { cache: 'no-store' });
    const data = await response.json();
    if (!response.ok) {
      if (data.status === 'not_ready') {
        renderState($('#contextNote'), 'partial',
          'Filtros por domínio, rota, ano ou status humano precisam do contexto do Article 1.', data.message || '');
        setState('Contexto do Article 1 indisponível para este filtro.', 'bad');
        return;
      }
      throw new Error(data.message || data.error || 'Falha ao consultar artigos');
    }
    if (data.status === 'not_ready') {
      $('#articleHealth').textContent = 'índice ainda não criado';
      $('#articleHealth').className = 'status-pill';
      $('#articleCount').textContent = '0';
      $('#workbenchContent').classList.add('hidden');
      setState(data.message || 'Workbench ainda sem índice.', 'bad');
      return;
    }
    if (data.status !== 'ready') throw new Error(data.message || 'Workbench indisponível');
    const healthParts = ['banco'];
    if (data.performance?.server_side_priority_sort) healthParts.push('prioridade');
    if (data.performance?.review_profile_index) healthParts.push('perfil científico');
    $('#articleHealth').textContent = `${healthParts.join(' + ')} verificados`;
    $('#articleHealth').className = 'status-pill ok';
    $('#articleCount').textContent = fmt(data.total_filtered);
    if (data.context_restricted) {
      renderState($('#contextNote'), 'partial',
        'Recorte restrito ao conjunto Tier A perfilado.',
        data.filters?.context?.universe || 'Domínio, rota, ano e status humano só existem para documentos com perfil de revisão.');
    } else {
      $('#contextNote').classList.add('hidden');
    }
    state.cursor = data.next_cursor || null;
    const html = (data.articles || []).map(articleRow).join('');
    if (append) $('#articleList').insertAdjacentHTML('beforeend', html);
    else $('#articleList').innerHTML = html ||
      '<div class="detail-placeholder"><strong>Nenhum artigo neste filtro.</strong><p>Isso é um recorte vazio, não ausência de literatura.</p></div>';
    $('#loadMore').classList.toggle('hidden', !state.cursor);
    $('#workbenchContent').classList.remove('hidden');
    $('#workbenchState').classList.add('hidden');
  } catch (error) {
    $('#articleHealth').textContent = 'erro no índice';
    $('#articleHealth').className = 'status-pill bad';
    $('#workbenchContent').classList.add('hidden');
    setState(error.message, 'bad');
  } finally {
    state.loading = false;
    $('#loadMore').disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Scientific Article Dossier v2
// ---------------------------------------------------------------------------

const DOSSIER_TABS = [
  ['overview', 'Overview'], ['methods', 'Methods'], ['evidence', 'Evidence'],
  ['domains', 'Domains'], ['recommendations', 'Recommendations'],
  ['provenance', 'Provenance'], ['review', 'Human review']
];

const field = (label, value) =>
  `<div class="snapshot-item"><strong>${esc(label)}</strong><span>${value ? esc(value) : 'Not extracted'}</span></div>`;

function overviewTab(data) {
  const card = data.card || {};
  const identity = card.identity || {};
  const reference = card.reference || {};
  const profile = data.review_profile || null;
  const effectiveClass = profile?.primary_document_class || card.document_class;
  const abstract = card.abstract || identity.abstract || '';
  return `<div class="snapshot-grid">
    ${field('Title', identity.title)}
    ${field('Authors', reference.authors || identity.authors)}
    ${field('Year', identity.year)}
    ${field('Journal', reference.journal || identity.journal)}
    ${field('DOI', identity.doi || reference.doi)}
    ${field('PMID', identity.pmid || reference.pmid)}
    ${field('Provider', providerLabels[identity.source_provider] || identity.source_provider)}
    ${field('Document type', classLabels[effectiveClass] || effectiveClass)}
    ${field('Routes', (data.routes || []).join(' · '))}
    ${field('Full-text status', fullTextLabels[card.full_text_status] || card.full_text_status)}
    ${field('Extraction method', card.extraction_method)}
  </div>
  <h4>Abstract</h4>
  ${abstract ? `<p class="abstract">${esc(abstract)}</p>` : '<p class="provenance">Not extracted.</p>'}
  <p class="provenance">Presença no Bank e classe documental não são inclusão científica nem qualidade metodológica.</p>`;
}

function methodsTab(data) {
  const snapshot = (data.card || {}).study_snapshot || {};
  const entries = Object.entries(snapshot)
    .filter(([, values]) => Array.isArray(values) ? values.length : Boolean(values));
  const extracted = entries.map(([key, values]) =>
    field(snapshotLabels[key] || key, (Array.isArray(values) ? values : [values]).join(' · '))).join('');
  const missing = NOT_EXTRACTED_METHOD_FIELDS.map(label => field(label, '')).join('');
  return `<div class="snapshot-grid">${extracted}${missing}</div>
    <p class="provenance">Somente campos efetivamente extraídos são exibidos com valor. "Not extracted" significa que o pipeline atual não extrai esse campo — não que o estudo não o tenha.</p>`;
}

function excerptHtml(excerpt) {
  const reference = excerpt.reference || {};
  const location = [excerpt.section, excerpt.locator].filter(Boolean).join(' · ');
  const ids = [reference.doi ? `DOI ${reference.doi}` : '', reference.pmid ? `PMID ${reference.pmid}` : ''].filter(Boolean).join(' · ');
  return `<article class="quote-card">
    <div class="quote-head"><span class="quote-kind">${esc(kindLabels[excerpt.kind] || excerpt.kind)}</span>
      <span class="mini-pill">candidate evidence excerpt</span><span>${esc(location)}</span></div>
    <blockquote class="source-quote">${esc(excerpt.verbatim_excerpt || '')}</blockquote>
    <div class="provenance">${esc(excerpt.document_id || '')}${ids ? ` · ${esc(ids)}` : ''} · extração ${esc(excerpt.extraction_method || 'n/d')} · SHA ${esc(String(excerpt.excerpt_sha256 || '').slice(0, 12))}…</div>
  </article>`;
}

function resultHtml(result) {
  const numbers = [...(result.effect_measures || []), ...(result.confidence_intervals || []), ...(result.p_values || [])];
  const outcomes = (result.outcomes || []).filter(Boolean);
  return `<article class="result-card ${result.result_kind === 'main_result' ? 'main' : ''}">
    <div class="result-card-head"><strong>${result.result_kind === 'main_result' ? 'Resultado principal' : 'Resultado secundário'}</strong>
      <span class="mini-pill">candidate evidence excerpt</span></div>
    ${outcomes.length ? `<div class="provenance"><strong>Outcome:</strong> ${esc(outcomes.join(' · '))}</div>` : ''}
    ${numbers.length ? `<div class="result-numbers">${numbers.map(value => `<span class="result-number">${esc(value)}</span>`).join('')}</div>` : ''}
    <blockquote class="source-quote">${esc(result.result_text || '')}</blockquote>
    <div class="provenance">Trecho-fonte rastreável · não é EvidenceClaim aceito.</div>
  </article>`;
}

function evidenceTab(data) {
  const results = data.result_bundles || [];
  const excerpts = (data.evidence_excerpts || [])
    .filter(item => !['main_result', 'secondary_result'].includes(item.kind));
  return `<h4>Result bundles</h4>
    ${results.length ? results.map(resultHtml).join('') : '<p class="provenance">Nenhum ResultBundle materializado para este artigo.</p>'}
    <h4>Evidence excerpts</h4>
    ${excerpts.length ? excerpts.map(excerptHtml).join('') : '<p class="provenance">Nenhum trecho adicional selecionado.</p>'}
    <p class="provenance">Todo trecho aqui é <strong>candidate evidence excerpt</strong> de máquina, com proveniência rastreável. Nenhum é EvidenceClaim aceito.</p>`;
}

function domainsTab(data) {
  const profile = data.review_profile;
  if (!profile) return '<p class="provenance">Perfil de revisão ainda não materializado para este artigo.</p>';
  const domains = profile.operational_domains || [];
  const matches = profile.operational_domain_matches || {};
  if (!domains.length) {
    return '<p class="provenance">Nenhum domínio operacional detectado pelas regras atuais. Ausência de sinal não é exclusão.</p>';
  }
  return `<div class="snapshot-grid">${domains.map(domain => {
    const terms = (matches[domain] || []).slice(0, 8);
    return `<div class="snapshot-item"><strong>${esc(domainLabels[domain] || domain)}</strong>` +
      `<span>${terms.length ? esc(terms.join(' · ')) : 'sinal detectado (termos não registrados)'}</span></div>`;
  }).join('')}</div>
  <p class="provenance">Domínios são sinais determinísticos de navegação, com os termos que os acionaram. Não são elegibilidade nem qualidade.</p>
  <p><a class="chip-button" href="${esc(linkTo('/evidence-map.html', { domain: domains[0] }))}">Ver este domínio no Evidence Map →</a></p>`;
}

function recommendationsTab(data) {
  const candidates = (data.evidence_excerpts || []).filter(item => item.kind === 'conclusion');
  return `<h4>Extracted recommendation-like text</h4>
    ${candidates.length
      ? candidates.map(excerptHtml).join('')
      : '<p class="provenance">Not extracted. Nenhum trecho de conclusão foi materializado para este artigo.</p>'}
    <h4>Accepted NutEV recommendation</h4>
    <p class="provenance">Nenhuma. Texto extraído de um artigo nunca é convertido automaticamente em recomendação NutEV; isso exige o workflow canônico de síntese.</p>`;
}

function provenanceTab(data) {
  const card = data.card || {};
  const priority = data.bank_priority || {};
  const machine = data.machine_relevance || {};
  return `<div class="snapshot-grid">
    ${field('Document ID', card.document_id)}
    ${field('Record ID', card.record_id)}
    ${field('Cache key', String(card.cache_key || '').slice(0, 24))}
    ${field('Extractor version', card.extractor_version)}
    ${field('Contexto compacto', `${fmt(card.llm_context_chars)} caracteres`)}
    ${field('Chamadas externas de LLM', String(card.token_cost_policy?.external_llm_calls ?? 0))}
    ${field('Texto integral enviado a LLM', card.token_cost_policy?.full_text_sent_to_llm ? 'sim' : 'não')}
  </div>
  <h4>Machine signals (painel separado)</h4>
  <div class="snapshot-grid">
    ${field('Bank tier', tierLabel(priority.reference_tier))}
    ${field('Bank rank', priority.reference_rank ? `#${fmt(priority.reference_rank)}` : '')}
    ${field('Bank score', fmtScore(priority.reference_score))}
    ${field('Machine relevance', relevanceLabels[machine.band] || machine.band || '')}
    ${field('Machine relevance score', fmtScore(machine.score))}
  </div>
  <p class="provenance">${esc(priority.semantics || '')} ${esc(machine.semantics || '')}</p>
  <p class="provenance">Estes são sinais de máquina para ordem de leitura/processamento e não são julgamento científico: não são decisão humana, elegibilidade, qualidade, risco de viés, certeza ou recomendação.</p>`;
}

function humanReviewTab(review) {
  if (!review) return '<p class="provenance">Carregando estado humano…</p>';
  const state_ = review.review || {};
  const reviewers = state_.reviewers || [];
  const events = review.events || [];
  return `<p><span class="review-status ${esc(state_.status || 'NOT_STARTED')}">${
    esc(reviewStatusLabels[state_.status] || state_.status || 'Não revisado')}</span></p>
    ${reviewers.length ? `<div class="conflict-grid">${reviewers.map(item => `
      <div class="conflict-side">
        <strong>${esc(item.reviewer_id)}</strong>
        <div>${esc(reviewStatusLabels[item.status] || item.status)}${item.decision ? ` · ${esc(decisionLabels[item.decision] || item.decision)}` : ''}</div>
        <div>${esc(item.reason_code || '')}</div>
        <div>${esc(item.reason_text || 'sem justificativa registrada')}</div>
        <small>${esc(item.updated_at || '')}</small>
      </div>`).join('')}</div>`
      : '<p class="provenance">Nenhum revisor humano registrou estado para este documento.</p>'}
    <h4>Trilha de eventos (append-only)</h4>
    ${events.length ? `<div class="cell-doc-list">${events.map(event => `
      <div class="cell-doc"><div><strong>${esc(reviewStatusLabels[event.status] || event.status)}</strong>
        <small>${esc([event.reviewer_id, event.stage, event.route, event.decision && (decisionLabels[event.decision] || event.decision)].filter(Boolean).join(' · '))}</small>
        ${event.reason_text ? `<small>${esc(event.reason_text)}</small>` : ''}</div>
        <div class="cell-doc-side"><small>${esc(event.created_at)}</small>
        ${event.supersedes ? '<span class="mini-pill">substitui evento anterior</span>' : ''}</div></div>`).join('')}</div>`
      : '<p class="provenance">Sem eventos registrados.</p>'}
    <p class="provenance">${esc(review.guardrail || '')}</p>
    <p><a class="chip-button" href="/review.html">Abrir Review Control Center →</a></p>`;
}

function detailHtml(data, review) {
  const card = data.card || {};
  const identity = card.identity || {};
  const reference = card.reference || {};
  const profile = data.review_profile || null;
  const effectiveClass = profile?.primary_document_class || card.document_class;
  const chips = [
    identity.year, classLabels[effectiveClass] || effectiveClass,
    providerLabels[identity.source_provider] || identity.source_provider,
    fullTextLabels[card.full_text_status] || card.full_text_status
  ].filter(Boolean);
  const tabs = DOSSIER_TABS.map(([key, label]) =>
    `<button class="tab-button" type="button" role="tab" data-dossier-tab="${esc(key)}" ` +
    `aria-selected="${state.tab === key}" id="dossier-tab-${esc(key)}" aria-controls="dossier-panel-${esc(key)}">${esc(label)}</button>`
  ).join('');
  const panels = {
    overview: overviewTab(data),
    methods: methodsTab(data),
    evidence: evidenceTab(data),
    domains: domainsTab(data),
    recommendations: recommendationsTab(data),
    provenance: provenanceTab(data),
    review: humanReviewTab(review)
  };
  return `<div class="detail-head">
    <h2>${esc(identity.title || 'Sem título')}</h2>
    <div class="detail-ref">${esc(reference.reference_stub || 'Referência incompleta')}</div>
    <div class="detail-chips">${chips.map(value => `<span class="mini-pill">${esc(value)}</span>`).join('')}</div>
  </div>
  <div class="tab-strip" role="tablist" aria-label="Seções do dossiê">${tabs}</div>
  ${DOSSIER_TABS.map(([key]) =>
    `<section class="detail-section${state.tab === key ? '' : ' hidden'}" role="tabpanel" ` +
    `id="dossier-panel-${esc(key)}" aria-labelledby="dossier-tab-${esc(key)}">${panels[key]}</section>`).join('')}`;
}

function selectDossierTab(tab) {
  state.tab = tab;
  for (const [key] of DOSSIER_TABS) {
    const button = document.querySelector(`[data-dossier-tab="${key}"]`);
    const panel = document.getElementById(`dossier-panel-${key}`);
    if (button) button.setAttribute('aria-selected', String(key === tab));
    if (panel) panel.classList.toggle('hidden', key !== tab);
  }
}

async function openArticle(documentId) {
  state.selected = documentId;
  document.querySelectorAll('.article-row').forEach(row =>
    row.classList.toggle('active', row.dataset.documentId === documentId));
  $('#articleDetail').innerHTML = '<div class="detail-placeholder"><strong>Carregando dossiê…</strong></div>';
  try {
    const [detail, review] = await Promise.allSettled([
      fetchJson(`/api/articles/${encodeURIComponent(documentId)}`),
      fetchJson(`/api/review/document/${encodeURIComponent(documentId)}`)
    ]);
    if (detail.status !== 'fulfilled') throw detail.reason;
    $('#articleDetail').innerHTML = detailHtml(
      detail.value, review.status === 'fulfilled' ? review.value : null);
  } catch (error) {
    $('#articleDetail').innerHTML =
      `<div class="detail-placeholder"><strong>Não foi possível abrir o artigo.</strong><p>${esc(error.message)}</p></div>`;
  }
}

function resetAndLoad() {
  state.cursor = null;
  state.selected = null;
  $('#articleDetail').innerHTML =
    '<div class="detail-placeholder"><div class="placeholder-mark">▤</div><strong>Selecione um artigo</strong><p>O dossiê abre aqui sem tirar você da lista.</p></div>';
  syncControls();
  loadPage();
}

function setFilter(key, value) {
  if (!value || value === 'all') delete state.filters[key];
  else state.filters[key] = String(value);
  writeFilters(state.filters);
  resetAndLoad();
}

const debouncedLoad = () => {
  clearTimeout(state.debounce);
  state.debounce = setTimeout(resetAndLoad, 260);
};

$('#articleQuery').addEventListener('input', debouncedLoad);
['tierFilter', 'sortFilter'].forEach(id => $(`#${id}`).addEventListener('change', resetAndLoad));
$('#providerFilter').addEventListener('change', event => setFilter('source_provider', event.target.value));
$('#classFilter').addEventListener('change', event => setFilter('document_class', event.target.value));
$('#fullTextFilter').addEventListener('change', event => setFilter('full_text_status', event.target.value));
$('#routeFilter').addEventListener('change', event => setFilter('route', event.target.value));
$('#domainFilter').addEventListener('change', event => setFilter('domain', event.target.value));
$('#reviewStatusFilter').addEventListener('change', event => setFilter('review_status', event.target.value));
$('#yearFrom').addEventListener('change', event => setFilter('year_from', event.target.value));
$('#yearTo').addEventListener('change', event => setFilter('year_to', event.target.value));
$('#clearFilters').addEventListener('click', () => {
  $('#articleQuery').value = '';
  $('#tierFilter').value = '';
  $('#sortFilter').value = 'relevance';
  state.filters = {};
  writeFilters(state.filters);
  resetAndLoad();
});
$('#loadMore').addEventListener('click', () => loadPage({ append: true }));
$('#articleList').addEventListener('click', event => {
  const row = event.target.closest('.article-row');
  if (row) openArticle(row.dataset.documentId);
});
$('#articleDetail').addEventListener('click', event => {
  const button = event.target.closest('[data-dossier-tab]');
  if (button) selectDossierTab(button.dataset.dossierTab);
});
window.addEventListener('popstate', () => { state.filters = readFilters(); resetAndLoad(); });

syncControls();
loadPage().then(() => {
  const requested = new URLSearchParams(window.location.search).get('document_id');
  if (requested) openArticle(requested);
});
