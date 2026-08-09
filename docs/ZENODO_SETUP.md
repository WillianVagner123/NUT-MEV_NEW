# Depositar no Zenodo e obter o DOI permanente

O artigo (Artigo 1) pode citar uma versão arquivada do **NutEV Evidence Engine**. O GitHub fornece o repositório e o histórico de desenvolvimento; o Zenodo preserva uma *release* específica e emite um DOI persistente para o software arquivado.

> Para esta primeira release citável, a identidade foi padronizada como **software version `0.1.0` / Git tag `v0.1.0`**. O projeto continua descrito como **alpha** em termos de maturidade científica. Não use `0.1.0-alpha` ou `v1.0-artigo1` como identidades alternativas da mesma release.

## 1. Fonte de metadados

O repositório mantém dois arquivos complementares:

- `.zenodo.json` — metadados do depósito GitHub→Zenodo;
- `CITATION.cff` — metadados de citação para GitHub e ferramentas compatíveis com CFF.

Eles devem representar o mesmo objeto científico e permanecer sincronizados em título, versão, criadores e licença.

## 2. Conectar o Zenodo ao GitHub

Na interface atual do Zenodo/GitHub:

1. entre no Zenodo usando a conta apropriada;
2. habilite a integração com GitHub;
3. localize `WillianVagner123/NutEV-Evidence-Engine`;
4. habilite o repositório para arquivamento de releases.

Antes do primeiro depósito definitivo, confirme o fluxo na documentação oficial atual do Zenodo. Se desejar testar o processo, use o ambiente de sandbox do Zenodo antes de publicar a release citable definitiva.

## 3. Antes da release — HUMAN INPUT REQUIRED

Não publique enquanto estes campos não estiverem confirmados:

- **ORCID** do(s) creator(s);
- **afiliação institucional** na redação exata;
- autores/contributors adicionais e ordem, se aplicável;
- DOI do Artigo 1, se já existir e for apropriado registrá-lo como identificador relacionado;
- ponto exato de derivação do projeto upstream, caso seja declarado publicamente.

Não invente nenhum desses valores.

## 4. Executar o GO / NO-GO

Antes de criar a tag, complete `docs/RELEASE_CHECKLIST.md` para o commit candidato final.

A release somente pode ser publicada quando estiverem aprovados:

- versionamento;
- testes;
- build;
- reprodução zero-key;
- segurança e privacidade;
- copyright/proveniência;
- documentação;
- `.zenodo.json`;
- `CITATION.cff`;
- coerência software ↔ Artigo 1.

Registrar o SHA exato do commit aprovado.

## 5. Criar a tag e a GitHub Release

Após o GO final:

```bash
git tag -a v0.1.0 -m "NutEV Evidence Engine v0.1.0"
git push origin v0.1.0
```

Na GitHub Release:

- **Tag:** `v0.1.0`
- **Title:** `NutEV Evidence Engine v0.1.0`
- **Maturity:** deixar explícito nas notas que o software permanece em estágio **alpha**;
- **Description:** resumir o escopo científico, capacidades metodológicas, revisão humana obrigatória, reprodutibilidade e limitações conhecidas.

A tag deve apontar exatamente para o SHA que passou pelo GO / NO-GO.

## 6. Arquivamento no Zenodo

Com a integração habilitada, a publicação da GitHub Release deve iniciar o arquivamento no Zenodo.

Depois do processamento:

1. abra o registro Zenodo criado;
2. confirme que ele corresponde à release `v0.1.0`;
3. verifique os metadados efetivamente publicados;
4. registre o DOI da versão específica;
5. registre o DOI do conceito/software geral quando apresentado pelo Zenodo.

Para o manuscrito que precisa reproduzir a análise, cite preferencialmente o **DOI correspondente à versão exata do software usada no estudo**.

## 7. Auditoria do registro Zenodo real

Compare o depósito com o GitHub:

| Campo | GitHub / arquivos | Zenodo | Status |
|---|---|---|---|
| título | | | |
| versão | `0.1.0` | | |
| criadores | | | |
| ORCID | | | |
| afiliação | | | |
| licença | MIT | | |
| descrição | | | |
| keywords | | | |
| related identifiers | | | |
| release/tag | `v0.1.0` | | |

Não encerre o processo enquanto houver divergência material.

## 8. Depois de obter o DOI

O DOI só existe depois do depósito. Portanto, não coloque placeholders como se fossem identificadores reais.

Em commits posteriores à release arquivada, atualize conforme apropriado:

1. `CITATION.cff` — adicionar o DOI real e a data real da release;
2. `README.md` — substituir o badge de DOI pendente pelo badge/identificador real;
3. `docs/CODE_AVAILABILITY.md` — inserir versão e DOI reais;
4. manuscrito — inserir a declaração de disponibilidade de código e a referência do software.

Esses commits pós-release pertencem ao desenvolvimento posterior e **não alteram os arquivos já congelados no registro Zenodo da versão `v0.1.0`**.

## 9. Releases futuras

Cada nova release deve:

- receber novo número de versão e nova tag;
- passar pelo mesmo GO / NO-GO;
- gerar um novo registro de versão no Zenodo;
- manter versões antigas imutáveis e citáveis.

Nunca mova silenciosamente uma tag já publicada para outro commit.

---

## Checklist rápido

- [ ] identidade única: `0.1.0` / `v0.1.0`
- [ ] maturidade `alpha` documentada separadamente da versão
- [ ] ORCID confirmado
- [ ] afiliação confirmada
- [ ] autoria/contributors confirmados
- [ ] provenance revisada
- [ ] `docs/RELEASE_CHECKLIST.md` com todos os gates PASS
- [ ] Zenodo conectado ao repositório
- [ ] GitHub Release `v0.1.0` publicada somente após GO
- [ ] registro Zenodo conferido
- [ ] Version DOI registrado
- [ ] DOI inserido posteriormente em citação, README e manuscrito
