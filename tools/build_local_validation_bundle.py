from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
from pathlib import Path
from typing import Any

REQUIRED_PACKET_COLUMNS = [
    "question_id",
    "pool_item_id",
    "assessor_order",
    "reference_id",
    "title",
    "abstract",
    "journal",
    "year",
    "doi",
    "pmid",
    "pmcid",
    "url",
    "assessor_id",
    "relevance_grade",
    "reason",
    "decision_timestamp",
    "blind_to_nutev",
    "notes",
]
FORBIDDEN_FIELDS = {
    "rank",
    "reference_rank",
    "reference_score",
    "score_breakdown",
    "system",
    "system_membership",
    "system_score",
    "systems_count",
    "system_origin",
    "taxonomy",
    "taxonomy_primary",
    "taxonomy_secondary",
    "taxonomy_groups",
    "taxonomy_group_scores",
    "nutev_score",
    "nutev_rank",
}
QUESTION_FIELDS = {
    "question_id",
    "question_text",
    "split",
    "sampling_stratum",
    "population_context",
    "intervention_exposure",
    "comparator",
    "outcome_construct",
    "time_window",
    "languages",
    "document_types",
}

CSS = r'''
:root{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:#1f2937;background:#f5f7fb;--p:#0f766e;--b:#d9e0ea;--m:#64748b;--s:#fff}*{box-sizing:border-box}body{margin:0;background:#f5f7fb}.top{position:sticky;top:0;background:#fff;border-bottom:1px solid var(--b);padding:.8rem 1rem;display:flex;justify-content:space-between;gap:1rem;z-index:3}.brand{font-weight:800}.badge{border:1px solid var(--b);border-radius:999px;padding:.25rem .55rem;font-size:.8rem}.wrap{width:min(1180px,calc(100% - 2rem));margin:1rem auto 3rem}.grid{display:grid;grid-template-columns:minmax(0,1fr) 280px;gap:1rem}@media(max-width:900px){.grid{grid-template-columns:1fr}}.card{background:#fff;border:1px solid var(--b);border-radius:16px;padding:1.1rem;box-shadow:0 8px 24px rgba(15,23,42,.07)}.q{background:#ecfeff;border:1px solid #a5f3fc;border-radius:12px;padding:.85rem}.muted{color:var(--m)}.small{font-size:.86rem}.title{font-size:1.22rem;line-height:1.35}.meta{display:flex;gap:.5rem;flex-wrap:wrap}.abstract{white-space:pre-wrap;line-height:1.5;background:#f8fafc;border:1px solid var(--b);border-radius:12px;padding:.8rem;max-height:340px;overflow:auto}.grades{display:grid;grid-template-columns:repeat(3,1fr);gap:.6rem;margin:.8rem 0}@media(max-width:620px){.grades{grid-template-columns:1fr}}button,input,textarea{font:inherit}.grade,.btn{border:1px solid var(--b);background:#fff;border-radius:10px;padding:.7rem .8rem;cursor:pointer}.grade{font-weight:750;border-width:2px}.grade.sel[data-g="0"]{border-color:#ef4444;background:#fef2f2}.grade.sel[data-g="1"]{border-color:#f59e0b;background:#fffbeb}.grade.sel[data-g="2"]{border-color:#22c55e;background:#f0fdf4}.btn.primary{background:var(--p);border-color:var(--p);color:#fff;font-weight:700}.row{display:flex;gap:.55rem;flex-wrap:wrap;align-items:center}.field{margin:.8rem 0}.field label{display:block;font-weight:700;margin-bottom:.3rem}textarea{width:100%;min-height:85px;border:1px solid var(--b);border-radius:10px;padding:.7rem}.progress{height:10px;background:#e7edf4;border-radius:999px;overflow:hidden}.progress span{display:block;height:100%;background:var(--p)}.kpi{padding:.7rem;border:1px solid var(--b);border-radius:10px;margin:.55rem 0}.notice{padding:.8rem;border:1px solid var(--b);border-radius:12px;background:#f8fafc}.warn{background:#fff7ed;border-color:#fdba74}.success{background:#f0fdf4;border-color:#86efac}.quick{display:flex;gap:.4rem;flex-wrap:wrap;margin-top:.45rem}.quick button{font-size:.78rem}.footer{text-align:center;color:var(--m);font-size:.78rem;margin-top:1.5rem}.ctx{white-space:pre-wrap;font-size:.83rem;color:#475569}
'''

