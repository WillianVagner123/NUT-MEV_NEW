# NutEV Scientific Article Dossier

The Corpus Explorer article detail is presented as a tabbed Scientific Dossier with these views:

- Overview;
- Methods;
- Evidence;
- Domains;
- Provenance;
- Human Review.

The dossier is a UI layer over the existing verified `/api/articles/{document_id}` response. That endpoint intentionally returns `full_text_in_response: false`.

Methods are shown only when represented by the current study snapshot or source excerpts; missing fields must not be inferred. Result bundles and evidence excerpts remain candidate machine/index artifacts and are not accepted `EvidenceClaim` objects.

The Human Review tab is fail-closed for the current Article 1 discovery/calibration corpus and links to the Review Control Center. It does not write screening decisions.

Bank priority and machine profile information remain operational navigation metadata and must stay visually distinct from human scientific decisions.
