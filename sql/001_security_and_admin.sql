-- =====================================================================
-- Traders Lab: security hardening + admin / credits / staff management
-- Run once in the Supabase SQL Editor. The script is idempotent
-- (safe to run again).
--
-- BEFORE RUNNING: replace CHANGE_ME@example.com below with YOUR e-mail
-- (the one you log in with). It is used to
--   1) claim all legacy rows that have no user_id yet, and
--   2) create the first admin.
-- =====================================================================
begin;

-- ---------------------------------------------------------------------
-- 0. Settings: your e-mail (kept only in the database, not in the repo)
-- ---------------------------------------------------------------------
-- (transaction-local setting; no temporary table, so Supabase shows no RLS warning)
select set_config('tl.owner_email', 'CHANGE_ME@example.com', true);

do $$
declare v_email text; v_uid uuid;
begin
  v_email := current_setting('tl.owner_email');
  if v_email is null or v_email like 'CHANGE_ME%' then
    raise exception 'Edit the e-mail at the top of this script first (CHANGE_ME@example.com).';
  end if;
  select id into v_uid from auth.users where lower(email) = lower(v_email);
  if v_uid is null then
    raise exception 'No auth user with e-mail % - register/log in once first.', v_email;
  end if;
end $$;

-- ---------------------------------------------------------------------
-- 1. Data tables: create the ones that do not exist yet, add user_id
--    (default = the calling user)
-- ---------------------------------------------------------------------
create table if not exists public.user_settings (
  id        bigserial primary key,
  category  text not null,
  item_name text not null,
  user_id   uuid default auth.uid()
);
create table if not exists public.balance_transactions (
  "Transaction ID" text primary key,
  "Date"           text,
  "Amount"         numeric,
  "Description"    text,
  user_id          uuid default auth.uid()
);

alter table public.trades               add column if not exists user_id uuid;
alter table public.user_settings        add column if not exists user_id uuid;
alter table public.balance_transactions add column if not exists user_id uuid;

-- user_id may have been created as text in older versions: convert it to uuid
do $$
declare t text; v_type text;
begin
  foreach t in array array['trades', 'user_settings', 'balance_transactions'] loop
    select data_type into v_type from information_schema.columns
     where table_schema = 'public' and table_name = t and column_name = 'user_id';
    if v_type is not null and v_type <> 'uuid' then
      execute format('alter table public.%I alter column user_id drop default', t);
      execute format(
        'alter table public.%I alter column user_id type uuid
           using (case when user_id::text ~* ''^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$''
                       then user_id::text::uuid else null end)', t);
    end if;
  end loop;
end $$;

alter table public.trades               alter column user_id set default auth.uid();
alter table public.user_settings        alter column user_id set default auth.uid();
alter table public.balance_transactions alter column user_id set default auth.uid();

-- legacy rows (created before multi-user support) belong to the owner
do $$
declare v_uid uuid;
begin
  select id into v_uid from auth.users where lower(email) = lower(current_setting('tl.owner_email'));
  update public.trades               set user_id = v_uid where user_id is null;
  update public.user_settings        set user_id = v_uid where user_id is null;
  update public.balance_transactions set user_id = v_uid where user_id is null;
end $$;

create index if not exists trades_user_id_idx               on public.trades (user_id);
create index if not exists user_settings_user_id_idx        on public.user_settings (user_id);
create index if not exists balance_transactions_user_id_idx on public.balance_transactions (user_id);

-- ---------------------------------------------------------------------
-- 2. Row Level Security: everybody sees and edits only their own rows
-- ---------------------------------------------------------------------
do $$
declare t text;
begin
  foreach t in array array['trades', 'user_settings', 'balance_transactions'] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists %I on public.%I', t || '_own_all', t);
    execute format(
      'create policy %I on public.%I for all to authenticated
         using (user_id = auth.uid()) with check (user_id = auth.uid())',
      t || '_own_all', t);
    execute format('revoke all on public.%I from anon', t);
  end loop;
end $$;

-- ---------------------------------------------------------------------
-- 3. Staff roles (admins / mentors) - managed from the admin panel
-- ---------------------------------------------------------------------
create table if not exists public.staff_roles (
  email      text primary key,
  role       text not null check (role in ('admin', 'mentor')),
  added_by   text,
  created_at timestamptz not null default now(),
  constraint staff_email_lowercase check (email = lower(email))
);
alter table public.staff_roles enable row level security;
revoke all on public.staff_roles from anon, authenticated;

insert into public.staff_roles (email, role, added_by)
select lower(current_setting('tl.owner_email')), 'admin', 'bootstrap'
on conflict (email) do update set role = 'admin';

create or replace function public.is_admin()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from public.staff_roles
    where email = lower(coalesce(auth.jwt() ->> 'email', '')) and role = 'admin'
  );