JS = r'''
const PACKET_B64=__PACKET_B64__;
const EXPECTED_SHA=__EXPECTED_SHA__;
const ASSESSOR=__ASSESSOR__;
const QUESTIONS=__QUESTIONS__;
const KEY='nutev-private-review-v1:'+ASSESSOR+':'+EXPECTED_SHA;
let rows=[],idx=0,decisions={};
function b64utf8(x){const b=atob(x),u=new Uint8Array(b.length);for(let i=0;i<b.length;i++)u[i]=b.charCodeAt(i);return new TextDecoder('utf-8').decode(u)}
function parseCSV(t){let out=[],row=[],f='',q=false;for(let i=0;i<t.length;i++){const c=t[i];if(q){if(c==='"'){if(t[i+1]==='"'){f+='"';i++}else q=false}else f+=c}else{if(c==='"')q=true;else if(c===','){row.push(f);f=''}else if(c==='\n'){row.push(f.replace(/\r$/,''));out.push(row);row=[];f=''}else f+=c}}if(f.length||row.length){row.push(f.replace(/\r$/,''));out.push(row)}const h=out.shift().map(x=>x.replace(/^\uFEFF/,''));return out.filter(r=>r.some(x=>x!=='')).map(r=>Object.fromEntries(h.map((k,i)=>[k,r[i]??''])))}
function csvCell(v){v=String(v??'');return /[",\r\n]/.test(v)?'"'+v.replaceAll('"','""')+'"':v}
function toCSV(items){const h=__HEADERS__;return '\uFEFF'+h.join(',')+'\r\n'+items.map(r=>h.map(k=>csvCell(r[k])).join(',')).join('\r\n')+'\r\n'}
function esc(s){return String(s??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;')}
function load(){try{decisions=JSON.parse(localStorage.getItem(KEY)||'{}')}catch{decisions={}}}
function save(){localStorage.setItem(KEY,JSON.stringify(decisions))}
function current(){return rows[idx]}
function dFor(r){return decisions[r.pool_item_id]||{grade:null,reason:'',reviewLater:false,blind:true,timestamp:''}}
function stats(){const done=rows.filter(r=>decisions[r.pool_item_id]?.timestamp).length;const flag=rows.filter(r=>decisions[r.pool_item_id]?.reviewLater).length;return{done,flag,pct:Math.round(100*done/rows.length)}}
const qr={0:['Fora do escopo da pergunta','População/intervenção não aplicável','Não responde ao construto'],1:['Relevante como contexto ou apoio','Aplicação parcial à pergunta','Útil, mas não é central'],2:['Diretamente aplicável à pergunta','Referência central','Evidência-chave para o construto']};
function contextText(q){return [q.population_context&&'População: '+q.population_context,q.intervention_exposure&&'Intervenção/exposição: '+q.intervention_exposure,q.comparator&&'Comparador: '+q.comparator,q.outcome_construct&&'Desfechos: '+q.outcome_construct,q.document_types&&'Tipos: '+q.document_types].filter(Boolean).join('\n')}
function render(){const r=current(),d=dFor(r),s=stats(),q=QUESTIONS[r.question_id]||{question_text:r.question_id};const href=r.doi?('https://doi.org/'+r.doi.replace(/^https?:\/\/doi\.org\//i,'').replace(/^doi:/i,'')):(r.url||'');document.querySelector('#app').innerHTML=`<div class="top"><div><span class="brand">NutEV Validation</span> <span class="badge">BLIND</span></div><div><span class="badge">${esc(ASSESSOR)}</span></div></div><div class="wrap"><div class="grid"><main class="card"><div class="q"><b>${esc(r.question_id)}</b><div>${esc(q.question_text||r.question_id)}</div><details><summary>Contexto de elegibilidade</summary><div class="ctx">${esc(contextText(q))}</div></details></div><p class="small muted">Referência ${idx+1} de ${rows.length}</p><h2 class="title">${esc(r.title)}</h2><div class="meta muted small"><span>${esc(r.journal||'—')}</span><span>${esc(r.year||'—')}</span><span>${esc(r.reference_id)}</span></div>${href?`<p><a target="_blank" rel="noopener" href="${esc(href)}">Abrir fonte ↗</a></p>`:''}<h3>Resumo</h3><div class="abstract">${esc(r.abstract||'Abstract indisponível.')}</div><h3 style="margin-top:1rem">Relevância para a pergunta</h3><div class="grades">${[0,1,2].map(g=>`<button class="grade ${d.grade===g?'sel':''}" data-g="${g}"><b>${g}</b><br>${g===0?'Irrelevante':g===1?'Relevante / periférica':'Diretamente relevante / chave'}</button>`).join('')}</div><div class="field"><label>Justificativa</label><textarea id="reason">${esc(d.reason)}</textarea><div class="quick" id="quick"></div></div><div class="field"><label><input type="checkbox" id="later" ${d.reviewLater?'checked':''}> Revisar depois</label></div><div class="field"><label><input type="checkbox" id="blind" ${d.blind?'checked':''}> Permaneci cego ao score/rank/taxonomia/origem NutEV e à decisão do outro avaliador</label></div><div class="row"><button class="btn" id="prev">← Anterior</button><button class="btn primary" id="saveNext">Salvar e próxima →</button><button class="btn" id="pending">Próxima pendente</button></div><p class="small muted">Atalhos: 0/1/2 nota · S salvar/próxima · J/K próxima/anterior.</p></main><aside class="card"><h3>Progresso</h3><div class="progress"><span style="width:${s.pct}%"></span></div><div class="kpi"><b>${s.done} / ${rows.length}</b><div class="small muted">concluídos</div></div><div class="kpi"><b>${s.flag}</b><div class="small muted">revisar depois</div></div><div class="row"><button class="btn" id="backup">Backup JSON</button><button class="btn" id="export">Exportar CSV</button></div><div class="notice ${s.done===rows.length?'success':''}" style="margin-top:.8rem">${s.done===rows.length?'100% concluído. Exporte o CSV final.':'O progresso é salvo automaticamente neste navegador.'}</div></aside></div><div class="footer">Não compartilhe este arquivo nem abra o packet do outro assessor no mesmo perfil de navegador.</div></div>`;bind()}
function setGrade(g){const r=current(),d=dFor(r);d.grade=g;decisions[r.pool_item_id]=d;save();render()}
function bind(){const r=current(),d=dFor(r),reason=document.querySelector('#reason'),quick=document.querySelector('#quick');function paint(){quick.innerHTML=d.grade===null?'':qr[d.grade].map(x=>`<button class="btn" data-x="${esc(x)}">${esc(x)}</button>`).join('');quick.querySelectorAll('button').forEach(b=>b.onclick=()=>{reason.value=b.dataset.x;d.reason=b.dataset.x;decisions[r.pool_item_id]=d;save()})}paint();document.querySelectorAll('.grade').forEach(b=>b.onclick=()=>setGrade(Number(b.dataset.g)));reason.oninput=()=>{d.reason=reason.value;decisions[r.pool_item_id]=d;save()};document.querySelector('#later').onchange=e=>{d.reviewLater=e.target.checked;decisions[r.pool_item_id]=d;save()};document.querySelector('#blind').onchange=e=>{d.blind=e.target.checked;decisions[r.pool_item_id]=d;save()};document.querySelector('#prev').onclick=()=>{idx=Math.max(0,idx-1);render()};document.querySelector('#saveNext').onclick=saveNext;document.querySelector('#pending').onclick=nextPending;document.querySelector('#backup').onclick=backup;document.querySelector('#export').onclick=exportCSV}
function saveNext(){const r=current(),d=dFor(r);if(![0,1,2].includes(d.grade))return alert('Escolha 0, 1 ou 2.');if(!d.reason.trim())return alert('A justificativa é obrigatória.');if(!d.blind&&!confirm('Você declarou quebra de cegueira. Salvar mesmo assim?'))return;d.timestamp=new Date().toISOString();decisions[r.pool_item_id]=d;save();let n=rows.findIndex((x,i)=>i>idx&&!decisions[x.pool_item_id]?.timestamp);idx=n>=0?n:Math.min(rows.length-1,idx+1);render()}
function nextPending(){for(let i=1;i<=rows.length;i++){const n=(idx+i)%rows.length,d=decisions[rows[n].pool_item_id];if(!d?.timestamp||d?.reviewLater){idx=n;render();return}}alert('Não há itens pendentes.')}
function download(name,text,type){const a=document.createElement('a'),u=URL.createObjectURL(new Blob([text],{type}));a.href=u;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)}
function backup(){download('NUTEV_'+ASSESSOR+'_backup.json',JSON.stringify({assessor_id:ASSESSOR,packet_sha256:EXPECTED_SHA,exported_at:new Date().toISOString(),decisions},null,2),'application/json')}
function exportCSV(){const out=rows.map(r=>{const d=dFor(r);return{...r,relevance_grade:d.grade??'',reason:d.reason||'',decision_timestamp:d.timestamp||'',blind_to_nutev:d.blind?'true':'false',notes:[r.notes,d.reviewLater?'REVIEW_LATER':''].filter(Boolean).join('; ')}});const incomplete=out.filter(r=>r.relevance_grade===''||!r.reason||!r.decision_timestamp);if(incomplete.length&&!confirm(`Ainda há ${incomplete.length} linhas incompletas. Exportar mesmo assim?`))return;download('ASSESSOR_'+ASSESSOR+'_completed.csv',toCSV(out),'text/csv;charset=utf-8')}
window.onkeydown=e=>{if(['TEXTAREA','INPUT'].includes(e.target.tagName))return;if(['0','1','2'].includes(e.key)){e.preventDefault();setGrade(Number(e.key))}else if(e.key.toLowerCase()==='s'){e.preventDefault();saveNext()}else if(e.key.toLowerCase()==='j'){e.preventDefault();idx=Math.min(rows.length-1,idx+1);render()}else if(e.key.toLowerCase()==='k'){e.preventDefault();idx=Math.max(0,idx-1);render()}};
rows=parseCSV(b64utf8(PACKET_B64));load();const first=rows.findIndex(r=>!decisions[r.pool_item_id]?.timestamp);idx=first>=0?first:0;render();
'''


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = [dict(row) for row in reader]
    return fields, rows


