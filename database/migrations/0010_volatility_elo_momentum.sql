-- ============================================================
-- Analytics Fase 3, 4 e 5: volatilidade, Elo rating, momentum
-- ============================================================

create table if not exists team_volatility (
    id uuid primary key default gen_random_uuid(),

    competition_id uuid not null references competitions(id) on delete cascade,
    team_id uuid not null references teams(id) on delete cascade,

    points_stddev numeric(5,2),
    goal_difference_stddev numeric(5,2),
    volatility_index numeric(5,2),

    matches_considered integer not null,

    computed_at timestamptz not null default now(),

    unique (competition_id, team_id)
);

create table if not exists team_elo_ratings (
    id uuid primary key default gen_random_uuid(),

    competition_id uuid not null references competitions(id) on delete cascade,
    team_id uuid not null references teams(id) on delete cascade,

    rating numeric(7,2) not null,
    matches_considered integer not null,

    computed_at timestamptz not null default now(),

    unique (competition_id, team_id)
);

create table if not exists team_momentum (
    id uuid primary key default gen_random_uuid(),

    competition_id uuid not null references competitions(id) on delete cascade,
    team_id uuid not null references teams(id) on delete cascade,

    momentum_score numeric(6,2),
    attacking_trend numeric(5,2),
    defensive_trend numeric(5,2),
    points_trend numeric(5,2),
    weighted_form_score numeric(5,2),

    computed_at timestamptz not null default now(),

    unique (competition_id, team_id)
);

create index if not exists idx_team_volatility_team_id on team_volatility(team_id);
create index if not exists idx_team_elo_ratings_team_id on team_elo_ratings(team_id);
create index if not exists idx_team_momentum_team_id on team_momentum(team_id);

grant select, insert, update, delete on team_volatility to service_role;
grant select, insert, update, delete on team_elo_ratings to service_role;
grant select, insert, update, delete on team_momentum to service_role;
grant select on team_volatility to anon, authenticated;
grant select on team_elo_ratings to anon, authenticated;
grant select on team_momentum to anon, authenticated;

alter table team_volatility enable row level security;
alter table team_elo_ratings enable row level security;
alter table team_momentum enable row level security;

create policy "Public read access" on team_volatility for select using (true);
create policy "Public read access" on team_elo_ratings for select using (true);
create policy "Public read access" on team_momentum for select using (true);