$$;

create or replace function public.my_staff_role()
returns text language sql stable security definer set search_path = public as $$
  select role from public.staff_roles
  where email = lower(coalesce(auth.jwt() ->> 'email', ''));
$$;

-- ---------------------------------------------------------------------
-- 4. user_preferences: users may change only cosmetic columns
-- ---------------------------------------------------------------------
create table if not exists public.user_preferences (
  user_id uuid primary key references auth.users (id) on delete cascade
);
alter table public.user_preferences add column if not exists "User_Mail"                text;
alter table public.user_preferences add column if not exists credits_balance            numeric not null default 10;
alter table public.user_preferences add column if not exists subscription_status        text    not null default 'active';
alter table public.user_preferences add column if not exists subscription_expires_at    timestamptz;
alter table public.user_preferences add column if not exists language                   text;
alter table public.user_preferences add column if not exists theme                      text;
alter table public.user_preferences add column if not exists mobile_view_mode           text;
alter table public.user_preferences add column if not exists desktop_view_mode          text;
alter table public.user_preferences add column if not exists created_at                 timestamptz not null default now();

-- normalise column types of pre-existing columns (they may have been created as text / float)
do $$
declare v_type text;
begin
  select data_type into v_type from information_schema.columns
   where table_schema = 'public' and table_name = 'user_preferences' and column_name = 'subscription_expires_at';
  if v_type <> 'timestamp with time zone' then
    alter table public.user_preferences
      alter column subscription_expires_at type timestamptz
      using nullif(btrim(subscription_expires_at::text), '')::timestamptz;
  end if;

  select data_type into v_type from information_schema.columns
   where table_schema = 'public' and table_name = 'user_preferences' and column_name = 'credits_balance';
  if v_type <> 'numeric' then
    alter table public.user_preferences
      alter column credits_balance type numeric using coalesce(credits_balance, 0)::numeric;
  end if;
end $$;

-- repair legacy rows, then enforce sane defaults
update public.user_preferences set subscription_status = 'active' where subscription_status is null;
update public.user_preferences set credits_balance = 0 where credits_balance is null;
alter table public.user_preferences
  alter column subscription_status set default 'active',
  alter column subscription_status set not null,
  alter column credits_balance set default 10,
  alter column credits_balance set not null;

alter table public.user_preferences enable row level security;
drop policy if exists "Enable all actions for users based on user_id" on public.user_preferences;
drop policy if exists prefs_select_own on public.user_preferences;
drop policy if exists prefs_update_own on public.user_preferences;
create policy prefs_select_own on public.user_preferences
  for select to authenticated using (user_id = auth.uid());
create policy prefs_update_own on public.user_preferences
  for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());

revoke all on public.user_preferences from anon, authenticated;
grant select on public.user_preferences to authenticated;
grant update (language, theme, mobile_view_mode, desktop_view_mode)
  on public.user_preferences to authenticated;

-- every new account gets a preferences row (10 free credits, active)
create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
begin
  insert into public.user_preferences (user_id, "User_Mail")
  values (new.id, new.email)
  on conflict (user_id) do nothing;
  return new;
end $$;

drop trigger if exists on_auth_user_created_prefs on auth.users;
create trigger on_auth_user_created_prefs
  after insert on auth.users
  for each row execute function public.handle_new_user();

-- accounts that exist but have no row yet (created before this script)
insert into public.user_preferences (user_id, "User_Mail")
select u.id, u.email from auth.users u
on conflict (user_id) do nothing;

-- fallback for accounts without a row (the app calls this once on login)
create or replace function public.ensure_my_preferences()
returns jsonb language plpgsql security definer set search_path = public as $$
declare v_uid uuid := auth.uid();
begin
  if v_uid is null then raise exception 'not_authenticated'; end if;
  insert into public.user_preferences (user_id, "User_Mail")
  values (v_uid, auth.jwt() ->> 'email')
  on conflict (user_id) do nothing;
  return (select to_jsonb(p) from public.user_preferences p where p.user_id = v_uid);
