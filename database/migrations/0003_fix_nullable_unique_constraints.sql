-- ============================================================
-- Corrige constraints de unicidade com group_id nullable
-- Substitui índices baseados em coalesce() (não suportados pelo
-- ON CONFLICT do PostgREST/Supabase) por UNIQUE NULLS NOT DISTINCT,
-- que trata múltiplos NULL como equivalentes usando colunas literais.
-- ============================================================

drop index if exists uq_rounds_competition_group_number;

alter table rounds
    add constraint uq_rounds_competition_group_number
    unique nulls not distinct (competition_id, group_id, number);

drop index if exists uq_standings_competition_group_team;

alter table standings_entries
    add constraint uq_standings_competition_group_team
    unique nulls not distinct (competition_id, group_id, team_id);
