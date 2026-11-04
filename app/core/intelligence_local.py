"""Optional local scene worker with durable cache and cancellation."""
import hashlib,json,os,shutil,threading,uuid
from pathlib import Path
_LOCK=threading.Lock()
WORKER = ''  # Filled with the reviewed standalone worker by patch_local.py.

def directory():
 from config import DATA_DIR
 return Path(DATA_DIR)/'models'/'intelligence50'

def ready():
 folder=directory()
 return bool(shutil.which('python.exe')) and all((folder/p).is_file() for p in
     ('transnetv2.pth','transnetv2_pytorch.py','manifest.json'))

def scenes(source,duration,ctx):
 from config import DATA_DIR,settings
 from app.core.analysis_process import supervise
 from app.core.giong_hang import lib_torch
 if not WORKER:raise RuntimeError('Bộ dò cảnh chưa đóng gói đầy đủ.')
 if not ready():raise RuntimeError('Chưa cài bộ TransNet trên máy này. Tắt tùy chọn hoặc cài bộ dò cảnh trước.')
 folder=directory();manifest=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
 for name in ('transnetv2.pth','transnetv2_pytorch.py'):
  if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=manifest[name]:
   raise RuntimeError('Tệp TransNet không khớp bản đã kiểm tra; cần cài lại bộ dò cảnh.')
 src=Path(source);stat=src.stat();signature=[str(src.resolve()),stat.st_size,stat.st_mtime_ns,duration,manifest]
 key=hashlib.sha256(json.dumps(signature,sort_keys=True).encode()).hexdigest()
 cache=Path(DATA_DIR)/'_cache'/'transnet';cache.mkdir(parents=True,exist_ok=True)
 target=cache/(key+'.json')
 while not _LOCK.acquire(timeout=.2):ctx.check_canceled()
 try:
  ctx.check_canceled()
  if target.exists():return json.loads(target.read_text(encoding='utf-8'))
  identifier=uuid.uuid4().hex;script=cache/(identifier+'.py');job=cache/(identifier+'.job.json')
  result=cache/(identifier+'.result.json')
  script.write_text(WORKER,encoding='utf-8')
  job.write_text(json.dumps(dict(source=str(src),duration=duration,ffmpeg=settings.FFMPEG_PATH,
       model_dir=str(folder),libraries=[lib_torch()],output=str(result))),encoding='utf-8')
  try:
   supervise([shutil.which('python.exe'),str(script),str(job)],str(cache),dict(os.environ),ctx,
             base=.01,span=.02,creationflags=0x08000000)
   now=src.stat()
   if (now.st_size,now.st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):
    raise RuntimeError('Nguồn thay đổi khi dò cảnh; không dùng kết quả cũ.')
   value=json.loads(result.read_text(encoding='utf-8'))
   result.replace(target)
   return value
  finally:
   for p in (script,job,result):
    try:p.unlink(missing_ok=True)
    except OSError:pass
 finally:_LOCK.release()

