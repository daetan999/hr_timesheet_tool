# Data Pipeline & Serving Architecture

> Part of the [MERIDIAN blueprint](../README.md). All integration names are vendor-class descriptions; no client identifiers, endpoints, or production configuration appear in this document.

## 1. Ingestion & Orchestration

The predictive layer depends entirely on data freshness, quality, and consistency. MERIDIAN ingests heterogeneous, high-velocity streams from global properties and centralizes them in a dual-layer feature store.

- **Reservations & rates** — pulled in real time from the property-management system's integration platform (Oracle OHIP-class API) over REST/gRPC.
- **Building telemetry** — Building Management Systems transmit continuous utility consumption and equipment vibration over **BACnet**; edge gateway controllers pre-process signals (including FFT spectral features via NumPy) and push to **Apache Kafka**, partitioned by property for ordered, replayable consumption.
- **Batch context** — **Apache Airflow** schedules daily feature ETLs, localized weather refreshes (Cooling/Heating Degree Days against an 18 °C base), competitor-rate snapshots, and training workflows. Heavy window aggregations run as **Spark SQL** window functions over 90-day partitioned tables.

## 2. Feast Feature Store — Zero Offline/Online Skew

Feast standardizes every engineered feature so the exact same definition serves both training and live inference:

| Layer | Store | Purpose | SLA |
|---|---|---|---|
| Online | Redis Enterprise | Live inference feature retrieval | < 15 ms p99, < 5 min freshness |
| Offline | Snowflake | Point-in-time-correct training sets, backfills | High-throughput batch |

Over **70% of engineered features are shared across models**, which cut the time to ship a new predictive feature from months to days.

## 3. Training & Model Governance

- Every training run is tracked in **MLflow**: hyperparameters, metrics (MAPE, F1, loss curves), and artifacts serialized to **ONNX**.
- Models progress through strict lifecycle stages — `Staging → Production` — only after passing automated integration test suites.
- Training executes as GPU jobs on **AWS EKS**, rebuilt from the Feast offline store for full reproducibility.

## 4. High-Throughput GPU Serving

Production networks serve from **Triton Inference Server** on EKS with NVIDIA T4 instances:

- **Dynamic batching** — Triton buffers requests up to 10 ms to form parallel batches, lifting GPU utilization from ~5% to 80%+.
- **Multi-model concurrency** — 100+ property-specific models are loaded and evicted dynamically in shared GPU memory, decoupling portfolio growth from linear infrastructure cost.
- **Latency budget** — the dynamic pricing endpoint holds **p99 < 150 ms** end-to-end; breaching it causes booking drop-offs on external distribution channels.

## 5. Drift Monitoring & Closed-Loop Retraining

**Evidently AI** watches every production model:

| Drift type | Statistic | Threshold | Automated response |
|---|---|---|---|
| Feature drift | Wasserstein distance | > 0.15 | Warning surfaced to dashboards |
| Target drift | Population Stability Index | > 0.20 | Webhook fires Airflow `retrain_evaluate_promote` DAG |
| Concept drift | Page-Hinkley test | > 3σ | Pause automated pricing, page data science on-call |

The retraining DAG rebuilds the training set from the offline store, evaluates the challenger against the champion, and re-enters the same MLflow promotion gates — **no human in the hot path**. This automation reduced manual model-maintenance hours by 85%.

## 6. Failure-Mode Engineering

- **Smart-meter null drops:** sensor packet loss produces null telemetry; pipelines reject null sequences and substitute rolling-median imputations so LSTM autoencoders never crash on malformed windows.
- **Cold-start properties:** newly acquired or renovated properties lack history. Static attributes (location, tier, capacity) are t-SNE-clustered to find the most similar existing property group, and the TFT bootstraps from that cluster's pre-trained weights — transfer learning that collapsed new-property onboarding from 3 weeks to 1 hour.
