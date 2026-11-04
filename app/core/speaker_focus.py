"""Opt-in conservative speaker crop. Never identify a person from their face."""
import hashlib,json,os,shutil,threading,uuid,math
from pathlib import Path
_LOCK=threading.Lock()
WORKER=''

def directory():
 from config import DATA_DIR
 return Path(DATA_DIR)/'models'/'intelligence50'/'talknet'

def ready():
 p=directory()
 return bool(shutil.which('python.exe')) and all((p/f).exists() for f in
     ('pretrain_TalkSet.model','yunet.onnx','manifest.json','dependencies/python_speech_features','dependencies/scipy'))

def inspect(source,segments,ctx):
 from config import DATA_DIR,settings
 from app.core.analysis_process import supervise
 from app.core.giong_hang import lib_torch
 if not ready() or not WORKER:raise RuntimeError('Bộ TalkNet chưa được cài đầy đủ trên máy này.')
 folder=directory();manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
 for name,expected in manifest['files'].items():
  if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=expected:raise RuntimeError('Model TalkNet thay đổi; cần cài lại bộ đã kiểm tra.')
 src=Path(source);st=src.stat()
 signature=[str(src.resolve()),st.st_size,st.st_mtime_ns,segments,manifest,hashlib.sha256(WORKER.encode()).hexdigest()]
 key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
 cache=Path(DATA_DIR)/'_cache'/'talknet';cache.mkdir(parents=True,exist_ok=True);dest=cache/(key+'.json')
 while not _LOCK.acquire(timeout=.2):ctx.check_canceled()
 try:
  ctx.check_canceled()
  if dest.exists():return json.loads(dest.read_text(encoding='utf-8'))
  name=uuid.uuid4().hex;script=cache/(name+'.py');job=cache/(name+'.job.json');result=cache/(name+'.result.json')
  script.write_text(WORKER,encoding='utf-8')
  from app.core.ffmpeg_utils import probe
  info=probe(source)
  if not info.has_audio:raise RuntimeError('TalkNet cần tiếng gốc để đối chiếu người nói; video này không có âm thanh.')
  job.write_text(json.dumps(dict(source=str(src),segments=segments,ffmpeg=settings.FFMPEG_PATH,
      libraries=[lib_torch(),str(folder/'dependencies')],model_dir=str(folder),output=str(result),width=info.width,height=info.height)),encoding='utf-8')
  try:
   supervise([shutil.which('python.exe'),str(script),str(job)],str(cache),dict(os.environ),ctx,base=.03,span=.04,creationflags=0x08000000)
   now=src.stat()
   if (now.st_size,now.st_mtime_ns)!=(st.st_size,st.st_mtime_ns):raise RuntimeError('Nguồn thay đổi khi dò người nói; chưa dùng kết quả.')
   value=json.loads(result.read_text(encoding='utf-8'));result.replace(dest);return value
  finally:
   for p in (script,job,result):
    try:p.unlink(missing_ok=True)
    except OSError:pass
 finally:_LOCK.release()

