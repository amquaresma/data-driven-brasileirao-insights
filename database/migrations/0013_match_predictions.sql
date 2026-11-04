create table if not exists match_predictions (
    id uuid primary key default gen_random_uuid(),
    match_id uuid not null references matches(id) on delete cascade,
    model_version text not null,
    p_home numeric(6,5) not null,
    p_draw numeric(6,5) not null,
    p_away numeric(6,5) not null,
    elo_diff numeric(7,2),
    trained_on integer not null,
    generated_at timestamptz not null default now(),
    unique (match_id, model_version)
);

create index if not exists idx_match_predictions_match_id on match_predictions(match_id);

grant select, insert, update, delete on match_predictions to service_role;
grant select on match_predictions to anon, authenticated;
alter table match_predictions enable row level security;
create policy "Public read access" on match_predictions for select using (true);
