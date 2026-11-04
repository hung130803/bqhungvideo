# Cổng: bấm "Hủy tất cả" lúc Part đang XẾP HÀNG dựng lệnh -> lượt đó bị bỏ, không tạo việc xuất mới.
import os,sys,tempfile,threading,time
T=tempfile.mkdtemp(); os.environ.update(QT_QPA_PLATFORM='offscreen',BQ_DATA_DIR=T,BQ_DB_PATH=T+'/t.db',BQ_QSETTINGS_INI=T+'/s.ini')
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__))); import _test_guard
from PyQt6.QtWidgets import QApplication; qa=QApplication([])
from app.ui.state import AppState
from app.ui.studio_page import StudioPage
from app import services
from app.database.db import db
StudioPage._pipe_resume_auto=lambda s:None
st=AppState(); p=StudioPage(st)
pid=services.create_project('K','Mỹ')
v1=db.execute("INSERT INTO videos(project_id,src_path) VALUES(?,?)",(pid,'/x1.mp4')).lastrowid
v2=db.execute("INSERT INTO videos(project_id,src_path) VALUES(?,?)",(pid,'/x2.mp4')).lastrowid
db.conn().commit()
ev=threading.Event(); applied=[]; res={}
p._export_snap=lambda vid:{}
def prep(vid,only,resume,snap):
    if vid==v1: ev.wait(5)
    return {'vid':vid}
p._export_prepare=prep
p._export_apply=lambda vid,only,val:(applied.append(vid),1)[1]
p._xuat_nen(v1,khi_xong=lambda v,n,l:res.__setitem__(v,(n,l)))
time.sleep(0.2)
p._xuat_nen(v2,khi_xong=lambda v,n,l:res.__setitem__(v,(n,l)))
st.huy_gen+=1   # bấm Hủy tất cả lúc v2 đang xếp hàng
ev.set()
t0=time.time()
while len(res)<2 and time.time()-t0<5: qa.processEvents(); time.sleep(0.02)
print('res',res,'applied',applied)
ok = applied==[] and res[v2][0] is None and 'hủy' in res[v2][1].lower()
print('PASS' if ok else 'FAIL'); os._exit(0 if ok else 1)
