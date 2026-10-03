# Prompt for Claude Code — Remove Blockers to Going Live

Paste this to Claude Code as-is.

---

I want to go live. Paper-only calibration isn't cutting it — the system needs to run live to actually learn. I want you to find and remove every blocker currently preventing the framework from going live, end to end.

Do this in two steps. Don't skip to step 2 without finishing step 1.

## STEP 1 — Full blocker audit, report before touching anything

Go through the entire pipeline — scan, trigger generation, production, publish — and list every gate, flag, or condition that stops output at each stage. For each one, tell me:

- What it's called in code and where it lives
- What exactly it blocks (generation? publish? something else?)
- What triggers it to lift (a count, a threshold, a manual flag, something else?)
- Current status right now (met / not met, and by how much)

I already know one of these from the admin dashboard: **Approve → Publish to Client** is blocked on `12/30 legs with CLV (need ≥30); mean CLV -1.631 (must be positive); ARCHITECT_SIGNOFF=1`. Confirm this one and find any others — including anything not visible on the admin screen.

## STEP 2 — For each blocker found, tell me what removing it actually does

Don't just remove things. For every blocker in the Step 1 list, tell me plainly:

- If I remove/bypass it, what changes in practice — what starts happening that wasn't happening before?
- Who is affected — just me, or does it change what clients see?
- Is there a reason this gate exists that I should know before I override it?

**Flag explicitly:** if any blocker is protecting something other than my own capital — for example, the client-publish gate, which stands between the current system (mean CLV -1.631%, i.e. currently losing to the closing line) and anything a paying client would see — call that out clearly as its own category before I confirm removal. I'm not asking you to leave it blocked forever; I'm asking you not to fold "stop showing me my own test data" and "stop showing clients a system with unproven edge" into one silent removal.

## WHAT I ACTUALLY WANT LIVE

Full trigger generation, running continuously, using live odds and real timing, logged against real closing lines — this is the live calibration I want instead of paper. Capital deployment and client publish are separate decisions I'll make explicitly once I see Step 1 and Step 2 laid out. Don't auto-enable either of those as a side effect of "going live."
