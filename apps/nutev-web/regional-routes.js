const $ = selector => document.querySelector(selector);
const state = { profile: null, files: {}, report: null };

function esc(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

function routeStorageKey(routeId) {
  return `nutev_regional_route:${state.profile?.profile_id || 'default'}:${routeId}`;
}

function loadRouteFields(routeId) {
  try {
    return JSON.parse(localStorage.getItem(routeStorageKey(routeId)) || '{}') || {};
  } catch (_error) {
    return {};
  }
}

function saveRouteFields(routeId) {
  const card = document.querySelector(`[data-route-id="${CSS.escape(routeId)}"]`);
  if (!card) return;
  const payload = {
    execution_date: card.querySelector('[data-field="execution_date"]')?.value || '',
    result_count: card.querySelector('[data-field="result_count"]')?.value || '',
    evidence_scope: card.querySelector('[data-field="evidence_scope"]')?.value || '',
    official_confirmed: Boolean(card.querySelector('[data-field="official_confirmed"]')?.checked),
    no_zero_recoding: Boolean(card.querySelector('[data-field="no_zero_recoding"]')?.checked),
    notes: card.querySelector('[data-field="notes"]')?.value || ''
  };
  localStorage.setItem(routeStorageKey(routeId), JSON.stringify(payload));
}

function officialUrl(route) {
  if (route.url_mode === 'bvs_lilacs') {
    const params = new URLSearchParams();
    params.set('lang', 'pt');
    params.set('q', route.query);
    params.append('filter[db_cluster][]', 'LILACS');
    return `${route.official_base_url}?${params.toString()}`;
  }
  if (route.url_mode === 'scielo_subject') {
    const params = new URLSearchParams({ lang: 'pt', q: `subject:(${route.query})` });
    return `${route.official_base_url}?${params.toString()}`;
  }
  return route.official_base_url;
}

async function sha256File(file) {
  const buffer = await file.arrayBuffer();
  const digest = await crypto.subtle.digest('SHA-256', buffer);
  return [...new Uint8Array(digest)].map(value => value.toString(16).padStart(2, '0')).join('');
}

function countRecords(fileName, text) {
  const lower = fileName.toLowerCase();
  if (lower.endsWith('.ris')) {
    return (text.match(/^TY\s{0,2}-\s/gm) || []).length;
  }
  if (lower.endsWith('.bib') || lower.endsWith('.bibtex')) {
    return (text.match(/^@[a-zA-Z]+\s*\{/gm) || []).length;
  }
  if (lower.endsWith('.csv')) {
    const rows = text.split(/\r?\n/).filter(line => line.trim());
    return Math.max(0, rows.length - 1);
  }
  return null;
}

async function inspectFiles(routeId, fileList) {
  const files = [...fileList];
  const metadata = [];
  for (const file of files) {
    let parsedRecords = null;
    try {
      const text = await file.text();
      parsedRecords = countRecords(file.name, text);
    } catch (_error) {
      parsedRecords = null;
    }
    metadata.push({
      name: file.name,
      size_bytes: file.size,
      type: file.type || '',
      sha256: await sha256File(file),
      parsed_records: parsedRecords
    });
  }
  state.files[routeId] = metadata;
  renderFiles(routeId);
}

function renderFiles(routeId) {
  const root = document.querySelector(`[data-file-list="${CSS.escape(routeId)}"]`);
  if (!root) return;
  const files = state.files[routeId] || [];
  if (!files.length) {
    root.innerHTML = '<span class="regional-muted">Nenhum arquivo selecionado nesta sessão.</span>';
    return;
  }
  root.innerHTML = files.map(file => `
    <div class="regional-file">
      <strong>${esc(file.name)}</strong>
      <span>${esc(file.size_bytes)} bytes</span>
      <code>SHA-256 ${esc(file.sha256)}</code>
      <span>${file.parsed_records === null ? 'contagem interna: não aplicável' : `registros detectados no arquivo: ${esc(file.parsed_records)}`}</span>
    </div>
  `).join('');
}

function renderRoute(route, index) {
  const saved = loadRouteFields(route.route_id);
  const url = officialUrl(route);
  return `
    <article class="card regional-card regional-route" data-route-id="${esc(route.route_id)}">
      <div class="section-head">
        <div>
          <h2>2.${index + 1} ${esc(route.route_id)}</h2>
          <p>${esc(route.provider)} · ${esc(route.role)}</p>
        </div>
        <span class="qa-badge warn" data-route-badge>AGUARDANDO</span>
      </div>
      <div class="regional-query-block">
        <div class="regional-query-head"><strong>Query canônica</strong><a class="button-link primary" href="${esc(url)}" target="_blank" rel="noopener noreferrer">Abrir busca oficial</a></div>
        <code>${esc(route.query)}</code>
        <div class="regional-muted">${esc(route.notes)}</div>
      </div>
      <div class="regional-form-grid">
        <label>Data real da execução<input data-field="execution_date" type="date" value="${esc(saved.execution_date || '')}"></label>
        <label>Resultados exibidos pela interface<input data-field="result_count" type="number" min="0" step="1" placeholder="Ex.: 247" value="${esc(saved.result_count || '')}"></label>
        <label>Escopo da evidência anexada
          <select data-field="evidence_scope">
            <option value="">— selecionar —</option>
            <option value="FULL_EXPORT" ${saved.evidence_scope === 'FULL_EXPORT' ? 'selected' : ''}>Exportação completa</option>
            <option value="CHUNKED_EXPORT" ${saved.evidence_scope === 'CHUNKED_EXPORT' ? 'selected' : ''}>Exportação em partes</option>
            <option value="VALIDATION_SAMPLE" ${saved.evidence_scope === 'VALIDATION_SAMPLE' ? 'selected' : ''}>Amostra/exportação de validação</option>
            <option value="SCREEN_CAPTURE" ${saved.evidence_scope === 'SCREEN_CAPTURE' ? 'selected' : ''}>Captura da tela oficial</option>
          </select>
        </label>
        <label>Arquivo(s) de evidência<input data-field="files" type="file" multiple accept=".ris,.csv,.bib,.bibtex,.txt,.html,.htm,.json,.png,.jpg,.jpeg,.pdf"></label>
      </div>
      <label class="regional-check"><input data-field="official_confirmed" type="checkbox" ${saved.official_confirmed ? 'checked' : ''}> <span>Confirmo que a consulta acima foi executada na interface oficial e que a contagem informada foi lida nessa execução.</span></label>
      <label class="regional-check"><input data-field="no_zero_recoding" type="checkbox" ${saved.no_zero_recoding ? 'checked' : ''}> <span>Confirmo que erro, 403, bloqueio ou indisponibilidade não foi registrado como “0 resultados”.</span></label>
      <label>Observações / limites da exportação<textarea data-field="notes" rows="3" placeholder="Ex.: a interface limita exportação a 2.000 registros; foram exportados dois lotes.">${esc(saved.notes || '')}</textarea></label>
      <div class="regional-file-list" data-file-list="${esc(route.route_id)}"></div>
      <ul class="qa-guardrails">${route.required_evidence.map(item => `<li>${esc(item)}</li>`).join('')}</ul>
    </article>
  `;
}

function routeEvidence(route) {
  const card = document.querySelector(`[data-route-id="${CSS.escape(route.route_id)}"]`);
  const countRaw = card.querySelector('[data-field="result_count"]').value;
  const resultCount = countRaw === '' ? null : Number(countRaw);
  const executionDate = card.querySelector('[data-field="execution_date"]').value;
  const scope = card.querySelector('[data-field="evidence_scope"]').value;
  const officialConfirmed = card.querySelector('[data-field="official_confirmed"]').checked;
  const noZeroRecoding = card.querySelector('[data-field="no_zero_recoding"]').checked;
  const notes = card.querySelector('[data-field="notes"]').value.trim();
  const files = state.files[route.route_id] || [];
  const issues = [];
  if (!executionDate) issues.push('Data real da execução ausente.');
  if (resultCount === null || !Number.isInteger(resultCount) || resultCount < 0) issues.push('Contagem oficial ausente ou inválida.');
  if (!scope) issues.push('Escopo da evidência não informado.');
  if (!officialConfirmed) issues.push('Execução na interface oficial não confirmada.');
  if (!noZeroRecoding) issues.push('Guardrail 403/unavailable ≠ zero não confirmado.');
  if (!files.length) issues.push('Nenhum arquivo/captura de evidência selecionado nesta sessão.');
  if (scope && scope !== 'FULL_EXPORT' && !notes) issues.push('Explique a limitação quando a evidência não for exportação completa.');

  const parsedTotal = files.reduce((sum, file) => sum + (Number.isInteger(file.parsed_records) ? file.parsed_records : 0), 0);
  const hasParsed = files.some(file => Number.isInteger(file.parsed_records));
  if (scope === 'FULL_EXPORT' && hasParsed && resultCount !== null && parsedTotal !== resultCount) {
    issues.push(`Exportação marcada como completa, mas o arquivo contém ${parsedTotal} registros e a interface informa ${resultCount}.`);
  }

  return {
    route_id: route.route_id,
    provider: route.provider,
    query: route.query,
    official_search_url: officialUrl(route),
    execution_date: executionDate,
    result_count: resultCount,
    evidence_scope: scope,
    official_execution_confirmed: officialConfirmed,
    unavailable_not_recoded_as_zero: noZeroRecoding,
    notes,
    files,
    parsed_records_total: hasParsed ? parsedTotal : null,
    validation_status: issues.length ? 'REVIEW_REQUIRED' : 'PASS',
    issues
  };
}

function evaluate() {
  const routes = state.profile.routes.map(routeEvidence);
  const pass = routes.every(route => route.validation_status === 'PASS');
  state.report = {
    schema_version: 1,
    created_at: new Date().toISOString(),
    profile_id: state.profile.profile_id,
    gate_id: state.profile.gate_id,
    mode: state.profile.mode,
    formal_search: false,
    prisma_eligible: false,
    routes,
    technical_route_gate: pass ? 'PASS' : 'REVIEW_REQUIRED',
    gf01_candidate_complete: pass,
    freeze_authorized: false,
    guardrail: state.profile.guardrail
  };

  for (const routeResult of routes) {
    const card = document.querySelector(`[data-route-id="${CSS.escape(routeResult.route_id)}"]`);
    const badge = card.querySelector('[data-route-badge]');
    badge.textContent = routeResult.validation_status;
    badge.className = `qa-badge ${routeResult.validation_status === 'PASS' ? 'ok' : 'warn'}`;
  }

  const gate = $('#regionalGate');
  if (pass) {
    gate.className = 'qa-state ok';
    gate.innerHTML = '<strong>Rotas tecnicamente documentadas.</strong> O relatório pode ser incorporado ao CONTROL CENTER como evidência para GF-01. Esta validação ainda não é busca formal e não autoriza freeze.';
  } else {
    gate.className = 'qa-state bad';
    gate.innerHTML = `<strong>GF-01 ainda incompleto.</strong><ul>${routes.flatMap(route => route.issues.map(issue => `<li>${esc(route.route_id)}: ${esc(issue)}</li>`)).join('')}</ul>`;
  }
  $('#downloadRegionalBtn').disabled = false;
}

function downloadReport() {
  if (!state.report) return;
  const text = JSON.stringify(state.report, null, 2) + '\n';
  const blob = new Blob([text], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = `REGIONAL_PREFREEZE_${state.profile.profile_id}_${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

function wireRoute(route) {
  const card = document.querySelector(`[data-route-id="${CSS.escape(route.route_id)}"]`);
  card.querySelectorAll('input:not([type="file"]),select,textarea').forEach(node => {
    node.addEventListener('change', () => saveRouteFields(route.route_id));
    node.addEventListener('input', () => saveRouteFields(route.route_id));
  });
  card.querySelector('[data-field="files"]').addEventListener('change', async event => {
    await inspectFiles(route.route_id, event.target.files || []);
  });
  renderFiles(route.route_id);
}

async function load() {
  $('#regionalHealth').textContent = 'carregando…';
  try {
    const response = await fetch('./regional-route-profiles.json', { cache: 'no-store' });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const payload = await response.json();
    state.profile = payload.profiles?.[0];
    if (!state.profile) throw new Error('Perfil regional ausente.');
    $('#regionalProfileState').className = 'qa-state ok';
    $('#regionalProfileState').innerHTML = `Perfil ativo: <strong>${esc(state.profile.profile_id)}</strong> · gate ${esc(state.profile.gate_id)} · ${esc(state.profile.routes.length)} rotas.`;
    $('#regionalGuardrail').className = 'qa-state';
    $('#regionalGuardrail').innerHTML = `<strong>Guardrail:</strong> ${esc(state.profile.guardrail)}`;
    $('#regionalRoutes').innerHTML = state.profile.routes.map(renderRoute).join('');
    state.profile.routes.forEach(wireRoute);
    $('#regionalHealth').textContent = 'pronto';
    $('#regionalHealth').className = 'status-pill ok';
  } catch (error) {
    $('#regionalProfileState').className = 'qa-state bad';
    $('#regionalProfileState').textContent = `Falha: ${error.message}`;
    $('#regionalHealth').textContent = 'falha';
    $('#regionalHealth').className = 'status-pill bad';
  }
}

$('#refreshRegional').addEventListener('click', load);
$('#evaluateRegionalBtn').addEventListener('click', evaluate);
$('#downloadRegionalBtn').addEventListener('click', downloadReport);
load();
