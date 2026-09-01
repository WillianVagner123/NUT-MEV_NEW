const APPROVED='APPROVED_FOR_GOVERNED_USE';
const RELEASE_TYPE='NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1';
let governance=null;
let releases=null;
let latestPackage=null;

const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const short=value=>{const text=String(value||'');return text.length>18?`${text.slice(0,10)}…${text.slice(-6)}`:text||'—'};

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

function approvedEntries(){
  const entries=Array.isArray(governance?.entries)?governance.entries:[];
  return entries.filter(entry=>entry.status===APPROVED&&entry.governance_decision?.action==='APPROVE'&&entry.governance_decision?.human_entered===true&&entry.governance_decision?.source_revalidated_at_decision===true);
}

function renderKpis(){
  const approved=approvedEntries().length;
  const records=Array.isArray(releases?.records)?releases.records.length:0;
  $('releaseKpis').innerHTML=[
    ['Approved sources',approved,'Governance-approved registry entries eligible for revalidation'],
    ['Prepared packages',records,'Persisted governed dissemination records'],
    ['Release type','V1','NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1'],
    ['Canonical synthesis','NO','Release package remains canonical:false'],
  ].map(([label,value,note])=>`<article class="kpi-card"><span>${esc(label)}</span><strong>${esc(value)}</strong><small>${esc(note)}</small></article>`).join('');
}

function renderApprovedSelect(){
  const select=$('approvedEntry');
  const entries=approvedEntries();
  select.innerHTML='<option value="">Selecione uma entrada aprovada</option>'+entries.map(entry=>`<option value="${esc(entry.artifact_id)}">${esc(entry.artifact_id)} · ${esc(entry.reviewer||'reviewer n/a')}</option>`).join('');
  if(!entries.length)$('prepareState').textContent='Nenhuma entrada APPROVED_FOR_GOVERNED_USE disponível no registry local.';
  validateForm();
}

function renderRecords(){
  const records=Array.isArray(releases?.records)?releases.records:[];
  if(!records.length){$('releaseRecords').innerHTML='<div class="small-state">Nenhum governed release preparado neste output root.</div>';return;}
  $('releaseRecords').innerHTML=records.map(record=>`<article class="release-record">
    <div><span>Package</span><strong>${esc(record.package_id)}</strong><small>${esc(record.release_type)}</small></div>
    <div><span>Source</span><strong>${esc(record.source_registry_artifact_id)}</strong><small>${esc(record.source_registry_status)}</small></div>
    <div><span>Prepared by</span><strong>${esc(record.prepared_by)}</strong><small>${esc(record.generated_at)}</small></div>
    <div><span>SHA-256</span><strong>${esc(short(record.package_content_sha256))}</strong><small>release_package_canonical: ${esc(record.release_package_canonical)}</small></div>
  </article>`).join('');
}

function validateForm(){
  const ready=Boolean($('approvedEntry').value&&$('preparedBy').value.trim()&&$('releasePurpose').value.trim().length>=20);
  $('prepareRelease').disabled=!ready;
}

function renderLatest(result){
  latestPackage=result?.package||null;
  const record=result?.record||{};
  if(!latestPackage){$('latestPackageCard').classList.add('hidden');return;}
  $('latestPackageCard').classList.remove('hidden');
  $('latestPackage').innerHTML=[
    ['Package id',record.package_id],
    ['Content SHA-256',latestPackage.content_sha256],
    ['Source registry',latestPackage.source_registry_artifact_id],
    ['Registry status',latestPackage.source_registry_status],
    ['Search id',latestPackage.search_id],
    ['Context version',latestPackage.context_version],
    ['Prepared by',latestPackage.prepared_by],
    ['Canonical',String(latestPackage.canonical)],
  ].map(([label,value])=>`<article><span>${esc(label)}</span><strong>${esc(value)}</strong></article>`).join('');
}

async function prepare(){
  const artifactId=$('approvedEntry').value;
  const preparedBy=$('preparedBy').value.trim();
  const purpose=$('releasePurpose').value.trim();
  if(!artifactId||!preparedBy||purpose.length<20)return;
  $('prepareRelease').disabled=true;
  $('prepareState').textContent='Revalidando registry entry, Brief e contexto atual no servidor…';
  try{
    const result=await postJson('/api/synthesis/releases/prepare',{artifact_id:artifactId,prepared_by:preparedBy,purpose});
    if(result?.package?.release_type!==RELEASE_TYPE||result?.package?.canonical!==false)throw new Error('Release package retornado perdeu o contrato V1 não canônico.');
    if(result.package?.guardrails?.governed_release_is_not_scientific_validation!==true)throw new Error('Release package perdeu guardrail de scientific validation.');
    renderLatest(result);
    $('prepareState').textContent='Package preparado e persistido após revalidação. Preparação ≠ scientific validation.';
    releases=await getJson('/api/synthesis/releases');
    renderKpis();renderRecords();
  }catch(error){
    latestPackage=null;
    $('latestPackageCard').classList.add('hidden');
    $('prepareState').textContent=`Bloqueado: ${error.message}`;
  }finally{validateForm();}
}

function downloadLatest(){
  if(!latestPackage)return;
  const blob=new Blob([JSON.stringify(latestPackage,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a');
  anchor.href=url;
  anchor.download=`nutev-governed-synthesis-release-${String(latestPackage.content_sha256).slice(0,12)}.json`;
  document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);
}

async function load(){
  $('releaseHealth').textContent='verificando…';
  $('releaseState').classList.remove('hidden');
  $('releaseContent').classList.add('hidden');
  try{
    [governance,releases]=await Promise.all([getJson('/api/synthesis/governance'),getJson('/api/synthesis/releases')]);
    renderKpis();renderApprovedSelect();renderRecords();
    $('releaseState').classList.add('hidden');
    $('releaseContent').classList.remove('hidden');
    $('releaseHealth').textContent='local registry conectado';
  }catch(error){
    $('releaseHealth').textContent='local-only / indisponível';
    $('releaseState').textContent=`Governed Release indisponível neste navegador: ${error.message}`;
  }
}

$('approvedEntry').addEventListener('change',validateForm);
$('preparedBy').addEventListener('input',validateForm);
$('releasePurpose').addEventListener('input',validateForm);
$('prepareRelease').addEventListener('click',prepare);
$('downloadRelease').addEventListener('click',downloadLatest);
$('refreshRelease').addEventListener('click',load);
load();
