# Limitações conhecidas

Este documento descreve limitações atuais do **NutEV Reference Engine**. Elas fazem parte do contrato do produto e devem permanecer explícitas em qualquer uso científico.

## 1. Estado científico: benefício incremental ainda não demonstrado

O estado atual do projeto permanece:

```text
B — DEMOTE
```

O Engine funciona como utilitário operacional/experimental, mas ainda não possui demonstração externa de benefício científico incremental sobre baselines ou ferramentas existentes.

Até existir gold standard independente e benchmark reproduzível, métricas como recall, precision, MAP, MRR, nDCG, workload reduction e generalização permanecem `NOT_TESTED` quando não houver dados reais.

## 2. Ranking não é qualidade científica

O score é uma heurística de prioridade de leitura. Ele combina sinais de taxonomia, focus keywords, tipo documental, provider, identificador válido, recência e penalidades de metadados.

Ele não mede diretamente:

- risco de viés;
- qualidade metodológica;
- certeza da evidência;
- força de recomendação;
- elegibilidade para revisão;
- aplicabilidade clínica.

Um item com score maior pode ser cientificamente menos importante para uma pergunta específica.

## 3. Pesos do ranking ainda não foram calibrados externamente

Os pesos e caps atuais são regras de engenharia versionadas. Ainda não foi demonstrado que a combinação vigente supera baselines simples ou permanece estável sob perturbação dos parâmetros.

A validação prevista inclui ablation study e sensitivity analysis antes de qualquer claim forte sobre o ranking.

## 4. A taxonomia é canônica e versionada, mas ainda não validada externamente

A taxonomia ativa é compilada pelo `config/taxonomy_registry.json`, versão `2026-08-v2`, nas dimensões:

```text
domain
context
condition
outcome
```

Os `keyword_taxonomy*.json` são fontes de vocabulário; o registry controla quais caminhos viram grupos canônicos.

`workstreams.*` e `global.document_types.*` são excluídos do score taxonômico. Caminhos semânticos não registrados causam falha em vez de criar categoria silenciosa.

Isso garante controle estrutural, mas **não prova validade de conteúdo**, concordância com especialistas ou capacidade classificatória suficiente. Esses pontos ainda exigem validação humana independente.

## 5. `taxonomy_primary` é uma convenção determinística

A escolha da taxonomia primária segue regras programadas e não deve ser interpretada automaticamente como o tema cientificamente dominante do documento.

A regra de prioridade entre dimensões deve ser testada contra classificação humana antes de ser tratada como válida externamente.

## 6. Deduplicação é determinística, não semântica/work-level

Coleta e ranking usam o mesmo contrato canônico em `src/nutev/reference_identity.py`:

```text
DOI válido -> PMID válido -> URL HTTP(S) normalizada -> título normalizado
```

Isso elimina a inconsistência anterior entre as duas etapas, mas não resolve todos os casos de equivalência intelectual.

Podem permanecer separados:

- republicações;
- versões preprint/final;
- traduções;
- guidelines publicados paralelamente;
- documentos irmãos;
- registros equivalentes com identificadores diferentes.

`records_unique == records_input` significa apenas que a regra ativa não removeu nenhum registro; não prova unicidade semântica.

## 7. Identificador sintaticamente válido não é identificador resolvido

DOI, PMID e PMCID precisam ter formato plausível para receber classe `A_IDENTIFIER` e bônus de identificador.

Entretanto, a validação sintática não prova que:

- o DOI existe na agência registradora;
- o PMID/PMCID resolve;
- o identificador corresponde ao título esperado;
- o provider forneceu o identificador correto.

Resolução bibliográfica e leitura crítica permanecem externas ao gate.

## 8. Provider pode influenciar o score

A configuração atual atribui pesos diferentes a providers. Ainda não foi demonstrado que essa diferença melhora relevância independente.

Até existir benchmark `leave-one-provider-out` e teste de provider bias, esses pesos devem ser tratados como heurística não validada, não como proxy de qualidade científica.

## 9. Assimetria de metadados pode influenciar o ranking

Providers oferecem níveis diferentes de detalhe para:

- abstract;
- keywords;
- autores;
- tipo documental;
- datas;
- identificadores;
- URLs.

Como o score usa parte desses campos, a riqueza do metadata pode alterar a posição de uma obra sem que sua relevância científica tenha mudado. O efeito ainda precisa ser quantificado.

## 10. Tipos documentais são inferidos principalmente pelo título

