# Changelog

Mudanças públicas relevantes do NutEV Reference Engine são registradas aqui. O histórico completo de implementação permanece disponível no Git.

## [Unreleased]

### Scientific Workspace v2

- Adicionado `/quality.html` como **Quality Observatory** somente-leitura para saúde operacional, proveniência, retrieval, completude de metadados, mapeamento, providers e estado dos gates, sem representar esses sinais como qualidade metodológica da evidência.
- Corrigida a interpretação do gate PRESS no dashboard: `NOT_YET_RECORDED_AS_PASS` não pode mais ser aceito por correspondência de substring; somente o valor canônico exato `PASS` aprova a apresentação do gate.
- Adicionado `tools/audit_scientific_workspace_v2.py`, death test adversarial executável para detectar regressões de semântica científica, mutações indevidas, promoção prematura de C4, vazamento de ranking no snapshot, falsa semântica PRISMA e totais de produção hardcoded.
- O job de CI `audit guardrail contract` passou a executar explicitamente o death test, além do contrato fail-closed de ranking.
- Adicionados testes específicos para Quality Observatory e para a regressão do parser de PRESS.
- Adicionado `/intelligence.html` como **Scientific Intelligence / Synthesis Layer** rank-blind, com síntese estrutural por domínio, classes documentais, rotas, cobertura de result bundles e sinais de cobertura do corpus.
- A inspeção de achados usa carregamento lazy de até 24 dossiês por domínio, com concorrência limitada e sem enviar full text integral ou o corpus detalhado inteiro ao navegador.
- Recorrência de outcome é apresentada apenas como rótulo estruturado repetido no lote carregado; convergência/divergência permanece fila de comparação para revisão humana, sem classificação automática de agreement, contradiction ou certainty.
- Sinais de baixa representação são explicitamente tratados como `corpus coverage signals`, nunca como `evidence gap` automático.
- O Scientific Workspace death test agora também falha se a synthesis layer reintroduzir ranking, mutações, consenso por recorrência, evidence gap automático ou carregamento detalhado não limitado.
- Adicionado `/synthesis-review.html` como **Human Synthesis Review**, com adjudicação pairwise explícita de comparabilidade em população, construct/intervenção, outcome e timeframe, seguida de relação humana `CONVERGENT`, `DIVERGENT`, `COMPLEMENTARY`, `NOT_COMPARABLE` ou `UNCLEAR`.
- Julgamentos humanos exigem identificação do revisor e justificativa mínima antes de serem salvos; nenhuma relação é preselecionada ou inferida automaticamente pelo frontend.
- O estado da Human Synthesis Review é um rascunho `canonical:false` armazenado somente no navegador, sem POST científico ao servidor e sem mutar PRESS, GF-10, freeze, screening, RoB, certainty ou PRISMA.
- A Human Synthesis Review agora deriva `context_fingerprint` determinístico de `search_id`, `context_version`, pergunta, SHA-256 do Workbench, SHA-256 do manifest de rotas, versão de review profile e contagem de Article Summaries; o armazenamento local também é escopado por esse fingerprint para não reutilizar silenciosamente decisões após rebuild do contexto.
- A exportação `NUTEV_HUMAN_SYNTHESIS_REVIEW_DRAFT_V1` inclui `context_source`, `context_fingerprint`, snapshots source-linked dos achados, decisões humanas e SHA-256 determinístico do conteúdo científico, permanecendo explicitamente não canônica.
- O death test adversarial passou a bloquear adjudicação automática, revisão anônima/sem justificativa, POST/LLM externo, detalhes não limitados, ausência de context fingerprint e qualquer export que silenciosamente crie claims, screening, RoB, certainty ou PRISMA.
- Adicionado `/synthesis-brief.html` como **Human Synthesis Brief**, que importa a revisão humana somente no navegador e libera apresentação/export apenas após validar tipo do artefato, semântica humana, content SHA-256 e correspondência do context fingerprint com o Article 1 atual.
- O Brief rejeita decisões duplicadas, pares inválidos, snapshots sem bundle/result text e artefatos cujos guardrails não confirmem explicitamente que relações foram human-entered e que nenhum EvidenceClaim, screening, RoB, certainty, PRISMA ou formal-search state foi criado.
- `NUTEV_HUMAN_SYNTHESIS_BRIEF_V1` permanece `canonical:false`, preserva os julgamentos source-linked, produz SHA-256 próprio e oferece Print/PDF para apresentação executiva sem converter contagens de relações em evidence strength, meta-analysis ou certainty.
- A documentação/UI agora explicita que SHA-256 verifica consistência/integridade de conteúdo, mas **não prova autoria, autenticidade da identidade do revisor nem validade científica**.
- A CI passou a executar `node --check` também em `synthesis-brief.js`, e a suíte/death test cobrem a cadeia `Scientific Intelligence -> Human Synthesis Review -> Human Synthesis Brief`.
- Adicionado `/synthesis-governance.html` como **Synthesis Governance Registry**, uma superfície de coordenação local-only para registrar Briefs verificados sem converter importação em aprovação automática.
- O registry persiste o Brief pelo `content_sha256` e mantém entradas metadata-only com estados `STAGED`, `APPROVED_FOR_GOVERNED_USE` e `REJECTED_BY_GOVERNANCE`; staging repetido do mesmo Brief é idempotente.
- Os endpoints `GET /api/synthesis/governance`, `POST /api/synthesis/governance/stage` e `POST /api/synthesis/governance/decide` exigem loopback; o limite ampliado de 2 MiB é aplicado somente aos payloads de governance, mantendo 256 KiB como padrão da API.
- O servidor revalida tipo, guardrails, decisões humanas, `content_sha256`, `source_context_fingerprint`, search id, context version e pergunta antes do staging; ele não confia na validação browser-side do Brief.
- Aprovação/rejeição exige nome do responsável e justificativa mínima, reabre o Brief imutável no artifact store e revalida fonte/contexto no momento da decisão. Mudança do Workbench após staging bloqueia a decisão.
- `APPROVED_FOR_GOVERNED_USE` é explicitamente governance approval, não certainty, RoB, EvidenceClaim, meta-analysis, PRISMA ou canonical scientific synthesis; todas as entradas mantêm `canonical_scientific_synthesis_created:false`.
- O registry registra que reviewer/governor names não são identidades criptograficamente autenticadas nesta fase.
- Adicionado `tools/audit_synthesis_governance.py`; o job de guardrail do CI passou a executar o death test de governance além do Scientific Workspace death test, e o lint verifica a sintaxe de `synthesis-governance.js`.

