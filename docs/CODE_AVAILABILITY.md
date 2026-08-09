# Disponibilidade de código / Code availability

Parágrafos preparados para a seção de **Disponibilidade de código** do manuscrito.

> Substitua somente campos explicitamente marcados como `HUMAN INPUT REQUIRED` quando os valores reais forem confirmados. Não inventar DOI, ORCID ou afiliação.

## Português

O software utilizado neste estudo — **NutEV Evidence Engine** — está disponível publicamente sob licença **MIT** no repositório GitHub `WillianVagner123/NutEV-Evidence-Engine`. A release citável reconciliada é a versão **0.2.0** (tag Git **`v0.2.0`**), publicada em **9 de agosto de 2026**, mantendo-se a classificação de maturidade científica **alpha**. As tags históricas `v0.1.0`–`v0.1.8` permanecem preservadas e não são reutilizadas. O DOI específico da versão Zenodo deverá ser inserido somente após verificação do registro arquivado: **HUMAN INPUT REQUIRED — DOI da versão Zenodo**.

O projeto evoluiu de uma base de código aberto sob licença MIT (*Local Deep Research*, LearningCircuit). O motor herdado foi removido da árvore atual do projeto; sua proveniência histórica e a atribuição original permanecem documentadas no `NOTICE.md`, no `LICENSE` e no histórico Git. O software foi desenvolvido para apoiar a **organização, rastreabilidade, deduplicação, classificação, extração estruturada, auditoria e revisão humana** do corpus documental relacionado à Nutrição do Estilo de Vida.

O sistema **não fornece diagnóstico, prescrição individual ou recomendação clínica final**. Saídas computacionais, incluindo `RecommendationCandidate`, permanecem candidatas sujeitas à revisão e adjudicação humana. Decisões de inclusão, exclusão, codificação e interpretação científica permanecem sob responsabilidade de revisores humanos conforme a governança metodológica do projeto. Este repositório corresponde à camada de **Evidence Engine** e **não contém nem executa** o *Clinical Decision Engine*, que constitui artefato distinto.

Para execuções científicas, o software diferencia o espaço de queries gerado das expressões efetivamente tentadas e mantém `query_execution_ledger.json/.csv` como evidência de tentativa no pipeline genérico. Para buscas formais congeladas em bases indexadas, o executor de estratégia mantém adicionalmente expressão exata, snapshot bruto, SHA-256 e manifesto da execução. A conclusão computacional de uma rodada é separada de `scientific_readiness`; o software não infere aprovação humana ou prontidão de manuscrito apenas porque a execução terminou.

Em conformidade com direitos autorais e governança de dados, a release do software não deve redistribuir PDFs ou textos integrais protegidos, dados pessoais ou clínicos, credenciais, bases locais privadas ou outputs científicos não autorizados. A documentação pública deve priorizar metadados, URLs oficiais, DOI e os trechos mínimos necessários à auditoria.

## English

The software used in this study — the **NutEV Evidence Engine** — is publicly available under the **MIT license** in the GitHub repository `WillianVagner123/NutEV-Evidence-Engine`. The reconciled citable software release is version **0.2.0** (Git tag **`v0.2.0`**), published on **August 9, 2026**, while its scientific maturity remains explicitly classified as **alpha**. Historical tags `v0.1.0`–`v0.1.8` are preserved and are not reused. The version-specific Zenodo DOI must be inserted only after the archived record has been verified: **HUMAN INPUT REQUIRED — Zenodo Version DOI**.

The project evolved from an MIT-licensed open-source base (*Local Deep Research*, LearningCircuit). The inherited engine has been removed from the current source tree; its historical provenance and original attribution remain documented in `NOTICE.md`, `LICENSE`, and the Git history. The software supports the **organization, traceability, deduplication, classification, structured extraction, auditing, and human review** of the documentary corpus related to Lifestyle Nutrition.

The system **does not provide diagnosis, individual prescription, or final clinical recommendations**. Computational outputs, including `RecommendationCandidate`, remain candidates subject to human review and adjudication. Inclusion, exclusion, coding, and scientific interpretation decisions remain the responsibility of human reviewers under the project's methodological governance. This repository represents the **Evidence Engine** layer and **does not contain or execute** the separate *Clinical Decision Engine*.

For scientific runs, generated query space is separated from expressions actually attempted, with `query_execution_ledger.json/.csv` serving as generic-pipeline attempt evidence. Frozen formal indexed-database executions additionally preserve exact expressions, raw snapshots, SHA-256 values, and run manifests. Computational completion is kept separate from `scientific_readiness`; the software does not infer human approval or manuscript readiness merely from a completed run.

In accordance with copyright and data-governance requirements, the software release must not redistribute protected third-party PDFs/full texts, personal or clinical data, credentials, private local databases, or unauthorized scientific outputs. Public documentation should preferentially share metadata, official URLs, DOIs, and only the minimum excerpts required for verification.

## Campos a confirmar antes da submissão

| Campo | Estado |
|---|---|
| Versão do software | `0.2.0` |
| Tag publicada | `v0.2.0` |
| Data da release | `2026-08-09` |
| Maturidade | alpha |
| DOI da versão Zenodo | HUMAN INPUT REQUIRED — somente após verificação do registro |
| ORCID do(s) creator(s) | HUMAN INPUT REQUIRED / omitir se ainda não confirmado |
| Afiliação institucional exata | HUMAN INPUT REQUIRED / omitir se ainda não confirmada |
| DOI do Artigo 1 relacionado | preencher somente se existir e for pertinente |