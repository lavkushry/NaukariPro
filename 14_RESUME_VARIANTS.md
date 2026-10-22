# 14_RESUME_VARIANTS.md — Targeted Role-Specific Resume Variations

> **Author:** Agent 12 — Job Matching & Resume Tailoring Agent  
> **Candidate:** Lavkush Kumar  
> **Core Policy:** Zero Factual Drift across all variants. Every date, title, employer, metric, and project link remains identical to [`01_FACT_MATRIX.md`](./01_FACT_MATRIX.md). Only headline, summary emphasis, skills prioritization, and project ordering are tailored.  

---

## Overview of Variants

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       TARGET RESUME VARIANT SPECTRUM                        │
│                                                                             │
│  [ Variant A: ML Platform Engineer ]      → IDPs, K8s, Terraform, Kafka    │
│  [ Variant B: MLOps Engineer ]            → CI/CD, Serving, MLflow, Docker  │
│  [ Variant C: AI Infrastructure Engineer ]→ Rust, Sandboxing, Cedar, pgvect │
│  [ Variant D: Platform / SRE for AI ]     → Reliability, RTO, MTTR, SRE    │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Variant A: ML Platform Engineer

### 1. Target Role & Persona
* **Target Roles:** ML Platform Engineer, Platform Engineer — AI/ML, Cloud ML Platform Specialist.
* **Target Companies:** Databricks, Uber, Atlassian, Razorpay, Flipkart, Salesforce.
* **Strategic Angle:** Emphasize Kubernetes orchestration, self-service infrastructure-as-code, and distributed data backbones that empower data science teams.

### 2. Tailored Headline
> **ML Platform Engineer | Kubernetes (kubeadm, EKS) · Terraform · Ansible · Apache Kafka · Redis · SRE**

### 3. Tailored Professional Summary
> **ML Platform Engineer** with **2.5+ years** of experience building and automating high-availability Kubernetes platforms, distributed data streaming infrastructure, and internal developer tooling. Expert in **Kubernetes (kubeadm, EKS), Terraform, Ansible, Docker, Helm, Apache Kafka, and Redis**. Demonstrated track record in automating bare-metal cluster lifecycles (slashing bootstrap by **83%**), operating stateful data backbones with **99.95% platform availability**, and developing distributed infrastructure control planes in **Python** and **Rust**.

### 4. Technical Skills Ordering
1. **Platform & Orchestration:** Kubernetes (`kubeadm`, AWS EKS), Docker, containerd, Helm, ArgoCD, Harbor Registry
2. **Infrastructure as Code:** Terraform (modules, remote state), Ansible (40+ playbooks/roles, Jinja2), Bash, YAML
3. **Data & Distributed Systems:** Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, pgvector (HNSW), MinIO S3
4. **CI/CD & DevSecOps:** Jenkins (declarative), GitLab CI, GitHub Actions, Trivy container scanning, SonarQube, RBAC
5. **Observability & SRE:** Prometheus, Grafana, Alertmanager, ELK Stack (Logstash Grok, Kibana), Velero DR
6. **Languages & Frameworks:** Python (FastAPI, AsyncIO, PyTest), Rust, SQL, Jinja2, RESTful APIs
7. **ML & AI Infrastructure:** MLflow (Model Registry, Lineage), Model Serving APIs, Vector Indexing, Cedar Policy

### 5. Project Ordering
1. **Project Vulcan — Enterprise Automation Control Plane** (FastAPI, pgvector, Redis Redlock, MinIO S3)
2. **AegisAgent — Zero-Trust AI Agent Security Gateway** (Rust, Cedar Engine, Kubernetes Helm)

---

## Variant B: MLOps Engineer

### 1. Target Role & Persona
* **Target Roles:** MLOps Engineer, DevOps Engineer — ML/AI, Machine Learning Operations Specialist.
* **Target Companies:** Amazon, Microsoft, Adobe, LinkedIn, 2K, Synthesia.
* **Strategic Angle:** Emphasize containerized deployment automation, CI/CD quality gates, model serving APIs, and centralized observability.

### 2. Tailored Headline
> **MLOps Engineer | CI/CD Automation · Kubernetes · Docker · Model Serving · Prometheus · Python · AWS**

### 3. Tailored Professional Summary
> **MLOps & DevOps Engineer** with **2.5+ years** of experience automating containerized application lifecycles, continuous delivery pipelines, and production observability stacks. Strong technical depth across **Kubernetes, Docker, Jenkins, GitLab CI, Prometheus, Grafana, ELK Stack, and FastAPI**. Proven history in cutting deployment lead times by **40%**, reducing incident resolution time (**MTTR**) by **45%**, and architecting secure API gateways and automation engines for AI systems.

### 4. Technical Skills Ordering
1. **ML & AI Infrastructure:** MLflow (Model Registry, Lineage), Model Serving APIs, Vector Indexing, Cedar Policy Engine
2. **CI/CD & Automation:** Jenkins (declarative), GitLab CI, GitHub Actions, Trivy container scanning, SonarQube, Helm
3. **Platform & Containers:** Kubernetes (kubeadm, AWS EKS), Docker, containerd, Helm, ArgoCD (GitOps)
4. **Observability & Monitoring:** Prometheus, Grafana, Alertmanager, ELK Stack (Elasticsearch, Logstash Grok, Kibana)
5. **Infrastructure as Code:** Terraform (modules, remote state), Ansible (40+ playbooks/roles, Jinja2), Bash
6. **Data & Streaming:** Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, pgvector (HNSW), MinIO S3
7. **Languages & Frameworks:** Python (FastAPI, AsyncIO, PyTest), Rust, SQL, RESTful APIs, WebSockets

