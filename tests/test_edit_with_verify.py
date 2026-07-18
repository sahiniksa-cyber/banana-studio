"""اختبار منطق 'التأكد أن التعديل نُفِّذ': يتحقق ويعيد المحاولة مصعّدًا عند الحاجة."""
import io
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generator  # noqa: E402


def _png(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def _solid(color, size=(200, 260)):
    return Image.new("RGB", size, color)


BEFORE = _png(_solid((180, 180, 180)))
CHANGED = _png(_solid((30, 30, 30)))          # مختلفة تمامًا
SAME = _png(_solid((180, 180, 180)))          # نفس الأصل (الموديل ما عدّل)


def test_success_on_first_attempt_no_escalation():
    calls = []

    def run_fn(escalate, quality):
        calls.append((escalate, quality))
        return CHANGED

    res = generator.edit_with_verify(run_fn, BEFORE)
    assert res["changed"] is True
    assert res["attempts"] == 1
    assert res["out"] == CHANGED
    assert calls == [(False, "low")]  # محاولة واحدة، بدون تصعيد


def test_retries_with_escalation_when_first_did_nothing():
    outputs = [SAME, CHANGED]
    calls = []

    def run_fn(escalate, quality):
        calls.append((escalate, quality))
        return outputs[len(calls) - 1]

    res = generator.edit_with_verify(run_fn, BEFORE)
    assert res["changed"] is True
    assert res["attempts"] == 2
    assert calls[0][0] is False          # الأولى بدون تصعيد
    assert calls[1][0] is True           # الثانية مصعّدة
    assert res["out"] == CHANGED


def test_reports_not_changed_when_model_never_edits():
    def run_fn(escalate, quality):
        return SAME  # يستهبل دائمًا

    res = generator.edit_with_verify(run_fn, BEFORE)
    assert res["changed"] is False       # صدق: لم يُنفَّذ التعديل
    assert res["attempts"] == 2
    assert res["out"] is not None        # نرجّع أفضل ناتج للمعالجة/الرسالة


def test_mask_change_outside_region_counts_as_not_changed():
    # الناتج يغيّر خارج التأشير فقط → يجب أن يُعتبر لم يُنفَّذ داخل التأشير
    after = _solid((180, 180, 180))
    ImageDraw.Draw(after).rectangle([120, 160, 199, 259], fill=(0, 0, 0))
    after_png = _png(after)

    mask = Image.new("L", (200, 260), 0)
    ImageDraw.Draw(mask).rectangle([0, 0, 80, 80], fill=255)  # التأشير أعلى-يسار
    mask_png = _png(mask)

    def run_fn(escalate, quality):
        return after_png

    res = generator.edit_with_verify(run_fn, BEFORE, mask=mask_png)
    assert res["changed"] is False
