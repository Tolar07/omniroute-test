"""
THROWAWAY py3 port of RyanSCodes/Dixon-Coles-Football-Predictor.

Cross-check only (bug-finding exercise, NOT a model we adopt):
  * Monte-Carlo hill-climb fit (stochastic) vs our L-BFGS-B MLE.
  * home_adv = 1.2 FIXED, rho = 0.03 FIXED (hardcoded upstream).
  * No decay (upstream comment).
  * raw-multiplier abilities (attack ~ 1, defence ~ 1) — NOT log-scale.

Mechanical py3 fixes applied:
  * print stmt -> print()
  * df.as_matrix() -> df.values
  * np.datetime64 arithmetic -> timedelta64('D')
  * random.seed() added for reproducibility (upstream had none)
  * rdiff tolerance relaxed 1e-9 -> 1e-7 + cycle cap (throwaway speed)

Scoring math kept byte-for-byte identical to upstream DC_Functions.py +
DC_Football_Predictor.py so divergences vs OLP XDV are attributable to the
FIT/parameters, not to a translation slip.
"""
import random
import math
import numpy as np

home_adv = 1.2
rho = 0.03

# teams = 2015/16 EPL (from upstream E0.csv listing)
teams = ["Arsenal", "Aston Villa", "Bournemouth", "Chelsea", "Crystal Palace",
         "Everton", "Leicester", "Liverpool", "Man City", "Man United",
         "Newcastle", "Norwich", "Southampton", "Stoke", "Sunderland", "Swansea",
         "Tottenham", "Watford", "West Brom", "West Ham"]


def poisson(m, n):
    p = math.exp(-m)
    r = [p]
    for i in range(1, n):
        p *= m / float(i)
        r.append(p)
    return r


def tau_matrix(home_mean, away_mean, home_goals, away_goals):
    if home_goals == 0 and away_goals == 0:
        return 1.0 - home_mean * away_mean * rho
    elif home_goals == 0 and away_goals == 1:
        return 1.0 + home_mean * rho
    elif home_goals == 1 and away_goals == 0:
        return 1.0 + away_mean * rho
    elif home_goals == 1 and away_goals == 1:
        return 1.0 - rho
    else:
        return 1.0


def log_likelihood(matches, ability_dict):
    """matches: list of (home_team, away_team, fthg, ftag)."""
    total = 0.0
    for (home_team, away_team, home_goals, away_goals) in matches:
        home_mean = home_adv * ability_dict[home_team][0] * ability_dict[away_team][1]
        away_mean = ability_dict[away_team][0] * ability_dict[home_team][1]
        home_dist = poisson(home_mean, home_goals + 1)
        away_dist = poisson(away_mean, away_goals + 1)
        tau = tau_matrix(home_mean, away_mean, home_goals, away_goals)
        total += (math.log(home_dist[home_goals]) + math.log(away_dist[away_goals])
                  + math.log(tau))
    return total


def monte_carlo_opt(log_like, ability_dict, matches, max_cycles=2000,
                    tol=1e-7):
    """Upstream hill-climb, delta=0.1 random walk, one param at a time."""
    delta = 0.1
    conv = []
    k = 0
    rdiff = 1.0
    while rdiff > tol and k < max_cycles:
        for key in sorted(ability_dict.keys()):
            j = 0
            if random.random() > 0.5:
                j = 1
            disp = delta * (random.random() - 0.5)
            ability_dict[key][j] += disp
            if ability_dict[key][j] > 0:
                trial = log_likelihood(matches, ability_dict)
                if trial < log_like:
                    ability_dict[key][j] -= disp
                else:
                    rdiff = abs((trial - log_like) / log_like)
                    log_like = trial
            else:
                ability_dict[key][j] -= disp
        conv.append(log_like)
        k += 1
    return ability_dict, conv, k


def fit(matches, seed=123):
    """Fit on (home_team, away_team, fthg, ftag) tuples. Returns ability_dict."""
    random.seed(seed)
    ability_dict = {}
    for team in teams:
        ability_dict[team] = [random.random(), random.random()]
    log_like = log_likelihood(matches, ability_dict)
    ability_dict, conv, k = monte_carlo_opt(log_like, ability_dict, matches)
    return ability_dict, k


def score_matrix(ability_dict, home, away, size=10):
    """1X2 probs for a fixture, matching upstream 10x10 tau-scaled grid."""
    home_mean = home_adv * ability_dict[home][0] * ability_dict[away][1]
    away_mean = ability_dict[away][0] * ability_dict[home][1]
    home_dist = poisson(home_mean, size)
    away_dist = poisson(away_mean, size)
    d = np.zeros((size, size))
    for i in range(size):
        for j in range(size):
            d[i, j] = tau_matrix(home_mean, away_mean, i, j) * home_dist[i] * away_dist[j]
    total = d.sum()
    d /= total
    home_win = float(sum(d[i, j] for i in range(size) for j in range(size) if i > j))
    draw = float(sum(d[i, j] for i in range(size) for j in range(size) if i == j))
    away_win = float(sum(d[i, j] for i in range(size) for j in range(size) if i < j))
    return (home_win, draw, away_win), (home_mean, away_mean)
