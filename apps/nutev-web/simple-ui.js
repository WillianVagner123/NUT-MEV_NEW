const SIMPLE_REPLACEMENTS=[
  ['engine conectado','online'],
  ['engine indisponível','indisponível'],
  ['Radar ainda sem snapshot','Panorama ainda sem dados'],
  ['Radar bloqueado.','Não foi possível carregar o panorama.'],
  ['Carregando auditoria verificada…','Carregando panorama…'],
  ['Tópicos / competências','Temas acompanhados'],
  ['Documentos únicos','Documentos encontrados'],
  ['Providers observados','Fontes consultadas'],
  ['Tópicos com gaps','Temas que precisam de atenção'],
  ['Busca ativa requerida','Temas para pesquisar'],
  ['P1 · alta','Prioridade alta'],
  ['P2 · média','Prioridade média'],
  ['P3 · baixa','Prioridade baixa'],
  ['P4 · monitorar','Em dia'],
  ['Full text','Texto completo'],
  ['Semântica','Conteúdo organizado'],
  ['Relações','Informações conectadas'],
  ['Watch ainda não executado','Sem histórico ainda'],
  ['Watch desatualizado','Histórico precisa ser atualizado'],
  ['Watch baseline verificado','Primeira leitura registrada'],
  ['Watch verificado','Histórico atualizado'],
  ['zero verificado','nenhum resultado confirmado'],
  ['não executado','ainda não pesquisado'],
  ['manual/licenciado','acesso manual'],
  ['status-aware','monitorado'],
  ['Preview auditável','Prévia da estratégia'],
  ['Modo revisão ativo. Escolha construtor ou estratégia exata.','Opções de revisão abertas.'],
  ['A estratégia só será usada quando este modo estiver ativado.','Use somente se estiver fazendo uma revisão estruturada.'],
  ['fontes conectadas no modo web','fontes disponíveis']
];

function simplifyTextNode(node){
  if(!node?.parentElement)return;
  if(node.parentElement.closest('code,pre,textarea,input,select,option'))return;
  let value=node.nodeValue;
  for(const [from,to] of SIMPLE_REPLACEMENTS)value=value.replaceAll(from,to);
  if(value!==node.nodeValue)node.nodeValue=value;
}

function simplifyTree(root=document.body){
  if(!root)return;
  const walker=document.createTreeWalker(root,NodeFilter.SHOW_TEXT);
  const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
  nodes.forEach(simplifyTextNode);
}

function simplifyStatusAttributes(){
  document.querySelectorAll('[title]').forEach(el=>{
    let value=el.getAttribute('title')||'';
    for(const [from,to] of SIMPLE_REPLACEMENTS)value=value.replaceAll(from,to);
    el.setAttribute('title',value);
  });
}

function applySimpleUI(){simplifyTree();simplifyStatusAttributes()}

const observer=new MutationObserver(mutations=>{
  for(const mutation of mutations){
    if(mutation.type==='characterData')simplifyTextNode(mutation.target);
    for(const node of mutation.addedNodes){if(node.nodeType===Node.TEXT_NODE)simplifyTextNode(node);else if(node.nodeType===Node.ELEMENT_NODE)simplifyTree(node)}
  }
});

applySimpleUI();
observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true});
