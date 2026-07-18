"""اختبار مقياس الفرق: يتأكد أن التعديل نُفِّذ فعلًا (لم يُرجع الموديل نفس الصورة)."""
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


def test_identical_images_metric_near_zero():
    a = _solid((180, 180, 180))
    metric = generator.change_metric(_png(a), _png(a.copy()))
    assert metric < 1.0


def test_clearly_different_images_metric_large():
    a = _solid((20, 20, 20))
    b = _solid((230, 230, 230))
    metric = generator.change_metric(_png(a), _png(b))
    assert metric > 50.0


def test_change_only_inside_mask_is_detected_within_region():
    # الأصل رمادي؛ الناتج فيه مربّع أسود أعلى-يسار فقط
    base = _solid((180, 180, 180))
    after = base.copy()
    ImageDraw.Draw(after).rectangle([0, 0, 90, 90], fill=(0, 0, 0))

    # قناع أبيض على نفس المنطقة (أبيض = المنطقة المعنيّة)
    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rectangle([0, 0, 90, 90], fill=255)

    inside = generator.change_metric(_png(base), _png(after), mask=_png(mask))
    assert inside > 40.0  # تغيّر واضح داخل التأشير


def test_no_change_inside_mask_when_edit_landed_elsewhere():
    # التغيّر حصل خارج التأشير → القياس داخل التأشير يجب أن يكون شبه صفر
    base = _solid((180, 180, 180))
    after = base.copy()
    ImageDraw.Draw(after).rectangle([100, 150, 199, 259], fill=(0, 0, 0))

    mask = Image.new("L", base.size, 0)
    ImageDraw.Draw(mask).rectangle([0, 0, 90, 90], fill=255)  # التأشير أعلى-يسار

    inside = generator.change_metric(_png(base), _png(after), mask=_png(mask))
    assert inside < 3.0  # ما تغيّر شيء داخل التأشير


def test_handles_different_sizes():
    a = _solid((100, 100, 100), size=(200, 260))
    b = _solid((100, 100, 100), size=(400, 520))  # نفس اللون بحجم مختلف
    metric = generator.change_metric(_png(a), _png(b))
    assert metric < 1.0  # يُعاد التحجيم قبل المقارنة → لا فرق
