# OLP XDV — Telegram Board Review vs. Production Intent
### Board reviewed: 2026-08-11 daily board (Phase 2, ID415)
### Cross-checked against: `OLP_XDV_PRODUCTION_INTENT.md` (written yesterday, 10 Aug) + framework hard rules (HR34, ID405, calibration doctrine)

**Purpose:** identify where today's live board diverges from stated intent/rules, for Claude Code to investigate and fix. Not a rebuild request — targeted discrepancies only.

---

## FINDING 1 — Qualifying-round fixtures treated as accumulator candidates (likely rule breach)

The 4 fixtures in "TODAY'S PRODUCED BET" and the "★ ACCUMULATOR CANDIDATES (deploy-eligible)" block (Lyon v Sparta Praha, Bodo/Glimt v St. Gilloise, Nijmegen v Olympiakos Piraeus, Sturm Graz v Fenerbahçe) are **Champions League qualifying/play-off round matches**, not UCL league-phase fixtures.

This matters because it was explicitly resolved in a prior session (25 Jul governance discussion, logged in memory):
> "Conference League + qualifying rounds are NOT on the 15-league whitelist (only UCL/UEL league phases) → HR34 banned by default... ratifying Euro qualifiers as a capital surface is Architect-only (bright line, not auto-ratify)."

The board is showing these as "deploy-eligible" candidates without that ratification ever having happened for this season's qualifying round. **Ask Claude Code: is qualifying-round UCL/UEL/Conference League fixtures being auto-included in the deploy-eligible pool, and if so, on what basis — was this ratified, or is the whitelist check not distinguishing league-phase from qualifying-phase fixtures?**

---

## FINDING 2 — Away-win picks appearing as "produced" candidates (ID405 tension)

Of the 4 headline picks, **3 of 4 are away-team wins**: St. Gilloise (away, 47%), Olympiakos Piraeus (away, 47%), Fenerbahçe (away, 44%). Only Lyon (home, 85%) is a home pick.

The board's own footnote states the rule correctly:
> "Away wins are never recommended (ID405 — proven negative market); a card may still show one as the prediction"

That footnote is written to justify showing an away pick *on the wide scan board* as a raw model output — not to justify surfacing 3 of 4 away picks as the day's **headline produced accumulator legs**. Per the production intent doc, "TODAY'S PRODUCED BET" legs are meant to be genuine candidates the accumulator logic would build on (eventually feeding a booking code). Putting ID405-banned picks into that specific slot blurs "shown for transparency" with "recommended" — the exact distinction ID405 exists to protect.

**Ask Claude Code: does the "TODAY'S PRODUCED BET" section apply the ID405 away-win exclusion before selecting legs, or only the wide SCAN board?** If only the wide board, that's the bug.

---

## FINDING 3 — Confidence levels are thin for a "candidate" label

3 of the 4 legs sit at 44–47% — barely above a coin flip for a three-outcome market, and below the framework's own softness/edge bar elsewhere. Combined with Finding 1 (qualifying round, thin data coverage — only 4 of the section's fixtures have any model output, the other 10+ are NO DATA) this looks like the accumulator-candidate slot is being filled from a data-thin, non-deploy league rather than skipped when nothing genuinely qualifies. Worth confirming this isn't happening structurally on light-fixture days.

---

## FINDING 4 — Labeling contradiction: "produced bet" vs "no production pick"

The board says both:
- "TODAY'S PRODUCED BET — 4 produced leg(s)... MARKED PAPER"
- "🎯 PRODUCTION BETS — 2026-08-11 ... NO production pick today — no deploy-eligible fixture with a live price kicks off today."

These read as contradictory in the same document even though they're likely answering two different questions (wide-scan paper output vs. capital-gated production pick). Given Findings 1–2, it's not just a labeling ambiguity — it's plausible the first section is leaking non-deploy-eligible, ID405-flagged fixtures into a "produced bet" framing while the second (correct) section properly gates on real deploy-eligibility. **Recommend Claude Code rename or restructure so a reader can't mistake the paper wide-scan output for an actual production recommendation** — this is exactly the HR53 "unambiguous, self-contained" mandate from yesterday's ratification.

---

## FINDING 5 — Calibration integrity check needed

7-day rolling shows 15 legs logged, 12 with CLV, mean CLV -1.63%. Calibration doctrine (ratified 25 Jul) restricts calibration input to the 5 live domestic deploy leagues only (Ekstraklasa, Danish Superliga, Scottish Prem, Eredivisie, Belgian Pro) — explicitly excluding qualifying-round Euro fixtures as "poor calibration data (skewed, non-representative)."

**Ask Claude Code to confirm none of the 15 logged legs come from Champions League/Europa/Conference League qualifying fixtures** (i.e., the same pool flagged in Finding 1). If any do, the 12/30 gate count and the -1.63% mean CLV are both contaminated and the Phase 3 gate math needs correcting.

---

## WHAT'S WORKING CORRECTLY (no action needed)

- Honest edge caveat is present, prominent, and unambiguous top and bottom — HR53-compliant.
- Genuine NO-DATA fixtures (Celje v Ararat-Armenia, etc.) are marked "NO DATA — PENDING" rather than filled in — HR35 respected.
- Capital authority line ("Capital authority: THE ARCHITECT. Nothing here is live until you deploy it") is present and correct.
- The negative mean CLV (-1.63%) is reported plainly rather than spun — consistent with the framework's honesty mandate.

---

## RECOMMENDED NEXT STEP

Before trusting today's board as calibration input: have Claude Code answer Findings 1, 2, and 5 with a direct code/data trace (not a re-explanation of intent) — specifically, show the filter logic that decides what enters "TODAY'S PRODUCED BET" and confirm whether league-phase vs. qualifying-phase and ID405 are both checked there, and whether the CLV log has any qualifying-round contamination.
