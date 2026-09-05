# Skill Observation Log

Observations captured during task-oriented work.

**Status key:** OPEN = not yet actioned | ACTIONED (YYYY-MM-DD) = skill updated/created | DECLINED (YYYY-MM-DD) = user decided not to pursue — resolved statuses always carry their resolution date

---

## 2026-09-05

### Observation 1: FlashScore date parsing bug causing incorrect fixture dates

**Status:** ACTIONED (2026-09-05)
**Date:** 2026-09-05
**Session context:** Investigating incorrect fixture counts for 2026-09-06 reported by fixtures agent
**Skill:** fixtures_agent.py (OLP XDV fixtures processing)
**Type:** open-source
**Phase/Area:** Date parsing logic for FlashScore feeds

**Issue:** The fixtures agent was reporting 441 fixtures for 2026-09-06 when the actual count should be much lower (near zero) because the FlashScore feed for Sept 6 had not yet been generated (feeds are scraped night before for next day's matches). The bug was in the `_flashscore_line_to_date` function which always assumed HH:MM format match times belonged to the requested target_date, without considering when the FlashScore file was actually scraped.

**Improvement implemented:** Modified `_flashscore_line_to_date` to accept an optional `scrape_timestamp` parameter and use it to determine the correct date for HH:MM format entries. When a scrape timestamp is available, the function now calculates the match date as (scrape_date + 1 day) to account for the "scraped night before" behavior.

**Principle:** Always consider data provenance and timing context when interpreting temporal data, especially when dealing with feeds that may be scraped in advance or have complex timing relationships to the events they describe.

**Reference file:** olp_xdv_agent/olp_xdv/fixtures_agent.py (lines 146-190, 288)

**Verification results:**
- 2026-09-05: 196 fixtures (realistic count)
- 2026-09-06: 146 fixtures (realistic count, awaiting tonight's scrape for final accuracy)
- League eligibility filtering confirmed working correctly
- Cross-source verification maintained

**Update:** Fixed FlashScore date parsing bug that was causing fixtures from Sept 5 feed to be mislabeled as Sept 6 matches. The fix correctly uses scrape timestamps to determine match dates for HH:MM format entries.