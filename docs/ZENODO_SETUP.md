# Depositar no Zenodo e obter o DOI permanente

O Artigo 1 pode citar uma versão arquivada do **NutEV Evidence Engine**. O GitHub fornece o repositório e o histórico de desenvolvimento; o Zenodo pode preservar uma release específica e emitir um DOI persistente para o software arquivado.

> A release citável reconciliada **já foi publicada no GitHub** como **software version `0.2.0` / Git tag `v0.2.0`**, em **9 de agosto de 2026**. O projeto continua descrito como **alpha** em termos de maturidade científica. As tags históricas `v0.1.0`–`v0.1.8` e a tag publicada `v0.2.0` são imutáveis e não devem ser sobrescritas ou movidas.

## 1. Estado atual

- GitHub Release `v0.2.0`: **publicada**;
- commit congelado da release: `bd4191a4dbc1a71cddf34911033078acc5165bb9`;
- Zenodo Version DOI: **PENDING — não verificado publicamente**;
- Concept DOI: **PENDING — não verificado publicamente**;
- ORCID/afiliação: incluir somente se confirmados.

Não interprete `PENDING` como DOI existente. Nenhum DOI deve entrar no manuscrito, README ou arquivos de citação antes da verificação do registro real.

## 2. Fonte de metadados

O repositório mantém dois arquivos complementares:

- `.zenodo.json` — metadados do depósito GitHub→Zenodo;
- `CITATION.cff` — metadados de citação para GitHub e ferramentas compatíveis com CFF.

Eles devem representar o mesmo objeto científico e permanecer sincronizados em título, versão, criadores e licença.

## 3. Habilitar/verificar a integração Zenodo↔GitHub

1. entre no Zenodo usando a conta apropriada;
2. abra a integração com GitHub;
3. localize `WillianVagner123/NutEV-Evidence-Engine`;
4. confirme que o repositório está habilitado para arquivamento de releases;
5. confirme se a release `v0.2.0` foi ingerida;
6. abra o registro real e confira versão, tag, criadores, licença e arquivos.

Se o repositório não estava habilitado quando `v0.2.0` foi publicada, siga o procedimento atual suportado pelo Zenodo sem mover/recriar a tag. Preserve a identidade do software publicado.

## 4. Metadados humanos

Não invente ORCID, afiliação, funding, autoria adicional, DOI de artigo ou ponto de derivação upstream. Inclua cada campo somente quando confirmado. A ausência de um campo opcional é preferível a um valor inventado.

## 5. Auditoria do registro Zenodo real

| Campo | GitHub / arquivos | Zenodo | Status |
|---|---|---|---|
| título | NutEV Evidence Engine | | |
| versão | `0.2.0` | | |
| Git tag | `v0.2.0` | | |
| release date | `2026-08-09` | | |
| criadores | conforme `.zenodo.json` | | |
| ORCID | somente se confirmado | | |
| afiliação | somente se confirmada | | |
| licença | MIT | | |
| descrição | conforme metadados publicados | | |
| keywords | conforme metadados publicados | | |
| related identifiers | somente relações verificadas | | |
| Version DOI | PENDING | | |
| Concept DOI | PENDING | | |

Não encerre a auditoria enquanto houver divergência material entre o objeto GitHub congelado e o registro Zenodo.

## 6. Depois de verificar o DOI

Somente depois de observar o registro público real, em commits **posteriores** à release arquivada, atualize conforme apropriado:

1. `CITATION.cff` — DOI real;
2. `README.md` — badge/identificador real;
3. `docs/CODE_AVAILABILITY.md` — Version DOI real;
4. `docs/RELEASE_RECORD_v0.2.0.md` — record ID, Version DOI e Concept DOI quando aplicável;
5. manuscrito — declaração de disponibilidade e referência do software.

Esses commits pós-release **não alteram nem movem** `v0.2.0`.

## 7. Relação com a auditoria científica pós-release

A publicação do software `v0.2.0` e a prontidão da execução definitiva do Artigo 1 são gates diferentes. A auditoria de 2026-08-09 identificou remediações de proveniência de busca e `scientific_readiness` que pertencem a commits/releases posteriores.

Assim:

- `v0.2.0` continua sendo o objeto de software publicado;
- não reescrever a tag para incorporar correções posteriores;
- a execução definitiva do Artigo 1 deve usar um commit/release que satisfaça `docs/ARTICLE1_SEARCH_EXECUTION_CONTRACT.md` e os gates P0 revalidados.

## 8. Releases futuras

Cada release futura recebe nova versão/tag, novo GO/NO-GO e, se arquivada, novo Version DOI. Nunca mova silenciosamente uma tag já publicada.

Use `docs/RELEASE_CHECKLIST.md` como template reutilizável para a próxima release.

## Checklist atual do Zenodo

- [x] identidade GitHub publicada: `0.2.0` / `v0.2.0`
- [x] data da GitHub Release: `2026-08-09`
- [x] tag histórica preservada/imutável
- [x] maturidade alpha documentada separadamente
- [ ] Zenodo conectado/habilitado para o repositório — verificar na conta
- [ ] registro `v0.2.0` observado publicamente
- [ ] metadados do registro conferidos
- [ ] Version DOI registrado
- [ ] Concept DOI registrado quando aplicável
- [ ] DOI real inserido posteriormente em citação, README, release record e manuscrito

Até esses itens serem verificados, o DOI permanece **PENDING**.