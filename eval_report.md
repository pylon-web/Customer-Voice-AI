# Customer Voice AI — Model Quality & Compliance Benchmark

**Evaluated At:** 2026-09-29 01:18:17 UTC  
**Sample Size:** 200 reviews  
**Overall Status:** `PASSED`

## Executive KPI Summary

| Metric Dimension | Observed Score | Target SLA | Status |
| :--- | :---: | :---: | :---: |
| **Sentiment Accuracy** | **100.0%** | ≥ 85.0% | ✅ PASS |
| **Sentiment Macro F1** | **1.000** | ≥ 0.800 | ✅ PASS |
| **Category Accuracy** | **83.5%** | ≥ 80.0% | ✅ PASS |
| **Severity (Adjacent)** | **87.5%** | ≥ 90.0% | ❌ FAIL |
| **Responsible AI Guardrail** | **100.0%** | 100.0% | ✅ PASS |
| **Team Routing Accuracy** | **100.0%** | ≥ 90.0% | ✅ PASS |

## Sentiment Classification Breakdown

| Class | Support | Precision | Recall | F1-Score |
| :--- | :---: | :---: | :---: | :---: |
| **POSITIVE** | 88 | 1.000 | 1.000 | 1.000 |
| **NEUTRAL** | 28 | 1.000 | 1.000 | 1.000 |
| **NEGATIVE** | 84 | 1.000 | 1.000 | 1.000 |

## Responsible AI Guardrail Adherence

* Total Hypotheses Tested: **4**
* Zero-Certainty Violations: **0** (100% tentative framing required)
* Prohibited Phrasing Detections: `0`