# Proveniência e fronteira de licença

## Origem

O NutEV Reference Engine evoluiu a partir de um repositório que incorporava código do projeto open source **Local Deep Research**, mantido pela LearningCircuit e distribuído sob licença MIT.

A árvore operacional atual não contém o runtime histórico de Local Deep Research. O histórico permanece disponível no Git e a atribuição upstream é preservada em `LICENSE` e `NOTICE.md`.

O repositório não afirma um commit exato de derivação porque esse ponto não foi estabelecido independentemente.

## Árvore atual

O produto suportado hoje está restrito ao Reference Engine:

- `src/nutev/search/` — providers e helpers de busca;
- `tools/` — coleta e ranking;
- `config/` — queries, limites, ranking e taxonomia;
- `nutev_tests/` — testes atuais;
- `docs/` — documentação do produto, operação, release e proveniência;
- launchers Windows — caminho operacional suportado.

A árvore atual de `src/nutev/` não depende de `src/local_deep_research/`.

## Fronteira de autoria

Não afirmar:

- que todo o código atual foi escrito pela LearningCircuit;
- que o repositório atual não possui nenhuma proveniência upstream;
- um commit de derivação não verificado;
- ORCID ou afiliação não confirmados.

A metadata da release v1.0.0 identifica Willian Vagner Dorneles Schneider como criador do NutEV Reference Engine publicado.

## Licença

A licença do repositório é MIT, conforme `LICENSE`.

Dependências e serviços externos mantêm seus próprios termos/licenças. URLs retornadas por providers são metadados e não transferem direitos de redistribuição do conteúdo remoto.

## Release publicada

- versão: `1.0.0`;
- tag: `v1.0.0`;
- release commit: `5728d79b05e618897f01ba93886a17584c9f215f`;
- Zenodo record: `21998607`;
- DOI: `10.5281/zenodo.21998607`.

O DOI foi registrado somente depois da criação real do arquivo Zenodo e não alterou a tag já publicada.

## Gate para futuras releases

Antes de uma nova release pública:

1. preservar licença e atribuição upstream;
2. sincronizar identidade da versão em `CITATION.cff`, `.zenodo.json`, README, changelog e release notes;
3. validar o SHA candidato em CI/security/build;
4. verificar ausência de segredos, dados privados e texto completo não redistribuível;
5. criar uma nova tag imutável;
6. publicar a GitHub Release correspondente;
7. verificar o registro Zenodo;
8. registrar somente o DOI realmente emitido para a nova versão.

Não reutilizar `10.5281/zenodo.21998607` como DOI version-specific de uma versão futura.