def load_questions(path: Path) -> dict[str, dict[str, str]]:
    fields, rows = read_csv(path)
    missing = QUESTION_FIELDS - set(fields)
    if missing:
        raise SystemExit(f"QUESTIONS.csv missing fields: {', '.join(sorted(missing))}")
    out: dict[str, dict[str, str]] = {}
    for row in rows:
        if row.get("split") != "validation":
            continue
        qid = (row.get("question_id") or "").strip()
        if not qid:
            raise SystemExit("QUESTIONS.csv contains blank validation question_id")
        out[qid] = {key: row.get(key, "") for key in QUESTION_FIELDS}
    if not out:
        raise SystemExit("QUESTIONS.csv contains no validation questions")
    return out


def validate_packet(path: Path, manifest: dict[str, Any]) -> tuple[str, bytes, list[dict[str, str]]]:
    data = path.read_bytes()
    fields, rows = read_csv(path)
    missing = set(REQUIRED_PACKET_COLUMNS) - set(fields)
    if missing:
        raise SystemExit(f"Packet missing fields: {', '.join(sorted(missing))}")
    leaked = FORBIDDEN_FIELDS & set(fields)
    if leaked:
        raise SystemExit(f"Packet leaks prohibited fields: {', '.join(sorted(leaked))}")
    if not rows:
        raise SystemExit("Packet is empty")
    assessor_ids = {(row.get("assessor_id") or "").strip() for row in rows}
    if len(assessor_ids) != 1 or "" in assessor_ids:
        raise SystemExit("Packet must contain exactly one non-blank assessor_id")
    assessor = next(iter(assessor_ids))
    for line_number, row in enumerate(rows, start=2):
        if (row.get("blind_to_nutev") or "").strip().casefold() != "true":
            raise SystemExit(f"Packet is not initially blind at line {line_number}")
        if any((row.get(key) or "").strip() for key in ("relevance_grade", "reason", "decision_timestamp")):
            raise SystemExit(f"Packet already contains a human decision at line {line_number}")
    outputs = {item.get("assessor_id"): item for item in manifest.get("outputs", [])}
    expected = outputs.get(assessor)
    if not expected:
        raise SystemExit(f"Manifest has no output for assessor_id={assessor}")
    actual_sha = sha256_bytes(data)
    if expected.get("sha256") != actual_sha:
        raise SystemExit(f"Packet SHA-256 mismatch: expected {expected.get('sha256')}, got {actual_sha}")
    if int(expected.get("rows", -1)) != len(rows):
        raise SystemExit(f"Packet row-count mismatch: expected {expected.get('rows')}, got {len(rows)}")
    if manifest.get("label_blind") is not True or manifest.get("independent_order_per_assessor") is not True:
        raise SystemExit("Manifest does not declare label_blind=true and independent_order_per_assessor=true")
    return assessor, data, rows