end $$;

-- ---------------------------------------------------------------------
-- 5. Credit ledger + atomic spend / refund
-- ---------------------------------------------------------------------
create table if not exists public.credit_ledger (
  id            bigserial primary key,
  user_id       uuid not null references auth.users (id) on delete cascade,
  kind          text not null check (kind in ('spend', 'refund', 'admin')),
  delta         numeric not null,
  balance_after numeric not null,
  reason        text,
  actor         text,
  refund_of     bigint references public.credit_ledger (id),
  created_at    timestamptz not null default now()
);
create unique index if not exists credit_ledger_one_refund_per_spend
  on public.credit_ledger (refund_of) where refund_of is not null;
create index if not exists credit_ledger_user_idx on public.credit_ledger (user_id, created_at desc);

alter table public.credit_ledger enable row level security;
drop policy if exists ledger_select_own on public.credit_ledger;
create policy ledger_select_own on public.credit_ledger
  for select to authenticated using (user_id = auth.uid() or public.is_admin());
revoke all on public.credit_ledger from anon, authenticated;
grant select on public.credit_ledger to authenticated;

create or replace function public.has_active_subscription(p_uid uuid)
returns boolean language sql stable security definer set search_path = public as $$
  select coalesce((
    select p.subscription_status in ('active', 'trial')
           and (p.subscription_expires_at is null or p.subscription_expires_at > now())
    from public.user_preferences p where p.user_id = p_uid
  ), false);
$$;

-- the old single-argument version returned a bare number
drop function if exists public.spend_credits(numeric);
drop function if exists public.spend_credits(double precision);

create or replace function public.spend_credits(p_amount numeric, p_reason text default 'spend')
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  v_uid uuid := auth.uid();
  v_balance numeric;
  v_entry bigint;
begin
  if v_uid is null then
    return jsonb_build_object('ok', false, 'error', 'not_authenticated');
  end if;
  if p_amount is null or p_amount <= 0 or p_amount > 50 then
    return jsonb_build_object('ok', false, 'error', 'invalid_amount');
  end if;
  if not public.has_active_subscription(v_uid) then
    return jsonb_build_object('ok', false, 'error', 'subscription_inactive');
  end if;

  update public.user_preferences
     set credits_balance = credits_balance - p_amount
   where user_id = v_uid and credits_balance >= p_amount
  returning credits_balance into v_balance;

  if not found then
    return jsonb_build_object('ok', false, 'error', 'insufficient_credits');
  end if;

  insert into public.credit_ledger (user_id, kind, delta, balance_after, reason, actor)
  values (v_uid, 'spend', -p_amount, v_balance, left(coalesce(p_reason, 'spend'), 100), 'self')
  returning id into v_entry;

  return jsonb_build_object('ok', true, 'balance', v_balance, 'entry_id', v_entry);
end $$;

-- gives back a spend that did not produce a result (e.g. the AI call failed);
-- only the caller's own spend, only once, only within 15 minutes
create or replace function public.refund_spend(p_entry_id bigint)
returns jsonb language plpgsql security definer set search_path = public as $$
declare
  v_uid uuid := auth.uid();
  v_row public.credit_ledger%rowtype;
  v_balance numeric;
begin
  if v_uid is null then
    return jsonb_build_object('ok', false, 'error', 'not_authenticated');
  end if;

  select * into v_row from public.credit_ledger
   where id = p_entry_id and user_id = v_uid and kind = 'spend'
     and created_at > now() - interval '15 minutes'
   for update;
  if not found then
    return jsonb_build_object('ok', false, 'error', 'not_refundable');
  end if;
  if exists (select 1 from public.credit_ledger where refund_of = v_row.id) then
    return jsonb_build_object('ok', false, 'error', 'already_refunded');
  end if;

  update public.user_preferences
     set credits_balance = credits_balance + (-v_row.delta)
   where user_id = v_uid
  returning credits_balance into v_balance;

  insert into public.credit_ledger (user_id, kind, delta, balance_after, reason, actor, refund_of)
  values (v_uid, 'refund', -v_row.delta, v_balance, 'refund: ' || coalesce(v_row.reason, ''), 'self', v_row.id);

  return jsonb_build_object('ok', true, 'balance', v_balance);
