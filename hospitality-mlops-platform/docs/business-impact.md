# Business Impact — Five Technical-to-Financial Case Studies

> Part of the [MERIDIAN blueprint](../README.md). Figures are aggregated, portfolio-level modeled outcomes; all client and property identifiers are withheld.

Enterprise ML programs fail when technical metrics never reach the financial statements. MERIDIAN's five transmission paths:

![Value transmission diagram](assets/value-transmission.svg)

## 1. +4.2% RevPAR Lift → +$4.8M Annualized Profit

- **Under-prediction (lost margin):** legacy heuristics sold out inventory early at non-surge rates. The TFT detects early booking-velocity anomalies (local events, corporate blocks) and surge-prices the remaining ~20% of inventory — pure margin capture.
- **Over-prediction (empty rooms):** an unsold room-night expires worthless at midnight. Compressing MAPE to 4.5% optimally balances occupancy against ADR (`RevPAR = Occupancy × ADR`).
- The RL pricing agent contributes a floor of **+3.2% yield over static rules** inside this lift.

## 2. −14% Utility Waste → −$1.8M Annualized OpEx

- **Ghost leaks:** pipe leaks behind drywall run undetected for weeks. Evaluating 15-minute smart-meter windows, the autoencoder flags continuous overnight flow within 30 minutes; automated alerts dispatch on-site shutoffs — avoiding water loss and structural mold remediation.
- **Load shifting:** thermal-load forecasts pre-cool heavy-mass zones in cheap off-peak hours and curtail HVAC during peak tariffs.

## 3. −42% Catastrophic Downtime → +$1.5M CapEx Deferred

Chiller compressors degrade over months with subtle vibration and current-draw signatures that calendar-based maintenance misses until seizure — $120k+ immediate capital and 3–4 weeks of lead time per unit. Weibull MTTF models schedule an off-peak **$500 bearing replacement** instead, extending asset life and eliminating emergency call-out premiums.

## 4. −58% Cloud Hosting → −$240k/Year Saved

The original architecture ran one CPU inference server per property, idle ~95% of the time against bursty pricing traffic. Consolidating 100+ property models onto a shared Triton GPU cluster with 10 ms dynamic batching lifted GPU utilization from ~5% to 80%+, cut the hosting bill 58%, and absorbs 10× reservation-volume spikes without re-architecture.

## 5. 77% MTTR Reduction → +3% Repeat Bookings

Every minute of unresolved guest issues (broken safe, failed AC) erodes lifetime value and invites negative reviews. BERT-based routing parses guest-app and internal log text, determines urgency and issue type, and lands a work order on the correct on-duty engineer's device in seconds — MTTR **35 → 8 minutes**.
