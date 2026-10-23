"""
Feature 6: AI Interview Prep Tools
High-impact interview simulation and intelligent answer evaluation engine.
Calibrated for a 2.5 YOE candidate targeting ₹25 LPA Azure Data Engineer / Platform roles.
"""

import re
import logging

logger = logging.getLogger("naukariPro.InterviewPrep")

INTERVIEW_TRACKS = {
    "1. Azure Databricks & PySpark Core": [
        {
            "id": "pyspark_skew",
            "q": "How do you diagnose and resolve data skew in a PySpark join?",
            "key_concepts": [
                "spark ui", "skew", "salting", "broadcast", "aqe",
                "adaptive query execution", "skewjoin", "shuffle", "partition"
            ],
            "ideal_answer": (
                "1. Identify the skewed join key using Spark UI stage details (one task takes 10x longer while others finish).\n"
                "2. Salting technique: Append a random prefix/suffix (e.g. 0 to N-1) to the skewed key on both dataframes to distribute partitions evenly.\n"
                "3. Broadcast join: If one dataset is under 10MB (or up to 100MB with broadcast hint), broadcast the smaller dataset to eliminate shuffle entirely.\n"
                "4. AQE (Adaptive Query Execution): Enable `spark.sql.adaptive.skewJoin.enabled = true` in Spark 3.x to let Spark split skewed partitions automatically."
            )
        },
        {
            "id": "pyspark_repartition_coalesce",
            "q": "Explain the difference between repartition() and coalesce() in PySpark.",
            "key_concepts": [
                "shuffle", "network", "full shuffle", "adjacent partitions",
                "decrease", "increase", "performance", "narrow dependency"
            ],
            "ideal_answer": (
                "• `repartition(n)`: Performs a full network shuffle across all executors. Used when increasing partition count or evening out skewed distributions.\n"
                "• `coalesce(n)`: Avoids a full shuffle by merging adjacent partitions into a smaller number. Only works when decreasing partition count (e.g., before writing to storage)."
            )
        }
    ],
    "2. Delta Lake & Medallion Architecture": [
        {
            "id": "delta_acid",
            "q": "How does Delta Lake guarantee ACID transactions over cloud object storage (ADLS Gen2)?",
            "key_concepts": [
                "_delta_log", "transaction log", "json commit", "checkpoint",
                "parquet", "optimistic concurrency", "occ", "atomicity", "adls"
            ],
            "ideal_answer": (
                "Delta Lake relies on the `_delta_log/` transaction log using serialized JSON commit files and checkpoint Parquet files.\n"
                "It uses Optimistic Concurrency Control (OCC): writes verify that no other transaction committed changes to the same partition/files.\n"
                "If a conflict occurs, Delta automatically retries the operation if concurrent modifications do not intersect."
            )
        },
        {
            "id": "medallion_architecture",
            "q": "What is the Medallion Architecture and how did you implement it in your Azure project?",
            "key_concepts": [
                "bronze", "silver", "gold", "raw", "clean", "deduplicate",
                "star schema", "adf", "databricks", "delta live tables"
            ],
            "ideal_answer": (
                "• Bronze Layer: Raw append-only ingestion from source systems via ADF (preserving original schema and ingest metadata).\n"
                "• Silver Layer: Cleaned, deduplicated, and schema-enforced data with joins and enrichments (PySpark batch transformations).\n"
                "• Gold Layer: Aggregated, business-level dimensional tables (Star Schema) and Delta Live Tables optimized for reporting and analytics."
            )
        }
    ],
    "3. Streaming & Distributed Infrastructure": [
        {
            "id": "kafka_k8s",
            "q": "How did you manage Apache Kafka on Kubernetes at HFCL, and how did you guarantee data persistence?",
            "key_concepts": [
                "statefulset", "pvc", "persistent volume", "replication factor",
                "insync replicas", "prometheus", "consumer lag", "rto", "backup"
            ],
            "ideal_answer": (
                "We deployed Kafka using Kubernetes StatefulSets backed by persistent volume claims (PVCs) on high-performance NVMe storage.\n"
                "We configured 3-way replication (`replication.factor=3`, `min.insync.replicas=2`), configured Prometheus exporter alerts for consumer lag, and used Velero for disaster recovery snapshots, reducing RTO from 8h to 30min."
            )
        }
    ],
    "4. HR, Compensation & ₹25 LPA Negotiation": [
        {
            "id": "comp_negotiation",
            "q": "You are currently at ₹12 LPA with 2.5 YOE. How do you justify asking for ₹25 LPA (over 100% hike)?",
            "key_concepts": [
                "deliverables", "platform", "databricks", "dataops", "infrastructure",
                "pyspark", "gcc", "market benchmark", "independent ownership"
            ],
            "ideal_answer": (
                "My current compensation reflects a standardized entry-level service baseline, whereas my day-to-day deliverables operate at a senior platform level:\n"
                "1. I independently manage multi-tenant Kubernetes platforms and end-to-end Medallion Lakehouse pipelines on Azure Databricks with ADF.\n"
                "2. I operate across both Cloud Infrastructure (IaC/Terraform/CI-CD) and distributed Big Data processing (PySpark/Delta Lake/Kafka), bridging DataOps and Data Engineering.\n"
                "3. Benchmark data for GCCs and product companies in Hyderabad/Bengaluru places specialized Cloud Data Engineers at ₹22-28 LPA for high-performance talent."
            )
        }
    ]
}

