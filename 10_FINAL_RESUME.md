# LAVKUSH KUMAR
**Bangalore, India** | **+91-9122036484** | **lav84095@gmail.com** | [**linkedin.com/in/lavkushry**](https://www.linkedin.com/in/lavkushry/) | [**github.com/lavkushry**](https://github.com/lavkushry)

---

### PROFESSIONAL SUMMARY
**Platform, DevOps & MLOps Infrastructure Engineer** with **2.5 years** of experience operating high-availability Kubernetes platforms, stateful data backbones, and automated CI/CD pipelines. Proficient in **Kubernetes (kubeadm, EKS), Terraform, Ansible, ArgoCD, Jenkins, Prometheus, and Apache Kafka**. Proven track record automating bare-metal clusters (**83% faster bootstrap**), disaster recovery (**93% RTO reduction**), and building open-source AI infrastructure and data platforms in **Rust** and **Python**.

---

### TECHNICAL SKILLS
* **Platform & Orchestration:** Kubernetes (`kubeadm`, AWS EKS), Docker, containerd, Helm, ArgoCD (GitOps), Harbor Registry
* **Infrastructure as Code:** Terraform (modular IaC, remote state), Ansible (40+ roles, Jinja2), Bash, YAML
* **CI/CD & Security:** Jenkins (declarative), GitLab CI, GitHub Actions, Trivy container scanning, SonarQube, RBAC, Nginx/Kong
* **Observability & SRE:** Prometheus, Grafana, Alertmanager, ELK Stack (Elasticsearch, Logstash Grok, Kibana), Velero DR
* **Data & Streaming Systems:** Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, pgvector (HNSW), MinIO S3
* **Languages & Data/AI Tooling:** Python (FastAPI, PySpark, PyTest), Rust, SQL, Databricks, Delta Lake, ADF, MLflow, Cedar Policy

---

### PROFESSIONAL EXPERIENCE

#### **CGI India** — Bangalore, India
**DevOps Engineer** | *Jun 2026 – Present*
* **Standardized** multi-tenant AWS EKS container platform deployments using modular Terraform and Ansible, establishing reproducible cluster baselines, auto-scaling node groups, and IAM roles across 3 environments.
* **Engineered** automated CI/CD pipelines in Jenkins and GitLab CI with Trivy vulnerability scanning, container linting, and staging smoke tests, eliminating manual release gates.
* **Hardened** cluster ingress and API gateway policies using Nginx Ingress and Kong Gateway (rate-limiting, TLS termination), and automated GitOps rollouts with ArgoCD and Helm charts.

#### **HFCL Limited** — Bangalore, India
**Engineer 1 — DevOps / Platform Engineering** | *Aug 2025 – Jun 2026*
* **Automated** bare-metal Kubernetes (`kubeadm`) cluster lifecycle via 40+ Ansible roles and Jinja2 templates (OS hardening, CNI, Harbor, Helm), cutting bootstrap time **from 2 days to 4 hours (83% reduction)**.
* **Operated** a 50-node on-premise Kubernetes platform for 15+ distributed microservices with namespace isolation, RBAC, and HPA, sustaining **99.95% platform availability**.
* **Orchestrated** stateful cluster workloads (Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB) on Kubernetes via StatefulSets; configured Velero DR and Prometheus/Grafana alerts, slashing **RTO from 8h to 30min (93%)** and **MTTR by 45%**.
* **Standardized** declarative Jenkins pipelines with Docker, Helm, SonarQube, and Trivy security gates, enabling zero-downtime rolling updates and doubling release frequency (**2x**).

#### **CGI India** — Bangalore, India
**Security Analyst Apprentice** | *Sep 2024 – Aug 2025*
* **Centralized** multi-source log ingestion via the ELK Stack (Elasticsearch, Logstash, Kibana), building operational dashboards and query filters that reduced root-cause investigation time by **35%**.
* **Authored** custom Logstash Grok patterns to parse high-volume unstructured syslog and firewall/IDS telemetry into structured schemas, cutting log triage time by **45%**.

#### **Stipe Solutions** — Bangalore, India
**Full Stack Developer Intern** | *Mar 2024 – Sep 2024*
* **Developed** 30+ cross-platform mobile screens using React Native and Flutter with RESTful API integrations and PostgreSQL query optimization for **1,000+ daily active users**.

---

### KEY PROJECTS

#### [**AegisAgent — Zero-Trust AI Agent Security Gateway**](https://github.com/lavkushry/AegisAgent) | *Rust, Cedar Policy Engine, Kubernetes, Helm, Docker* | *2026*
* **Architected** an open-source zero-trust security gateway for AI agents in Rust, integrating the Cedar Policy Engine to enforce ABAC over MCP tool invocations with **sub-75ms policy evaluation**.
* **Engineered** production Kubernetes Helm charts (`aegis-gateway`), ServiceMonitors, and NetworkPolicies with reproducible GitHub Actions CI/SAST pipelines ensuring **100%** scan coverage.

#### [**Project Vulcan — Enterprise Automation Control Plane**](https://github.com/lavkushry/vulcan) | *Python, FastAPI, pgvector, Redis Redlock, MinIO S3* | *2025*
* **Architected** an infrastructure control plane in Python (FastAPI), implementing distributed locking via Redis Redlock and decoupled MinIO S3 storage to eliminate runbook race conditions.
* **Integrated** semantic incident retrieval using PostgreSQL with pgvector (HNSW indexing) and WebSocket live log streaming, cutting SRE diagnostics down to **under 2 minutes** per task.

#### [**Azure Medallion Lakehouse Platform**](https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project) | *PySpark, Azure Databricks, Delta Lake, ADF, ADLS Gen2* | *2026*
* **Built** an end-to-end Medallion Lakehouse (Bronze/Silver/Gold) on Azure Databricks, Delta Lake, and ADF, optimizing PySpark batch transformations to cut ETL runtime by **35%** with ACID schema validation.

---

### EDUCATION
* **B.Tech in Computer Science & Engineering** — World College of Technology and Management (MDU, Rohtak) | *2020 – 2023*
* **Diploma in Computer Science Engineering** — Government Polytechnic, Patna-7 | *2016 – 2019*

---

### CERTIFICATIONS
* **Microsoft Azure Fundamentals (AZ-900)** (2025) | **Microsoft SC-200** (2025) | **Certified Kubernetes Administrator (CKA)** — CNCF *(In Progress)*

---

## Changelog

### Update: November 22, 2026
- Updated contact header to canonical `Bangalore, India`, `https://www.linkedin.com/in/lavkushry/`, and `https://github.com/lavkushry`.
- Aligned CGI India, HFCL Limited, CGI Apprentice, and Stipe Solutions titles, dates, and bullets strictly to `AGENTS.md §9` and `01_FACT_MATRIX.md`.
- Added verified public project link `Azure-Data-Engineering-Medallion-Lakehouse-Project` alongside `AegisAgent` and `vulcan`.
