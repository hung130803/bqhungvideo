"""Whole-source story selection, selective verification and economical script audits."""
import json
import math
import time
from copy import deepcopy
import re
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from app.ai import story_quality as q

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


def catalogue(units,ctx):
    """One batched pass indexes every unit; never one summary call per frame."""
    cards=[]
    for no,block in enumerate(q.evidence_batches(units,limit=6500),1):
        ctx.check_canceled();ctx.progress(.48,f'Lập bản đồ tình tiết toàn nguồn · nhóm {no}')
        wanted={u['id'] for u in block}
        found={}
        for attempt in range(2):
            remaining=[u for u in block if u['id'] not in found]
            if not remaining:break
            ctx.check_canceled()
            raw=q.ask('Index EVERY source interval, preserving its id. Return {"events":[{"id":int,'
                '"event":"at most 140 characters: specific event or speech claim + uncertainty",'
                '"interest":0-5}]}. Include even quiet intervals. Prioritize a concrete setup, unexpected change, reaction, consequence, '
                'payoff or useful explanation. Do not narrate a still-image inventory; do not invent motion. '
                'Interest is editorial relevance, not certainty.\n'+json.dumps(remaining,ensure_ascii=False))
            values=raw.get('events',[]) if isinstance(raw,dict) else []
            for value in values if isinstance(values,list) else []:
                if not isinstance(value,dict) or type(value.get('id')) is not int or value['id'] not in wanted:continue
                event=value.get('event');score=value.get('interest')
                if not isinstance(event,str) or not event.strip() or type(score) not in (int,float) or not math.isfinite(score):continue
                found[value['id']]={'id':value['id'],'event':event[:260],'interest':max(0,min(5,score))}
        if set(found)!=wanted:
            raise RuntimeError('Bản đồ tình tiết thiếu cảnh; thử lại để dùng phần xem hình đã lưu.')
        cards.extend(found.values())
    return sorted(cards,key=lambda v:v['id'])


def planning_cards(cards,ctx):
    """For long sources, retain story candidates from every region, then compare."""
    while q.token_size(cards)>2400:
        selected=[]
        for block in q.evidence_batches(cards,limit=5500):
            ctx.check_canceled()
            raw=q.ask('Select a connected set of the best story seeds from these events: setups AND payoffs, '
                'not just spectacle. Keep at most half the ids (minimum 2). Return {"ids":[int]}.\n'+json.dumps(block,ensure_ascii=False))
            ids=raw.get('ids',[]) if isinstance(raw,dict) else []
            if not ids or len(set(ids))!=len(ids) or any(type(i) is not int or i not in {c['id'] for c in block} for i in ids):
                raise RuntimeError('Chưa chọn được các tình tiết có căn cứ.')
            selected.extend(c for c in block if c['id'] in ids)
        if len(selected)>=len(cards):raise RuntimeError('AI chưa thu gọn được ứng viên; hãy thử lại.')
        cards=selected
    return cards


