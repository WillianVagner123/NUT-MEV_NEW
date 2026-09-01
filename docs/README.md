# Documentação do NutEV Reference Engine

Esta pasta contém a documentação operacional, técnica, de auditoria, taxonomia, release e proveniência do produto suportado atualmente.

## Ordem recomendada de leitura

1. [`POP_USO_NUTEV_REFERENCE_ENGINE.md`](POP_USO_NUTEV_REFERENCE_ENGINE.md) — como instalar, atualizar, executar, verificar sucesso e recuperar falhas.
2. [`ARCHITECTURE.md`](ARCHITECTURE.md) — arquitetura real do pipeline, regras de deduplicação, scoring e contratos de saída.
3. [`TAXONOMY.md`](TAXONOMY.md) — taxonomia canônica, dimensões, grupos, rank dentro da taxonomia e governança de novos termos.
4. [`AUDITABILITY_AND_GUARDRAILS.md`](AUDITABILITY_AND_GUARDRAILS.md) — integridade, rastreabilidade, hashes, quarentena e comportamento fail-closed.
5. [`SEARCH_PROVIDERS.md`](SEARCH_PROVIDERS.md) — providers, limites, credenciais, estados `failed`/`unavailable` e comportamento de cobertura.
6. [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) — limitações conhecidas e interpretação responsável dos outputs.
7. [`QUALITY_OBSERVATORY.md`](QUALITY_OBSERVATORY.md) — saúde operacional do Scientific Workspace v2 e death test adversarial, sem confundir qualidade do sistema com qualidade da evidência.
8. [`SCIENTIFIC_INTELLIGENCE.md`](SCIENTIFIC_INTELLIGENCE.md) — síntese estrutural por domínio, achados candidatos lazy, recorrência de outcomes e filas humanas de convergência/divergência sem decisão científica automática.
9. [`HUMAN_SYNTHESIS_REVIEW.md`](HUMAN_SYNTHESIS_REVIEW.md) — adjudicação humana pairwise de comparabilidade e relação entre achados, com rascunho local, justificativa obrigatória, proveniência e export SHA-256 não canônico.
10. [`HUMAN_SYNTHESIS_BRIEF.md`](HUMAN_SYNTHESIS_BRIEF.md) — verificação fail-closed de content SHA/context fingerprint e apresentação executiva dos julgamentos humanos, sem transformar integridade em autenticidade ou validade científica.
11. [`SYNTHESIS_GOVERNANCE_REGISTRY.md`](SYNTHESIS_GOVERNANCE_REGISTRY.md) — registry servidor-local para staging e decisão explícita de governance, com revalidação de fonte/contexto e separação formal entre governance approval e canonical scientific synthesis.
12. [`GOVERNED_SYNTHESIS_RELEASE.md`](GOVERNED_SYNTHESIS_RELEASE.md) — pacote de disseminação auditável derivado exclusivamente de entradas `APPROVED_FOR_GOVERNED_USE`, com nova revalidação de fonte/contexto, hash próprio e fronteira explícita entre disseminação governada e inferência científica.
13. [`GOVERNED_PUBLICATION_MANIFEST.md`](GOVERNED_PUBLICATION_MANIFEST.md) — publication manifest com citation bundle source-linked e `PUBLICATION_STATEMENT_CANDIDATE`, revalidando o Governed Release e impedindo promoção automática para EvidenceClaim aceito.
14. [`EVIDENCE_CLAIM_REVIEW.md`](EVIDENCE_CLAIM_REVIEW.md) — revisão humana claim-by-claim de citations atômicas, com EvidenceRecord referential-integrity gate e promoção explícita para EvidenceClaim source-level canônico somente após `ACCEPT`.
15. [`VALIDATED_WINDOWS_RUN_2026-08-18.md`](VALIDATED_WINDOWS_RUN_2026-08-18.md) — registro de uma execução real bem-sucedida anterior à taxonomia canônica v2.

## Release, DOI e proveniência

- [`RELEASE_V1_0_0.md`](RELEASE_V1_0_0.md) — identidade e conteúdo da release estável `v1.0.0`.
- [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md) — checklist para futuras releases.
- [`ZENODO_SETUP.md`](ZENODO_SETUP.md) — publicação GitHub/Zenodo e regra de DOI.
- [`PROVENANCE_AND_LICENSE.md`](PROVENANCE_AND_LICENSE.md) — proveniência do código e fronteira de licenciamento.
- [`REFERENCE_ENGINE_CLEANUP_AUDIT.md`](REFERENCE_ENGINE_CLEANUP_AUDIT.md) — auditoria histórica da redução do repositório ao Reference Engine.

