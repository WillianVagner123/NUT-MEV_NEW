# Search providers

The NutEV Reference Engine uses a deliberately small set of provider connectors. Provider identity is preserved into ranking records.

## Canonical providers

| Provider | Access | Operational limit | Notes |
|---|---|---:|---|
| PubMed | Public API | 2,000 | NCBI email/API key may improve responsible access. Checkpoints support resume. |
| Europe PMC | Public API | 3,000 | Public bibliographic coverage. |
| OpenAlex | Public API | 3,000 | Contact email can be configured where supported. |
| Crossref | Public API | 1,000 | Contact email can be configured where supported. |
| DOAJ | Public API | 1,000 | Open-access journal metadata. |
| Semantic Scholar | Public API | 1,000 | API key optional. |
| Official web sources | Configured manifest | manifest-defined | URLs are loaded from repository configuration. |
| LILACS/BVS | Public native web search | native page | Provider HTML is retained when access succeeds. HTTP 401/403 is recorded as `unavailable`. |
| SciELO | Public native web search | native page | Provider HTML is retained when access succeeds. HTTP 401/403 is recorded as `unavailable`. |
| Google Programmable Search | Optional credentials | connector-specific | Used only when configured. |
| Brave | Optional credentials | connector-specific | Used only when configured. |
| SerpAPI | Optional credentials | connector-specific | Used only when configured. |

## Collection profiles

The default profile is `operational` and uses `provider_limits` from `config/reference_search.json`.

A larger `deep` profile is available only by explicit opt-in and uses `deep_provider_limits`:

| Provider | Operational | Deep |
|---|---:|---:|
| PubMed | 2,000 | 9,999 |
| Europe PMC | 3,000 | 50,000 |
| OpenAlex | 3,000 | 50,000 |
| Crossref | 1,000 | 10,000 |
| DOAJ | 1,000 | 10,000 |
| Semantic Scholar | 1,000 | 10,000 |

Windows CMD:

```bat
set NUTEV_DEEP_COLLECTION=1
Iniciar-NutEV-Windows.bat
```

The active collection profile and provider limits are printed before network collection begins.

## Licensed providers

Scopus and Web of Science are not simulated. When licensed access is not configured, the collection manifest reports them as unavailable rather than substituting another database.

## Failure and unavailable behavior

A provider error produces an explicit status entry and never fabricates zero-result evidence.

For normal API providers, request failures are recorded as provider failures with the error message retained in run metadata.

For native LILACS/BVS and SciELO public web interfaces, HTTP `401` or `403` means automated access was refused by the remote interface. The current runtime records those providers as `unavailable` rather than treating the access denial as a fatal pipeline failure. The ranking can continue using successfully collected sources.

An unavailable or failed provider must not be interpreted as proof that the provider contains no relevant literature.

## Configuration

Canonical search queries and collection limits are stored in:

```text
config/reference_search.json
```

Ranking focus keywords and provider weights are stored in:

```text
config/reference_mode.json
```

## Credentials and contact metadata

Supported variable names are documented in `.env.example`.

The current runtime does **not** automatically load a `.env` file. Set environment variables in the shell or process environment before running.

Examples in Windows CMD:

```bat
set NCBI_EMAIL=you@example.com
set NCBI_API_KEY=...
set CROSSREF_MAILTO=you@example.com
set OPENALEX_MAILTO=you@example.com
set S2_API_KEY=...
set GOOGLE_API_KEY=...
set GOOGLE_CSE_ID=...
set BRAVE_API_KEY=...
set SERPAPI_API_KEY=...
```

Never commit real secrets.
