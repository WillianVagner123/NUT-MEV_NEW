from __future__ import annotations

from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
TESTS = ROOT / "nutev_tests"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def replace_once(path: Path, old: str, new: str) -> None:
    text = read(path)
    if old not in text:
        raise RuntimeError(f"{path}: anchor not found: {old[:100]!r}")
    write(path, text.replace(old, new, 1))


# 1. One user action from home -> search execution.
app = WEB / "app.js"
text = read(app)
replace_anchor = "  renderConceptBuilder(false);\n  try{\n"
if replace_anchor not in text:
    raise RuntimeError("app.js: init anchor missing")
text = text.replace(replace_anchor, "  renderConceptBuilder(false);\n  let engineReady=false;\n  try{\n", 1)
old_health = "    $('#health').textContent=health.status==='ok'?'engine conectado':'engine indisponível';$('#health').classList.add(health.status==='ok'?'ok':'bad');state.providers=providers.providers||[];renderProviders();renderExactQueryBuilder();"
new_health = "    engineReady=health.status==='ok';$('#health').textContent=engineReady?'engine conectado':'engine indisponível';$('#health').classList.add(engineReady?'ok':'bad');state.providers=providers.providers||[];renderProviders();renderExactQueryBuilder();"
if old_health not in text:
    raise RuntimeError("app.js: health anchor missing")
text = text.replace(old_health, new_health, 1)
old_params = "  const params=new URLSearchParams(location.search);if(params.get('view')==='history')switchView('history');if(params.get('q')){$('#question').value=params.get('q');switchView('search')}"
new_params = "  const params=new URLSearchParams(location.search);\n  if(params.get('view')==='history'){switchView('history');return}\n  const initialQuery=(params.get('q')||'').trim();\n  if(initialQuery){$('#question').value=initialQuery;switchView('search');if(engineReady&&state.providers.length)await runSearch()}"
if old_params not in text:
    raise RuntimeError("app.js: query-param anchor missing")
text = text.replace(old_params, new_params, 1)
text = text.replace("<strong>Iniciando Busca global exaustiva…</strong>", "<strong>Iniciando cobertura máxima disponível…</strong>")
text = text.replace("'Busca global exaustiva · '", "'Cobertura máxima disponível · '")
old_conf = "const CONFIDENCE_LABELS={high:'confiança alta',medium:'confiança média',low:'sinal insuficiente'};"
new_conf = "const CONFIDENCE_LABELS={high:'alta',medium:'média',low:'sinal insuficiente'};"
if old_conf not in text:
    raise RuntimeError("app.js: confidence anchor missing")
text = text.replace(old_conf, new_conf, 1)
result_re = re.compile(r"function resultCard\(r\)\{.*?\}\nasync function renderHistory", re.S)
match = result_re.search(text)
if not match:
    raise RuntimeError("app.js: resultCard block missing")
