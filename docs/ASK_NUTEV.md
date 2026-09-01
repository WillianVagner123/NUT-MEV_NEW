# Ask NutEV — grounded retrieval contract

`/ask.html` is a retrieval and context-composition workspace for Article 1. It is deliberately **not** an autonomous scientific reviewer and does not call an external LLM in this phase.

## Source

The page reads only the verified, rank-blind `agent-context/article1/ARTICLE_SUMMARIES.jsonl` bundle. The bundle contains safe metadata, route membership and deterministic review-profile context; it does not contain protected full text, Bank rank/score/tier or machine-relevance scores.

## What it does

1. accepts a natural-language question;
2. tokenizes it locally and performs deterministic lexical retrieval over titles, citation stubs, document class, route membership, operational domains and the matched terms already present in the safe review profile;
3. shows supporting documents and why they matched;
4. allows the researcher to select a smaller supporting set;
5. generates a grounded context packet that can be copied to ChatGPT, Claude or another analyzing agent;
6. points back to the Corpus Explorer / Scientific Dossier for deeper inspection.

The retrieval score is an internal navigation heuristic and is not displayed as scientific relevance, quality or eligibility.

## Scientific boundary

Ask NutEV must never turn any of the following into a scientific decision:

- lexical match;
- route membership;
- document class profile;
- retrieval/full-text status;
- evidence excerpt count;
- result bundle count.

The page does not include/exclude studies, assign risk of bias or certainty, approve recommendations, authorize PRESS/GF-10/query freeze, or emit PRISMA events.

## External models

There is no OpenAI/Anthropic/provider call in this implementation. The generated context packet is designed for a separate analyzing agent and explicitly instructs that agent to remain grounded in the supporting documents and canonical NutEV context. Connecting an external model in a future phase requires a separate provider/security/privacy contract and must not silently transmit protected full text.

## Performance

The current Article 1 bundle is limited to the verified Tier A context (662 summaries in the current production snapshot), so client-side retrieval is bounded. This page must not be changed to download the 33k Bank corpus to the browser.
