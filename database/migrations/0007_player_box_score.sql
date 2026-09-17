-- ============================================================
-- Fase 4 da Highlightly: players e player_match_statistics
-- (box score individual, incluindo xG/xA/xGOT por jogador)
-- ============================================================

create table if not exists players (
    id uuid primary key default gen_random_uuid(),

    name text not null,
    full_name text,
    position text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists player_external_ids (
    id uuid primary key default gen_random_uuid(),
    player_id uuid not null references players(id) on delete cascade,

    provider text not null,
    external_id text not null,

    created_at timestamptz not null default now(),

    unique (provider, external_id)
);

create index if not exists idx_player_external_ids_player_id
    on player_external_ids(player_id);

create table if not exists player_match_statistics (
    id uuid primary key default gen_random_uuid(),

    match_id uuid not null references matches(id) on delete cascade,
    player_id uuid not null references players(id) on delete cascade,
    team_id uuid not null references teams(id) on delete cascade,

    shirt_number integer,
    is_captain boolean,
    is_substitute boolean,
    minutes_played integer,
    match_rating numeric(4,2),
    offsides integer,

    goals_scored integer,
    goals_saved integer,
    goals_conceded integer,
    assists integer,

    dribbles_total integer,
    dribbles_successful integer,
    dribbles_failed integer,
    dribble_success_rate numeric(5,2),

    fouled_by_others integer,
    fouled_others integer,

    tackles_total integer,
    interceptions_total integer,

    duels_total integer,
    duels_won integer,
    duels_lost integer,
    duel_success_rate numeric(5,2),

    cards_red integer,
    cards_yellow integer,
    cards_second_yellow integer,

    passes_accuracy numeric(5,2),
    passes_successful integer,
    passes_failed integer,
    passes_total integer,
    passes_key integer,

    penalties_scored integer,
    penalties_missed integer,
    penalties_total integer,
    penalties_accuracy numeric(5,2),

    shots_on_target integer,
    shots_off_target integer,
    shots_total integer,
    shots_accuracy numeric(5,2),

    expected_goals numeric(5,3),
    expected_assists numeric(5,3),
    expected_goals_on_target numeric(5,3),
    expected_goals_on_target_conceded numeric(5,3),
    expected_goals_prevented numeric(5,3),

    source_provider text not null default 'highlightly',

    created_at timestamptz not null default now(),

    unique (match_id, player_id)
);

create index if not exists idx_player_match_statistics_match_id
    on player_match_statistics(match_id);
create index if not exists idx_player_match_statistics_player_id
    on player_match_statistics(player_id);

grant select, insert, update, delete on players to service_role;
grant select, insert, update, delete on player_external_ids to service_role;
grant select, insert, update, delete on player_match_statistics to service_role;
grant select on players to anon, authenticated;
grant select on player_external_ids to anon, authenticated;
grant select on player_match_statistics to anon, authenticated;

alter table players enable row level security;
alter table player_external_ids enable row level security;
alter table player_match_statistics enable row level security;

create policy "Public read access" on players
    for select using (true);

create policy "Public read access" on player_external_ids
    for select using (true);

create policy "Public read access" on player_match_statistics
    for select using (true);
