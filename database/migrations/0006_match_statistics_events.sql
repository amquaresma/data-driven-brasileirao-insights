-- ============================================================
-- Fase 3 da Highlightly: match_statistics (EAV) e match_events
-- ============================================================

create table if not exists match_statistics (
    id uuid primary key default gen_random_uuid(),
    match_id uuid not null references matches(id) on delete cascade,
    team_id uuid not null references teams(id) on delete cascade,

    stat_name text not null,
    stat_value numeric not null,

    source_provider text not null default 'highlightly',

    created_at timestamptz not null default now(),

    unique (match_id, team_id, stat_name)
);

create index if not exists idx_match_statistics_match_id
    on match_statistics(match_id);

create table if not exists match_events (
    id uuid primary key default gen_random_uuid(),
    match_id uuid not null references matches(id) on delete cascade,
    team_id uuid references teams(id) on delete set null,

    minute text,
    event_type text not null,
    player_name text,
    player_external_id text,
    assisting_player_name text,
    assisting_player_external_id text,
    substituted_player_name text,

    source_provider text not null default 'highlightly',
    source_external_id text,

    created_at timestamptz not null default now()
);

create index if not exists idx_match_events_match_id
    on match_events(match_id);

grant select, insert, update, delete on match_statistics to service_role;
grant select, insert, update, delete on match_events to service_role;
grant select on match_statistics to anon, authenticated;
grant select on match_events to anon, authenticated;

alter table match_statistics enable row level security;
alter table match_events enable row level security;

create policy "Public read access" on match_statistics
    for select using (true);

create policy "Public read access" on match_events
    for select using (true);
