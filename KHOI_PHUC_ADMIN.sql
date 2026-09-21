-- ============================================================
-- KHÔI PHỤC TÀI KHOẢN ADMIN (chạy 1 lần trong Supabase Dashboard)
-- Vào: supabase.com -> project của bạn -> SQL Editor -> dán -> Run
-- ============================================================

-- Trong cùng phiên SQL, đặt mật khẩu riêng trước khi chạy:
-- set bqhung.admin_password = 'MAT_KHAU_MOI_CUA_BAN';
-- Không dùng mật khẩu mặc định chung trong mã nguồn.
begin;
do $$
declare new_password text := current_setting('bqhung.admin_password', true);
begin
  if new_password is null or length(new_password) < 12 then
    raise exception 'Dat bqhung.admin_password (it nhat 12 ky tu) truoc khi khoi phuc';
  end if;
  insert into public.app_users(username, pass_hash, role, active)
  values ('admin', extensions.crypt(new_password, extensions.gen_salt('bf')), 'admin', true)
  on conflict (username) do update
    set pass_hash = extensions.crypt(new_password, extensions.gen_salt('bf')),
        role = 'admin', active = true;
end $$;

-- Bản script cũ từng tạo RETURNS void; PostgreSQL không đổi return type
-- bằng CREATE OR REPLACE. Chỉ bỏ đúng hàm đó khi kiểu trả về bị sai.
do $$
begin
  if exists (select 1 from pg_proc p join pg_namespace n on n.oid=p.pronamespace
    where n.nspname='public' and p.proname='app_admin_set_active'
      and p.oid=to_regprocedure('public.app_admin_set_active(text,text,text,boolean)')
      and p.prorettype <> 'text'::regtype) then
    drop function public.app_admin_set_active(text,text,text,boolean);
  end if;
end $$;

-- 2) VÁ: từ nay KHÔNG THỂ khoá tài khoản admin (xoá đã bị chặn sẵn)
create or replace function public.app_admin_set_active(
  p_admin text, p_admin_pass text, p_username text, p_active boolean)
returns text language plpgsql security definer set search_path = public as $$
begin
  if not _is_admin(p_admin, p_admin_pass) then
    return 'NOT_ADMIN';
  end if;
  update app_users set active = p_active
  where lower(username) = lower(p_username) and role <> 'admin';
  return 'OK';
end $$;
grant execute on function public.app_admin_set_active(text,text,text,boolean) to anon;
commit;
