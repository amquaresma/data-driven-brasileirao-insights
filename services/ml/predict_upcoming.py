"""
Previsões (casa/empate/fora) dos jogos ainda não disputados das Séries A e B.

Modelo "elo-logit-v1": regressão logística multinomial sobre a diferença de Elo
(o "Elo puro" da avaliação em janelas crescentes), treinada com todos os jogos
finalizados de match_features. O Elo de cada time vem de TODOS os jogos finalizados
até hoje, em ordem cronológica.

Cada previsão guarda versão do modelo e data, para medir a calibração depois.

Uso:
    python predict_upcoming.py
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

# Reaproveita os cálculos do serviço de analytics (o do ml vem primeiro no path).
sys.path.append(str(Path(__file__).resolve().parents[1] / "analytics"))

from calculations.elo import INITIAL_RATING, EloMatchInput, compute_elo_ratings  # noqa: E402
from compute_match_features import fetch_matches  # noqa: E402
from infrastructure.supabase import get_supabase_client  # noqa: E402
from train_baseline import load, pipeline  # noqa: E402
from scipy.stats import poisson  # noqa: E402
from sklearn.linear_model import PoissonRegressor  # noqa: E402
from sklearn.pipeline import make_pipeline  # noqa: E402
from sklearn.preprocessing import StandardScaler  # noqa: E402

MODEL_VERSION = "elo-logit-v1"
GOALS_FEATURES = ["elo_diff", "serie_a"]  # mesmas do 'Elo' em evaluate_poisson.py


def main() -> None:
    client = get_supabase_client()

    df = load()
    model = pipeline(1.0).fit(df[["elo_diff"]].to_numpy(float), df["result"].to_numpy().astype(str))
    classes = list(model.classes_)
    print(f"Modelo {MODEL_VERSION} treinado com {len(df)} jogos finalizados.")

    gx = df[GOALS_FEATURES].to_numpy(float)
    fit = lambda y: make_pipeline(StandardScaler(), PoissonRegressor(alpha=1.0, max_iter=1000)).fit(gx, y)
    goals_home = fit(df["home_goals"].to_numpy(float))
    goals_away = fit(df["away_goals"].to_numpy(float))

    names = {t["id"]: t["name"] for t in client.table("teams").select("id, name").execute().data}
    today = date.today().isoformat()
    now = datetime.now(timezone.utc).isoformat()

    for serie in ("a", "b"):
        comps = client.table("competitions").select("id, season").eq("code", serie).order("season").execute().data

        finished = []
        for comp in comps:
            for m in fetch_matches(client, comp["id"]):
                status = m["status"] or ""
                if "Finish" in status or status == "finished":
                    finished.append(
                        EloMatchInput(m["home_team_id"], m["away_team_id"], m["home_score"], m["away_score"], m["match_date"])
                    )
        ratings = compute_elo_ratings(finished)

        upcoming = (
            client.table("matches")
            .select("id, match_date, match_time, home_team_id, away_team_id")
            .eq("competition_id", comps[-1]["id"])
            .ilike("status", "%not started%")
            .gte("match_date", today)
            .order("match_date")
            .order("match_time")
            .execute()
            .data
        )
        if not upcoming:
            print(f"\nSérie {serie.upper()}: nenhum jogo futuro encontrado.")
            continue

        def rating(team_id: str) -> float:
            return ratings.get(team_id, {"rating": INITIAL_RATING})["rating"]

        diffs = np.array([[rating(u["home_team_id"]) - rating(u["away_team_id"])] for u in upcoming])
        proba = model.predict_proba(diffs)
        gfeat = np.hstack([diffs, np.full((len(diffs), 1), 1.0 if serie == "a" else 0.0)])
        lam_h, lam_a = goals_home.predict(gfeat), goals_away.predict(gfeat)
        p_over = 1.0 - poisson.cdf(2, lam_h + lam_a)

        rows = []
        for u, d, p, lh, la, po in zip(upcoming, diffs[:, 0], proba, lam_h, lam_a, p_over):
            pr = dict(zip(classes, p))
            rows.append({
                "match_id": u["id"],
                "model_version": MODEL_VERSION,
                "p_home": round(float(pr["H"]), 5),
                "p_draw": round(float(pr["D"]), 5),
                "p_away": round(float(pr["A"]), 5),
                "elo_diff": round(float(d), 2),
                "p_over_2_5": round(float(po), 5),
                "lambda_home": round(float(lh), 3),
                "lambda_away": round(float(la), 3),
                "trained_on": len(df),
                "generated_at": now,
            })
        client.table("match_predictions").upsert(rows, on_conflict="match_id,model_version").execute()

        avg = {k: float(np.mean([r[k] for r in rows])) for k in ("p_home", "p_draw", "p_away")}
        print(f"\nSérie {serie.upper()}: {len(rows)} jogos futuros | média prevista: "
              f"casa {avg['p_home']:.0%} | empate {avg['p_draw']:.0%} | fora {avg['p_away']:.0%}")
        for u, r in list(zip(upcoming, rows))[:8]:
            print(f"  {u['match_date']} {names[u['home_team_id']]} x {names[u['away_team_id']]}: "
                  f"casa {r['p_home']:.0%} | empate {r['p_draw']:.0%} | fora {r['p_away']:.0%}")


if __name__ == "__main__":
    main()
