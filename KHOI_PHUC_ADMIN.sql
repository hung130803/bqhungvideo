-- ============================================================
-- KHÔI PHỤC TÀI KHOẢN ADMIN (chạy 1 lần trong Supabase Dashboard)
-- Vào: supabase.com -> project của bạn -> SQL Editor -> dán -> Run
-- ============================================================

-- 1) Tạo lại / sửa lại tài khoản admin (user: admin, mật khẩu: hungbeta)
insert into app_users(username, pass_hash, role, active)
values ('admin', extensions.crypt('hungbeta', extensions.gen_salt('bf')),
        'admin', true)
on conflict (username) do update
  set pass_hash = extensions.crypt('hungbeta', extensions.gen_salt('bf')),
      role = 'admin', active = true;

-- 2) VÁ: từ nay KHÔNG THỂ khoá tài khoản admin (xoá đã bị chặn sẵn)
create or replace function app_admin_set_active(
  p_admin text, p_admin_pass text, p_username text, p_active boolean)
returns void language plpgsql security definer as $$
begin
  if not _is_admin(p_admin, p_admin_pass) then
    raise exception 'not admin';
  end if;
  update app_users set active = p_active
  where lower(username) = lower(p_username) and role <> 'admin';
end $$;
