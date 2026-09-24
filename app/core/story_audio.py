"""Re-write/re-synthesize overflowing narration instead of borrowing unrelated footage."""
import asyncio


def fit_narration_text(text,evidence,window,path,voice,lang,rate,pitch,on_progress=lambda _:None,allow_rewrite=True):
    from app.core import dubbing as d
    from app.ai.story_quality import shorten
    from app.queue.worker import current_job_canceled,CanceledError
    def check():
        if current_job_canceled():raise CanceledError()
    words=[]
    for attempt in range(3):
        check();duration=d.probe_duration(path)
        if duration<=0:raise RuntimeError('Giọng đọc rỗng/hỏng; chưa xuất video.')
        if duration/1.15<=window+.02:return text,words
        if not allow_rewrite:
            raise RuntimeError(f'Lời đã duyệt dài {duration:.1f}s nhưng cảnh chỉ {window:.1f}s. Mở Duyệt kịch bản, viết ngắn câu này rồi duyệt và xuất lại. Không cắt cụt hoặc tự đổi lời đã duyệt.')
        if attempt==2:break
        on_progress('Lời dài hơn cảnh — viết gọn, đối chiếu và thu lại…')
        target=max(.5,window*.85*window/duration)
        text=shorten(text,evidence,target,check)
        if voice.startswith('gemini:'):
            ok=d._synth_all_gemini([text],voice,[path],d.norm_lang(lang),edge_rate=rate,
                                 gemini_prefix=d.gemini_narrate_prefix(lang),allow_fallback=False)
            words=[]
        else:
            ok,word_lists=asyncio.run(d._synth_all_words([text],voice,[path],rate=rate,pitch=pitch,lang=lang,el_lui=False))
            words=word_lists[0] if word_lists else []
        if not ok or not ok[0]:raise RuntimeError('Không thu lại được câu đã rút gọn; thử lại hoặc kiểm tra giọng.')
    raise RuntimeError('Lời kể vẫn dài hơn cảnh sau 2 lượt sửa; chưa xuất, không cắt cụt lời.')
