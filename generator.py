"""طبقة توليد الصور: Nano Banana (Gemini) و GPT-Image (OpenAI).

كل موديل يستقبل:
  - الصورة المرجعية (تحدد الأسلوب) — اختيارية
  - الصورة المدخلة (المحتوى المراد تحويله)
  - البرومبت النصي
  - نسبة الأبعاد (aspect) والجودة (quality)
ويرجّع bytes الصورة الناتجة.
"""
import base64
import io
import logging
import mimetypes
import os
import re
import threading
import time
import requests
from PIL import Image, ImageFilter, ImageDraw, ImageOps

_log = logging.getLogger(__name__)
_RETRY_CODES = {429, 500, 502, 503, 504}  # ضغط/أخطاء مؤقتة → نعيد المحاولة

# ===== منظّم المعدّل: يحترم حد OpenAI (صور مدخلة/دقيقة) تلقائيًا =====
_RL_LIMIT = int(os.environ.get("OPENAI_IMAGES_PER_MIN", "5"))  # حد الحساب (Tier 1 = 5)
_RL_WINDOW = 60.0
_RL_LOCK = threading.Lock()
_RL_TIMES = []  # أوقات إرسال الصور المدخلة الأخيرة


def _rate_acquire(n=1):
    """ينتظر حتى يتوفّر مجال لإرسال n صورة مدخلة ضمن حد الدقيقة (يمنع 429)."""
    if _RL_LIMIT <= 0:
        return
    while True:
        with _RL_LOCK:
            now = time.time()
            cutoff = now - _RL_WINDOW
            while _RL_TIMES and _RL_TIMES[0] < cutoff:
                _RL_TIMES.pop(0)
            if len(_RL_TIMES) + n <= _RL_LIMIT or not _RL_TIMES:
                _RL_TIMES.extend([now] * n)
                return
            wait = _RL_TIMES[0] + _RL_WINDOW - now
        time.sleep(min(max(wait, 0.5), _RL_WINDOW))


def _retry_after(resp, default):
    """يستخرج وقت الانتظار الذي يطلبه OpenAI (رأس Retry-After أو "try again in 12s")."""
    ra = resp.headers.get("retry-after")
    if ra:
        try:
            return float(ra)
        except ValueError:
            pass
    m = re.search(r"try again in ([\d.]+)\s*s", resp.text or "")
    if m:
        return float(m.group(1)) + 1
    return default


def _post_with_retry(url, headers, data, files_factory, attempts=8, n_images=1):
    """POST مع تنظيم معدّل مسبق + إعادة محاولة تحترم حد OpenAI (429).

    files_factory(): دالة تُرجع قائمة الملفات جديدة في كل محاولة (لأن التيّارات تُستهلك).
    n_images: عدد الصور المدخلة في الطلب (لحساب حد الدقيقة).
    """
    _rate_acquire(n_images)  # ينتظر دوره ضمن حد الدقيقة قبل الإرسال
    resp = None
    for i in range(attempts):
        fhs = []
        try:
            files = files_factory(fhs)
            resp = requests.post(url, headers=headers, data=data, files=files, timeout=_TIMEOUT)
        finally:
            for fh in fhs:
                try: fh.close()
                except Exception: pass
        if resp.status_code in _RETRY_CODES and i < attempts - 1:
            base = min(4 * (2 ** i), 20)
            wait = _retry_after(resp, base) if resp.status_code == 429 else base
            time.sleep(min(max(wait, 1), 60))
            continue
        break
    return resp

# معرّفات الموديلات
GPT_IMAGE_MODEL = "gpt-image-2"   # أحدث موديل صور من OpenAI (مؤكّد يعمل مع حساب المستخدم)
# خرائط موديلات Gemini (الاسم الودّي → معرّف الـ API)
GEMINI_MODELS = {
    "nano_banana": "gemini-2.5-flash-image",       # Nano Banana
    "nano_banana_pro": "gemini-3-pro-image",        # Nano Banana Pro (أحدث وأقوى)
}

_TIMEOUT = 300

# نسب الأبعاد المدعومة → مقاس OpenAI الأقرب
_OPENAI_SIZE = {
    "1:1": "1024x1024",
    "3:4": "1024x1536",
    "9:16": "1024x1536",
    "4:3": "1536x1024",
    "16:9": "1536x1024",
}
_VALID_QUALITY = {"low", "medium", "high"}

