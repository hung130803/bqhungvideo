"""Bounded editorial controls; no network, rewriting or voice substitution."""
import re

DELIVERY={'neutral':'Tự nhiên','curious':'Gợi tò mò','brisk':'Dứt khoát','measured':'Rõ, chậm vừa','reflective':'Trầm, kết câu'}
ENERGY={'auto':'Theo vai trò cảnh','hush':'Hạ sâu / nhường tiếng gốc','low':'Nhẹ','mid':'Vừa','lift':'Nâng cao trào'}

def word_budget(seconds,lang):
    # Vietnamese whitespace separates syllables, not English-like words.
    vi=str(lang).casefold() in ('vi','vietnamese','vi-vn')
    return max(3,int(max(0,float(seconds))*(3.2 if vi else 1.9)))

def narration_ratio(preset):
    """UI percentage; none preserves contracts for legacy callers without it."""
    import math
    if 'recap_ratio' not in preset:return None
    try:value=float(preset['recap_ratio'])
    except (TypeError,ValueError):value=45.
    if not math.isfinite(value):value=45.
    return min(80.,max(15.,value))


def narration_word_limits(parts,preset,lang):
    """Budget SPOKEN time, not full shot time; original audio fills the rest.

    This is a writing estimate. Actual timing remains measured after TTS.
    Never shorten approved audio or change source windows to meet a ratio.
    """
    ratio=narration_ratio(preset)
    total=sum(max(0.,p['end']-p['start']) for p in parts)
    narrated=sum(max(0.,p['end']-p['start']) for p in parts if p.get('mode')=='narrate')
    factor=min(1.,total*ratio/100./narrated) if ratio is not None and narrated>0 else 1.
    rate=2.7 if str(lang).casefold() in ('vi','vietnamese','vi-vn') else 1.6
    return [0 if p.get('mode')!='narrate' else word_budget(p['end']-p['start'],lang)
        if ratio is None else min(word_budget(p['end']-p['start'],lang),max(3,int((p['end']-p['start'])*factor*rate))) for p in parts]


def delivery_rate(base,delivery):
    match=re.fullmatch(r'([+-]?\d+)%',str(base))
    if not match:return base
    delta={'neutral':0,'curious':-2,'brisk':4,'measured':-4,'reflective':-6}.get(delivery,0)
    return f'{max(-30,min(30,int(match[1])+delta)):+d}%'

def writing_direction(lang):
    native=(' Vietnamese: write idiomatic spoken Vietnamese, not word-for-word English. '
            'Count whitespace tokens as syllables; target 2.3-2.8 syllables/sec, never pad to the maximum. '
            'Use natural subject references; avoid stiff nominal phrases, repeated "người đàn ông này", '
            'invented slang, and sensational moral judgements. Translate reported speech into Vietnamese; '
            'never paste a whole English sentence into Vietnamese narration. Keep source quotes only in support_quote, '
            'not in spoken text. Retain proper names only when clearly supported. Translate ordinary English terms '
            'into familiar Vietnamese (for example bodycam = camera gắn trên người, prank = trò đùa); '
            'keep verified person/place/brand names unchanged, never invent phonetic spellings. '
            'Prefer a short natural reference after introducing a name. Write abbreviations and units '
            'in speakable Vietnamese when their meaning is known.' if str(lang).casefold() in ('vi','vietnamese','vi-vn') else '')
    return (' Before wording, internally outline ONE question, the factual context needed to understand it, '
            'the evidenced change and the answer. Each line must move that same story forward. '
            'Read all lines as one spoken paragraph, not isolated captions. Introduce the subject clearly, '
            'resolve pronouns and avoid unexplained jumps. Keep chronological order; never turn correlation into cause. '
            'Use concrete verbs, varied sentence lengths, restrained punctuation and one thought per breath. '
            'Do not write a sequence of flat image captions such as "she holds X, then she shows Y". '
            'Explain what each evidenced beat changes in the central question; omit redundant object inventories. '
            'Join consecutive narration lines with natural references and meaningful pauses, not a fresh introduction every shot. '
            'Prefer speakable sentences to headline fragments, formal report jargon and forced exclamations. '
            'Leave space for important original dialogue. No stage directions or emotion tags in spoken text. '
            'Humor and tension must arise from the source, not stock cliffhangers. The ending must answer the opening, '
            'without inventing an outcome outside the footage. Internally compare three grounded openings: '
            'a concrete contrast, an unresolved question, or an immediate consequence; choose only the one '
            'supported by these scenes. Avoid generic openings like you will not believe what happened. '
            'Vary the narrative angle between Parts; each Part needs its own evidenced question and answer, '
            'not merely a reworded title. Never invent dialogue or misidentify the speaker.'+native)


def gemini_delivery_prefix(lang, pace='normal', delivery='neutral', emotion=True, window=None):
    """TTS-only direction: never alter approved script or subtitle text."""
    language='Vietnamese' if str(lang).lower() in ('vi','vi-vn','vietnamese') else str(lang)
    # Provider pace is stochastic; apply the selected tempo after synthesis.
    speed='fluent conversational'
    tone={'neutral':'natural, warm and direct', 'curious':'light curiosity, stressing the key contrast',
          'brisk':'confident and decisive', 'measured':'clear and composed, not drawn-out',
          'reflective':'warm and thoughtful with a concise ending'}.get(delivery,'natural and direct')
    timing=''
    if window is not None:
        import math
        seconds=float(window)
        if not math.isfinite(seconds) or seconds<=0:raise ValueError('Invalid speech window')
        timing=f' Finish within {seconds:.2f} seconds; this is a maximum, not a target to fill. Never slow down to fill the scene.'
    return (f'Read the text below exactly once in {language}. Use a {speed} pace. '
            + (f'Delivery: {tone}. Emphasize one meaningful phrase, vary intonation naturally. ' if emotion else 'Use even, neutral delivery without theatrical emphasis. ')
            + 'Keep the same speaker identity and comfortable pitch throughout. Connect words smoothly; '
            'use short pauses at punctuation, no dramatic silence or isolated word-by-word reading. '
            'Preserve foreign proper names and pronounce them naturally in their original language within the sentence; '
            'do not spell ordinary names letter by letter. Do not translate, add, omit or repeat words. '
            'Read numbers naturally in the output language. Do not vocalize these instructions.'+timing+'\nText:\n')


def gemini_pace_tempo(pace):
    """Deterministic user control, preserving pitch and scene timing."""
    return {'slow':.95,'normal':1.,'fast':1.12}.get(pace,1.)
