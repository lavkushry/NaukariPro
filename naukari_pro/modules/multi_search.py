"""
naukariPro Feature: Universal Multi-Source Job Search & Hunter
Aggregates and scores job opportunities across:
- Naukri (Direct & Screening Chatbot)
- LinkedIn (Easy Apply & Direct Listings)
- Hacker News Who's Hiring (Algolia / Firebase API)
- Direct Enterprise Career Portals (Greenhouse, Ashby, Lever, Workday)
"""

import os
import sys
import json
import re
import urllib.parse
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from naukari_pro.config import load_config
from naukari_pro.modules.career_portals import load_applicant_profile

TARGET_TITLES = [
    "Azure Data Engineer",
    "Data Engineer",
    "Azure Databricks",
    "PySpark",
    "Delta Lake",
    "Cloud Data Platform"
]

LOCATIONS = ["Hyderabad", "Bengaluru", "Pune", "Remote"]

class UniversalJobSearchEngine:
    def __init__(self):
        self.profile = load_applicant_profile()

    def search_hacker_news(self, limit=10):
        """Fetches fresh tech openings from Hacker News Who's Hiring via Algolia API."""
        print("[*] Querying Hacker News Who's Hiring API...")
        results = []
        try:
            # 1. Identify latest 'Ask HN: Who is hiring' thread
            story_url = "https://hn.algolia.com/api/v1/search?tags=story,author_whoishiring&query=Who%20is%20hiring"
            s_resp = requests.get(story_url, timeout=10)
            if s_resp.status_code == 200:
                s_hits = s_resp.json().get("hits", [])
                story_id = s_hits[0]["objectID"] if s_hits else ""
            else:
                story_id = ""

            # 2. Query comments within the hiring thread
            query_tag = f"comment,story_{story_id}" if story_id else "comment"
            url = f"https://hn.algolia.com/api/v1/search?tags={query_tag}&query=data%20engineer"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                hits = resp.json().get("hits", [])
                for h in hits:
                    raw_text = h.get("comment_text", "")
                    if not raw_text or len(raw_text) < 40:
                        continue

                    soup = BeautifulSoup(raw_text, "html.parser")
                    text = soup.get_text()
                    first_line = text.split("\n")[0]

                    parts = [p.strip() for p in first_line.split("|")]
                    comp = parts[0] if len(parts) > 0 and len(parts[0]) < 50 else "Tech Employer"
                    title = parts[1] if len(parts) > 1 and len(parts[1]) < 60 else "Data Engineer"
                    loc = parts[2] if len(parts) > 2 and len(parts[2]) < 50 else "Remote / Hybrid"

                    url_match = re.search(r'https?://[^\s<>"]+', text)
                    job_url = url_match.group(0) if url_match else f"https://news.ycombinator.com/item?id={h.get('story_id', '')}"

                    results.append({
                        "source": "Hacker News (Who's Hiring)",
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": job_url,
                        "snippet": text[:180].replace("\n", " ") + "...",
                        "type": "Career Portal / Direct Apply"
                    })
                    if len(results) >= limit:
                        break
        except Exception as e:
            print(f"HN API notice: {e}")

        return results

    def get_linkedin_search_links(self):
        """Generates precision LinkedIn search queries for Azure Data Engineer roles."""
        links = []
        for kw in ["Azure Data Engineer", "Azure Databricks", "PySpark Data Engineer"]:
            for loc in ["Hyderabad, India", "Bengaluru, India", "India"]:
                params = {
                    "keywords": kw,
                    "location": loc,
                    "f_TPR": "r604800",   # Past week
                    "f_WT": "2,3",        # Hybrid & Remote
                    "f_E": "2,3",         # Entry to Mid-Senior (2-5 YOE)
                    "sortBy": "DD"        # Most recent
                }
                encoded = urllib.parse.urlencode(params)
                url = f"https://www.linkedin.com/jobs/search/?{encoded}"
                links.append({"title": kw, "location": loc, "url": url})
        return links

    def run_multi_search(self):
        print("\n" + "=" * 65)
        print("  🌐 UNIVERSAL MULTI-SOURCE JOB HUNTER")
        print(f"  Target: ₹25 LPA Azure Data Engineer | Candidate: {self.profile['fullName']}")
        print("  Sources: Naukri, LinkedIn, Hacker News, Career Portals")
        print("=" * 65)

        hn_jobs = self.search_hacker_news(limit=6)
        print(f"\n[+] Hacker News Who's Hiring: Found {len(hn_jobs)} Data & AI Engineering roles:")
        for j in hn_jobs:
            print(f" -> {j['title']} @ {j['company']} [{j['location']}]")
            print(f"    Apply: {j['url']}")

        li_links = self.get_linkedin_search_links()
        print(f"\n[+] LinkedIn Precision Search Targets (Past Week | Hybrid/Remote | 2-5 YOE):")
        for l in li_links[:4]:
            print(f" -> {l['title']} in {l['location']}")
            print(f"    URL: {l['url']}")

        print("\n[+] To auto-fill any discovered external job portal (Greenhouse, Ashby, Lever, Workday):")
        print("    Run: ./naukariPro portal-apply --url \"<URL>\"")
        print("=" * 65 + "\n")
        return hn_jobs
