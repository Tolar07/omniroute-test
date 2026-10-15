# Heartbeat Policy

> **Single source of truth for the OLP XDV heartbeat staking rules.**
> Owned by the Architect. Read by every session. Enforced by `olp-xdv-supervisor`.
>
> Any section marked `<!-- ARCHITECT-FILL -->` is unset. While a section is
> unset, the supervisor refuses to publish a heartbeat.

---

## 1. Baseline stake

The stake the pipeline uses for the first heartbeat of a fresh lineage
(i.e. after a full lineage completes, or on cold start).

`baseline_stake_units`: <!-- ARCHITECT-FILL: e.g. 1.0 -->

Units are fractions of `bankroll_ngn` (currently defined in the pipeline env),
not absolute NGN — so a change in bankroll does not silently change stake.

## 2. Compound rule after a win

When the previous heartbeat settled `W`, the next heartbeat's stake is:

`next_stake = previous_stake * compound_factor`

- `compound_factor`: <!-- ARCHITECT-FILL: e.g. 2.0 for straight double -->
- `max_lineage_steps`: <!-- ARCHITECT-FILL: e.g. 4 (cap before reset) -->
- `reset_on`: <!-- ARCHITECT-FILL: one of {"loss", "lineage_complete", "either"} -->

Worked example (illustrative — replace with Architect's numbers):
Baseline 1.0 → W → 2.0 → W → 4.0 → W → 8.0 → W (lineage_complete) → reset to 1.0.

## 3. Selection rule

Given today's board of candidate heartbeats:

- Selection mode: <!-- ARCHITECT-FILL: one of {"highest_ev", "highest_ev_above_threshold", "kelly_weighted"} -->
- Minimum EV threshold (if threshold mode): <!-- ARCHITECT-FILL: e.g. 0.05 (5% edge) -->
- Tie-break rule: <!-- ARCHITECT-FILL: e.g. "shortest odds", "earliest kickoff", "lowest bookmaker margin" -->

The supervisor's gate refuses any selection that does not match this rule
against the day's board snapshot at the time of proposal.

## 4. Safety caps

Hard limits, enforced before every publish:

- `max_stake_units`: <!-- ARCHITECT-FILL: e.g. 8.0 -->
- `max_daily_stake_units`: <!-- ARCHITECT-FILL: e.g. 15.0 (sum across heartbeats in one day) -->
- `min_bankroll_units_remaining`: <!-- ARCHITECT-FILL: e.g. 0.5 (halt if bankroll drops below this) -->

## 5. Halt conditions

The supervisor halts publish (exit 2) when any of the following is true:

- Policy has any unset `<!-- ARCHITECT-FILL -->` sections.
- `HEARTBEAT_STATE.json` was updated more than 26 hours ago (stale).
- Two sessions recorded conflicting outcomes for the same `lineage_step` in the last 24 hours.
- Proposed stake differs from `previous_stake * compound_factor` after a win.
- Proposed selection is not the highest-EV entry (or the rule's equivalent).
- Any safety cap would be breached by the proposal.

## 6. Change procedure

To change any number above:

1. The Architect edits this file directly on `main` (never through a session's chat context alone).
2. Commit message must start with `policy(heartbeat):` and include the reason.
3. The next session's opening protocol picks up the change automatically.
4. In-flight lineages continue under the old rule until they reset; the new rule takes effect from the next fresh lineage.

---

*Last edited: <!-- ARCHITECT-FILL: date --> by <!-- ARCHITECT-FILL: name -->*
