# LAVKUSH KUMAR
**Hyderabad, India** | **+91-9122036484** | **lavkushry@gmail.com** | [**linkedin.com/in/lavkushry**](https://linkedin.com/in/lavkushry) | [**github.com/lavkushry**](https://github.com/lavkushry)

---

### PROFESSIONAL SUMMARY
**Platform Engineer specializing in ML Platform and AI Infrastructure** with **2.5+ years** of experience operating high-availability Kubernetes platforms, scalable data streaming, and CI/CD pipelines. Proficient in **Kubernetes (kubeadm, EKS), Terraform, Ansible, Jenkins, Prometheus, and Apache Kafka**. Track record of automating bare-metal clusters (**83% faster bootstrap**), stateful data backbones (**93% RTO reduction**), and open-source AI agent security control planes in **Rust** and **Python**.

---

### TECHNICAL SKILLS
* **Platform & Orchestration:** Kubernetes (`kubeadm`, AWS EKS), Docker, containerd, Helm, ArgoCD (GitOps), Harbor Registry
* **Infrastructure as Code:** Terraform (modular architecture, remote state), Ansible (40+ roles, Jinja2), Bash, YAML
* **CI/CD & Security:** Jenkins (declarative), GitLab CI, GitHub Actions, Trivy container scanning, SonarQube, RBAC
* **Observability & SRE:** Prometheus, Grafana, Alertmanager, ELK Stack (Elasticsearch, Logstash Grok, Kibana), Velero DR
* **Data & Distributed Systems:** Apache Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB, pgvector (HNSW), MinIO S3
* **Languages & Frameworks:** Python (FastAPI, AsyncIO, PyTest), Rust, SQL, Jinja2, RESTful APIs, WebSockets
* **ML & AI Infrastructure:** MLflow (Model Registry, Lineage), Model Serving APIs, Vector Indexing, Cedar Policy Engine

---

### PROFESSIONAL EXPERIENCE

#### **CGI India (Client: PNC Bank GCC)** — Hyderabad, India
**DevOps Engineer (Contractor — Cloud Infra & Kubernetes)** | *Jun 2026 – Present*
* **Provisioned** multi-tenant AWS EKS cluster infrastructure using Terraform modules and Ansible, establishing reproducible VPC peering, IAM roles, and auto-scaling node groups across environments.
* **Engineered** declarative Jenkins and GitLab CI pipelines with Trivy container scanning and automated quality gates, cutting deployment lead time by **40%**.
* **Hardened** ingress routing using Nginx Ingress and Kong Gateway with rate-limiting and mTLS, slashing gateway latency overhead by **15%** across **8** production microservices.

#### **HFCL Limited** — Bangalore, India
**Engineer 1 — DevOps / Platform Engineering** *(Platform Automation & Reliability)* | *Aug 2025 – Jun 2026*
* **Automated** bare-metal Kubernetes (`kubeadm`) lifecycle via 40+ Ansible roles and Jinja2 templates (OS hardening, CNI, Harbor, Helm), cutting bootstrap time **from 2 days to 4 hours (83% reduction)**.
* **Operated** a 50-node on-premise Kubernetes platform for 15+ mission-critical microservices with namespace isolation, RBAC, and HPA, sustaining **99.95% platform availability**.
* **Orchestrated** stateful cluster workloads (Kafka, Redis, PostgreSQL, TimescaleDB, MongoDB) on Kubernetes via StatefulSets; configured Velero DR and Prometheus/Grafana alerts, slashing **RTO from 8h to 30min (93%)** and **MTTR by 45%**.
* **Standardized** declarative Jenkins pipelines with Docker, Helm, and Trivy security gates, enabling zero-downtime rolling updates and doubling release frequency (**2x**).

#### **CGI India** — Hyderabad, India
**Security Analyst Apprentice** *(Log Analytics & Observability)* | *Sep 2024 – Aug 2025*
* **Deployed** centralized log pipelines via the ELK Stack (Elasticsearch, Logstash, Kibana), building operational dashboards and query filters that reduced root-cause investigation time by **35%**.
* **Authored** custom Logstash Grok patterns to parse unstructured syslog and network telemetry into structured JSON schemas, accelerating incident triage by **50%**.

#### **Stipe Solutions** — Bangalore, India
**Full Stack Developer Intern** *(Mobile & Web Engineering)* | *Mar 2024 – Sep 2024*
* **Developed** 30+ production mobile screens and UI components using React Native and Flutter, integrating RESTful APIs and state management for **1,000+ daily active users**.

---

### KEY PROJECTS

#### [**AegisAgent — Zero-Trust AI Agent Security Gateway**](https://github.com/lavkushry/AegisAgent) | *Rust, Cedar Policy Engine, Kubernetes, Helm, Docker* | *2026*
* **Architected** an open-source zero-trust security gateway for AI agents in Rust, integrating the Cedar Policy Engine to enforce ABAC over MCP tool invocations with **sub-75ms policy evaluation**.
* **Engineered** production Kubernetes Helm charts (`aegis-gateway`), ServiceMonitors, and NetworkPolicies, containerizing agent cages with reproducible GitHub Actions CI/SAST pipelines ensuring **100%** scan coverage.

#### [**Project Vulcan — Enterprise Automation Control Plane**](https://github.com/lavkushry/vulcan) | *Python, FastAPI, pgvector, Redis Redlock, MinIO S3, WebSockets* | *2025*
* **Architected** an infrastructure control plane in Python (FastAPI), implementing distributed locking via Redis Redlock and decoupled MinIO S3 storage to eliminate runbook race conditions.
* **Integrated** semantic incident retrieval using PostgreSQL with pgvector (HNSW indexing) and WebSocket live log streaming, cutting SRE incident diagnostics down to **under 2 minutes** per task.

---

### EDUCATION
* **World College of Technology and Management** — Gurgaon, India  
  *B.Tech in Computer Science & Engineering* | *Jun 2020 – May 2023*
* **Government Polytechnic, Patna-7** — Patna, India  
  *Diploma in Computer Science Engineering* | *Jul 2016 – Jun 2019*

---

### CERTIFICATIONS
* **Microsoft Azure Fundamentals (AZ-900)** (2025) | **Microsoft Security Operations Analyst (SC-200)** (2025) | **Certified Kubernetes Administrator (CKA)** — CNCF *(In Progress, Expected 2026)*
