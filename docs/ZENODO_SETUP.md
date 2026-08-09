# Depositar no Zenodo e obter o DOI permanente

O Artigo 1 pode citar uma versão arquivada do **NutEV Evidence Engine**. O GitHub fornece o repositório e o histórico de desenvolvimento; o Zenodo preserva uma *release* específica e emite um DOI persistente para o software arquivado.

> A release citável reconciliada é **software version `0.2.0` / Git tag `v0.2.0`**. O projeto continua descrito como **alpha** em termos de maturidade científica. As tags históricas `v0.1.0`–`v0.1.8` já existem e serão preservadas; nenhuma delas será sobrescrita ou movida.

## 1. Fonte de metadados

O repositório mantém dois arquivos complementares:

- `.zenodo.json` — metadados do depósito GitHub→Zenodo;
- `CITATION.cff` — metadados de citação para GitHub e ferramentas compatíveis com CFF.

Eles devem representar o mesmo objeto científico e permanecer sincronizados em título, versão, criadores e licença.

## 2. Conectar o Zenodo ao GitHub

1. entre no Zenodo usando a conta apropriada;
2. habilite a integração com GitHub;
3. localize `WillianVagner123/NutEV-Evidence-Engine`;
4. habilite o repositório para arquivamento de releases.

Confirme o fluxo na documentação oficial atual do Zenodo antes do depósito definitivo. Se desejar testar o processo, use o ambiente de sandbox do Zenodo.

## 3. Metadados humanos

Não invente ORCID, afiliação, funding, autoria adicional, DOI de artigo ou ponto de derivação upstream. Inclua cada campo somente quando confirmado. A ausência de um campo opcional é preferível a um valor inventado.

## 4. Executar o GO / NO-GO

Antes de criar a tag, complete `docs/RELEASE_CHECKLIST.md` para o commit candidato final. A release somente pode ser publicada após aprovação de versionamento/tag, testes, build, demo zero-key, segurança/privacidade, copyright/proveniência, documentação, metadados e coerência software ↔ Artigo 1.

Registrar o SHA exato do commit aprovado.

## 5. Criar a tag e a GitHub Release

A tag planejada é **`v0.2.0`** e deve ser criada apenas se ainda não existir e apontar exatamente para o SHA que passou pelo release gate.

Release title:

**NutEV Evidence Engine v0.2.0**

As release notes devem declarar explicitamente **alpha research-software maturity**, escopo científico, revisão humana obrigatória, controles de reprodutibilidade e limitações conhecidas.

Nunca sobrescreva ou mova uma tag histórica.

## 6. Arquivamento no Zenodo

Com a integração GitHub→Zenodo habilitada, a publicação da GitHub Release deve iniciar o arquivamento.

Depois do processamento:

1. confirme que o registro corresponde a `v0.2.0`;
2. confira os metadados efetivamente publicados;
3. registre o DOI da versão específica;
4. registre o Concept DOI quando aplicável.

Para reprodutibilidade do manuscrito, cite o **Version DOI da versão exata usada no estudo**.

## 7. Auditoria do registro Zenodo real

| Campo | GitHub / arquivos | Zenodo | Status |
|---|---|---|---|
| título | NutEV Evidence Engine | | |
| versão | `0.2.0` | | |
| criadores | | | |
| ORCID | se confirmado | | |
| afiliação | se confirmada | | |
| licença | MIT | | |
| descrição | | | |
| keywords | | | |
| related identifiers | | | |
| release/tag | `v0.2.0` | | |

Não encerre o processo enquanto houver divergência material.

## 8. Depois de obter o DOI

O DOI só deve ser escrito como real depois do depósito. Em commits posteriores à release arquivada, atualize conforme apropriado:

1. `CITATION.cff` — DOI real e data real da release;
2. `README.md` — badge/identificador real;
3. `docs/CODE_AVAILABILITY.md` — versão e DOI reais;
4. manuscrito — declaração de disponibilidade e referência do software.

Esses commits pós-release **não alteram o objeto já congelado** no Zenodo.

## 9. Releases futuras

Cada release recebe nova versão/tag, novo GO/NO-GO e novo Version DOI. Nunca mova silenciosamente uma tag já publicada.

## Checklist rápido

- [ ] identidade única: `0.2.0` / `v0.2.0`
- [ ] `v0.2.0` confirmado como tag ainda não utilizada
- [ ] maturidade alpha documentada separadamente
- [ ] metadados humanos incluídos somente quando confirmados
- [ ] provenance revisada
- [ ] release-validation verde no SHA final
- [ ] Zenodo conectado ao repositório
- [ ] GitHub Release `v0.2.0` publicada somente após GO
- [ ] registro Zenodo conferido
- [ ] Version DOI registrado
- [ ] DOI real inserido posteriormente em citação, README e manuscrito
