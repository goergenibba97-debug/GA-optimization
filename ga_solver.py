"""Genetic algorithm for the two-echelon capacitated warehouse location problem.

Chromosome  : binary vector y (y_i = 1 -> warehouse i is open)
Fitness     : fixed costs + optimal transport cost for that open set
              (flows x_ki and z_ij are obtained from a small LP, so every
              chromosome is evaluated at its best possible routing)
Operators   : tournament selection, uniform crossover, bit-flip mutation,
              elitism, capacity-repair operator.
"""
import itertools
import time
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import linprog

PENALTY = 1e12


@dataclass
class Data:
    sup_names: list
    cus_names: list
    wh_names: list
    O: np.ndarray      # supplier capacity   (K)
    R: np.ndarray      # customer demand     (J)
    F: np.ndarray      # warehouse fixed cost (I)
    Cap: np.ndarray    # warehouse capacity  (I)
    C: np.ndarray      # supplier -> warehouse unit cost (K x I)
    D: np.ndarray      # warehouse -> customer unit cost (I x J)


def load_excel(file) -> Data:
    sup = pd.read_excel(file, sheet_name="Suppliers")
    cus = pd.read_excel(file, sheet_name="Customers")
    wh = pd.read_excel(file, sheet_name="Warehouses")
    C = pd.read_excel(file, sheet_name="Cost_Supplier_Warehouse", index_col=0)
    D = pd.read_excel(file, sheet_name="Cost_Warehouse_Customer", index_col=0)
    d = Data(sup.iloc[:, 0].astype(str).tolist(), cus.iloc[:, 0].astype(str).tolist(),
             wh.iloc[:, 0].astype(str).tolist(),
             sup.iloc[:, 1].to_numpy(float), cus.iloc[:, 1].to_numpy(float),
             wh.iloc[:, 1].to_numpy(float), wh.iloc[:, 2].to_numpy(float),
             C.to_numpy(float), D.to_numpy(float))
    K, I, J = len(d.O), len(d.F), len(d.R)
    if d.C.shape != (K, I):
        raise ValueError(f"Cost_Supplier_Warehouse must be {K}x{I}, got {d.C.shape}")
    if d.D.shape != (I, J):
        raise ValueError(f"Cost_Warehouse_Customer must be {I}x{J}, got {d.D.shape}")
    if d.O.sum() < d.R.sum():
        raise ValueError("Total supply is lower than total demand: infeasible.")
    if d.Cap.sum() < d.R.sum():
        raise ValueError("Total warehouse capacity is lower than total demand: infeasible.")
    return d


def route(y, d: Data):
    """Optimal flows for a fixed open set. Returns (transport_cost, x, z) or None."""
    idx = np.flatnonzero(y)
    m, K, J, I = len(idx), len(d.O), len(d.R), len(d.F)
    if m == 0 or d.Cap[idx].sum() < d.R.sum():
        return None
    nx, nz = K * m, m * J
    c = np.concatenate([d.C[:, idx].ravel(), d.D[idx, :].ravel()])
    A_ub = np.zeros((K + m, nx + nz)); b_ub = np.concatenate([d.O, d.Cap[idx]])
    for k in range(K):
        A_ub[k, k * m:(k + 1) * m] = 1
    for a in range(m):
        A_ub[K + a, nx + a * J: nx + (a + 1) * J] = 1
    A_eq = np.zeros((J + m, nx + nz)); b_eq = np.concatenate([d.R, np.zeros(m)])
    for a in range(m):
        for j in range(J):
            A_eq[j, nx + a * J + j] = 1
        for k in range(K):
            A_eq[J + a, k * m + a] = 1
        A_eq[J + a, nx + a * J: nx + (a + 1) * J] = -1
    res = linprog(c, A_ub=A_ub, b_ub=b_ub, A_eq=A_eq, b_eq=b_eq, bounds=(0, None), method="highs")
    if not res.success:
        return None
    x = np.zeros((K, I)); z = np.zeros((I, J))
    x[:, idx] = res.x[:nx].reshape(K, m)
    z[idx, :] = res.x[nx:].reshape(m, J)
    return res.fun, x, z


class Evaluator:
    def __init__(self, d):
        self.d, self.cache = d, {}

    def __call__(self, y):
        key = tuple(int(v) for v in y)
        if key not in self.cache:
            r = route(np.array(key), self.d)
            self.cache[key] = PENALTY if r is None else float(self.d.F @ np.array(key) + r[0])
        return self.cache[key]


def repair(y, d, rng):
    y = y.copy()
    if y.sum() == 0:
        y[rng.integers(len(y))] = 1
    while d.Cap[y == 1].sum() < d.R.sum():
        y[rng.choice(np.flatnonzero(y == 0))] = 1
    return y


def run_ga(d: Data, pop_size=30, generations=40, p_cx=0.85, p_mut=0.08,
           tournament=3, elite=2, seed=42, progress=None):
    rng = np.random.default_rng(seed)
    I = len(d.F)
    ev = Evaluator(d)
    pop = [repair(rng.integers(0, 2, I), d, rng) for _ in range(pop_size)]
    hist, t0 = [], time.time()
    for g in range(generations + 1):
        fit = np.array([ev(ind) for ind in pop])
        b = int(fit.argmin())
        hist.append(dict(generation=g, best=fit[b], mean=fit[fit < PENALTY].mean(),
                         worst=fit[fit < PENALTY].max(), open="".join(map(str, pop[b]))))
        if progress:
            progress(g / generations, hist[-1])
        if g == generations:
            break
        order = np.argsort(fit)
        new = [pop[i].copy() for i in order[:elite]]
        while len(new) < pop_size:
            pick = lambda: pop[min(rng.integers(0, pop_size, tournament), key=lambda i: fit[i])]
            p1, p2 = pick(), pick()
            if rng.random() < p_cx:
                mask = rng.random(I) < 0.5
                c1, c2 = np.where(mask, p1, p2), np.where(mask, p2, p1)
            else:
                c1, c2 = p1.copy(), p2.copy()
            for c in (c1, c2):
                flip = rng.random(I) < p_mut
                c[flip] = 1 - c[flip]
                new.append(repair(c, d, rng))
        pop = new[:pop_size]
    fit = np.array([ev(i) for i in pop])
    best = pop[int(fit.argmin())]
    cost_t, x, z = route(best, d)
    return dict(y=best, total=float(d.F @ best + cost_t), fixed=float(d.F @ best),
                upstream=float((d.C * x).sum()), downstream=float((d.D * z).sum()),
                x=x, z=z, history=pd.DataFrame(hist), evaluations=len(ev.cache),
                seconds=time.time() - t0)


def brute_force(d: Data):
    """Exact optimum by enumerating all 2^I open sets (only for small I)."""
    ev = Evaluator(d)
    return min(ev(np.array(y)) for y in itertools.product([0, 1], repeat=len(d.F)))