def render_html(packet_bytes: bytes, packet_sha: str, assessor: str, questions: dict[str, dict[str, str]]) -> str:
    js = JS.replace("__PACKET_B64__", json.dumps(base64.b64encode(packet_bytes).decode("ascii")))
    js = js.replace("__EXPECTED_SHA__", json.dumps(packet_sha))
    js = js.replace("__ASSESSOR__", json.dumps(assessor))
    js = js.replace("__QUESTIONS__", json.dumps(questions, ensure_ascii=False, sort_keys=True))
    js = js.replace("__HEADERS__", json.dumps(REQUIRED_PACKET_COLUMNS))
    return (
        '<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        f"<title>NutEV Validation - {assessor}</title><style>{CSS}</style></head>"
        f'<body><div id="app"></div><script>{js}</script></body></html>\n'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Build one self-contained private NutEV blind-review HTML bundle.")
    parser.add_argument("--questions", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--expected-questions-sha256")
    args = parser.parse_args()

    if args.expected_questions_sha256:
        actual_questions_sha = sha256_bytes(args.questions.read_bytes())
        if actual_questions_sha != args.expected_questions_sha256:
            raise SystemExit(
                f"QUESTIONS.csv SHA-256 mismatch: expected {args.expected_questions_sha256}, got {actual_questions_sha}"
            )

    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    assessor, packet_bytes, packet_rows = validate_packet(args.packet, manifest)
    questions = load_questions(args.questions)
    packet_qids = {row["question_id"] for row in packet_rows}
    missing_questions = packet_qids - set(questions)
    if missing_questions:
        raise SystemExit(f"Packet references unknown/non-validation questions: {', '.join(sorted(missing_questions))}")
    questions = {qid: questions[qid] for qid in sorted(packet_qids)}
    packet_sha = sha256_bytes(packet_bytes)
    html = render_html(packet_bytes, packet_sha, assessor, questions)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html, encoding="utf-8")
    print(json.dumps({
        "status": "PASS",
        "assessor_id": assessor,
        "packet_rows": len(packet_rows),
        "packet_sha256": packet_sha,
        "questions_in_packet": sorted(packet_qids),
        "output": str(args.output),
        "scientific_boundary": "The generated HTML embeds one blinded assessor packet only. Do not commit or publish generated private reviewer HTML files.",
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
