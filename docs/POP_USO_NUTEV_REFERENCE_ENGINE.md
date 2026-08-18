# POP — Uso do NutEV Reference Engine

**Documento:** Procedimento Operacional Padrão  
**Produto:** NutEV Reference Engine  
**Versão estável publicada:** 1.0.0  
**Plataforma operacional principal:** Windows  
**Python suportado:** 3.12 ou 3.13  
**Fluxo atual da `main`:** `SEARCH -> NORMALIZE -> DEDUPLICATE -> TRACEABILITY GATE -> RANK -> EXPORT -> AUDIT`  
**DOI da versão publicada:** `10.5281/zenodo.21998607`

## 1. Objetivo

Padronizar instalação, atualização, execução, verificação, auditoria e interpretação do NutEV Reference Engine.

O software coleta referências em múltiplas fontes, normaliza metadados, verifica a integridade dos masters de coleta, aplica um gate de rastreabilidade, deduplica, calcula um score explicável e exporta resultados estruturados.

O runtime canônico não usa modelo generativo para inventar referências ou completar metadados ausentes.

O ranking não substitui critérios de elegibilidade, avaliação metodológica, síntese de evidências ou recomendação clínica.

## 2. Escopo e versão

Este POP cobre a branch `main` corrente de:

```text
WillianVagner123/NutEV-Evidence-Engine
```

A tag `v1.0.0` é o snapshot publicado e arquivado. Guardrails adicionados depois da release pertencem à `main` e não reescrevem a tag.

Antes de uma execução auditável, registrar:

```bat
git rev-parse HEAD
```

## 3. Responsabilidade do operador

O operador deve:

- usar Python 3.12 ou 3.13;
- atualizar `main` antes de uma execução corrente;
- registrar o SHA do repositório;
- não editar manualmente masters de coleta;
- não apagar checkpoints por padrão;
- verificar os códigos finais das três etapas;
- verificar `AUDIT_MANIFEST.json` e a quarentena;
- preservar manifests, hashes e outputs quando a execução for usada em pesquisa;
- tratar o ranking como prioridade de leitura, não como decisão científica automática;
- nunca preencher DOI/PMID/URL por suposição;
- não versionar credenciais ou dados privados.

## 4. Primeira instalação

No Prompt de Comando:

```bat
cd %USERPROFILE%
git clone https://github.com/WillianVagner123/NutEV-Evidence-Engine.git
cd NutEV-Evidence-Engine
Iniciar-NutEV-Windows.bat
```

O launcher cria `.venv` quando necessário, instala o projeto em modo editável e executa o pipeline suportado.

## 5. Atualização antes do uso

```bat
cd %USERPROFILE%\NutEV-Evidence-Engine
git checkout main
git pull --ff-only origin main
git rev-parse HEAD
```

Se o clone estiver em outro local, use a pasta correspondente.

## 6. Execução padrão

```bat
Iniciar-NutEV-Windows.bat
```

O fluxo deve mostrar:

```text
[1/3] COLETA MULTI-FONTE
[2/3] LILACS/BVS + SCIELO NATIVO
[3/3] RANKING DE REFERENCIAS
```

O perfil padrão é `operational`. Para coleta profunda:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

Depois, para voltar ao padrão na mesma sessão:

```bat
set NUTEV_DEEP_COLLECTION=
```

Limites maiores não significam cobertura exaustiva.

## 7. Critério de sucesso operacional

O final esperado é:

```text
Coleta geral: codigo 0
LILACS/BVS + SciELO: codigo 0
Ranking: codigo 0
SUCESSO: ranking de referencias gerado.
```

Confirmar a existência de:

```text
project_output_reference/reference_ranking/TOP_REFERENCIAS.md
project_output_reference/reference_ranking/reference_ranking.csv
project_output_reference/reference_ranking/reference_ranking.jsonl
project_output_reference/reference_ranking/reference_quarantine.jsonl
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
project_output_reference/reference_ranking/latest.json
```

Uma execução com registros em quarentena pode terminar com status:

```text
COMPLETE_WITH_QUARANTINE
```

Isso não é sinônimo de falha. Significa que itens sem rastreabilidade suficiente foram separados do ranking.

## 8. Guardrail de integridade — obrigatório

Cada manifesto de coleta que declara um master deve conter:

```text
master_records_path
master_records_sha256
```

Antes de ler o master, o ranker recalcula o SHA-256.

Se o hash real for diferente do hash declarado, a execução deve falhar com mensagem semelhante a:

```text
Guardrail failure: SHA-256 mismatch ...
```

Procedimento correto:

1. não editar o manifesto para “fazer bater”;
2. não alterar o master manualmente;
3. identificar por que o arquivo mudou;
4. restaurar o arquivo correspondente ao manifesto ou refazer a coleta;
5. executar novamente.

O sistema não deve continuar com um input cuja integridade declarada não possa ser comprovada.

## 9. Gate de rastreabilidade

Cada registro recebe uma classe:

| Classe | Critério |
|---|---|
| `A_IDENTIFIER` | possui DOI, PMID ou PMCID |
| `B_TRACEABLE_URL` | possui URL HTTP/HTTPS rastreável |
| `Q_INCOMPLETE_ORIGIN` | falta provider ou título |
| `Q_UNTRACEABLE` | sem identificador e sem URL rastreável |

Por padrão, `Q_*` vai para:

```text
reference_quarantine.jsonl
```

e não entra no ranking.

Para retirar um item da quarentena, corrija o dado na origem ou na etapa de coleta com evidência verificável. Não invente identificadores.