NO_KEY_MSG = "لا يمكن إنشاء الصورة — أضف مفتاح API من الإعدادات."

# تحسين البرومبت (يقلّد ما يفعله ChatGPT داخليًا قبل التوليد)
ENHANCE_MODEL = "gpt-4o-mini"
_ENHANCE_SYS = (
    "You are an expert product-photography prompt engineer for an AI image editor. "
    "Rewrite the user's brief instruction into ONE vivid, detailed English prompt to "
    "edit an EXISTING product photo. Describe background, lighting, shadows, composition, "
    "mood, lens and commercial 'ChatGPT-quality' polish. CRITICAL: keep the product itself "
    "unchanged (same shape, colors, details). Output ONLY the final prompt, no preamble."
)


def enhance_prompt(user_prompt, openai_key):
    """يوسّع أمر المستخدم القصير إلى برومبت احترافي غني (مثل ChatGPT).

    يستخدم موديلًا نصّيًا من OpenAI؛ وعند أي فشل يرجع لصيغة ثابتة جيدة (لا يكسر التوليد).
    """
    up = (user_prompt or "").strip()
    if not up:
        return up
    static = (
        f"High-end professional product photography. {up}. Studio lighting, soft natural "
        "shadows, clean balanced composition, sharp focus, fine detail, commercial quality."
    )
    if not openai_key or not openai_key.startswith("sk-"):
        return static
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_key}"},
            json={
                "model": ENHANCE_MODEL,
                "messages": [
                    {"role": "system", "content": _ENHANCE_SYS},
                    {"role": "user", "content": up},
                ],
                "temperature": 0.7,
                "max_tokens": 300,
            },
            timeout=60,
        )
        if r.status_code == 200:
            txt = (r.json()["choices"][0]["message"]["content"] or "").strip()
            return txt or static
    except Exception:  # noqa: BLE001
        pass
    return static


class GenerationError(Exception):
    pass


# ---------- تحسين الجودة بالذكاء (مستويات) ----------
# مستوى التحسين → شدّة اللغة + جودة الإخراج (خانات مثل الجودات في الواجهة)
ENHANCE_LEVELS = {
    "light":  {"word": "subtly",       "quality": "medium"},
    "medium": {"word": "noticeably",   "quality": "high"},
    "strong": {"word": "dramatically", "quality": "high"},
}

ENHANCE_INSTRUCTION = (
    "Enhance this product photo to the highest professional quality: {word} increase sharpness "
    "and fine detail, upscale perceived resolution, reduce noise and compression artefacts, and "
    "improve overall clarity and lighting. CRITICAL: keep the product/subject identity, shape, "
    "colours, materials, any text or logo, and the overall composition EXACTLY the same — do not "
    "add, remove, move or restyle anything. Only improve the technical image quality."
)

# بادئة تصعيد التحسين عند رجوع نتيجة شبه مطابقة (لم يتحسّن شيء)
ENHANCE_ESCALATE = (
    "The previous result looked essentially unchanged. Apply a clearly stronger, more visible "
    "quality enhancement now, while still keeping the product identical. "
)


# ---------- مساعد البرومبت: وصف العميل العامّي → برومبت احترافي جاهز ----------
_ASSIST_MODEL = "gpt-4o-mini"
_ASSIST_SYS = (
    "You are a senior prompt engineer for a professional AI product-photography editor. "
    "The user describes — often in casual Arabic — what their CLIENT wants for a product image. "
    "Understand the intent precisely, then output ONE single, ready-to-use, richly detailed "
    "ENGLISH prompt that instructs an AI image editor to transform an EXISTING product photo "
    "accordingly. Cover, as relevant: scene and background, lighting and shadows, mood, camera "
    "and lens, colour palette, composition, and commercial 'ChatGPT-quality' polish. ALWAYS "
    "include an explicit instruction to keep the product itself unchanged (same shape, colours, "
    "details and any text/logo). Output ONLY the final prompt. No preamble, no explanation, no "
    "quotes, no markdown, no lists — just the prompt sentence(s)."
)

# بدايات ترفض (اعتذار/رفض) — نعتبرها ناتجًا غير صالح ونرجع للصيغة الاحتياطية
_ASSIST_REJECT = (
    "sorry", "i cannot", "i can't", "i'm unable", "i am unable", "as an ai",
    "i'm sorry", "unfortunately", "i won't", "i will not",
)


