(function hydrateCorpusFiltersFromUrl(){
  const params=new URLSearchParams(window.location.search);
  const mappings={
    document_class:'classFilter',
    source_provider:'providerFilter',
    full_text_status:'fullTextFilter',
    tier:'tierFilter',
    sort:'sortFilter',
    q:'articleQuery'
  };
  for(const [param,id] of Object.entries(mappings)){
    const value=params.get(param);if(!value)continue;
    const node=document.getElementById(id);if(!node)continue;
    if(node.tagName==='SELECT'){
      if([...node.options].some(option=>option.value===value))node.value=value;
    }else node.value=value;
  }
})();
