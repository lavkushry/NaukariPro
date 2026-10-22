# 🏗️ How to Write MLOps Project Points — Project Bullet Writing Guide

> **Target:** 2 YOE MLOps Engineer targeting Google, Amazon, Microsoft, Uber, Atlassian, Salesforce, Adobe, LinkedIn, Flipkart, Razorpay, Databricks, NVIDIA  
> **Governed by:** [`AGENTS.md`](./AGENTS.md) — all bullets follow the 5-Stage Engineering Formula  
> **Last Updated:** June 29, 2026

---

## Table of Contents

1. [What Makes a Project Point Strong](#1-what-makes-a-project-point-strong)
2. [The 5-Stage Engineering Formula for Projects](#2-the-5-stage-engineering-formula-for-projects)
3. [Project Selection Criteria](#3-project-selection-criteria)
4. [How Many Projects & Which Ones](#4-how-many-projects--which-ones)
5. [What Recruiters Look For in Projects](#5-what-recruiters-look-for-in-projects)
6. [How to Show Production Readiness](#6-how-to-show-production-readiness)
7. [How to Include GitHub Links & Architecture](#7-how-to-include-GitHub-links--architecture)
8. [20 Weak → Strong Project Bullet Transformations](#8-20-weak--strong-project-bullet-transformations)
9. [15 Reusable Project Bullet Templates](#9-15-reusable-project-bullet-templates)
10. [8 Complete MLOps Project Examples](#10-8-complete-mlops-project-examples)
11. [Realistic Metrics for Projects](#11-realistic-metrics-for-projects)
12. [README Structure for Each Project](#12-readme-structure-for-each-project)
13. [GitHub Repo Structure](#13-GitHub-repo-structure)
14. [ATS Keywords for Projects](#14-ats-keywords-for-projects)
15. [Mistakes to Avoid](#15-mistakes-to-avoid)

---

## 1. What Makes a Project Point Strong

A strong MLOps project bullet answers **5 questions in one line:**

| Question | Signal |
|:---|:---|
| **What did you build?** | Production system, not a notebook |
| **What tools did you use?** | MLOps/DevOps stack — ATS keyword match |
| **How is it automated?** | CI/CD, orchestration, event-driven triggers |
| **At what scale?** | Throughput, volume, concurrency |
| **What was the impact?** | Latency, uptime, cost, deployment speed |

**Key hiring manager insight:** Projects are your **proof-of-work**. At 2 YOE, your projects are often stronger signals than your job experience. Hiring managers at Google, Amazon, and Uber inspect GitHub repos before phone screens.

**What differentiates a project from experience:** Project bullets should emphasize **architecture decisions**, **tool integration**, and **end-to-end lifecycle** — showing you can design systems from scratch, not just maintain existing ones.

> **Source:** Amazon Engineering Blog, Google Cloud MLOps Whitepaper, KodeKloud MLOps Survey 2026

---

## 2. The 5-Stage Engineering Formula for Projects

$$\text{[Action Verb]} + \text{[ML System]} + \text{[MLOps Tool]} + \text{[Automation/Scale]} + \text{[Impact]}$$

### Anatomy of a Strong Project Bullet

```
Architected    a GitOps ML deployment platform    using ArgoCD, Helm, and EKS,
[Action Verb]  [ML System]                        [MLOps Tool]

automating zero-downtime rolling deployments for 6+ production model microservices,
[Automation/Scale]

eliminating manual deployment steps and reducing release time from 2 hours to 8 minutes.
[Impact]
```

### Key Difference from Experience Bullets

| Dimension | Experience Bullet | Project Bullet |
|:---|:---|:---|
| **Scope** | What you did at work | What you designed from scratch |
| **Focus** | Operational impact | Architecture decisions |
| **Ownership** | "Engineered..." (contribution to team) | "Architected..." (end-to-end design) |
| **Evidence** | Company context | GitHub link + README |

---

## 3. Project Selection Criteria

### Scoring Rubric (Rate Each Project 0–100)

| Criterion | Weight | Score 0 | Score 50 | Score 100 |
|:---|:---|:---|:---|:---|
| **End-to-End Lifecycle** | 25% | Training only | Train + Deploy | Train → Deploy → Monitor → Retrain |
| **Production Readiness** | 20% | Jupyter notebook | Docker container | K8s + health checks + scaling |
| **CI/CD Automation** | 15% | Manual deploys | Basic CI | Full CI/CD with quality gates |
| **Observability** | 15% | No monitoring | Basic logging | Prometheus + Grafana + alerting |
| **Data Engineering** | 10% | Static CSV | Basic pipelines | Feature store + versioning |
| **Cloud & IaC** | 10% | Local only | Single cloud service | Multi-service IaC (Terraform) |
| **Documentation** | 5% | No README | Basic README | Architecture diagram + quickstart |

**Target:** Only include projects scoring **75+/100** on your resume.

---

## 4. How Many Projects & Which Ones

### Rules

| Rule | Guidance |
|:---|:---|
| **Number** | **2–3 projects** on resume (not more — quality > quantity) |
| **Depth** | 2 bullets per project (one architecture, one impact) |
| **Links** | Every project MUST have a GitHub link |
| **Diversity** | Each project should showcase a **different** MLOps skill cluster |

### Decision Framework: Which Projects to Include

| If your work experience emphasizes... | Your projects should emphasize... |
|:---|:---|
| CI/CD & deployment | Monitoring, drift detection, feature stores |
| Monitoring & observability | LLMOps, RAG pipelines, model optimization |
| Batch processing | Real-time serving, streaming, low-latency inference |
| Traditional ML | LLMOps, vector databases, GenAI infrastructure |

### What to Exclude

* ❌ Titanic, MNIST, Iris — toy datasets signal junior/student level
* ❌ Jupyter-only projects without infrastructure code
* ❌ Course completion projects from Coursera/Udemy
* ❌ Projects without CI/CD (`.GitHub/workflows/`)
* ❌ Forked repos presented as your own work
* ❌ More than 3 projects (dilutes page space)

---

## 5. What Recruiters Look For in Projects

Based on 50+ MLOps JD analysis (June 2026):

| # | Signal | What It Proves | Frequency in JDs |
|:---|:---|:---|:---|
| 1 | **Containerized deployment** | Can ship production artifacts | 95% |
| 2 | **CI/CD pipeline** | Understands automation-first development | 90% |
| 3 | **Kubernetes orchestration** | Can manage production workloads | 85% |
| 4 | **Model registry** | Understands governance and versioning | 75% |
| 5 | **Monitoring & alerting** | Understands operational reliability | 70% |
| 6 | **API serving (FastAPI/gRPC)** | Can build serving infrastructure | 80% |
| 7 | **Cloud services** | Can work with managed cloud infrastructure | 90% |
| 8 | **Data versioning** | Understands reproducibility | 55% |
| 9 | **Drift detection** | Understands model lifecycle management | 45% |
| 10 | **LLMOps / RAG** | Shows modern GenAI infrastructure skills | 35% |

---

## 6. How to Show Production Readiness

A production-ready project is **not** a Jupyter notebook with model.fit(). It must demonstrate:

### Production Readiness Checklist

| Layer | Must-Have | How to Show |
|:---|:---|:---|
| **Containerization** | Dockerfile with multi-stage build | `Dockerfile` in repo root |
| **Orchestration** | K8s manifests or Docker-compose | `infra/k8s/` or `Docker-compose.yml` |
| **CI/CD** | Automated test + build + deploy | `.GitHub/workflows/ci.yml` |
| **API Serving** | REST/gRPC endpoint with docs | FastAPI with `/docs` Swagger |
| **Health Checks** | Liveness & readiness probes | K8s probe configs or `/health` endpoint |
| **Monitoring** | Metrics collection | Prometheus configs + Grafana dashboard |
| **Data Versioning** | Dataset tracking | `dvc.yaml` or DVC configuration |
| **Model Registry** | Model versioning and staging | MLflow integration with stage transitions |
| **Testing** | Unit + integration tests | `tests/` directory with pytest |
| **Documentation** | README with architecture | Architecture diagram + quickstart guide |

### Before vs After

```
BEFORE (Notebook-only):
├── model.ipynb          ← Training notebook
├── data/train.csv       ← Raw data
└── requirements.txt     ← No infrastructure

AFTER (Production-ready):
├── .GitHub/workflows/   ← CI/CD
├── src/
│   ├── train/           ← Training pipeline
│   ├── serve/           ← FastAPI inference
│   └── monitor/         ← Drift detection
├── infra/
│   ├── k8s/             ← K8s manifests
│   └── Terraform/       ← IaC
├── tests/               ← pytest
├── Dockerfile           ← Multi-stage build
├── Docker-compose.yml   ← Local orchestration
├── dvc.yaml             ← Data versioning
└── README.md            ← Architecture + quickstart
```

---

## 7. How to Include GitHub Links & Architecture

### Resume Format

```
PROJECT NAME | GitHub.com/username/repo-name
Tech Stack: Python, Docker, Kubernetes, ArgoCD, MLflow, GitHub Actions

• [Architecture/deployment bullet following 5-stage formula]
• [Monitoring/impact bullet following 5-stage formula]
```

### Architecture Diagrams

Include a Mermaid or ASCII architecture diagram in your README:

```
Data Source → Airflow DAG → Feature Engineering → MLflow Registry
                                                      ↓
                                              Docker Build → ECR
                                                      ↓
                                              ArgoCD → EKS Cluster
                                                      ↓
                                              FastAPI ← Load Balancer
                                                      ↓
                                              Prometheus → Grafana
```

### GitHub Link Rules

* Use full URL: `GitHub.com/username/repo-name` (not shortened)
* Repository must have a comprehensive README
* Repository must have at least `.GitHub/workflows/` and `Dockerfile`
* Never link to private repos (recruiter can't access)
* Never link to empty/skeleton repos

---

## 8. 20 Weak → Strong Project Bullet Transformations

### 1. End-to-End ML Pipeline

**❌ Weak:** "Created an end-to-end ML pipeline."  
**✅ Strong:** "Architected an end-to-end ML deployment pipeline using Airflow, MLflow, and Docker, automating data validation, model training, registry promotion, and containerized serving for 3 production models."  
**💡 Why:** Shows full lifecycle, specific tools, and production context.

### 2. Kubernetes Deployment

**❌ Weak:** "Deployed model on Kubernetes."  
**✅ Strong:** "Deployed production inference services on AWS EKS using Helm charts and Terraform, configuring HPA for auto-scaling and health check probes for zero-downtime availability."  
**💡 Why:** Shows K8s depth (HPA, Helm, probes) and IaC (Terraform).

### 3. CI/CD Pipeline

**❌ Weak:** "Set up CI/CD for the project."  
**✅ Strong:** "Engineered GitHub Actions CI/CD workflows automating lint checks, unit tests, Docker build, Trivy security scanning, and ArgoCD-triggered Kubernetes deployments on main branch merge."  
**💡 Why:** Specifies each CI/CD stage, security awareness, and deployment strategy.

### 4. Model Monitoring

**❌ Weak:** "Added monitoring to the project."  
**✅ Strong:** "Implemented Prometheus metrics collection and Grafana dashboards tracking prediction latency, throughput, and feature distribution drift across 4 inference endpoints."  
**💡 Why:** Shows specific metrics tracked, tool depth, and multi-endpoint scope.

### 5. Docker Containerization

**❌ Weak:** "Used Docker for the project."  
**✅ Strong:** "Containerized the training and inference pipeline using multi-stage Docker builds, reducing image sizes from 2.1GB to 380MB by separating build dependencies from runtime."  
**💡 Why:** Shows technique (multi-stage), before→after numbers, and optimization reasoning.

### 6. FastAPI Serving

**❌ Weak:** "Built an API for model serving."  
**✅ Strong:** "Built async FastAPI inference endpoints with automatic OpenAPI documentation, connection pooling, and structured logging, handling 800+ concurrent requests at sub-35ms average latency."  
**💡 Why:** Shows async architecture, documentation, performance metrics.

### 7. MLflow Model Registry

**❌ Weak:** "Used MLflow for experiment tracking."  
**✅ Strong:** "Integrated MLflow tracking and model registry with automated stage transitions (Staging → Production) based on benchmark validation, managing 20+ model versions with full artifact lineage."  
**💡 Why:** Shows governance workflow, automated promotion, and version scale.

### 8. Airflow DAGs

**❌ Weak:** "Created Airflow DAGs."  
**✅ Strong:** "Developed Airflow DAGs with S3 data-arrival sensors for event-driven model retraining, configuring automatic retries, SLA monitoring, and Slack failure notifications."  
**💡 Why:** Shows event-driven design, reliability patterns, and operational alerting.

### 9. Feature Store

**❌ Weak:** "Built a feature store."  
**✅ Strong:** "Engineered a real-time feature serving pipeline using Feast and Redis, achieving sub-10ms online lookup latency and eliminating training-serving skew across 8 model features."  
**💡 Why:** Shows latency optimization, consistency guarantee, and feature scale.

### 10. Data Versioning

**❌ Weak:** "Tracked data using DVC."  
**✅ Strong:** "Integrated DVC with S3 for dataset versioning and experiment reproducibility, enabling exact recreation of any model training run across 50+ experiments."  
**💡 Why:** Shows reproducibility guarantee and experiment volume.

### 11. Drift Detection

**❌ Weak:** "Detected model drift."  
**✅ Strong:** "Implemented automated data drift monitoring using PSI (Population Stability Index) via Evidently AI, triggering Airflow retraining DAGs when feature distributions exceeded configurable thresholds."  
**💡 Why:** Shows statistical technique (PSI), tool specificity, and automated response.

### 12. LLMOps / RAG Pipeline

**❌ Weak:** "Built a RAG pipeline with LangChain."  
**✅ Strong:** "Architected a production RAG pipeline using vLLM, Qdrant vector database, and LangChain, serving sub-400ms retrieval-augmented responses with automated hallucination guardrail alerts."  
**💡 Why:** Shows LLM serving (vLLM), vector DB, safety guardrails — all 2026 high-signal.

### 13. Terraform Infrastructure

**❌ Weak:** "Used Terraform for cloud."  
**✅ Strong:** "Provisioned reproducible ML infrastructure on AWS (EKS, S3, ECR, IAM) using Terraform modules with remote state locking, enabling one-command environment setup across Dev/Staging/Prod."  
**💡 Why:** Shows Terraform depth (modules, remote state) and multi-environment strategy.

### 14. Batch Inference

**❌ Weak:** "Ran batch predictions."  
**✅ Strong:** "Engineered a distributed batch inference pipeline using PySpark and PyTorch, processing 500K+ records/hour with automated checkpointing, retry logic, and prediction distribution validation."  
**💡 Why:** Shows distributed systems, reliability patterns, and data validation.

### 15. Canary Deployment

**❌ Weak:** "Did model rollouts."  
**✅ Strong:** "Configured ArgoCD canary deployments with automated rollback on prediction quality degradation, routing 10% traffic to new model versions and validating accuracy against baseline before promotion."  
**💡 Why:** Shows deployment strategy, automated quality gates, and risk management.

### 16. GPU Optimization

**❌ Weak:** "Used GPU for model serving."  
**✅ Strong:** "Optimized GPU utilization on K8s inference pods using NVIDIA MPS (Multi-Process Service) and dynamic batching, improving throughput by 2.5x while reducing per-request GPU cost by 35%."  
**💡 Why:** Shows GPU-aware optimization, specific techniques, and cost impact.

### 17. Cost Optimization

**❌ Weak:** "Reduced project costs."  
**✅ Strong:** "Implemented K8s spot instance scheduling and pod right-sizing for inference workloads, reducing monthly compute costs by 28% while maintaining SLA-compliant p99 latency."  
**💡 Why:** Shows specific techniques, realistic savings, and SLA awareness.

### 18. Streaming Features

**❌ Weak:** "Processed streaming data."  
**✅ Strong:** "Integrated Apache Kafka consumers for real-time feature ingestion, processing 50K+ events/second with exactly-once delivery semantics and feeding features to Redis for sub-5ms online serving."  
**💡 Why:** Shows streaming architecture, delivery guarantees, and latency.

### 19. Testing & Validation

**❌ Weak:** "Wrote tests for the project."  
**✅ Strong:** "Implemented comprehensive test suites with pytest covering data validation, model inference correctness, and API contract testing, achieving 85%+ code coverage enforced via CI checks."  
**💡 Why:** Shows testing strategy, coverage metrics, and CI enforcement.

### 20. Model Optimization (ONNX/Quantization)

**❌ Weak:** "Optimized model inference."  
**✅ Strong:** "Reduced PyTorch model inference latency by 45% via ONNX Runtime conversion and INT8 quantization, shrinking artifact size from 1.2GB to 310MB while maintaining accuracy within 0.3% of baseline."  
**💡 Why:** Shows specific optimization techniques, before→after numbers, and accuracy tradeoff awareness.

---

## 9. 15 Reusable Project Bullet Templates

Fill in the blanks with your specific details:

### Architecture Bullets

1. **Architected** a [system type] using [3-4 tools], automating [what process] for [N]+ production [components] with [metric].

2. **Engineered** an end-to-end [pipeline type] pipeline using [orchestrator] and [registry], automating [lifecycle stages] from data validation to model deployment.

3. **Designed** a [architecture type] architecture using [tools], supporting [throughput/scale] with [reliability metric].

### Deployment Bullets

4. **Deployed** production [service type] services on [cloud/K8s] using [deployment tool], configuring [scaling strategy] and [health pattern] for [availability metric].

5. **Containerized** the [pipeline/service] using multi-stage Docker builds, reducing image sizes by [X]% and accelerating [build/deploy] by [Y minutes].

6. **Configured** [deployment strategy] deployments with [tool], routing [X]% traffic to new versions and validating [metric] before full promotion.

### Monitoring Bullets

7. **Implemented** [monitoring type] monitoring using [tools], tracking [specific metrics] to lower [MTTD/MTTR] by [X]%.

8. **Integrated** [drift detection tool] for automated [drift type] monitoring, configuring [alerting tool] and [retraining trigger] when [threshold condition].

### Data & Feature Bullets

9. **Engineered** a [feature serving type] pipeline using [feature store] and [cache], achieving sub-[X]ms feature retrieval and eliminating [consistency problem].

10. **Integrated** [versioning tool] with [storage], establishing [reproducibility guarantee] across [N]+ [experiments/datasets].

### Optimization Bullets

11. **Optimized** [resource type] costs by implementing [technique], reducing monthly [cloud] spend by [X]% without impacting [SLA metric].

12. **Reduced** inference latency by [X]% via [optimization technique], shrinking model artifacts from [A] to [B] while maintaining accuracy within [tolerance].

### CI/CD Bullets

13. **Engineered** [CI/CD tool] workflows automating [stages list], enforcing [quality gate] before triggering [deployment target] deployments.

14. **Automated** [pipeline type] triggered by [event source], automatically [action sequence] and reducing [response time] from [before] to [after].

### LLMOps Bullets

15. **Built** a production [LLM system type] using [LLM serving tool] and [vector DB], serving sub-[X]ms [query type] with [safety/monitoring mechanism].

---

## 10. 8 Complete MLOps Project Examples

Each project includes: architecture, tech stack, 3 resume bullets, README requirements, and ATS keywords covered.

---

### Project 1: End-to-End GitOps ML Deployment Platform

```
Architecture: GitHub Push → Actions CI → ECR → ArgoCD → EKS → MLflow → Prometheus
```

**Tech Stack:** Python, Docker, Kubernetes (EKS), ArgoCD, MLflow, GitHub Actions, Helm, Terraform, Prometheus, Grafana

**Resume Bullets:**
1. Architected a GitOps ML deployment platform on AWS EKS using ArgoCD and Helm, automating zero-downtime rolling deployments upon main branch merge commits.
2. Configured GitHub Actions CI to execute automated model benchmark evaluation, container security scanning (Trivy), and Docker image tagging prior to ArgoCD-triggered production rollouts.
3. Implemented Prometheus + Grafana monitoring for deployed model endpoints, tracking prediction latency, throughput, and error rates with automated PagerDuty alerts.

**ATS Keywords Covered:** Kubernetes, EKS, Docker, ArgoCD, GitOps, Helm, MLflow, CI/CD, GitHub Actions, Terraform, Prometheus, Grafana, Triton (optional), Zero-downtime, Canary Deployment

---

### Project 2: Real-time Feature Store & Low-Latency Serving

```
Architecture: Events → Kafka → Feast → Redis (Online) / Postgres (Offline) → FastAPI → Prometheus
```

**Tech Stack:** Python, Feast, Redis, PostgreSQL, FastAPI, Docker Compose, Kafka, Prometheus

**Resume Bullets:**
1. Engineered a real-time feature retrieval pipeline with Feast and Redis, achieving sub-10ms online feature lookup and eliminating training-serving skew across 8 production model features.
2. Developed async FastAPI serving endpoints integrated with Feast online store, supporting 1,000+ real-time requests/second with automatic OpenAPI documentation.
3. Integrated Kafka consumers for streaming feature ingestion, processing 50K+ events/second with exactly-once delivery semantics.

**ATS Keywords Covered:** Feature Store, Feast, Redis, FastAPI, Kafka, Real-time, Low-latency, Training-serving skew, PostgreSQL, Docker, Prometheus

---

### Project 3: Production LLMOps RAG Pipeline

```
Architecture: Documents → Chunking → Embeddings → Qdrant → vLLM → Langfuse → Prometheus
```

**Tech Stack:** Python, vLLM, Qdrant, LangChain, FastAPI, Docker, Kubernetes, Prometheus, Grafana, Langfuse

**Resume Bullets:**
1. Built a production RAG deployment pipeline using vLLM and Qdrant vector database, serving sub-400ms retrieval-augmented responses with automated hallucination guardrail alerts.
2. Integrated Langfuse observability for LLM trace monitoring, tracking per-request token cost, retrieval precision, and response quality scores across production RAG traffic.
3. Deployed the RAG pipeline on K8s GPU nodes with continuous batching, achieving 3x throughput improvement over baseline HuggingFace Transformers pipeline.

**ATS Keywords Covered:** LLMOps, RAG, vLLM, Vector Database, Qdrant, LangChain, FastAPI, Kubernetes, Langfuse, Guardrails, GPU, Continuous Batching

---

### Project 4: Automated ML Drift Monitoring & Retraining System

```
Architecture: Inference Logs → S3 → Airflow DAG → Evidently AI → Retraining → MLflow → Slack
```

**Tech Stack:** Python, Airflow, Evidently AI, MLflow, AWS S3, Docker, PostgreSQL, Slack API

**Resume Bullets:**
1. Implemented automated data drift detection using PSI (Population Stability Index) via Evidently AI, configuring Slack alerts and Airflow retraining triggers when feature distributions exceeded 15% threshold.
2. Configured end-to-end retraining workflows with automated model versioning in MLflow, reducing model staleness response time from 2 weeks to 6 hours.
3. Developed Airflow DAGs with S3 data-arrival sensors for event-driven monitoring, configuring automatic retries and SLA violation notifications.

**ATS Keywords Covered:** Data Drift, Concept Drift, Evidently AI, Airflow, MLflow, Model Registry, Automated Retraining, S3, PSI, Monitoring, Docker

---

### Project 5: Distributed Batch Inference Pipeline

```
Architecture: Data Lake (S3) → Spark → PyTorch Model → Output Store → Airflow → Prometheus
```

**Tech Stack:** Python, PySpark, PyTorch, Docker, AWS S3, Airflow, Prometheus

**Resume Bullets:**
1. Engineered a distributed batch inference pipeline using PySpark and PyTorch, processing 500K+ records/hour across 8 worker nodes with automated checkpointing and retry logic.
2. Configured Airflow scheduling with S3 data-arrival sensors, automating daily batch scoring and alerting on prediction distribution anomalies via Prometheus.

**ATS Keywords Covered:** Batch Inference, PySpark, Distributed Processing, PyTorch, Airflow, S3, Docker, Prometheus

---

### Project 6: Multi-Model Serving on Triton Inference Server

```
Architecture: Models → ONNX/TensorRT → Triton Server → K8s → Load Balancer → Prometheus
```

**Tech Stack:** Python, PyTorch, ONNX Runtime, Triton Inference Server, Kubernetes, Helm, Prometheus

**Resume Bullets:**
1. Deployed multi-model serving infrastructure on Triton Inference Server with dynamic batching and model ensemble support, increasing GPU throughput by 2.5x across 5 concurrent model endpoints.
2. Optimized model artifacts using ONNX Runtime conversion and INT8 quantization, reducing inference latency by 45% and artifact sizes by 4x while maintaining accuracy within 0.3% baseline.

**ATS Keywords Covered:** Triton Inference Server, ONNX, Model Optimization, INT8 Quantization, Dynamic Batching, GPU, Kubernetes, Multi-model Serving

---

### Project 7: ML Infrastructure as Code with Terraform

```
Architecture: Terraform → AWS (EKS, S3, ECR, IAM) → GitOps PR Review → Apply → State Lock
```

**Tech Stack:** Python, Terraform, AWS (EKS, S3, ECR, IAM, VPC), Helm, GitHub Actions

**Resume Bullets:**
1. Provisioned reproducible ML infrastructure on AWS (EKS clusters, S3 buckets, ECR registries, IAM roles) using Terraform modules with remote state locking, enabling one-command environment setup.
2. Designed GitOps-based Terraform workflow with PR review enforcement and automated `plan` output, standardizing infrastructure changes across Dev/Staging/Prod environments.

**ATS Keywords Covered:** Terraform, Infrastructure as Code, AWS, EKS, S3, ECR, IAM, Helm, GitOps, Multi-environment, GitHub Actions

---

### Project 8: Comprehensive ML Observability Stack

```
Architecture: Inference Endpoints → Prometheus Exporters → Grafana → Alert Manager → PagerDuty
```

**Tech Stack:** Python, Prometheus, Grafana, OpenTelemetry, ELK Stack, PagerDuty, Docker Compose

**Resume Bullets:**
1. Established a comprehensive ML observability stack using Prometheus, Grafana, and OpenTelemetry, tracking prediction drift, SLO compliance, and infrastructure health across 10+ model endpoints.
2. Configured Grafana Alert Manager with PagerDuty integration and escalation policies, achieving sub-5-minute response time for critical model degradation events.

**ATS Keywords Covered:** Prometheus, Grafana, OpenTelemetry, Observability, SLO, SLI, Monitoring, Alerting, ELK Stack, PagerDuty, Drift Detection

---

## 11. Realistic Metrics for Projects

### Credible Ranges (2 YOE Personal/Side Projects)

| Metric | ✅ Realistic | ❌ Red Flag |
|:---|:---|:---|
| **API requests** | 100–10K req/sec | "millions per second" |
| **Data processed** | 10K–500K records/batch | "petabytes processed" |
| **Latency** | 10ms–200ms response | "sub-1ms" (unrealistic without hardware-specific optimization) |
| **Docker image size** | 200MB–500MB (optimized) | "5MB image with ML model" |
| **Models served** | 1–5 concurrent | "50+ concurrent models" on personal project |
| **Cost savings** | Relative % reduction | "$5M saved" on personal project |
| **Feature retrieval** | Sub-10ms with Redis | "Sub-1ms" (limited by network, not code) |

### Use Honest Language

> "Use honest metrics from your own testing. Avoid fake production numbers."  
> — Google Cloud MLOps Best Practices

* ✅ "Achieved sub-35ms p95 latency in local benchmarks with 100 concurrent connections"
* ❌ "Served 1 billion requests/day with zero downtime" (for a personal project)

---

## 12. README Structure for Each Project

Every project repo MUST have a comprehensive README with these sections:

```markdown
# Project Name

One-line description of what the project does and why.

## Architecture

[Mermaid/ASCII architecture diagram showing full pipeline flow]

## Tech Stack

| Component | Tool |
|-----------|------|
| ML Training | PyTorch |
| Serving | FastAPI |
| Container | Docker (multi-stage) |
| Orchestration | Kubernetes (EKS) |
| CI/CD | GitHub Actions + ArgoCD |
| Monitoring | Prometheus + Grafana |
| Model Registry | MLflow |
| Data Versioning | DVC |

## Getting Started

Three-command setup:
```bash
Git clone https://GitHub.com/username/project.Git
Docker-compose up -d
curl http://localhost:8000/predict -X POST -d '{"data": [1,2,3]}'
```

## API Documentation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/predict` | POST | Run model inference |
| `/health` | GET | Health check |
| `/metrics` | GET | Prometheus metrics |

## CI/CD Pipeline

Description of automated stages (lint → test → build → deploy).

## Monitoring

Screenshot or description of Grafana dashboards and alerting setup.

## Performance Benchmarks

| Metric | Value |
|--------|-------|
| p95 Latency | 35ms |
| Throughput | 800 req/sec |
| Docker Image Size | 380MB |

## License

MIT
```

---

## 13. GitHub Repo Structure

```
project/
├── .GitHub/
│   └── workflows/
│       ├── ci.yml                # Lint + test + build
│       └── cd.yml                # Deploy to K8s/cloud
├── src/
│   ├── train/                    # Training pipeline
│   │   ├── train.py
│   │   └── config.yaml
│   ├── serve/                    # Inference API
│   │   ├── app.py                # FastAPI application
│   │   └── schemas.py            # Pydantic models
│   └── monitor/                  # Drift detection
│       └── drift_detector.py
├── infra/
│   ├── Terraform/                # IaC provisioning
│   │   ├── main.tf
│   │   └── variables.tf
│   ├── k8s/                      # K8s manifests
│   │   ├── deployment.yaml
│   │   └── service.yaml
│   └── helm/                     # Helm charts (optional)
│       └── Chart.yaml
├── tests/
│   ├── test_train.py
│   ├── test_serve.py
│   └── conftest.py
├── Dockerfile                    # Multi-stage build
├── Docker-compose.yml            # Local development
├── Makefile                      # Common commands
├── pyproject.toml                # Dependencies
├── dvc.yaml                      # Data versioning
├── .dockerignore
├── .gitignore
└── README.md                     # Comprehensive docs
```

---

## 14. ATS Keywords for Projects

Embed these keywords naturally in project bullets and tech stack listings:

| Category | Must-Have | Differentiator |
|:---|:---|:---|
| **Lifecycle** | End-to-End, Pipeline, Automated | GitOps, Continuous Training, Event-driven |
| **Containers** | Docker, Multi-stage Build, Kubernetes | Helm, ArgoCD, HPA, Pod Autoscaling |
| **CI/CD** | GitHub Actions, CI/CD, Automated Testing | Trivy, Canary Deployment, Quality Gates |
| **MLOps** | MLflow, Model Registry, Airflow | Kubeflow, DVC, Feast, Feature Store |
| **Serving** | FastAPI, REST API, Model Deployment | Triton, vLLM, gRPC, ONNX, KServe |
| **Monitoring** | Prometheus, Grafana, Monitoring | Evidently AI, Data Drift, OpenTelemetry, Langfuse |
| **Cloud** | AWS, S3, Docker | Terraform, EKS, GKE, SageMaker, Vertex AI |
| **LLMOps** | (Emerging) | RAG, Vector Database, Qdrant, vLLM, Guardrails |

---

## 15. Mistakes to Avoid

| Mistake | Why It Fails | Fix |
|:---|:---|:---|
| **Jupyter-only projects** | No infrastructure = not MLOps | Add Docker, CI/CD, K8s, monitoring |
| **Toy datasets (Titanic/MNIST)** | Signals student, not engineer | Use realistic datasets or synthetic production-grade data |
| **No GitHub link** | Unverifiable claim | Every project MUST have a public GitHub repo |
| **No README** | Recruiters skip repos without README | Comprehensive README with architecture diagram |
| **No CI/CD in repo** | Missing `.GitHub/workflows/` = not production-ready | Add GitHub Actions CI pipeline |
| **Too many projects (5+)** | Dilutes page space on 1-page resume | Select 2–3 deep, high-scoring projects |
| **Fake production metrics** | "Serving 1B requests" on personal project = credibility red flag | Use honest benchmarks from local testing |
| **Copy-pasted project** | Identical to course tutorial | Extend with your own infra, monitoring, deployment |
| **Missing tech stack line** | ATS can't extract keywords from prose | Explicit `Tech Stack:` line with comma-separated tools |
| **Same skills as work experience** | Projects should fill gaps, not duplicate | Diversify: if work = CI/CD, project = monitoring/RAG |

---

## Changelog

### Update: June 29, 2026

**Research Areas Used:**
- 50+ MLOps/ML Platform JDs from FAANG, unicorns, AI companies
- Google Cloud MLOps Whitepaper, AWS Well-Architected ML Lens
- GitHub best practices (GitHub.blog)
- MLOps Community project portfolio survey 2026
- HuggingFace, DockerHub, and FastAPI documentation

**Key Improvements:**
- Removed embedded AGENTS.md copy — now references AGENTS.md file
- Added Table of Contents for navigation
- Expanded from 5 to 8 complete project examples
- Added 3 new project examples: LLMOps/RAG, Triton Multi-Model, ML IaC, Observability Stack
- Added 20 weak→strong transformations (up from 10)
- Added 15 reusable fill-in-the-blank bullet templates
- Added project selection decision framework ("if your work experience emphasizes X, projects should show Y")
- Added project scoring rubric with weights
- Added realistic metrics table for personal projects
- Added full GitHub repo structure template
- Added comprehensive README template
- Added ATS keyword table for projects
- Updated recruiter signal table with JD frequency percentages

**Sections Added:**
- Table of Contents
- Project Selection Criteria (§3) with scoring rubric
- How Many Projects & Which Ones (§4) with decision framework
- How to Show Production Readiness (§6) with before/after comparison
- How to Include GitHub Links & Architecture (§7)
- Realistic Metrics for Projects (§11)
- GitHub Repo Structure (§13)
- ATS Keywords for Projects (§14)
- LLMOps/RAG project example
- Triton multi-model serving project
- ML IaC project
- Observability stack project

**Sections Rewritten:**
- What Recruiters Look For (§5) — now with JD frequency percentages
- Mistakes to Avoid (§15) — expanded from 5 to 10 mistakes with fixes
- All original transformations enhanced with "💡 Why" explanations
