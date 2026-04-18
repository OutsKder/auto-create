-- ZHIJIE ENGINE DATABASE SCHEMA
-- Compatible with Supabase PostgreSQL and self-hosted PostgreSQL + Node.js backends.
--
-- Notes:
-- 1) For production, tighten RLS policies and move login/session issuing to a backend.
-- 2) This schema keeps auth/business tables separate so it can be reused by a custom backend later.

create extension if not exists pgcrypto;

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  display_name text,
  password_hash text not null,
  password_salt text not null,
  status text not null default 'active' check (status in ('active', 'disabled', 'pending')),
  role text not null default 'member' check (role in ('admin', 'member', 'viewer')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_login_at timestamptz
);

create index if not exists idx_users_email on public.users (email);
create index if not exists idx_users_status on public.users (status);

create table if not exists public.email_verification_codes (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  purpose text not null check (purpose in ('register', 'login', 'reset_password')),
  code_hash text not null,
  code_salt text not null,
  expires_at timestamptz not null,
  used_at timestamptz,
  attempt_count integer not null default 0,
  ip_address inet,
  verified_user_id uuid references public.users(id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists idx_email_codes_email on public.email_verification_codes (email);
create index if not exists idx_email_codes_purpose on public.email_verification_codes (purpose);
create index if not exists idx_email_codes_expires_at on public.email_verification_codes (expires_at);

create table if not exists public.sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  refresh_token_hash text not null,
  refresh_token_salt text not null,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz,
  user_agent text,
  ip_address inet
);

create index if not exists idx_sessions_user_id on public.sessions (user_id);
create index if not exists idx_sessions_expires_at on public.sessions (expires_at);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  owner_user_id uuid not null references public.users(id) on delete cascade,
  status text not null default 'active' check (status in ('active', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_projects_owner on public.projects (owner_user_id);
create index if not exists idx_projects_status on public.projects (status);

create table if not exists public.project_members (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  user_id uuid not null references public.users(id) on delete cascade,
  role text not null default 'viewer' check (role in ('owner', 'editor', 'reviewer', 'viewer')),
  created_at timestamptz not null default now(),
  unique (project_id, user_id)
);

create index if not exists idx_project_members_project_id on public.project_members (project_id);
create index if not exists idx_project_members_user_id on public.project_members (user_id);

create table if not exists public.requirements (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  title text not null,
  background text not null,
  goal text not null,
  constraints text,
  priority text not null default 'medium' check (priority in ('high', 'medium', 'low')),
  owner_user_id uuid references public.users(id) on delete set null,
  current_stage_id text,
  overall_status text not null default 'draft' check (overall_status in ('draft', 'in_progress', 'blocked', 'completed')),
  created_by uuid not null references public.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  deleted_at timestamptz
);

create index if not exists idx_requirements_project_id on public.requirements (project_id);
create index if not exists idx_requirements_status on public.requirements (overall_status);
create index if not exists idx_requirements_priority on public.requirements (priority);
create index if not exists idx_requirements_updated_at on public.requirements (updated_at desc);

create table if not exists public.requirement_stages (
  id uuid primary key default gen_random_uuid(),
  requirement_id uuid not null references public.requirements(id) on delete cascade,
  stage_key text not null,
  stage_name text not null,
  status text not null default 'pending' check (status in ('pending', 'running', 'waiting_review', 'approved', 'rejected', 'completed')),
  output text,
  note text,
  requires_review boolean not null default false,
  sort_order integer not null,
  updated_at timestamptz not null default now(),
  unique (requirement_id, stage_key)
);

create index if not exists idx_requirement_stages_requirement_id on public.requirement_stages (requirement_id);
create index if not exists idx_requirement_stages_stage_key on public.requirement_stages (stage_key);
create index if not exists idx_requirement_stages_status on public.requirement_stages (status);

create table if not exists public.requirement_logs (
  id uuid primary key default gen_random_uuid(),
  requirement_id uuid not null references public.requirements(id) on delete cascade,
  stage_id uuid references public.requirement_stages(id) on delete set null,
  action_type text not null,
  message text not null,
  created_by uuid references public.users(id) on delete set null,
  created_at timestamptz not null default now(),
  meta jsonb not null default '{}'::jsonb
);

create index if not exists idx_requirement_logs_requirement_id on public.requirement_logs (requirement_id);
create index if not exists idx_requirement_logs_stage_id on public.requirement_logs (stage_id);
create index if not exists idx_requirement_logs_created_at on public.requirement_logs (created_at desc);

create table if not exists public.audit_logs (
  id uuid primary key default gen_random_uuid(),
  actor_user_id uuid references public.users(id) on delete set null,
  action text not null,
  target_type text not null,
  target_id uuid,
  detail jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  ip_address inet
);

create index if not exists idx_audit_logs_actor on public.audit_logs (actor_user_id);
create index if not exists idx_audit_logs_created_at on public.audit_logs (created_at desc);

-- Timestamp trigger helper
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists trg_users_updated_at on public.users;
create trigger trg_users_updated_at
before update on public.users
for each row execute function public.set_updated_at();

drop trigger if exists trg_projects_updated_at on public.projects;
create trigger trg_projects_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

drop trigger if exists trg_requirements_updated_at on public.requirements;
create trigger trg_requirements_updated_at
before update on public.requirements
for each row execute function public.set_updated_at();

drop trigger if exists trg_requirement_stages_updated_at on public.requirement_stages;
create trigger trg_requirement_stages_updated_at
before update on public.requirement_stages
for each row execute function public.set_updated_at();

-- Demo / prototype RLS: keep accessible for browser-only MVP.
-- Tighten these policies when moving to a real backend.
alter table public.users enable row level security;
alter table public.email_verification_codes enable row level security;
alter table public.sessions enable row level security;
alter table public.projects enable row level security;
alter table public.project_members enable row level security;
alter table public.requirements enable row level security;
alter table public.requirement_stages enable row level security;
alter table public.requirement_logs enable row level security;
alter table public.audit_logs enable row level security;

-- Minimal demo policies. Replace with authenticated user/role-based policies for production.
do $$
begin
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'users' and policyname = 'demo_select_users') then
    create policy demo_select_users on public.users for select using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'users' and policyname = 'demo_insert_users') then
    create policy demo_insert_users on public.users for insert with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'users' and policyname = 'demo_update_users') then
    create policy demo_update_users on public.users for update using (true) with check (true);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'email_verification_codes' and policyname = 'demo_select_codes') then
    create policy demo_select_codes on public.email_verification_codes for select using (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'email_verification_codes' and policyname = 'demo_insert_codes') then
    create policy demo_insert_codes on public.email_verification_codes for insert with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'email_verification_codes' and policyname = 'demo_update_codes') then
    create policy demo_update_codes on public.email_verification_codes for update using (true) with check (true);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'sessions' and policyname = 'demo_sessions_all') then
    create policy demo_sessions_all on public.sessions for all using (true) with check (true);
  end if;

  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'projects' and policyname = 'demo_projects_all') then
    create policy demo_projects_all on public.projects for all using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'project_members' and policyname = 'demo_project_members_all') then
    create policy demo_project_members_all on public.project_members for all using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'requirements' and policyname = 'demo_requirements_all') then
    create policy demo_requirements_all on public.requirements for all using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'requirement_stages' and policyname = 'demo_requirement_stages_all') then
    create policy demo_requirement_stages_all on public.requirement_stages for all using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'requirement_logs' and policyname = 'demo_requirement_logs_all') then
    create policy demo_requirement_logs_all on public.requirement_logs for all using (true) with check (true);
  end if;
  if not exists (select 1 from pg_policies where schemaname = 'public' and tablename = 'audit_logs' and policyname = 'demo_audit_logs_all') then
    create policy demo_audit_logs_all on public.audit_logs for all using (true) with check (true);
  end if;
end $$;