WORKER = '"""Standalone worker. PyTorch is loaded only in the child, never beside Qt."""\nimport json,os,sys,time\nfrom pathlib import Path\n\ndef publish(kind,progress=0,message=\'\'):\n p=Path(os.environ[\'BQ_ANALYSIS_STATUS_FILE\']);tmp=p.with_suffix(\'.tmp\')\n tmp.write_text(json.dumps(dict(kind=kind,progress=progress,message=message,updated=time.monotonic_ns())),encoding=\'utf-8\')\n for attempt in range(5):\n  try:tmp.replace(p);return\n  except PermissionError:\n   if attempt==4:raise\n   time.sleep(.02)\n\ndef main():\n args=json.loads(Path(sys.argv[1]).read_text(encoding=\'utf-8\'))\n sys.path[:0]=args[\'libraries\']+[args[\'model_dir\']]\n publish(\'progress\',0,\'Nạp bộ dò chuyển cảnh TransNet V2\')\n import numpy as np\n import torch\n import subprocess\n from transnetv2_pytorch import TransNetV2\n torch.set_num_threads(2)\n model=TransNetV2()\n model.load_state_dict(torch.load(Path(args[\'model_dir\'])/\'transnetv2.pth\',map_location=\'cpu\',weights_only=True))\n model.eval()\n command=[args[\'ffmpeg\'],\'-hide_banner\',\'-loglevel\',\'error\',\'-i\',args[\'source\'],\n          \'-an\',\'-vf\',\'fps=25,scale=48:27\',\'-threads\',\'2\',\'-f\',\'rawvideo\',\'-pix_fmt\',\'rgb24\',\'pipe:1\']\n size=48*27*3\n predictions=[];frames_read=0\n with subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,creationflags=0x08000000) as proc:\n  try:\n   def read_frames(count):\n    nonlocal frames_read\n    raw=bytearray()\n    while len(raw)<count*size:\n     chunk=proc.stdout.read(count*size-len(raw))\n     if not chunk:break\n     raw.extend(chunk)\n    if len(raw)%size:raise ValueError(\'Khung hình nguồn chưa đọc đầy đủ\')\n    frames_read+=len(raw)//size\n    return np.frombuffer(raw,dtype=np.uint8).reshape((-1,27,48,3)).copy()\n   initial=read_frames(75)\n   if len(initial)==0:raise ValueError(\'Không đọc được hình video\')\n   batch=np.concatenate((np.repeat(initial[:1],25,axis=0),initial))\n   ended=len(initial)<75\n   while True:\n    if len(batch)<100:batch=np.concatenate((batch,np.repeat(batch[-1:],100-len(batch),axis=0)))\n    with torch.inference_mode():scores=torch.sigmoid(model(torch.from_numpy(batch[None]))[0])[0,:,0].numpy()\n    predictions.extend(scores[25:75].tolist())\n    publish(\'progress\',min(.98,len(predictions)/max(1,args[\'duration\']*25)),\n            f"TransNet · đã dò {len(predictions)/25:.0f}/{args[\'duration\']:.0f} giây")\n    if ended and len(predictions)>=frames_read:break\n    more=read_frames(50)\n    ended=len(more)<50\n    batch=np.concatenate((batch[50:],more))\n   if proc.wait(timeout=30)!=0:raise ValueError(\'Đọc nguồn thất bại khi dò chuyển cảnh\')\n  finally:\n   if proc.poll() is None:proc.kill();proc.wait(timeout=5)\n predictions=predictions[:frames_read]\n # Collapse a run of transition frames into its strongest frame, not many tiny scenes.\n cuts=[];group=[]\n for i,score in enumerate(predictions+[0.]):\n  if score>=.5:group.append((score,i))\n  elif group:\n   at=max(group)[1]/25\n   if .08<at<args[\'duration\']-.08:cuts.append(round(at,3))\n   group=[]\n bounds=[0.]+cuts+[args[\'duration\']]\n result={\'engine\':\'transnetv2\',\'cut_points\':cuts,\n         \'scenes\':[{\'start\':a,\'end\':b} for a,b in zip(bounds,bounds[1:])],\n         \'decoded_seconds\':frames_read/25}\n if abs(frames_read/25-args[\'duration\'])>max(.5,args[\'duration\']*.005):\n  raise ValueError(\'Chưa đọc đủ thời lượng nguồn; không dùng kết quả dò cảnh thiếu\')\n dest=Path(args[\'output\']);tmp=dest.with_suffix(\'.tmp\')\n tmp.write_text(json.dumps(result),encoding=\'utf-8\');tmp.replace(dest)\n publish(\'done\',1,f\'TransNet · tìm được {len(cuts)+1} cảnh\')\n\nif __name__==\'__main__\':\n try:main()\n except Exception as exc:\n  publish(\'error\',0,str(exc));sys.exit(1)\n'
