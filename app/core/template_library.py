"""Ready-made editable channel layouts, inserted once without overwriting edits."""
from copy import deepcopy
from app.core.template_backgrounds import encode

_SPECS=[
 ('paper','01 · Giấy ấm — kể chuyện','Kể chuyện / phóng sự','Nền giấy nhăn, mép video uốn cong nhẹ, hai lớp video rõ nét chạy đồng bộ và phụ đề vàng.', '#252222','#fffaf2',True,'Ô sáng chạy từ (vàng)'),
 ('linen','02 · Linen — đời thường','Vlog / đời thường','Nền vải sáng, chữ gọn, chuyển cảnh mềm.', '#323b40','#ffffff',False,'Trắng đơn giản'),
 ('navy','03 · Bản tin — xanh đêm','Tin tức / giải thích','Nền xanh đêm, nhãn sáng, chữ tương phản rõ.', '#ffffff','#213e5a',False,'Ô sáng chạy từ (xanh neon)'),
 ('mint','04 · Ngọc xanh — khám phá','Khám phá / săn đồ','Nền ngọc dịu, hợp khám phá đồ vật, mẹo và hành trình.', '#153d35','#eefbf5',True,'Ô sáng chạy từ (xanh lá)'),
 ('sunset','05 · Cam đào — nhật ký','Vlog / du lịch','Chuyển sắc cam đào, bố cục ấm và nhẹ.', '#4d292d','#fff5ec',True,'Ô sáng chạy từ (vàng)'),
 ('aurora','06 · Cực quang — công nghệ','Công nghệ / gaming','Tím xanh chuyển động chậm, chữ sáng dễ đọc.', '#ffffff','#26284c',True,'Ô sáng chạy từ (xanh neon)'),
 ('graphite','07 · Than chì — công việc','Công việc / kỹ năng','Than chì kín đáo, ưu tiên hình thao tác và phụ đề.', '#ffffff','#29333e',False,'Ô sáng chạy từ (vàng)'),
 ('sand','08 · Cát — tạp chí','Review / lifestyle','Nền cát có đường cong nhẹ, tiêu đề tối trên ô kem.', '#443a29','#fffaed',True,'Trắng đơn giản'),
]

def catalog():
    out=[]
    for theme,name,category,description,ink,card,motion,caption in _SPECS:
        layout=dict(video_rect=[.5,.49,.98],bg=encode(theme,motion,curve=theme in ('paper','sand'),echo=theme=='paper'),fit_src=True,trim_black=False,
            captions=True,cap_font='Be Vietnam Pro',cap_size=.043,cap_color='',cap_ny=.66,
            cap_preset=caption,cap_delay=0.,cap_hook=False,hook_first=False,
            speed=1.,pitch=1.,flip_h=False,che_chu=False,fx_fade=True,fx_whoosh=False,
            chuyen_canh='nhe',hieu_ung='fx:nhe:hat_nhieu,loe_sang,toi_vien,tuong_phan,zoom_day,zoom_lui',bgm_mode='off',orig_vol=1.,
            narr_preset=caption,narr_font='Be Vietnam Pro',narr_size=.043,narr_ny=.72,
            layers=[dict(text='{title}',size=.039,font='Be Vietnam đậm',color=ink,bg=True,
                         bg_color=card,bg_alpha=.97,outline=0.,radius=15,padx=.28,pady=.10,nx=.5,ny=.18,is_part=False),
                    dict(text='Part {n}',size=.032,font='Be Vietnam',color=ink,bg=True,
                         bg_color=card,bg_alpha=.97,outline=0.,radius=12,padx=.35,pady=.15,nx=.5,ny=.79,is_part=True)])
        if theme=='paper':
            layout['video_rect']=[.5,.50,1.]
            layout['cap_ny']=.60;layout['narr_ny']=.68
            layout['layers'][0].update(ny=.235,size=.034,font='Be Vietnam',bg_color='#ffffff')
            layout['layers'][1].update(ny=.75,bg_color='#ffffff')
        out.append(dict(id=theme,name=name,category=category,description=description,layout=layout))
    return deepcopy(out)

def ensure_templates():
    from app import services
    added=[]
    for entry in catalog():
        if services.get_template(entry['name']) is None:
            services.save_template(entry['name'],entry['layout']);added.append(entry['name'])
    return added
