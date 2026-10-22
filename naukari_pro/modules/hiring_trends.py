"""
Feature 8: Industry Hiring Trends
Salary benchmarks, geographic compensation distribution, and high-volume GCC hiring trends.
"""

import logging

logger = logging.getLogger("naukariPro.HiringTrends")

SALARY_BENCHMARKS = {
    "Bengaluru": {"min": 20, "median": 24, "max": 28, "open_vacancies_pct": "38%"},
    "Hyderabad": {"min": 18, "median": 22, "max": 26, "open_vacancies_pct": "29%"},
    "Pune": {"min": 16, "median": 20, "max": 24, "open_vacancies_pct": "18%"},
    "Remote / Pan-India": {"min": 22, "median": 25, "max": 30, "open_vacancies_pct": "15%"}
}

TOP_HIRING_COMPANIES = [
    {"name": "Lloyds Technology Centre", "hub": "Hyderabad", "focus": "Azure Databricks & Cloud Lakehouse", "package": "₹22 - 27 LPA"},
    {"name": "PNC Bank GCC", "hub": "Hyderabad / Remote", "focus": "Platform & Data Infra", "package": "₹22 - 26 LPA"},
    {"name": "JPMorgan Chase", "hub": "Bengaluru / Hyderabad", "focus": "Big Data PySpark & AWS/Azure", "package": "₹24 - 30 LPA"},
    {"name": "Barclays", "hub": "Pune", "focus": "Data Engineering & Kafka", "package": "₹20 - 25 LPA"},
    {"name": "Walmart Global Tech", "hub": "Bengaluru", "focus": "Lakehouse & Real-time Streaming", "package": "₹25 - 32 LPA"},
    {"name": "HSBC Technology", "hub": "Hyderabad / Pune", "focus": "Data Platform & Kubernetes", "package": "₹21 - 26 LPA"},
    {"name": "Cognizant / Infosys / TCS (High-growth Accounts)", "hub": "Pan-India", "focus": "Azure Databricks Migrations", "package": "₹16 - 22 LPA"}
]

class HiringTrendsEngine:
    def display_market_report(self):
        print("\n" + "=" * 75)
        print("  NAUKARIPRO: 2026 INDUSTRY HIRING & SALARY BENCHMARK REPORT")
        print("  Focus: Azure Data Engineering (2-4 YOE | Target 25 LPA)")
        print("=" * 75)

        print("\n[+] GEOGRAPHIC SALARY DISTRIBUTION (LPA)")
        print(f"{'Location Hub':<20} | {'Min CTC':<10} | {'Median CTC':<12} | {'Top Tier (25 LPA)':<18} | {'Share'}")
        print("-" * 75)
        for loc, data in SALARY_BENCHMARKS.items():
            print(f"{loc:<20} | ₹{data['min']} LPA   | ₹{data['median']} LPA    | ₹{data['max']} LPA          | {data['open_vacancies_pct']}")

        print("\n[+] TOP ACTIVELY HIRING ENTERPRISES & GCCS")
        print(f"{'Enterprise / GCC':<26} | {'Target Hub':<16} | {'Salary Range':<16} | {'Key Focus'}")
        print("-" * 75)
        for comp in TOP_HIRING_COMPANIES:
            print(f"{comp['name']:<26} | {comp['hub']:<16} | {comp['package']:<16} | {comp['focus']}")

        print("\n[+] RECRUITER ENGAGEMENT STRATEGY:")
        print("• Optimal Profile Bump Time: Weekdays 09:15 AM - 10:00 AM IST (Captures morning search queues).")
        print("• Peak Recruiter Resdex Activity: Tuesdays, Wednesdays, Thursdays.")
        print("• Highest Salary Multiple: Hyderabad & Bengaluru GCCs pay a 30-40% premium over standard IT services.")
        print("=" * 75 + "\n")