new_result = r'''function rankingWhy(r){const query=Number(r.query_relevance_score||0),priority=Number(r.nutev_priority_score||0);const parts=[];if(Number.isFinite(query))parts.push(`relevância para a consulta ${query.toFixed(1)}`);if(Number.isFinite(priority))parts.push(`prioridade NutEV ${priority.toFixed(1)}`);return parts}
function resultCard(r){const href=r.doi?`https://doi.org/${String(r.doi).replace(/^https?:\/\/doi\.org\//i,'').replace(/^doi:/i,'')}`:(r.url||'');const id=r.pmid?`PMID ${r.pmid}`:(r.doi?`DOI ${r.doi}`:'');const c=r.search_classification||{};const klass=inferredClass(r);const confidence=c.confidence||'low';const taxonomy=c.taxonomy_primary||r.taxonomy_primary||'';const reasons=whyMatched(r);const rankingReasons=rankingWhy(r);const signals=(c.signals||[]).map(x=>`${x.field}: ${x.value}`);return `<article class="result-card"><div class="result-top"><div class="rank">${esc(r.reference_rank)}</div><div style="flex:1"><h3>${esc(r.title||'(sem título)')}</h3><div class="meta"><span>${esc(r.journal||'—')}</span><span>${esc(r.year||'—')}</span><span>${esc(r.source_provider||r.source||'')}</span><span>${esc(id)}</span></div><div class="classification-row"><span class="class-pill">${esc(CLASS_LABELS[klass]||klass)}</span><span class="confidence-pill">Confiança da classificação: ${esc(CONFIDENCE_LABELS[confidence]||confidence)}</span>${taxonomy?`<span class="taxonomy-pill">${esc(taxonomyLabel(taxonomy))}</span>`:''}</div></div><div class="score"><strong>${Number(r.reference_score||0).toFixed(1)}</strong><span>ranking final</span></div></div>${reasons.length?`<div class="why-match"><strong>Por que foi recuperado</strong><span>${reasons.map(esc).join(' · ')}</span></div>`:''}${rankingReasons.length?`<div class="why-match"><strong>Por que está nesta posição</strong><span>${rankingReasons.map(esc).join(' · ')}</span></div>`:''}${signals.length?`<div class="result-signals"><strong>Como foi classificado:</strong> ${signals.map(esc).join(' · ')}</div>`:''}${r.abstract?`<div class="abstract">${esc(r.abstract).slice(0,900)}${String(r.abstract).length>900?'…':''}</div>`:''}${href?`<div class="links"><a href="${esc(href)}" target="_blank" rel="noopener noreferrer">Abrir fonte ↗</a></div>`:''}</article>`}
async function renderHistory'''
text = text[: match.start()] + new_result + text[match.end() :]
write(app, text)

# 2. Query-conditioned ranking, while preserving old NutEV priority as a secondary signal.
adapter = WEB / "search_adapter.py"
text = read(adapter)
score_re = re.compile(r"def _score_rows\(.*?\n\n\ndef _read_jsonl", re.S)
match = score_re.search(text)
if not match:
    raise RuntimeError("search_adapter.py: score block missing")
new_score = '''def _query_relevance_score(classification: dict[str, Any]) -> float:
    match = classification.get("query_match") or {}
    considered = {str(value) for value in (match.get("terms_considered") or []) if str(value)}
    title_hits = {str(value) for value in (match.get("title_hits") or []) if str(value)}
    abstract_hits = {str(value) for value in (match.get("abstract_hits") or []) if str(value)}
    if not considered:
        return 0.0
    covered = (title_hits | abstract_hits) & considered
    coverage = len(covered) / max(1, len(considered))
    score = len(title_hits & considered) * 18.0 + len(abstract_hits & considered) * 6.0 + coverage * 25.0
    return round(min(100.0, score), 2)


def _score_rows(rows: list[dict[str, Any]], *, query: str | None = None) -> list[dict[str, Any]]:
    taxonomy, taxonomy_meta = load_canonical_taxonomy(REPO_ROOT / "config")
    profile = _read_profile()
    focus_keywords = list(profile.get("focus_keywords") or [])
    provider_weights = dict(profile.get("provider_weights") or {})
    guardrails = dict(profile.get("guardrails") or {})
    primary_dimension_order = list((taxonomy_meta or {}).get("primary_dimension_order") or [])

    ranked: list[dict[str, Any]] = []
    for row in rows:
        scored = score_record(
            row,
            taxonomy,
            focus_keywords,
            provider_weights,
            guardrails=guardrails,
            primary_dimension_order=primary_dimension_order,
        )
        effective_query = str(scored.get("provider_query") or query or "").strip()
        classification = classify_search_record(scored, query=effective_query)
        query_relevance = _query_relevance_score(classification)
        nutev_priority = max(0.0, min(float(scored.get("reference_score") or 0.0), 100.0))
        scored["search_classification"] = classification
        scored["query_relevance_score"] = query_relevance
        scored["nutev_priority_score"] = round(nutev_priority, 2)
        scored["ranking_score_breakdown"] = {
            "query_relevance": query_relevance,
            "nutev_priority": round(nutev_priority, 2),
            "query_weight": 0.8,
            "nutev_priority_weight": 0.2,
        }
        scored["reference_score"] = round(query_relevance * 0.8 + nutev_priority * 0.2, 2)
        ranked.append(scored)
    ranked.sort(
        key=lambda item: (
            -float(item.get("reference_score") or 0.0),
            -float(item.get("query_relevance_score") or 0.0),
            -float(item.get("nutev_priority_score") or 0.0),
            str(item.get("title") or "").casefold(),
        )
    )
    for index, item in enumerate(ranked, start=1):
        item["reference_rank"] = index
    return ranked


def _read_jsonl'''
text = text[: match.start()] + new_score + text[match.end() :]
write(adapter, text)