end $$;

-- ---------------------------------------------------------------------
-- 6. Admin audit log + admin functions (all re-check is_admin())
-- ---------------------------------------------------------------------
create table if not exists public.admin_audit_log (
  id          bigserial primary key,
  actor_email text not null,
  action      text not null,
  target      text,
  details     jsonb,
  created_at  timestamptz not null default now()
);
alter table public.admin_audit_log enable row level security;
revoke all on public.admin_audit_log from anon, authenticated;

create or replace function public._require_admin()
returns text language plpgsql stable security definer set search_path = public as $$
begin
  if not public.is_admin() then
    raise exception 'not_admin' using errcode = '42501';
  end if;
  return lower(auth.jwt() ->> 'email');
end $$;
revoke all on function public._require_admin() from public, anon, authenticated;

create or replace function public.admin_list_users()
returns table (
  user_id uuid, email text, credits_balance numeric, subscription_status text,
  subscription_expires_at timestamptz, created_at timestamptz,
  last_sign_in_at timestamptz, trades_count bigint
) language plpgsql stable security definer set search_path = public as $$
begin
  perform public._require_admin();
  return query
    select u.id, u.email::text, p.credits_balance, p.subscription_status,
           p.subscription_expires_at, u.created_at, u.last_sign_in_at,
           (select count(*) from public.trades t
             where t.user_id = u.id and t."ActionType" ilike '%Start Row%')
      from auth.users u
      left join public.user_preferences p on p.user_id = u.id
     order by u.created_at desc;
end $$;

create or replace function public.admin_adjust_credits(p_user uuid, p_delta numeric, p_reason text default null)
returns jsonb language plpgsql security definer set search_path = public as $$
declare v_actor text := public._require_admin(); v_balance numeric;
begin
  if p_delta is null or p_delta = 0 or abs(p_delta) > 100000 then
    return jsonb_build_object('ok', false, 'error', 'invalid_amount');
  end if;
  update public.user_preferences
     set credits_balance = credits_balance + p_delta
   where user_id = p_user and credits_balance + p_delta >= 0
  returning credits_balance into v_balance;
  if not found then
    return jsonb_build_object('ok', false, 'error',
      case when exists (select 1 from public.user_preferences where user_id = p_user)
           then 'would_go_negative' else 'user_not_found' end);
  end if;
  insert into public.credit_ledger (user_id, kind, delta, balance_after, reason, actor)
  values (p_user, 'admin', p_delta, v_balance, left(coalesce(p_reason, 'admin adjustment'), 200), v_actor);
  insert into public.admin_audit_log (actor_email, action, target, details)
  values (v_actor, 'adjust_credits', p_user::text,
          jsonb_build_object('delta', p_delta, 'balance_after', v_balance, 'reason', p_reason));
  return jsonb_build_object('ok', true, 'balance', v_balance);
end $$;

create or replace function public.admin_set_subscription(
  p_user uuid, p_status text, p_expires timestamptz default null, p_clear_expiry boolean default false)
returns jsonb language plpgsql security definer set search_path = public as $$
declare v_actor text := public._require_admin(); v_row public.user_preferences%rowtype;
begin
  if p_status not in ('active', 'trial', 'suspended', 'cancelled') then
    return jsonb_build_object('ok', false, 'error', 'invalid_status');
  end if;
  update public.user_preferences
     set subscription_status = p_status,
         subscription_expires_at = case when p_clear_expiry then null
                                        else coalesce(p_expires, subscription_expires_at) end
   where user_id = p_user
  returning * into v_row;
  if not found then
    return jsonb_build_object('ok', false, 'error', 'user_not_found');
  end if;
  insert into public.admin_audit_log (actor_email, action, target, details)
  values (v_actor, 'set_subscription', p_user::text,
          jsonb_build_object('status', v_row.subscription_status, 'expires_at', v_row.subscription_expires_at));
  return jsonb_build_object('ok', true, 'status', v_row.subscription_status,
                            'expires_at', v_row.subscription_expires_at);
end $$;

