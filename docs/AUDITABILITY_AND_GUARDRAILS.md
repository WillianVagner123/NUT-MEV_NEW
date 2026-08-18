# Auditabilidade e guardrails do NutEV Reference Engine

Data da política: 2026-08-18  
Versão da política: `2026-08-18.2`

## Objetivo

O NutEV Reference Engine deve ser capaz de responder, para cada execução:

1. de onde cada registro veio;
2. qual arquivo de coleta o continha;
3. se esse arquivo ainda corresponde ao hash registrado no manifesto;
4. por que o registro recebeu determinado score;
5. quais registros foram rejeitados pelo guardrail;
6. quais arquivos finais foram produzidos e qual é o SHA-256 de cada um.

O engine não usa um modelo generativo para criar referências. Metadados ausentes não são completados por inferência. Provider indisponível não é substituído por conteúdo inventado de outra fonte.

## Princípios fail-closed

### 1. Integridade de entrada

O ranker só aceita um master declarado em `latest.json` quando:

- `master_records_path` existe;
- `master_records_sha256` está presente;
- o SHA-256 real do arquivo é idêntico ao declarado.

Se o arquivo foi alterado, corrompido ou substituído depois da coleta, o ranking é interrompido com erro de guardrail. O sistema não tenta "consertar" silenciosamente o conteúdo.

### 2. Rastreabilidade por registro

Cada registro recebe uma classificação determinística:

- `A_IDENTIFIER`: possui DOI, PMID ou PMCID com formato sintaticamente plausível;
- `B_TRACEABLE_URL`: não possui identificador válido, mas possui URL HTTP/HTTPS rastreável;
- `Q_INCOMPLETE_ORIGIN`: falta provider ou título;
- `Q_INVALID_IDENTIFIER`: apresenta identificador, mas nenhum identificador tem formato válido e não existe URL HTTP/HTTPS rastreável;
- `Q_UNTRACEABLE`: não possui identificador válido nem URL HTTP/HTTPS rastreável.

O gate reconhece DOI mesmo quando fornecido no formato de URL `https://doi.org/...`; PMID precisa ser numérico; PMCID precisa seguir o padrão `PMC` + dígitos. O engine não corrige um identificador malformado por adivinhação.

Por padrão, classes `Q_*` não entram no ranking. Elas são gravadas em:

```text
project_output_reference/reference_ranking/reference_quarantine.jsonl
```

Nenhum identificador, URL, autor, ano ou abstract é criado para retirar um registro da quarentena.

### 3. Hash de origem do registro

Cada item elegível recebe `audit_origin_sha256`, calculado sobre um payload determinístico contendo:

- provider;
- DOI;
- PMID;
- PMCID;
- URL;
- título;
- query/provider_query.

Esse hash não prova que o conteúdo científico do artigo é verdadeiro. Ele serve para detectar mudança no conjunto de metadados usados como origem do item.

### 4. Score explicável

Cada linha do ranking contém `score_breakdown` com componentes separados:

- taxonomia;
- taxonomia antes do cap;
- palavras-chave foco;
- palavras-chave foco antes do cap;
- tipo documental;
- provider;
- identificador;
- recência;
- penalidades.

O score da taxonomia e das palavras-chave foco possui teto configurado para reduzir inflação causada por grande quantidade de grupos históricos ou termos redundantes.

Tipos documentais sobrepostos não acumulam bônus. Um título como `clinical practice guideline` pode produzir vários `document_type_hits`, mas somente o sinal de maior peso é aplicado ao score (`document_type_applied`).

## Configuração versionada

Os guardrails ficam em:

```text
config/reference_mode.json
```

Configuração canônica atual:

```json
{
  "guardrails": {
    "require_traceable_origin": true,
    "fail_on_input_hash_mismatch": true,
    "taxonomy_score_cap": 60,
    "focus_score_cap": 40,
    "document_type_scoring": "highest_weight_only"
  }
}
```

Alterar essa política muda o comportamento metodológico do ranker e deve passar por revisão, testes e registro no histórico Git.

## Manifesto de auditoria

Toda execução bem-sucedida gera:

```text
project_output_reference/reference_ranking/AUDIT_MANIFEST.json
```

O manifesto registra:

- versão da política;
- política ativa;
- manifests de coleta utilizados;
- SHA-256 dos masters de entrada;
- SHA-256 de `reference_mode.json` e de todos os `keyword_taxonomy*.json`;
- contagens de entrada, rastreáveis, quarentena e únicos ranqueados;
- SHA-256 dos outputs;
- assertions de guardrail.

Os outputs auditados são:

```text
reference_ranking.jsonl
reference_ranking.csv
TOP_REFERENCIAS.md
reference_quarantine.jsonl
```

## Como auditar uma execução

1. Registre o commit do software:

```bash
git rev-parse HEAD
```

2. Preserve a pasta da execução e especialmente:

```text
07_logs/collect_everything/latest.json
07_logs/latin_native/latest.json
reference_ranking/latest.json
reference_ranking/AUDIT_MANIFEST.json
```

3. Confirme que `AUDIT_MANIFEST.json` tem `status: PASS`.

4. Recalcule os SHA-256 dos arquivos de entrada e saída e compare com o manifesto.

5. Para uma referência específica, use:

- `audit_traceability`;
- `audit_reasons`;
- `audit_origin_sha256`;
- `audit_source_run_id`;
- `audit_source_master_sha256`;
- `reference_provider`;
- DOI/PMID/PMCID/URL.

6. Para entender o ranking, examine `score_breakdown`, `matched_terms`, `taxonomy_groups`, `focus_keyword_hits` e `document_type_applied`.

## O que o guardrail não prova

Auditabilidade de software não equivale a validação científica do documento.

O guardrail não prova:

- que um DOI sintaticamente válido realmente foi registrado pela agência DOI;
- que um PMID/PMCID sintaticamente válido resolve para o documento esperado;
- que o estudo é metodologicamente bom;
- que o abstract está correto;
- que o provider não contém erro bibliográfico;
- que a conclusão científica é verdadeira;
- que o item deve ser incluído em revisão sistemática;
- que existe recomendação clínica.

A validação sintática reduz a aceitação de lixo/corrupção, mas não substitui resolução do identificador no provider nem leitura crítica.

## Regra para futuras funções com IA generativa

Se uma função futura usar LLM para resumo, síntese ou extração, ela não deve ser considerada parte confiável do Reference Engine até implementar, no mínimo:

- citação obrigatória do registro-fonte em cada afirmação;
- distinção explícita entre texto extraído e inferência;
- bloqueio de saída quando a fonte necessária não estiver disponível;
- trilha de prompt/modelo/versão/configuração;
- teste de regressão para referências inexistentes;
- revisão humana para qualquer uso científico ou clínico.

Até que esses requisitos existam, o produto canônico permanece um mecanismo determinístico de descoberta, rastreabilidade e priorização de referências.
