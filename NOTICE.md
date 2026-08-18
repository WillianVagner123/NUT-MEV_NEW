# NOTICE

Este repositório contém o **NutEV Reference Engine** (`nutev-nutmev`) e preserva informações de licença/proveniência de um projeto open source anterior.

## Projeto upstream

- Projeto: Local Deep Research (LDR)
- Organização upstream: LearningCircuit
- Copyright upstream preservado: Copyright (c) 2025 LearningCircuit
- Licença upstream: MIT License
- Repositório upstream: `https://github.com/LearningCircuit/local-deep-research`
- Commit exato de derivação: não estabelecido de forma independente neste repositório; não deve ser inventado.

O runtime original de LDR não está presente na árvore operacional atual. Material histórico permanece no histórico Git, enquanto a atribuição MIT upstream continua preservada.

## Produto atual

O produto suportado é o NutEV Reference Engine:

```text
SEARCH -> NORMALIZE -> DEDUPLICATE -> RANK -> EXPORT
```

Componentes principais:

- `src/nutev/search/` — conectores e helpers de busca;
- `tools/` — coleta e ranking;
- `config/` — queries, limites, ranking e taxonomia;
- `nutev_tests/` — testes atuais;
- `docs/` — documentação operacional, técnica, release e proveniência;
- `Iniciar-NutEV-Windows.bat`, `RODAR_TUDO.cmd` e `run_everything_now.cmd` — caminho operacional no Windows.

A árvore atual de `src/nutev/` não depende do runtime removido `src/local_deep_research/`.

## Criador e release atual

A metadata da release `v1.0.0` identifica **Willian Vagner Dorneles Schneider** como criador do NutEV Reference Engine.

ORCID e afiliação institucional não são afirmados sem confirmação independente.

Release publicada:

- versão: `1.0.0`;
- tag: `v1.0.0`;
- release commit: `5728d79b05e618897f01ba93886a17584c9f215f`;
- Zenodo record: `21998607`;
- DOI: `10.5281/zenodo.21998607`.

O DOI foi adicionado à documentação/citação corrente somente depois da criação real do registro Zenodo. A tag publicada permaneceu imutável.

## Dependências e serviços externos

Dependências Python são declaradas em `pyproject.toml`.

Cada provider, serviço externo e dependência mantém seus próprios termos, licenças e políticas de uso. O fato de o engine preservar uma URL externa não transfere ao repositório direitos sobre o conteúdo remoto.

## Fronteira de distribuição

Não devem ser incluídos no repositório público sem direito apropriado:

- textos completos protegidos;
- dados privados de pesquisa;
- dados pessoais/participantes;
- credenciais;
- outputs locais não destinados à distribuição.

## Futuras releases

Antes de uma nova release citable:

1. preservar a atribuição MIT upstream;
2. sincronizar versão/título/criador em `CITATION.cff`, `.zenodo.json`, README e release notes;
3. validar o SHA exato com CI/security/build;
4. confirmar ausência de segredos e conteúdo não redistribuível;
5. criar uma nova tag sem mover tags antigas;
6. verificar a ingestão do arquivo no Zenodo;
7. registrar somente o DOI realmente emitido para aquela versão.

Este NOTICE registra proveniência e fronteiras de atribuição; ele não afirma que todo o código atual tenha sido escrito pelo upstream nem que o repositório não possua proveniência upstream.