def _assist_fallback(brief):
    """صيغة احتياطية قوية عند غياب المفتاح أو فشل/رفض الموديل — لا تكسر أبدًا."""
    b = (brief or "").strip()
    return (
        "High-end professional product photography of the same product, unchanged. "
        f"Client request: {b}. Realise it as a clean commercial studio shot with balanced "
        "composition, soft directional lighting, natural soft shadows, accurate colours, sharp "
        "focus and fine detail. Keep the product itself exactly the same — same shape, colours, "
        "materials, details and any text or logo — change only the scene, background and styling."
    )


def _assist_valid(txt):
    """يتأكد أن ناتج الموديل برومبت حقيقي لا 'هبد': طول معقول وليس اعتذارًا/رفضًا."""
    t = (txt or "").strip()
    if len(t) < 25:
        return False
    low = t.lower()
    return not any(low.startswith(p) for p in _ASSIST_REJECT)


def assist_prompt(brief, openai_key):
    """يحوّل وصف العميل المختصر إلى برومبت إنجليزي احترافي جاهز للمراجعة.

    عند غياب المفتاح أو فشل الشبكة أو ناتج غير صالح → صيغة احتياطية قوية (لا يفشل).
    """
    b = (brief or "").strip()
    if not b:
        return b
    if not openai_key or not openai_key.startswith("sk-"):
        return _assist_fallback(b)
    try:
        r = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {openai_key}"},
            json={
                "model": _ASSIST_MODEL,
                "messages": [
                    {"role": "system", "content": _ASSIST_SYS},
                    {"role": "user", "content": b},
                ],
                "temperature": 0.7,
                "max_tokens": 400,
            },
            timeout=60,
        )
        if r.status_code == 200:
            txt = (r.json()["choices"][0]["message"]["content"] or "").strip()
            if _assist_valid(txt):
                return txt
    except Exception:  # noqa: BLE001
        pass
    return _assist_fallback(b)


# ---------- التحقق من أن التعديل نُفِّذ فعلًا (مقياس فرق بكسلي) ----------
def _as_pil(src):
    """يقبل مسارًا أو bytes أو صورة PIL ويرجّع صورة PIL بوضع RGB."""
    if isinstance(src, Image.Image):
        return src.convert("RGB")
    if isinstance(src, (bytes, bytearray)):
        return Image.open(io.BytesIO(bytes(src))).convert("RGB")
    return Image.open(src).convert("RGB")


# عتبات "هل تغيّرت الصورة فعلًا؟" (متوسط فرق رمادي 0..255 على مقاس 256)
EDIT_MIN_CHANGE = 1.5   # تعديل عام على كامل الصورة
MASK_MIN_CHANGE = 3.0   # تعديل داخل منطقة محدّدة (يجب أن يكون أوضح)


def edit_with_verify(run_fn, before, mask=None, min_change=None, plan=None):
    """يشغّل التعديل ويتحقق أنه غيّر الصورة فعلًا؛ يصعّد ويعيد المحاولة إن لم ينفّذ.

    run_fn(escalate: bool, quality: str) -> bytes الناتج.
    before: الصورة قبل التعديل (مسار/bytes/PIL) للمقارنة.
    mask:  قناع اختياري — يقيس الفرق داخل التأشير فقط (أبيض = المنطقة).
    يرجّع: {"out": bytes, "changed": bool, "attempts": int, "metric": float}.
      changed=False تعني أن الموديل لم ينفّذ التعديل رغم كل المحاولات
      (نرجّع أفضل ناتج حتى يقرّر النداء إظهار رسالة صريحة بدل ادّعاء النجاح).
    """
    if min_change is None:
        min_change = MASK_MIN_CHANGE if mask is not None else EDIT_MIN_CHANGE
    # الخطة: (تصعيد؟، الجودة) — أولًا سريع وبلا تصعيد، ثم مصعّد وأدقّ
    steps = plan or [(False, "low"), (True, "medium")]
    best_out, best_metric = None, -1.0
    for i, (escalate, quality) in enumerate(steps):
        out = run_fn(escalate, quality)
        metric = change_metric(before, out, mask=mask)
        if metric > best_metric:
            best_out, best_metric = out, metric
        if metric >= min_change:
            return {"out": out, "changed": True, "attempts": i + 1, "metric": metric}
    return {"out": best_out, "changed": False, "attempts": len(steps), "metric": best_metric}


