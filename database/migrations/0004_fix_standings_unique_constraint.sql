-- ============================================================
-- Corrige a chave única de standings_entries
--
-- Problema: a constraint original incluía group_id na chave
-- única (competition_id, group_id, team_id). Isso está
-- semanticamente errado — um time só pode ocupar uma posição
-- na classificação de uma competição por vez, então group_id
-- é apenas um atributo da linha (para competições agrupadas),
-- não parte da identidade da entry.
--
-- Efeito do bug: ao reingerir uma competição depois que ela
-- passou a ter grupos (ex: Série C mudou de fase), o pipeline
-- criava uma linha NOVA em vez de atualizar a existente, porque
-- group_id mudou de NULL para um UUID real.
-- ============================================================

alter table standings_entries
    drop constraint if exists uq_standings_competition_group_team;

alter table standings_entries
    add constraint uq_standings_competition_team
    unique (competition_id, team_id);