# 3. Ignore provider-query syntax words in user-facing overlap explanations.
classifier = ROOT / "src" / "nutev" / "search" / "classification.py"
text = read(classifier)
anchor = '    "which",\n'
if anchor not in text:
    raise RuntimeError("classification.py: stopword anchor missing")
extra = ''.join(f'    "{value}",\n' for value in ("or", "not", "title", "abstract", "mesh", "decs", "title_abs", "tw", "mh"))
for value in ("or", "not", "title", "abstract", "mesh", "decs", "title_abs", "tw", "mh"):
    if f'    "{value}",\n' in text:
        extra = extra.replace(f'    "{value}",\n', "")
text = text.replace(anchor, anchor + extra, 1)
write(classifier, text)

# 4. Public navigation/glossary only expose generic search product surfaces.
product = WEB / "product-ui.js"
text = read(product)
nav_re = re.compile(r"const NAV_GROUPS=\[.*?\n\]\n\nconst GLOSSARY=\[.*?\n\]", re.S)
match = nav_re.search(text)
if not match:
    raise RuntimeError("product-ui.js: nav/glossary block missing")
new_nav = '''const NAV_GROUPS=[
  {label:'Descoberta',items:[
    {key:'dashboard',href:'/',icon:'⌂',label:'Início'},
    {key:'search',href:'/search.html',icon:'⌕',label:'Buscar artigos'},
    {key:'articles',href:'/articles.html',icon:'▤',label:'Biblioteca'}
  ]},
  {label:'Sistema',items:[
    {key:'history',href:'/search.html?view=history',icon:'◷',label:'Minhas buscas'},
    {key:'advanced',href:'/advanced.html',icon:'⚙',label:'Laboratório avançado'}
  ]}
]

const GLOSSARY=[
  ['Busca progressiva','Execução que consulta provedores em etapas e preserva o estado de cada fonte. Uma fonte indisponível não é tratada como zero resultados.'],
  ['Provider','Fonte externa consultada pelo NutEV, como PubMed, Europe PMC, OpenAlex, Crossref, DOAJ, SciELO ou LILACS/BVS.'],
  ['Deduplicação','Processo que consolida registros equivalentes vindos de fontes diferentes sem apagar a proveniência de origem.'],
  ['Ranking','Ordem de apresentação condicionada à consulta, combinando relevância para a busca e prioridade operacional NutEV. Não significa qualidade, certeza ou recomendação.'],
  ['Proveniência','Rastro que liga um registro à fonte, consulta, versão e contexto em que foi recuperado e processado.']
]'''
text = text[: match.start()] + new_nav + text[match.end() :]
old_active = "  if(path==='/articles.html'||path==='/evidence.html')return 'articles'\n  if(path==='/evidence-map.html')return 'map'\n  if(path==='/radar.html')return 'radar'\n  if(path==='/ask.html')return 'ask'\n  if(path==='/advanced.html')return 'advanced'"
new_active = "  if(path==='/articles.html')return 'articles'\n  if(['/evidence.html','/evidence-map.html','/radar.html','/ask.html'].includes(path))return 'advanced'\n  if(path==='/advanced.html')return 'advanced'"
if old_active not in text:
    raise RuntimeError("product-ui.js: active-nav anchor missing")
text = text.replace(old_active, new_active, 1)
text = text.replace('placeholder="Ex.: PRESS, ResultBundle, PRISMA"', 'placeholder="Ex.: provider, ranking, proveniência"')
write(product, text)

# 5. Home only advertises generic product flows.
home = WEB / "index.html"
text = read(home)
home_re = re.compile(r'<section class="home-grid" aria-label="Áreas principais">.*?</section>', re.S)
if not home_re.search(text):
    raise RuntimeError("index.html: home grid missing")
