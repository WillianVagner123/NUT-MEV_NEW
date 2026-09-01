const MANIFEST_TYPE='NUTEV_GOVERNED_PUBLICATION_MANIFEST_V1';
const STATEMENT_TYPE='NUTEV_PUBLICATION_STATEMENT_CANDIDATE_V1';
let releases=null;
let publications=null;
let latestManifest=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const short=value=>{const text=String(value||'');return text.length>20?`${text.slice(0,11)}…${text.slice(-7)}`:text||'—'};

async function getJson(url){
  const response=await fetch(url,{headers:{Accept:'application/json'},cache:'no-store'});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message||data.error||`HTTP ${response.status}`);
  return data;
}

async function postJson(url,payload){
  const response=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(payload)});
  const data=await response.json().catch(()=>({}));
  if(!response.ok)throw new Error(data.message||data.error||`HTTP ${response.status}`);
  return data;
}

function releaseRecords(){return Array.isArray(releases?.records)?releases.records:[];}
function publicationRecords(){return Array.isArray(publications?.records)?publications.records:[];}

function renderKpis(){
  $('publicationKpis').innerHTML=[
    ['Governed releases',releaseRecords().length,'Persisted dissemination packages available for server revalidation'],
    ['Publication manifests',publicationRecords().length,'Metadata records only'],
    ['Statement mode','CANDIDATE','Human-judgement descriptions; never accepted claims'],
    ['Canonical synthesis','NO','Manifest remains canonical:false'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderReleaseSelect(){
  const select=$('releasePackage');
  const records=releaseRecords();
  select.innerHTML='<option value="">Selecione um release</option>'+records.map(record=>`<option value="${esc(record.package_id)}">${esc(record.package_id)} · ${esc(record.prepared_by||'operator n/a')}</option>`).join('');
  if(!records.length)$('preparePublicationState').textContent='Nenhum Governed Release persistido está disponível neste output root.';
  validateForm();
}

function renderRecords(){
  const records=publicationRecords();
  if(!records.length){$('publicationRecords').innerHTML='<div class="small-state">Nenhum publication manifest preparado neste output root.</div>';return;}
  $('publicationRecords').innerHTML=records.map(record=>`<article class="publication-record">
    <div><span>Manifest</span><strong>${esc(record.manifest_id)}</strong><small>${esc(record.manifest_type)}</small></div>
    <div><span>Source release</span><strong>${esc(record.source_release_package_id)}</strong><small>${esc(short(record.source_release_content_sha256))}</small></div>
    <div><span>Owner</span><strong>${esc(record.publication_owner)}</strong><small>${esc(record.generated_at)}</small></div>
    <div><span>Traceability</span><strong>${esc(record.citation_count)} citations · ${esc(record.statement_candidate_count)} statements</strong><small>publication_manifest_canonical: ${esc(record.publication_manifest_canonical)}</small></div>
  </article>`).join('');
}

function validateForm(){
  const ready=Boolean($('releasePackage').value&&$('publicationOwner').value.trim()&&$('intendedUse').value.trim().length>=20);
  $('preparePublication').disabled=!ready;
}

function renderManifest(result){
  latestManifest=result?.manifest||null;
  const record=result?.record||{};
  if(!latestManifest){$('latestManifestCard').classList.add('hidden');return;}
  $('latestManifestCard').classList.remove('hidden');
  $('latestManifestMeta').innerHTML=[
    ['Manifest id',record.manifest_id],
    ['Content SHA-256',latestManifest.content_sha256],
    ['Source release',latestManifest.source_release_package_id],
    ['Context',short(latestManifest.source_context_fingerprint)],
    ['Owner',latestManifest.publication_owner],
    ['Citations',latestManifest.citation_bundle?.length||0],
    ['Statement candidates',latestManifest.statement_candidates?.length||0],
    ['Canonical',String(latestManifest.canonical)],
  ].map(([label,value])=>`<article><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join('');

  const statements=Array.isArray(latestManifest.statement_candidates)?latestManifest.statement_candidates:[];
  $('statementCandidates').innerHTML=statements.map(item=>`<article class="statement-card">
    <p>${esc(item.statement_text)}</p>
    <div class="statement-tags"><span>${esc(item.relation)}</span><span>${esc(item.publication_status)}</span><span>EvidenceClaim: ${esc(item.accepted_evidence_claim)}</span></div>
    <small>${esc(item.statement_id)} · citations ${esc((item.citation_ids||[]).join(', '))}</small>
    <small>${esc(item.statement_semantics)}</small>
  </article>`).join('')||'<div class="small-state">Nenhum statement candidate.</div>';

  const citations=Array.isArray(latestManifest.citation_bundle)?latestManifest.citation_bundle:[];
  $('citationBundle').innerHTML=citations.map(item=>`<article class="citation-card">
    <span>${esc(item.citation_id)} · ${esc(item.role)}</span><strong>${esc(item.title)}</strong>
    <small>${esc(item.document_id)} · bundle ${esc(item.bundle_id)}</small>
    <blockquote>${esc(item.result_text)}</blockquote>
    <small>source_sentence_sha256: ${esc(short(item.source_sentence_sha256))}</small>
  </article>`).join('')||'<div class="small-state">Nenhuma citation disponível.</div>';
}

async function prepare(){
  const packageId=$('releasePackage').value;
  const publicationOwner=$('publicationOwner').value.trim();
  const intendedUse=$('intendedUse').value.trim();
  if(!packageId||!publicationOwner||intendedUse.length<20)return;
  $('preparePublication').disabled=true;
  $('preparePublicationState').textContent='Revalidando Governed Release e construindo citation bundle no servidor…';
  try{
    const result=await postJson('/api/synthesis/publications/prepare',{package_id:packageId,publication_owner:publicationOwner,intended_use:intendedUse});
    if(result?.manifest?.manifest_type!==MANIFEST_TYPE||result?.manifest?.canonical!==false)throw new Error('Publication manifest perdeu o contrato V1 não canônico.');
    const statements=Array.isArray(result.manifest?.statement_candidates)?result.manifest.statement_candidates:[];
    if(statements.some(item=>item.statement_type!==STATEMENT_TYPE||item.accepted_evidence_claim!==false||item.publication_status!=='CANDIDATE_ONLY'))throw new Error('Statement candidate foi promovido indevidamente.');
    if(result.manifest?.guardrails?.accepted_evidence_claims_created!==false)throw new Error('Manifest perdeu o guardrail de EvidenceClaim.');
    renderManifest(result);
    $('preparePublicationState').textContent='Manifest preparado após revalidação. Statement candidate ≠ accepted EvidenceClaim.';
    publications=await getJson('/api/synthesis/publications');
    renderKpis();renderRecords();
  }catch(error){
    latestManifest=null;
    $('latestManifestCard').classList.add('hidden');
    $('preparePublicationState').textContent=`Bloqueado: ${error.message}`;
  }finally{validateForm();}
}

function downloadManifest(){
  if(!latestManifest)return;
  const blob=new Blob([JSON.stringify(latestManifest,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a');
  anchor.href=url;
  anchor.download=`nutev-publication-manifest-${String(latestManifest.content_sha256).slice(0,12)}.json`;
  document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);
}

async function load(){
  $('publicationHealth').textContent='verificando…';
  $('publicationState').classList.remove('hidden');
  $('publicationContent').classList.add('hidden');
  try{
    [releases,publications]=await Promise.all([getJson('/api/synthesis/releases'),getJson('/api/synthesis/publications')]);
    renderKpis();renderReleaseSelect();renderRecords();
    $('publicationState').classList.add('hidden');
    $('publicationContent').classList.remove('hidden');
    $('publicationHealth').textContent='local publication ledger conectado';
  }catch(error){
    $('publicationHealth').textContent='local-only / indisponível';
    $('publicationState').textContent=`Publication Manifest indisponível neste navegador: ${error.message}`;
  }
}

$('releasePackage').addEventListener('change',validateForm);
$('publicationOwner').addEventListener('input',validateForm);
$('intendedUse').addEventListener('input',validateForm);
$('preparePublication').addEventListener('click',prepare);
$('downloadManifest').addEventListener('click',downloadManifest);
$('refreshPublication').addEventListener('click',load);
load();
