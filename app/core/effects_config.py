"""Explicit effect pools; old levels retain their original selection behavior."""
NEW_KEYS={'nhay_don_mem','nhip_sang_doi','mau_am_diu','mau_lanh_diu','mau_phim_cu','mau_don_sac','mau_ruc_nhe','mau_pastel'}
PACKS={
 'Kể chuyện — gọn, rõ':('zoom_day','zoom_lui','loe_sang','toi_vien','hat_nhieu','tuong_phan'),
 'Nhịp nhanh — nháy / zoom':('zoom_nhoi','rung_lac','nhay_don_mem','nhip_sang_doi','loe_sang','luot_ngang','zoom_lui'),
 'Phim — màu / ánh sáng':('mau_am_diu','mau_lanh_diu','mau_phim_cu','mau_don_sac','mau_pastel','toi_vien','zoom_day'),
 'Gaming — glitch / chuyển động':('xao_khoi','xao_doc','doi_o','rung_xoay','luot_doc','nhay_don_mem','mau_ruc_nhe'),
 'Khám phá — sáng, ít rung':('zoom_day','zoom_lui','tuong_phan','loe_sang','mau_am_diu','mau_ruc_nhe'),
}
def parse(value):
    from app.core.hieu_ung import KHO
    text=str(value or '').strip().lower()
    if text in ('tat','nhe','vua','manh'):return text,None
    fields=text.split(':',2)
    if len(fields)==3 and fields[0]=='fx' and fields[1] in ('tat','nhe','vua','manh'):
        return fields[1],tuple(sorted({k for k in fields[2].split(',') if k in KHO}))
    return 'tat',None
def encode(level,keys):
    from app.core.hieu_ung import KHO
    level=level if level in ('tat','nhe','vua','manh') else 'tat'
    if keys is None:return level
    return 'fx:'+level+':'+','.join(sorted({k for k in keys if k in KHO}))
def allowed(available,keys):
    return [k for k in available if k in keys] if keys is not None else [k for k in available if k not in NEW_KEYS]
def category(key,h):
    if key in NEW_KEYS and key.startswith('mau_'):return 'Tông màu'
    if h.nhom=='lop_phu':return 'Lớp phủ / hạt'
    if any(s in key for s in ('zoom','rung','luot','nghieng','phoi','meo','xien')):return 'Zoom / chuyển động'
    if any(s in key for s in ('sang','nhay','chop','tuong_phan','toi_vien')):return 'Nháy / ánh sáng'
    if any(s in key for s in ('glitch','xao','dong','bang','o_vuong','doi_o','truot')):return 'Glitch / hình học'
    return 'Phim / khác'
def register(H,add,pools):
    # Only used when explicitly selected. New color looks intentionally change chroma.
    wave="sin(PI*(t-{a})/({b}-{a}))"
    entries=[
      ('nhay_don_mem','Nháy đơn êm',"eq=brightness='{p1}*"+wave+"':eval=frame{en}",((.035,.10),),('caotrao','noi','hook')),
      ('nhip_sang_doi','Hai nhịp sáng nhẹ',"eq=brightness='{p1}*pow(sin(2*PI*(t-{a})/({b}-{a})),2)':eval=frame{en}",((.025,.07),),('caotrao','noi','hook')),
      ('mau_am_diu','Tông ấm dịu',"eq=gamma_r='1+{p1}*"+wave+"':gamma_b='1-{p1}*"+wave+"':eval=frame{en}",((.03,.12),),('ke','tinh','chot','noi')),
      ('mau_lanh_diu','Tông lạnh dịu',"eq=gamma_b='1+{p1}*"+wave+"':gamma_r='1-{p1}*"+wave+"':eval=frame{en}",((.03,.12),),('ke','tinh','chot','noi')),
      ('mau_phim_cu','Màu phim hoài niệm',"eq=saturation='1-{p1}*"+wave+"':gamma_r='1+0.06*"+wave+"':eval=frame{en}",((.20,.50),),('ke','tinh','chot')),
      ('mau_don_sac','Chuyển đơn sắc ngắn',"hue=s='1-{p1}*"+wave+"'{en}",((.5,1.),),('ke','tinh','chot','noi')),
      ('mau_ruc_nhe','Nhấn màu rực nhẹ',"eq=saturation='1+{p1}*"+wave+"':eval=frame{en}",((.10,.30),),('caotrao','dong','noi','hook')),
      ('mau_pastel','Màu pastel mềm',"eq=saturation='1-{p1}*"+wave+"':brightness='0.035*"+wave+"':eval=frame{en}",((.10,.30),),('ke','tinh','chot')),
    ]
    for key,name,expr,params,kinds in entries:
        add(H(key,name,name,'thuan',expr,ts=params,dai=.70,hop=kinds,ghi_chu='Chỉ chạy khi chọn trong kho. Tông màu làm thay đổi màu hình trong thời gian ngắn.'))
        for kind in kinds:pools[kind]=tuple(pools.get(kind,()))+(key,)
