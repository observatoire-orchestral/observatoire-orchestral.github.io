-- Phase 6.1 : exécuter UNE fois dans Supabase SQL Editor.
-- Ne modifie aucune ligne de public.articles ni public.profiles.
create table if not exists public.editorial_suggestions (
  article_id uuid primary key references public.articles(id) on delete cascade,
  title_snapshot text not null,
  category_snapshot text not null,
  proposed_category text not null,
  orchestra_snapshot text not null,
  proposed_orchestra text not null,
  relevance text not null,
  relevance_reason text,
  confidence text,
  category_reason text,
  editorial_action text,
  imported_at timestamptz not null default now()
);
create index if not exists editorial_suggestions_relevance_idx on public.editorial_suggestions(relevance);
alter table public.editorial_suggestions enable row level security;
drop policy if exists "approved members read editorial suggestions" on public.editorial_suggestions;
create policy "approved members read editorial suggestions" on public.editorial_suggestions
  for select to authenticated using (
    exists(select 1 from public.profiles p where p.id = (select auth.uid()) and p.approved = true)
  );
revoke all on public.editorial_suggestions from anon, authenticated;
grant select on public.editorial_suggestions to authenticated;
-- Import par GitHub Actions avec service_role seulement. Les membres ne peuvent pas modifier les suggestions.