text = home_re.sub('''<section class="home-grid" aria-label="Áreas principais">
        <a class="card home-action" href="/search.html"><strong>⌕ Buscar artigos</strong><span>Consulta múltiplas fontes, deduplica, ranqueia e explica os resultados.</span></a>
        <a class="card home-action" href="/articles.html"><strong>▤ Biblioteca</strong><span>Explore artigos guardados por classe documental, fonte, texto completo e prioridade.</span></a>
        <a class="card home-action" href="/search.html?view=history"><strong>◷ Minhas buscas</strong><span>Reabra buscas persistidas e continue a exploração sem perder o contexto.</span></a>
      </section>''', text, count=1)
write(home, text)

# 6. Article-1-specific explorers remain available but hibernated/noindexed.
legacy_pages = ("evidence.html", "evidence-map.html", "radar.html", "ask.html")
for name in legacy_pages:
    path = WEB / name
    text = read(path)
    if '<meta name="robots" content="noindex,nofollow">' not in text:
        head_anchor = '<meta name="color-scheme" content="light">'
        if head_anchor not in text:
            raise RuntimeError(f"{name}: head anchor missing")
        text = text.replace(head_anchor, head_anchor + '\n  <meta name="robots" content="noindex,nofollow">', 1)
    text, count = re.subn(r'<nav(?:\s[^>]*)?>.*?</nav>', '<nav aria-label="Navegação principal"></nav>', text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{name}: sidebar nav count={count}")
    if 'src="./product-ui.js"' not in text:
        text = text.replace('</body>', '  <script type="module" src="./product-ui.js"></script>\n</body>', 1)
    write(path, text)

advanced = WEB / "advanced.html"
text = read(advanced)
legacy_anchor = '<div class="advanced-links"><a href="/scientific-dashboard.html">Abrir painel científico →</a><a href="/quality.html">Quality Observatory →</a></div>'
legacy_links = '<div class="advanced-links"><a href="/scientific-dashboard.html">Abrir painel científico →</a><a href="/evidence.html">Evidence Explorer do Artigo 1 →</a><a href="/evidence-map.html">Evidence Map do Artigo 1 →</a><a href="/radar.html">Evidence Radar do Artigo 1 →</a><a href="/ask.html">Ask NutEV do Artigo 1 →</a><a href="/quality.html">Quality Observatory →</a></div>'
if legacy_anchor not in text:
    raise RuntimeError("advanced.html: Article 1 links anchor missing")
text = text.replace(legacy_anchor, legacy_links, 1)
write(advanced, text)

robots = WEB / "robots.txt"
text = read(robots)
for item in ("/evidence.html", "/evidence-map.html", "/radar.html", "/ask.html"):
    line = f"Disallow: {item}\n"
    if line not in text:
        text = text.replace("Disallow: /api/\n", line + "Disallow: /api/\n", 1)
write(robots, text)

sitemap = WEB / "sitemap.xml"
write(sitemap, '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://nutev.mindsperformance.com.br/</loc></url>
  <url><loc>https://nutev.mindsperformance.com.br/search.html</loc></url>
  <url><loc>https://nutev.mindsperformance.com.br/articles.html</loc></url>
</urlset>
''')

secure = WEB / "secure_server.py"
text = read(secure)
marker = 'NOINDEX_EXACT_PATHS = {\n'
if marker not in text:
    raise RuntimeError("secure_server.py: NOINDEX set missing")
for item in ("/evidence.html", "/evidence-map.html", "/radar.html", "/ask.html"):
    if f'    "{item}",\n' not in text:
        text = text.replace(marker, marker + f'    "{item}",\n', 1)
write(secure, text)

# 7. Update tests that intentionally encoded the old public product boundary.
shell_test = TESTS / "test_product_shell_remediation.py"
text = read(shell_test)
text = text.replace('        "radar.html",\n        "review-qa.html",', '        "evidence.html",\n        "evidence-map.html",\n        "radar.html",\n        "ask.html",\n        "review-qa.html",', 1)
nav_re = re.compile(r'def test_canonical_navigation_is_search_classification_first\(\) -> None:.*?\n\ndef test_search_and_home_present', re.S)
if not nav_re.search(text):
    raise RuntimeError("test_product_shell_remediation.py: nav contract missing")
text = nav_re.sub('''def test_canonical_navigation_is_search_classification_first() -> None:
    script = read(WEB / "product-ui.js")
    nav = script.split("const NAV_GROUPS=", 1)[1].split("const GLOSSARY=", 1)[0]
    for label in ("Início", "Buscar artigos", "Biblioteca", "Minhas buscas", "Laboratório avançado"):
        assert label in nav
    for hibernated in ("Mapa de evidências", "Radar", "Perguntar ao corpus", "PRESS", "Review Control", "Review Routes", "Validação científica", "QA"):
        assert hibernated not in nav
    assert "normalizeNavigation" in script
    assert 'aria-current="page"' in script
    assert "AI Context" not in nav


def test_search_and_home_present''', text, count=1)
gloss_re = re.compile(r'def test_glossary_explains_scientific_terms_without_rewriting_raw_code\(\) -> None:.*?\n\ndef test_strategy_pages', re.S)
if not gloss_re.search(text):
    raise RuntimeError("test_product_shell_remediation.py: glossary contract missing")
text = gloss_re.sub('''def test_glossary_explains_search_terms_without_leaking_hibernated_workflows() -> None:
    script = read(WEB / "product-ui.js")
    css = read(WEB / "product-ui.css")
    glossary = script.split("const GLOSSARY=", 1)[1].split("const STRATEGY_FLOW_STORAGE_KEY", 1)[0]
    for term in ("Busca progressiva", "Provider", "Deduplicação", "Ranking", "Proveniência"):
        assert term in glossary
    for hidden in ("PRESS", "PRISMA", "EvidenceClaim", "EvidenceSet", "Freeze"):
        assert hidden not in glossary
    assert "code,pre,script,style,textarea" in script
    assert "glossary-trigger" in css
    assert "glossary-dialog" in css


def test_strategy_pages''', text, count=1)
write(shell_test, text)

indexing = TESTS / "test_public_indexing_policy.py"
text = read(indexing)
text = text.replace('        f"{DOMAIN}/articles.html",\n        f"{DOMAIN}/radar.html",\n', '        f"{DOMAIN}/articles.html",\n', 1)
for item in ("/evidence.html", "/evidence-map.html", "/radar.html", "/ask.html"):
    if f'        "{item}",\n' not in text:
        text = text.replace('        "/api/",\n', f'        "{item}",\n        "/api/",\n', 1)
secure_anchor = "        '\"/regional-routes.html\"',\n"
secure_extra = "        '\"/evidence.html\"',\n        '\"/evidence-map.html\"',\n        '\"/radar.html\"',\n        '\"/ask.html\"',\n"
if secure_extra not in text:
    if secure_anchor not in text:
        raise RuntimeError("test_public_indexing_policy.py: server assertion anchor missing")
    text = text.replace(secure_anchor, secure_anchor + secure_extra, 1)
write(indexing, text)

radar_test = TESTS / "test_radar_web_contract.py"
text = read(radar_test)
old = '''def test_radar_is_first_class_in_main_navigation() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    radar = (WEB / "radar.html").read_text(encoding="utf-8")
    assert 'href="/radar.html"' in index
    assert "Evidence Radar" in index
'''
new = '''def test_radar_is_hibernated_under_advanced_laboratory() -> None:
    index = (WEB / "index.html").read_text(encoding="utf-8")
    advanced = (WEB / "advanced.html").read_text(encoding="utf-8")
    radar = (WEB / "radar.html").read_text(encoding="utf-8")
    assert 'href="/radar.html"' not in index
    assert 'href="/radar.html"' in advanced
    assert '<meta name="robots" content="noindex,nofollow">' in radar
'''
if old not in text:
    raise RuntimeError("test_radar_web_contract.py: old nav test missing")
write(radar_test, text.replace(old, new, 1))

map_test = TESTS / "test_evidence_map_ui.py"
text = read(map_test)
old = '''def test_main_navigation_surfaces_evidence_map() -> None:
    home = read("index.html")
    explorer = read("evidence.html")

    assert 'href="/evidence-map.html"' in home
    assert 'href="/evidence-map.html"' in explorer
'''
new = '''def test_evidence_map_is_hibernated_under_advanced_laboratory() -> None:
    home = read("index.html")
    advanced = read("advanced.html")
    explorer = read("evidence.html")
    map_html = read("evidence-map.html")

    assert 'href="/evidence-map.html"' not in home
    assert 'href="/evidence-map.html"' in advanced
    assert '<meta name="robots" content="noindex,nofollow">' in explorer
    assert '<meta name="robots" content="noindex,nofollow">' in map_html
'''
if old not in text:
    raise RuntimeError("test_evidence_map_ui.py: old nav test missing")
write(map_test, text.replace(old, new, 1))

p0 = TESTS / "test_search_first_product_p0.py"
write(p0, '''from __future__ import annotations

from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "nutev-web"
if str(WEB) not in sys.path:
    sys.path.insert(0, str(WEB))

import search_adapter


def read(name: str) -> str:
    return (WEB / name).read_text(encoding="utf-8")


def test_home_query_runs_immediately_after_search_page_initializes() -> None:
    app = read("app.js")
    assert "if(params.get('view')==='history'){switchView('history');return}" in app
    assert "if(engineReady&&state.providers.length)await runSearch()" in app


def test_primary_shell_contains_only_generic_search_product_surfaces() -> None:
    script = read("product-ui.js")
    nav = script.split("const NAV_GROUPS=", 1)[1].split("const GLOSSARY=", 1)[0]
    for href in ("/evidence.html", "/evidence-map.html", "/radar.html", "/ask.html"):
        assert href not in nav
    home = read("index.html")
    for href in ('href="/evidence-map.html"', 'href="/radar.html"', 'href="/ask.html"'):
        assert href not in home


def test_article1_exploration_surfaces_are_noindexed_and_use_canonical_shell() -> None:
    for name in ("evidence.html", "evidence-map.html", "radar.html", "ask.html"):
        html = read(name)
        assert '<meta name="robots" content="noindex,nofollow">' in html
        assert 'src="./product-ui.js"' in html
        nav = re.search(r'<nav[^>]*>(.*?)</nav>', html, re.S)
        assert nav and "PRESS" not in nav.group(1) and "Review" not in nav.group(1)


def test_query_relevance_dominates_legacy_nutev_priority(monkeypatch) -> None:
    monkeypatch.setattr(search_adapter, "load_canonical_taxonomy", lambda _path: ({}, {}))
    monkeypatch.setattr(search_adapter, "_read_profile", lambda: {"focus_keywords": [], "provider_weights": {}, "guardrails": {}})
    monkeypatch.setattr(search_adapter, "score_record", lambda row, *_args, **_kwargs: {**row, "reference_score": float(row["legacy_priority"])})
    ranked = search_adapter._score_rows([
        {"title": "Creatine supplementation and cognition in older adults", "abstract": "Creatine improved cognitive task performance in older adults.", "provider_query": "creatine cognition older adults", "legacy_priority": 10},
        {"title": "Lifestyle medicine clinical practice guideline", "abstract": "General lifestyle care guidance.", "provider_query": "creatine cognition older adults", "legacy_priority": 100},
    ], query="creatine cognition older adults")
    assert ranked[0]["title"].startswith("Creatine supplementation")
    assert ranked[0]["query_relevance_score"] > ranked[1]["query_relevance_score"]
    assert ranked[0]["nutev_priority_score"] == 10
    assert ranked[1]["nutev_priority_score"] == 100


def test_classification_explanation_uses_effective_provider_query(monkeypatch) -> None:
    monkeypatch.setattr(search_adapter, "load_canonical_taxonomy", lambda _path: ({}, {}))
    monkeypatch.setattr(search_adapter, "_read_profile", lambda: {"focus_keywords": [], "provider_weights": {}, "guardrails": {}})
    monkeypatch.setattr(search_adapter, "score_record", lambda row, *_args, **_kwargs: {**row, "reference_score": 1.0})
    result = search_adapter._score_rows([
        {"title": "Creatine and cognition", "abstract": "Older adults", "provider_query": "creatine cognition"}
    ], query="human question without those terms")[0]
    match = result["search_classification"]["query_match"]
    assert "creatine" in match["title_hits"]
    assert "human" not in match["terms_considered"]
''')

print("search-first P0 materialized")
