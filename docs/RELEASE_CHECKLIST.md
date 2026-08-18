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

## 2. Produto e fronteira científica

- [ ] fluxo suportado continua documentado corretamente;
- [ ] providers implementados correspondem à documentação;
- [ ] Scopus/Web of Science não são simulados;
- [ ] falhas/indisponibilidades permanecem explícitas;
- [ ] provider identity é preservada;
- [ ] queries e limites configurados estão revisados;
- [ ] regra de identidade/deduplicação está documentada;
- [ ] scoring e tiers estão documentados em `docs/ARCHITECTURE.md`;
- [ ] limitações relevantes estão em `docs/KNOWN_LIMITATIONS.md`;
- [ ] outputs continuam dentro do contrato público esperado;
- [ ] README/POP deixam explícito que ranking não é elegibilidade, qualidade metodológica ou recomendação clínica.

## 3. Guardrails e auditabilidade

- [ ] `config/reference_mode.json` contém política de guardrails explicitamente versionada/documentada;
- [ ] masters de coleta possuem `master_records_sha256`;
- [ ] ranker falha quando o hash do master diverge do manifesto;
- [ ] registros sem origem rastreável são colocados em quarentena e não entram silenciosamente no ranking;
- [ ] nenhum teste ou código completa DOI/PMID/URL por suposição;
- [ ] cada registro ranqueado exporta campos de rastreabilidade;
- [ ] cada registro ranqueado exporta `score_breakdown`;
- [ ] caps de score e regra de tipo documental estão documentados;
- [ ] `AUDIT_MANIFEST.json` é gerado e contém hashes de inputs/configurações/outputs;
- [ ] hashes registrados no manifesto foram recalculados e conferidos em teste;
- [ ] contrato específico de guardrails no CI passa;
- [ ] qualquer função generativa futura tem contrato próprio de fonte/citação e não pode fabricar referências.

## 4. Testes e qualidade

- [ ] testes Python 3.12 passam;
- [ ] testes Python 3.13 passam;
- [ ] Windows smoke passa;
- [ ] `python -m compileall -q src tools nutev_tests` passa;
- [ ] Ruff blocking checks passam;
- [ ] typecheck passa;
- [ ] testes de hash mismatch/quarentena/score breakdown passam;
- [ ] regressões de provider/ranking/output foram adicionadas quando necessárias.

## 5. Segurança e dependências

- [ ] secret/security scan passa;
- [ ] dependency review passa;
- [ ] CodeQL passa;
- [ ] não há secrets, dados privados ou conteúdo protegido indevido no diff;
- [ ] `.env.example` contém somente placeholders/documentação;
- [ ] caminhos ou logs compartilháveis foram revisados para exposição desnecessária de dados locais.

## 6. Distribuição

- [ ] `python -m build` produz wheel e sdist;
- [ ] `twine check` passa;
- [ ] instalação limpa do wheel passa;
- [ ] `pip check` passa;
- [ ] `nutev --version` retorna a versão pretendida;
- [ ] artefatos não incluem outputs locais indevidos.

## 7. GitHub e governança

- [ ] PR de release está mergeado sem ignorar checks necessários;
- [ ] SHA final de `main` foi registrado;
- [ ] required checks/ruleset da branch foram revisados na interface do GitHub;
- [ ] tag nova aponta exatamente para esse SHA;
- [ ] tag antiga não foi movida;
- [ ] GitHub Release usa a mesma versão/tag/título;
- [ ] release notes correspondem ao código publicado;
- [ ] PRs legados incompatíveis com o produto atual foram fechados ou explicitamente classificados;
- [ ] links de issue templates apontam somente para recursos habilitados.

## 8. Zenodo

- [ ] integração GitHub/Zenodo está pronta;
- [ ] release foi ingerida pelo Zenodo;
- [ ] título/criador/licença/versão foram conferidos no registro;
- [ ] arquivos arquivados correspondem ao snapshot da tag;
- [ ] DOI version-specific foi efetivamente emitido;
- [ ] somente depois da emissão real o DOI foi adicionado à metadata corrente;
- [ ] patch de DOI não move a tag publicada.

## 9. Pós-release

- [ ] comparar tag com o SHA registrado e confirmar identidade;
- [ ] verificar URL da GitHub Release;
- [ ] verificar DOI/record URL;
- [ ] atualizar README/CITATION/docs sem reescrever o snapshot publicado;
- [ ] registrar limitações ou bugs descobertos em execução real como mudanças pós-release, não como se estivessem presentes na tag original;
- [ ] guardar um `AUDIT_MANIFEST.json` de uma execução real da versão quando aplicável.

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

A tag v1.0.0 é imutável. Guardrails pós-release em `main` não devem ser retroativamente atribuídos ao snapshot publicado.