def validate_edit(raw,units,used,minimum,maximum):
    if not isinstance(raw,dict) or not isinstance(raw.get('title'),str) or not raw['title'].strip():raise ValueError('Thiếu tiêu đề câu chuyện.')
    shots=raw.get('shots');lookup={u['id']:u for u in units}
    if not isinstance(shots,list) or not 4<=len(shots)<=24:raise ValueError('Cần 4–24 cảnh có vai trò rõ ràng.')
    seen=set();parts=[];last=-1
    for shot in shots:
        if not isinstance(shot,dict):raise ValueError('Cảnh không hợp lệ.')
        uid=shot.get('source_id');role=shot.get('role');why=shot.get('reason','')
        if type(uid) is not int or uid not in lookup or uid in seen or uid in used or uid<=last:raise ValueError('Cảnh không có nguồn, trùng hoặc đảo diễn biến.')
        if role not in ROLES or not isinstance(why,str) or len(why.strip())<8:raise ValueError('Thiếu vai trò hoặc lý do chọn cảnh.')
        u=lookup[uid];a=shot.get('start',u['start']);b=shot.get('end',u['end'])
        if type(a) not in (int,float) or type(b) not in (int,float) or not math.isfinite(a+b) or not u['start']<=a<b<=u['end'] or b-a<1.5:
            raise ValueError('Mốc cắt vượt cảnh nguồn hoặc cảnh quá ngắn.')
        mode=shot.get('mode','narrate')
        if mode not in ('orig','narrate'):raise ValueError('Vai âm thanh không hợp lệ.')
        if mode=='orig' and (not u.get('safe_orig',True) or a!=u['start'] or b!=u['end']):
            raise ValueError('Cảnh giữ lời gốc phải có mép câu trọn vẹn.')
        sfx=shot.get('sfx','none')
        if sfx not in SFX:raise ValueError('Loại tiếng động không được hỗ trợ.')
        parts.append(dict(start=float(a),end=float(b),mode=mode,text='',source_id=uid,role=role,
                          reason=why.strip()[:400],sfx=sfx,evidence=json.dumps(u,ensure_ascii=False)))
        seen.add(uid);last=uid
    duration=sum(p['end']-p['start'] for p in parts)
    if not minimum<=duration<=maximum:raise ValueError(f'Tổng cảnh {duration:.1f}s; cần {minimum:.0f}–{maximum:.0f}s.')
    if parts[0]['role']!='hook' or parts[0]['mode']!='narrate' or not any(p['role']=='payoff' for p in parts):
        raise ValueError('Cần hook mở đầu và cảnh trả lời điều hook đã hứa.')
    gaps=sum(b['start']-a['end']>1 for a,b in zip(parts,parts[1:]))
    continuous=str(raw.get('continuous_reason') or '').strip()
    if not gaps and len(lookup)>len(parts)+2 and len(continuous)<25:
        raise ValueError('Đang lấy nguyên một cụm liền: chọn setup/diễn biến/kết quả ở các vị trí phù hợp, hoặc giải thích vì sao hành động phải liền mạch.')
    return {'title':raw['title'].strip()[:250],'angle':str(raw.get('angle',''))[:400],
            'continuous_reason':continuous,'parts':parts,'windows':[[p['start'],p['end']] for p in parts],'duration':duration}