## Produto suportado

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> CLASSIFY -> RANK -> EXPORT
```

Entrada operacional no Windows:

```text
Iniciar-NutEV-Windows.bat
```

Fluxo interno:

```text
Iniciar-NutEV-Windows.bat
  -> RODAR_TUDO.cmd
     -> run_everything_now.cmd
        -> tools/run_everything_now.py
     -> tools/run_latin_sources.py
     -> tools/rank_references.py
```

## Taxonomia canônica

Os arquivos `keyword_taxonomy*.json` preservam o vocabulário acumulado do projeto. A classificação usada no ranking é organizada por `config/taxonomy_registry.json` em quatro dimensões estáveis:

```text
domain
context
condition
outcome
```

Estruturas históricas `workstreams.*` e `global.document_types.*` não entram no score taxonômico. Novos caminhos semânticos não registrados fazem a compilação da taxonomia falhar em vez de alterar silenciosamente o ranking.

## Saídas canônicas

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/reference_quarantine.jsonl
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
project_output_reference/reference_ranking/latest.json
```

O ranking exporta `reference_rank` global e também classificação/rank taxonômico por referência, incluindo `taxonomy_primary`, `taxonomy_primary_rank`, `taxonomy_secondary`, `taxonomy_group_scores` e `taxonomy_ranks`.

## Fronteira de interpretação

O Reference Engine é uma ferramenta de **descoberta, classificação e priorização de leitura**. O Scientific Workspace também oferece superfícies de organização, síntese estrutural, registro de rascunhos de julgamento humano, apresentação executiva desses julgamentos, registry de governance local, preparação auditável de pacotes de disseminação governada, publication manifests com citations source-linked e uma camada explícita de revisão humana para aceitar proposições source-level como `EvidenceClaim`.

A aceitação de um EvidenceClaim na Fase 16 é estreita: significa que um revisor humano aceitou uma **proposição reportada pela fonte**, vinculada a um `EvidenceRecord` materializado e revalidado. Ela não converte a proposição em verdade científica, não inclui o artigo em uma revisão e não avalia a qualidade da evidência.

Ele não substitui:

- triagem científica;
- avaliação metodológica;
- avaliação de risco de viés;
- avaliação de certainty;
- síntese formal de evidências;
- autenticação da identidade de revisores, responsáveis de governance, preparadores de release ou responsáveis de publicação;
- decisão clínica;
- julgamento humano sobre a pertinência de uma referência.

`APPROVED_FOR_GOVERNED_USE` é um estado de governance do registry. Não significa certeza, qualidade metodológica, inclusão PRISMA ou canonical scientific synthesis.

`NUTEV_GOVERNED_SYNTHESIS_RELEASE_V1` é um pacote de disseminação `canonical:false`. Seu hash e seu release record documentam integridade/proveniência do package, não validade científica, autoria autenticada, certeza ou meta-análise.

`NUTEV_GOVERNED_PUBLICATION_MANIFEST_V1` também permanece `canonical:false`. Seus `PUBLICATION_STATEMENT_CANDIDATE` descrevem julgamentos humanos registrados e exigem autoria/edição humana; não são EvidenceClaims aceitos, recomendações, certainty, RoB, meta-analysis ou PRISMA.

`NUTEV_CANONICAL_EVIDENCE_CLAIM_RECORD_V1` é canônico apenas como registro NutEV de uma proposição source-level explicitamente aceita por revisão humana. Um claim aceito continua com `screening_eligibility_verified:false`, `claim_evaluation_created:false`, `risk_of_bias_assessed:false`, `certainty_assessed:false`, `evidence_set_created:false` e `clinical_recommendation_created:false`.

A deduplicação atual é orientada por DOI, PMID, URL e, como fallback, título normalizado. Ela não garante unicidade semântica entre publicações relacionadas.

## Evidência operacional registrada

Uma execução real no Windows, em 18/08/2026, terminou com status `COMPLETE`, `8.702` registros de entrada no ranking, `8.702` registros únicos segundo a regra então ativa, `115` grupos brutos de taxonomia carregados e TOP 100 exportado.

Esse registro é histórico. A taxonomia canônica v2 reorganiza os grupos para reduzir fragmentação e remover workstreams históricos do scoring; portanto, a contagem de grupos de futuras execuções não deve ser comparada diretamente com os `115` grupos do run anterior.

Esses números descrevem uma execução observada, não uma promessa de volume ou cobertura para execuções futuras.

## Release publicada

- versão: `1.0.0`
- tag: `v1.0.0`
- release commit: `5728d79b05e618897f01ba93886a17584c9f215f`
- Zenodo record: `21998607`
- DOI: `10.5281/zenodo.21998607`

A `main` pode conter correções pós-release. A tag publicada permanece imutável.
