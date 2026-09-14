-- ============================================================
-- Grants de privilégio para roles do Supabase
-- Necessário porque as tabelas foram criadas via SQL puro,
-- sem passar pela interface visual do Supabase (que configura
-- esses grants automaticamente).
-- ============================================================

grant usage on schema public to anon, authenticated, service_role;

grant select, insert, update, delete on all tables in schema public to service_role;
grant usage, select on all sequences in schema public to service_role;

grant select on all tables in schema public to anon, authenticated;

alter default privileges in schema public
    grant select, insert, update, delete on tables to service_role;

alter default privileges in schema public
    grant usage, select on sequences to service_role;

alter default privileges in schema public
    grant select on tables to anon, authenticated;
