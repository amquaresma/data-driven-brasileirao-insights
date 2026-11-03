"""
Avaliação em janelas crescentes (rolling origin): cada jogo dos últimos 60% é previsto
por um modelo treinado só com o passado. Bootstrap pareado (2000 reamostragens) dá o
intervalo de 95% da diferença de log loss. Diferença negativa = melhor que a referência.

Uso:
    python evaluate_rolling.py
"""

from __future__ import annotations

import numpy as np

from train_baseline import GOALS_FEATURES, RESULT_FEATURES, load, pipeline

N_FOLDS, START, N_BOOT = 6, 0.4, 2000


def per_match_logloss(y, proba, classes):
    idx = np.searchsorted(classes, y)
    return -np.log(np.clip(proba[np.arange(len(y)), idx], 1e-12, 1.0))


def evaluate(title, df, y, features, elo_only=None):
    n = len(df)
    classes = np.unique(y)
    X = df[features].to_numpy(float)
    all_cols = list(range(len(features)))
    specs = [("completo C=0.01", all_cols, 0.01), ("completo C=0.1", all_cols, 0.1)]
    if elo_only:
        specs.insert(0, ("Elo puro", [features.index(f) for f in elo_only], 1.0))

    losses: dict[str, list] = {}
    edges = np.linspace(int(n * START), n, N_FOLDS + 1).astype(int)
    for e0, e1 in zip(edges[:-1], edges[1:]):
        ytr, yte = y[:e0], y[e0:e1]
        prior = np.array([(ytr == c).mean() for c in classes])
        losses.setdefault("prior", []).append(per_match_logloss(yte, np.tile(prior, (len(yte), 1)), classes))
        for name, cols, C in specs:
            model = pipeline(C).fit(X[:e0][:, cols], ytr)
            assert list(model.classes_) == list(classes)
            losses.setdefault(name, []).append(per_match_logloss(yte, model.predict_proba(X[e0:e1][:, cols]), classes))

    L = {k: np.concatenate(v) for k, v in losses.items()}
    m = len(L["prior"])
    idx = np.random.default_rng(0).integers(0, m, size=(N_BOOT, m))

    def diff(a, b):
        d = L[a] - L[b]
        lo, hi = np.percentile(d[idx].mean(axis=1), [2.5, 97.5])
        return d.mean(), lo, hi

    print(f"\n=== {title} | {m} jogos previstos, {N_FOLDS} janelas ===")
    for k, v in L.items():
        print(f"  log loss {k:<18}{v.mean():.4f}")
    pairs = [(k, "prior") for k in L if k != "prior"]
    if "Elo puro" in L:
        pairs += [(k, "Elo puro") for k in L if k.startswith("completo")]
    for a, b in pairs:
        mean, lo, hi = diff(a, b)
        flag = "" if lo > 0 or hi < 0 else "  (IC inclui 0: sem evidência de diferença)"
        print(f"  {a} - {b}: {mean:+.4f}  IC95% [{lo:+.4f}, {hi:+.4f}]{flag}")


if __name__ == "__main__":
    df = load()
    evaluate("Resultado", df, df["result"].to_numpy().astype(str), RESULT_FEATURES, elo_only=["elo_diff"])
    evaluate("Over 2.5 gols", df, df["over_2_5"].astype(int).to_numpy(), GOALS_FEATURES)