class InterviewPrepEngine:
    @property
    def q_and_a_bank(self):
        all_qas = []
        for track, qas in INTERVIEW_TRACKS.items():
            for qa in qas:
                all_qas.append({"topic": track, "q": qa["q"], "ans": qa["ideal_answer"]})
        return all_qas

    def get_tracks(self):
        return list(INTERVIEW_TRACKS.keys())

    def get_questions_for_track(self, track_name):
        return INTERVIEW_TRACKS.get(track_name, [])

    def score_candidate_answer(self, question_item, candidate_answer):
        """
        Evaluates candidate answer against core technical concepts, quantification, and depth.
        Returns a score out of 10 with actionable feedback.
        """
        ans_clean = (candidate_answer or "").strip()
        if not ans_clean:
            return {
                "score": 0,
                "concepts_covered": [],
                "concepts_missed": question_item.get("key_concepts", []),
                "feedback": "Empty answer provided. Review the ideal response.",
                "model_answer": question_item.get("ideal_answer")
            }

        ans_lower = ans_clean.lower()
        key_concepts = question_item.get("key_concepts", [])
        
        covered = [c for c in key_concepts if c in ans_lower]
        missed = [c for c in key_concepts if c not in ans_lower]

        # Concept coverage score (0 to 6 points)
        coverage_ratio = len(covered) / max(1, len(key_concepts))
        concept_pts = round(coverage_ratio * 6.0, 1)

        # Quantification / numbers check (0 to 2 points)
        has_metrics = bool(re.search(r'\d+', ans_clean))
        metric_pts = 2.0 if has_metrics else 0.5

        # Word count & articulation depth (0 to 2 points)
        word_count = len(ans_clean.split())
        depth_pts = 2.0 if word_count >= 35 else (1.0 if word_count >= 15 else 0.5)

        total_score = min(10.0, round(concept_pts + metric_pts + depth_pts, 1))

        if total_score >= 8.5:
            feedback = "Excellent response! Demonstrates strong architectural understanding and specific implementation details."
        elif total_score >= 6.0:
            feedback = f"Good foundational answer. To reach a ₹25 LPA standard, incorporate missing keywords: {', '.join(missed[:3])}."
        else:
            feedback = f"Needs improvement. The response lacks key technical depth. Crucial missing concepts: {', '.join(missed[:4])}."

        return {
            "score": total_score,
            "concepts_covered": covered,
            "concepts_missed": missed,
            "word_count": word_count,
            "has_metrics": has_metrics,
            "feedback": feedback,
            "model_answer": question_item.get("ideal_answer")
        }

    def display_full_prep_guide(self):
        print("\n" + "=" * 70)
        print("  NAUKARIPRO: AI INTERVIEW PREPARATION MASTER BANK (₹25 LPA FOCUS)")
        print("=" * 70 + "\n")
        for track, qas in INTERVIEW_TRACKS.items():
            print(f"\n### {track.upper()} ###")
            for idx, qa in enumerate(qas, 1):
                print(f"\nQ{idx}: {qa['q']}")
                print("-" * 50)
                print(f"Key Concepts Expected: {', '.join(qa.get('key_concepts', []))}")
                print(f"Benchmark Answer:\n{qa['ideal_answer']}")
        print("\n" + "=" * 70 + "\n")

    def run_interactive_mock_interview(self):
        """Interactive terminal mock interview session with automated scoring."""
        print("\n" + "=" * 70)
        print("  🎙️ NAUKARIPRO: INTERACTIVE AI MOCK INTERVIEW EVALUATOR")
        print("  Benchmark: ₹25 LPA Azure Data Platform / GCC Senior Standards")
        print("=" * 70)

        all_qas = []
        for track, qas in INTERVIEW_TRACKS.items():
            for qa in qas:
                all_qas.append((track, qa))

        total_questions = min(3, len(all_qas))
        session_scores = []

        for idx, (track, qa) in enumerate(all_qas[:total_questions], 1):
            print(f"\n[Question {idx}/{total_questions}] Domain: {track}")
            print(f"👉 {qa['q']}")
            print("-" * 60)
            candidate_ans = input("Your Answer (press Enter when done): ").strip()

            result = self.score_candidate_answer(qa, candidate_ans)
            session_scores.append(result["score"])

            print("\n" + "-" * 40)
            print(f"  ⭐ Score: {result['score']}/10.0")
            print(f"  📝 Concepts Covered: {', '.join(result['concepts_covered']) if result['concepts_covered'] else 'None'}")
            if result['concepts_missed']:
                print(f"  ⚠️ Key Missing Keywords: {', '.join(result['concepts_missed'])}")
            print(f"  💡 Evaluator Feedback: {result['feedback']}")
            print(f"\n  📘 Model Benchmark Answer:\n{result['model_answer']}")
            print("-" * 60)

        avg_score = round(sum(session_scores) / max(1, len(session_scores)), 1)
        print("\n" + "=" * 70)
        print(f"  🏁 MOCK INTERVIEW COMPLETE — Overall Score: {avg_score}/10.0")
        if avg_score >= 8.0:
            print("  🏆 Strong ₹25 LPA Readiness: Candidate demonstrates deep technical ownership.")
        elif avg_score >= 6.0:
            print("  📈 Moderate Readiness: Good technical base, practice metric-driven explanations.")
        else:
            print("  📚 Needs Additional Preparation: Focus on Delta Lake internals and Spark AQE.")
        print("=" * 70 + "\n")
