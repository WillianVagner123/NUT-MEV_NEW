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

function translateInternalEnums(root=document){
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT)
  const nodes=[]
  while(walker.nextNode())nodes.push(walker.currentNode)
  for(const node of nodes){
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

function improveNavigationAccessibility(){
  document.querySelectorAll('.nav-icon').forEach(icon=>icon.setAttribute('aria-hidden','true'))
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

function applyProductUi(){
  translateInternalEnums(document)
  explainResultCap()
  improveNavigationAccessibility()
}

const observer=new MutationObserver(applyProductUi)
observer.observe(document.documentElement,{childList:true,subtree:true})
applyProductUi()
renderBuildIdentity()
