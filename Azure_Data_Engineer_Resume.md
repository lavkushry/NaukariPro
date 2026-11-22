# LAVKUSH KUMAR
**Bangalore, India** | **+91-9122036484** | **lav84095@gmail.com** | [**linkedin.com/in/lavkushry**](https://www.linkedin.com/in/lavkushry/) | [**github.com/lavkushry**](https://github.com/lavkushry)

---

### PROFESSIONAL SUMMARY
**Platform, Data Infrastructure & MLOps Engineer** with **2.5 years** of experience building high-availability Kubernetes platforms, distributed data backbones (Kafka, Redis, PostgreSQL/TimescaleDB), and Terraform/Ansible automation. Experienced across cloud-native CI/CD, observability, and Azure Data Engineering project architectures (**PySpark, Azure Databricks, Delta Lake, ADF**), delivering **83% faster cluster bootstrap** and **93% RTO reduction**.

---

### TECHNICAL SKILLS
* **Data & Streaming Backbones:** Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, pgvector (HNSW), MinIO S3
* **Data Engineering (Projects):** Azure Databricks, PySpark, Spark SQL, Delta Lake, Medallion Architecture, Azure Data Factory (ADF), ADLS Gen2
* **Platform & Orchestration:** Kubernetes (`kubeadm`, AWS EKS), Docker, containerd, Helm, ArgoCD (GitOps), Harbor Registry
* **IaC, CI/CD & Security:** Terraform (remote state), Ansible (40+ roles, Jinja2), Jenkins, GitLab CI, GitHub Actions, Trivy, Nginx/Kong
* **Observability & SRE:** Prometheus, Grafana, Alertmanager, ELK Stack (Elasticsearch, Logstash Grok, Kibana), Velero DR
* **Languages & Frameworks:** Python (FastAPI, PySpark, PyTest), Rust, SQL, Bash, YAML, Cedar Policy Engine

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
* **Orchestrated** stateful distributed data backbones (Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB) on Kubernetes via StatefulSets; configured Velero DR and Prometheus/Grafana alerts, slashing **RTO from 8h to 30min (93%)** and **MTTR by 45%**.
* **Standardized** declarative Jenkins pipelines with Docker, Helm, SonarQube, and Trivy security gates, enabling zero-downtime rolling updates and doubling release frequency (**2x**).

#### **CGI India** — Bangalore, India
**Security Analyst Apprentice** | *Sep 2024 – Aug 2025*
* **Centralized** multi-source log ingestion via the ELK Stack (Elasticsearch, Logstash, Kibana), building operational dashboards and query filters that reduced root-cause investigation time by **35%**.
* **Authored** custom Logstash Grok patterns to parse high-volume unstructured syslog and firewall/IDS telemetry into structured schemas, cutting log triage time by **45%**.

#### **Stipe Solutions** — Bangalore, India
**Full Stack Developer Intern** | *Mar 2024 – Sep 2024*
* **Developed** 30+ cross-platform mobile screens using React Native and Flutter with RESTful API integrations and PostgreSQL query optimization for **1,000+ daily active users**.

---

### KEY ENGINEERING PROJECTS

#### [**Azure Medallion Lakehouse Platform**](https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project) | *Azure Databricks, PySpark, Delta Lake, ADF, ADLS Gen2, SQL* | *2026*
* **Architected** an end-to-end Medallion Lakehouse (Bronze, Silver, Gold) on Azure Databricks and Delta Lake with ADF orchestration and ADLS Gen2 storage layers.
* **Optimized** distributed PySpark and Spark SQL transformations with schema validation and partition pruning, cutting batch ETL pipeline runtime by **35%** while enforcing ACID consistency.

#### [**AegisAgent — Zero-Trust AI Agent Security Gateway**](https://github.com/lavkushry/AegisAgent) | *Rust, Cedar Policy Engine, Kubernetes, Helm, Docker* | *2026*
* **Architected** an open-source zero-trust security gateway for AI agents in Rust with the Cedar Policy Engine (**sub-75ms policy evaluation**) and Helm charts with GitHub Actions CI/SAST scanning.

#### [**Project Vulcan — Enterprise Automation Control Plane**](https://github.com/lavkushry/vulcan) | *Python, FastAPI, pgvector, Redis Redlock, MinIO S3* | *2025*
* **Engineered** a FastAPI infrastructure control plane with Redis Redlock distributed locking, MinIO S3 storage, and PostgreSQL/pgvector HNSW retrieval, cutting SRE diagnostics under **2 minutes**.

---

### EDUCATION
* **B.Tech in Computer Science & Engineering** — World College of Technology and Management (MDU, Rohtak) | *2020 – 2023*
* **Diploma in Computer Science Engineering** — Government Polytechnic, Patna-7 | *2016 – 2019*

### CERTIFICATIONS
* **Microsoft Azure Fundamentals (AZ-900)** (2025) | **Microsoft SC-200** (2025) | **Certified Kubernetes Administrator (CKA)** — CNCF *(In Progress)*

---

## Changelog

### Update: November 22, 2026
- Removed fabricated CGI India `Azure Data Engineer` title and Azure Lakehouse employment bullets; restored canonical `AGENTS.md §9` & `01_FACT_MATRIX.md` experience.
- Fixed broken vanity LinkedIn and GitHub URLs to `https://www.linkedin.com/in/lavkushry/` and `https://github.com/lavkushry`.
- Replaced unlinked synthetic second project with verified public repositories `AegisAgent` and `vulcan` alongside `Azure-Data-Engineering-Medallion-Lakehouse-Project`.
