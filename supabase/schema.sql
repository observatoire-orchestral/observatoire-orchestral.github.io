-- À exécuter dans Supabase > SQL Editor. Ne jamais exposer service_role dans le navigateur.
create extension if not exists pgcrypto;
create table if not exists public.profiles (
 id uuid primary key references auth.users(id) on delete cascade,
 role text not null default 'viewer' check (role in ('viewer','reviewer','admin')),
 created_at timestamptz not null default now()
);
create table if not exists public.articles (
 id uuid primary key default gen_random_uuid(),
 url text not null unique,
 title text not null,
 summary text,
 source_name text not null,
 orchestra text not null default 'Autres / National',
 topic text not null default 'Autres',
 published_at timestamptz,
 created_at timestamptz not null default now(),
 is_auto boolean not null default true,
 review_status text not null default 'pending' check (review_status in ('pending','approved','rejected')),
 reviewed_by uuid references auth.users(id),
 reviewed_at timestamptz
);
create index if not exists articles_published_idx on public.articles(published_at desc);
create index if not exists articles_orchestra_idx on public.articles(orchestra);
create or replace function public.make_profile() returns trigger language plpgsql security definer set search_path = '' as $$
begin insert into public.profiles(id) values(new.id) on conflict(id) do nothing;return new;end $$;
drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users for each row execute function public.make_profile();
insert into public.profiles(id) select id from auth.users on conflict(id) do nothing;
create or replace function public.is_reviewer() returns boolean language sql stable security definer set search_path = '' as $$
 select exists(select 1 from public.profiles where id = (select auth.uid()) and role in ('reviewer','admin'))
$$;
alter table public.profiles enable row level security;
alter table public.articles enable row level security;
drop policy if exists "profile own read" on public.profiles;
create policy "profile own read" on public.profiles for select to authenticated using (id = (select auth.uid()));
drop policy if exists "members read articles" on public.articles;
create policy "members read articles" on public.articles for select to authenticated using (true);
drop policy if exists "reviewers update articles" on public.articles;
create policy "reviewers update articles" on public.articles for update to authenticated using (public.is_reviewer()) with check (public.is_reviewer());
-- Restreindre les colonnes modifiables : un reviewer ne peut modifier QUE les champs de validation.
revoke all on public.articles from anon, authenticated;
grant select on public.articles to authenticated;
grant update(review_status,reviewed_by,reviewed_at) on public.articles to authenticated;
revoke all on public.profiles from anon, authenticated;
grant select on public.profiles to authenticated;
-- Après création du premier compte, promouvoir manuellement son UUID (Supabase > Authentication > Users) :
-- update public.profiles set role='admin' where id='UUID_DU_COMPTE';
-- Les clés service_role contournent les politiques RLS : à conserver UNIQUEMENT dans GitHub Actions.
