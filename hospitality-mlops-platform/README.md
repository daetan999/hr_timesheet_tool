# MERIDIAN — Enterprise MLOps Platform for Hospitality Asset Intelligence

<!-- Badges: replace placeholder targets with your CI/CD and registry URLs -->
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](#)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-EE4C2C)](#)
[![MLflow](https://img.shields.io/badge/MLflow-registry-0194E2)](#)
[![Triton](https://img.shields.io/badge/Triton-inference-76B900)](#)
[![Kubernetes](https://img.shields.io/badge/EKS-GPU%20serving-326CE5)](#)
[![License](https://img.shields.io/badge/license-MIT-lightgrey)](#)

---

## Executive Summary

MERIDIAN is a production MLOps platform that replaces manual heuristics with real-time, ML-driven asset management across a global hospitality portfolio. Eight model families — demand forecasting, reinforcement-learning dynamic pricing, ESG anomaly detection, predictive maintenance, NLP ticket routing, and more — run on one shared data and serving backbone, translating model metrics directly into financial statements:

- **+$4.8M annualized profit** from a +4.2% global RevPAR lift (forecast MAPE compressed 12.5% → 4.5%)
- **−$1.8M annual utility OpEx** from LSTM-driven leak detection and HVAC load shifting (−14% utility waste)
- **+$1.5M CapEx deferred** by predicting equipment failure 14 days ahead (−42% catastrophic downtime)
- **−$240k/year cloud spend** by consolidating 100+ models onto a dynamically batched GPU cluster (−58% hosting cost)
- **85% reduction in manual model-maintenance hours** via fully automated drift-triggered retraining

---

## Data Security & Scope Disclaimer

> **Architectural Blueprint Notice:** This repository serves strictly as a sanitized, open-source structural blueprint demonstrating system design, MLOps architecture, and model engineering. The platform's internal codename, all client and property identifiers, proprietary datasets, internal endpoints, and production access tokens have been completely renamed, omitted, or mocked for security and compliance. Business impact figures are aggregated, portfolio-level modeled outcomes.

---

## Visual Architecture

### Platform Architecture — Ingest → Featurize → Train → Serve → Observe

![MERIDIAN platform architecture: PMS, IoT and market signals flow through Kafka and Airflow into a Feast feature store, feeding MLflow-governed training and Triton GPU inference behind four product views](docs/assets/platform-architecture.svg)

<details>
<summary><strong>Diagram-as-code source (Mermaid)</strong></summary>

```mermaid
flowchart TB
    subgraph Sources
        PMS[Hospitality PMS<br/>OHIP-class API · REST/gRPC]
        IOT[Building IoT / BMS<br/>BACnet telemetry · edge FFT]
        EXT[External Signals<br/>weather · competitor rates · events]
    end
    subgraph Movement["Streaming & Orchestration"]
        KAFKA[Apache Kafka<br/>partitioned-by-property topics]
        AIRFLOW[Apache Airflow<br/>batch ETL · training DAGs]
    end
    subgraph Feast["Feast Feature Store — zero offline/online drift"]
        REDIS[(Online · Redis<br/>&lt;15 ms p99)]
        SNOW[(Offline · Snowflake<br/>point-in-time training sets)]
    end
    subgraph MLPlatform["ML Platform"]
        TRAIN[EKS GPU Training<br/>MLflow registry · ONNX]
        TRITON[Triton Inference Server<br/>dynamic batching · T4 GPUs]
    end
    subgraph Views["Product Views"]
        V1[View 1 · Portfolio Financials]
        V2[View 2 · Portfolio Management]
        V3[View 3 · Sustainability ESG]
        V4[View 4 · Property Operations]
    end
    DRIFT[Evidently Drift Monitor]

    PMS --> KAFKA
    IOT --> KAFKA
    EXT --> AIRFLOW
    KAFKA --> AIRFLOW
    KAFKA --> REDIS
    AIRFLOW --> SNOW
    AIRFLOW --> REDIS
    SNOW --> TRAIN
    REDIS --> TRITON
    TRAIN -->|staged promotion| TRITON
    TRITON --> V1 & V2 & V3 & V4
    TRITON --> DRIFT
    DRIFT -->|PSI > 0.20 webhook| AIRFLOW
```

</details>

### Continuous MLOps Lifecycle — Ship → Observe → Retrain

![Continuous MLOps lifecycle: CI, MLflow registry gates, EKS canary rollout, Triton serving, Evidently drift monitoring, and a closed-loop automated retraining path](docs/assets/mlops-lifecycle.svg)

<details>
<summary><strong>Diagram-as-code source (Mermaid)</strong></summary>

```mermaid
flowchart LR
    CI[1 · Code & CI<br/>unit + integration suites] --> REG[2 · MLflow Registry<br/>ONNX · Staging→Prod gates]
    REG --> CD[3 · EKS Rollout<br/>progressive canary]
    CD --> SERVE[4 · Triton Serving<br/>p99 &lt;150 ms]
    SERVE --> MON[5 · Evidently Monitoring<br/>Wasserstein · PSI · Page-Hinkley]
    MON -->|"PSI > 0.20 webhook"| RETRAIN[Airflow DAG<br/>retrain_evaluate_promote]
    RETRAIN -->|challenger re-enters gates| REG
    MON -->|"Page-Hinkley > 3σ"| HALT[Pause pricing ·<br/>page data scientist]
```

</details>

### Technical-to-Financial Transmission

![Five transmission paths mapping model metrics to financial outcomes worth more than $8.3M annually](docs/assets/value-transmission.svg)

---

## The Four Product Views

| View | Models | Operational Role | Modeled Impact |
|---|---|---|---|
| **1 · Portfolio Financials** | Temporal Fusion Transformer (quantile demand forecasts) + PyTorch DQN pricing agent | Continuous rate optimization from booking velocity, competitor deltas, and demand quantiles | **+$4.8M** annualized profit (+4.2% RevPAR; RL agent contributes ≥ +3.2% yield vs static rules) |
| **2 · Portfolio Management** | t-SNE + K-Means asset clustering; Random Forest IRR feasibility | Context-aware peer benchmarking and acquisition feasibility scoring | Precision capital allocation across the global portfolio |
| **3 · Sustainability (ESG)** | Bidirectional LSTM autoencoders; SARIMAX thermal load forecasting | Leak/anomaly flagging within 30 minutes; HVAC pre-cooling around tariff windows | **−14%** utility waste · **−$1.8M** annual OpEx |
| **4 · Property Operations** | Weibull survival analysis × random forest; fine-tuned BERT ticket routing | 14-day failure prediction; instant work-order triage to on-duty engineers | **−42%** catastrophic downtime · MTTR **35 → 8 min** |

---

## Spotlight: The RL Dynamic Pricing Agent

The flagship model is a **Deep Q-Network (PyTorch)** trained with ε-greedy exploration over offline historical simulation:

- **State space `S`** — inventory velocity (On-The-Book vs capacity), Days-To-Arrival window, hourly competitor pricing delta, and TFT demand quantiles (τ ∈ {0.1, 0.5, 0.9})
- **Action space `A`** — continuous rate modifications constrained to a **bounded action space** (−15% … +35% of baseline rack rate) to prevent race-to-the-bottom feedback loops with competitor pricing algorithms
- **Reward `R`** — maximizes yield over a rolling 30-day booking window: `R = Σ (Occupancy × ADR) − Penalty(overprice-vacancy)`
- **Hard SLA** — evaluate state and return a pricing action in **< 150 ms p99**; stale prices cause booking drop-offs on external channels

Skeleton implementation: [`models/pricing_agent/dqn_pricing_agent.py`](models/pricing_agent/dqn_pricing_agent.py)

---

## Engineered Feature Families

| Feature family | Grain | Contents | Computed by |
|---|---|---|---|
| `F_Demand_Lag` | room class × property | Rolling ADR & occupancy at t−1/7/14/30 · OTB booking velocity (first derivative) | Spark SQL window functions over 90-day partitions |
| `F_Climate_Index` | property location | Cooling / Heating Degree Days vs 18 °C base | Python microservice over weather APIs |
| `F_Telemetry_Spectral` | HVAC asset | FFT magnitude bands, peak frequencies, kurtosis from raw vibration | NumPy at the edge → Kafka |

Feature definitions: [`feature_store/feature_definitions.py`](feature_store/feature_definitions.py)

---

## Reliability Engineering

**Service-level objectives**

| SLO | Target |
|---|---|
| Pricing endpoint inference latency | p99 < 150 ms |
| Feature freshness (PMS event → Redis) | < 5 min |
| Daily ETL ingestion success | > 99.9% |

**Hardened edge cases**

- **Smart-meter null-value drops** — ingestion rejects null telemetry sequences and substitutes rolling-median inputs, preventing LSTM autoencoder crashes on sensor packet loss.
- **Cold-start properties** — new acquisitions with no booking history are t-SNE-mapped to their nearest existing property cluster and bootstrapped from that cluster's pre-trained TFT weights (transfer learning), giving day-one pricing accuracy and cutting onboarding from **3 weeks to 1 hour**.
- **Drift response tiers** — feature drift (Wasserstein > 0.15) warns; target drift (PSI > 0.20) auto-retrains; concept drift (Page-Hinkley > 3σ) pauses automated pricing and pages a human.

---

## Repository Map

```
docs/                  Architecture deep-dives, model portfolio, business impact case studies
docs/assets/           Hand-built SVG architecture diagrams (render natively on GitHub)
pipelines/airflow/     Feature-engineering and drift-triggered retraining DAGs (illustrative)
feature_store/         Feast feature definitions (entity/view schemas)
models/                DQN pricing-agent skeleton · TFT hyperparameter manifest
serving/               Triton dynamic-batching config · EKS deployment manifest
monitoring/            Evidently drift thresholds and monitor service (illustrative)
```

All code in this repository is **illustrative blueprint code**: it demonstrates the interfaces, configuration shapes, and engineering conventions of the production system without any proprietary logic, data, or credentials.

---

## Deep-Dive Documentation

- [`docs/architecture.md`](docs/architecture.md) — data pipeline, feature store, and serving architecture
- [`docs/model-portfolio.md`](docs/model-portfolio.md) — per-view model specifications and mathematics
- [`docs/business-impact.md`](docs/business-impact.md) — five case studies linking model metrics to P&L

---

## License

Released under the MIT License.
