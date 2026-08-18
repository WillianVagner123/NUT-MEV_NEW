# Checklist de release

Use este checklist no **SHA exato** candidato à release. Não valide uma versão usando checks executados em outro commit.

## 1. Identidade

- [ ] `src/nutev/__version__.py` contém a versão pretendida.
- [ ] `pyproject.toml` continua apontando a versão para esse arquivo.
- [ ] `README.md` descreve o escopo real da versão.
- [ ] `CITATION.cff` usa título, versão, data e criador corretos.
- [ ] `.zenodo.json` usa título, versão e criador corretos.
- [ ] `CHANGELOG.md` contém a nova versão.
- [ ] release notes foram preparadas.
- [ ] nenhum DOI novo foi inventado antecipadamente.

## 2. Produto

- [ ] fluxo suportado continua documentado corretamente;
- [ ] providers implementados correspondem à documentação;
- [ ] Scopus/Web of Science não são simulados;
- [ ] falhas/indisponibilidades permanecem explícitas;
- [ ] provider identity é preservada;
- [ ] queries e limites configurados estão revisados;
- [ ] regra de identidade/deduplicação está documentada;
- [ ] scoring e tiers estão documentados em `docs/ARCHITECTURE.md`;
- [ ] limitações relevantes estão em `docs/KNOWN_LIMITATIONS.md`;
- [ ] outputs continuam dentro do contrato público esperado.

## 3. Testes e qualidade

- [ ] testes Python 3.12 passam;
- [ ] testes Python 3.13 passam;
- [ ] Windows smoke passa;
- [ ] `python -m compileall -q src tools nutev_tests` passa;
- [ ] Ruff blocking checks passam;
- [ ] typecheck passa;
- [ ] regressões de provider/ranking/output foram adicionadas quando necessárias.

## 4. Segurança e dependências

- [ ] secret/security scan passa;
- [ ] dependency review passa;
- [ ] CodeQL passa;
- [ ] não há secrets, dados privados ou conteúdo protegido indevido no diff;
- [ ] `.env.example` contém somente placeholders/documentação.

## 5. Distribuição

- [ ] `python -m build` produz wheel e sdist;
- [ ] `twine check` passa;
- [ ] instalação limpa do wheel passa;
- [ ] `pip check` passa;
- [ ] `nutev --version` retorna a versão pretendida;
- [ ] artefatos não incluem outputs locais indevidos.

## 6. GitHub

- [ ] PR de release está mergeado sem ignorar checks necessários;
- [ ] SHA final de `main` foi registrado;
- [ ] tag nova aponta exatamente para esse SHA;
- [ ] tag antiga não foi movida;
- [ ] GitHub Release usa a mesma versão/tag/título;
- [ ] release notes correspondem ao código publicado.

## 7. Zenodo

- [ ] integração GitHub/Zenodo está pronta;
- [ ] release foi ingerida pelo Zenodo;
- [ ] título/criador/licença/versão foram conferidos no registro;
- [ ] arquivos arquivados correspondem ao snapshot da tag;
- [ ] DOI version-specific foi efetivamente emitido;
- [ ] somente depois da emissão real o DOI foi adicionado à metadata corrente;
- [ ] patch de DOI não move a tag publicada.

## 8. Pós-release

- [ ] comparar tag com o SHA registrado e confirmar identidade;
- [ ] verificar URL da GitHub Release;
- [ ] verificar DOI/record URL;
- [ ] atualizar README/CITATION/docs sem reescrever o snapshot publicado;
- [ ] registrar limitações ou bugs descobertos em execução real como mudanças pós-release, não como se estivessem presentes na tag original.

## Referência v1.0.0

A release `v1.0.0` foi publicada em 18/08/2026 no commit:

```text
5728d79b05e618897f01ba93886a17584c9f215f
```

Zenodo record:

```text
21998607
```

DOI:

```text
10.5281/zenodo.21998607
```
