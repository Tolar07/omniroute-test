"""
THROWAWAY cross-check: OLP XDV engine/dixon_coles.py vs RyanSCodes py3 port.

Same training data (2015/16 EPL, all matches before 07/05/2016), same five
out-of-sample fixtures, 1X2 probabilities side by side. B365 proportional
devig included as the market reference.

This is a bug-finding exercise, not a rewrite. Large divergence on a fixture
is a signal to inspect, not a verdict on either model.

Run:  python crosscheck_dc.py   (from this directory)
"""
import csv
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "olp_xdv_agent", "olp_xdv"))
E0 = os.path.join(HERE, "..", "Dixon-Coles-Football-Predictor", "E0.csv")

sys.path.insert(0, REPO)
from data.football_data_source import MatchResult          # noqa: E402
from engine import dixon_coles as olp_dc                   # noqa: E402
import rs_dc_py3                                            # noqa: E402

CUTOFF = "2016-05-07"   # fit on strictly earlier matches
FIXTURES = [   # (home, away, b365h, b365d, b365a)
    ("Swansea", "Man City", 6.00, 4.75, 1.53),     # clear away fav
    ("Man United", "Bournemouth", 1.67, 4.20, 5.25),  # clear home fav
    ("Chelsea", "Leicester", 2.30, 3.75, 3.10),    # balanced, slight home
    ("West Brom", "Liverpool", 2.40, 3.60, 3.00),  # balanced
    ("Stoke", "West Ham", 3.50, 3.60, 2.15),       # away-fav mid
]


def load_rows():
    with open(E0, newline="") as f:
        return list(csv.DictReader(f))


def iso_date(r):
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            from datetime import datetime
            return datetime.strptime(r["Date"], fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(r["Date"])


def b365(r):
    return tuple(float(r[k]) for k in ("B365H", "B365D", "B365A"))


def proportional_devig(odds):
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return tuple(x / s for x in inv)


def olp_1x2(model, home, away):
    """OLP XDV 1X2 from the fitted model's tau-corrected score matrix."""
    lam = model.lambdas(home, away)
    if lam is None:
        return None, None
    mat = olp_dc.score_matrix(lam[0], lam[1], model.rho)
    n = mat.shape[0]
    p_h = float(mat[np.tril_indices(n, -1)].sum())
    p_d = float(np.trace(mat))
    p_a = float(mat[np.triu_indices(n, 1)].sum())
    return (p_h, p_d, p_a), lam


def uniform_nll(rows_tr, lambdas_fn, rho):
    """Model-agnostic negative log-likelihood over the training rows, computed
    from (lambda_home, lambda_away) + rho ONLY — the scoring math. This is the
    apples-to-apples number that separates 'fit is bad' from 'math differs':
    whichever fit is closer to the true MLE has the lower NLL here."""
    from scipy.stats import poisson as sp_poisson
    total = 0.0
    for r in rows_tr:
        lam_h, lam_a = lambdas_fn(r["HomeTeam"], r["AwayTeam"])
        hg, ag = int(r["FTHG"]), int(r["FTAG"])
        tau = olp_dc._dc_tau(hg, ag, lam_h, lam_a, rho)
        total += (sp_poisson.logpmf(hg, lam_h) + sp_poisson.logpmf(ag, lam_a)
                  + math.log(max(tau, 1e-6)))
    return -total


def main():
    rows = load_rows()
    train = [r for r in rows if iso_date(r) < CUTOFF and all(b365(r))]
    print(f"training matches (< {CUTOFF}): {len(train)}  "
          f"(full season {len(rows)})")

    # OLP XDV DC: L-BFGS-B MLE, fits home_adv + rho.
    mr = [MatchResult(league="E0", date=iso_date(r),
                      home_team=r["HomeTeam"], away_team=r["AwayTeam"],
                      fthg=int(r["FTHG"]), ftag=int(r["FTAG"]), ftr=r["FTR"])
          for r in train]
    olp_model = olp_dc.fit(mr)
    print(f"OLP XDV fit: home_adv={olp_model.home_advantage:.4f} "
          f"rho={olp_model.rho:.4f} n_matches={olp_model.n_matches_fit}")

    # RyanSCodes DC: Monte-Carlo hill-climb, home_adv=1.2 rho=0.03 fixed.
    rs_train = [(r["HomeTeam"], r["AwayTeam"], int(r["FTHG"]), int(r["FTAG"]))
                for r in train]
    rs_ability, k = rs_dc_py3.fit(rs_train)
    print(f"RS py3 port fit: {k} cycles (home_adv=1.2 fixed, rho=0.03 fixed)")

    # Model-agnostic NLL: does the divergence come from the FIT or the MATH?
    olp_nll = uniform_nll(train,
                          lambda h, a: olp_model.lambdas(h, a),
                          olp_model.rho)
    rs_nll = uniform_nll(
        train,
        lambda h, a: rs_dc_py3.score_matrix(rs_ability, h, a)[1],
        rs_dc_py3.rho)
    print(f"uniform NLL on training (lower = closer to true MLE): "
          f"OLP={olp_nll:.1f}  RS={rs_nll:.1f}  "
          f"delta={rs_nll - olp_nll:+.1f}")

    # Ability table for the teams in the prediction fixtures.
    involved = sorted({t for (h, a, *_ ) in FIXTURES for t in (h, a)})
    print()
    print("fitted abilities (attack/defence):")
    print(f"{'team':<14} {'OLP log-scale':>16}   {'RS raw mult':>16}")
    for t in involved:
        s = olp_model.teams.get(t)
        olp_s = f"{s.attack:+.2f}/{s.defence:+.2f}" if s else "unrated"
        rs_a = rs_ability[t][0]
        rs_d = rs_ability[t][1]
        print(f"{t:<14} {olp_s:>16}   {rs_a:>7.3f}/{rs_d:<7.3f}")

    print()
    print(f"{'fixture':<32} {'RS [H D A]':>24} {'OLP [H D A]':>24} "
          f"{'|d|max':>7} {'B365 devig':>24}")
    for (h, a, oh, od, oa) in FIXTURES:
        rs_probs, rs_lam = rs_dc_py3.score_matrix(rs_ability, h, a)
        olp_probs, olp_lam = olp_1x2(olp_model, h, a)
        mkt = proportional_devig((oh, od, oa))
        dmax = max(abs(x - y) for x, y in zip(rs_probs, olp_probs)) \
            if olp_probs else float("nan")
        name = f"{h} v {a}"
        print(f"{name:<32} "
              f"{tuple(round(p, 4) for p in rs_probs)!s:>24} "
              f"{tuple(round(p, 4) for p in olp_probs)!s:>24} "
              f"{dmax:>7.3f} "
              f"{tuple(round(p, 3) for p in mkt)!s:>24}")
        print(f"{'':<32} RS lam={rs_lam[0]:.2f}/{rs_lam[1]:.2f}  "
              f"OLP lam={olp_lam[0]:.2f}/{olp_lam[1]:.2f}  "
              f"B365=({oh:.2f}/{od:.2f}/{oa:.2f})")


if __name__ == "__main__":
    main()
