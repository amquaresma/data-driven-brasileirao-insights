-- ============================================================
-- Etapa 4.1 — Schema core (Campeonato Brasileiro API)
-- competitions, teams, groups, rounds, matches, standings
-- ============================================================

create extension if not exists pgcrypto;

-- ------------------------------------------------------------
-- competitions
-- ------------------------------------------------------------
create table if not exists competitions (
    id uuid primary key default gen_random_uuid(),

    code text not null,
    season integer not null,
    name text not null,
    slug text,

    sport text,
    grouped boolean not null default false,

    phase_slug text,
    phase_description text,
    phase_type_id text,

    edition_name text,
    edition_location text,
    edition_starts_at date,
    edition_ends_at date,

    source_provider text,
    source_url text,
    source_resource_id text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (code, season)
);

-- ------------------------------------------------------------
-- teams
-- ------------------------------------------------------------
create table if not exists teams (
    id uuid primary key default gen_random_uuid(),

    name text not null,
    short_name text,
    badge_url text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists team_external_ids (
    id uuid primary key default gen_random_uuid(),
    team_id uuid not null references teams(id) on delete cascade,

    provider text not null,
    external_id text not null,

    created_at timestamptz not null default now(),

    unique (provider, external_id)
);

create index if not exists idx_team_external_ids_team_id
    on team_external_ids(team_id);

-- ------------------------------------------------------------
-- groups
-- ------------------------------------------------------------
create table if not exists groups (
    id uuid primary key default gen_random_uuid(),
    competition_id uuid not null references competitions(id) on delete cascade,

    external_id text not null,
    name text not null,

    created_at timestamptz not null default now(),

    unique (competition_id, external_id)
);

create index if not exists idx_groups_competition_id
    on groups(competition_id);

-- ------------------------------------------------------------
-- rounds
-- ------------------------------------------------------------
create table if not exists rounds (
    id uuid primary key default gen_random_uuid(),
    competition_id uuid not null references competitions(id) on delete cascade,
    group_id uuid references groups(id) on delete cascade,

    external_id text,
    number integer not null,
    total integer,
    label text,

    created_at timestamptz not null default now()
);

create index if not exists idx_rounds_competition_id
    on rounds(competition_id);
create index if not exists idx_rounds_group_id
    on rounds(group_id);

create unique index if not exists uq_rounds_competition_group_number
    on rounds (
        competition_id,
        coalesce(group_id, '00000000-0000-0000-0000-000000000000'::uuid),
        number
    );

-- ------------------------------------------------------------
-- matches
-- ------------------------------------------------------------
create table if not exists matches (
    id uuid primary key default gen_random_uuid(),

    provider text not null,
    external_id text not null,

    competition_id uuid references competitions(id) on delete set null,
    round_id uuid references rounds(id) on delete set null,

    home_team_id uuid references teams(id) on delete set null,
    away_team_id uuid references teams(id) on delete set null,

    date_time timestamptz,
    match_date date,
    match_time text,

    venue text,

    started boolean not null default false,
    status text,
    status_code text,

    home_score integer,
    away_score integer,
    penalties_home integer,
    penalties_away integer,

    coverage_label text,
    coverage_url text,
    coverage_status_code text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),

    unique (provider, external_id)
);

create index if not exists idx_matches_competition_id
    on matches(competition_id);
create index if not exists idx_matches_round_id
    on matches(round_id);
create index if not exists idx_matches_home_team_id
    on matches(home_team_id);
create index if not exists idx_matches_away_team_id
    on matches(away_team_id);
create index if not exists idx_matches_date_time
    on matches(date_time);

-- ------------------------------------------------------------
-- standings_entries
-- ------------------------------------------------------------
create table if not exists standings_entries (
    id uuid primary key default gen_random_uuid(),

    competition_id uuid not null references competitions(id) on delete cascade,
    group_id uuid references groups(id) on delete cascade,
    team_id uuid not null references teams(id) on delete cascade,

    table_name text,

    position integer not null,
    points integer,
    matches_played integer,
    wins integer,
    draws integer,
    losses integer,
    goals_for integer,
    goals_against integer,
    goal_difference integer,
    efficiency numeric(5,2),
    movement text,
    recent_form text[],
    legend text,

    source_provider text,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_standings_competition_id
    on standings_entries(competition_id);
create index if not exists idx_standings_group_id
    on standings_entries(group_id);
create index if not exists idx_standings_team_id
    on standings_entries(team_id);

create unique index if not exists uq_standings_competition_group_team
    on standings_entries (
        competition_id,
        coalesce(group_id, '00000000-0000-0000-0000-000000000000'::uuid),
        team_id
    );

-- ------------------------------------------------------------
-- RLS — leitura pública
-- ------------------------------------------------------------
alter table competitions enable row level security;
alter table teams enable row level security;
alter table team_external_ids enable row level security;
alter table groups enable row level security;
alter table rounds enable row level security;
alter table matches enable row level security;
alter table standings_entries enable row level security;

create policy "Public read access" on competitions
    for select using (true);

create policy "Public read access" on teams
    for select using (true);

create policy "Public read access" on groups
    for select using (true);

create policy "Public read access" on rounds
    for select using (true);

create policy "Public read access" on matches
    for select using (true);

create policy "Public read access" on standings_entries
    for select using (true);
