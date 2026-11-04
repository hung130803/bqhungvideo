"""Whole-source story selection, selective verification and economical script audits."""
import json
from app.ai.structured import EVENTS
import math
import time
from copy import deepcopy
import re
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from app.ai import story_quality as q
from app.ai.editorial_context import SCENE_CRAFT, VOICE_CRAFT, repair_context
from app.core.story_craft import word_budget,writing_direction,DELIVERY,ENERGY,narration_ratio,narration_word_limits
from app.core.story_checks import context as scene_context,continuity_issues,language_issues

ROLES={'hook','setup','build','payoff','ending'}
SFX={'none','transition','impact','riser','reveal','pop','suspense','comedy','scratch','sad','drumroll'}
STYLE={
    'story':'Conversational storytelling: concrete stakes, short varied sentences, setup and satisfying payoff.',
    'funny':'Dry observational humor about the evidenced contrast; no invented motives, cruelty, or fake reactions.',
    'analysis':'Explain the evidenced mechanism or contrast; separate speaker claims from verified observations.',
    'clickbait':'High curiosity from a specific real contrast. No fake superlatives, manufactured danger or vague teasers.'}


class AuditFailure(ValueError):
    def __init__(self,message,checks):
        super().__init__(message);self.checks=checks


def compact_context_rows(rows,limit=3600):
    """Retain every scene/date anchor while bounding added visual audit context."""
    rows=deepcopy(rows)
    for size in (240,140,80,40):
        if q.token_size(rows)<=limit:return rows
        for row in rows:
            for key in ('speech','local_speech','event','reason'):
                if isinstance(row.get(key),str):row[key]=row[key][:size]
            for observation in row.get('scene_context',{}).get('visual',[]):
                observation['visible']=observation.get('visible','')[:size]
                observation['uncertain']=observation.get('uncertain','')[:min(size,60)]
            if size==40:
                visual=row.get('scene_context',{}).get('visual',[])
                if visual:row['scene_context']['visual']=[visual[len(visual)//2]]
    if q.token_size(rows)>limit:raise ValueError('Bối cảnh còn quá dài để kiểm tra đủ cảnh; cần chọn ít cảnh hơn, không bỏ kiểm tra.')
    return rows


def catalogue(units,ctx,state=None,on_checkpoint=None):
    """One batched pass indexes every unit; never one summary call per frame."""
    # state belongs to the existing source/model/preset checkpoint key.
    # Store individual validated cards so a later timeout never discards
    # earlier paid responses. An incomplete response is NOT synthesized.
    state=state if isinstance(state,dict) else {}
    allowed={u['id'] for u in units}
    def valid(value):
        return (isinstance(value,dict) and type(value.get('id')) is int
            and value['id'] in allowed and isinstance(value.get('event'),str)
            and bool(value['event'].strip()) and type(value.get('interest')) in (int,float)
            and math.isfinite(value['interest']) and 0<=value['interest']<=5)
    retained={v['id']:dict(v) for k,v in state.items() if valid(v) and str(v['id'])==str(k)}
    cards=[]
    gemini=q.llm.active_provider()=='gemini'
    batches=q.evidence_batches(units,limit=18000 if gemini else 6500,
        token_limit=7500 if gemini else 3000)
    for no,block in enumerate(batches,1):
        ctx.check_canceled();ctx.progress(.48,f'Lập bản đồ tình tiết toàn nguồn · nhóm {no}/{len(batches)}')
        wanted={u['id'] for u in block}
        found={i:retained[i] for i in wanted if i in retained}
        for attempt in range(2):
            remaining=[u for u in block if u['id'] not in found]
            if not remaining:break
            ctx.check_canceled()
            raw=q.ask('Index EVERY source interval, preserving its id. Return {"events":[{"id":int,'
                '"event":"at most 140 characters: specific event or speech claim + uncertainty",'
                '"interest":0-5}]}. Include even quiet intervals. Prioritize a concrete setup, unexpected change, reaction, consequence, '
                'payoff or useful explanation. Speech establishes reported events even when stills cannot show them. Preserve negation, speaker, recipient, obligation and causal direction EXACTLY: made dinner so does not have to wash dishes must never become should wash dishes. Index a concrete event, not clothing or room inventory. Unknown identity does not erase an evidenced conflict. Do not invent motion. '
                'Interest is editorial relevance, not certainty.\n'+json.dumps(remaining,ensure_ascii=False),
                response_schema=EVENTS)
            values=raw.get('events',[]) if isinstance(raw,dict) else []
            for value in values if isinstance(values,list) else []:
                if not isinstance(value,dict) or type(value.get('id')) is not int or value['id'] not in wanted:continue
                event=value.get('event');score=value.get('interest')
                if not isinstance(event,str) or not event.strip() or type(score) not in (int,float) or not math.isfinite(score):continue
                found[value['id']]={'id':value['id'],'event':event[:260],'interest':max(0,min(5,score))}
            # Persist even a valid partial group before requesting missing ids.
            if found:
                state.update({str(i):dict(v) for i,v in found.items()})
                retained.update(found)
                if on_checkpoint:on_checkpoint()
        if set(found)!=wanted:
            raise RuntimeError('Bản đồ tình tiết thiếu cảnh; thử lại để dùng phần xem hình đã lưu.')
        cards.extend(found.values())
    return sorted(cards,key=lambda v:v['id'])


def shortlist_ids(raw,allowed,maximum):
    """Normalize harmless JSON variations without accepting invented source ids."""
    values=raw.get('ids') if isinstance(raw,dict) else None
    if not isinstance(values,list) or not values:raise ValueError('Cần ids là danh sách mã cảnh có sẵn.')
    ids=[]
    for value in values:
        if isinstance(value,str) and re.fullmatch(r'[0-9]+',value.strip()):value=int(value.strip())
        if type(value) is not int or value not in allowed:raise ValueError('Có mã cảnh không nằm trong nhóm nguồn được gửi.')
        if value not in ids:ids.append(value)
    if len(ids)>maximum:raise ValueError(f'Chỉ chọn tối đa {maximum} mã cảnh để thu gọn danh sách.')
    return ids


def planning_cards(cards,ctx):
    """For long sources, retain story candidates from every region, then compare."""
    for _ in range(4):
        if q.token_size(cards)<=2400:break
        selected=[]
        for number,block in enumerate(q.evidence_batches(cards,limit=5500),1):
            allowed={c['id'] for c in block};maximum=max(2,len(block)//2);error=''
            for attempt in range(2):
                ctx.check_canceled();ctx.progress(.51,f'Thu gọn ghi chú cảnh · nhóm {number}, lượt {attempt+1}/2')
                raw=q.ask('Select a connected set of the best story seeds from these events: setups AND payoffs, '
                    f'not just spectacle. Keep at most {maximum} ids. Return exactly {{"ids":[integer source ids]}}. '
                    'Use ids from this batch, not row positions. No objects or descriptions inside ids.\n'+
                    json.dumps({'events':block,'repair':error},ensure_ascii=False))
                try:ids=shortlist_ids(raw,allowed,maximum);break
                except ValueError as exc:error=str(exc)
            else:
                # Shortlisting is an optimization, not evidence verification.
                # Preserve the original batch when its JSON cannot be repaired.
                ids=allowed
                ctx.progress(.51,f'Giữ đủ cảnh nhóm {number}; AI chưa trả danh sách thu gọn hợp lệ')
            selected.extend(c for c in block if c['id'] in ids)
        # Do not starve the requested edit duration or loop on an unshrinking reply.
        if len(selected)>=len(cards) or len(selected)<8:break
        cards=selected
    return cards


def planning_notes(cards,lookup,ctx):
    """Compact text before dropping any source candidate, including 10–20m videos."""
    budget=10000 if q.llm.active_provider()=='gemini' else 3300
    def rows(pool,limit,anchors=False):
        result=[]
        for c in pool:
            u=lookup[c['id']]
            row=[c['id'],round(u['end']-u['start'],2),c['event'][:limit]]
            if anchors:
                timed=[]
                for o in u.get('observations',[]):
                    at=float(o.get('at',-1))
                    if u['start']<=at<=u['end']:
                        timed.append([round(at-u['start'],2),str(o.get('visible',''))[:max(24,limit//2)]])
                row.append(timed[:3])
            result.append(row)
        return result
    for limit in (140,80,50):
        notes=rows(cards,limit,True)
        if q.token_size(notes)<=budget:return cards,notes
    for limit in (260,140,110,80):
        notes=rows(cards,limit)
        if q.token_size(notes)<=budget:return cards,notes
    selected=planning_cards(cards,ctx)
    for limit in (140,110,80,60):
        notes=rows(selected,limit)
        if q.token_size(notes)<=budget:return selected,notes
    raise RuntimeError('Ghi chú cảnh còn quá dài sau khi thu gọn; chưa thể gửi vừa giới hạn AI. '
                       'Phần xem hình đã lưu; thử lại hoặc dùng nguồn ngắn hơn. Đây không phải kết luận video thiếu tình tiết.')


def fit_small_duration_gap(parts,lookup,minimum,maximum,*,context_repair=False):
    """Restore rounding gaps, or bounded context before semantic review; never alter original speech."""
    total=round(math.fsum(p['end']-p['start'] for p in parts),6)
    missing=minimum-total
    limit=min(5.,minimum*.05) if context_repair else .5
    if not 0<missing<=limit+1e-6:return
    trial=deepcopy(parts)
    for i,p in enumerate(trial):
        if p['mode']!='narrate':continue
        u=lookup[p['source_id']]
        # Never cross another selected interval, even for unusual source indexes.
        right=min(u['end'],trial[i+1]['start'] if i+1<len(trial) else u['end'])
        left=max(u['start'],trial[i-1]['end'] if i else u['start'])
        for edge,room in (('end',right-p['end']),('start',p['start']-left)):
            # Context repair stays close to the chosen beat (at most one
            # second per edge); semantic review still follows this adjustment.
            amount=min(max(0,room),missing,1. if context_repair else .5)
            p[edge]+=amount if edge=='end' else -amount
            missing-=amount
            if missing<=1e-8:break
        if missing<=1e-8:break
    actual=round(math.fsum(p['end']-p['start'] for p in trial),6)
    if minimum<=actual<=maximum:
        parts[:]=trial


def validate_edit(raw,units,used,minimum,maximum,*,context_repair=False):
    if not isinstance(raw,dict) or not isinstance(raw.get('title'),str) or not raw['title'].strip():raise ValueError('Thiếu tiêu đề câu chuyện.')
    shots=raw.get('shots');lookup={u['id']:u for u in units}
    if not isinstance(shots,list) or not 1<=len(shots)<=len(lookup):raise ValueError('Cần các cảnh có vai trò rõ ràng, không vượt số cảnh nguồn.')
    seen=set();parts=[];last=-1
    for shot in shots:
        if not isinstance(shot,dict):raise ValueError('Cảnh không hợp lệ.')
        uid=shot.get('source_id');role=shot.get('role');why=shot.get('reason','')
        if type(uid) is not int or uid not in lookup or uid in seen or uid in used or uid<=last:raise ValueError('Cảnh không có nguồn, trùng hoặc đảo diễn biến.')
        if role not in ROLES or not isinstance(why,str) or len(why.strip())<8:raise ValueError('Thiếu vai trò hoặc lý do chọn cảnh.')
        u=lookup[uid];a=shot.get('start',u['start']);b=shot.get('end',u['end'])
        if 'in' in shot or 'out' in shot:
            lo,hi=shot.get('in'),shot.get('out')
            if ('start' in shot or 'end' in shot or type(lo) not in (int,float)
                    or type(hi) not in (int,float) or not math.isfinite(lo+hi)):
                raise ValueError('Mép dựng cần in/out bằng số, không trộn với mốc tuyệt đối.')
            a=round(u['start']+lo,3);b=round(u['start']+hi,3)
        if type(a) not in (int,float) or type(b) not in (int,float) or not math.isfinite(a+b) or not u['start']<=a<b<=u['end'] or b-a<1.0:
            raise ValueError('Mốc cắt vượt cảnh nguồn hoặc cảnh quá ngắn.')
        mode=shot.get('mode','narrate')
        if mode not in ('orig','narrate'):raise ValueError('Vai âm thanh không hợp lệ.')
        if mode=='orig' and not ((u.get('safe_orig',True) and a==u['start'] and b==u['end']) or (u.get('orig_window') and [a,b]==u['orig_window'])):
            raise ValueError('Cảnh giữ lời gốc phải có mép câu trọn vẹn.')
        sfx=shot.get('sfx','none')
        if sfx not in SFX:raise ValueError('Loại tiếng động không được hỗ trợ.')
        parts.append(dict(start=float(a),end=float(b),mode=mode,text='',source_id=uid,role=role,
                          reason=why.strip()[:400],sfx=sfx,evidence=json.dumps(u,ensure_ascii=False)))
        seen.add(uid);last=uid
    fit_small_duration_gap(parts,lookup,minimum,maximum,context_repair=context_repair)
    duration=round(math.fsum(p['end']-p['start'] for p in parts),6)
    if not minimum<=duration<=maximum:raise ValueError(f'Tổng cảnh {duration:.1f}s; cần {minimum:.0f}–{maximum:.0f}s.')
    if parts[0]['role']!='hook' or parts[0]['mode']!='narrate' or (len(parts)>1 and not any(p['role']=='payoff' for p in parts)):
        raise ValueError('Cần hook mở đầu và cảnh trả lời điều hook đã hứa.')
    gaps=sum(b['start']-a['end']>1 for a,b in zip(parts,parts[1:]))
    continuous=str(raw.get('continuous_reason') or '').strip()
    if not gaps and len(lookup)>len(parts)+2 and len(continuous)<25:
        raise ValueError('Đang lấy nguyên một cụm liền: chọn setup/diễn biến/kết quả ở các vị trí phù hợp, hoặc giải thích vì sao hành động phải liền mạch.')
    return {'title':raw['title'].strip()[:250],'angle':str(raw.get('angle',''))[:400],
            'continuous_reason':continuous,'parts':parts,'windows':[[p['start'],p['end']] for p in parts],'duration':duration}


def source_alternatives(cards,lookup,selected=()):
    """Bounded direct speech for competing high-interest beats, not summary-only review."""
    chosen=set(selected)
    ranked=sorted((c for c in cards if c['id'] not in chosen),key=lambda c:(-c.get('interest',0),c['id']))
    # Compare across the whole timeline, not eight equally-rated early cards.
    ordered=sorted(cards,key=lambda c:lookup[c['id']]['start'])
    region={c['id']:min(3,i*4//max(1,len(ordered))) for i,c in enumerate(ordered)}
    buckets=[[c for c in ranked if region[c['id']]==r] for r in range(4)]
    diverse=[bucket[depth] for depth in range(2) for bucket in buckets if len(bucket)>depth]
    rows=[]
    for c in diverse:
        u=lookup[c['id']]
        # Complete lines only: never truncate a negation at the end of a phrase.
        lines=u.get('transcript','').splitlines()
        speech=[]
        for line in lines:
            if len(line)>220:continue
            if sum(len(x) for x in speech)+len(line)>220:break
            speech.append(line)
        rows.append({'id':c['id'],'event':c['event'][:180],
                     'speech':' '.join(speech),'interest':c.get('interest',0)})
    while rows and q.token_size(rows)>700:rows.pop()
    return rows


def ask_selection(prompt,**kwargs):
    """Budget the assembled request, including repair history and system text."""
    instructions,separator,encoded=prompt.rpartition('\n')
    if not separator:raise ValueError('Selection request is missing structured data')
    payload=json.loads(encoded)
    def pack():return instructions+'\n'+json.dumps(payload,ensure_ascii=False,separators=(',',':'))
    def fits():return q.llm._uoc_token(pack())+q.llm._uoc_token(q.SYSTEM)<=q.request_input_limit()
    # Redundant draft prose is optional, source evidence and repair diagnosis are not.
    previous=payload.get('previous_plan')
    if not fits() and isinstance(previous,dict):
        payload['previous_plan']={k:v for k,v in previous.items() if k in ('title','angle','shots')}
        payload['previous_plan']['shots']=[{k:v for k,v in row.items() if k in ('source_id','in','out','start','end','mode')}
            for row in previous.get('shots',[]) if isinstance(row,dict)]
    if not fits():payload.pop('previous_plan',None)
    if not fits():
        for key in ('already_planned','previous_stories'):
            if key in payload:
                payload[key]=[{k:v for k,v in row.items() if k in ('title','angle','hook')} for row in payload[key]]
    # Remove optional duplicates, never the event catalogue or source evidence.
    if not fits():payload.pop('strongest_available_beats',None)
    if not fits():payload.pop('omitted_candidates',None)
    return q.ask(pack(),**kwargs)


def supplement_short_selection(raw,units,reserved,minimum,maximum,cards,ctx):
    """Ask for one evidenced bridge, then revalidate duration and story normally."""
    plan=validate_edit(raw,units,reserved,1,maximum)
    deficit=minimum-plan['duration']
    if not 0<deficit<=max(12.,minimum*.15):return raw
    lookup={u['id']:u for u in units};selected={p['source_id'] for p in plan['parts']}
    candidates=[c for c in cards if c['id'] not in selected|reserved
                and deficit<=lookup[c['id']]['end']-lookup[c['id']]['start']<=maximum-plan['duration']]
    candidates.sort(key=lambda c:(min(abs(c['id']-i) for i in selected),-c.get('interest',0)))
    candidates=candidates[:16]
    if not candidates:return raw
    evidence=[{'id':c['id'],'seconds':round(lookup[c['id']]['end']-lookup[c['id']]['start'],3),
               'event':c['event'][:220],'speech':lookup[c['id']].get('transcript','')[:260]} for c in candidates]
    ctx.check_canceled();ctx.progress(.54,f'Bổ sung ngữ cảnh: đang có {plan["duration"]:.1f}s, cần ít nhất {minimum:g}s')
    answer=ask_selection('Repair a short story selection after safe dialogue boundaries were applied. '
        'Choose exactly ONE candidate interval which provides relevant setup, explanation or reaction '
        'for this SAME incident. Do not invent a link, repeat an event, or add unrelated filler. '
        'It will use narration over the whole candidate interval, preserving existing original speech. '
        'Return {"source_id":integer,"reason":"specific evidenced connection"}, or '
        '{"source_id":null,"reason":"no supported bridge"} if none fits.\n'+json.dumps({
            'title':plan['title'],'angle':plan.get('angle',''),'actual_seconds':plan['duration'],
            'required_seconds':[minimum,maximum],
            'selected':[{'id':p['source_id'],'reason':p['reason'][:160]} for p in plan['parts']],
            'candidates':evidence},ensure_ascii=False),reasoning='medium')
    if not isinstance(answer,dict):return raw
    sid=answer.get('source_id');reason=answer.get('reason')
    if type(sid) is not int or sid not in {c['id'] for c in candidates} or not isinstance(reason,str) or len(reason.strip())<8:return raw
    result=deepcopy(raw);u=lookup[sid]
    result['shots'].append({'source_id':sid,'start':u['start'],'end':u['end'],
                           'mode':'narrate','reason':reason,'role':'build','sfx':'none'})
    result['shots'].sort(key=lambda s:lookup[s['source_id']]['start'])
    for i,shot in enumerate(result['shots']):
        shot['role']='hook' if i==0 else 'payoff' if i==len(result['shots'])-1 else 'setup' if i==1 else 'build'
        if i==0:shot['mode']='narrate'
    return result


def choose_edits(units,cards,used,preset,count,ctx):
    """Choose one coherent story at a time, then reserve its source intervals."""
    minimum,maximum=q.length_limits(preset)
    target_ratio=narration_ratio(preset)
    lookup={u['id']:u for u in units};reserved=set(used);plans=[]
    for part_index in range(count):
        available=[dict(c) for c in cards if c['id'] not in reserved]
        # Compact rows keep EVERY normal-length source interval visible. Do not
        # rank away a quiet setup before the whole-source story is understood.
        available,notes=planning_notes(available,lookup,ctx)
        allowed={n[0] for n in notes};error='';previous=None;reviewable=None
        for attempt in range(3):
            ctx.check_canceled();ctx.progress(.53,f'Chọn mạch chuyện {part_index+1}/{count} · lượt {attempt+1}/3')
            raw=ask_selection(SCENE_CRAFT + f'Select ONE complete story lasting {minimum}-{maximum}s from these source events. '
                'Each compact event row is [source_id, seconds, event description, optional timed visual anchors]. '
                'A visual anchor is [seconds from interval start, fallible still-image description]. '
                'Choose a SPECIFIC incident, NOT a montage of unrelated daily activities. First identify its '
                'setup and its actual outcome/reaction, then select the connected events needed to understand it. '
                'Look across the WHOLE source: the setup can be minutes before the payoff. Do not assume two '
                'different objects or meals are the same thing. Treat source_title only as a topic hint, not proof. '
                'retrieval_candidates_not_facts are fallible search hints, never proof or mandatory choices. Examine their source evidence and surrounding context alongside other arcs. '
                'Compare at least three available story arcs internally before selecting: specificity of conflict, change, reaction and payoff. Choose the strongest coherent arc first, not the earliest event. '
                'Do not abandon the central topic just because still images leave objects uncertain; attributed '
                'speech can establish what the participants SAY they prepared or discovered. Then distinct remaining '
                'stories on later Parts. No invented danger, identity, surprise or causal connection. '
                'Use unique ids in chronological order. These intervals are a SEARCH INDEX, not final shots. '
                'For each shot specify in/out seconds relative to that interval start, with 0 <= in < out <= seconds. '
                'Trim around supplied timed evidence with context on either side; do not invent a precise '
                'action time from a vague summary. If there are no useful timing anchors, keep that interval intact. '
                'Select the useful beat within each interval, omit dead time, and vary shot lengths for a clear '
                'setup, change and payoff; never default to six identical 12-second blocks. '
                'SUM the chosen out-in durations AFTER original-dialogue window adjustment; aim near the midpoint of the requested range rather than exactly its minimum. Use more connected intervals if needed. '
                'Preserve confrontation, denial, correction, retort and reaction as original dialogue. For ids in safe_dialogue_windows, orig uses exactly that inner window; sum its duration instead of the full interval. Otherwise keep whole intervals for orig. Never create arbitrary cuts '
                'just to satisfy a count; hold an important reaction when warranted. If action must remain continuous, '
                'explain why. Never pad an incomplete story with irrelevant scenes. Return '
                '{"title":"factual title","angle":"one specific real contrast",'
                '"continuous_reason":"only when necessary","shots":[{"source_id":int,'
                '"in":0.0,"out":8.0,"reason":"specific connection to THIS story","mode":"narrate|orig"}]}. '
                'Opening always narrated. Honor narration_target_percent as an approximate SPOKEN-time target: '
                'reserve meaningful whole original dialogue/reactions when safe; use short narration bridges elsewhere. '
                'Do not narrate every shot by default or invent extra cuts to hit a percentage. If repairing, address the specific '
                'error while retaining valid scenes.\n'+json.dumps({'source_title':preset.get('_source_title',''),
                'retrieval_candidates_not_facts':[i for i in preset.get('_twelve_candidate_ids',[]) if i in allowed], 'events':notes,'safe_dialogue_windows':{u['id']:[round(t-u['start'],3) for t in u['orig_window']] for u in units if u['id'] in {c['id'] for c in sorted(available,key=lambda c:-c.get('interest',0))[:12]} and u.get('orig_window') and not u.get('safe_orig',True)},'strongest_available_beats':sorted([{'id':c['id'],'interest':c.get('interest',0)} for c in available],key=lambda c:(-c['interest'],c['id']))[:12],'narration_target_percent':target_ratio,'already_planned':[story_brief(p) for p in plans],
                'diversity_rule':'Choose a different question and payoff, not the same incident retold using different shots.',
                'repair':error,'previous_plan':previous},ensure_ascii=False),reasoning='medium')
            try:
                if not isinstance(raw,dict) or not isinstance(raw.get('shots'),list):raise ValueError('Thiếu danh sách cảnh.')
                prepared=deepcopy(raw);shots=prepared['shots']
                if any(not isinstance(shot,dict) or type(shot.get('source_id')) is not int or shot['source_id'] not in allowed for shot in shots):
                    raise ValueError('Chỉ chọn source_id trong danh sách đang có.')
                # Source chronology is deterministic; do not trust the order of
                # JSON rows to manufacture a reveal before its actual setup.
                shots.sort(key=lambda shot:lookup[shot['source_id']]['start'])
                for i,shot in enumerate(shots):
                    if not isinstance(shot,dict) or type(shot.get('source_id')) is not int or shot['source_id'] not in allowed:
                        raise ValueError('Chỉ chọn source_id trong danh sách đang có.')
                    # Roles describe the narration structure; source time/order is never rewritten.
                    shot['role']='hook' if i==0 else 'payoff' if i==len(shots)-1 else 'setup' if i==1 else 'build'
                    shot['sfx']='none'
                    unit=lookup[shot['source_id']]
                    if i==0 or (not unit.get('safe_orig',True) and not unit.get('orig_window')):shot['mode']='narrate'
                    if shot.get('mode')=='orig' and not unit.get('safe_orig',True) and unit.get('orig_window'):
                        shot.pop('in',None);shot.pop('out',None)
                        shot.update(start=unit['orig_window'][0],end=unit['orig_window'][1])
                    if shot.get('mode')=='orig':
                        # The model sees rounded interval lengths, not exact file
                        # boundaries. Snap only a full-interval rounding mismatch;
                        # an intentional trim must use narration, never cut speech.
                        if 'in' in shot or 'out' in shot:
                            lo,hi=shot.get('in'),shot.get('out')
                            valid=(type(lo) in (int,float) and type(hi) in (int,float)
                                   and math.isfinite(lo+hi) and 'start' not in shot and 'end' not in shot)
                            if valid and abs(lo)<=.006 and abs(hi-(unit['end']-unit['start']))<=.006:
                                shot.pop('in');shot.pop('out')
                                shot.update(start=unit['start'],end=unit['end'])
                            elif valid:shot['mode']='narrate'
                        elif [shot.get('start',unit['start']),shot.get('end',unit['end'])] not in ([unit['start'],unit['end']],unit.get('orig_window')):
                            shot['mode']='narrate'
                try:
                    plan=validate_edit(prepared,units,reserved,minimum,maximum,context_repair=True)
                except ValueError:
                    # Shortlisting must not hide context needed to meet duration.
                    prepared=supplement_short_selection(prepared,units,reserved,minimum,maximum,cards,ctx)
                    plan=validate_edit(prepared,units,reserved,minimum,maximum,context_repair=True)
                # Check relationships against original speech, not only condensed event cards.
                evidence=[{'id':p['source_id'],'reason':p['reason'],
                    'speech':lookup[p['source_id']].get('transcript','')[:750],
                    'event':next(c['event'] for c in cards if c['id']==p['source_id']),
                    'scene_context':scene_context(lookup[p['source_id']])} for p in plan['parts']]
                if q.token_size(evidence)>3500:
                    for e in evidence:e['speech']=e['speech'][:300]
                evidence=compact_context_rows(evidence)
                check=ask_selection('Verify the proposed story using these original source speech excerpts and '
                    'event notes AND visual scene context. Are these scenes about ONE connected story, with a real setup and outcome? '
                    'Treat compilations as multiple incidents: a roadside stop and an airport incident are NOT the same '
                    'event merely because police occur in both. Compare visible dates, location, clothing and participants; '
                    'do not bridge conflicting dates or locations without explicit evidence. Visual notes are fallible, '
                    'so unresolved contradictions mean needs review. '
                    'Anonymous people, unnamed relationships and gaps that skip irrelevant material are valid: '
                    'do not reject solely because a name or identity is unknown. The same incident can be '
                    'understood from attributed dialogue, without demanding proof of every motion in a still. '
                    'Approval means this selection CAN be told accurately by attributing speech and avoiding '
                    'unproven details; it does not certify that the speakers told the truth. Unknown ingredients '
                    'or a joke about disguising food do not make the story unusable if narration reports the claims. '
                    'Reject unrelated topics used as padding, switching one food/object for another without '
                    'evidence, or claiming a reveal/reaction that is not shown or stated. Speech is a speaker '
                    'claim, not objective proof. Do not demand every event appear in a still image. '
                    'Compare omitted_candidates against the selected arc. Prefer an evidenced conflict with reaction and consequence over unrelated routine talk. Reject missing decisive reactions or a final topic that does not answer the opening. A shared kitchen is not a causal link between cooking and a much later juice argument. Direct speech overrides a contradictory event summary, especially negations. If a stronger coherent story is omitted, explain its source ids in issues and return approved=false so selection can repair. Compare previous stories too: different timestamps or wording alone are NOT a new story. '
                    'A complementary part must answer a materially different question with its own supported payoff. '
                    'Return {"approved":boolean,"distinct_from_previous":boolean,"new_value":"what is new",'
                    '"issues":"specific correction","title":"accurate concise title",'
                    '"angle":"accurate angle"}.\n'+json.dumps({'title':plan['title'],'angle':plan['angle'],'evidence':evidence,
                    'omitted_candidates':source_alternatives(available,lookup,[p['source_id'] for p in plan['parts']]),'previous_stories':[story_brief(p) for p in plans]},ensure_ascii=False),reasoning='medium')
                local_warnings=continuity_issues(plan['parts'])
                if local_warnings:
                    check=dict(check) if isinstance(check,dict) else {}
                    check.update(approved=False,issues='; '.join(local_warnings))
                distinct=not plans or (isinstance(check,dict) and check.get('distinct_from_previous') is True)
                if not isinstance(check,dict) or check.get('approved') is not True or not distinct:
                    issue=str(check.get('issues','Cần xem lại mạch chuyện') if isinstance(check,dict) else 'Kiểm tra mạch chuyện chưa trả đủ dữ liệu')
                    if not distinct:issue='Cần kiểm tra trùng ý giữa các Part. '+issue
                    plan['selection_review']={'approved':False,'issues':issue[:900],
                        'duplicate':bool(plans and isinstance(check,dict) and check.get('distinct_from_previous') is False)}
                    reviewable=plan
                    raise ValueError(plan['selection_review']['issues'][:700])
                for key in ('title','angle'):
                    if isinstance(check.get(key),str) and check[key].strip():plan[key]=check[key].strip()[:250]
                plans.append(plan);reserved.update(p['source_id'] for p in plan['parts']);break
            except ValueError as exc:
                error=str(exc)
                previous=raw if isinstance(raw,dict) and q.token_size(raw)<1200 else None
        else:
            if reviewable is None:raise RuntimeError('Chưa chọn được câu chuyện đủ dài và có căn cứ: '+error)
            if plans and not preset.get('recap_count') and reviewable.get('selection_review',{}).get('duplicate'):
                ctx.progress(.56,f'Tự động giữ {len(plans)} Part; chưa có góc kể mới đủ khác để thêm Part')
                return plans
            # Structurally valid drafts remain editable, but semantic doubts are
            # never turned into an automatic approval or hidden from the user.
            plans.append(reviewable);reserved.update(p['source_id'] for p in reviewable['parts'])
    return plans


def story_brief(plan):
    return {'title':plan['title'],'angle':plan.get('angle',''),
            'beats':[p.get('reason','')[:160] for p in plan['parts']],
            'hook':plan['parts'][0].get('text','')[:180]}


def enrich_scene(src,unit,ctx,fractions):
    """Only add missing time anchors within the actual cut; never count one frame twice."""
    a,b=unit['start'],unit['end'];span=b-a
    observations=[o for o in unit.get('observations',[]) if a<=float(o['at'])<=b]
    missing=[f for f in fractions if not any(abs(float(o['at'])-(a+span*f))<=span*.08 for o in observations)]
    if missing:
        extra=q.visual_evidence(src,unit,unit.get('transcript',''),ctx,fractions=tuple(missing))
        observations+=extra['observations']
    return dict(unit,observations=sorted(observations,key=lambda o:float(o['at'])))


def inspect_disputed(plan,checks,src,ctx):
    """An extra bounded look only where narration was disputed, before rewriting."""
    bad={r['source_id'] for r in checks if r.get('supported') is not True or r.get('scene_match') is not True}
    for part in plan['parts']:
        if part['source_id'] not in bad:continue
        ctx.check_canceled()
        unit=json.loads(part['evidence'])
        unit=enrich_scene(src,unit,q.VisionContext(ctx),(.04,.96))
        part['evidence']=json.dumps(unit,ensure_ascii=False)


def refine(plans,units,src,ctx,on_checkpoint=None):
    lookup={u['id']:u for u in units};selected=[p for plan in plans for p in plan['parts']]
    child=q.VisionContext(ctx)
    def inspect(p):
        ctx.check_canceled();source=lookup[p['source_id']]
        u=dict(source,start=p['start'],end=p['end'])
        u['observations']=[o for o in source.get('observations',[]) if p['start']<=float(o['at'])<=p['end']]
        lines=[]
        for line in source.get('transcript','').splitlines():
            match=re.match(r'^(\d+(?:\.\d+)?)-(\d+(?:\.\d+)?):',line)
            if match and float(match[2])>p['start'] and float(match[1])<p['end']:lines.append(line)
        u['transcript']='\n'.join(lines)
        u=enrich_scene(src,u,child,(.15,.5,.85))
        merged={float(o['at']):o for o in source.get('observations',[])+u['observations']}
        source['observations']=list(merged.values())
        return u
    todo=iter(selected);pending={};done=0
    with ThreadPoolExecutor(max_workers=2,thread_name_prefix='story-refine') as executor:
        while True:
            ctx.check_canceled()
            while len(pending)<2:
                p=next(todo,None)
                if p is None:break
                pending[executor.submit(inspect,p)]=p
            if not pending:break
            ready,_=wait(pending,timeout=.5,return_when=FIRST_COMPLETED)
            for future in ready:
                p=pending.pop(future);p['evidence']=json.dumps(future.result(),ensure_ascii=False);done+=1
                if on_checkpoint:on_checkpoint()
            ctx.progress(.59+.10*done/max(1,len(selected)),f'Đối chiếu đúng khúc sẽ xuất {done}/{len(selected)}'+child.status())


def audit(plan,ctx):
    language_problems=language_issues(plan['parts'],plan.get('target_language',''))
    if language_problems:raise ValueError('; '.join(language_problems))
    checks=[]
    # Each check sees complete local evidence, in bounded batches, once.
    for block in q.evidence_batches(plan['parts'],limit=7500):
        ctx.check_canceled()
        raw=q.ask('Audit EACH shot independently using its attached local evidence. Orig rows have no narration: '
            'empty orig text is supported and scene_match=true by definition. Text may be engaging '
            'but no invented identities, motives, actions or unobserved outcome. A still image cannot prove motion. '
            'An explicitly attributed speech claim ("the speaker says/calls it...") IS supported when the '
            'local transcript says that, even if the object cannot be identified in a still. scene_match means '
            'the narration belongs to this source interval, NOT that every spoken claim must be visually '
            'provable. Do not mark such attributed speech false merely because the frame is blurred. '
            'Reject unqualified guesses, invented action or narrator claims that conflict with the local evidence. '
            'Return {"checks":[{"source_id":int,"supported":boolean,"scene_match":boolean,"issue":"..."}]}.\n'+json.dumps(block,ensure_ascii=False))
        rows=raw.get('checks',[]) if isinstance(raw,dict) else []
        if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) or len(rows)!=len(block) or {r.get('source_id') for r in rows}!={p['source_id'] for p in block}:
            raise ValueError('AI chưa kiểm tra đủ từng câu/cảnh.')
        checks.extend(rows)
    problems=[r.get('issue') or f"Cảnh {r['source_id']} chưa khớp" for r in checks if r.get('supported') is not True or r.get('scene_match') is not True]
    if problems:raise AuditFailure('; '.join(str(p) for p in problems)[:900],checks)
    from app.ai.editorial_context import CONTINUITY_REVIEW
    raw=q.ask(CONTINUITY_REVIEW + 'Audit this finished SHORT STORY. Specific hook paid off? Clear setup-change-payoff? '
        'No unrelated cuts, repetitive image descriptions, filler, unsupported title, or false causality? '
        'Natural varied spoken language, not a list of what is on screen? Check unexplained pronouns, '
        'stiff translation, repeated ideas, a hook unanswered by the ending, and narration that merely labels each image. '
        'Source-time gaps are intentional '
        'montage: do NOT reject simply because timestamps jump or require events to be adjacent. '
        'Reject only if the actual story connection or claimed cause is missing. '
        'Use local speech AND visual scene context to distinguish unrelated incidents from omitted transitions. '
        'A shared topic or police uniform does not establish same event. Different visible dates, clothes or '
        'locations require explicit support for continuity. Check target_language: reported speech must be '
        'retold in that language, not pasted as untranslated quotations. Return '
        '{"approved":boolean,"issues":[strings]}.\n'+json.dumps({k:v for k,v in plan.items() if k!='parts'}|{
        'shots':compact_context_rows([{k:v for k,v in p.items() if k in ('source_id','start','end','text','role','mode','reason')}|{
            'local_speech':json.loads(p['evidence']).get('transcript','')[:400],
            'scene_context':scene_context(json.loads(p['evidence']))} for p in plan['parts']],limit=2800)},ensure_ascii=False),reasoning='medium')
    if not isinstance(raw,dict) or raw.get('approved') is not True:raise ValueError(str(raw.get('issues','Chưa đạt mạch chuyện') if isinstance(raw,dict) else 'Kết quả kiểm tra không hợp lệ')[:900])
    scene_problems=continuity_issues(plan['parts'])
    return {'approved':not scene_problems,'checks':checks,**({'issues':'; '.join(scene_problems)} if scene_problems else {})}


def repair_claims(plan,failure,lang,ctx,preset=None):
    """Repair only disputed sentences; do not regenerate already supported shots."""
    budgets=dict(zip((p['source_id'] for p in plan['parts']),narration_word_limits(plan['parts'],preset,lang))) if preset is not None else {}
    issues={r['source_id']:r.get('issue','Unsupported claim') for r in failure.checks
            if r.get('supported') is not True or r.get('scene_match') is not True}
    selected=[p for p in plan['parts'] if p['source_id'] in issues and p['mode']=='narrate']
    if not selected:raise ValueError(str(failure))
    candidate=deepcopy(plan);by_id={p['source_id']:p for p in candidate['parts']}
    for block in q.evidence_batches(selected,limit=6500):
        ctx.check_canceled()
        notes=[dict(p,issue=issues[p['source_id']],max_words=budgets.get(p['source_id'],word_budget(p['end']-p['start'],lang)),
            adjacent_draft_context_only=repair_context(candidate['parts'],p['source_id'])) for p in block]
        raw=q.ask(VOICE_CRAFT + 'Adjacent draft lines are context for pronouns and flow, NOT factual evidence. '
            'Repair the listed sentence so it connects to both neighbours; do not copy a claim from them. '
            + f'Repair ONLY these disputed narration sentences in {lang}. Return '
            '{"shots":[{"source_id":int,"text":"...","support_quote":"literal supporting excerpt"}]}. '
            'Use at most max_words per shot. Anchor the narration in an exact speech or visible-evidence '
            'quote from this SAME shot; include that quote in support_quote. Prefer attributed speech when '
            'the image is uncertain. No invented motion, motives, metaphors presented as facts, or guesses '
            'about an unclear object. Do not repeat the disputed claim. An opening hook can be a short '
            'concrete question about the supported contrast; it need not claim an unseen event.\n'+json.dumps(notes,ensure_ascii=False),reasoning='medium')
        rows=raw.get('shots',[]) if isinstance(raw,dict) else []
        if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) or len(rows)!=len(block) or {r.get('source_id') for r in rows}!={p['source_id'] for p in block}:
            raise ValueError('Chưa sửa đủ các câu bị đánh dấu.')
        for row in rows:
            p=by_id[row['source_id']];text=row.get('text');quote=row.get('support_quote')
            evidence=json.loads(p['evidence']);source=evidence.get('transcript','')+'\n'+'\n'.join(o.get('visible','') for o in evidence.get('observations',[]))
            norm=lambda s:' '.join(str(s).casefold().split())
            if not isinstance(quote,str) or len(quote.strip())<4 or norm(quote) not in norm(source):raise ValueError('Câu sửa chưa dẫn đúng căn cứ của cảnh.')
            if not isinstance(text,str) or not text.strip() or len(text)>1000:raise ValueError('Lời sửa không hợp lệ.')
            if not re.search(r'[\u3400-\u9fff\u3040-\u30ff]',text) and len(text.split())>budgets.get(p['source_id'],word_budget(p['end']-p['start'],lang)):raise ValueError('Lời sửa vẫn quá dài cho cảnh.')
            p['text']=text.strip();p['support_quote']=quote
    if candidate['parts'][0]['text']!=plan['parts'][0]['text']:
        # Retain old alternatives as suggestions; the repaired opening is the actual selected hook.
        candidate['hooks']=[candidate['parts'][0]['text']]+list(plan.get('hooks',[]))[:2]
        candidate['selected_hook']=0
    return candidate


def representative_observations(observations):
    ordered=sorted(observations,key=lambda o:float(o['at']))
    if len(ordered)<=3:return ordered
    return [ordered[0],ordered[len(ordered)//2],ordered[-1]]


def script(plan,preset,lang,ctx,index,count,src=None):
    limits=narration_word_limits(plan['parts'],preset,lang)
    target_ratio=narration_ratio(preset)
    error='';draft=None
    for attempt in range(3):
        ctx.check_canceled();ctx.progress(.70+.24*index/count,f'Viết hook, diễn biến và kết · Part {index+1}/{count}, lượt {attempt+1}/3')
        # Concise local facts for writing; full originals remain for the audit.
        notes=[]
        for p,limit in zip(plan['parts'],limits):
            u=json.loads(p['evidence'])
            notes.append({k:v for k,v in p.items() if k in ('source_id','start','end','mode','role')}|{'speech':u.get('transcript','')[:750],
                'max_words':limit, 'connection':str(p.get('reason',''))[:200],
                'visual':[{'at':o.get('at'),'visible':o.get('visible','')[:240],'uncertain':o.get('uncertain','')[:100]}
                    for o in representative_observations(u.get('observations',[]))]})
        previous=[{'source_id':p['source_id'],'text':p['text'][:220]} for p in draft['parts']] if draft else []
        if q.token_size(notes)+q.token_size(previous)>3800:
            for n in notes:
                n['speech']=n['speech'][:220]
                for o in n['visual']:o['visible']=o['visible'][:120];o['uncertain']=o['uncertain'][:70]
        from app.ai.editorial_context import NARRATION_RULES
        from app.ai.script_batches import write as write_batches
        instructions=(NARRATION_RULES + f'Write an engaging {lang} short-video narration. '
            + STYLE.get(preset.get('recap_style'),STYLE['story']) +
            ' Read the narration as one spoken paragraph. Narrate in third person, never impersonate the source speaker. Respect target language; '
            'translate reported speech naturally, keep verified names. Keep all supplied shot ids, order, '
            'modes and times. Write only those shots. Each narration must fit its max_words budget with '
            'breathing room. Orig rows must have empty text. For each narrated row quote a short literal '
            'support_quote from THAT row speech or visible evidence. Do not infer motion from stills. '
            'The opening is a specific factual curiosity hook answered by the ending; do not restart at each cut. Interpret idioms in context (lose it can mean lose composure, not lose an object). Preserve reported speech attribution: a father saying the mother yells at him is not children hearing her yell. Never turn a plan or attempt into a completed action. '
            'Return three alternative hooks and select one; selected hook opens the first spoken line. '
            'For later batches continue existing narration; keep the original hooks. Only final batch '
            'closes the story. Never invent a resolution. Repair listed errors while retaining valid lines. '
            'Use at most three SFX accents per whole Part, never fake real-event sounds. '
            'delivery: neutral/curious/brisk/measured/reflective; music_energy: auto/hush/low/mid/lift. '
            'music_mood: calm/mystery/tension/playful/bright/emotional. SFX allowed: '+','.join(sorted(SFX))+'. '
            'sfx_offset must be within this shot in seconds. Return {"title":"factual target-language title",'
            '"music_mood":"calm","hooks":["...","...","..."],"selected_hook":0,'
            '"shots":[{"source_id":0,"text":"...","support_quote":"...","delivery":"neutral",'
            '"music_energy":"auto","sfx":"none","sfx_offset":0,"sfx_reason":""}]}.')
        payload={'title':plan['title'],'angle':plan['angle'],'shots':notes,
            'narration_target_percent':target_ratio,'selection_issues':plan.get('selection_review'),
            'previous_hooks':preset.get('_previous_hooks',[]),'previous_draft':previous,'repair':error}
        try:
            raw=write_batches(instructions,payload,ctx)
            if not isinstance(raw,dict):raise ValueError('Kịch bản không đúng định dạng.')
            rows=raw.get('shots',[]);hooks=raw.get('hooks',[]);selected=raw.get('selected_hook')
            if not isinstance(hooks,list) or len(hooks)!=3 or any(not isinstance(h,str) or not h.strip() for h in hooks) or type(selected) is not int or not 0<=selected<3:raise ValueError('Thiếu lựa chọn hook.')
            if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) or len(rows)!=len(plan['parts']) or [r.get('source_id') for r in rows]!=[p['source_id'] for p in plan['parts']]:raise ValueError('Kịch bản đã đổi cảnh.')
            candidate=deepcopy(plan)
            candidate['target_language']=lang
            if isinstance(raw.get('title'),str) and raw['title'].strip():candidate['title']=raw['title'].strip()[:140]
            from app.core.music_library import MOODS
            mood=raw.get('music_mood')
            candidate['music_mood']=mood if isinstance(mood,str) and mood in MOODS else 'calm'
            for row,p,limit in zip(rows,candidate['parts'],limits):
                text=row.get('text');sfx=row.get('sfx','none')
                if not isinstance(text,str) or len(text)>1000 or (p['mode']=='narrate' and not text.strip()):raise ValueError('Lời kể thiếu hoặc quá dài.')
                if p['mode']=='narrate' and not re.search(r'[\u3400-\u9fff\u3040-\u30ff]',text) and len(text.split())>limit:
                    raise ValueError(f"Cảnh {p['source_id']} quá nhiều lời: tối đa {limit} từ theo tỷ lệ kể đã chọn. Viết ngắn lại từng cảnh, giữ hook trong câu đầu.")
                if not isinstance(sfx,str) or sfx not in SFX:sfx='none'  # Optional hints must not destroy a usable draft.
                p['text']=text.strip() if p['mode']=='narrate' else '';p['sfx']=sfx
                delivery=row.get('delivery');energy=row.get('music_energy')
                p['delivery']=delivery if isinstance(delivery,str) and delivery in DELIVERY else 'neutral'
                p['music_energy']=energy if isinstance(energy,str) and energy in ENERGY else 'auto'
                offset=row.get('sfx_offset',0.0)
                if type(offset) not in (int,float) or not math.isfinite(offset) or not 0<=offset<p['end']-p['start']:
                    p['sfx']='none';offset=0.0
                p['sfx_offset']=float(offset);p['sfx_reason']=str(row.get('sfx_reason',''))[:240]
                if p['mode']=='narrate':
                    quote=row.get('support_quote','');u=json.loads(p['evidence'])
                    evidence=u.get('transcript','')+'\n'+'\n'.join(o.get('visible','') for o in u.get('observations',[]))
                    normalize=lambda value:' '.join(str(value).casefold().split())
                    if isinstance(quote,str) and len(quote.strip())>=4 and normalize(quote) in normalize(evidence):
                        p['support_quote']=quote
                    # A missing verbatim quote is not proof of a false sentence.
                    # The mandatory independent audit below still checks the full
                    # local evidence; never display a fabricated citation.
            if not candidate['parts'][0]['text'].startswith(hooks[selected].strip()):
                # Some models revise the opening while leaving the selection
                # index stale. Audit the ACTUAL spoken opening, never prepend a
                # second hook or discard all otherwise valid narration.
                opening=re.split(r'(?<=[.!?])\s+',candidate['parts'][0]['text'],maxsplit=1)[0]
                hooks=[opening]+[h for h in hooks if h!=opening][:2];selected=0
            if sum(p['sfx']!='none' for p in candidate['parts'])>3:raise ValueError('Quá nhiều tiếng động; chỉ nhấn tối đa 3 tình tiết.')
            candidate['hooks']=hooks;candidate['selected_hook']=selected;draft=candidate
            for repair in range(3):
                try:
                    candidate['review']=audit(candidate,ctx)
                    if plan.get('selection_review',{}).get('approved') is False:
                        candidate['review']['approved']=False
                        candidate['review']['issues']='Cần duyệt liên hệ giữa các cảnh: '+str(plan['selection_review'].get('issues',''))
                    return candidate
                except AuditFailure as exc:
                    candidate['review']={'approved':False,'issues':str(exc),'checks':exc.checks};draft=candidate
                    if repair==2:return draft
                    if repair==0 and src:
                        ctx.progress(.75+.2*index/count,f'Xem thêm đầu/cuối cảnh có câu chưa khớp · Part {index+1}/{count}')
                        inspect_disputed(candidate,exc.checks,src,ctx)
                    ctx.progress(.75+.2*index/count,f'Sửa đúng câu chưa khớp · Part {index+1}/{count}, lượt {repair+1}/2')
                    try:candidate=repair_claims(candidate,exc,lang,ctx,preset)
                    except ValueError:return draft
                except ValueError as exc:
                    error=str(exc);candidate['review']={'approved':False,'issues':error};break
        except ValueError as exc:error=str(exc)
    if draft is not None:
        if 'review' not in draft:draft['review']={'approved':False,'issues':error}
        return draft
    raise RuntimeError('Chưa viết được kịch bản đầy đủ: '+error)


def direct(units,src,used,preset,count,lang,ctx,cache=None):
    from pathlib import Path
    preset=dict(preset,_source_title=Path(src).stem)
    started=time.monotonic();saved={};checkpoint_key=None
    if cache:
        from app.core.analysis import get_analysis,_set
        from config import settings
        checkpoint_key=q.digest([2,cache[1],preset,sorted(used),count,lang,q.llm.active_provider(),
            getattr(settings,'GEMINI_MODEL',''),getattr(settings,'GROQ_MODEL',''),
            getattr(settings,'OLLAMA_MODEL',''),q.llm.groq_vision_model()] +
            ([settings.APIFORCODE_MODEL,settings.APIFORCODE_VISION_MODEL] if q.llm.active_provider()=='apiforcode' else []))
        previous=get_analysis(cache[0],'story_director') or {}
        body=previous.get('state')
        if (previous.get('key')==checkpoint_key and isinstance(body,dict)
            and previous.get('checksum')==q.digest(body)):
            saved=deepcopy(body)
    if saved.get('editorial_version')!=3:
        for name in ('cards','catalogue_partial','plans','refined','scripts'):saved.pop(name,None)
        saved['editorial_version']=3
    if narration_ratio(preset) is not None and saved.get('narration_settings_version')!=1:
        # Keep paid event indexing; previous plans/scripts ignored this setting.
        for name in ('plans','refined','scripts'):saved.pop(name,None)
        saved['narration_settings_version']=1

    def save():
        if cache:
            _set(cache[0],'story_director','done',{'key':checkpoint_key,'state':deepcopy(saved),
                 'checksum':q.digest(saved)},engine=q.llm.active_provider())

    def save_evidence():
        if cache:
            # Persist each completed refined image set, including partial runs.
            _set(cache[0],'story_evidence','done',{'key':cache[1],
                 'units':{str(u['id']):u for u in units},'complete':True},engine=q.llm.active_provider())

    cards=saved.get('cards')
    if cards is None:
        with q.request_stage(ctx,'Lập bản đồ tình tiết',.48):
            cards=catalogue(units,ctx,state=saved.setdefault('catalogue_partial',{}),on_checkpoint=save)
        saved['cards']=cards;save()
    else:ctx.progress(.48,'Dùng bản đồ tình tiết đã lưu; không gọi AI lại bước này')
    plans=saved.get('plans')
    if plans is None:
        with q.request_stage(ctx,'Chọn mạch chuyện',.53):plans=choose_edits(units,cards,used,preset,count,ctx)
        saved['plans']=deepcopy(plans);save()
    else:ctx.progress(.56,'Dùng các mạch chuyện đã lưu; tiếp tục bước còn thiếu')
    if not saved.get('refined'):
        if cache:refine(plans,units,src,ctx,on_checkpoint=save_evidence)
        else:refine(plans,units,src,ctx)
        saved['plans']=deepcopy(plans);saved['refined']=True;save_evidence();save()
    else:ctx.progress(.69,'Dùng phần đối chiếu cảnh đã lưu')
    completed=saved.setdefault('scripts',{})
    hooks=[]
    for i,plan in enumerate(plans):
        ctx.check_canceled()
        if str(i) in completed:
            plans[i]=deepcopy(completed[str(i)])
            ctx.progress(.70+.24*i/max(1,len(plans)),f'Dùng kịch bản Part {i+1} đã lưu; vẫn cần duyệt trước khi xuất')
        else:
            with q.request_stage(ctx,f'Viết và kiểm tra kịch bản Part {i+1}/{len(plans)}',.70+.24*i/max(1,len(plans))):
                plans[i]=script(plan,dict(preset,_previous_hooks=hooks),lang,ctx,i,len(plans),src=src)
            completed[str(i)]=deepcopy(plans[i]);save()
        hooks.append(plans[i]['parts'][0]['text'][:180])
    if cache:
        lookup={u['id']:u for u in units}
        for plan in plans:
            for part in plan['parts']:
                evidence=json.loads(part['evidence']);u=lookup[part['source_id']]
                u['observations']=list({float(o['at']):o for o in u.get('observations',[])+evidence.get('observations',[])}.values())
        _set(cache[0],'story_evidence','done',{'key':cache[1],'units':{str(u['id']):u for u in units},'complete':True},engine=q.llm.active_provider())
    return plans,{'planning_seconds':round(time.monotonic()-started,1),'source_units':len(units),
                  'selected_units':sum(len(p['parts']) for p in plans),'requested_parts':count,'planned_parts':len(plans),
                  'audio_plan_version':1}
