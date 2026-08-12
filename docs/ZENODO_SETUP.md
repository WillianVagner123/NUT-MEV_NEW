# Depositar no Zenodo e obter o DOI permanente

O Artigo 1 pode citar uma versão arquivada do **NutEV Evidence Engine**. O GitHub fornece o repositório e o histórico de desenvolvimento; o Zenodo pode preservar uma release específica e emitir um DOI persistente para o software arquivado.

A última GitHub Release publicada continua sendo **software version `0.2.0` / tag `v0.2.0`**, de **9 de agosto de 2026**. O desenvolvimento atual está em `0.3.0.dev1`; **não existe `v0.3.0` publicada**.

## 1. Estado atual

- GitHub Release `v0.2.0`: **publicada**;
- commit congelado da release `v0.2.0`: `bd4191a4dbc1a71cddf34911033078acc5165bb9`;
- nova linha de desenvolvimento: `0.3.0.dev1`;
- `nutev play`: presente na `main` como orquestrador PILOT;
- próxima release/Zenodo: **não autorizada ainda**;
- Zenodo Version DOI atual: **PENDING — nenhum DOI novo deve ser inferido**;
- Concept DOI: **PENDING — não verificado**;
- ORCID/afiliação: incluir somente se confirmados.

Não interprete `PENDING` como DOI existente. Nenhum DOI deve entrar no manuscrito, README ou arquivos de citação antes da verificação do registro real.

## 2. Fonte de metadados

O repositório mantém dois arquivos complementares:

- `.zenodo.json` — metadados usados pelo fluxo GitHub→Zenodo;
- `CITATION.cff` — metadados de citação usados pelo GitHub e ferramentas compatíveis com CFF.

Quando os dois arquivos existem, o fluxo de arquivamento GitHub→Zenodo usa `.zenodo.json` como fonte de metadados. Por isso, a preparação da próxima release deve validar `.zenodo.json` como fonte efetiva do depósito **e** manter `CITATION.cff` semanticamente sincronizado para citação/uso no GitHub.

Nunca atualize somente um deles e assuma que o outro será automaticamente reconciliado.

## 3. Gate obrigatório antes da próxima release

A futura release candidata deve satisfazer [`RELEASE_PLAN_v0.3.0.md`](RELEASE_PLAN_v0.3.0.md), incluindo:

- validação real do `nutev play`;
- CI/release checks no SHA candidato;
- resolução da proveniência/licença em #1014;
- higiene de código/compatibilidade em #1015 ou limitação explicitamente documentada;
- reconciliação da versão/tag/CHANGELOG/README/`CITATION.cff`/`.zenodo.json` no mesmo SHA;
- verificação de que o artefato de release não contém PDFs protegidos, dados privados ou credenciais.

A conclusão dos gates científicos do Artigo 1 e a publicação do software são conceitos distintos. Se GF-02/PRESS/GF-10 ainda estiverem abertos, uma release de software só pode ser publicada se isso estiver descrito corretamente; ela não pode ser apresentada como a execução formal concluída do Artigo 1.

## 4. Habilitar/verificar a integração Zenodo↔GitHub

Na conta Zenodo apropriada:

1. abra a integração com GitHub;
2. sincronize/localize `WillianVagner123/NutEV-Evidence-Engine`;
3. habilite o repositório para arquivamento de releases;
4. confirme o estado da release histórica `v0.2.0` sem mover/recriar a tag;
5. antes da futura release, confira que a integração continua habilitada.

O processamento de uma release futura só deve ser disparado depois do GO no SHA candidato.

## 5. Publicar uma futura release

Depois do GO:

```text
candidate SHA aprovado
        ↓
criar tag nova e imutável
        ↓
criar GitHub Release dessa tag
        ↓
aguardar processamento pelo Zenodo
        ↓
abrir o registro real
        ↓
verificar arquivos + metadados + DOI
```

