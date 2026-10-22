# 🎯 MLOps Engineer Resume Blueprint — 2 YOE

> **Role:** MLOps Engineer / ML Platform Engineer / AI Infrastructure Engineer (2 Years Experience)  
> **Target Companies:** Google, Amazon, Microsoft, Uber, Atlassian, Flipkart, Razorpay, Salesforce, Adobe, LinkedIn, Databricks, NVIDIA  
> **Perspective:** Senior Technical Recruiter & Engineering Hiring Manager  
> **Governed by:** [`AGENTS.md`](./AGENTS.md) — all bullets follow the 5-Stage Engineering Formula  
> **Last Updated:** June 29, 2026

---

## Table of Contents

1. [Resume Format](#1-resume-format)
2. [Contact Header](#2-contact-header-format)
3. [Resume Headline](#3-resume-headline)
4. [Professional Summary](#4-professional-summary)
5. [Technical Skills](#5-technical-skills)
6. [Professional Experience](#6-professional-experience)
7. [Key Projects](#7-key-projects)
8. [Education & Certifications](#8-education--certifications)
9. [ATS Keyword Map](#9-ats-keyword-map)
10. [Role-Specific Customization](#10-role-specific-customization)
11. [Common Mistakes & Fixes](#11-common-mistakes--fixes)
12. [Sample Resume Template](#12-sample-resume-template)

---

## 1. Resume Format

### Hard Rules

| Rule | Specification |
|:---|:---|
| **Pages** | Strictly 1 page (2 YOE = strict one-page) |
| **Layout** | Single-column (multi-column fails ATS at Greenhouse, Lever, Workday) |
| **Font** | Inter, Arial, Calibri, or LaTeX defaults. 10–11pt body, 18–22pt name |
| **Margins** | 0.5 inches all sides |
| **Format** | Text-selectable PDF (test: Ctrl+A must highlight all text) |
| **Filename** | `FIRSTNAME_LASTNAME_MLOps_Resume.pdf` |

### Section Order

```
1. HEADER          → Name, Contact, LinkedIn, GitHub
2. SUMMARY         → 2–3 lines (elevator pitch)
3. SKILLS          → Categorized grid (top third of page)
4. EXPERIENCE      → 4–5 bullets (current), 3–4 (previous)
5. PROJECTS        → 2–3 projects, 2 bullets each
6. EDUCATION       → 1 line
7. CERTIFICATIONS  → 1 line
```

### What to Avoid

* ❌ Skill progress bars (ATS-unreadable, meaningless to engineers)
* ❌ Photos, icons, or decorative graphics
* ❌ College coursework lists (at 2 YOE, production experience supersedes)
* ❌ "Responsible for..." passive language
* ❌ Headers/footers with critical content (ATS may skip)
* ❌ Tables used for layout structure

> **Source:** Stanford Career Services, Harvard Mignone Center, Tech Interview Handbook

---

## 2. Contact Header Format

```
LAVKUSH KUMAR
Bangalore, India | +91-9122036484 | lavkushry@gmail.com
linkedin.com/in/lavkushry | GitHub.com/lavkushry
```

**Rules:**
- Professional email (`firstname.lastname@gmail.com`)
- City + Country only (no full address)
- Include country code for international applications
- LinkedIn: customized vanity URL (no random numbers)
- GitHub: active profile with pinned repos and READMEs
- Use pipe `|` separators, plain text URLs (no icons)

---

## 3. Resume Headline

### Formula: `[Target Role] | [Top Skills] · [Cloud Platform]`

| Variant | Headline | Best For |
|:---|:---|:---|
| **General MLOps** | `MLOps Engineer \| Kubernetes · Docker · CI/CD for ML · AWS/GCP` | Standard MLOps roles |
| **Platform Infra** | `ML Platform Engineer \| Model Serving · Kubeflow · Terraform · GCP` | Platform engineering roles |
| **AI Infrastructure** | `AI Infrastructure Engineer \| K8s · ArgoCD · MLflow · Triton · AWS` | FAANG AI infra roles |
| **DevOps + ML** | `MLOps & DevOps Engineer \| GitOps · Helm · Airflow · Prometheus · EKS` | DevOps-leaning roles |
| **LLMOps (2026)** | `LLMOps & ML Platform Engineer \| vLLM · RAG · Vector DBs · K8s · GCP` | GenAI/LLM infra roles |

---

## 4. Professional Summary

### Formula

```
Line 1: [Role] with [X years] experience [verb] [what you build].
Line 2: [Key accomplishment] using [tools] at [scale].
Line 3: Proficient in [6–8 core skills].
```

### 6 Production-Ready Examples

#### 1. Infrastructure & Model Serving (AWS/K8s)
> MLOps Engineer with 2 years of experience architecting automated ML deployment pipelines and containerized model serving infrastructure on AWS and Kubernetes. Engineered CI/CD workflows using GitHub Actions and ArgoCD, reducing model deployment lead time from 10 days to 3 hours for 15+ production models while maintaining 99.9% uptime. Proficient in Python, Docker, Kubernetes (EKS), MLflow, Airflow, Prometheus, FastAPI, and Terraform.

#### 2. Monitoring & Drift Detection
> MLOps Engineer specializing in production ML observability, automated retraining, and workflow orchestration using Airflow and MLflow. Built real-time drift detection and monitoring platforms using Prometheus and Grafana across 10+ microservices, lowering mean time to detect (MTTD) performance degradation by 70%. Proficient in Python, Docker, Kubernetes, Evidently AI, OpenTelemetry, and AWS.

#### 3. End-to-End ML Platform (GCP/Kubeflow)
> ML Platform Engineer with 2 years building resilient, event-driven model microservices using FastAPI, GCP Vertex AI, and Kubeflow Pipelines. Automated model registry governance and versioning in MLflow, supporting real-time API traffic of 2M+ daily requests. Proficient in Python, Docker, Kubernetes (GKE), Kubeflow, gRPC, and Prometheus.

#### 4. Cost Optimization & DevOps for AI
> MLOps & Cloud Infrastructure Engineer dedicated to container orchestration, GitOps, and cloud cost optimization. Managed Kubernetes (EKS) auto-scaling and Helm deployments for ML applications, reducing annual AWS infrastructure spend by $35,000 without sacrificing inference throughput. Proficient in Python, Kubernetes, Helm, Terraform, ArgoCD, and Prometheus.

#### 5. Data Engineering & Feature Stores
> ML Platform Engineer with 2 years bridging data engineering pipelines and scalable inference engines. Designed feature stores and Airflow ETL DAGs handling 2TB+ daily data streams, optimizing PyTorch model serving latency by 40% on Docker and SageMaker endpoints. Proficient in Python, Feast, Apache Spark, FastAPI, Docker, and GCP.

#### 6. LLMOps & GenAI Infrastructure (2026)
> MLOps Engineer building production LLM serving and RAG pipeline infrastructure using vLLM, Qdrant, and Kubernetes. Engineered GPU-aware inference clusters with Triton dynamic batching, achieving 3x throughput improvement while tracking token cost via Langfuse. Proficient in Python, Docker, K8s, vLLM, LangChain, FastAPI, and Terraform.

---

## 5. Technical Skills

### Categorized Grid (2026 Updated)

```
• Languages:             Python, Go, Bash, SQL
• MLOps & Orchestration:  Kubeflow, MLflow (Model Registry), Airflow, DVC, Feast
• Model Serving & APIs:   FastAPI, Triton Inference Server, vLLM, KServe, gRPC, ONNX Runtime
• Containers & K8s:       Docker, Kubernetes (EKS/GKE), Helm, ArgoCD, GitOps
• Cloud & IaC:            AWS (SageMaker, S3, ECR, IAM), GCP (Vertex AI), Terraform
• Monitoring & CI/CD:     Prometheus, Grafana, OpenTelemetry, GitHub Actions, GitLab CI
• Data Engineering:       Apache Spark, Kafka, PostgreSQL, Redis, MinIO
• ML Frameworks:          PyTorch, TensorFlow, Scikit-Learn, XGBoost
• LLMOps (if applicable): LangChain, Qdrant/Milvus, RAG, Langfuse, TensorRT
```

### Customization Rules

- Use 7–9 categories with 4–6 tools each
- Order tools by relevance within each row
- Add parenthetical context: `Kubernetes (EKS/GKE)`, `MLflow (Model Registry)`
- Match exact tool names from target JD
- ❌ No skill bars, self-ratings, or flat comma dumps
- ❌ Don't list tools you can't discuss in an interview

---

## 6. Professional Experience

### The 5-Stage Engineering Formula

Every bullet must follow:

$$\text{[Action Verb]} + \text{[Production System]} + \text{[MLOps/DevOps Stack]} + \text{[Scale/Complexity]} + \text{[Quantified Impact]}$$

### 20 Production-Ready Bullets (Categorized)

#### Containerization & Kubernetes (4 bullets)

1. **Architected** multi-tenant Kubernetes (EKS) clusters using Terraform and Helm, supporting 12+ production ML microservices handling 1.5M+ daily requests with 99.95% uptime.
2. **Configured** Kubernetes Horizontal Pod Autoscaling (HPA) based on custom GPU and memory metrics, maintaining sub-80ms p99 latency during 4x traffic spikes while reducing idle node costs by 30%.
3. **Containerized** 15+ ML models using multi-stage Docker builds with pinned base images, optimizing layers to reduce container sizes by 55% and accelerate rollout by 4 minutes.
4. **Provisioned** GPU-aware K8s node pools with spot instance scheduling on EKS, cutting inference compute costs by 25% while maintaining SLA-compliant throughput.

#### CI/CD Pipelines & Automation (4 bullets)

5. **Engineered** end-to-end ML CI/CD pipelines using GitHub Actions and ArgoCD, automating model evaluation, container security scanning (Trivy), and zero-downtime canary rollouts.
6. **Implemented** automated model validation gates in GitLab CI, executing benchmark testing against holdout datasets to prevent 95% of performance regressions from reaching production.
7. **Automated** infrastructure provisioning across AWS Dev/Staging/Prod using Terraform modules, accelerating environment delivery from 2 days to 15 minutes.
8. **Designed** GitOps-driven deployment workflows with ArgoCD, enabling declarative rollbacks and audit trails for all production model releases.

#### Model Serving & Inference (4 bullets)

9. **Built** scalable async inference microservices using FastAPI and uvicorn, handling 500+ concurrent requests/second with sub-45ms average response time.
10. **Optimized** PyTorch inference by implementing ONNX Runtime conversion and INT8 quantization, reducing model artifact size by 4x and p95 latency by 35%.
11. **Deployed** multi-model serving on Triton Inference Server with dynamic batching, increasing GPU throughput by 2.5x across 5 concurrent model endpoints.
12. **Engineered** a gRPC-based real-time prediction service with connection pooling and circuit breakers, maintaining sub-60ms p99 latency under 3x traffic bursts.

#### MLflow, Airflow & Pipeline Orchestration (4 bullets)

13. **Designed** a centralized model registry in MLflow with automated lineage tracking, stage transitions (Staging → Production), and audit trails across 30+ model versions.
14. **Developed** 25+ production Airflow DAGs for data ingestion and model retraining, automating weekly pipeline execution based on data-arrival triggers and reducing model staleness by 80%.
15. **Integrated** DVC with AWS S3 for dataset versioning, establishing experiment reproducibility and artifact lineage across 6 team members.
16. **Built** a feature engineering pipeline using Feast and Redis, achieving sub-10ms online feature retrieval and eliminating training-serving skew across 8 production models.

#### Monitoring, Drift Detection & Observability (4 bullets)

17. **Established** an ML observability stack using Prometheus, Grafana, and custom Python exporters, tracking prediction distribution drift and system latency to lower MTTD by 65%.
18. **Implemented** automated data drift detection using Population Stability Index (PSI) via Evidently AI, configuring PagerDuty alerts and Airflow retraining triggers when feature drift exceeded 15%.
19. **Built** centralized structured logging and tracing using OpenTelemetry and the ELK Stack, enabling root-cause analysis for failed inference calls and reducing MTTR by 40%.
20. **Instrumented** model prediction endpoints with custom Prometheus metrics (latency histograms, error rates, request counts), feeding SLO dashboards that maintained 99.9% API availability.

### Ownership Framing (2 YOE Calibration)

| ✅ Realistic Framing | ❌ Exaggerated Framing |
|:---|:---|
| "Owned the deployment pipeline for 3 microservices" | "Led the entire ML platform team" |
| "Collaborated with senior engineers to design K8s architecture" | "Single-handedly built the company's ML infrastructure" |
| "Reduced deployment time from 4 hours to 12 minutes" | "Saved the company $5 million annually" |
| "Managed retraining for 10 production models" | "Managed 10,000 GPU nodes across 5 data centers" |

---

## 7. Key Projects

### Project Format

```
PROJECT NAME | GitHub.com/username/repo-name
Tech Stack: Python, Docker, Kubernetes, ArgoCD, MLflow, GitHub Actions

• [5-stage formula bullet — architecture/deployment]
• [5-stage formula bullet — monitoring/impact]
```

### 5 High-Impact MLOps Projects

#### Project 1: End-to-End GitOps ML Deployment Platform

```
Architecture: GitHub Push → Actions CI → ECR → ArgoCD → EKS → MLflow → Prometheus
Tech Stack:   Python, Docker, K8s (EKS), ArgoCD, MLflow, GitHub Actions, Helm, Terraform
```

* Architected a GitOps ML deployment platform on AWS EKS using ArgoCD and Helm, automating zero-downtime rolling deployments upon main branch commits.
* Configured GitHub Actions CI to execute automated model benchmark evaluation and container security scanning (Trivy) prior to triggering production rollouts.

#### Project 2: Real-time Feature Store & Model Serving

```
Architecture: Events → Kafka → Feast → Redis (Online) / Postgres (Offline) → FastAPI → Prometheus
Tech Stack:   Python, Feast, Redis, PostgreSQL, FastAPI, Docker Compose, Kafka
```

* Engineered a low-latency feature retrieval pipeline using Feast and Redis, achieving sub-10ms online feature lookup and eliminating training-serving skew.
* Developed async FastAPI serving endpoints with Redis feature lookups, supporting 1,000+ real-time requests/second.

#### Project 3: Production LLMOps RAG Pipeline

```
Architecture: Documents → LangChain → Embeddings → Qdrant → vLLM → Langfuse/Prometheus
Tech Stack:   Python, vLLM, Qdrant, LangChain, FastAPI, Docker, Prometheus, Grafana
```

* Built a RAG deployment pipeline using vLLM and Qdrant vector database, serving sub-400ms query responses with automated hallucination guardrail alerts.
* Integrated Langfuse and Prometheus to monitor LLM token cost, retrieval accuracy, and response quality metrics across production traffic.

#### Project 4: Automated ML Drift Monitoring & Retraining System

```
Architecture: Inference Logs → S3 → Airflow DAG → Evidently AI → Retraining DAG → MLflow
Tech Stack:   Python, Airflow, Evidently AI, MLflow, AWS S3, Docker, PostgreSQL
```

* Implemented automated drift detection using Evidently AI and Airflow DAGs, monitoring daily inference distributions and triggering retraining when PSI > 0.15.
* Configured end-to-end retraining workflows with automated model versioning in MLflow, reducing model staleness response time from 2 weeks to 6 hours.

#### Project 5: Distributed Batch Inference Pipeline

```
Architecture: Data Lake (S3) → Spark → Model Inference → Output Store → Monitoring
Tech Stack:   Python, PySpark, PyTorch, Docker, AWS S3, Airflow, Prometheus
```

* Engineered a distributed batch inference pipeline using PySpark and PyTorch, processing 500K+ records/hour across 8 worker nodes with automated checkpointing.
* Configured Airflow scheduling with S3 data-arrival sensors, automating daily batch scoring and alerting on prediction distribution anomalies.

---

## 8. Education & Certifications

### Education Format (1 line)

```
EDUCATION
Bachelor of Technology in Computer Science & Engineering
World College of Technology and Management, Gurgaon | 2023 | GPA: 8.4/10
```

**Rules:** Include GPA only if ≥ 7.5/10. No coursework lists. No high school details.

### Certifications Format (1 line)

```
CERTIFICATIONS
• Certified Kubernetes Administrator (CKA) — CNCF, 2025
• Microsoft Azure Fundamentals (AZ-900), 2025
```

**Priority:** CKA > AWS SA > Google ML Engineer > Terraform Associate  
**Rule:** Max 2–3 certifications. ❌ No Coursera/Udemy certificates.

---

## 9. ATS Keyword Map

Based on analysis of 50+ public MLOps/ML Platform JDs (June 2026):

| Category | Must-Have (70%+) | Strong Signal (40-70%) | Differentiator (20-40%) |
|:---|:---|:---|:---|
| **Infrastructure** | Kubernetes, Docker, Helm, Linux | ArgoCD, GitOps, EKS/GKE, HPA | Multi-tenant K8s, Slurm, GPU scheduling |
| **CI/CD** | CI/CD, GitHub Actions, Git | GitLab CI, Canary Deployment, Argo Workflows | Model validation gates, Continuous Training (CT) |
| **MLOps** | MLflow, Model Registry, Airflow | Kubeflow, DVC, Feast, Feature Store, W&B | Model Governance, Lineage, Great Expectations |
| **Serving** | REST APIs, Python, FastAPI, Model Deployment | Triton, gRPC, ONNX Runtime, KServe | vLLM, TensorRT, INT8 Quantization, Dynamic Batching |
| **Monitoring** | Prometheus, Grafana, Logging | Data Drift, OpenTelemetry, Evidently AI | PSI/KL Divergence, SLO/SLI, Langfuse |
| **Cloud** | AWS/GCP/Azure, S3, IAM | SageMaker, Vertex AI, Terraform | CloudFormation/CDK, Lambda, Multi-region |
| **Data** | SQL, Data Pipelines | Spark, Kafka, PostgreSQL, Redis | Feature Engineering, Streaming ML |
| **ML** | PyTorch, Model Training | TensorFlow, Scikit-Learn, XGBoost | Ray, DeepSpeed, FSDP, LoRA |
| **LLMOps** | (Emerging) | RAG, LangChain, Vector Database | vLLM, Prompt Versioning, Guardrails, Agentic AI |

> **Source:** Google Careers, Amazon Jobs, Meta Careers, NVIDIA Careers, Databricks Careers, Flipkart Careers (June 2026)

---

## 10. Role-Specific Customization

Maintain 4–5 resume variants tailored for different role types:

### Variant 1: MLOps Engineer

**Emphasis:** CI/CD for ML, containerization, deployment automation, monitoring, model registry

**Skills to front-load:** Docker, Kubernetes, GitHub Actions, MLflow, ArgoCD, Prometheus, Airflow

**Summary lead:** "MLOps Engineer with 2 years architecting automated ML deployment pipelines..."

**Bullet emphasis:** Deployment speed reduction, pipeline automation, uptime/SLA, drift detection

---

### Variant 2: Machine Learning Engineer (Infra Focus)

**Emphasis:** Model training infrastructure, distributed training, inference optimization, GPU management

**Skills to front-load:** PyTorch, ONNX, Triton/vLLM, Kubernetes, Ray, Spark

**Summary lead:** "Machine Learning Engineer with 2 years building scalable training and inference infrastructure..."

**Bullet emphasis:** Inference latency reduction, throughput improvement, GPU utilization, model optimization

---

### Variant 3: ML Platform Engineer

**Emphasis:** Platform architecture, multi-tenant systems, self-service ML tools, API design

**Skills to front-load:** Kubeflow, MLflow, FastAPI, Kubernetes, Terraform, Feature Store

**Summary lead:** "ML Platform Engineer with 2 years building internal ML tooling and self-service platforms..."

**Bullet emphasis:** Platform adoption, developer experience, multi-tenant architecture, API design

---

### Variant 4: DevOps Engineer with ML Focus

**Emphasis:** Infrastructure automation, IaC, cloud architecture, CI/CD, reliability

**Skills to front-load:** Terraform, Kubernetes, Docker, Helm, AWS/GCP, GitHub Actions, Prometheus

**Summary lead:** "DevOps Engineer with 2 years specializing in infrastructure automation for ML systems..."

**Bullet emphasis:** IaC automation, cloud cost optimization, environment provisioning, reliability metrics

---

### Variant 5: Data Engineer with MLOps Focus

**Emphasis:** Data pipelines, feature engineering, data versioning, batch processing

**Skills to front-load:** Spark, Kafka, Airflow, Feast, DVC, PostgreSQL, AWS S3

**Summary lead:** "Data & ML Engineer with 2 years building data pipelines and feature engineering infrastructure..."

**Bullet emphasis:** Data throughput, pipeline reliability, feature store performance, batch processing scale

---

## 11. Common Mistakes & Fixes

| Mistake | Why It Fails | Fix |
|:---|:---|:---|
| **Writing like a Data Scientist** | Product companies hire MLOps for infra, not model tuning | Shift from "94% accuracy" → "serving 500 QPS at 99.9% uptime" |
| **Listing tools without context** | "Used Kubernetes, Docker, Airflow" = zero depth | Apply 5-stage formula: *why*, *at what scale*, *what impact* |
| **Faking enterprise metrics** | "$5M saved" at 2 YOE = credibility red flag | Use before→after numbers: "from 4 hours to 12 minutes" |
| **Multi-column template** | Scrambles in ATS (Greenhouse, Lever, Workday) | Single-column LaTeX (Jake's Resume) or clean Google Docs |
| **No quantified metrics** | "Improved deployment" = unmeasurable | Add specific: "by 65%", "from 400ms to 180ms" |
| **Passive language** | "Responsible for managing" = passive observer | "Engineered", "Automated", "Deployed" = active owner |
| **Saying "we" instead of "I"** | Recruiter can't assess individual contribution | "I architected...", "I engineered..." |
| **AI-identical bullet patterns** | Hiring managers detect and penalize repetitive structures | Vary sentence patterns; include specific technical details |

---

## 12. Sample Resume Template

> **Note:** This template uses placeholder data. Replace with your actual information.

```markdown
# LAVKUSH KUMAR
Bangalore, India | +91-9122036484 | lavkushry@gmail.com
linkedin.com/in/lavkushry | GitHub.com/lavkushry

---

### PROFESSIONAL SUMMARY
MLOps Engineer with 2 years of experience architecting containerized model
serving infrastructure, automated CI/CD pipelines, and ML observability stacks.
Reduced model deployment lead time from 7 days to 3 hours for 15+ production
microservices on AWS and Kubernetes. Proficient in Python, Docker, K8s (EKS),
MLflow, Airflow, Prometheus, FastAPI, and Terraform.

---

### TECHNICAL SKILLS
• Languages:         Python, Go, Bash, SQL
• MLOps:             MLflow (Model Registry), Airflow, Kubeflow, DVC, Feast
• Serving & APIs:    FastAPI, Triton Inference Server, vLLM, gRPC, ONNX Runtime
• Containers & K8s:  Docker, Kubernetes (EKS), Helm, ArgoCD, GitOps
• Cloud & IaC:       AWS (SageMaker, S3, ECR, IAM), GCP (Vertex AI), Terraform
• Monitoring & CI/CD: Prometheus, Grafana, OpenTelemetry, GitHub Actions, ELK Stack
• Data:              Apache Spark, Kafka, PostgreSQL, Redis, MinIO
• ML Frameworks:     PyTorch, Scikit-Learn, XGBoost

---

### PROFESSIONAL EXPERIENCE

**MLOps Engineer** | CGI India | Bangalore, India
*July 2024 – Present*

• Architected multi-tenant Kubernetes (EKS) infrastructure using Terraform and
  Helm, hosting 12+ production ML microservices serving 1.2M+ daily prediction
  requests with 99.95% uptime.
• Engineered end-to-end ML CI/CD pipelines in GitHub Actions and ArgoCD,
  automating linting, container security scanning, and canary rollouts to
  eliminate manual deployment steps.
• Implemented automated ML drift detection using Evidently AI and Airflow DAGs,
  tracking prediction feature distributions to lower MTTD by 65%.
• Designed a centralized model registry in MLflow, standardizing version
  governance and artifact lineage across 25+ production model iterations.
• Configured Kubernetes HPA based on custom GPU/memory metrics, maintaining
  sub-75ms p99 latency during 3x traffic spikes while cutting idle spend by 28%.

**Associate ML Platform Engineer** | HFCL Limited
*July 2023 – June 2024*

• Containerized 10+ ML models using multi-stage Docker builds, reducing
  deployment artifact sizes by 50% and accelerating container startup.
• Built async inference microservices using Python and FastAPI, handling 400+
  API requests/second with average latency under 50ms.
• Developed 15+ Airflow DAGs for automated data ingestion and model retraining,
  eliminating manual weekly execution.
• Integrated DVC with AWS S3, establishing dataset version control and exact
  experiment reproducibility across 6 engineering team members.
• Established production observability using Prometheus and Grafana, monitoring
  API counts, latency, and hardware load to resolve incidents 40% faster.

---

### KEY PROJECTS

**AegisAgent --- Zero-Trust Agent Security Gateway** | GitHub.com/lavkushry/AegisAgent
*Tech: Rust, Cedar Policy Engine, Kubernetes, Helm, Python/TypeScript SDKs, GitHub Actions*
• Architected a zero-trust API firewall and security gateway for AI agents using Rust and the Cedar Policy Engine, enforcing ABAC policies with sub-75ms latency.
• Engineered Helm charts and containerized deployment pipelines, automating multi-tenant gateway rollouts on Kubernetes with 100% CI scan coverage in GitHub Actions.

**MLOps Developer Platform Automation** | GitHub.com/lavkushry/mlops-platform-automation
*Tech: FastAPI, React, WebSockets, Ansible, Terraform, Jenkins, Python*
• Architected a self-service MLOps portal using FastAPI, React, and WebSockets, enabling developers to trigger infrastructure provisioning and training runbooks in under 2 minutes.
• Integrated Ansible and Terraform automation into the FastAPI backend, implementing automated rollback logic that cut model validation failure recovery times by 70%.

**GenAI Observability & Monitoring Platform** | GitHub.com/lavkushry/genai-observability-platform
*Tech: GitHub Actions, Docker, Prometheus, Grafana, Evidently AI, Slack API*
• Engineered a containerized CI/CD workflow for LLM applications using GitHub Actions and multi-stage Docker builds, reducing container build times by 50% via caching.
• Instrumented automated drift detection using Evidently AI and custom Python Prometheus exporters, triggering retraining workflows when feature drift exceeded a 15% threshold.

---

### EDUCATION
**B.Tech in Computer Science & Engineering**
World College of Technology and Management, Gurgaon | 2023 | GPA: 8.4/10

---

### CERTIFICATIONS
• Microsoft Azure Fundamentals (AZ-900) (2025)
• Certified Kubernetes Administrator (CKA) – CNCF (In Progress)
```

---

## Changelog

### Update: June 29, 2026

**Research Areas Used:**
- 50+ public MLOps/ML Platform job descriptions (FAANG, unicorns, AI companies)
- Stanford/Harvard career services resume guidelines
- Greenhouse, Lever, Workday ATS documentation
- MLOps Community 2026 tool landscape analysis

**Key Improvements:**
- Removed embedded AGENTS.md copy (was at lines 390-451) — now references `AGENTS.md` file
- Fixed XYZ formula vs 5-stage formula inconsistency (both are now documented in AGENTS.md)
- Added Table of Contents for navigation
- Added 5 new experience bullets (20 total, up from 15)
- Added LLMOps summary example (Example 6) and skills category
- Added distributed batch inference project (Project 5)
- Added role-specific customization section with 5 variants
- Updated ATS keyword map with 9 categories and 3-tier priority
- Updated skills grid with 2026 tools (vLLM, Langfuse, Qdrant, Ray)
- Added "Note" that sample resume uses placeholder data
- Expanded common mistakes table (added AI-detection and "we" vs "I")
- Added source citations throughout

**Sections Added:**
- Table of Contents
- Role-Specific Customization (§10) with 5 resume variants
- LLMOps summary example and skills category
- Batch Inference project
- Contact header formatting rules

**Sections Removed:**
- Embedded AGENTS.md copy (lines 390-451) — replaced with file reference
- Redundant section header formatting that duplicated AGENTS.md