def change_metric(before, after, mask=None, _size=256):
    """متوسط الفرق البكسلي (0..255) بين صورتين — اختياريًا داخل قناع فقط.

    before/after/mask: مسار أو bytes أو صورة PIL. يُعاد تحجيم الكل لمقاس موحّد
    قبل المقارنة (فلا يتأثر باختلاف الأبعاد). القناع: أبيض = المنطقة المعنيّة.
    القيمة الأعلى = تغيّر أكبر؛ القريبة من الصفر = الموديل لم يعدّل شيئًا.
    """
    a = _as_pil(before).resize((_size, _size), Image.LANCZOS).convert("L")
    b = _as_pil(after).resize((_size, _size), Image.LANCZOS).convert("L")
    aa = np.asarray(a, dtype=np.float32)
    bb = np.asarray(b, dtype=np.float32)
    diff = np.abs(aa - bb)
    if mask is not None:
        m = _as_pil(mask).resize((_size, _size), Image.LANCZOS).convert("L")
        mm = np.asarray(m, dtype=np.float32) / 255.0
        total = float(mm.sum())
        if total < 1.0:  # قناع فارغ عمليًا → قِس الصورة كاملة
            return float(diff.mean())
        return float((diff * mm).sum() / total)
    return float(diff.mean())


def _guess_mime(path):
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


def _validate_key(model, key):
    """يمنع تبادل المفاتيح: مفتاح OpenAI (sk-) لـ GPT-Image فقط، وGoogle (AIza) لـ Gemini."""
    k = (key or "").strip()
    if model == "gpt_image" and k.startswith("AIza"):
        raise GenerationError(
            "وضعت مفتاح Google (Gemini) في خانة GPT-Image. "
            "GPT-Image يحتاج مفتاح OpenAI يبدأ بـ sk-."
        )
    if model in GEMINI_MODELS and k.startswith("sk-"):
        raise GenerationError(
            "وضعت مفتاح OpenAI في خانة Nano Banana. "
            "Nano Banana يحتاج مفتاح Google يبدأ بـ AIza."
        )


def _as_ref_list(reference_paths):
    """يقبل None أو مسارًا واحدًا أو قائمة، ويرجّع قائمة مسارات."""
    if not reference_paths:
        return []
    if isinstance(reference_paths, (list, tuple)):
        return list(reference_paths)
    return [reference_paths]


def generate(model, api_key, prompt, input_path, reference_paths=None, aspect=None, quality=None):
    """يوزّع على الموديل المطلوب ويرجّع bytes للصورة الناتجة.

    reference_paths: صورة مرجعية واحدة أو قائمة عدة مراجع (أسلوب متعدد الأمثلة).
    """
    if not api_key:
        raise GenerationError(NO_KEY_MSG)
    _validate_key(model, api_key)
    refs = _as_ref_list(reference_paths)
    if model in GEMINI_MODELS:
        return _generate_gemini(api_key, prompt, input_path, refs, aspect, GEMINI_MODELS[model])
    if model == "gpt_image":
        return _generate_openai(api_key, prompt, input_path, refs, aspect, quality)
    raise GenerationError(f"موديل غير معروف: {model}")


def generate_region(model, api_key, prompt, input_path, reference_path,
                    mask_path, base_path, aspect=None, quality=None):
    """تعديل منطقة محددة فقط: يولّد صورة مرشّحة ثم يدمجها داخل القناع فوق الصورة الأساسية."""
    base = Image.open(base_path).convert("RGB")
    mask = Image.open(mask_path).convert("L").resize(base.size)
    cand_bytes = generate(model, api_key, prompt, input_path, reference_path,
                          aspect=aspect, quality=quality)
    candidate = Image.open(io.BytesIO(cand_bytes)).convert("RGB").resize(base.size)
    out = Image.composite(candidate, base, mask)
    return _to_png_bytes(out)


