import math

def test_prob(name, goals, gp):
    gpg = goals / gp
    # Option 1: Volume penalty
    vol_pen = min(1.0, (gp + 5) / 20.0)
    exp = gpg * vol_pen
    prob1 = (1 - math.exp(-exp)) * 100
    
    # Option 2: Pure Bayesian
    gpg_bayes = (goals + 1.5) / (gp + 10)
    prob2 = (1 - math.exp(-gpg_bayes)) * 100
    
    print(f"{name:15}: GP={gp:2d}, G={goals:2d} | Orig={gpg:.2f} | VolPen={prob1:.1f}% | Bayes={prob2:.1f}%")

test_prob("Barré-Boulet", 1, 1)
test_prob("Barré-Boulet", 1, 2)
test_prob("Average Joe", 3, 10)
test_prob("MacKinnon", 40, 55)
test_prob("McConnor", 10, 15)
