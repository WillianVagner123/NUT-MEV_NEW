const STATUS_LABELS={
  COMPLETE:'Concluída',
  COMPLETE_WITH_PROVIDER_GAPS:'Concluída, com lacunas em algumas fontes',
  COMPLETE_WITH_AUDIT_GAPS:'Concluída, com lacunas de auditoria',
  PREFLIGHT:'Pré-verificação',
  PILOT:'Piloto',
  DEVELOPMENT:'Desenvolvimento',
  SUPPLEMENTARY:'Suplementar',
  FORMAL:'Formal'
}

const NAV_GROUPS=[
  {label:'Visão geral',items:[
    {key:'dashboard',href:'/',icon:'◫',label:'Dashboard'}
  ]},
  {label:'Evidências',items:[
    {key:'search',href:'/search.html',icon:'⌕',label:'Buscar evidências'},
    {key:'articles',href:'/articles.html',icon:'▤',label:'Corpus'},
    {key:'radar',href:'/radar.html',icon:'⌁',label:'Radar de evidências'}
  ]},
  {label:'Estratégia',items:[
    {key:'qa',href:'/review-qa.html',icon:'◎',label:'QA'},
    {key:'press',href:'/press-review.html',icon:'▣',label:'PRESS'},
    {key:'regional',href:'/regional-routes.html',icon:'↗',label:'Rotas regionais'}
  ]},
  {label:'Validação',items:[
    {key:'validation',href:'/validation/',icon:'✓',label:'Validação científica'}
  ]},
  {label:'Sistema',items:[
    {key:'history',href:'/search.html?view=history',icon:'◷',label:'Minhas buscas'}
  ]}
]

const GLOSSARY=[
  ['Busca progressiva','Execução que consulta provedores em etapas e preserva o estado de cada fonte. Uma fonte indisponível não é tratada como zero resultados.'],
  ['Provider','Fonte externa consultada pelo NutEV, como PubMed, Europe PMC, OpenAlex, Crossref, DOAJ, SciELO ou LILACS/BVS.'],
  ['Deduplicação','Processo que consolida registros equivalentes vindos de fontes diferentes sem apagar a proveniência de origem.'],
  ['Ranking','Ordem operacional de leitura ou processamento. Ranking não significa recomendação, inclusão, qualidade metodológica ou certeza da evidência.'],
  ['ResultBundle','Estrutura processada que organiza resultados extraídos pelo pipeline. Seu texto não deve ser tratado como citação literal da publicação.'],
  ['Fonte verbatim','Trecho reproduzido literalmente de uma fonte rastreável, acompanhado de identificadores e hash quando disponível.'],
  ['EvidenceClaim','Afirmação de evidência com proveniência própria e revisão governada. Não é criada automaticamente só porque um ResultBundle existe.'],
  ['EvidenceSet','Conjunto governado de evidências associado a uma pergunta ou decisão científica específica.'],
  ['QA','Controle metodológico prospectivo da estratégia de busca. Não substitui triagem humana e não autoriza PRISMA por si só.'],
  ['PRESS','Revisão independente e estruturada de uma estratégia eletrônica de busca. Alterações materiais devem retornar ao ciclo de versionamento e PILOT.'],
  ['Pré-freeze','Estado anterior ao congelamento formal de uma estratégia. Ajustes ainda podem ocorrer desde que sejam rastreados e revalidados.'],
  ['Freeze','Congelamento formal de uma estratégia/versionamento após os gates definidos. O NutEV não deve inferir freeze apenas por haver um run executado.'],
  ['PRISMA','Relato estruturado do processo de revisão. Snapshots, pilots, QA, PRESS ou buscas exploratórias não equivalem automaticamente a uma etapa PRISMA.'],
  ['Proveniência','Rastro que liga um dado, trecho, decisão ou resultado à sua origem, versão e contexto de processamento.']
]

function escapeHtml(value){
  return String(value??'').replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;').replaceAll("'",'&#39;')
}

function ensureProductStyles(){
  if(document.querySelector('link[data-nutev-product-ui]'))return
  const link=document.createElement('link')
  link.rel='stylesheet'
  link.href='/product-ui.css'
  link.dataset.nutevProductUi='true'
  document.head.appendChild(link)
}

function activeNavKey(){
  const path=location.pathname.replace(/\/+$/,'')||'/'
  const params=new URLSearchParams(location.search)
  if(path==='/search.html'&&params.get('view')==='history')return 'history'
  if(path==='/')return 'dashboard'
  if(path==='/search.html'||path==='/ask.html')return 'search'
  if(['/articles.html','/evidence.html','/evidence-map.html'].includes(path))return 'articles'
  if(['/radar.html','/intelligence.html'].includes(path))return 'radar'
  if(['/review-qa.html','/review-routes.html','/quality.html','/strategy.html'].includes(path))return 'qa'
  if(path==='/press-review.html')return 'press'
  if(path==='/regional-routes.html')return 'regional'
  if(path.startsWith('/validation'))return 'validation'
  return ''
}

function canonicalNavHtml(active){
  return NAV_GROUPS.map(group=>{
    const items=group.items.map(item=>`<a class="nav-item${active===item.key?' active':''}" href="${item.href}"${active===item.key?' aria-current="page"':''}><span class="nav-icon" aria-hidden="true">${item.icon}</span><span>${escapeHtml(item.label)}</span></a>`).join('')
    return `<div class="nav-group-label">${escapeHtml(group.label)}</div>${items}`
  }).join('')
}