Expressões como `clinical practice guideline`, `consensus`, `systematic review` e similares podem gerar bônus.

A política impede empilhamento de expressões sobrepostas, mas ainda pode haver falso positivo ou falso negativo textual.

## 11. A quarentena pode reduzir recall

Registros `Q_*` não entram no ranking por padrão.

Classes atuais:

- `Q_INCOMPLETE_ORIGIN`;
- `Q_INVALID_IDENTIFIER`;
- `Q_UNTRACEABLE`.

Isso protege rastreabilidade, mas pode excluir referências reais com metadados incompletos. A perda de recall atribuível à quarentena ainda é `NOT_TESTED` até revisão humana de uma amostra apropriada.

Correções devem vir do dado-fonte; o Engine não deve preencher metadados por suposição.

## 12. Hashes provam integridade de arquivo, não verdade externa

`master_records_sha256`, hashes de configuração e hashes de output permitem detectar alteração em relação ao manifesto.

Eles não constituem assinatura do PubMed, Crossref, OpenAlex ou outro provider e não validam a verdade científica do registro.

## 13. Limites de coleta não equivalem a exaustividade

Os perfis operacional e profundo usam tetos por provider. Cobertura depende também de:

- consulta configurada;
- indexação;
- paginação;
- rate limits;
- credenciais;
- falhas temporárias;
- idiomas;
- disponibilidade de metadata.

Aumentar o limite não transforma o sistema em busca exaustiva.

## 14. BVS/LILACS e SciELO podem ficar indisponíveis para automação

Respostas `401`/`403` ou outras falhas de interface são registradas como indisponibilidade da rota automatizada.

`unavailable` **não significa zero literatura**. Significa que aquela fonte não foi obtida por aquela rota naquela execução.

## 15. Scopus e Web of Science não são simulados

Sem acesso licenciado/configurado, essas bases não participam da coleta real. O Engine não cria resultados substitutos com esses rótulos.

## 16. Providers opcionais dependem de credenciais

Google Programmable Search, Brave e SerpAPI só executam quando suas credenciais estão disponíveis. Execuções com combinações diferentes de providers não têm cobertura equivalente.

## 17. APIs e metadados externos mudam

Uma mesma versão do software pode receber resultados diferentes em datas distintas porque bases bibliográficas e APIs são sistemas vivos.

A reprodutibilidade do software deve ser distinguida da estabilidade do universo bibliográfico externo.

## 18. TOP N não é o conjunto total

`TOP_REFERENCIAS.md` é uma janela de leitura prioritária. O conjunto elegível completo está em `reference_ranking.csv` e `reference_ranking.jsonl`; registros em quarentena ficam separados.

## 19. O runtime canônico não usa IA generativa para criar referências

O Engine não deve inventar DOI, autores, títulos, anos ou abstracts. Funções generativas futuras, se existirem, precisarão de contrato próprio de citação, proveniência, separação entre extração/inferência e revisão humana.

## 20. Não é revisão sistemática nem sistema clínico

O Reference Engine não é:

- protocolo PRISMA;
- screening científico automático;
- avaliação de risco de viés;
- avaliação de certeza da evidência;
- recomendação clínica;
- substituto de revisão humana.

## 21. Governança do repositório continua separada da validação científica

CI verde e guardrails corretos são necessários, mas não suficientes para validação científica. Regras administrativas do GitHub, proteção de branch e metadata do repositório também não constituem evidência de desempenho científico.

## 22. Uso recomendado

Use o Engine para:

1. descoberta e agregação de referências candidatas;
2. organização taxonômica;
3. prioridade técnica de leitura;
4. inspeção de proveniência e `score_breakdown`;
5. curadoria humana posterior.

Não use `reference_score`, faixa A/B/C ou `taxonomy_primary_rank` como justificativa isolada de inclusão, exclusão, qualidade ou recomendação científica.

## 23. Próxima fronteira de validação

O protocolo em `validation/` exige, antes de promoção científica do produto:

- gold standard independente;
- baselines apropriados;
- benchmark quantitativo;
- ablations;
- validação da taxonomia contra humanos;
- benchmark de deduplicação;
- provider/metadata bias;
- perda de recall da quarentena;
- sensibilidade do score;
- teste externo selado;
- estudo de workload quando aplicável.

Ausência desses dados deve continuar sendo reportada como `NOT_TESTED` ou `INSUFFICIENT_EVIDENCE`, nunca como resultado positivo implícito.
