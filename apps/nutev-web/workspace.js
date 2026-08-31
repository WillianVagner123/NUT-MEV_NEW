// Shared helpers for the NutEV Scientific Intelligence Workspace.
// URL state is the single source of truth for filters, so any view can be copied and shared.

export const $ = selector => document.querySelector(selector);
export const $$ = selector => Array.from(document.querySelectorAll(selector));

export const esc = value => String(value ?? '')
  .replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;').replaceAll("'", '&#39;');

export const fmt = value => new Intl.NumberFormat('pt-BR').format(Number(value || 0));
export const pct = (part, total) => total
  ? `${(100 * Number(part || 0) / Number(total)).toLocaleString('pt-BR', { maximumFractionDigits: 1 })}%`
  : '—';

/** Filter keys that every workspace understands and round-trips through the URL. */
export const FILTER_KEYS = [
  'route', 'domain', 'document_class', 'source_provider',
  'full_text_status', 'year_from', 'year_to', 'review_status'
];

export const FILTER_LABELS = {
  route: 'Rota',
  domain: 'Domínio',
  document_class: 'Tipo documental',
  source_provider: 'Fonte',
  full_text_status: 'Texto completo',
  year_from: 'Ano de',
  year_to: 'Ano até',
  review_status: 'Status de revisão'
};

/** Human-readable values for the shared filter vocabulary, so chips never show raw keys. */
export const FILTER_VALUE_LABELS = {
  route: {
    'B-NORM': 'B-NORM', 'C-STRUCT': 'C-STRUCT',
    overlap: 'Overlap', unrouted: 'Não roteados'
  },
  domain: {
    nutrition_assessment: 'Avaliação nutricional', dietary_counseling: 'Aconselhamento alimentar',
    nutrition_prescription: 'Prescrição nutricional', monitoring_follow_up: 'Monitoramento / seguimento',
    food_skills_competencies: 'Competências alimentares', food_literacy: 'Food literacy',
    social_context: 'Contexto social', food_based_guidance: 'Orientação baseada em alimentos',
    nutrition_care_process: 'Nutrition Care Process', lifestyle_medicine: 'Medicina do Estilo de Vida',
    implementation_practice: 'Implementação na prática', no_operational_domain: 'Sem domínio detectado'
  },
  document_class: {
    food_based_dietary_guideline: 'Guia alimentar / FBDG', clinical_practice_guideline: 'Diretriz clínica',
    consensus_statement: 'Consenso', position_statement: 'Position statement',
    framework_model: 'Framework / modelo', competency_curriculum: 'Competências / currículo',
    evidence_synthesis: 'Síntese de evidência', implementation_evaluation: 'Implementação',
    primary_randomized: 'Ensaio randomizado', primary_observational: 'Observacional',
    primary_qualitative: 'Qualitativo', review: 'Revisão', guidance: 'Guidance',
    unclassified: 'Não classificado'
  },
  source_provider: {
    pubmed: 'PubMed', europepmc: 'Europe PMC', openalex: 'OpenAlex', crossref: 'Crossref',
    doaj: 'DOAJ', semantic_scholar: 'Semantic Scholar', lilacs_bvs_native: 'LILACS / BVS',
    scielo_native: 'SciELO'
  },
  full_text_status: {
    retrieved: 'Recuperado', partial: 'Parcial', unavailable: 'Indisponível',
    not_retrieved: 'Não recuperado', not_attempted: 'Ainda não buscado'
  },
  review_status: {
    NOT_STARTED: 'Não revisado', IN_REVIEW: 'Em revisão', REVIEWED: 'Revisado',
    CONFLICT: 'Conflito', ADJUDICATION_REQUIRED: 'Adjudicação pendente', RESOLVED: 'Resolvido'
  }
};

export const filterValueLabel = (key, value) =>
  FILTER_VALUE_LABELS[key]?.[value] || String(value);

export function readFilters(search = window.location.search) {
  const params = new URLSearchParams(search);
  const filters = {};
  for (const key of FILTER_KEYS) {
    const value = (params.get(key) || '').trim();
    if (value && value !== 'all') filters[key] = value;
  }
  return filters;
}

export function filterParams(filters, extra = {}) {
  const params = new URLSearchParams();
  for (const key of FILTER_KEYS) {
    if (filters[key]) params.set(key, filters[key]);
  }
  for (const [key, value] of Object.entries(extra)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, value);
  }
  return params;
}

/** Replace the URL without adding a history entry, so filters stay copy-pasteable. */
export function writeFilters(filters, { replace = true } = {}) {
  const params = filterParams(filters);
  const query = params.toString();
  const url = `${window.location.pathname}${query ? `?${query}` : ''}`;
  if (replace) window.history.replaceState(filters, '', url);
  else window.history.pushState(filters, '', url);
}

/** Build a link into another workspace carrying the current filters. */
export function linkTo(pathname, filters, extra = {}) {
  const query = filterParams(filters, extra).toString();
  return `${pathname}${query ? `?${query}` : ''}`;
}

export async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' });
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const error = new Error(payload?.message || payload?.error || `${url}: HTTP ${response.status}`);
    error.payload = payload;
    error.status = response.status;
    throw error;
  }
  return payload;
}

/**
 * Render one of the distinguishable component states.
 * "Provider unavailable" and "context stale" are never rendered as "no studies exist".
 */
export function renderState(node, kind, message, detail = '') {
  if (!node) return;
  const kinds = {
    loading: ['', 'Carregando…'],
    empty: ['empty', 'Nenhum documento neste recorte. Isso é um filtro vazio, não ausência de literatura.'],
    partial: ['partial', 'Dados parciais.'],
    stale: ['stale', 'Contexto desatualizado.'],
    error: ['error', 'Falha ao carregar.']
  };
  const [klass, fallback] = kinds[kind] || kinds.error;
  node.className = `state-note ${klass}`.trim();
  node.innerHTML = `<strong>${esc(message || fallback)}</strong>${detail ? `<div>${esc(detail)}</div>` : ''}`;
  node.classList.remove('hidden');
}

export function activeFilterChips(node, filters, onRemove, onClear) {
  if (!node) return;
  const entries = Object.entries(filters).filter(([, value]) => value);
  if (!entries.length) {
    node.innerHTML = '<span>Sem filtros ativos · visão completa do recorte disponível.</span>';
    return;
  }
  node.innerHTML = `<span>Filtros ativos:</span>${entries.map(([key, value]) =>
    `<span class="filter-chip">${esc(FILTER_LABELS[key] || key)}: ${esc(filterValueLabel(key, value))}` +
    `<button type="button" data-remove-filter="${esc(key)}" aria-label="Remover filtro ${esc(FILTER_LABELS[key] || key)}">×</button></span>`
  ).join('')}<button type="button" class="chip-button" data-clear-filters>Limpar tudo</button>`;
  node.querySelectorAll('[data-remove-filter]').forEach(button => {
    button.addEventListener('click', () => onRemove(button.dataset.removeFilter));
  });
  const clear = node.querySelector('[data-clear-filters]');
  if (clear) clear.addEventListener('click', onClear);
}

export function provenanceLine(provenance = {}) {
  const parts = [
    provenance.search_id ? `search ${provenance.search_id}` : '',
    provenance.context_version || '',
    provenance.context_created_at ? `contexto ${provenance.context_created_at}` : '',
    provenance.article_summaries_sha256
      ? `sha ${String(provenance.article_summaries_sha256).slice(0, 12)}…`
      : ''
  ].filter(Boolean);
  return parts.join(' · ');
}
