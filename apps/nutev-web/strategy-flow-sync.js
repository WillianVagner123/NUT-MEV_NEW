function flowApi(){return window.NutEVStrategyFlow||null}
function text(selector){return String(document.querySelector(selector)?.textContent||'').trim()}
function currentStep(step){return flowApi()?.read?.()?.[step]||{}}
function sameValue(left,right){return JSON.stringify(left)===JSON.stringify(right)}

function publish(step,patch){
  const api=flowApi()
  if(!api?.update)return
  const current=currentStep(step)
  if(Object.entries(patch).every(([key,value])=>sameValue(current[key],value)))return
  api.update(step,patch)
}

function classificationProgress(){
  const match=text('#classificationCounter').match(/(\d+)\s*\/\s*(\d+)/)
  return match?{done:Number(match[1]),total:Number(match[2])}:{done:0,total:0}
}

function syncQa(){
  const badge=text('#qaSummary .qa-badge').toUpperCase()
  const runCard=text('#mainRunCard')
  if(badge){
    const progress=classificationProgress()
    publish('qa',{
      status:badge==='PASS'?'TECHNICAL_PASS':'REVIEW_REQUIRED',
      technical_gate:badge,
      scientific_decision:'PENDING_HUMAN_REVIEW',
      human_classifications_done:progress.done,
      human_classifications_total:progress.total
    })
    return
  }
  if(runCard.includes('Run principal elegível para QA')){
    publish('qa',{status:'READY',scientific_decision:'PENDING_HUMAN_REVIEW'})
  }else if(runCard.includes('Nenhum run compatível encontrado')){
    publish('qa',{status:'PENDING_RUN',scientific_decision:'PENDING_HUMAN_REVIEW'})
  }else if(runCard.includes('Run ainda não elegível')){
    publish('qa',{status:'REVIEW_REQUIRED',scientific_decision:'PENDING_HUMAN_REVIEW'})
  }
}

function syncPress(){
  const gate=document.querySelector('#pressGate')
  if(gate?.classList.contains('press-gate-ready')){
    publish('press',{status:'PRESS_REVIEW_COMPLETE_PENDING_CANONICAL_REGISTRATION',freeze_authorized:false,gf10_authorized:false})
    return
  }
  if(gate?.classList.contains('press-gate-return')){
    publish('press',{status:'REVISION_REQUIRED',freeze_authorized:false,gf10_authorized:false})
    return
  }
  if(gate?.classList.contains('press-gate-block')){
    publish('press',{status:'PRESS_FAIL',freeze_authorized:false,gf10_authorized:false})
    return
  }
  if(gate?.classList.contains('press-gate-pending')){
    publish('press',{status:'PRESS_IN_REVIEW',freeze_authorized:false,gf10_authorized:false})
    return
  }
  if(text('#pressHealth').toLocaleLowerCase('pt-BR')==='pronto'&&!currentStep('press').status){
    publish('press',{status:'READY_FOR_HUMAN_REVIEW',freeze_authorized:false,gf10_authorized:false})
  }
}

function syncRegional(){
  const gate=document.querySelector('#regionalGate')
  if(gate?.classList.contains('ok')){
    publish('regional',{status:'PASS',technical_route_gate:'PASS',gf01_candidate_complete:true,freeze_authorized:false})
    return
  }
  if(gate?.classList.contains('bad')){
    publish('regional',{status:'REVIEW_REQUIRED',technical_route_gate:'REVIEW_REQUIRED',gf01_candidate_complete:false,freeze_authorized:false})
    return
  }
  if(text('#regionalHealth').toLocaleLowerCase('pt-BR')==='pronto'&&!currentStep('regional').status){
    publish('regional',{status:'READY_FOR_EVIDENCE',gf01_candidate_complete:false,freeze_authorized:false})
  }
}

function sync(){
  const path=location.pathname.replace(/\/+$/,'')||'/'
  if(path==='/review-qa.html')syncQa()
  else if(path==='/press-review.html')syncPress()
  else if(path==='/regional-routes.html')syncRegional()
}

function observeRelevantSurface(){
  const path=location.pathname.replace(/\/+$/,'')||'/'
  const selectors=path==='/review-qa.html'
    ?['#mainRunCard','#qaSummary','#classificationCounter']
    :path==='/press-review.html'
      ?['#pressHealth','#pressGate']
      :path==='/regional-routes.html'
        ?['#regionalHealth','#regionalGate']
        :[]
  const observer=new MutationObserver(()=>sync())
  for(const selector of selectors){
    const node=document.querySelector(selector)
    if(node)observer.observe(node,{childList:true,subtree:true,characterData:true,attributes:true,attributeFilter:['class']})
  }
}

sync()
observeRelevantSurface()
window.addEventListener('load',sync)