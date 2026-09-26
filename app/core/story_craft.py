"""Bounded editorial controls; no network, rewriting or voice substitution."""
import re

DELIVERY={'neutral':'Tự nhiên','curious':'Gợi tò mò','brisk':'Dứt khoát','measured':'Rõ, chậm vừa','reflective':'Trầm, kết câu'}
ENERGY={'auto':'Theo vai trò cảnh','hush':'Hạ sâu / nhường tiếng gốc','low':'Nhẹ','mid':'Vừa','lift':'Nâng cao trào'}

def word_budget(seconds,lang):
    # Vietnamese whitespace separates syllables, not English-like words.
    vi=str(lang).casefold() in ('vi','vietnamese','vi-vn')
    return max(3,int(max(0,float(seconds))*(3.2 if vi else 1.9)))

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
            'not in spoken text. Retain proper names only when clearly supported.' if str(lang).casefold() in ('vi','vietnamese','vi-vn') else '')
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
            'without inventing an outcome outside the footage.'+native)
