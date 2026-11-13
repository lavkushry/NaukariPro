"""Indeed RSS adapter offline proofs."""

from __future__ import annotations

import asyncio
from naukari_pro.aggregation.adapters import indeed as indeed_mod
from naukari_pro.aggregation.base import AdapterRegistry, SourceRecord
import naukari_pro.aggregation.adapters  # noqa: F401


SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Indeed jobs</title>
    <item>
      <title>Azure Data Engineer - Acme Corp</title>
      <link>https://www.indeed.co.in/viewjob?jk=abc123def</link>
      <description>&lt;b&gt;Hyderabad, Telangana&lt;/b&gt; Databricks PySpark</description>
      <pubDate>Fri, 13 Nov 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_indeed_registered():
    assert AdapterRegistry.get("indeed") is not None
    assert "indeed" in AdapterRegistry.known()


def test_indeed_parses_rss(monkeypatch):
    def fake_sync_request(url, **kwargs):
        return 200, {"Content-Type": "application/rss+xml"}, SAMPLE_RSS

    monkeypatch.setattr(indeed_mod, "sync_request", fake_sync_request)
    adapter = indeed_mod.IndeedAdapter()
    source = SourceRecord(
        company="Indeed India",
        ats_type="indeed",
        board_identifier='devops|"Hyderabad"',
        domain="indeed.co.in",
    )
    result = asyncio.run(adapter.fetch_jobs(source))
    assert result.status_code == 200
    assert result.error is None
    assert len(result.jobs) == 1
    job = result.jobs[0]
    assert job.company == "Acme Corp"
    assert "Azure Data Engineer" in job.title
    assert "jk=abc123def" in job.url or "abc123def" in job.external_job_id
