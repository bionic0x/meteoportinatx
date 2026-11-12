# D-021 — Instrument QC and durable forensic archive (#7)

**Language / Idioma:** [Español](DECISION-FORENSE-QC-Y-ALMACEN.md) · English

**Decision: 11 November 2026 · status: policy adopted, remote store NOT provisioned.**
Scope: research archive and out-of-sample PROSPECTIVE benchmark.
No effect on alerts, models, 24/7 monitoring or Render Free.

## 1. Source of truth and durability

An **exclusive PRIVATE GitHub repository** (`meteoportinatx-forecast-ledger-private`) is selected as the primary remote store, with **a second independent encrypted copy** on an owner-managed computer/disk (weekly backup). Do not store secrets, personal data, the property's location or owner-entered observations. Include only verified public station identifiers and coordinates, authorised instrument metrics, frozen forecasts, QC reasons and hashes. Avoid Git LFS and large files; partition by date and episode.

Rationale: Render Free has no persistent disk and GitHub Actions artifacts expire; neither is suitable as a durable system of record. Private Git provides history and access management, **but Git is not WORM and guarantees neither immutability nor backup**. The second copy, SHA-256 hash log and restore tests are essential. Do not claim “verified durable archive” until demonstrating restoration from the external copy of **20 forecast/observation pairs** with the same hashes, scores and exclusions. Protect the branch and use least-privilege access where the account permits. Do not enable paid services. Creating the private repository and minimally scoped authentication secret requires owner intervention: the current connector cannot create repositories or write secrets.

The local `src/forecast_ledger.py` ledger maintains the timeline `issued_at`, `provider_run_at`, `valid_from`, `valid_to` and `captured_at`. Only captures made before the validity window are prospective; remote imports are excluded from the prospective benchmark unless independently attested. Write locally first (atomic operation), replicate afterwards, and record receipts and SHA-256. If replication fails, report `ARCHIVE_AT_RISK` without pretending it is backed up.

## 2. QC criteria for PORTUS buoys (Hs)

| Check | Result |
|---|---|
| Buoy identity, verified coordinates, instrument, provider, unit and UTC timestamp with timezone | If any is missing: `UNKNOWN` |
| Non-finite sample, negative Hs, impossible timestamp, explicitly invalid provider flag, contradictory identity | `REJECTED` |
| Hmax present but less than Hs, non-positive Tp, direction outside 0–360°, uncorroborated sudden jumps, duplicates/conflicts for the same buoy/time | `UNKNOWN`, manual review; do not automatically declare a physical error in extreme events |
| Physically plausible sample without a **documented provider quality flag**, or without traceability to the original measurement | `UNKNOWN` (**do not** promote to PASS merely because it comes from an official API) |
| Unambiguously good provider quality flag, documented semantics, verified station/UTC/unit, no anomalies or duplicates | `INSTRUMENT_QC_PASS` after independent review/audit of the adapter |

The current `src_portus` implementation does NOT publish an explicit source instrument-quality field: **the forensic archive must classify these readings as `UNKNOWN` by default** until the provider indicator is incorporated and validated. Do not retroactively change an original `UNKNOWN`: retain the review and evidence as a new linked record. Do not mix Hs with Hmax, swell or wave height inside Portinatx.

**Freshness ≠ retrospective QC:** for live decisions, an Hs observation expires after 120 minutes (current operational criterion, subject to calibration against actual PORTUS cadence); a valid historical reading is not rejected solely because it is old. Each datum retains `observed_at` in UTC, `captured_at`, `source_id` and source hash. Do not use download time as instrument time. Retain duplicates with an auditable exclusion or deduplication reason.

**Verification pairing** (distinct from instrument QC): same station identifier and spatial domain, same units and validity window (exact match in the ledger), model at the buoy's actual coordinates and model time within ±30 minutes only for the `sea_model_check` diagnostic. Prospective skill also requires a previously frozen model and the same verified observation. Do not compare a 72-hour forecast maximum in the bay against the latest buoy 68–172 km away. No valid pair: `NO_COMPARABLE`, not “model was right/wrong”.

## 3. Activation gates

1. Identify PORTUS QC flags, their dictionary and reporting interval in provider documentation; add authorised real samples and tests.
2. Provision a private repository, minimum-scope credential, external encrypted backup and a 20-pair restore test; document integrity and access revocation.
3. Run in shadow for 90 days with a baseline, denominators, independent episodes and exclusion reasons, without touching alert weights.
4. Activate only after reviewing data, reuse permission and cron failures. Until then #7 remains **open**.

Sources: `docs/FORECAST-LEDGER-P0.md`, `src/forecast_ledger.py`, [Puertos del Estado, real time](https://portus.puertos.es/Portus/html/info/infotr.html) and [buoy representativeness FAQ](https://www.puertos.es/servicios/oceanografia/faqs).