def _to_png_bytes(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


def generate_masked_openai(api_key, prompt, image_path, frontend_mask_path, quality=None):
    """تحرير المنطقة المحددة فقط عبر قناع OpenAI الأصلي (inpainting طبيعي).

    الذكاء يعدّل داخل المنطقة ويدمجها مع باقي الصورة تلقائيًا.
    نوسّع القناع وننعّمه قليلًا حتى يفهم المنطقة لا يأخذها بالملي.
    """
    if not api_key:
        raise GenerationError(NO_KEY_MSG)
    img = Image.open(image_path).convert("RGBA")
    fm = Image.open(frontend_mask_path).convert("L").resize(img.size)  # أبيض = محدد
    fm = fm.filter(ImageFilter.MaxFilter(9))       # توسيع المنطقة
    fm = fm.filter(ImageFilter.GaussianBlur(6))    # تنعيم الحواف (لا تحديد حاد)
    # قناع OpenAI: شفاف حيث التحديد (يُحرَّر)، معتم في الباقي (يُحفَظ)
    alpha = ImageOps.invert(fm)
    mask_img = Image.new("RGBA", img.size, (0, 0, 0, 255))
    mask_img.putalpha(alpha)

    img_bytes = io.BytesIO(); img.save(img_bytes, "PNG"); img_bytes = img_bytes.getvalue()
    mask_bytes = io.BytesIO(); mask_img.save(mask_bytes, "PNG"); mask_bytes = mask_bytes.getvalue()

    data = {"model": GPT_IMAGE_MODEL, "prompt": prompt}
    if quality in _VALID_QUALITY:
        data["quality"] = quality

    def _files(_fhs):
        return [("image", ("image.png", io.BytesIO(img_bytes), "image/png")),
                ("mask", ("mask.png", io.BytesIO(mask_bytes), "image/png"))]

    resp = _post_with_retry(
        "https://api.openai.com/v1/images/edits",
        {"Authorization": f"Bearer {api_key}"}, data, _files, n_images=1,
    )
    if resp.status_code != 200:
        raise GenerationError(f"OpenAI خطأ {resp.status_code}: {resp.text[:300]}")
    try:
        return base64.b64decode(resp.json()["data"][0]["b64_json"])
    except (KeyError, IndexError):
        raise GenerationError("OpenAI لم يُرجع صورة. الرد: " + resp.text[:300])


# ---------- قفل المنتج (ضمان عدم تغيّر شكل المنتج في الكود) ----------
def lock_subject(original_path, generated_bytes):
    """يعزل المنتج من الصورة الأصلية ويلصقه فوق ناتج الذكاء.

    النتيجة: بكسل المنتج = الأصل تمامًا (شكل مضمون)، والخلفية/الأسلوب من الذكاء.
    عند فشل العزل نرفع خطأً واضحًا (لا نمرّر منتجًا متغيّرًا بصمت أبدًا).
    """
    try:
        orig = Image.open(original_path).convert("RGB")
        gen = Image.open(io.BytesIO(generated_bytes)).convert("RGB")
        if gen.size != orig.size:
            gen = gen.resize(orig.size)
        alpha = _foreground_alpha(original_path).resize(orig.size)
        # قناع أكثر شمولًا لضمان تغطية كامل المنتج (نرفع القيم المتوسطة ونوسّع قليلًا)
        alpha = alpha.point(lambda v: 255 if v > 30 else int(min(255, v * 5)))
        alpha = alpha.filter(ImageFilter.MaxFilter(5))       # توسيع (dilate) ~2px
        alpha = alpha.filter(ImageFilter.GaussianBlur(1.2))  # تنعيم الحواف
        out = Image.composite(orig, gen, alpha)  # المنتج من الأصل، الباقي من الذكاء
        return _to_png_bytes(out)
    except Exception as e:  # noqa: BLE001
        _log.warning("lock_subject فشل العزل: %s", e)
        raise GenerationError(f"تعذّر قفل شكل المنتج (عزل الخلفية): {e}") from e


def seg_selftest():
    """فحص أن عزل المنتج يعمل فعليًا (يُستخدم في /api/health)."""
    img = Image.new("RGB", (96, 96), (240, 240, 240))
    ImageDraw.Draw(img).ellipse([24, 24, 72, 72], fill=(200, 40, 40))
    mask = _alpha_from_pil(img)
    arr = list(mask.getdata())
    return max(arr) - min(arr) > 40  # القناع فيه تباين (عزل ناجح)


# ---------- عزل المنتج عبر onnxruntime (نموذج U2Net-p الخفيف 4.6MB) ----------
import numpy as np  # noqa: E402
from pathlib import Path as _Path  # noqa: E402

_MODEL_PATH = _Path(__file__).parent / "models" / "u2netp.onnx"
_ORT_SESSION = None
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def _get_session():
    global _ORT_SESSION
    if _ORT_SESSION is None:
        import onnxruntime as ort  # استيراد كسول
        _ORT_SESSION = ort.InferenceSession(
            str(_MODEL_PATH), providers=["CPUExecutionProvider"]
        )
    return _ORT_SESSION


def _alpha_from_pil(img):
    """يُرجع قناع المنتج (L) بنفس أبعاد الصورة عبر U2Net-p."""
    orig_size = img.size
    small = img.convert("RGB").resize((320, 320), Image.LANCZOS)
    arr = (np.array(small).astype(np.float32) / 255.0 - _MEAN) / _STD
    arr = arr.transpose(2, 0, 1)[None, ...].astype(np.float32)
    sess = _get_session()
    pred = sess.run(None, {sess.get_inputs()[0].name: arr})[0][0, 0, :, :]
    mi, ma = float(pred.min()), float(pred.max())
    pred = (pred - mi) / (ma - mi + 1e-8)
    mask = Image.fromarray((pred * 255).astype(np.uint8))
    return mask.resize(orig_size, Image.LANCZOS)


def _foreground_alpha(path):
    return _alpha_from_pil(Image.open(path).convert("RGB"))


# ---------- Nano Banana (Gemini) ----------
def _generate_gemini(api_key, prompt, input_path, references=None, aspect=None,
                     model_id="gemini-2.5-flash-image"):
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:generateContent"
    )
    parts = [{"text": prompt}]
    # الصورة المدخلة (المنتج) أولاً، ثم المراجع (الأسلوب) — قد تكون عدة
    parts.append(_gemini_inline(input_path))
    for rp in _as_ref_list(references):
        parts.append(_gemini_inline(rp))

    body = {"contents": [{"parts": parts}]}
    if aspect:
        body["generationConfig"] = {"imageConfig": {"aspectRatio": aspect}}

    resp = requests.post(url, params={"key": api_key}, json=body, timeout=_TIMEOUT)

    # بعض إصدارات الـ API قد لا تقبل imageConfig — نعيد المحاولة بدونها بدل الفشل
    if resp.status_code == 400 and aspect:
        body.pop("generationConfig", None)
        resp = requests.post(url, params={"key": api_key}, json=body, timeout=_TIMEOUT)

    if resp.status_code != 200:
        raise GenerationError(f"Gemini خطأ {resp.status_code}: {resp.text[:300]}")

    data = resp.json()
    try:
        for part in data["candidates"][0]["content"]["parts"]:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                return base64.b64decode(inline["data"])
    except (KeyError, IndexError):
        pass
    raise GenerationError("Gemini لم يُرجع صورة. الرد: " + resp.text[:300])


