# Changelog

Mudanças públicas relevantes do NutEV Reference Engine são registradas aqui. O histórico completo de implementação permanece disponível no Git.

## [Unreleased]

### Documentação e governança

- README principal reescrito a partir do comportamento real da `main`.
- POP operacional consolidado para instalação, atualização, execução, retomada, validação e registro de runs.
- Arquitetura e pesos reais do ranking documentados em `docs/ARCHITECTURE.md`.
- Limitações conhecidas documentadas em `docs/KNOWN_LIMITATIONS.md`.
- Documentação de providers alinhada aos perfis `operational` e `deep`.
- Templates de issue/PR e políticas do repositório alinhados ao escopo atual do Reference Engine.
- Documentação de segurança corrigida para refletir `project_output_reference` e o fato de que `.env` não é carregado automaticamente.

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
