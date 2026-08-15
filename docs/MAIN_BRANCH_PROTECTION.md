# Proteção canônica da `main`

A configuração versionada está em `.github/rulesets/main.json` e é aplicada pelo script PowerShell `scripts/configure_main_ruleset.ps1`.

## Aplicar ou atualizar

No Windows, dentro do clone autenticado com `gh auth login`:

```powershell
.\scripts\configure_main_ruleset.ps1
```

O script é idempotente: cria o ruleset `Protect main` quando ausente e atualiza o mesmo ruleset quando ele já existe.

## Verificar sem alterar

```powershell
.\scripts\configure_main_ruleset.ps1 -VerifyOnly
```

Para validar somente o arquivo local, sem chamar GitHub:

```powershell
.\scripts\configure_main_ruleset.ps1 -ValidateOnly
```

## Contrato aplicado

O ruleset:

- atinge apenas `refs/heads/main`;
- bloqueia deleção e non-fast-forward/force-push;
- exige pull request antes de atualizar `main`;
- exige resolução das conversas de review;
- não exige um segundo aprovador humano, adequado ao repositório pessoal atual;
- exige que a branch do PR esteja atualizada com a base;
- exige os checks canônicos atuais de Python 3.12/3.13, Windows, lint, typecheck, CodeQL, dependency review, secret/file scan e validação do artefato de release.

A lista de checks é deliberadamente explícita. Se nomes de jobs forem alterados, `.github/rulesets/main.json` e `nutev_tests/test_main_ruleset_config.py` devem ser atualizados no mesmo PR.

## Segurança metodológica

Proteção de branch é governança de software. Ela não fecha nem implica qualquer gate científico do Artigo 1, PRESS, FREEZE, decisão R1/R2, elegibilidade PRISMA ou autorização metodológica.
