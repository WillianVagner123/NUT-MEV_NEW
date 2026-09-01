const SNAPSHOT_VERSION='nutev_article1_scientific_snapshot_v1';

const textEncoder=new TextEncoder();

function stableValue(value){
  if(Array.isArray(value))return value.map(stableValue);
  if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(key=>[key,stableValue(value[key])]));
  return value;
}

function stableJson(value){return JSON.stringify(stableValue(value))}

async function sha256Text(text){
  const digest=await crypto.subtle.digest('SHA-256',textEncoder.encode(text));
  return [...new Uint8Array(digest)].map(value=>value.toString(16).padStart(2,'0')).join('');
}

async function fetchText(url){
  const response=await fetch(url,{cache:'no-store'});
  if(!response.ok)throw new Error(`${url} HTTP ${response.status}`);
  return response.text();
}

function countBy(rows,getter){
  const output={};
  for(const row of rows){
    const values=getter(row);
    for(const value of Array.isArray(values)?values:[values]){
      if(value===undefined||value===null||value==='')continue;
      output[value]=(output[value]||0)+1;
    }
  }
  return output;
}

function effectiveClass(row){return row.review_profile?.primary_document_class||row.document_class||'unclassified'}
function domains(row){return row.review_profile?.operational_domains||[]}

export async function buildScientificSnapshot(){
  const urls={
    search_state:'/agent-context/article1/SEARCH_STATE.json',
    context_manifest:'/agent-context/article1/CONTEXT_MANIFEST.json',
    article_summaries:'/agent-context/article1/ARTICLE_SUMMARIES.jsonl',
    query_draft:'/strategy-data/article1_query_draft_v1.json',
    build_info:'/build-info.json'
  };
  const entries=await Promise.all(Object.entries(urls).map(async([key,url])=>[key,url,await fetchText(url)]));
  const sourceTexts=Object.fromEntries(entries.map(([key,,text])=>[key,text]));
  const sourceUrls=Object.fromEntries(entries.map(([key,url])=>[key,url]));
  const sourceHashes=Object.fromEntries(await Promise.all(entries.map(async([key,,text])=>[key,await sha256Text(text)])));

  const searchState=JSON.parse(sourceTexts.search_state);
  const contextManifest=JSON.parse(sourceTexts.context_manifest);
  const queryDraft=JSON.parse(sourceTexts.query_draft);
  const buildInfo=JSON.parse(sourceTexts.build_info);
  const articles=sourceTexts.article_summaries.split(/\r?\n/).filter(Boolean).map(JSON.parse);
  const routedUnion=articles.filter(row=>(row.routes||[]).length>0).length;
  const overlap=articles.filter(row=>(row.routes||[]).includes('B-NORM')&&(row.routes||[]).includes('C-STRUCT')).length;

  const core={
    snapshot_version:SNAPSHOT_VERSION,
    project:'NutEV Evidence Engine · Article 1',
    search_id:searchState.search_id||null,
    question:searchState.question||queryDraft.question||null,
    build_commit:buildInfo.build_commit||'unknown',
    source_urls:sourceUrls,
    source_sha256:sourceHashes,
    context_manifest_version:contextManifest.context_version||contextManifest.manifest_version||null,
    query:{
      draft_version:queryDraft.draft_version||null,
      status:queryDraft.status||null,
      gf10_authorized:Boolean(queryDraft.formal_gate?.authorized),
      c4_social_context_status:queryDraft.routes?.['C-STRUCT']?.subroutes?.['C4-SOCIAL-CONTEXT']?.status||null
    },
    formal_search:searchState.formal_search||{},
    corpus:{
      safe_article_summaries:articles.length,
      document_class_counts:countBy(articles,effectiveClass),
      operational_domain_counts:countBy(articles,domains),
      full_text_status_counts:countBy(articles,row=>row.full_text_status||'unknown'),
      provider_counts:countBy(articles,row=>row.source_provider||'unknown'),
      publication_year_counts:countBy(articles,row=>row.year?String(row.year):'unknown'),
      routes:{
        'B-NORM':articles.filter(row=>(row.routes||[]).includes('B-NORM')).length,
        'C-STRUCT':articles.filter(row=>(row.routes||[]).includes('C-STRUCT')).length,
        union:routedUnion,
        overlap,
        unrouted:articles.length-routedUnion
      }
    },
    runtime:searchState.runtime||{},
    scientific_boundaries:{
      discovery_is_not_formal_search:true,
      snapshot_is_not_prisma:true,
      route_is_not_inclusion:true,
      retrieval_is_not_eligibility:true,
      machine_profile_is_not_quality_or_rob:true,
      document_count_is_not_evidence_strength:true,
      snapshot_does_not_change_scientific_state:true
    }
  };
  const snapshotId=await sha256Text(stableJson(core));
  return {...core,snapshot_id:snapshotId,generated_at:new Date().toISOString()};
}

export function downloadSnapshot(snapshot){
  const blob=new Blob([JSON.stringify(snapshot,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob);
  const anchor=document.createElement('a');
  anchor.href=url;
  anchor.download=`nutev-article1-snapshot-${snapshot.snapshot_id.slice(0,12)}.json`;
  document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(url);
}