def crop_filter(result,segments,width,height,flip=False):
 """Use crop only with sufficient coverage; merge into six-second focus blocks."""
 if width<=height*9/16 or height<2:return None
 total=sum(b-a for a,b in segments);rows=[];offset=0.;covered=0.
 for a,b in segments:
  for row in result.get('windows',[]):
   if not isinstance(row,dict) or row.get('found') is not True:continue
   try:s,e,cx=float(row['start']),float(row['end']),float(row['cx'])
   except (ValueError,TypeError,KeyError):continue
   if not all(math.isfinite(v) for v in (s,e,cx)) or not 0<=cx<=1 or e<=s:continue
   lo,hi=max(a,s),min(b,e)
   if hi<=lo:continue
   rows.append((offset+lo-a,offset+hi-a,1-cx if flip else cx));covered+=hi-lo
  offset+=b-a
 if total<=0 or covered/total<.6:return None
 terms=[];prior=.5
 for start in range(0,math.ceil(total),6):
  end=min(total,start+6)
  relevant=[(max(0,min(end,e)-max(start,s)),cx) for s,e,cx in rows]
  weight=sum(w for w,_ in relevant)
  center=sum(w*cx for w,cx in relevant)/weight if weight>=.6*(end-start) else .5
  terms.append(f"gte(t,{start})*lt(t,{end:.3f})*({prior:.5f}+({center-prior:.5f})*min(1,max(0,(t-{start})/0.6)))")
  prior=center
 # All values are locally generated finite numbers; no model-supplied filter text.
 expression='+'.join(terms)
 crop_width=max(2,int(height*9/16)//2*2)
 return f"{crop_width}:{int(height)//2*2}:'max(0,min(iw-ow,iw*({expression})-ow/2))':0"

WORKER = '"""Bounded active-speaker evaluation on selected source windows only."""\nimport os,sys,json,time\nfrom pathlib import Path\n\ndef publish(kind,progress=0,message=\'\'):\n p=Path(os.environ[\'BQ_ANALYSIS_STATUS_FILE\']);tmp=p.with_suffix(\'.tmp\')\n tmp.write_text(json.dumps(dict(kind=kind,progress=progress,message=message,updated=time.monotonic_ns())),encoding=\'utf-8\')\n for attempt in range(5):\n  try:tmp.replace(p);return\n  except PermissionError:\n   if attempt==4:raise\n   time.sleep(.02)\n\ndef main():\n args=json.loads(Path(sys.argv[1]).read_text(encoding=\'utf-8\'))\n sys.path[:0]=args[\'libraries\']+[args[\'model_dir\']]\n publish(\'progress\',0,\'TalkNet · nạp bộ đối chiếu hình và tiếng\')\n import torch,numpy as np,cv2,subprocess\n from python_speech_features import mfcc\n from model.talkNetModel import talkNetModel\n from loss import lossAV\n torch.set_num_threads(2);cv2.setNumThreads(2)\n state=torch.load(Path(args[\'model_dir\'])/\'pretrain_TalkSet.model\',map_location=\'cpu\',weights_only=True)\n model=talkNetModel().eval();head=lossAV().eval()\n model.load_state_dict({k[6:]:v for k,v in state.items() if k.startswith(\'model.\')})\n head.load_state_dict({k[7:]:v for k,v in state.items() if k.startswith(\'lossAV.\')})\n detector=cv2.FaceDetectorYN.create(str(Path(args[\'model_dir\'])/\'yunet.onnx\'),\'\',(480,270),.8,.3,5000)\n def run(command):\n  r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=90,creationflags=0x08000000)\n  if r.returncode:raise RuntimeError(\'Không đọc được hình/tiếng cho TalkNet\')\n  return r.stdout\n def iou(a,b):\n  x=max(a[0],b[0]);y=max(a[1],b[1]);w=max(0,min(a[0]+a[2],b[0]+b[2])-x);h=max(0,min(a[1]+a[3],b[1]+b[3])-y)\n  inter=w*h;return inter/max(1,a[2]*a[3]+b[2]*b[3]-inter)\n total=sum(b-a for a,b in args[\'segments\']);elapsed=0.;results=[];track_count=0;max_score=None\n for a,b in args[\'segments\']:\n  start=a\n  while start<b-.02:\n   length=min(6.,b-start)\n   base=[args[\'ffmpeg\'],\'-hide_banner\',\'-loglevel\',\'error\',\'-ss\',str(start),\'-i\',args[\'source\'],\'-t\',str(length),\'-threads\',\'2\']\n   raw=run(base+[\'-an\',\'-vf\',\'fps=25,scale=480:270:force_original_aspect_ratio=decrease,pad=480:270:(ow-iw)/2:(oh-ih)/2\',\'-f\',\'rawvideo\',\'-pix_fmt\',\'bgr24\',\'pipe:1\'])\n   if len(raw)%(480*270*3):raise RuntimeError(\'TalkNet nhận khung hình chưa đầy đủ\')\n   frames=np.frombuffer(raw,np.uint8).reshape((-1,270,480,3))\n   audio=np.frombuffer(run(base+[\'-vn\',\'-ac\',\'1\',\'-ar\',\'16000\',\'-f\',\'s16le\',\'pipe:1\']),\'<i2\').copy()\n   tracks=[]\n   for frame_index in range(0,len(frames),5):\n    _,detections=detector.detect(frames[frame_index])\n    boxes=[] if detections is None else [v[:4] for v in detections if min(v[2:4])>=20]\n    assigned=set()\n    for box in sorted(boxes,key=lambda x:x[2]*x[3],reverse=True)[:4]:\n     options=[(iou(track[-1][1],box),i) for i,track in enumerate(tracks)\n              if i not in assigned and frame_index-track[-1][0]<=10]\n     overlap,index=max(options,default=(0.,-1))\n     if overlap<.3:tracks.append([]);index=len(tracks)-1\n     tracks[index].append((frame_index,box));assigned.add(index)\n   votes=[]\n   for track in tracks:\n    if len(track)<5 or track[-1][0]-track[0][0]<20:continue\n    indices=np.array([x[0] for x in track]);boxes=np.array([x[1] for x in track],float)\n    begin,end=int(indices[0]),int(indices[-1])+1\n    face_frames=[]\n    for index in range(begin,end):\n     x,y,w,h=[np.interp(index,indices,boxes[:,j]) for j in range(4)]\n     half=max(w,h)/2;cx=x+w/2;cy=y+h/2;pad=int(half*1.8)+2\n     frame=np.pad(frames[index],((pad,pad),(pad,pad),(0,0)),constant_values=110)\n     # Match the official TalkNet face crop geometry and 112x112 center input.\n     face=frame[int(cy+pad-half):int(cy+pad+half*1.8),int(cx+pad-half*1.4):int(cx+pad+half*1.4)]\n     face=cv2.resize(face,(224,224));face=cv2.cvtColor(face,cv2.COLOR_BGR2GRAY)[56:168,56:168]\n     face_frames.append(face)\n    speech=audio[int(begin/25*16000):int(end/25*16000)]\n    if len(speech)<1600:continue\n    features=mfcc(speech,16000,numcep=13,winlen=.025,winstep=.010)\n    count=min(len(face_frames),len(features)//4)\n    if count<20:continue\n    with torch.inference_mode():\n     va=model.forward_visual_frontend(torch.from_numpy(np.array(face_frames[:count])).float()[None])\n     aa=model.forward_audio_frontend(torch.from_numpy(features[:count*4]).float()[None])\n     aa,va=model.forward_cross_attention(aa,va)\n     scores=head(model.forward_audio_visual_backend(aa,va))\n    track_count+=1;current=float(np.max(scores));max_score=current if max_score is None else max(max_score,current)\n    width=args.get(\'width\',480);height=args.get(\'height\',270)\n    scaled_width=width*min(480/width,270/height);padding=(480-scaled_width)/2\n    center=float((np.median(boxes[:,0]+boxes[:,2]/2)-padding)/scaled_width)\n    votes.append({\'scores\':scores,\'begin\':begin,\'end\':begin+count,\'cx\':min(1.,max(0.,center))})\n   for second in range(int(np.ceil(length))):\n    lo=second*25;hi=min(len(frames),(second+1)*25)\n    ranked=[]\n    for vote in votes:\n     left=max(lo,vote[\'begin\']);right=min(hi,vote[\'end\'])\n     if right-left<max(10,(hi-lo)*.8):continue\n     ranked.append({\'score\':float(np.median(vote[\'scores\'][left-vote[\'begin\']:right-vote[\'begin\']])),\'cx\':vote[\'cx\']})\n    ranked.sort(key=lambda x:x[\'score\'],reverse=True)\n    best=ranked[0] if ranked else None\n    certain=bool(best and best[\'score\']>0 and (len(ranked)==1 or best[\'score\']-ranked[1][\'score\']>=.5))\n    results.append({\'start\':round(start+second,3),\'end\':round(min(start+length,start+second+1),3),\n                    \'found\':certain,\'cx\':round(best[\'cx\'],5) if certain else .5})\n   elapsed+=length;start+=length\n   publish(\'progress\',elapsed/max(1,total),f\'TalkNet · đã kiểm tra {elapsed:.0f}/{total:.0f} giây cảnh được chọn\')\n output=Path(args[\'output\']);temp=output.with_suffix(\'.tmp\')\n temp.write_text(json.dumps({\'engine\':\'talknet\',\'windows\':results,\'evaluated_tracks\':track_count,\'maximum_raw_score\':max_score}),encoding=\'utf-8\');temp.replace(output)\n publish(\'done\',1,\'TalkNet · đã lưu vị trí người nói; đoạn không chắc giữ nguyên khung\')\n\nif __name__==\'__main__\':\n try:main()\n except Exception as exc:publish(\'error\',0,str(exc));sys.exit(1)\n'
