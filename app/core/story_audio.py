"""Re-write/re-synthesize overflowing narration instead of borrowing unrelated footage."""
import asyncio
import math

class NarrationTimingError(RuntimeError):
    """Requires an edit, not another identical automatic export attempt."""

def timing_error(duration,window):
    return NarrationTimingError(f'story_narration_too_long: Lời đã duyệt dài {duration:.1f}s nhưng cảnh chỉ {window:.1f}s. '
        'Mở Duyệt kịch bản, rút gọn đúng câu này rồi Lưu & duyệt và xuất lại. '
        'Không cần phân tích lại video; không cắt cụt câu hoặc tự đổi lời đã duyệt.')


def fit_narration_text(text,evidence,window,path,voice,lang,rate,pitch,on_progress=lambda _:None,allow_rewrite=True,delivery_prefix=None):
    from app.core import dubbing as d
    from app.ai.story_quality import shorten
    from app.queue.worker import current_job_canceled,CanceledError
    def check():
        if current_job_canceled():raise CanceledError()
    if not math.isfinite(window) or window<=0:raise ValueError('Cảnh không có thời lượng hợp lệ.')
    words=[]
    retaken=False
    for attempt in range(3):
        check();duration=d.probe_duration(path)
        if duration<=0:raise RuntimeError('Giọng đọc rỗng/hỏng; chưa xuất video.')
        if duration/1.15<=window+.02:return text,words
        if voice.startswith('gemini:') and not retaken:
            # Same approved words and same voice; the initial expressive take
            # may be much slower than the available shot. A distinct prompt also
            # avoids retrieving the identical overlong take from the TTS cache.
            retaken=True
            on_progress('Giọng Gemini đọc quá dài — thu lại nguyên lời, đúng thời lượng cảnh…')
            import tempfile
            import shutil
            from pathlib import Path
            with tempfile.TemporaryDirectory(prefix='story_retake_') as temp:
                candidate=str(Path(temp)/'retake.wav')
                prefix=((delivery_prefix or d.gemini_narrate_prefix(lang))+
                    f'\nRead the exact following text ONCE, in about {window*.94:.2f} seconds. '
                    'Use a natural, fluent conversational pace, short breathing pauses, no long dramatic pauses. '
                    'Do not repeat, omit, add, translate or change any words. Do not read these instructions. Text:\n')
                ok=d._synth_all_gemini([text],voice,[candidate],d.norm_lang(lang),edge_rate=rate,
                    gemini_prefix=prefix,allow_fallback=False)
                check()
                shorter=d.probe_duration(candidate) if ok and ok[0] else 0
                if 0<shorter<duration:
                    shutil.copyfile(candidate,path);duration=shorter
                if duration/1.15<=window+.02:return text,words
        if not allow_rewrite:
            raise timing_error(duration,window)
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
    raise timing_error(d.probe_duration(path),window)
