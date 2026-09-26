"""Local warning signals, not proof of event identity or automated fact checking."""
import json
import re
import unicodedata
from collections import Counter

def evidence(part):
    try:value=json.loads(part.get('evidence') or '{}')
    except (ValueError,TypeError):return {}
    return value if isinstance(value,dict) else {}

def dates(unit):
    # Only dates explicitly described in visible frames; not arbitrary years in dialogue.
    counts=Counter()
    for o in unit.get('observations',[]):
        if not isinstance(o,dict):continue
        counts.update(set(re.findall(r'\b(20\d{2}-[01]\d-[0-3]\d)\b',str(o.get('visible','')))))
    return sorted(d for d,n in counts.items() if n>=2)

def context(unit):
    observations=[o for o in unit.get('observations',[]) if isinstance(o,dict)]
    if len(observations)>3:observations=[observations[0],observations[len(observations)//2],observations[-1]]
    return dict(observed_dates=dates(unit),visual=[dict(at=o.get('at'),visible=str(o.get('visible',''))[:240],
        uncertain=str(o.get('uncertain',''))[:100]) for o in observations])

def continuity_issues(parts):
    anchors=[(i,dates(evidence(p))) for i,p in enumerate(parts)]
    known=[set(d) for _,d in anchors if d]
    if len(known)<2 or set.intersection(*known):return []
    detail='; '.join(f'Cảnh {i+1}: '+', '.join(d) for i,d in anchors if d)
    return ['Mô tả hình có ngày ghi khác nhau; có thể ghép nhầm các vụ việc. Cần xem nguồn, không coi đây là cùng một diễn biến: '+detail]

def language_issues(parts,lang):
    if str(lang).casefold() not in ('vi','vietnamese','vi-vn'):return []
    issues=[]
    normalize=lambda s:unicodedata.normalize('NFKC',s).replace('’',"'").casefold()
    pattern=r"(?<![\w])(?:[A-Za-z]+(?:['’][A-Za-z]+)?[ \t]+){3,}[A-Za-z]+(?:['’][A-Za-z]+)?(?![\w])"
    for i,p in enumerate(parts):
        if p.get('mode')!='narrate':continue
        speech=normalize(str(evidence(p).get('transcript','')))
        for match in re.finditer(pattern,str(p.get('text',''))):
            run=match.group().strip()
            # Detect copied source phrases, not names, brands or short loanwords.
            words=run.split()
            if normalize(run) in speech and any(w[0].islower() for w in words):
                issues.append(f'Cảnh {i+1}: lời tiếng Việt còn chép nguyên câu nguồn "{run[:90]}". Viết lại ý bằng tiếng Việt, giữ đúng người nói và mức chắc chắn.');break
    return issues

def warnings(parts,lang):return language_issues(parts,lang)+continuity_issues(parts)
