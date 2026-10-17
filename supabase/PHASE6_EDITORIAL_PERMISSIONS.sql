-- Phase 6 : À exécuter UNE FOIS dans Supabase SQL Editor.
-- Ne PAS réexécuter supabase/schema.sql : il correspond à un ancien schéma.
-- Conserve toutes les données et les décisions existantes.
-- Autorise les rôles reviewer/admin (contrôlés par public.is_reviewer()).
-- La politique RLS « reviewers update articles » doit déjà exister.
GRANT UPDATE (category, orchestra, review_status, reviewed_by, reviewed_at)
ON TABLE public.articles TO authenticated;
