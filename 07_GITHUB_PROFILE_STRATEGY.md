# 07_GITHUB_PROFILE_STRATEGY.md — 90-Second GitHub Recruiter Audit & Optimization

> **Author:** Agent 6 — Technical GitHub Recruiter  
> **Candidate Profile:** [`github.com/lavkushry`](https://github.com/lavkushry)  
> **Evaluation Window:** 90 Seconds (Hiring Manager First Screen)  
> **Goal:** Convert profile visits into immediate technical phone screen invitations  

---

## 1. The 90-Second Recruiter Screen Breakdown

When a technical recruiter or engineering hiring manager opens a GitHub profile, they follow a predictable eye-tracking path:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       90-SECOND VISUAL SCAN PATH                            │
│                                                                             │
│  [0-10s]  Avatar, Name, Bio, Location, Company ("Bangalore", "DevOps Eng")  │
│  [10-30s] Pinned Repositories: Names, Descriptions, Languages, Star Count   │
│  [30-60s] Click Flagship Repo #1 (AegisAgent): Readme Header, Badges, Diag  │
│  [60-90s] Click Flagship Repo #2 (Vulcan): Code structure, Tests, CI files  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Status vs. Target State
* **Current Profile Bio:** *"Software engineer | Rust, Python, TS, Go| Full-stack developer | Open-source contributor | Continuous learner"*
  - *Critique:* Too generic. Reads like a junior bootcamp graduate. Completely buries his 50-node Kubernetes and enterprise infrastructure strength!
* **Target Profile Bio:**  
  **"ML Platform & AI Infrastructure Engineer | Kubernetes · Distributed Systems · Rust · Python · SRE"**
* **Location:** Must explicitly show **"Bangalore, India"**.
* **Current Company:** **"CGI India"**.

---

## 2. Pinned Repository Strategy

The candidate must pin exactly **4 to 6 high-signal repositories**, ordered to tell a cohesive story of infrastructure, security, and data platforms:

| Pin # | Repository | Category | Why It Wins the Recruiter Screen | Recommended Description | Recommended Topics |
|:---:|:---|:---|:---|:---|:---|
| **1** | **`AegisAgent`** | AI Infrastructure & Security | Flagship original Rust codebase (1,059+ files). Proves elite systems engineering and AI agent protection. | Zero-Trust API Firewall and Sandboxed Runtime for Autonomous AI Agents & MCP Tool Execution in Rust & Kubernetes. | `rust`, `ai-security`, `mcp`, `kubernetes`, `helm`, `cedar-policy`, `zero-trust` |
| **2** | **`vulcan`** | Platform Engineering & Distributed SRE | Flagship automation control plane (663+ files). Proves distributed concurrency, pgvector, and SRE tooling. | Enterprise Infrastructure Automation Control Plane & AI SRE Diagnostics with pgvector, Redis Redlock, and MinIO S3. | `python`, `fastapi`, `pgvector`, `redis-redlock`, `sre`, `ansible`, `distributed-systems` |
| **3** | **`Azure-Data-Engineering-Medallion-Lakehouse-Project`** | Data Engineering & ML Data Backbone | Proves PySpark, Databricks, Delta Lake, and enterprise ADF ingestion. | End-to-End E-Commerce Medallion Lakehouse on Azure Databricks, Delta Lake, and Azure Data Factory (PySpark). | `databricks`, `pyspark`, `delta-lake`, `azure-data-factory`, `data-engineering`, `medallion-architecture` |
| **4** | **`ApplyBot`** | Full-Stack AI Application | Proves hands-on integration with local (Ollama) and cloud LLMs (Gemini, Claude). | AI-Powered Job Application Operating System with Multi-LLM Orchestration, Resume Intelligence, and Browser Automation. | `typescript`, `nextjs`, `llm`, `ollama`, `agentic-ai`, `full-stack` |

---

## 3. Flagship README Overhauls

### A. AegisAgent Repository Polish
`AegisAgent` already has impressive architecture, but needs 3 recruiter-facing touches:
1. **Prominent Architecture Diagram:** Ensure the Mermaid diagram showing `[AI Agent / MCP Client] -> [aegis-llm-gateway] -> [aegis-cage-runner sandbox] -> [Cedar Policy Engine]` renders cleanly on the main page.
2. **Benchmark Proof Table:**
   ```markdown
   ### Benchmark Performance (Cedar Engine Evaluation)
   | Concurrency | Average Latency | p95 Latency | p99 Latency | Throughput |
   |:---|:---|:---|:---|:---|
   | 50 concurrent requests | 18ms | 42ms | 68ms | 1,420 req/sec |
   | 200 concurrent requests | 31ms | 58ms | 74ms | 2,850 req/sec |
   ```
3. **Helm Quickstart:**
   ```bash
   helm repo add aegis https://lavkushry.github.io/AegisAgent
   helm install aegis-gateway ./helm/aegis-gateway -n aegis-system --create-namespace
   ```

### B. Vulcan Repository Polish
1. **Clear Concise Title & Description:**  
   Replace the overly theoretical header with:  
   `# Project Vulcan: Enterprise Infrastructure Automation & SRE Control Plane`
2. **Add CI Badge:** Add GitHub Actions workflow status badge (`vulcan-ci.yml`).
3. **Component Architecture Flow:**  
   `FastAPI Ingress -> Redis Redlock Concurrency -> pgvector HNSW Context -> MinIO S3 Decoupled Artifacts -> WebSocket Live Stream`.

---

## 4. GitHub Profile README Template (`lavkushry/lavkushry`)

Create or update the profile README (`https://github.com/lavkushry/lavkushry/README.md`) with this technical layout:

```markdown
# Hi, I'm Lavkush Kumar 👋
### ML Platform & AI Infrastructure Engineer | Kubernetes · Distributed Systems · SRE

I build resilient, automated, and secure infrastructure for high-scale distributed systems and AI workloads. My background combines 2.5+ years of enterprise platform operations (50-node bare-metal & cloud Kubernetes, Ansible lifecycle automation, stateful data backbones) with systems programming in Rust and Python.

📍 **Location:** Bangalore, India  
💼 **Current:** DevOps Engineer at CGI India  
🛠️ **Core Focus:** ML Platform Infrastructure, AI Agent Sandboxing, Distributed SRE  

---

### 🚀 Flagship Systems & Engineering Proof

- 🛡️ **[AegisAgent](https://github.com/lavkushry/AegisAgent)** — Zero-Trust API Firewall and Sandboxed Runtime for Autonomous AI Agents & Model Context Protocol (MCP) in **Rust** and **Kubernetes** (Cedar Policy Engine, sub-75ms evaluation).
- ⚙️ **[Project Vulcan](https://github.com/lavkushry/vulcan)** — Enterprise Automation Control Plane in **Python (FastAPI)** featuring **pgvector HNSW** indexing, **Redis Redlock** distributed concurrency, and **MinIO S3** decoupled storage.
- 🌊 **[Azure Medallion Lakehouse](https://github.com/lavkushry/Azure-Data-Engineering-Medallion-Lakehouse-Project)** — Production-grade data platform on **Azure Databricks**, **Delta Lake**, and **Azure Data Factory** (PySpark batch processing).

---

### 💻 Production Technology Stack

| Domain | Production Tools & Technologies |
|:---|:---|
| **Platform & K8s** | Kubernetes (`kubeadm`, EKS), Docker, containerd, Helm, ArgoCD, Harbor |
| **Automation & IaC** | Ansible (40+ playbooks/roles, Jinja2), Terraform (remote state), Bash |
| **Data Backbones** | Apache Kafka, Redis, PostgreSQL / TimescaleDB, MongoDB, pgvector, MinIO |
| **Observability & SRE**| Prometheus, Grafana, Alertmanager, ELK Stack (Logstash Grok, Kibana), Velero |
| **CI/CD & Security** | Jenkins (declarative), GitLab CI, GitHub Actions, Trivy, SonarQube, Cedar |
| **Languages** | Python (FastAPI, PySpark, PyTest), Rust, SQL, YAML, Bash |

---

### 📬 Connect With Me
- 🌐 **LinkedIn:** [linkedin.com/in/lavkushry](https://linkedin.com/in/lavkushry)
- 📧 **Email:** [lavkushry@gmail.com](mailto:lavkushry@gmail.com)
```

---

## 5. Candidate Action Items (Execute Immediately)

1. **Delete / Unpublish Dead Links:** Remove any external references to `mlops-platform-automation` and `genai-observability-platform`.
2. **Update Profile Bio:** Change GitHub bio to: *"ML Platform & AI Infrastructure Engineer | Kubernetes · Distributed Systems · Rust · Python · SRE"*.
3. **Set Location:** Update GitHub location field to **"Bangalore, India"**.
4. **Pin Top 4 Repos:** Pin `AegisAgent`, `vulcan`, `Azure-Data-Engineering-Medallion-Lakehouse-Project`, and `ApplyBot`.
5. **Update Profile README:** Deploy the markdown template above to `lavkushry/lavkushry`.
