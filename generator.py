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
import mimetypes
import requests
from PIL import Image, ImageOps, ImageEnhance

# معرّفات الموديلات
NANO_BANANA_MODEL = "gemini-2.5-flash-image"
GPT_IMAGE_MODEL = "gpt-image-1"

_TIMEOUT = 300

# نسب الأبعاد المدعومة → مقاس OpenAI الأقرب
_OPENAI_SIZE = {
    "1:1": "1024x1024",
    "3:4": "1024x1536",
    "9:16": "1024x1536",
    "4:3": "1536x1024",
    "16:9": "1536x1024",
}
# نسب الأبعاد → أبعاد بكسل لوضع التجربة
_ASPECT_PX = {
    "1:1": (1024, 1024),
    "3:4": (900, 1200),
    "9:16": (720, 1280),
    "4:3": (1200, 900),
    "16:9": (1280, 720),
}
_VALID_QUALITY = {"low", "medium", "high"}


class GenerationError(Exception):
    pass


def _guess_mime(path):
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


def generate(model, api_key, prompt, input_path, reference_path=None, demo=False,
             aspect=None, quality=None):
    """يوزّع على الموديل المطلوب ويرجّع bytes للصورة الناتجة.

    demo=True: يولّد نتيجة معالَجة محليًا بدون API (لتجربة المنصة بدون توكن).
    aspect: 1:1 / 3:4 / 4:3 / 9:16 / 16:9
    quality: low / medium / high (خاص بـ GPT-Image)
    """
    if demo:
        return _to_png_bytes(_mock_transform(input_path, aspect=aspect))
    if not api_key:
        raise GenerationError("مفتاح API غير مضبوط. أضِفه من الإعدادات، أو فعّل وضع التجربة.")
    if model == "nano_banana":
        return _generate_gemini(api_key, prompt, input_path, reference_path, aspect)
    if model == "gpt_image":
        return _generate_openai(api_key, prompt, input_path, reference_path, aspect, quality)
    raise GenerationError(f"موديل غير معروف: {model}")


def generate_region(model, api_key, prompt, input_path, reference_path,
                    mask_path, base_path, demo=False, aspect=None, quality=None):
    """تعديل منطقة محددة فقط: يولّد صورة مرشّحة ثم يدمجها داخل القناع فوق الصورة الأساسية.

    يعطي سلوك "أعِد رسم هذا الجزء فقط" لكل الموديلات وفي وضع التجربة.
    """
    base = Image.open(base_path).convert("RGB")
    mask = Image.open(mask_path).convert("L").resize(base.size)
    if demo:
        candidate = _mock_transform(base_path, strong=True).resize(base.size)
    else:
        cand_bytes = generate(model, api_key, prompt, input_path, reference_path,
                              demo=False, aspect=aspect, quality=quality)
        candidate = Image.open(io.BytesIO(cand_bytes)).convert("RGB").resize(base.size)
    out = Image.composite(candidate, base, mask)
    return _to_png_bytes(out)


# ---------- وضع التجربة (بدون API) ----------
def _mock_transform(input_path, strong=False, aspect=None):
    """يحوّل الصورة محليًا لإشارة بصرية واضحة أنها "مولّدة" (لأغراض التجربة)."""
    im = Image.open(input_path).convert("RGB")
    gray = ImageOps.grayscale(im)
    if strong:
        tint = ImageOps.colorize(gray, black=(10, 40, 70), white=(255, 200, 90))
        tint = ImageEnhance.Contrast(tint).enhance(1.25)
    else:
        tint = ImageOps.colorize(gray, black=(25, 25, 60), white=(255, 220, 120))
    # احترام نسبة الأبعاد المطلوبة (قص للتعبئة)
    if aspect in _ASPECT_PX:
        tint = ImageOps.fit(tint, _ASPECT_PX[aspect], Image.LANCZOS)
    return tint


def _to_png_bytes(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


# ---------- Nano Banana (Gemini) ----------
def _generate_gemini(api_key, prompt, input_path, reference_path, aspect=None):
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{NANO_BANANA_MODEL}:generateContent"
    )
    parts = [{"text": prompt}]
    # الصورة المرجعية أولاً (الأسلوب) ثم الصورة المدخلة (المحتوى)
    if reference_path:
        parts.append(_gemini_inline(reference_path))
    parts.append(_gemini_inline(input_path))

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
        # gpt-image-1 يقبل عدة صور مدخلة عبر image[]
        for p in ([reference_path] if reference_path else []) + [input_path]:
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