def _gemini_inline(path):
    with open(path, "rb") as f:
        raw = f.read()
    return {
        "inlineData": {
            "mimeType": _guess_mime(path),
            "data": base64.b64encode(raw).decode(),
        }
    }


# ---------- GPT-Image (OpenAI) ----------
def _generate_openai(api_key, prompt, input_path, references=None, aspect=None, quality=None):
    url = "https://api.openai.com/v1/images/edits"
    # الصورة المدخلة (المنتج) أولاً = الأساس، ثم المراجع (الأسلوب) — قد تكون عدة
    paths = [input_path] + _as_ref_list(references)
    data = {"model": GPT_IMAGE_MODEL, "prompt": prompt}
    if aspect in _OPENAI_SIZE:
        data["size"] = _OPENAI_SIZE[aspect]
    if quality in _VALID_QUALITY:
        data["quality"] = quality

    def _files(fhs):
        out = []
        for p in paths:
            fh = open(p, "rb"); fhs.append(fh)
            out.append(("image[]", (str(p).replace("\\", "/").split("/")[-1], fh, _guess_mime(p))))
        return out

    resp = _post_with_retry(url, {"Authorization": f"Bearer {api_key}"}, data, _files,
                            n_images=len(paths))

    if resp.status_code != 200:
        raise GenerationError(f"OpenAI خطأ {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    try:
        b64 = payload["data"][0]["b64_json"]
        return base64.b64decode(b64)
    except (KeyError, IndexError):
        raise GenerationError("OpenAI لم يُرجع صورة. الرد: " + resp.text[:300])
