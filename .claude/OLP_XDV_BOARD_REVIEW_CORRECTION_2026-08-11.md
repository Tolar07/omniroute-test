# OLP XDV — Correction to 2026-08-11 Telegram Board Review
### Architect directive: engine softness gate CANCELLED, market opened

This supersedes part of `OLP_XDV_TELEGRAM_BOARD_REVIEW_2026-08-11.md` sent earlier today. Read that file first for context; this is a targeted correction, not a replacement.

---

## DIRECTIVE (Architect, 11 Aug 2026)

> "I have killed engine softness. I have cancelled awaiting exclusion. I have opened the entire market. I've reduced the discipline [deliberately]."

This is an explicit, in-scope Architect decision — capital-gating changes are Architect-only by the framework's own governance rules, so this is valid regardless of whether it's been logged elsewhere. **Claude Code: confirm in the codebase whether the softness Tier A/B `deploy_eligible` gate (ratified v303.10, FIX 3 — "only Tier A/B leagues are deploy_eligible... everything else is scan-only") has already been removed, and if not, remove it now per this directive.**

---

## FINDING 1 — CLOSED, not a bug

Original finding: Champions League qualifying-round fixtures (non-whitelisted, non-deploy-league) were appearing as "ACCUMULATOR CANDIDATES (deploy-eligible)" in today's board. Given the softness gate is now cancelled and the market is intentionally open, this is **expected behavior**, not a leak. No fix needed here.

---

## FINDING 2 — STILL OPEN (softness cancellation does not resolve this)

3 of 4 headline "TODAY'S PRODUCED BET" legs were away-team win picks (St. Gilloise, Olympiakos Piraeus, Fenerbahçe). ID405 ("away wins are never recommended — a card may still show one as the prediction") is a separate rule from league softness. Opening the market changes *which leagues* can surface candidates; it says nothing about whether ID405's exclusion still applies when selecting the headline produced-bet legs.

**Question for the Architect, to relay to Claude Code once answered:** is ID405 still active as-is, or is it also being loosened as part of "opened the entire market"? Until told otherwise, Claude Code should keep ID405 enforced on the produced-bet/accumulator-candidate selection step — cancelling softness was stated specifically about league eligibility, not about the away-win exclusion.

---

## FINDING 5 — STILL OPEN, now with an added question

Original finding: confirm the 15 logged calibration legs (12 with CLV, mean -1.63%) aren't contaminated by qualifying-round/non-deploy-league fixtures, since calibration doctrine (ratified 25 Jul) restricted calibration input to the 5 domestic deploy leagues specifically to keep the Phase 3 gate number meaningful.

**New question raised by today's directive:** now that the deploy-eligibility gate is cancelled, does the calibration doctrine's league restriction also widen to "all leagues," or does calibration stay scoped to the original 5 even though production no longer is? These don't have to move together — production and calibration serve different purposes (one surfaces bets, the other measures whether the system beats the closing line) — but leaving it undecided means the 12/30 gate count and mean CLV could silently start mixing thin, less-verified leagues into the number that decides Phase 3. **Recommend the Architect make this an explicit call, the same way the softness cancellation was explicit**, rather than let it default either way.

---

## FINDINGS 3 AND 4 — UNCHANGED

Finding 3 (thin 44–47% confidence on 3 of 4 legs) and Finding 4 (labeling contradiction between "TODAY'S PRODUCED BET" and "NO production pick today") stand as originally written — neither is affected by the softness cancellation.

---

## SUMMARY FOR CLAUDE CODE

1. Confirm/complete removal of the Tier A/B softness `deploy_eligible` gate — Finding 1 closed.
2. Do NOT touch ID405 away-win exclusion logic without further Architect instruction — Finding 2 still open.
3. Flag back to the Architect (don't decide silently): does calibration-log league scope also widen, or stay at the original 5 deploy leagues? — Finding 5 still open, now with this added branch.
4. Findings 3 and 4 (thin confidence legs, "produced bet" vs "no production pick" label contradiction) still need addressing independent of all of the above.
