# Technical Resume — Solutions Engineering & MLOps Portfolio

**@daetan999** · Principal-level solutions engineering across MLOps, agentic AI, workflow automation, and cloud infrastructure.

<!-- Add your preferred contact channels: -->
<!-- [LinkedIn](#) · [Email](#) -->

Every project below is a **sanitized public blueprint of a production system**: client identifiers, credentials, internal endpoints, and proprietary integrations are removed or mocked — the architecture, the engineering judgment, and the measured business impact are what remain. Diagrams are hand-built SVG (rendered natively by GitHub) with Mermaid diagram-as-code sources alongside.

---

## Portfolio at a Glance

| Project | Domain | Core Stack | Measured Impact |
|---|---|---|---|
| **[MERIDIAN — Enterprise MLOps Platform](https://github.com/daetan999/hospitality-mlops-platform)** | ML-driven hospitality asset intelligence | PyTorch · Feast · Kafka · Airflow · MLflow · Triton · EKS · Snowflake · Redis | **>$8.3M annualized** across 5 value paths |
| **[HR Timesheet Tool](https://github.com/daetan999/hr_timesheet_tool)** | Workforce time-capture automation | Python · FastAPI · Jinja2 · PyMuPDF · openpyxl | Payroll cycle: **days → minutes**; auditable review trail |
| Agentic FP&A Analytics *(blueprint in preparation)* | LLM agent system for marketing-mix P&L analytics | Google Agent Development Kit (ADK) · GCP | — |
| Enterprise GCP Data Platform *(blueprint in preparation)* | Cloud data platform & workflow design | GCP · warehouse-centric data lake · UML-documented architecture | — |

---

## Featured: MERIDIAN — Enterprise MLOps Platform

Eight model families — quantile demand forecasting (Temporal Fusion Transformer), a bounded-action **DQN reinforcement-learning pricing agent**, LSTM-autoencoder ESG anomaly detection, Weibull survival predictive maintenance, fine-tuned BERT ticket routing — operating on one shared data and serving backbone, with fully automated drift-triggered retraining (no human in the hot path).

[![MERIDIAN platform architecture](docs/assets/meridian-platform-architecture.svg)](https://github.com/daetan999/hospitality-mlops-platform)

**What makes it principal-level engineering:**

- **A feature store as the contract** — Feast with Redis online (< 15 ms p99) and Snowflake offline guarantees zero training/serving skew; 70%+ feature reuse across models cut new-feature delivery from months to days.
- **Serving economics** — Triton dynamic batching + multi-model GPU concurrency consolidated 100+ single-tenant CPU pods onto a small shared T4 cluster: GPU utilization ~5% → 80%+, hosting spend −58%.
- **Self-correcting production** — Evidently drift tiers (Wasserstein warn / PSI auto-retrain / Page-Hinkley halt-and-page) reduced manual model maintenance by 85%.
- **Metrics that land on the P&L** — every model KPI maps to a financial statement line:

[![Technical-to-financial transmission](docs/assets/meridian-value-transmission.svg)](https://github.com/daetan999/hospitality-mlops-platform)

**→ Full blueprint: [`hospitality-mlops-platform`](https://github.com/daetan999/hospitality-mlops-platform)**

---

## Featured: HR Timesheet Tool — Workforce Time-Capture Blueprint

An automated capture-to-payroll workflow replacing paper time cards and spreadsheet reconciliation: structured ingestion of scanned/photographed time cards, deterministic validation with exception surfacing, an exception-driven HR review queue, and payroll-ready Excel export — server-rendered FastAPI/Jinja2 with a pluggable (mocked) extraction layer.

[![Timesheet end-to-end submission pipeline](docs/assets/timesheet-system-flow.svg)](https://github.com/daetan999/hr_timesheet_tool)

| Relational schema, designed for 1:1 SQL promotion | Product — exception-driven review queue |
| --- | --- |
| [![Timesheet relational schema](docs/assets/timesheet-data-schema.svg)](https://github.com/daetan999/hr_timesheet_tool) | [![Review queue screenshot](docs/assets/timesheet-review.png)](https://github.com/daetan999/hr_timesheet_tool) |

**→ Full blueprint: [`hr_timesheet_tool`](https://github.com/daetan999/hr_timesheet_tool)**

---

## In-Flight Blueprints

- **Agentic FP&A Analytics** — an LLM agent system built on Google's **Agent Development Kit** for marketing-mix-modeling P&L analysis on GCP. Sanitized public duplicate in preparation; architecture diagrams will accompany it.
- **Enterprise GCP Data Platform** — a cloud data platform with UML-documented workflows and GCP infrastructure design. Sanitized public duplicate in preparation.

---

## Engineering Competency Matrix

| Discipline | Evidenced By | Technologies |
|---|---|---|
| **MLOps & Model Serving** | MERIDIAN registry-gated CD, drift-triggered retraining, GPU serving economics | MLflow · ONNX · Triton · Evidently · EKS/Kubernetes |
| **ML Engineering** | Quantile TFT forecasting, DQN RL with bounded action spaces, LSTM autoencoders, survival analysis, fine-tuned BERT | PyTorch · pytorch-forecasting · scikit-learn |
| **Data Platforms** | Dual-layer Feast feature store, Kafka streaming, Spark SQL window features, warehouse modeling | Feast · Kafka · Airflow · Spark · Snowflake · Redis |
| **Backend & Product Engineering** | Timesheet capture-to-payroll workflow, exception-driven review UX, document processing | Python · FastAPI · Jinja2 · PyMuPDF · openpyxl |
| **Agentic AI** | ADK-based FP&A agent system (blueprint in preparation) | Google ADK · GCP |
| **Architecture Communication** | Every repo: diagrams-as-code, hand-built SVG system diagrams, ERDs, value-transmission maps | SVG · Mermaid · UML |

---

## How These Blueprints Are Built

1. **Confidentiality inventory** — every project name, client identifier, dataset/table name, endpoint, and credential in the source system is catalogued.
2. **Sanitize, don't lobotomize** — identifiers are renamed or mocked; architecture, data models, SLOs, and failure-mode engineering are preserved faithfully.
3. **Diagrams as code** — system diagrams are generated SVG (strict-XML-valid, GitHub-native rendering) with Mermaid sources embedded for maintainability.
4. **Impact stays quantified** — business results are kept as aggregated, portfolio-level figures with the mechanism that produced them, because architecture without outcomes is decoration.

---

## License

Portfolio content and diagrams released under the MIT License.
