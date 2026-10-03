# FIXTURE FETCH SPEC — AMENDMENT 1: HORIZON

**Amends:** FIXTURE_FETCH_SPEC.md
**Status:** UNRATIFIED
**Date:** 11 Sep 2026

---

## 1. Verified horizon

The mirror's calendar exposes offsets `d=-7` through `d=+7`. Fifteen
days, rolling. There is no continuous or unbounded mode — 8 days out
does not exist. Any design assuming an arbitrary horizon is building on
something that isn't there.

```
d=-7 → 04/09 Fr        d=0  → Today (11/09 Fr)
d=-1 → Yesterday       d=+1 → Tomorrow
                       d=+2 → 13/09 Su
                       d=+7 → 18/09 Fr
```

## 2. Date anchoring — do not infer, read

Fetch `https://m.flashscore.info/calendar/` at the start of every run.
It returns each offset with its literal date label. Parse that into an
offset→date map and use it as the authority.

This removes date inference from the pipeline entirely. Combined with
the §3 offset resolution in the parent spec, a fixture's calendar day
now comes from two independent signals — the calendar label for the
page it appeared on, and its resolved kickoff. They must agree. If they
don't, that fixture is `NO DATA — PENDING`, not a guess.

## 3. MANDATORY — the identical-payload guard

**Observed 11 Sep 2026:** a fetch of `?d=1` returned the `d=0` payload
with the parameter stripped from the response URL. The mirror served
Today while being asked for Tomorrow, and said nothing about it.

Cause not established — possibly session/cookie dependent, possibly
user-agent gated, possibly a redirect. It does not matter. The
pipeline must assume it can happen on any offset, at any time, and
catch it.

```python
import hashlib

def payload_signature(fixtures):
    """Order-independent fingerprint of a day's fixture set."""
    ids = sorted(fx["match_id"] for fx in fixtures)
    return hashlib.sha256("|".join(ids).encode()).hexdigest()[:16]

class HorizonCollision(RuntimeError):
    pass

def fetch_horizon(offsets, calendar_map):
    seen = {}
    days = {}
    for d in offsets:
        fixtures = fetch_and_parse(d)
        sig = payload_signature(fixtures)

        if sig in seen:
            raise HorizonCollision(
                f"offset d={d} returned the identical fixture set as "
                f"d={seen[sig]} — the d parameter is not being honoured. "
                f"Halting: any board built from this would be misdated."
            )
        seen[sig] = d
        days[calendar_map[d]] = fixtures
    return days
```

Two distinct days returning byte-identical `match_id` sets is not a
coincidence in football. Treat it as proof the parameter failed and
halt the run. A missed board is recoverable; a board of fixtures that
already kicked off is not.

Additional cheap assertion: the page header text should read "Today"
only for `d=0`. If it reads "Today" on any other offset, halt.

## 4. Rescheduling — what a horizon buys you

`match_id` is stable, so snapshot each horizon pull and diff against
the last. This gives you, for free:

- **Kickoff moved** — same `match_id`, different resolved time
- **Postponed** — status flips to `Postponed`
- **Fixture added** — new `match_id` inside the whitelist
- **Fixture vanished** — `match_id` present yesterday, absent today

The fourth is the one that matters and the one you currently have no
detection for. It's the Bradford v Burnley class of failure: a leg
sitting in a live acca whose fixture quietly moved out from under it.

## 5. Scan horizon vs deploy horizon — separate decisions

These must not be conflated, and I'd hold them apart until you have
evidence.

**Scan horizon: extend to d=+7.** Cheap, informational, no capital
consequence. Fifteen page fetches per run is nothing. Rate-limit
politely — a second between requests, one run per cycle, not a loop.

**Deploy horizon: keep at d=0/d=+1 for now.** Reasons to hold:

- Odds at T-5 are not odds at T-0. The edge you calculate five days
  out is against a provisional line.
- Lineups and injuries are unknown that far ahead, and your model has
  no input for them.
- Booking codes generated days early may expire before you act, and
  the `read_betslip_combined_odds` bug means you can't currently
  verify what a code actually contains.

**But there's a real argument the other way, and it's yours to weigh.**
CLV is measured against the closing line. Betting early is structurally
how positive CLV is generated — you're taking a price before the market
moves to it. Your last recorded CLV was −1.631% across 12/30 legs,
which is negative, and betting close to kickoff is one common cause of
exactly that. A wider deploy horizon might be the fix for your worst
current metric rather than a new risk.

That's a hypothesis, not a finding. The way to settle it is to run the
scan at d=+7, log the price you *would* have taken, and compare it to
the closing line at T-0 for 30 legs. If early entry shows better CLV,
you'll have evidence to widen the deploy horizon. If it doesn't, you've
lost nothing but log space.

Do not widen deploy on the strength of the argument alone.

## 6. Interaction with the scope question

The 9-league whitelist and a 7-day horizon multiply. Nine competitions
across fifteen days is a manageable scan. Sixty-one competitions across
fifteen days is a different object entirely — and every fixture in it
needs odds, which is the feed that's already hitting quota.

Settle scope before switching the horizon on.