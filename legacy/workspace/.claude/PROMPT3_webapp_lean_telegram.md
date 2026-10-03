# Prompt for Claude Code — Web app IS the Telegram output; pause the admin tier

Paste this to Claude Code as-is.

---

I want the web app to be **the Telegram board** — the same lean PRODUCTION BETS output I get on my phone (★ Acca A — HEADLINE, each leg `fixture (league) — market @ price`, `Combined X.XX · Booking code: CODE`, singles each with their own booking code), including the booking codes. **The production pipeline that renders Telegram is the feed for the web app** — one render, two outlets, the web can never drift from what Telegram delivers. And I want the admin web app paused.

Read `CLAUDE.md` (working protocol) and `docs/OLP_XDV_MASTER_DOCUMENTATION_2026-08-11.md` fully before touching anything. Follow the safe-move protocol (git status/log first, combine, commit with `--only`, `Co-Authored-By: Claude <noreply@anthropic.com>`).

Do this in steps. Don't skip to a later step before finishing the earlier one.

## STEP 1 — Audit before touching anything

Map the current production render path and the booking-code data path, and report before editing:

1. **The Telegram production path.** Read `output/produce_bet.py` (`render_telegram_board`, which appends `render_production_block`) and `engine/acca.py::render_production_block`. That is the exact output I want on the web: `★ Acca A — HEADLINE, N legs`, one line per leg `fixture (league) — market @ price`, `Combined X.XX · Booking code: CODE`, then the `SINGLES — one standalone slip each, own booking code` block, and an honest `NO production pick today` when nothing eligible (HR35 — never fabricate).
2. **Which webapp renderer is live.** The server has two — `webapp/render.py` (legacy) and `webapp/render_v2.py` (new prototype). Confirm which `webapp/server.py` serves for `/dashboard` and `/admin`, and what each does with the production output today.
3. **Why booking codes don't reach either surface today.** Logs show codes WERE captured on 2026-08-11 (`Acca A: BOOKED — CODE M5LMFE` at 16:59) but Telegram and the web both show `NO DATA — PENDING`. Trace it: codes are written to `output/boards/acca_<date>_codes.json` by `booking/booking_codes.py`, then a later run that fell back to MANUAL cleaned/replaced that file so the captured code was lost. Confirm the stale-codes mechanism in `run_daily.py` and report exactly why a good capture can be erased.
4. **What "pause the admin web app" touches.** Enumerate the `/admin` routes, admin-only endpoints, and the `Approve → Publish` action in `webapp/server.py`/`webapp/schema.py`. Flag explicitly anything that is a protected constant per CLAUDE.md (ARCHITECT_SIGNOFF, client-publish gating, `trim_payload` data-leak boundary, the ≥30-legs/positive-CLV gate) — those stay untouched unless I explicitly order otherwise. Report, don't silently remove.

## STEP 2 — The Telegram production feeds the web (one render, two outlets)

1. **The web page is the Telegram board, not a second design.** The web serves the daily Telegram board output — the same render the push delivers — mapped to HTML. The production block, the scan, the honest-edge/capital line: everything the Telegram message carries is on the page, byte-faithful. **No second renderer, no re-derivation.** If it isn't in the Telegram output, it isn't on the web page.
2. **One render call, both outlets.** Refactor so the daily production render (the one that builds the Telegram message) is the single source the web reads. The production block + booking codes on the web come from that exact call — so web == Telegram structurally, and the two can never disagree about today's picks or codes.
3. **Booking codes ride the same path.** Because codes are generated before render (so they reach the Telegram push), feeding the push to the web carries them too. Keep and fix the persistence gap from Step 1 — a good capture (like M5LMFE) must survive a later MANUAL regen run. Where a code is genuinely absent, render `NO DATA — PENDING` (HR35 — never fabricate). This is a code fix, not a workaround, and it fixes both surfaces at once.
4. **Keep the honesty.** The honest-edge/capital line stays on the page (it's in the Telegram envelope — carry it). Verify the page carries no model internals (Elo/xG/consensus/EV/verification) — the Telegram board is already lean, so the boundary holds by construction; confirm it.

## STEP 3 — Pause the admin tier

1. Stop serving `/admin`, the admin-only API endpoints, and internal pages (`/stats`, `/why` if admin-only) — the admin web app is paused.
2. The Telegram-fed board becomes the web's one surface (still on `0.0.0.0:8088`, phone-first).
3. **Flag, don't decide:** with `/admin` gone there is no `Approve → Publish` button, and the web is fed by the same production that feeds Telegram. Tell me plainly what this means for publish: the daily run already auto-delivers to Telegram — does it now equally feed the web (auto-publish in effect), or is the web gated separately? Do NOT change `ARCHITECT_SIGNOFF`, the CLV publish gate, or the trim boundary as a side effect — those are mine. If the Telegram feed is the publish path, confirm the override/gate numbers are still stamped honestly (never silent).

## WHAT I ACTUALLY WANT

A web app that is, visually and in content, the Telegram board I already trust — same lean production block with booking codes, same honest `NO DATA — PENDING` where a code or pick is genuinely missing — with the admin tier turned off. One production render feeding Telegram and the web. When you're done, show me the live rendered page side-by-side with the Telegram output for the same date.

## VERIFICATION (run all before reporting done)

- **Same-output proof:** for a given date, the served web page must contain the same production-block text as the Telegram board — compare them, don't eyeball it.
- Webapp suites: `webapp_schema_test`, `webapp_render_test`, `webapp_server_test`, `webapp_export_test`, `webapp_produce_test` (use `PYTHONIOENCODING=utf-8 py -3.12 tests/<name>.py`, source `.env` for env-dependent ones).
- The booking-code persistence fix: prove a captured code survives a MANUAL fallback run, and that the code then appears on BOTH the Telegram render and the web page.
- Live check: curl `/dashboard/2026-08-11` and confirm the lean production block + a booking-code line render, and that `/admin` no longer serves.
- `git status --short` + `git log --oneline -5` before and after; commit only the intended paths.