def choose_edits(units,cards,used,preset,count,ctx):
    """Choose one coherent story at a time, then reserve its source intervals."""
    minimum,maximum=q.length_limits(preset)
    lookup={u['id']:u for u in units};reserved=set(used);plans=[]
    for part_index in range(count):
        available=[dict(c) for c in cards if c['id'] not in reserved]
        # Compact rows keep EVERY normal-length source interval visible. Do not
        # rank away a quiet setup before the whole-source story is understood.
        notes=[[c['id'],round(lookup[c['id']]['end']-lookup[c['id']]['start'],2),c['event']] for c in available]
        if q.token_size(notes)>3300:
            notes=[[row[0],row[1],row[2][:140]] for row in notes]
        if q.token_size(notes)>3300:
            available=planning_cards(available,ctx)
            notes=[[c['id'],round(lookup[c['id']]['end']-lookup[c['id']]['start'],2),c['event'][:140]] for c in available]
        allowed={n[0] for n in notes};error='';previous=None;reviewable=None
        for attempt in range(3):
            ctx.check_canceled();ctx.progress(.53,f'Chọn mạch chuyện {part_index+1}/{count} · lượt {attempt+1}/3')
            raw=q.ask(f'Select ONE complete story lasting {minimum}-{maximum}s from these source events. '
                'Each compact event row is [source_id, seconds, event description]. '
                'Choose a SPECIFIC incident, NOT a montage of unrelated daily activities. First identify its '
                'setup and its actual outcome/reaction, then select the connected events needed to understand it. '
                'Look across the WHOLE source: the setup can be minutes before the payoff. Do not assume two '
                'different objects or meals are the same thing. Treat source_title only as a topic hint, not proof. '
                'For the first Part, connect the title topic preparation to its later reveal/reaction WHEN supported. '
                'Do not abandon the central topic just because still images leave objects uncertain; attributed '
                'speech can establish what the participants SAY they prepared or discovered. Then distinct remaining '
                'stories on later Parts. No invented danger, identity, surprise or causal connection. '
                'Use unique ids in chronological order. SUM their seconds to reach the target: six 12s '
                'intervals = 72s. Do not take an arbitrary continuous block. If action must remain continuous, '
                'explain why. Never pad an incomplete story with irrelevant scenes. Return '
                '{"title":"factual title","angle":"one specific real contrast",'
                '"continuous_reason":"only when necessary","shots":[{"source_id":int,'
                '"reason":"specific connection to THIS story","mode":"narrate|orig"}]}. '
                'Narration is the default. Opening always narrated. If repairing, address the specific '
                'error while retaining valid scenes.\n'+json.dumps({'source_title':preset.get('_source_title',''),
                'events':notes,'already_planned':[p['title'] for p in plans],'repair':error,'previous_plan':previous},ensure_ascii=False),reasoning='medium')
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
                    if i==0 or not lookup[shot['source_id']].get('safe_orig',True):shot['mode']='narrate'
                plan=validate_edit(prepared,units,reserved,minimum,maximum)
                # Check relationships against original speech, not only condensed event cards.
                evidence=[{'id':p['source_id'],'reason':p['reason'],
                    'speech':lookup[p['source_id']].get('transcript','')[:750],
                    'event':next(c['event'] for c in available if c['id']==p['source_id'])} for p in plan['parts']]
                if q.token_size(evidence)>3500:
                    for e in evidence:e['speech']=e['speech'][:300]
                check=q.ask('Verify the proposed story using these original source speech excerpts and '
                    'event notes. Are these scenes about ONE connected story, with a real setup and outcome? '
                    'Anonymous people, unnamed relationships and gaps that skip irrelevant material are valid: '
                    'do not reject solely because a name or identity is unknown. The same incident can be '
                    'understood from attributed dialogue, without demanding proof of every motion in a still. '
                    'Approval means this selection CAN be told accurately by attributing speech and avoiding '
                    'unproven details; it does not certify that the speakers told the truth. Unknown ingredients '
                    'or a joke about disguising food do not make the story unusable if narration reports the claims. '
                    'Reject unrelated topics used as padding, switching one food/object for another without '
                    'evidence, or claiming a reveal/reaction that is not shown or stated. Speech is a speaker '
                    'claim, not objective proof. Do not demand every event appear in a still image. '
                    'Return {"approved":boolean,"issues":"specific correction","title":"accurate concise title",'
                    '"angle":"accurate angle"}.\n'+json.dumps({'title':plan['title'],'angle':plan['angle'],'evidence':evidence},ensure_ascii=False),reasoning='medium')
                if not isinstance(check,dict) or check.get('approved') is not True:
                    plan['selection_review']={'approved':False,'issues':str(check.get('issues','Cần xem lại mạch chuyện') if isinstance(check,dict) else 'Kiểm tra mạch chuyện chưa trả đủ dữ liệu')[:900]}
                    reviewable=plan
                    raise ValueError(str(check.get('issues','Các cảnh chưa cùng một câu chuyện') if isinstance(check,dict) else 'Kiểm tra mạch chuyện không hợp lệ')[:700])
                for key in ('title','angle'):
                    if isinstance(check.get(key),str) and check[key].strip():plan[key]=check[key].strip()[:250]
                plans.append(plan);reserved.update(p['source_id'] for p in plan['parts']);break
            except ValueError as exc:
                error=str(exc)
                previous=raw if isinstance(raw,dict) and q.token_size(raw)<1200 else None
        else:
            if reviewable is None:raise RuntimeError('Chưa chọn được câu chuyện đủ dài và có căn cứ: '+error)
            # Structurally valid drafts remain editable, but semantic doubts are
            # never turned into an automatic approval or hidden from the user.
            plans.append(reviewable);reserved.update(p['source_id'] for p in reviewable['parts'])
    return plans


def refine(plans,units,src,ctx):
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
        if len(u['observations'])<2:
            extra=q.visual_evidence(src,u,u['transcript'],child,fractions=(.2,.8) if not u['observations'] else (.85,))
            u['observations']+=extra['observations']
            source['observations']=source.get('observations',[])+extra['observations']
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
            ctx.progress(.59+.10*done/max(1,len(selected)),f'Đối chiếu đúng khúc sẽ xuất {done}/{len(selected)}'+child.status())