create or replace function public.admin_credit_history(p_user uuid, p_limit int default 30)
returns setof public.credit_ledger language plpgsql stable security definer set search_path = public as $$
begin
  perform public._require_admin();
  return query select * from public.credit_ledger
                where user_id = p_user order by id desc limit least(greatest(p_limit, 1), 200);
end $$;

create or replace function public.admin_list_staff()
returns setof public.staff_roles language plpgsql stable security definer set search_path = public as $$
begin
  perform public._require_admin();
  return query select * from public.staff_roles order by role, email;
end $$;

create or replace function public.admin_set_staff(p_email text, p_role text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare v_actor text := public._require_admin(); v_email text := lower(trim(coalesce(p_email, '')));
begin
  if v_email !~ '^[^@\s]+@[^@\s]+\.[^@\s]+$' then
    return jsonb_build_object('ok', false, 'error', 'invalid_email');
  end if;
  if p_role not in ('admin', 'mentor') then
    return jsonb_build_object('ok', false, 'error', 'invalid_role');
  end if;
  if v_email = v_actor and p_role <> 'admin' then
    return jsonb_build_object('ok', false, 'error', 'cannot_demote_self');
  end if;
  insert into public.staff_roles (email, role, added_by) values (v_email, p_role, v_actor)
  on conflict (email) do update set role = excluded.role;
  insert into public.admin_audit_log (actor_email, action, target, details)
  values (v_actor, 'set_staff', v_email, jsonb_build_object('role', p_role));
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_remove_staff(p_email text)
returns jsonb language plpgsql security definer set search_path = public as $$
declare v_actor text := public._require_admin(); v_email text := lower(trim(coalesce(p_email, '')));
begin
  if v_email = v_actor then
    return jsonb_build_object('ok', false, 'error', 'cannot_remove_self');
  end if;
  delete from public.staff_roles where email = v_email;
  if not found then
    return jsonb_build_object('ok', false, 'error', 'not_found');
  end if;
  insert into public.admin_audit_log (actor_email, action, target)
  values (v_actor, 'remove_staff', v_email);
  return jsonb_build_object('ok', true);
end $$;

create or replace function public.admin_audit_list(p_limit int default 50)
returns setof public.admin_audit_log language plpgsql stable security definer set search_path = public as $$
begin
  perform public._require_admin();
  return query select * from public.admin_audit_log order by id desc limit least(greatest(p_limit, 1), 500);
end $$;

-- ---------------------------------------------------------------------
-- 7. Function privileges: only signed-in users may call the RPCs
-- ---------------------------------------------------------------------
do $$
declare f text;
begin
  foreach f in array array[
    'is_admin()', 'my_staff_role()', 'ensure_my_preferences()',
    'spend_credits(numeric, text)', 'refund_spend(bigint)',
    'admin_list_users()', 'admin_adjust_credits(uuid, numeric, text)',
    'admin_set_subscription(uuid, text, timestamptz, boolean)',
    'admin_credit_history(uuid, int)', 'admin_list_staff()',
    'admin_set_staff(text, text)', 'admin_remove_staff(text)', 'admin_audit_list(int)'
  ] loop
    execute format('revoke all on function public.%s from public, anon', f);
    execute format('grant execute on function public.%s to authenticated', f);
  end loop;
end $$;
revoke all on function public.has_active_subscription(uuid) from public, anon, authenticated;
revoke all on function public.handle_new_user() from public, anon, authenticated;

-- ---------------------------------------------------------------------
-- 8. Storage (bucket "screenshots"): upload / delete only inside own folder
--    Reading stays public (the bucket is public; links are unguessable).
-- ---------------------------------------------------------------------
drop policy if exists screenshots_insert_own on storage.objects;
drop policy if exists screenshots_update_own on storage.objects;
drop policy if exists screenshots_delete_own on storage.objects;
create policy screenshots_insert_own on storage.objects for insert to authenticated
  with check (bucket_id = 'screenshots' and (storage.foldername(name))[1] = auth.uid()::text);
create policy screenshots_update_own on storage.objects for update to authenticated
  using (bucket_id = 'screenshots' and (storage.foldername(name))[1] = auth.uid()::text)
  with check (bucket_id = 'screenshots' and (storage.foldername(name))[1] = auth.uid()::text);
create policy screenshots_delete_own on storage.objects for delete to authenticated
  using (bucket_id = 'screenshots' and (storage.foldername(name))[1] = auth.uid()::text);

commit;
