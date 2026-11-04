"""Budget complete script requests, retaining every selected scene in order."""
import json
from copy import deepcopy
from app.ai import story_quality as q

def fits(prompt):
    return q.llm._uoc_token(prompt)+q.llm._uoc_token(q.SYSTEM)<=q.request_input_limit()

def write(instructions,payload,ctx):
    def encode(data):return instructions+'\n'+json.dumps(data,ensure_ascii=False)
    if fits(encode(payload)) and len(payload['shots'])<=6:
        return q.ask(encode(payload),reasoning='medium')
    shots=payload['shots'];result=None;written=[];position=0
    while position<len(shots):
        ctx.check_canceled()
        # Context is explicitly NOT local factual evidence. Keep the last lines
        # intact for pronouns and the actual ending anchor for hook continuity.
        base={k:deepcopy(v) for k,v in payload.items() if k not in ('shots','previous_draft')}
        base['batch_context_only']={'first_batch':position==0,'last_batch':False,
            'previous_lines':[{'source_id':r['source_id'],'text':r.get('text','')} for r in written[-2:]],
            'opening':written[0].get('text','') if written else '',
            'ending_connection':shots[-1].get('connection',''),
            'story_arc_context_only':[{'source_id':r['source_id'],'role':r.get('role'),'connection':str(r.get('connection',''))[:100]} for r in (shots[:2]+shots[-2:])],
            'direction':'Write only supplied shots. Continue the story without a new hook or introduction after batch one. Context is not evidence; preserve speaker references.'}
        if result:
            base['batch_context_only']['hooks']=result.get('hooks',[])
        block=[];prompt=None
        for row in shots[position:position+6]:
            candidate=block+[row];ids={n['source_id'] for n in candidate}
            data=deepcopy(base);data['shots']=candidate
            data['previous_draft']=[r for r in payload.get('previous_draft',[]) if r['source_id'] in ids]
            data['batch_context_only']['last_batch']=position+len(candidate)==len(shots)
            trial=encode(data)
            if not fits(trial):break
            block=candidate;prompt=trial
        if not block:
            raise ValueError('Một cảnh và ngữ cảnh viết vượt ngân sách AI; chưa gửi yêu cầu, giữ nguyên cảnh nguồn.')
        raw=q.ask(prompt,reasoning='medium')
        rows=raw.get('shots') if isinstance(raw,dict) else None
        if (not isinstance(rows,list) or any(not isinstance(r,dict) for r in rows)
            or [r.get('source_id') for r in rows]!=[r['source_id'] for r in block]):
            raise ValueError('AI trả thiếu, trùng hoặc đổi thứ tự cảnh trong nhóm viết.')
        if result is None:result=deepcopy(raw)
        written.extend(rows);position+=len(block)
    # Three accents per Part, not three per batch. Optional accents never force
    # regeneration or change narration/source timing.
    accents=0
    for row in written:
        if row.get('sfx','none')!='none':
            accents+=1
            if accents>3:row['sfx']='none'
    result['shots']=written
    return result