### Documentação e governança

- README principal reescrito a partir do comportamento real da `main`.
- POP operacional consolidado para instalação, atualização, execução, retomada, validação e registro de runs.
- Arquitetura e pesos reais do ranking documentados em `docs/ARCHITECTURE.md`.
- Limitações conhecidas documentadas em `docs/KNOWN_LIMITATIONS.md`.
- Documentação de providers alinhada aos perfis `operational` e `deep`.
- Templates de issue/PR e políticas do repositório alinhados ao escopo atual do Reference Engine.
- Documentação de segurança corrigida para refletir `project_output_reference` e o fato de que `.env` não é carregado automaticamente.
- Documentado o contrato do Quality Observatory e do Scientific Workspace death test em `docs/QUALITY_OBSERVATORY.md`.
- Documentado o contrato da Scientific Intelligence / Synthesis Layer em `docs/SCIENTIFIC_INTELLIGENCE.md`.
- Documentado o fluxo de adjudicação humana e export não canônico em `docs/HUMAN_SYNTHESIS_REVIEW.md`.
- Documentado o contrato de verificação, context fingerprint, fronteira criptográfica e export executivo em `docs/HUMAN_SYNTHESIS_BRIEF.md`.
- Documentado o registry servidor-local, estados de governance, idempotência, revalidação no momento da decisão e fronteira `governance approval != scientific canonization` em `docs/SYNTHESIS_GOVERNANCE_REGISTRY.md`.

### Correções pós-v1.0.0 já presentes na main

- Perfil de coleta `operational` passou a ser o padrão para a primeira execução, mantendo os limites maiores via `NUTEV_DEEP_COLLECTION=1`.
- O terminal passou a exibir perfil e limites antes da coleta de rede.
- HTTP `401`/`403` nas interfaces nativas LILACS/BVS e SciELO passou a ser tratado como estado explícito `unavailable` em vez de falha fatal da rota latino-americana.
- Uma execução real no Windows foi registrada com status `COMPLETE`, 8.702 entradas no ranking, 115 grupos de taxonomia e TOP 100.
- DOI real da versão 1.0.0 foi registrado na documentação/citação após a publicação do arquivo Zenodo, sem mover a tag.

## [1.0.0] - 2026-08-18

### Produto

- Estabelecida a identidade **NutEV Reference Engine**.
- Definido o fluxo suportado:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

- Repositório reduzido ao escopo de descoberta, normalização, deduplicação por identidade, ranking e exportação de referências.
- Removidas superfícies antigas de revisão científica, orquestração, UI/API, OCR/full text e análise que não pertenciam ao produto final suportado.

### Providers

- PubMed.
- Europe PMC.
- OpenAlex.
- Crossref.
- DOAJ.
- Semantic Scholar.
- Fontes oficiais/institucionais configuradas.
- LILACS/BVS nativo.
- SciELO nativo.
- Google Programmable Search, Brave e SerpAPI quando configurados.

Scopus e Web of Science não são simulados.

### Ranking

- Carregamento de todos os arquivos `keyword_taxonomy*.json`.
- Focus keywords configuráveis.
- Pesos por provider.
- Sinais textuais de tipo documental.
- Bônus por presença de DOI/PMID/PMCID.
- Bônus leve de recência.
- Ordenação estável para os mesmos registros/configuração.
- Faixas A/B/C como prioridade de leitura.

### Deduplicação

- Regra de identidade baseada, em ordem, em DOI, PMID, URL e título normalizado.
- Preferência pela versão com texto descritivo mais rico quando a identidade coincide.

Essa regra não equivale a deduplicação semântica completa.

### Outputs

- `TOP_REFERENCIAS.md`.
- `reference_ranking.csv`.
- `reference_ranking.jsonl`.
- `latest.json`.

### Release e arquivo

- Versão: `1.0.0`.
- Tag publicada: `v1.0.0`.
- Release commit: `5728d79b05e618897f01ba93886a17584c9f215f`.
- GitHub Release publicada em 18/08/2026.
- Zenodo record: `21998607`.
- DOI da versão: `10.5281/zenodo.21998607`.

O DOI foi incorporado à documentação corrente após a criação real do registro Zenodo; a tag `v1.0.0` permaneceu imutável.

[Unreleased]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/WillianVagner123/NutEV-Evidence-Engine/releases/tag/v1.0.0