## 10. Auditoria de um registro

No `reference_ranking.jsonl`/CSV, verificar:

```text
audit_traceability
audit_origin_sha256
audit_source_run_id
audit_source_master_sha256
reference_provider
DOI / PMID / PMCID / URL
score_breakdown
matched_terms
taxonomy_groups
focus_keyword_hits
document_type_applied
```

`audit_origin_sha256` detecta mudança no payload de origem usado pelo engine. Ele não certifica a verdade científica do artigo.

## 11. Auditoria da execução

Abrir:

```text
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
```

Confirmar:

```text
"audit_type": "REFERENCE_RANKING_AUDIT"
"status": "PASS"
```

O manifesto contém:

- versão da política de guardrail;
- política ativa;
- masters e SHA-256 de entrada;
- SHA-256 de `reference_mode.json` e taxonomias usadas;
- contagem de registros recebidos, rastreáveis, em quarentena e únicos ranqueados;
- SHA-256 dos outputs;
- assertions de guardrail.

Para uma auditoria reproduzível, preservar esse manifesto junto com o SHA do Git e os manifests de coleta.

## 12. Score e proteção contra inflação

O ranker registra `score_breakdown` para cada referência.

A política atual limita:

```text
taxonomy_score_cap = 60
focus_score_cap = 40
```

Esses caps reduzem inflação decorrente de muitos grupos históricos ou termos redundantes.

Tipos documentais sobrepostos não acumulam bônus. Exemplo: um título contendo `clinical practice guideline` pode gerar hits também para `practice guideline` e `guideline`, mas somente o maior peso é aplicado.

O score continua sendo prioridade de recuperação, não nível de evidência.

## 13. Providers e indisponibilidade

O modo padrão tenta PubMed, Europe PMC, OpenAlex, Crossref, DOAJ, Semantic Scholar, fontes oficiais e as rotas nativas de LILACS/BVS e SciELO.

Google Programmable Search, Brave e SerpAPI dependem de credenciais.

Scopus e Web of Science não são simulados.

HTTP `401`/`403` em BVS/LILACS ou SciELO é registrado como indisponibilidade da rota automatizada; não significa “zero literatura”.

## 14. Variáveis opcionais

O runtime não carrega `.env` automaticamente. Variáveis podem ser definidas na sessão:

```bat
set NCBI_EMAIL=seu-email@exemplo.com
set NCBI_API_KEY=...
set CROSSREF_MAILTO=seu-email@exemplo.com
set OPENALEX_MAILTO=seu-email@exemplo.com
set S2_API_KEY=...
set GOOGLE_API_KEY=...
set GOOGLE_CSE_ID=...
set BRAVE_API_KEY=...
set SERPAPI_API_KEY=...
```

A ausência de `NCBI_EMAIL`/`ENTREZ_EMAIL` não impede PubMed; o cliente usa ritmo conservador.

## 15. Interrupção e retomada

PubMed mantém checkpoints. Após uma interrupção:

```bat
Iniciar-NutEV-Windows.bat
```

Não apague `project_output_reference` ou checkpoints por padrão.

Código `130` normalmente indica interrupção por `Ctrl+C`.

## 16. Deduplicação

A identidade atual segue:

```text
DOI -> PMID -> URL -> título normalizado
```

Isso não é deduplicação semântica. Versões paralelas ou registros equivalentes com identificadores diferentes podem permanecer separados.

## 17. Interpretação A/B/C

- posições 1–20: `A_TOP_REFERENCE`;
- posições 21–100: `B_STRONG_REFERENCE`;
- demais: `C_DISCOVERY`.

As faixas indicam ordem de leitura. Não indicam qualidade metodológica, certeza da evidência ou recomendação clínica.

## 18. Registro mínimo para pesquisa/auditoria

Preservar pelo menos:

```text
SHA do Git
07_logs/collect_everything/latest.json
07_logs/latin_native/latest.json
reference_ranking/latest.json
reference_ranking/AUDIT_MANIFEST.json
reference_ranking/reference_ranking.csv
reference_ranking/reference_ranking.jsonl
reference_ranking/reference_quarantine.jsonl
```

Registrar também data/hora, perfil de coleta, providers indisponíveis/falhos e qualquer intervenção manual documentada.

## 19. Execução histórica validada de 18/08/2026

A execução Windows registrada em `VALIDATED_WINDOWS_RUN_2026-08-18.md` teve 8.702 entradas e 115 grupos de taxonomia naquele estado do software.

Ela é evidência histórica de execução real, não um baseline obrigatório da `main` com os guardrails posteriores.

## 20. Mudanças metodológicas

Qualquer alteração que modifique:

- providers ou identidade dos providers;
- consultas ou limites;
- regra de identidade/deduplicação;
- rastreabilidade/quarentena;
- política de hashes;
- taxonomia ou caps;
- pesos ou tipos documentais;
- outputs ou manifesto de auditoria;
- interpretação dos scores;

deve atualizar documentação e testes e passar pelo CI antes do merge.

## 21. Referências internas

- guardrails e auditoria: `AUDITABILITY_AND_GUARDRAILS.md`;
- arquitetura e pesos: `ARCHITECTURE.md`;
- providers: `SEARCH_PROVIDERS.md`;
- limitações: `KNOWN_LIMITATIONS.md`;
- release: `RELEASE_V1_0_0.md`;
- checklist de release: `RELEASE_CHECKLIST.md`;
- DOI/Zenodo: `ZENODO_SETUP.md`.
