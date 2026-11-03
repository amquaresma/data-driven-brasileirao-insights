"""
Baseline de ML (só avaliação, não salva modelo): resultado (H/D/A) e Over 2.5.

Split TEMPORAL: 60% mais antigos = treino, 20% = validação (escolhe C), 20% mais
recentes = teste. Nunca embaralha. Compara com baselines (frequência do treino e
Elo puro). Métricas de probabilidade: log loss e Brier (menor é melhor).

Uso:
    python train_baseline.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from infrastructure.supabase import get_supabase_client

PAGE = 1000
C_GRID = [0.01, 0.03, 0.1, 0.3, 1.0]
NUMERIC = [
    "elo_diff", "home_elo", "away_elo", "home_form", "away_form",
    "home_gf_avg5", "away_gf_avg5", "home_ga_avg5", "away_ga_avg5",
    "home_pts_avg5", "away_pts_avg5", "home_rest_days", "away_rest_days",
]
RESULT_FEATURES = ["elo_diff", "form_diff", "pts_diff", "gd_diff", "rest_diff", "serie_a"]
GOALS_FEATURES = ["home_att_vs_def", "away_att_vs_def", "serie_a"]


def load() -> pd.DataFrame:
    client = get_supabase_client()
    codes = {
        c["id"]: c["code"]
        for c in client.table("competitions").select("id, code").in_("code", ["a", "b"]).execute().data
    }
    rows, offset = [], 0
    while True:
        page = (
            client.table("match_features").select("*").eq("min_history_ok", True)
            .order("match_date").order("match_id").range(offset, offset + PAGE - 1).execute().data
        )
        rows += page
        if len(page) < PAGE:
            break
        offset += PAGE

    df = pd.DataFrame(rows)
    df = df[df["competition_id"].isin(codes)].copy()
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["serie_a"] = (df["competition_id"].map(codes) == "a").astype(int)
    df["match_date"] = pd.to_datetime(df["match_date"])

    df["form_diff"] = df.home_form - df.away_form
    df["pts_diff"] = df.home_pts_avg5 - df.away_pts_avg5
    df["gd_diff"] = (df.home_gf_avg5 - df.home_ga_avg5) - (df.away_gf_avg5 - df.away_ga_avg5)
    df["rest_diff"] = (df.home_rest_days - df.away_rest_days).clip(-7, 7)
    df["home_att_vs_def"] = df.home_gf_avg5 + df.away_ga_avg5
    df["away_att_vs_def"] = df.away_gf_avg5 + df.home_ga_avg5

    needed = sorted(set(RESULT_FEATURES + GOALS_FEATURES))
    df = df.dropna(subset=needed)
    return df.sort_values(["match_date", "match_id"]).reset_index(drop=True)


def brier(y, proba, classes) -> float:
    onehot = (y[:, None] == classes[None, :]).astype(float)
    if len(classes) == 2:
        return float(((proba[:, 1] - onehot[:, 1]) ** 2).mean())
    return float(((proba - onehot) ** 2).sum(axis=1).mean())


def pipeline(C: float):
    return make_pipeline(StandardScaler(), LogisticRegression(C=C, max_iter=2000))


def run(title: str, df: pd.DataFrame, y: np.ndarray, features: list[str], positive, elo_only=None) -> None:
    n = len(df)
    i1, i2 = int(n * 0.6), int(n * 0.8)
    tr, va, te, trva = slice(0, i1), slice(i1, i2), slice(i2, n), slice(0, i2)
    classes = np.unique(y)
    X = df[features].to_numpy(float)
    cols = list(range(len(features)))

    def fit(c, C, rows):
        return pipeline(C).fit(X[rows][:, c], y[rows])

    best_C = min(
        C_GRID,
        key=lambda C: log_loss(y[va], fit(cols, C, tr).predict_proba(X[va][:, cols]), labels=classes),
    )

    preds = {}
    prior = np.array([(y[trva] == c).mean() for c in classes])
    preds["prior (freq. do treino)"] = np.tile(prior, (n - i2, 1))
    if elo_only:
        ecols = [features.index(f) for f in elo_only]
        preds["Elo puro"] = fit(ecols, 1.0, trva).predict_proba(X[te][:, ecols])
    full = fit(cols, best_C, trva)
    preds[f"completo (C={best_C})"] = full.predict_proba(X[te][:, cols])

    y_te = y[te]
    print(f"\n=== {title} | treino {i1}, validação {i2 - i1}, teste {n - i2} ===")
    print(f"período do teste: {df.match_date.iloc[i2].date()} a {df.match_date.iloc[-1].date()}")
    print(f"{'modelo':<28}{'logloss':>9}{'brier':>8}{'acc':>7}")
    for name, p in preds.items():
        acc = (classes[p.argmax(axis=1)] == y_te).mean()
        print(f"{name:<28}{log_loss(y_te, p, labels=classes):>9.4f}{brier(y_te, p, classes):>8.4f}{acc:>7.1%}")
    print(f"erro-padrão máximo da acurácia no teste: ±{50 / np.sqrt(n - i2):.1f} pp")

    pos_idx = list(classes).index(positive)
    p_pos = preds[f"completo (C={best_C})"][:, pos_idx]
    cal = pd.DataFrame({"pred": p_pos, "obs": (y_te == positive).astype(float)})
    cal["faixa"] = pd.qcut(cal["pred"], 4, duplicates="drop")
    print(f"calibração de P({positive}) no teste:")
    print(cal.groupby("faixa", observed=True).agg(previsto=("pred", "mean"), observado=("obs", "mean"), n=("pred", "size")).round(3).to_string())

    coef = full[-1].coef_
    print("pesos (features padronizadas):")
    for row, label in zip(coef if len(classes) > 2 else coef[:1], classes if len(classes) > 2 else [positive]):
        print(f"  {label}: " + ", ".join(f"{f}={w:+.2f}" for f, w in zip(features, row)))


if __name__ == "__main__":
    df = load()
    print(f"{len(df)} jogos com histórico mínimo (A e B, 2026)")
    run("Resultado (A=fora, D=empate, H=mandante)", df, df["result"].to_numpy(), RESULT_FEATURES, "H", elo_only=["elo_diff"])
    run("Over 2.5 gols", df, df["over_2_5"].astype(int).to_numpy(), GOALS_FEATURES, 1)