Não mova uma tag já publicada e não reutilize `v0.2.0`.

Se a próxima identidade aprovada for `0.3.0`, somente então crie `v0.3.0`. O nome `v0.3.0` não deve existir antecipadamente apenas porque existe `0.3.0.dev1` na árvore de desenvolvimento.

## 6. Metadados humanos e licença

Não invente ORCID, afiliação, funding, autoria adicional, DOI de artigo ou ponto de derivação upstream. Inclua cada campo somente quando confirmado.

A proveniência histórica Local Deep Research/LearningCircuit e o MIT precisam ser resolvidos conforme [`PROVENANCE_AND_LICENSE.md`](PROVENANCE_AND_LICENSE.md) e #1014. Não remova silenciosamente o aviso upstream de material herdado/substancialmente derivado; ao mesmo tempo, não atribua toda a implementação NutEV atual à LearningCircuit.

A licença declarada no Zenodo deve refletir a decisão real da release e os arquivos de licença da árvore candidata.

## 7. Auditoria do registro Zenodo real

| Campo | GitHub / arquivos | Zenodo | Status |
|---|---|---|---|
| título | NutEV Evidence Engine | | |
| versão | versão/tag candidata aprovada | | |
| Git tag | tag nova aprovada | | |
| release date | data real da GitHub Release | | |
| criadores | conforme `.zenodo.json` validado | | |
| ORCID | somente se confirmado | | |
| afiliação | somente se confirmada | | |
| licença | conforme decisão de release | | |
| descrição | conforme `.zenodo.json` | | |
| keywords | conforme metadados candidatos | | |
| related identifiers | somente relações verificadas | | |
| Version DOI | PENDING até observar registro | | |
| Concept DOI | PENDING até observar registro | | |

Não encerre a auditoria enquanto houver divergência material entre o objeto GitHub congelado e o registro Zenodo.

## 8. Depois de verificar o DOI

Somente depois de observar o registro público real, em commits **posteriores** à release arquivada, atualize conforme apropriado:

1. `CITATION.cff` — DOI real, quando o arquivo deve apontar ao registro publicado;
2. `README.md` — badge/identificador real;
3. `docs/CODE_AVAILABILITY.md` — Version DOI real;
4. release record — record ID, Version DOI e Concept DOI quando aplicável;
5. manuscrito — declaração de disponibilidade e referência do software.

Esses commits pós-release **não alteram nem movem** a tag arquivada.

## 9. Relação com a auditoria científica

A publicação do software e a prontidão da execução definitiva do Artigo 1 são gates diferentes.

O caminho científico atual permanece:

```text
GF-02 PILOT
→ GF-03 PRESS
→ GF-06 filtros/data
→ GF-07 triagem humana
→ GF-10 FREEZE
→ busca formal
→ corpus mestre
→ triagem
→ full text
→ extração/codebook
```

`nutev play` automatiza o que for computacionalmente autorizado pelo estado científico; ele não substitui esses gates.

## Checklist da próxima publicação

- [x] `nutev play` implementado e incorporado à `main`
- [ ] PLAY local `--metadata-only` validado em projeto científico real
- [ ] PLAY completo/bounded validado com full text/OCR
- [ ] #1014 licença/proveniência resolvida
- [ ] #1015 compatibility/code hygiene resolvido ou explicitamente aceito
- [ ] versão final escolhida
- [ ] `.zenodo.json` atualizado e validado no SHA candidato
- [ ] `CITATION.cff` sincronizado
- [ ] CHANGELOG/README/release notes reconciliados
- [ ] CI completo verde no SHA candidato
- [ ] tag nova criada
- [ ] GitHub Release criada
- [ ] Zenodo processou a release
- [ ] registro público conferido
- [ ] Version DOI registrado
- [ ] Concept DOI registrado quando aplicável

Até esses itens serem verificados, o próximo DOI permanece **PENDING**.