### 5. Project Ordering
1. **AegisAgent — Zero-Trust AI Agent Security Gateway** (Rust, Cedar Engine, Kubernetes, Helm, CI/CD)
2. **Project Vulcan — Enterprise Automation Control Plane** (Python, FastAPI, Redis Redlock, pgvector)

---

## Variant C: AI Infrastructure Engineer

### 1. Target Role & Persona
* **Target Roles:** AI Infrastructure Engineer, Inference Infrastructure Engineer, Systems Engineer — AI/ML.
* **Target Companies:** NVIDIA, Microsoft, Google, AI Startups, OpenAI ecosystem partners.
* **Strategic Angle:** Emphasize systems-level engineering in Rust and Python, sandboxed agent runtimes, vector databases, and zero-trust security control planes.

### 2. Tailored Headline
> **AI Infrastructure Engineer | Rust · Kubernetes · Cedar Policy Engine · pgvector · Systems Security · Linux**

### 3. Tailored Professional Summary
> **AI Infrastructure & Systems Engineer** with **2.5+ years** of experience engineering secure runtime environments, high-throughput container platforms, and distributed systems. Expert in **Rust, Python (FastAPI), Kubernetes, Docker, Cedar Policy Engine, and pgvector**. Creator of **AegisAgent**, an open-source zero-trust security gateway and sandboxed execution runtime for autonomous AI agents and MCP tools, complemented by extensive production experience managing 50-node Kubernetes clusters and stateful data infrastructure.

### 4. Technical Skills Ordering
1. **Languages & Systems:** Rust (Tokio, Axum, Systems Programming), Python (FastAPI, AsyncIO), SQL, Bash, Linux
2. **ML & AI Infrastructure:** Cedar Policy Engine (ABAC), pgvector (HNSW Indexing), Model Context Protocol (MCP) Security, MLflow
3. **Platform & Sandboxing:** Kubernetes (kubeadm, EKS), Docker, containerd, Helm charts, ServiceMonitors, NetworkPolicies
4. **Data & Storage:** Redis (Redlock Concurrency), MinIO S3 (Decoupled Storage), PostgreSQL, Apache Kafka
5. **Infrastructure as Code:** Terraform, Ansible (40+ roles), GitOps (ArgoCD), Harbor Registry
6. **Observability & SRE:** Prometheus, Grafana, Alertmanager, ELK Stack (Logstash Grok), Velero DR
7. **CI/CD & DevSecOps:** GitHub Actions (SAST), GitLab CI, Jenkins, Trivy, SonarQube, RBAC

### 5. Project Ordering
1. **AegisAgent — Zero-Trust AI Agent Security Gateway** (Rust, Cedar Engine, Kubernetes, Helm, Docker)
2. **Project Vulcan — Enterprise Automation Control Plane** (Python, pgvector, Redis Redlock, MinIO S3)

---

## Variant D: Platform / SRE for AI

### 1. Target Role & Persona
* **Target Roles:** SRE — ML Platform, Reliability Engineer — AI Systems, Production Infrastructure Engineer.
* **Target Companies:** Google, Uber, Salesforce, Adobe, Razorpay, Tier-1 FinTech.
* **Strategic Angle:** Emphasize high-availability uptime (99.95%), disaster recovery (RTO slashed to 30m), telemetry parsing (ELK Grok), and MTTR reduction.

### 2. Tailored Headline
> **Platform & SRE Engineer — AI/ML | Kubernetes · Prometheus · Grafana · ELK Stack · Kafka · SRE · Velero**

### 3. Tailored Professional Summary
> **Platform & SRE Engineer** with **2.5+ years** of production experience operating mission-critical Kubernetes platforms, distributed data backbones, and full-stack observability systems. Proven expert in **Prometheus, Grafana, ELK Stack (Logstash Grok), Kubernetes, Velero disaster recovery, Apache Kafka, and Ansible**. Slashed cluster disaster recovery time (**RTO**) by **93%** (8 hours to 30 minutes), reduced **MTTR by 45%**, and sustained **99.95% availability** across 50-node production clusters.

### 4. Technical Skills Ordering
1. **Observability & SRE:** Prometheus, Grafana, Alertmanager, ELK Stack (Elasticsearch, Logstash Grok, Kibana), Velero DR
2. **Platform & Orchestration:** Kubernetes (kubeadm, EKS), Docker, containerd, Helm, Ingress (Nginx, Kong), HPA
3. **Data Backbones & Resilience:** Apache Kafka, Redis, PostgreSQL/TimescaleDB, MongoDB, StatefulSets, PVCs
4. **Automation & IaC:** Ansible (40+ idempotent roles, Jinja2), Terraform (remote state), Bash, YAML
5. **CI/CD & Quality Gates:** Jenkins, GitLab CI, GitHub Actions, Trivy vulnerability scanning, SonarQube, zero-downtime rollouts
6. **Languages & Systems:** Python (FastAPI, PyTest), Rust, SQL, Linux OS Hardening, HAProxy, Keepalived
7. **AI Platform Systems:** pgvector, MLflow, Model Serving Health Probes, Cedar Policy Engine

### 5. Project Ordering
1. **Project Vulcan — Enterprise Automation Control Plane** (FastAPI, Redis Redlock, SRE Diagnostics, WebSockets)
2. **AegisAgent — Zero-Trust AI Agent Security Gateway** (Rust, Cedar Policy, Kubernetes Helm, ServiceMonitors)
