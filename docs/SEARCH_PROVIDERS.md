# Search providers

The NutEV Reference Engine uses a deliberately small set of provider connectors. Provider identity is preserved into ranking records.

## Canonical providers

| Provider | Access | Notes |
|---|---|---|
| PubMed | Public API | NCBI email/API key may improve responsible access. |
| Europe PMC | Public API | Public bibliographic coverage. |
| OpenAlex | Public API | Contact email can be configured where supported. |
| Crossref | Public API | Contact email can be configured where supported. |
| DOAJ | Public API | Open-access journal metadata. |
| Semantic Scholar | Public API | API key optional. |
| Official web sources | Configured manifest | URLs are loaded from repository configuration. |
| LILACS/BVS | Public native web search | Provider HTML is retained as retrieval evidence for the run. |
| SciELO | Public native web search | Provider HTML is retained as retrieval evidence for the run. |
| Google Programmable Search | Optional credentials | Used only when configured. |
| Brave | Optional credentials | Used only when configured. |
| SerpAPI | Optional credentials | Used only when configured. |

## Licensed providers

Scopus and Web of Science are not simulated. When licensed access is not configured, the collection manifest reports them as unavailable rather than substituting another database.

## Failure behavior

A provider error produces an explicit failed provider entry and an empty provider output for that attempt. A failure does not fabricate zero-result evidence and does not silently change provider identity.

## Configuration

Canonical search queries and collection limits are stored in:

```text
config/reference_search.json
```

Optional credentials are documented in `.env.example`.
