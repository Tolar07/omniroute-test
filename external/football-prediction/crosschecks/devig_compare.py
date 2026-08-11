"""
THROWAWAY comparison: OLP XDV's proportional devig vs penaltyblog's 7 methods.

OLP XDV engine/markets.py::implied_1x2 uses PROPORTIONAL devig
p_i = (1/odds_i) / sum(1/odds_j)  —  which is EXACTLY penaltyblog's
MULTIPLICATIVE method (verified: same formula, same output).

So the question is not "which method is ours" but "how far is proportional
from the alternatives, and on WHICH lines?"  Literature (Shin 1992/93, Clarke
2016, and the de-vig literature generally): on longshot-heavy lines with fat
overrounds, multiplicative OVERSTATES the favourite and UNDERSTATES the
longshot; Shin and the log/odds-ratio families move probability the other way.

Lines are real B365 closing odds from E0.csv 2015/16 (the cross-check season).
Run: python devig_compare.py
"""
import sys
import os
import numpy as np

from pb_implied.implied import calculate_implied

LINES = [
    ("Swansea v Man City (B365, 15/05/16)", (6.00, 4.75, 1.53)),
    ("Man United v Bournemouth (B365, 17/05/16)", (1.67, 4.20, 5.25)),
    ("Stoke v West Ham (B365, 15/05/16)", (3.50, 3.60, 2.15)),
    ("Chelsea v Leicester (B365, 15/05/16)", (2.30, 3.75, 3.10)),
    ("Arsenal v Aston Villa (B365, 15/05/16)", (1.17, 9.00, 17.00)),
]

METHODS = ["multiplicative", "additive", "power", "shin",
           "differential_margin_weighting", "odds_ratio", "logarithmic"]


def proportional(odds):
    inv = [1.0 / o for o in odds]
    s = sum(inv)
    return tuple(x / s for x in inv)


def main():
    print("method spread per line, home/draw/away implied probs:")
    print()
    for label, odds in LINES:
        inv_sum = sum(1.0 / o for o in odds)
        margin = inv_sum - 1.0
        rows = {m: tuple(round(p, 4) for p in calculate_implied(list(odds),
                                                                method=m).probabilities)
                for m in METHODS}
        # longshot = the most extreme price (max odd) -> its method spread
        ls_idx = int(np.argmax(odds))
        spread = max(rows[m][ls_idx] for m in METHODS) - \
            min(rows[m][ls_idx] for m in METHODS)
        print(f"{label}  (overround {margin*100:.1f}%)")
        print(f"  proportional (OLP XDV, == multiplicative): "
              f"{tuple(round(p,4) for p in proportional(odds))}")
        for m in METHODS:
            mark = "  <-- OLP XDV" if m == "multiplicative" else ""
            print(f"    {m:>28}: {rows[m]}{mark}")
        print(f"  >>> method spread on the longshot (odd={odds[ls_idx]:.2f}): "
              f"{spread*100:.2f}pp"
              f"  [multiplicative={rows['multiplicative'][ls_idx]*100:.1f}% vs "
              f"shin={rows['shin'][ls_idx]*100:.1f}%]")
        print()


if __name__ == "__main__":
    main()
