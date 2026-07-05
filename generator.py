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
from PIL import Image

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
_VALID_QUALITY = {"low", "medium", "high"}

NO_KEY_MSG = "لا يمكن إنشاء الصورة — أضف مفتاح API من الإعدادات."


class GenerationError(Exception):
    pass


def _guess_mime(path):
    mime, _ = mimetypes.guess_type(str(path))
    return mime or "image/png"


def generate(model, api_key, prompt, input_path, reference_path=None, aspect=None, quality=None):
    """يوزّع على الموديل المطلوب ويرجّع bytes للصورة الناتجة."""
    if not api_key:
        raise GenerationError(NO_KEY_MSG)
    if model == "nano_banana":
        return _generate_gemini(api_key, prompt, input_path, reference_path, aspect)
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
