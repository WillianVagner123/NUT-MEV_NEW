export const DOCUMENT_CLASS_ONTOLOGY_VERSION='nutev-document-class-v1';

export const DOCUMENT_CLASSES={
  evidence_synthesis:{label:'Síntese de evidência',members:['evidence_synthesis']},
  guidance:{label:'Diretriz / orientação',members:['guidance','food_based_dietary_guideline','clinical_practice_guideline','consensus_statement','position_statement']},
  framework_implementation:{label:'Framework / implementação',members:['framework_implementation','framework_model','competency_curriculum','implementation_evaluation']},
  primary_randomized:{label:'Ensaio randomizado',members:['primary_randomized']},
  primary_observational:{label:'Estudo observacional',members:['primary_observational']},
  primary_qualitative:{label:'Estudo qualitativo',members:['primary_qualitative']},
  review:{label:'Revisão',members:['review']},
  unclassified:{label:'Não classificado',members:['unclassified']},
};

export const DOCUMENT_SUBTYPE_LABELS={
  evidence_synthesis:'Síntese de evidência',
  guidance:'Diretriz / orientação',
  food_based_dietary_guideline:'Guia alimentar / FBDG',
  clinical_practice_guideline:'Diretriz clínica',
  consensus_statement:'Consenso',
  position_statement:'Position / scientific statement',
  framework_implementation:'Framework / implementação',
  framework_model:'Framework / modelo operacional',
  competency_curriculum:'Competências / currículo',
  implementation_evaluation:'Implementação / viabilidade',
  primary_randomized:'Ensaio randomizado',
  primary_observational:'Estudo observacional',
  primary_qualitative:'Estudo qualitativo',
  review:'Revisão',
  unclassified:'Não classificado',
};

const MEMBER_TO_CANONICAL=new Map();
for(const [canonical,definition] of Object.entries(DOCUMENT_CLASSES))for(const member of definition.members)MEMBER_TO_CANONICAL.set(member,canonical);

export function canonicalDocumentClass(value){
  const normalized=String(value||'').trim();
  return MEMBER_TO_CANONICAL.get(normalized)||'unclassified';
}

export function documentClassLabel(value){
  const canonical=canonicalDocumentClass(value);
  return DOCUMENT_CLASSES[canonical]?.label||DOCUMENT_CLASSES.unclassified.label;
}

export function documentSubtypeLabel(value){
  const normalized=String(value||'').trim();
  return DOCUMENT_SUBTYPE_LABELS[normalized]||normalized||DOCUMENT_SUBTYPE_LABELS.unclassified;
}

export function documentClassOptions(){
  return Object.entries(DOCUMENT_CLASSES).map(([value,definition])=>({value,label:definition.label}));
}
