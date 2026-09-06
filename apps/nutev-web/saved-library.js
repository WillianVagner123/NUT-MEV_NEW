const DB_NAME='nutev-saved-library';
const DB_VERSION=1;
const STORE='articles';
const MAX_PROVENANCE=25;
const SAVE_CHUNK=200;
let dbPromise=null;

function text(value){return String(value??'').trim()}
function normalized(value){return text(value).normalize('NFKC').replace(/\s+/g,' ').toLocaleLowerCase('en-US')}
function normalizeDoi(value){return normalized(value).replace(/^https?:\/\/(dx\.)?doi\.org\//,'').replace(/^doi:\s*/,'').trim()}
function normalizePmid(value){return text(value).replace(/^pmid[:\s]*/i,'').replace(/\D/g,'')}
function normalizeUrl(value){
  const raw=text(value);if(!raw)return'';
  try{const url=new URL(raw,location.origin);url.hash='';url.hostname=url.hostname.toLocaleLowerCase('en-US');return url.toString()}
  catch{return raw}
}

export function canonicalSavedKey(record={}){
  const doi=normalizeDoi(record.doi);if(doi)return`doi:${doi}`;
  const pmid=normalizePmid(record.pmid);if(pmid)return`pmid:${pmid}`;
  const url=normalizeUrl(record.url||record.landing_page_url||record.open_access_url);if(url)return`url:${url}`;
  const title=normalized(record.title||'(sem título)');
  const year=text(record.year);
  const journal=normalized(record.journal||record.venue||record.source_provider||record.source);
  return`meta:${title}|${year}|${journal}`;
}

export function sourceUrlFor(record={}){
  const doi=normalizeDoi(record.doi);if(doi)return`https://doi.org/${doi}`;
  return text(record.url||record.landing_page_url||record.open_access_url);
}

function openDb(){
  if(dbPromise)return dbPromise;
  if(!('indexedDB' in globalThis))return Promise.reject(new Error('IndexedDB indisponível neste navegador.'));
  dbPromise=new Promise((resolve,reject)=>{
    const request=indexedDB.open(DB_NAME,DB_VERSION);
    request.onupgradeneeded=()=>{
      const db=request.result;
      const store=db.objectStoreNames.contains(STORE)?request.transaction.objectStore(STORE):db.createObjectStore(STORE,{keyPath:'key'});
      if(!store.indexNames.contains('last_saved_at'))store.createIndex('last_saved_at','last_saved_at');
      if(!store.indexNames.contains('title_norm'))store.createIndex('title_norm','title_norm');
    };
    request.onsuccess=()=>resolve(request.result);
    request.onerror=()=>reject(request.error||new Error('Falha ao abrir a Biblioteca local.'));
    request.onblocked=()=>reject(new Error('Atualização da Biblioteca local bloqueada por outra aba.'));
  });
  return dbPromise;
}

function provenanceEntry(record,context={}){
  return{
    search_id:text(context.search_id),
    search_query:text(context.query),
    search_mode:text(context.search_mode),
    source_provider:text(record.source_provider||record.source),
    provider_query:text(record.provider_query),
    reference_rank:Number(record.reference_rank||0)||null,
    reference_score:Number(record.reference_score||0)||null,
    query_relevance_score:Number(record.query_relevance_score||0)||null,
    nutev_priority_score:Number(record.nutev_priority_score||0)||null,
    captured_at:new Date().toISOString(),
  };
}

function provenanceKey(entry){return[entry.search_id,entry.source_provider,entry.provider_query,entry.search_query].join('|')}
function mergedProvenance(existing,incoming){
  const out=[];const seen=new Set();
  for(const entry of [...(existing||[]),incoming]){const key=provenanceKey(entry);if(seen.has(key))continue;seen.add(key);out.push(entry)}
  return out.slice(-MAX_PROVENANCE);
}

function savedSnapshot(record,context,existing){
  const now=new Date().toISOString();
  const key=canonicalSavedKey(record);
  const article=JSON.parse(JSON.stringify(record));
  const provenance=mergedProvenance(existing?.provenance,provenanceEntry(record,context));
  return{
    key,
    title:text(record.title||'(sem título)'),
    title_norm:normalized(record.title||''),
    doi:normalizeDoi(record.doi),
    pmid:normalizePmid(record.pmid),
    year:record.year??null,
    journal:text(record.journal||record.venue),
    source_provider:text(record.source_provider||record.source),
    source_url:sourceUrlFor(record),
    document_class:text(record.search_classification?.document_class||record.document_class||record.article_type||'unclassified'),
    classification_confidence:text(record.search_classification?.confidence||''),
    taxonomy_primary:text(record.search_classification?.taxonomy_primary||record.taxonomy_primary||''),
    first_saved_at:existing?.first_saved_at||now,
    last_saved_at:now,
    provenance,
    article,
    storage_semantics:'browser_saved_search_result_not_scientific_inclusion',
  };
}

function saveChunk(db,records,context){
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(STORE,'readwrite');
    const store=tx.objectStore(STORE);
    let saved=0,updated=0;
    for(const record of records){
      const key=canonicalSavedKey(record);
      const get=store.get(key);
      get.onsuccess=()=>{
        const existing=get.result||null;
        if(existing)updated+=1;else saved+=1;
        store.put(savedSnapshot(record,context,existing));
      };
      get.onerror=()=>tx.abort();
    }
    tx.oncomplete=()=>resolve({saved,updated});
    tx.onerror=()=>reject(tx.error||new Error('Falha ao guardar artigos.'));
    tx.onabort=()=>reject(tx.error||new Error('Gravação na Biblioteca foi abortada.'));
  });
}

