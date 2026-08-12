# Minimal example — zero-key demo

The smallest way to see NutEV/NutMEV work, with **no API keys, no network and no real data**.

```bash
python -m venv .venv
python -m pip install -e ".[dashboard]"
nutev demo-data --project-root ./project_output_demo
nutev dashboard --project-root ./project_output_demo
```

- `nutev demo-data` generates **synthetic** outputs (metadata, tables, logs and reports).
- `nutev dashboard` opens the Streamlit review UI at `http://localhost:8501`.

Outputs are a demonstration, **not** scientific evidence. For the current Article 1 PILOT workflow use a registered global strategy and `nutev play`; see [`docs/PLAY.md`](../../docs/PLAY.md) and [`docs/REPRODUCIBILITY.md`](../../docs/REPRODUCIBILITY.md).
