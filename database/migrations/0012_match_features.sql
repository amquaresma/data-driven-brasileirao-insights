-- Features pré-jogo (só informação anterior ao jogo) + alvos, para o ML.
create table if not exists match_features (
    id uuid primary key default gen_random_uuid(),
    match_id uuid not null unique references matches(id) on delete cascade,
    competition_id uuid not null references competitions(id) on delete cascade,
    match_date date not null,
    home_team_id uuid not null references teams(id) on delete cascade,
    away_team_id uuid not null references teams(id) on delete cascade,

    home_elo numeric(7,2), away_elo numeric(7,2), elo_diff numeric(7,2),
    home_matches_played integer not null, away_matches_played integer not null,
    home_form numeric(5,2), away_form numeric(5,2),
    home_gf_avg5 numeric(5,2), away_gf_avg5 numeric(5,2),
    home_ga_avg5 numeric(5,2), away_ga_avg5 numeric(5,2),
    home_pts_avg5 numeric(5,2), away_pts_avg5 numeric(5,2),
    home_rest_days integer, away_rest_days integer,
    min_history_ok boolean not null,

    home_goals integer not null, away_goals integer not null, total_goals integer not null,
    result text not null check (result in ('H', 'D', 'A')),
    over_2_5 boolean not null,

    computed_at timestamptz not null default now()
);

create index if not exists idx_match_features_comp_date on match_features(competition_id, match_date);

grant select, insert, update, delete on match_features to service_role;
grant select on match_features to anon, authenticated;
alter table match_features enable row level security;
create policy "Public read access" on match_features for select using (true);
