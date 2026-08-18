# Providers de busca

O NutEV Reference Engine preserva a identidade de cada provider desde a coleta até o ranking. Falhas, bloqueios, ausência de credenciais e limitações de cobertura devem permanecer explícitos.

## Providers canônicos

| Provider | Acesso | Operational | Deep | Observação |
|---|---|---:|---:|---|
| PubMed | API pública NCBI E-utilities | 2.000 | 9.999 | Usa checkpoint/resume. E-mail/API key são opcionais. |
| Europe PMC | API pública | 3.000 | 50.000 | Cobertura bibliográfica pública. |
| OpenAlex | API pública | 3.000 | 50.000 | E-mail de contato pode ser configurado. |
| Crossref | API pública | 1.000 | 10.000 | `mailto` pode ser configurado. |
| DOAJ | API pública | 1.000 | 10.000 | Metadados de periódicos open access. |
| Semantic Scholar | API pública | 1.000 | 10.000 | API key opcional. |
| Fontes oficiais | manifesto configurado | conforme manifesto | conforme manifesto | URLs institucionais definidas no repositório. |
| LILACS/BVS | interface pública nativa | tentativa nativa | tentativa nativa | `401`/`403` é registrado como `unavailable`. |
| SciELO | interface pública nativa | tentativa nativa | tentativa nativa | `401`/`403` é registrado como `unavailable`. |
| Google Programmable Search | credenciais opcionais | connector-specific | connector-specific | Só executa quando configurado. |
| Brave | credenciais opcionais | connector-specific | connector-specific | Só executa quando configurado. |
| SerpAPI | credenciais opcionais | connector-specific | connector-specific | Só executa quando configurado. |

Os limites acima são os valores atuais de `config/reference_search.json` para os providers bibliográficos principais.

## Scopus e Web of Science

O engine não simula Scopus ou Web of Science.

Se uma base licenciada não estiver integrada/configurada, ela não recebe resultados fabricados de outra fonte.

## Perfil operacional

É o padrão.

```bat
Iniciar-NutEV-Windows.bat
```

O coletor imprime:

```text
collection profile: operational
provider limits: ...
```

## Perfil profundo

Ativação explícita:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

O coletor imprime que o perfil profundo pode levar substancialmente mais tempo.

Para limpar a variável na mesma sessão:

```bat
set NUTEV_DEEP_COLLECTION=
```

## Queries

As consultas ativas ficam em:

```text
config/reference_search.json
```

O arquivo contém:

- uma query própria para PubMed;
- uma query `generic` usada por APIs compatíveis;
- uma query `web` usada por rotas web/bibliográficas apropriadas.

A documentação não deve copiar uma query para outro provider e afirmar que ela é semanticamente idêntica quando a implementação não faz isso.

## Estados de provider

### `completed`

A coleta do provider terminou com registros ou metadados válidos conforme o contrato daquele conector.

### `empty`

O provider foi consultado e não retornou registros utilizáveis para aquela tentativa/consulta.

### `failed`

A requisição ou processamento falhou. O erro deve permanecer registrado.

`failed` não significa “a base não possui literatura”.

### `unavailable`

O provider não pôde ser usado pela rota disponível naquela execução, por exemplo quando uma interface nativa recusa automação com `401` ou `403`.

`unavailable` também não significa “zero literatura”.

### `skipped`

Pode ser usado por conectores quando uma condição explícita impede a execução, como rede desabilitada ou provider desativado por configuração/ambiente.

## PubMed

Variáveis suportadas:

```text
NCBI_EMAIL
ENTREZ_EMAIL
NCBI_API_KEY
NCBI_TOOL
```

Sem API key, o cliente usa um intervalo conservador entre requisições. Sem `NCBI_EMAIL`/`ENTREZ_EMAIL`, a coleta continua e registra um aviso.

O PubMed salva checkpoints e pode retomar uma busca parcial quando o contexto de execução usa `resume=True`.

## Europe PMC, OpenAlex, Crossref, DOAJ e Semantic Scholar

São conectores públicos independentes. Falha em um deles não deve ser convertida em resultado de outro provider.

Variáveis de contato/chave documentadas:

```text
CROSSREF_MAILTO
OPENALEX_MAILTO
S2_API_KEY
```

## LILACS/BVS e SciELO

As rotas atuais usam interfaces públicas nativas.

Se a resposta for HTTP `401` ou `403`:

- o provider é marcado como `unavailable`;
- zero registros fabricados são adicionados;
- a identidade do provider é preservada;
- o ranking pode continuar quando existem masters de outras fontes.

Uma mudança futura para API oficial ou outro endpoint deve ser documentada e testada antes de substituir essa descrição.

## Providers web opcionais

Variáveis:

```text
GOOGLE_API_KEY
GOOGLE_CSE_ID
BRAVE_API_KEY
SERPAPI_API_KEY
```

Google Programmable Search requer as duas variáveis `GOOGLE_API_KEY` e `GOOGLE_CSE_ID`.

Ausência de credenciais significa que o provider opcional não participa daquela execução.

## `.env`

`.env.example` é um catálogo de variáveis. O runtime atual não carrega automaticamente um arquivo `.env`.

Defina variáveis no ambiente do processo/shell antes de executar.

Nunca versione credenciais reais.

## Cobertura e interpretação

A presença de um provider no pipeline não garante busca exaustiva.

Cobertura depende de:

- query;
- limite configurado;
- paginação;
- rate limits;
- disponibilidade do serviço;
- indexação;
- qualidade dos metadados;
- credenciais;
- mudanças de interface.

Por isso, manifests e metadados de execução devem acompanhar qualquer afirmação sobre cobertura real.