def audit(plan,ctx):
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
    raw=q.ask('Audit this finished SHORT STORY. Specific hook paid off? Clear setup-change-payoff? '
        'No unrelated cuts, repetitive image descriptions, filler, unsupported title, or false causality? '
        'Natural varied spoken language, not a list of what is on screen? Return '
        '{"approved":boolean,"issues":[strings]}.\n'+json.dumps({k:v for k,v in plan.items() if k!='parts'}|{
        'shots':[{k:v for k,v in p.items() if k!='evidence'} for p in plan['parts']]},ensure_ascii=False),reasoning='medium')
    if not isinstance(raw,dict) or raw.get('approved') is not True:raise ValueError(str(raw.get('issues','Chưa đạt mạch chuyện') if isinstance(raw,dict) else 'Kết quả kiểm tra không hợp lệ')[:900])
    return {'approved':True,'checks':checks}


def repair_claims(plan,failure,lang,ctx):
    """Repair only disputed sentences; do not regenerate already supported shots."""
    issues={r['source_id']:r.get('issue','Unsupported claim') for r in failure.checks
            if r.get('supported') is not True or r.get('scene_match') is not True}
    selected=[p for p in plan['parts'] if p['source_id'] in issues and p['mode']=='narrate']
    if not selected:raise ValueError(str(failure))
    candidate=deepcopy(plan);by_id={p['source_id']:p for p in candidate['parts']}
    for block in q.evidence_batches(selected,limit=6500):
        ctx.check_canceled()
        notes=[dict(p,issue=issues[p['source_id']],max_words=max(3,int((p['end']-p['start'])*1.9))) for p in block]
        raw=q.ask(f'Repair ONLY these disputed narration sentences in {lang}. Return '
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
            if not re.search(r'[\u3400-\u9fff\u3040-\u30ff]',text) and len(text.split())>max(3,int((p['end']-p['start'])*1.9)):raise ValueError('Lời sửa vẫn quá dài cho cảnh.')
            p['text']=text.strip();p['support_quote']=quote
    if candidate['parts'][0]['text']!=plan['parts'][0]['text']:
        # Retain old alternatives as suggestions; the repaired opening is the actual selected hook.
        candidate['hooks']=[candidate['parts'][0]['text']]+list(plan.get('hooks',[]))[:2]
        candidate['selected_hook']=0
    return candidate


def script(plan,preset,lang,ctx,index,count):
    error='';draft=None
    for attempt in range(3):
        ctx.check_canceled();ctx.progress(.70+.24*index/count,f'Viết hook, diễn biến và kết · Part {index+1}/{count}, lượt {attempt+1}/3')
        # Concise local facts for writing; full originals remain for the audit.
        notes=[]
        for p in plan['parts']:
            u=json.loads(p['evidence'])
            notes.append({k:v for k,v in p.items() if k in ('source_id','start','end','mode','role')}|{'speech':u.get('transcript','')[:750],
                'max_words':max(3,int((p['end']-p['start'])*1.9)),
                'visual':[{'at':o.get('at'),'visible':o.get('visible','')[:240],'uncertain':o.get('uncertain','')[:100]} for o in u.get('observations',[])[:3]]})
        if q.token_size(notes)>3800:
            for n in notes:
                n['speech']=n['speech'][:220]
                for o in n['visual']:o['visible']=o['visible'][:120];o['uncertain']=o['uncertain'][:70]
        raw=q.ask(f'Write an engaging {lang} short-video narration. '+STYLE.get(preset.get('recap_style'),STYLE['story'])+
            ' Narrate as an outside storyteller, never impersonate the source speaker using I/my/we. '
            'Invent wording, not events. Avoid "we see", generic "nobody expected this", listing frame objects, '
            'or repeating the same sentence skeleton. Make the FIRST 2-3 seconds a concrete curiosity hook tied '
            'to the opening scene; pay it off later. Write 3 alternative hooks, choose the strongest supported one. '
            'Use setup -> escalation/change -> reaction/consequence -> satisfying ending. Link distant shots '
            'with honest bridges; keep uncertainty and speech attribution. Respect every existing shot id/mode/time; '
            'do NOT change scene order. Aim 1.3-1.7 spoken words/sec of each narrated window, leave breathing room. '
            'Each row has a HARD max_words limit; a 12-second shot needs roughly 16-22 words, NOT 40-60. '
            'Do not invent or exaggerate an action even for humor. A joke may comment on a REAL contrast, '
            'but must not claim an imaginary accident, reaction, object, relationship or identity. '
            'For EACH narrated shot choose a literal short support_quote from its speech (preferred) or visible '
            'evidence, then write the narration around THAT supported fact. Do not describe motion inferred '
            'from still images. Names are unnecessary: anonymous speaker labels are fine. No imaginary '
            'wind effects, ingredients, identities, or assumptions about what an unclear object really is. '
            'Orig rows have empty text. At most 3 editorial SFX accents, select meaningful emotional beats; '
            'Allowed SFX labels ONLY: '+','.join(sorted(SFX))+'. '
            'do not fake police sirens, gunshots or real-event sounds. Return {"hooks":[3 strings],'
            '"selected_hook":0-2,"shots":[{"source_id":int,"support_quote":"literal source excerpt","text":"...","sfx":"none"}]}. '
            'The selected hook must open the first narration, not be repeated in later shots.\n'+
            json.dumps({'title':plan['title'],'angle':plan['angle'],'shots':notes,'selection_issues':plan.get('selection_review'),'repair':error},ensure_ascii=False),reasoning='medium')
        try:
            if not isinstance(raw,dict):raise ValueError('Kịch bản không đúng định dạng.')
            rows=raw.get('shots',[]);hooks=raw.get('hooks',[]);selected=raw.get('selected_hook')
            if not isinstance(hooks,list) or len(hooks)!=3 or any(not isinstance(h,str) or not h.strip() for h in hooks) or type(selected) is not int or not 0<=selected<3:raise ValueError('Thiếu lựa chọn hook.')
            if not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows) or len(rows)!=len(plan['parts']) or [r.get('source_id') for r in rows]!=[p['source_id'] for p in plan['parts']]:raise ValueError('Kịch bản đã đổi cảnh.')
            candidate=deepcopy(plan)
            for row,p in zip(rows,candidate['parts']):
                text=row.get('text');sfx=row.get('sfx','none')
                if not isinstance(text,str) or len(text)>1000 or (p['mode']=='narrate' and not text.strip()):raise ValueError('Lời kể thiếu hoặc quá dài.')
                if p['mode']=='narrate' and not re.search(r'[\u3400-\u9fff\u3040-\u30ff]',text) and len(text.split())>max(3,int((p['end']-p['start'])*1.9)):
                    raise ValueError(f"Cảnh {p['source_id']} quá nhiều lời: tối đa {int((p['end']-p['start'])*1.9)} từ. Viết ngắn lại từng cảnh, giữ hook trong câu đầu.")
                if sfx not in SFX:sfx='none'  # An optional sound label must not destroy an otherwise usable draft.
                p['text']=text.strip() if p['mode']=='narrate' else '';p['sfx']=sfx
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
                    ctx.progress(.75+.2*index/count,f'Sửa đúng câu chưa khớp · Part {index+1}/{count}, lượt {repair+1}/2')
                    try:candidate=repair_claims(candidate,exc,lang,ctx)
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
    started=time.monotonic();cards=catalogue(units,ctx)
    plans=choose_edits(units,cards,used,preset,count,ctx)
    refine(plans,units,src,ctx)
    if cache:
        from app.core.analysis import _set
        _set(cache[0],'story_evidence','done',{'key':cache[1],'units':{str(u['id']):u for u in units},'complete':True},engine=q.llm.active_provider())
    for i,plan in enumerate(plans):plans[i]=script(plan,preset,lang,ctx,i,count)
    return plans,{'planning_seconds':round(time.monotonic()-started,1),'source_units':len(units),
                  'selected_units':sum(len(p['parts']) for p in plans)}
