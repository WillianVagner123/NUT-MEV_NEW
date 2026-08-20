-- NutEV Validation MVP schema
-- Target: hosted Supabase, PostgreSQL 15+
-- Safety model: public Data API + RLS, no service_role in browser, validation split only.

create schema if not exists private;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create table if not exists public.validation_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  role text not null default 'assessor' check (role in ('assessor','admin','adjudicator')),
  created_at timestamptz not null default now()
);

create table if not exists public.validation_rounds (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  split text not null default 'validation' check (split = 'validation'),
  status text not null default 'draft' check (status in ('draft','assessment','adjudication','locked')),
  candidate_runtime_sha text not null check (candidate_runtime_sha ~ '^[0-9a-f]{40}$'),
  questions_sha256 text not null check (questions_sha256 ~ '^[0-9a-f]{64}$'),
  created_by uuid not null references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.validation_questions (
  round_id uuid not null references public.validation_rounds(id) on delete cascade,
  question_id text not null,
  question_text text not null,
  eligibility_context jsonb not null default '{}'::jsonb,
  primary key (round_id, question_id)
);

create table if not exists public.validation_references (
  round_id uuid not null references public.validation_rounds(id) on delete cascade,
  pool_item_id text not null,
  question_id text not null,
  reference_id text not null,
  title text not null,
  abstract text,
  journal text,
  year text,
  doi text,
  pmid text,
  pmcid text,
  url text,
  primary key (round_id, pool_item_id),
  unique (round_id, question_id, reference_id),
  foreign key (round_id, question_id) references public.validation_questions(round_id, question_id) on delete cascade
);

create table if not exists public.validation_assignments (
  id uuid primary key default gen_random_uuid(),
  round_id uuid not null,
  pool_item_id text not null,
  assessor_user_id uuid not null references auth.users(id) on delete cascade,
  assessor_id text not null,
  assessor_order integer not null check (assessor_order > 0),
  relevance_grade smallint check (relevance_grade in (0,1,2)),
  reason text,
  decision_timestamp timestamptz,
  blind_to_nutev boolean not null default true,
  review_later boolean not null default false,
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (round_id, pool_item_id, assessor_user_id),
  unique (round_id, assessor_user_id, assessor_order),
  foreign key (round_id, pool_item_id) references public.validation_references(round_id, pool_item_id) on delete cascade,
  constraint decision_fields_complete check (
    relevance_grade is null or (
      nullif(btrim(reason), '') is not null and decision_timestamp is not null
    )
  )
);

create table if not exists public.validation_progress (
  round_id uuid not null references public.validation_rounds(id) on delete cascade,
  assessor_user_id uuid not null references auth.users(id) on delete cascade,
  assessor_id text not null,
  total_items integer not null default 0,
  completed_items integer not null default 0,
  flagged_items integer not null default 0,
  updated_at timestamptz not null default now(),
  primary key (round_id, assessor_user_id)
);

create table if not exists public.validation_adjudications (
  id uuid primary key default gen_random_uuid(),
  round_id uuid not null,
  pool_item_id text not null,
  relevance_grade smallint not null check (relevance_grade in (0,1,2)),
  adjudication_status text not null default 'RESOLVED' check (adjudication_status = 'RESOLVED'),
  adjudicator_id uuid not null references auth.users(id),
  reason text not null check (nullif(btrim(reason), '') is not null),
  adjudication_timestamp timestamptz not null,
  unique (round_id, pool_item_id),
  foreign key (round_id, pool_item_id) references public.validation_references(round_id, pool_item_id) on delete cascade
);

-- Auth user -> app profile. Role defaults to assessor and is not user-editable from the Data API.
create or replace function private.handle_validation_user()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.validation_profiles (id, display_name, role)
  values (new.id, coalesce(new.raw_user_meta_data ->> 'full_name', split_part(coalesce(new.email,''), '@', 1)), 'assessor')
  on conflict (id) do nothing;
  return new;
end;
$$;
revoke all on function private.handle_validation_user() from public, anon, authenticated;

drop trigger if exists on_validation_auth_user_created on auth.users;
create trigger on_validation_auth_user_created
after insert on auth.users
for each row execute function private.handle_validation_user();

-- Backfill users that existed before this schema was installed.
insert into public.validation_profiles (id, display_name, role)
select u.id, coalesce(u.raw_user_meta_data ->> 'full_name', split_part(coalesce(u.email,''), '@', 1)), 'assessor'
from auth.users u
on conflict (id) do nothing;

-- Security-definer lookup helpers avoid recursive RLS policy dependencies.
-- They derive the caller from auth.uid(); callers cannot ask about another user's authorization context.
create or replace function private.current_validation_role()
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select p.role from public.validation_profiles p where p.id = (select auth.uid());
$$;

create or replace function private.is_assigned_to_round(target_round uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.validation_assignments a
    where a.round_id = target_round and a.assessor_user_id = (select auth.uid())
  );
$$;

create or replace function private.is_assigned_to_item(target_round uuid, target_pool_item text)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1 from public.validation_assignments a
    where a.round_id = target_round
      and a.pool_item_id = target_pool_item
      and a.assessor_user_id = (select auth.uid())
  );
