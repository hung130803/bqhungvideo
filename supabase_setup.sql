-- ============================================================
-- BQ Hung Video — cài đặt MÁY CHỦ TÀI KHOẢN (chạy 1 lần trên Supabase)
-- Mở Supabase project -> SQL Editor -> dán toàn bộ file này -> Run.
-- ============================================================

create extension if not exists pgcrypto with schema extensions;

create table if not exists app_users (
  id         bigint generated always as identity primary key,
  username   text unique not null,
  pass_hash  text not null,
  role       text not null default 'user' check (role in ('admin','user')),
  active     boolean not null default true,
  note       text default '',
  created_at timestamptz default now()
);

-- Chặn MỌI truy cập trực tiếp bằng anon key. Chỉ đi qua các hàm bên dưới.
alter table app_users enable row level security;

-- ---- Đăng nhập: trả username+role nếu đúng mật khẩu và tài khoản đang mở ----
create or replace function app_login(p_username text, p_password text)
returns table(username text, role text)
language sql security definer set search_path = public as $$
  select u.username, u.role from app_users u
  where lower(u.username) = lower(p_username)
    and u.active = true
    and u.pass_hash = extensions.crypt(p_password, u.pass_hash);
$$;

-- ---- Kiểm tra 1 cặp admin hợp lệ (nội bộ, không cấp cho anon) ----
create or replace function _is_admin(p_admin text, p_admin_pass text)
returns boolean language sql security definer set search_path = public as $$
  select exists(
    select 1 from app_users u
    where lower(u.username) = lower(p_admin) and u.role = 'admin'
      and u.active = true and u.pass_hash = extensions.crypt(p_admin_pass, u.pass_hash));
$$;

-- ---- Admin: tạo mới HOẶC đặt lại mật khẩu/quyền 1 user ----
create or replace function app_admin_upsert_user(
  p_admin text, p_admin_pass text,
  p_username text, p_password text, p_role text default 'user')
returns text language plpgsql security definer set search_path = public as $$
begin
  if not _is_admin(p_admin, p_admin_pass) then return 'NOT_ADMIN'; end if;
  if coalesce(p_role,'user') not in ('admin','user') then p_role := 'user'; end if;
  insert into app_users(username, pass_hash, role, active)
    values (p_username, extensions.crypt(p_password, extensions.gen_salt('bf')), p_role, true)
  on conflict (username) do update
    set pass_hash = excluded.pass_hash, role = excluded.role, active = true;
  return 'OK';
end; $$;

-- ---- Admin: khoá / mở 1 user ----
create or replace function app_admin_set_active(
  p_admin text, p_admin_pass text, p_username text, p_active boolean)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not _is_admin(p_admin, p_admin_pass) then return 'NOT_ADMIN'; end if;
  update app_users set active = p_active
  where lower(username) = lower(p_username) and role <> 'admin';  -- KHÔNG khoá admin
  return 'OK';
end; $$;

-- ---- Admin: xoá 1 user (không cho xoá admin) ----
create or replace function app_admin_delete_user(
  p_admin text, p_admin_pass text, p_username text)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not _is_admin(p_admin, p_admin_pass) then return 'NOT_ADMIN'; end if;
  delete from app_users where lower(username) = lower(p_username) and role <> 'admin';
  return 'OK';
end; $$;

-- ---- Admin: liệt kê tất cả user ----
create or replace function app_admin_list_users(p_admin text, p_admin_pass text)
returns table(username text, role text, active boolean, note text,
              created_at timestamptz)
language plpgsql security definer set search_path = public as $$
begin
  if not _is_admin(p_admin, p_admin_pass) then return; end if;
  return query select u.username, u.role, u.active, u.note, u.created_at
    from app_users u order by u.created_at;
end; $$;

-- Cho phép anon GỌI (execute) các hàm công khai. _is_admin KHÔNG cấp (nội bộ).
grant execute on function app_login(text,text) to anon;
grant execute on function app_admin_upsert_user(text,text,text,text,text) to anon;
grant execute on function app_admin_set_active(text,text,text,boolean) to anon;
grant execute on function app_admin_delete_user(text,text,text) to anon;
grant execute on function app_admin_list_users(text,text) to anon;

-- ---- Tài khoản ADMIN đầu tiên: admin / doimatkhau123  (ĐỔI NGAY sau khi vào) ----
insert into app_users(username, pass_hash, role)
  values ('admin', extensions.crypt('doimatkhau123', extensions.gen_salt('bf')), 'admin')
  on conflict (username) do nothing;
