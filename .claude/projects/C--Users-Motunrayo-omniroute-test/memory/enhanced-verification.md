---
name: enhanced-verification
description: Enhanced cross-source fixture verification (fixture_matcher) deployed and tested
metadata:
  type: project
---

The enhanced verification thread from `TASK_SUMMARY.md` ("deploy for better team name
matching") was completed on 2026-09-28. Previously `verification/fixture_matcher.py`
existed but was wired into nothing and its own demo reported a 0% verification rate.

## Changes Made
1. **`verification/fixture_matcher.py` hardened** — the module now actually verifies
   fixtures reported by multiple sources:
   - Robust kickoff-date extraction across source key variants
     (`kickoff_utc`, `commence_time`, `start_time`, `datetime`, `kickoff_date`,
     `date`, `kickoff`), with a `target_date` fallback for sources that only carry a
     kickoff time. Fixes the bug where FlashScore (`kickoff_date`) never date-matched
     BBC/SportyBet (`kickoff`/`kickoff_utc`).
   - Generalized `normalize_team_name`: accent folding, `&`/"and" unification,
     punctuation removal, leading/trailing club-affix stripping (FC, AFC, AS, …),
     and an exact whole-name alias map (no more double-expansion such as
     `west ham united united`).
   - `match_fixtures(fixture_lists, target_date=None)` skips fixtures with no
     identifiable teams; `home_team`/`away_team` and `competition` keys also accepted.
2. **`test_fixture_matcher.py`** added at repo root (stdlib only; runs under plain
   `python3` or pytest). 9 tests, all passing — covers aliases, affix stripping,
   accents, key variants, cross-source verification, date separation, and skips.
3. **`collect_odds.py`** now imports the shared `normalize_team_name` from
   `verification.fixture_matcher` (with a safe fallback), so stored odds fixture keys
   use the same normalization as the verifier.
4. **`verification/__init__.py`** added to make it a proper package.

## Verification
- `python3 verification/fixture_matcher.py` → 100% verification rate on the 3-source
  demo (was 0%); all normalization checks pass.
- `python3 test_fixture_matcher.py` → 9/9 passed.
- `python3 -m py_compile collect_odds.py` → clean.

## Environment Note
The `olp_xdv_agent/olp_xdv` submodule (canonical vault, `brain/`, `fixtures_agent`,
`config/leagues.json`) is **not checked out** in the cloud environment, so the full
pipeline cannot be exercised here and `collect_odds.py` cannot run end-to-end
(`brain.store` lives in the submodule). The verification module and its tests are
fully self-contained and were validated in isolation. Wiring `match_fixtures` into
the submodule's `fixtures_agent` remains for a session where the submodule is present.