function normalizeNavigation(){
  const active=activeNavKey()
  const signature=`v2:${active}`
  document.querySelectorAll('.sidebar nav,.product-nav').forEach(nav=>{
    if(nav.dataset.nutevCanonicalNav===signature)return
    nav.setAttribute('aria-label','Navegação principal')
    nav.innerHTML=canonicalNavHtml(active)
    nav.dataset.nutevCanonicalNav=signature
  })
}

function shouldTranslateNode(node){
  const parent=node.parentElement
  if(!parent)return false
  return !parent.closest('code,pre,script,style,textarea,[data-raw-enum]')
}

function translateInternalEnums(root=document){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT)
  const nodes=[]
  while(walker.nextNode())nodes.push(walker.currentNode)
  for(const node of nodes){
    if(!shouldTranslateNode(node))continue
    let text=node.nodeValue||''
    for(const [raw,label] of Object.entries(STATUS_LABELS))text=text.replaceAll(raw,label)
    if(text!==node.nodeValue)node.nodeValue=text
  }
}

function explainResultCap(){
  const summary=document.querySelector('#summary')
  const values=[...document.querySelectorAll('#summary .summary-grid .kpi strong')].map(node=>Number(String(node.textContent||'').replace(/\D/g,'')))
  if(!summary||values.length<3||!Number.isFinite(values[0])||!Number.isFinite(values[2]))return
  const unique=values[0],returned=values[2]
  let note=document.querySelector('#resultCapNote')
  if(unique<=returned){note?.remove();return}
  if(!note){note=document.createElement('div');note.id='resultCapNote';note.className='review-result-note';summary.appendChild(note)}
  note.textContent=`Exibindo ${returned.toLocaleString('pt-BR')} de ${unique.toLocaleString('pt-BR')} referências únicas. Este modo possui limite de apresentação; use a busca sem teto para recuperar o conjunto completo.`
}

function ensureSkipLink(){
  if(document.querySelector('.skip-link'))return
  const target=document.querySelector('main.main,main,.workspace-body')
  if(!target)return
  if(!target.id)target.id='mainContent'
  const link=document.createElement('a')
  link.className='skip-link'
  link.href=`#${target.id}`
  link.textContent='Pular para o conteúdo principal'
  document.body.prepend(link)
}

function glossaryRows(filter=''){
  const normalized=filter.trim().toLocaleLowerCase('pt-BR')
  const rows=GLOSSARY.filter(([term,definition])=>!normalized||`${term} ${definition}`.toLocaleLowerCase('pt-BR').includes(normalized))
  if(!rows.length)return '<p class="glossary-empty">Nenhum termo encontrado.</p>'
  return rows.map(([term,definition])=>`<div class="glossary-row"><dt>${escapeHtml(term)}</dt><dd>${escapeHtml(definition)}</dd></div>`).join('')
}

function ensureGlossary(){
  if(document.querySelector('#nutevGlossaryButton'))return
  const button=document.createElement('button')
  button.id='nutevGlossaryButton'
  button.className='glossary-trigger'
  button.type='button'
  button.textContent='Glossário científico'
  button.setAttribute('aria-haspopup','dialog')

  const dialog=document.createElement('dialog')
  dialog.id='nutevGlossaryDialog'
  dialog.className='glossary-dialog'
  dialog.innerHTML=`<div class="glossary-head"><div><span class="glossary-eyebrow">Ajuda de termos</span><h2>Glossário científico</h2><p>Definições de interface para reduzir ambiguidade sem alterar os contratos científicos internos.</p></div><button class="glossary-close" type="button" aria-label="Fechar glossário">×</button></div><label class="glossary-search">Filtrar termos<input id="nutevGlossarySearch" type="search" autocomplete="off" placeholder="Ex.: PRESS, ResultBundle, PRISMA"></label><dl id="nutevGlossaryList" class="glossary-list">${glossaryRows()}</dl>`

  document.body.append(button,dialog)
  const close=()=>{if(typeof dialog.close==='function')dialog.close();else dialog.removeAttribute('open')}
  button.addEventListener('click',()=>{if(typeof dialog.showModal==='function')dialog.showModal();else dialog.setAttribute('open','')})
  dialog.querySelector('.glossary-close')?.addEventListener('click',close)
  dialog.addEventListener('click',event=>{if(event.target===dialog)close()})
  dialog.querySelector('#nutevGlossarySearch')?.addEventListener('input',event=>{
    const list=dialog.querySelector('#nutevGlossaryList')
    if(list)list.innerHTML=glossaryRows(event.target.value)
  })
}

async function renderBuildIdentity(){
  try{
    const response=await fetch('/api/version',{cache:'no-store'})
    if(!response.ok)return
    const build=await response.json()
    const main=document.querySelector('main.main,.main,.workspace')
    if(!main||document.querySelector('#nutevBuildFooter'))return
    const footer=document.createElement('footer')
    footer.id='nutevBuildFooter'
    footer.className='product-footer'
    const commit=String(build.commit||'unknown')
    const shortCommit=commit==='unknown'?commit:commit.slice(0,12)
    const time=build.build_time&&build.build_time!=='unknown'?` · ${build.build_time}`:''
    footer.textContent=`NutEV · build ${shortCommit}${time}`
    main.appendChild(footer)
  }catch{}
}

function applyProductUi(root=document){
  normalizeNavigation()
  translateInternalEnums(root)
  explainResultCap()
  ensureSkipLink()
  ensureGlossary()
}

ensureProductStyles()
applyProductUi()
renderBuildIdentity()

const observer=new MutationObserver(mutations=>{
  let changed=false
  for(const mutation of mutations){
    if(mutation.addedNodes.length){changed=true;break}
  }
  if(changed)applyProductUi(document)
})
observer.observe(document.documentElement,{childList:true,subtree:true})
