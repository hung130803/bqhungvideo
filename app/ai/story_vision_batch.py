"""Read timestamped frames in bounded groups, retaining valid partial evidence."""
from __future__ import annotations
import json
import tempfile
from types import SimpleNamespace

BATCH_SIZE = 8

def groups(units, transcript_for, token_size):
    """Limit image count AND text budget; never silently shorten transcript."""
    group=[]
    for unit in units:
        row={'unit':unit,'transcript':transcript_for(unit)}
        candidate=group+[row]
        if group and (len(candidate)>BATCH_SIZE or token_size(candidate)>3000):
            yield group;group=[]
        if token_size([row])>3000:
            raise RuntimeError('story_input_too_large: Lời thoại một khoảng hình quá dài; chưa gửi yêu cầu quá cỡ.')
        group.append(row)
    if group:yield group

def validate(value, rows):
    """Match explicit IDs; never assign replies by position or guess missing IDs."""
    frames=value.get('frames') if isinstance(value,dict) else None
    if not isinstance(frames,list):return {},'thiếu danh sách frames'
    wanted={r['unit']['id']:r for r in rows};counts={};valid={};bad=[]
    for frame in frames:
        if not isinstance(frame,dict) or type(frame.get('id')) is not int:
            bad.append('id không hợp lệ');continue
        identifier=frame['id'];counts[identifier]=counts.get(identifier,0)+1
        if identifier not in wanted:bad.append('id ngoài nhóm');continue
        visible=frame.get('visible');uncertain=frame.get('uncertain')
        if not isinstance(visible,str) or not visible.strip() or len(visible)>1800 or not isinstance(uncertain,str) or len(uncertain)>800:
            bad.append(f'căn cứ ảnh {identifier} chưa hợp lệ');continue
        row=wanted[identifier];unit=row['unit']
        valid[identifier]=dict(unit,transcript=row['transcript'],observations=[{
            'at':round((unit['start']+unit['end'])/2,3),
            'visible':visible.strip(),'uncertain':uncertain.strip()}])
    for identifier,count in counts.items():
        if count>1:
            valid.pop(identifier,None);bad.append(f'id trùng {identifier}')
    missing=set(wanted)-set(valid)
    if missing:bad.append('thiếu ảnh '+','.join(map(str,sorted(missing))))
    return valid,'; '.join(bad)

def inspect(src, unit, transcript, ctx, fractions):
    """Selected-scene verification: keep distinct observations for each sample."""
    from app.ai import story_quality as q
    samples=[]
    for i,fraction in enumerate(fractions):
        at=unit['start']+(unit['end']-unit['start'])*fraction
        samples.append({'id':i,'start':at,'end':at})
    cache={}
    # Zero-width sample rows anchor extraction and reply mapping to the exact
    # original sample times. The outer unit's true boundaries stay unchanged.
    child=SimpleNamespace(check_canceled=ctx.check_canceled,progress=lambda *a:None)
    result=build(src,samples,cache,[{'start':unit['start'],'end':unit['end'],'text':transcript}],None,
                 child,lambda:None,transcript_for=lambda u:transcript)
    return dict(unit,transcript=transcript,observations=[o for row in result for o in row['observations']])

def build(src, units, cache, segs, words, ctx, commit, transcript_for=None):
    from app.ai import story_quality as q
    remaining=[u for u in units if str(u['id']) not in cache]
    done=len(units)-len(remaining);calls=0
    blocks=groups(remaining,transcript_for or (lambda u:q.text_for(segs,u['start'],u['end'],words)),q.token_size)
    for rows in blocks:
        ctx.check_canceled();calls+=1
        ctx.progress(.03+.43*done/len(units),f'APIforcode · đọc nhóm {calls} · {len(rows)} ảnh/yêu cầu · đã có {done}/{len(units)} cảnh')
        with tempfile.TemporaryDirectory(prefix='bq_batch_frames_') as folder:
            paths=[];labels=[]
            for no,row in enumerate(rows,1):
                ctx.check_canceled();unit=row['unit']
                paths.extend(q.frame_paths(src,unit,folder,(.5,)))
                labels.append({'image_order':no,'id':unit['id'],'at':round((unit['start']+unit['end'])/2,3),
                    'speech_in_interval':row['transcript']})
            prompt=('These are DISTINCT sampled frames from ONE video, in the exact order listed below. '
                'Describe EACH image separately and return its explicit id. Never combine people or objects '
                'across images. A still frame does not prove motion, motives, relationships or unseen events. '
                'Speech is separate evidence, not proof of visible facts. Report blur/uncertainty honestly. '
                'Return ONE JSON object only: {"frames":[{"id":integer,"visible":"specific observations, '
                'at most 100 words","uncertain":"unknown details"}]}. Include every listed id exactly once. '
                'Do not create additional ids. Image manifest:\n'+json.dumps(labels,ensure_ascii=False))
            with q.llm.bounded_call(180,ctx.check_canceled):
                value=q.provider_call(lambda:q.llm.complete_vision_json(prompt,paths,system=q.SYSTEM,
                    provider='apiforcode',request_timeout=120),ctx.check_canceled,scope='vision')
        ctx.check_canceled()
        valid,problem=validate(value,rows)
        for identifier,item in valid.items():
            unit=next(r['unit'] for r in rows if r['unit']['id']==identifier)
            item['safe_orig']=not any(float(s['start'])+.08<b<float(s['end'])-.08 for s in segs for b in (unit['start'],unit['end']))
            cache[str(identifier)]=item;done+=1
        if valid:commit()
        if problem:
            raise RuntimeError('apiforcode_request_uncertain: Nhóm hình trả chưa đủ căn cứ: '+problem+
                '. Đã lưu các ảnh hợp lệ; không tự gọi lại. Thử lại chỉ xử lý ảnh còn thiếu.')
    return [cache[str(u['id'])] for u in units]
