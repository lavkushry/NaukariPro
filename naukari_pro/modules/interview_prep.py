"""
Feature 6: AI Interview Prep Tools
High-impact interview simulation and Q&A bank customized for a 2.5 YOE candidate targeting ₹25 LPA.
"""

import logging

logger = logging.getLogger("naukariPro.InterviewPrep")

INTERVIEW_TRACKS = {
    "1. Azure Databricks & PySpark Core": [
        {
            "q": "How do you diagnose and resolve data skew in a PySpark join?",
            "ideal_answer": (
                "1. Identify the skewed join key using Spark UI stage details (one task takes 10x longer while others finish).\n"
                "2. Salting technique: Append a random prefix/suffix (e.g. 0 to N-1) to the skewed key on both dataframes to distribute partitions evenly.\n"
                "3. Broadcast join: If one dataset is under 10MB (or up to 100MB with broadcast hint), broadcast the smaller dataset to eliminate shuffle entirely.\n"
                "4. AQE (Adaptive Query Execution): Enable `spark.sql.adaptive.skewJoin.enabled = true` in Spark 3.x to let Spark split skewed partitions automatically."
            )
        },
        {
            "q": "Explain the difference between repartition() and coalesce() in PySpark.",
            "ideal_answer": (
                "• `repartition(n)`: Performs a full network shuffle across all executors. Used when increasing partition count or evening out skewed distributions.\n"
                "• `coalesce(n)`: Avoids a full shuffle by merging adjacent partitions into a smaller number. Only works when decreasing partition count (e.g., before writing to storage)."
            )
        }
    ],
    "2. Delta Lake & Medallion Architecture": [
        {
            "q": "How does Delta Lake guarantee ACID transactions over cloud object storage (ADLS Gen2)?",
            "ideal_answer": (
                "Delta Lake relies on the `_delta_log/` transaction log using serialized JSON commit files and checkpoint Parquet files.\n"
                "It uses Optimistic Concurrency Control (OCC): writes verify that no other transaction committed changes to the same partition/files.\n"
                "If a conflict occurs, Delta automatically retries the operation if concurrent modifications do not intersect."
            )
        },
        {
            "q": "What is the Medallion Architecture and how did you implement it in your Azure project?",
            "ideal_answer": (
                "• Bronze Layer: Raw append-only ingestion from source systems via ADF (preserving original schema and ingest metadata).\n"
                "• Silver Layer: Cleaned, deduplicated, and schema-enforced data with joins and enrichments (PySpark batch transformations).\n"
                "• Gold Layer: Aggregated, business-level dimensional tables (Star Schema) and Delta Live Tables optimized for reporting and analytics."
            )
        }
    ],
    "3. Streaming & Distributed Infrastructure": [
        {
            "q": "How did you manage Apache Kafka on Kubernetes at HFCL, and how did you guarantee data persistence?",
            "ideal_answer": (
                "We deployed Kafka using Kubernetes StatefulSets backed by persistent volume claims (PVCs) on high-performance NVMe storage.\n"
                "We configured 3-way replication (`replication.factor=3`, `min.insync.replicas=2`), configured Prometheus exporter alerts for consumer lag, and used Velero for disaster recovery snapshots, reducing RTO from 8h to 30min."
            )
        }
    ],
    "4. HR, Compensation & ₹25 LPA Negotiation": [
        {
            "q": "You are currently at ₹12 LPA with 2.5 YOE. How do you justify asking for ₹25 LPA (over 100% hike)?",
            "ideal_answer": (
                "My current compensation reflects a standardized entry-level service baseline, whereas my day-to-day deliverables operate at a senior platform level:\n"
                "1. I independently manage multi-tenant Kubernetes platforms and end-to-end Medallion Lakehouse pipelines on Azure Databricks with ADF.\n"
                "2. I operate across both Cloud Infrastructure (IaC/Terraform/CI-CD) and distributed Big Data processing (PySpark/Delta Lake/Kafka), bridging DataOps and Data Engineering.\n"
                "3. Benchmark data for GCCs and product companies in Hyderabad/Bengaluru places specialized Cloud Data Engineers at ₹22-28 LPA for high-performance talent."
            )
        },
        {
            "q": "Why are you looking to leave CGI?",
            "ideal_answer": (
                "At CGI, I worked on mission-critical platform infrastructure for PNC Bank GCC. However, my long-term career focus is to specialize deeply as an Azure Data Engineer building core analytical lakehouses, distributed data pipelines, and streaming platforms. I am seeking a role where data engineering is the primary business driver."
            )
        }
    ]
}

class InterviewPrepEngine:
    def get_tracks(self):
        return list(INTERVIEW_TRACKS.keys())

    def get_questions_for_track(self, track_name):
        return INTERVIEW_TRACKS.get(track_name, [])

    def display_full_prep_guide(self):
        print("\n" + "=" * 70)
        print("  NAUKARIPRO: AI INTERVIEW PREPARATION MASTER BANK (25 LPA FOCUS)")
        print("=" * 70 + "\n")
        for track, qas in INTERVIEW_TRACKS.items():
            print(f"\n### {track.upper()} ###")
            for idx, qa in enumerate(qas, 1):
                print(f"\nQ{idx}: {qa['q']}")
                print("-" * 50)
                print(f"Key Points & Blueprint:\n{qa['ideal_answer']}")
        print("\n" + "=" * 70 + "\n")
