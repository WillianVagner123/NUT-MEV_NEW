# Security Policy — NutEV Reference Engine

## Escopo

Esta política cobre o repositório público `WillianVagner123/NutEV-Evidence-Engine` e o produto atualmente suportado, NutEV Reference Engine.

## Segredos e credenciais

Nunca versione:

- API keys;
- tokens;
- cookies/sessões;
- chaves privadas;
- credenciais de bancos/serviços;
- arquivos `.env` reais;
- URLs assinadas de acesso temporário.

`.env.example` contém somente nomes de variáveis e exemplos vazios.

O runtime atual **não carrega `.env` automaticamente**. Variáveis opcionais devem ser fornecidas pelo ambiente do processo/shell.

## Dados e outputs

A árvore gerada padrão é:

```text
project_output_reference/
```

Ela não deve ser versionada por padrão.

Antes de compartilhar logs ou outputs, revisar a presença de:

- dados pessoais;
- credenciais;
- URLs temporárias/assinadas;
- cookies/headers;
- caminhos locais que revelem informação desnecessária da estação de trabalho;
- textos completos protegidos por copyright.

## Conteúdo científico e copyright

O Reference Engine trabalha principalmente com metadados, identificadores e URLs de providers externos.

Não adicionar ao repositório textos completos protegidos sem direito explícito de redistribuição.

Quando uma fonte externa disponibiliza um link para PDF, o link pode ser preservado como metadado; isso não concede ao repositório direito de redistribuir o arquivo.

## Issues e pull requests

Não publicar em issues/PRs:

- segredos;
- dados de pacientes/participantes;
- informações privadas;
- exploit detalhado de uma vulnerabilidade ainda não corrigida.

Logs devem ser sanitizados antes do envio.

## Relato de vulnerabilidade

Quando houver mecanismo privado de security reporting disponível no GitHub do repositório, use-o.

Caso contrário, contate o mantenedor por um canal privado adequado. Não abra uma issue pública com detalhes exploráveis antes de uma correção coordenada.

## Dependências e CI

O repositório usa validações automatizadas que incluem, conforme os workflows atuais:

- security scan;
- dependency review;
- CodeQL;
- testes/compilação/lint;
- validação de artefatos de release.

Esses controles reduzem risco, mas não garantem ausência de vulnerabilidades.

## Provider safety

Contribuições a conectores devem:

- respeitar autenticação e rate limits;
- não registrar credenciais em logs;
- não contornar controles de acesso;
- tratar `401`/`403` como falha/indisponibilidade conforme o contrato do provider;
- nunca falsificar resultados quando um serviço não está disponível.

## Releases

Tags/releases publicadas são imutáveis. Uma correção de segurança após release deve ser feita em novo commit/release apropriado, sem reescrever silenciosamente o snapshot publicado.
