create table if not exists phases (
    id uuid primary key default gen_random_uuid(),
    competition_id uuid not null references competitions(id) on delete cascade,

    slug text not null,
    name text not null,
    phase_type text not null check (phase_type in ('league', 'groups', 'knockout')),
    phase_order integer not null,

    created_at timestamptz not null default now(),
    unique (competition_id, slug)
);

create index if not exists idx_phases_competition_id on phases(competition_id);

alter table groups add column if not exists phase_id uuid references phases(id) on delete set null;
alter table rounds add column if not exists phase_id uuid references phases(id) on delete set null;
alter table matches
    add column if not exists phase_id uuid references phases(id) on delete set null,
    add column if not exists tie_key text,
    add column if not exists leg integer;
alter table standings_entries add column if not exists phase_id uuid references phases(id) on delete cascade;

alter table standings_entries drop constraint if exists uq_standings_competition_team;
alter table standings_entries
    add constraint uq_standings_phase_team
    unique nulls not distinct (competition_id, phase_id, team_id);

grant select, insert, update, delete on phases to service_role;
grant select on phases to anon, authenticated;
alter table phases enable row level security;
create policy "Public read access" on phases for select using (true);