export async function saveArticles(records,context={}){
  const unique=new Map();
  for(const record of Array.isArray(records)?records:[]){if(record&&typeof record==='object')unique.set(canonicalSavedKey(record),record)}
  const values=[...unique.values()];
  if(!values.length)return{saved:0,updated:0,total:0};
  const db=await openDb();let saved=0,updated=0;
  for(let index=0;index<values.length;index+=SAVE_CHUNK){const part=await saveChunk(db,values.slice(index,index+SAVE_CHUNK),context);saved+=part.saved;updated+=part.updated}
  return{saved,updated,total:values.length};
}

export async function saveArticle(record,context={}){return saveArticles([record],context)}

export async function getSavedArticle(key){
  const db=await openDb();
  return new Promise((resolve,reject)=>{
    const tx=db.transaction(STORE,'readonly');const request=tx.objectStore(STORE).get(key);
    request.onsuccess=()=>resolve(request.result||null);request.onerror=()=>reject(request.error||new Error('Falha ao ler artigo salvo.'));
  });
}

export async function savedKeySet(keys){
  const db=await openDb();const unique=[...new Set((keys||[]).filter(Boolean))];const found=new Set();
  await Promise.all(unique.map(key=>new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readonly');const request=tx.objectStore(STORE).get(key);request.onsuccess=()=>{if(request.result)found.add(key);resolve()};request.onerror=()=>reject(request.error)})));
  return found;
}

export async function listSavedArticles({q='',limit=500}={}){
  const db=await openDb();
  const rows=await new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readonly');const request=tx.objectStore(STORE).getAll();request.onsuccess=()=>resolve(request.result||[]);request.onerror=()=>reject(request.error||new Error('Falha ao listar artigos salvos.'))});
  const needle=normalized(q);
  return rows.filter(item=>!needle||normalized([item.title,item.doi,item.pmid,item.journal,item.source_provider,...(item.provenance||[]).map(p=>p.search_query)].join(' ')).includes(needle)).sort((a,b)=>String(b.last_saved_at||'').localeCompare(String(a.last_saved_at||''))).slice(0,Math.max(1,Math.min(Number(limit)||500,5000)));
}

export async function countSavedArticles(){
  const db=await openDb();return new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readonly');const request=tx.objectStore(STORE).count();request.onsuccess=()=>resolve(Number(request.result||0));request.onerror=()=>reject(request.error||new Error('Falha ao contar artigos salvos.'))});
}

export async function removeSavedArticle(key){
  const db=await openDb();return new Promise((resolve,reject)=>{const tx=db.transaction(STORE,'readwrite');tx.objectStore(STORE).delete(key);tx.oncomplete=()=>resolve(true);tx.onerror=()=>reject(tx.error||new Error('Falha ao remover artigo salvo.'))});
}
