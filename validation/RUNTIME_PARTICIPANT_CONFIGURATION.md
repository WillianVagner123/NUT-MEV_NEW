# Runtime participant configuration

Human identities must not be hard-coded in NutEV source code or committed benchmark artifacts.

## Canonical rule

The benchmark uses opaque operational assessor IDs. Real-world identity mapping is private operational information and remains outside Git.

Generate the required assessor slots at runtime:

```bash
python tools/build_assessor_packets.py \
  --pool validation/data/VALIDATION_BLINDED_POOL.csv \
  --assessor-count 2 \
  --output-dir "$NUTEV_VALIDATION_PACKET_DIR" \
  --manifest "$NUTEV_VALIDATION_PACKET_DIR/VALIDATION_ASSESSOR_PACKETS_MANIFEST.json"
```

`--assessor-count` is configurable and must be at least 2. The default is 2 when neither an explicit count nor compatibility IDs are supplied.

The generated values are opaque identifiers such as `assessor_<digest>`. They are not names, e-mails, account IDs, or credentials.

For backward compatibility, `--assessor-id` may still be supplied repeatedly, but those values must also be opaque IDs. Never pass personally identifying values.

## Private mapping

The coordinator may maintain a private mapping from an opaque ID/private link to the intended human participant, but that mapping must not be committed to the repository or embedded in blinded benchmark artifacts.

The validation server independently creates a unique `round_id` and cryptographically random private reviewer token for each prepared session.

## Scientific guardrail

The software enforces a minimum of two independent assessors; it does not hard-code two named people. A future round may configure more than two assessors without changing source code.
