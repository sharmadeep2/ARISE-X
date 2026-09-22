# Research: Behavioral Drift Detection Algorithms and Application to Autonomous Agent Monitoring

Context: Prior art research for ARISE-X — a platform that builds a "behavioral fingerprint" of an
autonomous agent (tool selection distribution, average steps, recovery rate, human escalation rate,
goal deviation, cost/task) and detects drift over time due to changes in model, prompt, tools, RAG
corpus, memory, or user population.

## Research Topics / Questions

1. Classic statistical concept/data drift detection algorithms: PSI, KL divergence, JS divergence,
   ADWIN, DDM, Page-Hinkley test, KS test, CUSUM — method + typical use case (data vs concept vs
   performance drift).
2. Open-source drift detection libraries: River, Evidently AI, NannyML, Alibi Detect,
   whylogs/WhyLabs — drift capabilities and integration into ML monitoring pipelines.
3. LLM-specific and agent-specific drift/monitoring concepts: LLM output drift, prompt drift, model
   behavior drift after version upgrade, embedding-based drift detection, existing research/product
   features for behavioral drift in autonomous agents or multi-step LLM apps.
4. "Behavioral fingerprint" prior art: vector-of-metrics characterization and comparison over time
   (SRE golden signals, APM baselining, ML model cards).
5. How production ML monitoring platforms (Arize AI, WhyLabs, Fiddler AI, Evidently) implement drift
   alerting thresholds and root-cause attribution.

## Status: In Progress

(placeholder — populated during research)

## Findings

(placeholder — populated during research)

## Clarifying Questions

(placeholder)
