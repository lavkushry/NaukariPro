# M2 — Job Aggregator Engine (incremental)

**Date:** November 5, 2026  
**Status:** Extended existing WS1 aggregation (not a rewrite)

## Delivered

| Item | Path |
|------|------|
| `boards.csv` registry (jobseek schema) | `config/boards.csv` |
| Import/export helpers | `naukari_pro/aggregation/boards_registry.py` |
| CLI | `naukariPro boards-import` |
| NormalizedJob v2 fields | `apply_url`, salary_* , `status`, `description_hash` |
| CDX host patterns | Workday, SmartRecruiters, Keka, Teamtailor (+ fixed host capture) |
| India geo aliases + consultancy flag | `naukari_pro/aggregation/india_geo.py` |
| Ashby hardening | `isListed !== false`, prefer `descriptionPlain`, `includeCompensation=true` |
| Existing adapters kept | Greenhouse, Ashby, Lever, Workday, … |

## Notes

- Aggregation adapters, dedupe, storage, and CDX discovery already existed from WS1 — M2 wraps the boards registry + India layer + schema extensions around them.
- Live CDX discovery remains opt-in (network); offline tests cover parsers + CSV import only.

## Changelog

### November 5, 2026

- Added boards.csv registry, India geo, NormalizedJob v2 fields, Ashby/CDX hardening.
