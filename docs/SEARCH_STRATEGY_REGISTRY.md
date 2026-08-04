# NutEV Search Strategy Registry

## Purpose

The Search Strategy Registry preserves the global, article-independent search field as an auditable sequence of immutable versions. It complements the JSON download already available in the dashboard and prevents a formal review from depending on an untracked browser session or overwritten file.

The registry does not assign retrieved records to Article 1, 2, 3, 4, or 5. Article assignment remains a later classification decision so one bibliographic record can support more than one article without being duplicated.

## Storage

The initial relational implementation uses Python's built-in SQLite support and creates:

```text
<project_root>/01_querypacks/search_registry.sqlite3
```

No new runtime dependency is required. The database enables foreign keys, WAL mode, a 30-second busy timeout, and schema versioning through SQLite `PRAGMA user_version`.

## Entities

### `search_strategies`

Stable identity of a strategy.

- `strategy_id`
- `title`
- `article_scope`
- `created_at`
- `created_by`

### `search_strategy_versions`

Immutable versions attached to a strategy.

- sequential version number;
- `PILOT`, `FORMAL`, or `SUPPLEMENTARY` classification;
- explicit PRISMA eligibility;
- original query text and normalized terms;
- filters;
- exact provider expressions;
- notes, author, and timestamp;
- SHA-256 checksum of the scientific content.

Saving an existing strategy always creates the next version. Existing versions are never edited or replaced.

### `search_executions`

Execution ledger attached to a frozen strategy version.

- provider and breadth;
- exact expression executed;
- status;
- start and finish timestamps;
- number of records found;
- error message when applicable.

The execution API is available for the next integration stage, when the dashboard will run the providers directly.

## PRISMA rules

Default behavior:

- `PILOT`: not PRISMA-eligible;
- `FORMAL`: PRISMA-eligible;
- `SUPPLEMENTARY`: PRISMA-eligible.

The dashboard displays an explicit checkbox because eligibility is a protocol decision. Pilot results must not enter formal PRISMA counts merely because they were generated in the same interface.

## Dashboard workflow

1. Build the global search using the single research field.
2. Open **Registro e versionamento**.
3. Create a new strategy or select an existing strategy to append a version.
4. Choose search type and PRISMA eligibility.
5. Enter the responsible researcher and notes.
6. Save the immutable version.
7. Review the recent-version table and checksum.

The environment variable `NUTEV_RESEARCHER_NAME` may provide the default responsible-researcher name without hard-coding personal data in the repository.

## Migration direction

This SQLite registry is the first relational slice of the review platform. Its public service functions isolate persistence from the dashboard so the tables can later move to SQLAlchemy/PostgreSQL without changing the scientific search builder.
