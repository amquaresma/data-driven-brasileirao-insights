-- ============================================================
-- Fase 1 da Highlightly: tabelas de reconciliação de identidade
-- entre providers (competitions e matches), seguindo o mesmo
-- padrão já usado em team_external_ids.
-- ============================================================

create table if not exists competition_external_ids (
    id uuid primary key default gen_random_uuid(),
    competition_id uuid not null references competitions(id) on delete cascade,

    provider text not null,
    external_id text not null,

    created_at timestamptz not null default now(),

    unique (provider, external_id)
);

create index if not exists idx_competition_external_ids_competition_id
    on competition_external_ids(competition_id);

create table if not exists match_external_ids (
    id uuid primary key default gen_random_uuid(),
    match_id uuid not null references matches(id) on delete cascade,

    provider text not null,
    external_id text not null,

    created_at timestamptz not null default now(),

    unique (provider, external_id)
);

create index if not exists idx_match_external_ids_match_id
    on match_external_ids(match_id);

grant select, insert, update, delete on competition_external_ids to service_role;
grant select, insert, update, delete on match_external_ids to service_role;
grant select on competition_external_ids to anon, authenticated;
grant select on match_external_ids to anon, authenticated;

alter table competition_external_ids enable row level security;
alter table match_external_ids enable row level security;

create policy "Public read access" on competition_external_ids
    for select using (true);

create policy "Public read access" on match_external_ids
    for select using (true);
