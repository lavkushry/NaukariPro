"""
Workstream 1 — AI job aggregation.
Adapters fetch NormalizedJob records with honest fields only (NULL when unfetched).
"""

from naukari_pro.aggregation.models import NormalizedJob
from naukari_pro.aggregation.pipeline import AggregationPipeline, run_ingest_cycle
from naukari_pro.aggregation.dedup import DedupEngine

__all__ = [
    "NormalizedJob",
    "AggregationPipeline",
    "run_ingest_cycle",
    "DedupEngine",
]