$$;

create or replace function private.validation_round_status(target_round uuid)
returns text
language sql
stable
security definer
set search_path = ''
as $$
  select r.status from public.validation_rounds r where r.id = target_round;
$$;

create or replace function private.is_assessor_user(target_user uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (select 1 from public.validation_profiles p where p.id = target_user and p.role = 'assessor');
$$;

revoke all on function private.current_validation_role() from public, anon;
revoke all on function private.is_assigned_to_round(uuid) from public, anon;
revoke all on function private.is_assigned_to_item(uuid, text) from public, anon;
revoke all on function private.validation_round_status(uuid) from public, anon;
revoke all on function private.is_assessor_user(uuid) from public, anon;
grant execute on function private.current_validation_role() to authenticated;
grant execute on function private.is_assigned_to_round(uuid) to authenticated;
grant execute on function private.is_assigned_to_item(uuid, text) to authenticated;
grant execute on function private.validation_round_status(uuid) to authenticated;
grant execute on function private.is_assessor_user(uuid) to authenticated;

-- Keep reviewer progress visible without exposing grades to admins during blinded assessment.
create or replace function private.refresh_validation_progress()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  target_round uuid;
  target_user uuid;
  remaining integer;
begin
  target_round := coalesce(new.round_id, old.round_id);
  target_user := coalesce(new.assessor_user_id, old.assessor_user_id);
  select count(*)::int into remaining
  from public.validation_assignments a
  where a.round_id = target_round and a.assessor_user_id = target_user;

  if remaining = 0 then
    delete from public.validation_progress p
    where p.round_id = target_round and p.assessor_user_id = target_user;
    return coalesce(new, old);
  end if;

  insert into public.validation_progress (round_id, assessor_user_id, assessor_id, total_items, completed_items, flagged_items, updated_at)
  select
    target_round,
    target_user,
    min(a.assessor_id),
    count(*)::int,
    count(*) filter (where a.relevance_grade is not null)::int,
    count(*) filter (where a.review_later)::int,
    now()
  from public.validation_assignments a
  where a.round_id = target_round and a.assessor_user_id = target_user
  on conflict (round_id, assessor_user_id) do update
  set assessor_id = excluded.assessor_id,
      total_items = excluded.total_items,
      completed_items = excluded.completed_items,
      flagged_items = excluded.flagged_items,
      updated_at = excluded.updated_at;
  return coalesce(new, old);
end;
$$;
revoke all on function private.refresh_validation_progress() from public, anon, authenticated;

drop trigger if exists validation_assignment_progress on public.validation_assignments;
create trigger validation_assignment_progress
after insert or update or delete on public.validation_assignments
for each row execute function private.refresh_validation_progress();

-- Enforce state transitions and immutability of scientific identity after draft.
create or replace function private.guard_validation_round_transition()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
begin
  new.updated_at := now();
  if old.status <> 'draft' and (
    new.candidate_runtime_sha <> old.candidate_runtime_sha or
    new.questions_sha256 <> old.questions_sha256 or
    new.split <> old.split
  ) then
    raise exception 'scientific identity fields are immutable after draft';
  end if;

  if old.status = 'draft' and new.status = 'assessment' then
    if not exists (select 1 from public.validation_references r where r.round_id = old.id) then
      raise exception 'cannot start assessment without references';
    end if;
    if exists (
      select 1
      from public.validation_references r
      left join public.validation_assignments a
        on a.round_id = r.round_id and a.pool_item_id = r.pool_item_id
      where r.round_id = old.id
      group by r.pool_item_id
      having count(distinct a.assessor_user_id) < 2
    ) then
      raise exception 'every pool item requires at least two independent assessors';
    end if;
  elsif old.status = 'assessment' and new.status = 'adjudication' then
    if exists (
      select 1 from public.validation_assignments a
      where a.round_id = old.id and (
        a.relevance_grade is null or nullif(btrim(a.reason), '') is null or
        a.decision_timestamp is null or a.blind_to_nutev is not true
      )
    ) then
      raise exception 'all blind assessments must be complete before adjudication';
    end if;
    if exists (
      select 1 from public.validation_references r
      left join public.validation_assignments a
        on a.round_id = r.round_id and a.pool_item_id = r.pool_item_id
      where r.round_id = old.id
      group by r.pool_item_id
      having count(distinct a.assessor_user_id) < 2
    ) then
      raise exception 'every pool item requires two completed independent assessors';
    end if;
  elsif old.status = 'adjudication' and new.status = 'locked' then
    if exists (
      select 1
      from public.validation_assignments a
      where a.round_id = old.id
      group by a.pool_item_id
      having min(a.relevance_grade) <> max(a.relevance_grade)
         and not exists (
           select 1 from public.validation_adjudications j
           where j.round_id = old.id and j.pool_item_id = a.pool_item_id
         )
    ) then
      raise exception 'all conflicts must be adjudicated before lock';
    end if;
  elsif new.status <> old.status then
    raise exception 'invalid validation round transition % -> %', old.status, new.status;
  end if;
  return new;
end;
$$;
revoke all on function private.guard_validation_round_transition() from public, anon, authenticated;

drop trigger if exists validation_round_transition_guard on public.validation_rounds;
create trigger validation_round_transition_guard
before update on public.validation_rounds
for each row execute function private.guard_validation_round_transition();

-- RLS on every exposed public table.
alter table public.validation_profiles enable row level security;
alter table public.validation_rounds enable row level security;
alter table public.validation_questions enable row level security;
alter table public.validation_references enable row level security;
alter table public.validation_assignments enable row level security;
alter table public.validation_progress enable row level security;
alter table public.validation_adjudications enable row level security;

-- Idempotent policy recreation.
drop policy if exists validation_profiles_select on public.validation_profiles;
drop policy if exists validation_profiles_update_self on public.validation_profiles;
drop policy if exists validation_rounds_select on public.validation_rounds;
drop policy if exists validation_rounds_insert_admin on public.validation_rounds;
drop policy if exists validation_rounds_update_admin on public.validation_rounds;
drop policy if exists validation_rounds_delete_admin on public.validation_rounds;
drop policy if exists validation_questions_select on public.validation_questions;
drop policy if exists validation_questions_insert_admin on public.validation_questions;
drop policy if exists validation_questions_delete_admin on public.validation_questions;
drop policy if exists validation_references_select on public.validation_references;
drop policy if exists validation_references_insert_admin on public.validation_references;
drop policy if exists validation_references_delete_admin on public.validation_references;
drop policy if exists validation_assignments_select on public.validation_assignments;
drop policy if exists validation_assignments_insert_admin on public.validation_assignments;
drop policy if exists validation_assignments_update_self on public.validation_assignments;
drop policy if exists validation_assignments_delete_admin on public.validation_assignments;
drop policy if exists validation_progress_select on public.validation_progress;
drop policy if exists validation_adjudications_select on public.validation_adjudications;
drop policy if exists validation_adjudications_insert on public.validation_adjudications;
drop policy if exists validation_adjudications_update on public.validation_adjudications;

create policy validation_profiles_select on public.validation_profiles for select to authenticated using (true);
create policy validation_profiles_update_self on public.validation_profiles for update to authenticated
using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

create policy validation_rounds_select on public.validation_rounds for select to authenticated using (
  private.current_validation_role() in ('admin','adjudicator')
  or private.is_assigned_to_round(validation_rounds.id)
);
create policy validation_rounds_insert_admin on public.validation_rounds for insert to authenticated with check (
  private.current_validation_role() = 'admin'
  and created_by = (select auth.uid()) and split = 'validation'
);
create policy validation_rounds_update_admin on public.validation_rounds for update to authenticated
using (private.current_validation_role() = 'admin')
with check (private.current_validation_role() = 'admin');
create policy validation_rounds_delete_admin on public.validation_rounds for delete to authenticated using (
  private.current_validation_role() = 'admin' and status = 'draft'
);

create policy validation_questions_select on public.validation_questions for select to authenticated using (
  private.current_validation_role() in ('admin','adjudicator')
  or private.is_assigned_to_round(validation_questions.round_id)
);
create policy validation_questions_insert_admin on public.validation_questions for insert to authenticated with check (
  private.current_validation_role() = 'admin'
  and private.validation_round_status(validation_questions.round_id) = 'draft'
);
create policy validation_questions_delete_admin on public.validation_questions for delete to authenticated using (
  private.current_validation_role() = 'admin'
  and private.validation_round_status(validation_questions.round_id) = 'draft'
);

create policy validation_references_select on public.validation_references for select to authenticated using (
  private.current_validation_role() in ('admin','adjudicator')
  or private.is_assigned_to_item(validation_references.round_id, validation_references.pool_item_id)
);
create policy validation_references_insert_admin on public.validation_references for insert to authenticated with check (
  private.current_validation_role() = 'admin'
  and private.validation_round_status(validation_references.round_id) = 'draft'
);
create policy validation_references_delete_admin on public.validation_references for delete to authenticated using (
  private.current_validation_role() = 'admin'
  and private.validation_round_status(validation_references.round_id) = 'draft'
);

-- Assessors see only their own raw decisions while blinded. Admin/adjudicator get raw decisions only after assessment closes.
create policy validation_assignments_select on public.validation_assignments for select to authenticated using (
  assessor_user_id = (select auth.uid())
  or (
    private.current_validation_role() in ('admin','adjudicator')
    and private.validation_round_status(validation_assignments.round_id) in ('adjudication','locked')
  )
);
create policy validation_assignments_insert_admin on public.validation_assignments for insert to authenticated with check (
  private.current_validation_role() = 'admin'
  and private.is_assessor_user(validation_assignments.assessor_user_id)
  and private.validation_round_status(validation_assignments.round_id) = 'draft'
);
create policy validation_assignments_update_self on public.validation_assignments for update to authenticated
using (
  assessor_user_id = (select auth.uid())
  and private.validation_round_status(validation_assignments.round_id) = 'assessment'
)
with check (
  assessor_user_id = (select auth.uid())
  and private.validation_round_status(validation_assignments.round_id) = 'assessment'
);
create policy validation_assignments_delete_admin on public.validation_assignments for delete to authenticated using (
  private.current_validation_role() = 'admin'
  and private.validation_round_status(validation_assignments.round_id) = 'draft'
);

create policy validation_progress_select on public.validation_progress for select to authenticated using (
  assessor_user_id = (select auth.uid())
  or private.current_validation_role() in ('admin','adjudicator')
);

create policy validation_adjudications_select on public.validation_adjudications for select to authenticated using (
  private.current_validation_role() in ('admin','adjudicator')
  and private.validation_round_status(validation_adjudications.round_id) in ('adjudication','locked')
);
create policy validation_adjudications_insert on public.validation_adjudications for insert to authenticated with check (
  adjudicator_id = (select auth.uid())
  and private.current_validation_role() in ('admin','adjudicator')
  and private.validation_round_status(validation_adjudications.round_id) = 'adjudication'
);
create policy validation_adjudications_update on public.validation_adjudications for update to authenticated
using (
  adjudicator_id = (select auth.uid())
  and private.current_validation_role() in ('admin','adjudicator')
  and private.validation_round_status(validation_adjudications.round_id) = 'adjudication'
)
with check (adjudicator_id = (select auth.uid()));

-- Explicit Data API privileges (new projects may not auto-expose SQL-created tables).
grant usage on schema public to authenticated;
grant select on public.validation_profiles, public.validation_rounds, public.validation_questions,
  public.validation_references, public.validation_assignments, public.validation_progress,
  public.validation_adjudications to authenticated;
grant insert on public.validation_rounds, public.validation_questions, public.validation_references,
  public.validation_assignments, public.validation_adjudications to authenticated;
grant delete on public.validation_rounds, public.validation_questions, public.validation_references,
  public.validation_assignments to authenticated;
grant update (display_name) on public.validation_profiles to authenticated;
grant update (name, status) on public.validation_rounds to authenticated;
grant update (relevance_grade, reason, decision_timestamp, blind_to_nutev, review_later, notes)
  on public.validation_assignments to authenticated;
grant update (relevance_grade, adjudication_status, adjudicator_id, reason, adjudication_timestamp)
  on public.validation_adjudications to authenticated;

-- Do not grant table access to anon. Authentication endpoints remain available via Supabase Auth.
revoke all on public.validation_profiles, public.validation_rounds, public.validation_questions,
  public.validation_references, public.validation_assignments, public.validation_progress,
  public.validation_adjudications from anon;
