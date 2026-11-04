"""
Avaliação do modelo de gols (Poisson) em janelas crescentes, sem salvar nada.

Dois Poissons (gols do mandante e do visitante), treinados só com o passado de cada
janela. Total de gols ~ Poisson(lh + la), de onde saem Over/Under; o grid de placares
dá casa/empate/fora. Referências: frequência do treino (Over/Under) e Elo logístico
(resultado). Diferença negativa de log loss = melhor que a referência; IC95% por
bootstrap pareado.

Uso:
    python evaluate_poisson.py
"""

from __future__ import annotations

import numpy as np
from scipy.stats import poisson
from sklearn.linear_model import PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from train_baseline import load, pipeline

N_FOLDS, START, N_BOOT, MAX_GOALS = 6, 0.4, 2000, 12
LINES = [1.5, 2.5, 3.5]
ELO = ["elo_diff", "serie_a"]
FULL = ELO + ["home_gf_avg5", "home_ga_avg5", "away_gf_avg5", "away_ga_avg5"]


def pois():
    return make_pipeline(StandardScaler(), PoissonRegressor(alpha=1.0, max_iter=1000))


def over_prob(lh, la, line):
    return 1.0 - poisson.cdf(int(line), lh + la)


def result_probs(lh, la):
    """Colunas na ordem alfabética dos rótulos: A (fora), D (empate), H (casa)."""
    k = np.arange(MAX_GOALS + 1)
    grid = poisson.pmf(k[None, :, None], lh[:, None, None]) * poisson.pmf(k[None, None, :], la[:, None, None])
    home_win = (k[:, None] > k[None, :])
    draw = (k[:, None] == k[None, :])
    p = np.stack([
        (grid * (~home_win & ~draw)).sum(axis=(1, 2)),
        (grid * draw).sum(axis=(1, 2)),
        (grid * home_win).sum(axis=(1, 2)),
    ], axis=1)
    return p / p.sum(axis=1, keepdims=True)


def bin_loss(y, p):
    p = np.clip(p, 1e-9, 1 - 1e-9)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def main() -> None:
    df = load()
    n = len(df)
    hg, ag = df["home_goals"].to_numpy(float), df["away_goals"].to_numpy(float)
    total = hg + ag
    result = df["result"].to_numpy().astype(str)
    classes = np.array(["A", "D", "H"])
    X = {"Elo": df[ELO].to_numpy(float), "completo": df[FULL].to_numpy(float)}
    elo_x = df[["elo_diff"]].to_numpy(float)

    L: dict[str, list] = {}
    mae: dict[str, list] = {}
    edges = np.linspace(int(n * START), n, N_FOLDS + 1).astype(int)

    for e0, e1 in zip(edges[:-1], edges[1:]):
        te = slice(e0, e1)
        m = e1 - e0
        lam = {"constante": (np.full(m, hg[:e0].mean()), np.full(m, ag[:e0].mean()))}
        for name, Xn in X.items():
            lh = pois().fit(Xn[:e0], hg[:e0]).predict(Xn[te])
            la = pois().fit(Xn[:e0], ag[:e0]).predict(Xn[te])
            lam[name] = (lh, la)

        for line in LINES:
            y = (total[te] > line).astype(float)
            L.setdefault(f"over{line} prior", []).append(bin_loss(y, np.full(m, (total[:e0] > line).mean())))
            for name, (lh, la) in lam.items():
                L.setdefault(f"over{line} {name}", []).append(bin_loss(y, over_prob(lh, la, line)))

        yi = np.searchsorted(classes, result[te])
        prior = np.array([(result[:e0] == c).mean() for c in classes])
        L.setdefault("resultado prior", []).append(-np.log(np.tile(prior, (m, 1))[np.arange(m), yi]))
        logit = pipeline(1.0).fit(elo_x[:e0], result[:e0])
        assert list(logit.classes_) == list(classes)
        L.setdefault("resultado Elo logístico", []).append(-np.log(np.clip(logit.predict_proba(elo_x[te])[np.arange(m), :][np.arange(m), yi], 1e-9, 1)))
        for name, (lh, la) in lam.items():
            p = result_probs(lh, la)
            L.setdefault(f"resultado Poisson {name}", []).append(-np.log(np.clip(p[np.arange(m), yi], 1e-9, 1)))

        for name, (lh, la) in lam.items():
            mae.setdefault(name, []).append(np.abs(total[te] - (lh + la)))

    A = {k: np.concatenate(v) for k, v in L.items()}
    m_all = len(next(iter(A.values())))
    idx = np.random.default_rng(0).integers(0, m_all, size=(N_BOOT, m_all))

    def diff(a, b):
        d = A[a] - A[b]
        lo, hi = np.percentile(d[idx].mean(axis=1), [2.5, 97.5])
        flag = "" if lo > 0 or hi < 0 else "  (IC inclui 0: sem evidência de diferença)"
        return f"{d.mean():+.4f}  IC95% [{lo:+.4f}, {hi:+.4f}]{flag}"

    print(f"{m_all} jogos previstos em {N_FOLDS} janelas (cada um previsto só com o passado)\n")
    for line in LINES:
        print(f"=== Over/Under {line} ===")
        for k in (f"over{line} prior", f"over{line} constante", f"over{line} Elo", f"over{line} completo"):
            print(f"  log loss {k.split(' ', 1)[1]:<10}{A[k].mean():.4f}")
        for name in ("constante", "Elo", "completo"):
            print(f"  {name} - prior: {diff(f'over{line} {name}', f'over{line} prior')}")
        print()

    print("=== Resultado (casa/empate/fora) ===")
    for k in ("resultado prior", "resultado Elo logístico", "resultado Poisson constante", "resultado Poisson Elo", "resultado Poisson completo"):
        print(f"  log loss {k.replace('resultado ', ''):<22}{A[k].mean():.4f}")
    for name in ("Elo", "completo"):
        print(f"  Poisson {name} - Elo logístico: {diff(f'resultado Poisson {name}', 'resultado Elo logístico')}")
    print()

    print("=== Erro médio absoluto do total de gols (MAE) ===")
    for name, v in mae.items():
        print(f"  {name:<10}{np.concatenate(v).mean():.4f}")


if __name__ == "__main__":
    main()
