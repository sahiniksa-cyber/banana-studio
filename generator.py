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
import requests
from PIL import Image, ImageFilter, ImageDraw

_log = logging.getLogger(__name__)

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


def generate(model, api_key, prompt, input_path, reference_path=None, aspect=None, quality=None):
    """يوزّع على الموديل المطلوب ويرجّع bytes للصورة الناتجة."""
    if not api_key:
        raise GenerationError(NO_KEY_MSG)
    _validate_key(model, api_key)
    if model in GEMINI_MODELS:
        return _generate_gemini(api_key, prompt, input_path, reference_path, aspect,
                                GEMINI_MODELS[model])
    if model == "gpt_image":
        return _generate_openai(api_key, prompt, input_path, reference_path, aspect, quality)
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
def _generate_gemini(api_key, prompt, input_path, reference_path, aspect=None,
                     model_id="gemini-2.5-flash-image"):
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model_id}:generateContent"
    )
    parts = [{"text": prompt}]
    # الصورة المدخلة (المنتج) أولاً = الأساس المطلوب الحفاظ عليه،
    # ثم الصورة المرجعية (الأسلوب) ثانيًا كمرجع فقط.
    parts.append(_gemini_inline(input_path))
    if reference_path:
        parts.append(_gemini_inline(reference_path))

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
def _generate_openai(api_key, prompt, input_path, reference_path, aspect=None, quality=None):
    url = "https://api.openai.com/v1/images/edits"
    files = []
    fhs = []
    try:
        # الصورة المدخلة (المنتج) أولاً = الأساس، ثم المرجع (الأسلوب) ثانيًا
        for p in [input_path] + ([reference_path] if reference_path else []):
            fh = open(p, "rb")
            fhs.append(fh)
            files.append(("image[]", (str(p).replace("\\", "/").split("/")[-1], fh, _guess_mime(p))))
        data = {"model": GPT_IMAGE_MODEL, "prompt": prompt}
        if aspect in _OPENAI_SIZE:
            data["size"] = _OPENAI_SIZE[aspect]
        if quality in _VALID_QUALITY:
            data["quality"] = quality
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            data=data,
            files=files,
            timeout=_TIMEOUT,
        )
    finally:
        for fh in fhs:
            fh.close()

    if resp.status_code != 200:
        raise GenerationError(f"OpenAI خطأ {resp.status_code}: {resp.text[:300]}")

    payload = resp.json()
    try:
        b64 = payload["data"][0]["b64_json"]
        return base64.b64decode(b64)
    except (KeyError, IndexError):
        raise GenerationError("OpenAI لم يُرجع صورة. الرد: " + resp.text[:300])
