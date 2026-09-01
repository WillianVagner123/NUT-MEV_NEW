const detail=document.querySelector('#articleDetail');

const TAB_ORDER=[
  ['overview','Overview'],
  ['methods','Methods'],
  ['evidence','Evidence'],
  ['domains','Domains'],
  ['provenance','Provenance'],
  ['review','Human Review']
];

function classifySection(section){
  const title=section.querySelector('h3')?.textContent?.trim().toLowerCase()||'';
  if(title.includes('perfil para revisão'))return 'domains';
  if(title.includes('visão rápida'))return 'methods';
  if(title.includes('principais resultados')||title.includes('trechos-chave'))return 'evidence';
  if(title.includes('prioridade operacional')||title.includes('proveniência'))return 'provenance';
  return 'overview';
}

function activateTab(root,name){
  root.querySelectorAll('[data-dossier-tab]').forEach(button=>button.classList.toggle('active',button.dataset.dossierTab===name));
  root.querySelectorAll('[data-dossier-panel]').forEach(panel=>panel.classList.toggle('hidden',panel.dataset.dossierPanel!==name));
}

function enhanceDossier(){
  if(!detail||detail.dataset.dossierEnhanced==='true')return;
  const head=detail.querySelector('.detail-head');
  const sections=[...detail.querySelectorAll(':scope > .detail-section')];
  if(!head||!sections.length)return;
  detail.dataset.dossierEnhanced='true';

  const tabs=document.createElement('div');
  tabs.className='dossier-tabs';
  tabs.setAttribute('role','tablist');
  tabs.setAttribute('aria-label','Scientific dossier sections');
  tabs.innerHTML=TAB_ORDER.map(([key,label],index)=>`<button type="button" role="tab" data-dossier-tab="${key}" class="${index===0?'active':''}">${label}</button>`).join('');
  head.insertAdjacentElement('afterend',tabs);

  const panels={};
  for(const [key] of TAB_ORDER){
    const panel=document.createElement('div');
    panel.className=`dossier-panel${key==='overview'?'':' hidden'}`;
    panel.dataset.dossierPanel=key;
    panels[key]=panel;
    tabs.insertAdjacentElement('afterend',panel);
  }
  // Reinsert panels in canonical order after tabs.
  let anchor=tabs;
  for(const [key] of TAB_ORDER){anchor.insertAdjacentElement('afterend',panels[key]);anchor=panels[key]}

  const overview=document.createElement('section');
  overview.className='dossier-overview-note';
  overview.innerHTML='<strong>Article dossier</strong><p>Resumo estruturado do Workbench. O detalhe não contém full text integral e não representa decisão científica.</p>';
  panels.overview.appendChild(overview);

  for(const section of sections)panels[classifySection(section)].appendChild(section);

  const review=document.createElement('section');
  review.className='human-review-locked';
  review.innerHTML='<strong>Human review status</strong><p>O Article 1 atual permanece em corpus de discovery/calibração. Decisões formais de screening não são registradas nesta tela.</p><a href="/review.html">Open Review Control Center →</a>';
  panels.review.appendChild(review);

  const methodsBoundary=document.createElement('p');
  methodsBoundary.className='dossier-boundary';
  methodsBoundary.textContent='Campos de método são exibidos apenas quando materializados no snapshot/excerpts. Ausência de campo não é preenchida por inferência.';
  panels.methods.appendChild(methodsBoundary);

  const evidenceBoundary=document.createElement('p');
  evidenceBoundary.className='dossier-boundary';
  evidenceBoundary.textContent='Result bundles e excerpts são artefatos candidatos rastreáveis. Não são EvidenceClaims aceitos até revisão científica apropriada.';
  panels.evidence.appendChild(evidenceBoundary);

  tabs.addEventListener('click',event=>{const button=event.target.closest('[data-dossier-tab]');if(button)activateTab(detail,button.dataset.dossierTab)});
}

if(detail){
  const observer=new MutationObserver(()=>enhanceDossier());
  observer.observe(detail,{childList:true,subtree:false});
  enhanceDossier();
}
