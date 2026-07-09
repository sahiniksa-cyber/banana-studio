"""منصّة توليد الصور بقالب موحّد — الخادم الرئيسي (Flask)."""
import os
import threading
import time
import uuid
import zipfile
import io
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_file,
    abort,
)
from werkzeug.utils import secure_filename
from PIL import Image

# دعم صور آيفون HEIC/HEIF (اختياري — إن توفّرت المكتبة)
try:
    import pillow_heif
    pillow_heif.register_heif_opener()
except Exception:  # noqa: BLE001
    pass

import store
import generator

BASE_DIR = Path(__file__).parent
# مجلد البيانات: يفضّل قرص Railway الدائم تلقائيًا، ثم DATA_DIR، ثم مجلد محلي.
# يُحوّل دائمًا لمسار مطلق حتى لا يتأثر بمجلد التشغيل الحالي.
_vol = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", "").strip()
_data_env = os.environ.get("DATA_DIR", "").strip()
DATA_DIR = Path(_vol or _data_env or (BASE_DIR / "data")).resolve()
UPLOAD_DIR = DATA_DIR / "uploads"       # الصور المدخلة + المراجع المرفوعة
RESULT_DIR = DATA_DIR / "results"       # الصور الناتجة + مراجع التصميم المعتمدة
DB_FILE = DATA_DIR / "studio.db"

for d in (DATA_DIR, UPLOAD_DIR, RESULT_DIR):
    d.mkdir(parents=True, exist_ok=True)

store.init_db(DB_FILE)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024  # 200MB للدفعة

ALLOWED = {"png", "jpg", "jpeg", "webp", "heic", "heif", "bmp", "tiff", "tif", "gif", "avif"}


@app.errorhandler(ValueError)
def _handle_value_error(e):
    return jsonify({"error": str(e)}), 400

# توضيح أدوار الصور للموديل: الصورة الأولى = المنتج المطلوب الحفاظ عليه،
# الصورة الثانية (إن وُجدت) = مرجع للأسلوب فقط.
_KEEP_CLAUSE = (
    "الصورة الأولى هي المنتج المطلوب — أبقِ هذا المنتج كما هو تمامًا: نفس الشكل "
    "والهوية والتفاصيل والنِّسب، ولا تستبدله بأي منتج آخر."
)
_REF_CLAUSE = (
    " الصورة الثانية مرجع للأسلوب فقط (الخلفية، الإضاءة، الألوان، الطابع) — "
    "استرشد بأسلوبها فقط ولا تنسخ المنتج أو العناصر منها."
)

# الوضع "ب" (ثبات تام، بدون برومبت): يطابق أسلوب المرجع مع الحفاظ على منتج المستخدم.
STRICT_INSTRUCTION = (
    _KEEP_CLAUSE
    + " طابِق خلفية وإضاءة وألوان وطابع الصورة الثانية (المرجع) على منتج الصورة "
    "الأولى، دون تغيير المنتج نفسه ودون نسخ منتج المرجع."
)


def build_prompt(user_prompt, has_reference, strict):
    """يبني التعليمة النهائية للموديل مع توضيح أدوار الصور."""
    if strict:
        return STRICT_INSTRUCTION
    base = user_prompt or "طبّق أسلوبًا احترافيًا نظيفًا."
    if has_reference:
        return f"{_KEEP_CLAUSE} طبّق التالي على منتج الصورة الأولى: {base}.{_REF_CLAUSE}"
    # بدون مرجع (خطوة التصميم): صورة واحدة فقط
    return (
        "أبقِ المنتج/الموضوع الأساسي في الصورة كما هو تمامًا (شكله وهويته وتفاصيله)، "
        f"وطبّق عليه التالي فقط: {base}."
    )


def _allowed(fn):
    return "." in fn and fn.rsplit(".", 1)[1].lower() in ALLOWED


def _save_upload(file_storage):
    """يحفظ أي صورة (HEIC/WEBP/JPG/…) بعد تحويلها إلى PNG موحّد."""
    name = f"{uuid.uuid4().hex}.png"
    try:
        img = Image.open(file_storage.stream)
        img = img.convert("RGBA") if img.mode in ("RGBA", "LA") else img.convert("RGB")
        img.save(UPLOAD_DIR / name, "PNG")
    except Exception as e:  # noqa: BLE001
        raise ValueError("تعذّر قراءة الصورة. جرّب صيغة PNG أو JPG أو HEIC.") from e
    return name


def _ref_path(name):
    """مسار المرجع: قد يكون صورة مرفوعة (uploads) أو تصميمًا معتمدًا (results)."""
    if not name:
        return None
    up = UPLOAD_DIR / name
    if up.exists():
        return up
    res = RESULT_DIR / name
    if res.exists():
        return res
    return up  # احتياطي


# ============ الصفحة الرئيسية ============
@app.route("/")
def index():
    return render_template("index.html")


# ============ الإعدادات (مفاتيح API) ============
@app.route("/api/health")
def health():
    info = {
        "ok": True,
        "gpt_image_key_set": bool(store.get_setting("gpt_image_key")),
        "nano_banana_key_set": bool(store.get_setting("nano_banana_key")),
        "data_dir": str(DATA_DIR),
    }
    if request.args.get("seg") == "1":
        try:
            info["seg_ok"] = bool(generator.seg_selftest())
        except Exception as e:  # noqa: BLE001
            info["seg_ok"] = False
            info["seg_error"] = str(e)[:250]
    return jsonify(info)


@app.route("/api/settings", methods=["GET"])
def get_settings():
    gpt_env = bool(_env_key("gpt_image"))
    nano_env = bool(_env_key("nano_banana"))
    return jsonify(
        {
            "gpt_image_key_set": gpt_env or bool(store.get_setting("gpt_image_key")),
            "nano_banana_key_set": nano_env or bool(store.get_setting("nano_banana_key")),
            "gpt_image_key_env": gpt_env,     # مُدار من Railway
            "nano_banana_key_env": nano_env,  # مُدار من Railway
        }
    )


@app.route("/api/settings", methods=["POST"])
def save_settings():
    data = request.get_json(force=True)
    if data.get("nano_banana_key"):
        store.set_setting("nano_banana_key", data["nano_banana_key"].strip())
    if data.get("gpt_image_key"):
        store.set_setting("gpt_image_key", data["gpt_image_key"].strip())
    return jsonify({"ok": True})


# ============ القوالب ============
@app.route("/api/templates", methods=["GET"])
def api_list_templates():
    return jsonify(store.list_templates())


@app.route("/api/templates", methods=["POST"])
def api_create_template():
    name = request.form.get("name", "").strip()
    prompt = request.form.get("prompt", "").strip()
    if not name or not prompt:
        return jsonify({"error": "الاسم والبرومبت مطلوبان"}), 400
    reference = None
    if "reference" in request.files and request.files["reference"].filename:
        f = request.files["reference"]
        if not _allowed(f.filename):
            return jsonify({"error": "صيغة صورة غير مدعومة"}), 400
        reference = _save_upload(f)
    tid = store.create_template(name, reference, prompt)
    return jsonify(store.get_template(tid))


@app.route("/api/templates/<int:tid>", methods=["DELETE"])
def api_delete_template(tid):
    store.delete_template(tid)
    return jsonify({"ok": True})


# ============ الدفعات ============
@app.route("/api/batches", methods=["GET"])
def api_list_batches():
    return jsonify(store.list_batches())


@app.route("/api/batches", methods=["POST"])
def api_create_batch():
    name = request.form.get("name", "").strip() or time.strftime("دفعة %Y-%m-%d %H:%M")
    model = request.form.get("model", "nano_banana")
    strict = request.form.get("strict") == "1"
    template_id = request.form.get("template_id")
    template_id = int(template_id) if template_id else None
    prompt = request.form.get("prompt", "").strip() or None
    aspect = request.form.get("aspect") or None
    quality = request.form.get("quality") or None
    lock_subject = request.form.get("lock", "1") == "1"  # قفل المنتج (افتراضيًا مفعّل)

    # المرجع: إمّا ملف مرفوع، أو اسم ملف محفوظ مسبقًا (من جلسة تصميم الوضع "أ")
    reference = None
    if "reference" in request.files and request.files["reference"].filename:
        f = request.files["reference"]
        if not _allowed(f.filename):
            return jsonify({"error": "صيغة الصورة المرجعية غير مدعومة"}), 400
        reference = _save_upload(f)
    elif request.form.get("reference_name"):
        reference = secure_filename(request.form["reference_name"])

    files = request.files.getlist("images")
    files = [f for f in files if f.filename and _allowed(f.filename)]
    if not files:
        return jsonify({"error": "ارفع صورة واحدة على الأقل"}), 400

    bid = store.create_batch(
        name, template_id, model, reference=reference, prompt=prompt, strict=strict,
        aspect=aspect, quality=quality, lock_subject=lock_subject
    )
    for f in files:
        store.add_image(bid, _save_upload(f))

    threading.Thread(target=_process_batch, args=(bid,), daemon=True).start()
    return jsonify({"id": bid})


def _is_gpt(model):
    return model == "gpt_image"


def _env_key(model):
    """مفتاح من متغيّرات بيئة Railway (له الأولوية، لا يُحفظ في ملفات المنصة)."""
    if not _is_gpt(model):  # أي موديل Gemini (Nano Banana / Pro)
        return (os.environ.get("NANO_BANANA_KEY")
                or os.environ.get("GEMINI_API_KEY")
                or os.environ.get("GOOGLE_API_KEY") or "").strip()
    return (os.environ.get("GPT_IMAGE_KEY")
            or os.environ.get("OPENAI_API_KEY") or "").strip()


def _model_key(model):
    # الأولوية لمتغيّر البيئة (Railway)، ثم ما هو محفوظ محليًا (إن وُجد)
    return _env_key(model) or store.get_setting(
        "gpt_image_key" if _is_gpt(model) else "nano_banana_key"
    )


def _text_key():
    """مفتاح OpenAI لتحسين البرومبت النصّي (مستقل عن موديل الصورة)."""
    return _model_key("gpt_image")


def _process_batch(bid):
    batch = store.get_batch(bid)
    if not batch:
        return
    store.set_batch_status(bid, "running")
    api_key = _model_key(batch["model"])
    reference = _ref_path(batch.get("reference"))
    # تحسين البرومبت مرة واحدة للدفعة (مثل ChatGPT) — للوضع غير الصارم فقط
    raw = batch.get("prompt")
    if raw and not batch.get("strict"):
        raw = generator.enhance_prompt(raw, _text_key())
    prompt = build_prompt(raw, reference is not None, batch.get("strict"))
    lock = bool(batch.get("lock_subject"))

    for img in store.list_images(bid):
        store.update_image(img["id"], status="running")
        try:
            out = generator.generate(
                batch["model"],
                api_key,
                prompt,
                UPLOAD_DIR / img["original"],
                reference,
                aspect=batch.get("aspect"),
                quality=batch.get("quality"),
            )
            if lock:  # قفل المنتج (اختياري): يحفظ شكل المنتج تمامًا
                out = generator.lock_subject(UPLOAD_DIR / img["original"], out)
            result_name = f"{uuid.uuid4().hex}.png"
            (RESULT_DIR / result_name).write_bytes(out)
            store.update_image(img["id"], status="done", result=result_name, error=None)
        except Exception as e:  # noqa: BLE001
            store.update_image(img["id"], status="failed", error=str(e)[:400])

    store.set_batch_status(bid, "done")


@app.route("/api/batches/<int:bid>")
def api_get_batch(bid):
    batch = store.get_batch(bid)
    if not batch:
        abort(404)
    batch["images"] = store.list_images(bid)
    return jsonify(batch)


@app.route("/api/batches/<int:bid>", methods=["DELETE"])
def api_delete_batch(bid):
    store.delete_batch(bid)
    return jsonify({"ok": True})


@app.route("/api/batches/<int:bid>/download")
def api_download_batch(bid):
    images = store.list_images(bid)
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, "w", zipfile.ZIP_DEFLATED) as zf:
        for i, img in enumerate(images, 1):
            if img["result"]:
                zf.write(RESULT_DIR / img["result"], f"{i:03d}.png")
    mem.seek(0)
    return send_file(mem, mimetype="application/zip", as_attachment=True,
                     download_name=f"batch_{bid}.zip")


# ============ الوضع "أ": تصميم قالب من صورة واحدة (توليد + تعديل قبل الاعتماد) ============
@app.route("/api/design", methods=["POST"])
def api_design():
    """يولّد تصميمًا واحدًا من عيّنة + برومبت. أول مرة: رفع العيّنة.
    التكرار: إرسال sample_name للعيّنة المحفوظة مع برومبت جديد."""
    model = request.form.get("model", "nano_banana")
    prompt = request.form.get("prompt", "").strip()
    aspect = request.form.get("aspect") or None
    quality = request.form.get("quality") or None
    lock = request.form.get("lock", "1") == "1"
    if not prompt:
        return jsonify({"error": "اكتب برومبت التصميم"}), 400

    # العيّنة: ملف جديد أو اسم عيّنة محفوظة
    if "sample" in request.files and request.files["sample"].filename:
        f = request.files["sample"]
        if not _allowed(f.filename):
            return jsonify({"error": "صيغة صورة غير مدعومة"}), 400
        sample_name = _save_upload(f)
    elif request.form.get("sample_name"):
        sample_name = secure_filename(request.form["sample_name"])
    else:
        return jsonify({"error": "ارفع صورة العيّنة"}), 400

    api_key = _model_key(model)
    try:
        enhanced = generator.enhance_prompt(prompt, _text_key())
        eff = build_prompt(enhanced, has_reference=False, strict=False)
        out = generator.generate(model, api_key, eff, UPLOAD_DIR / sample_name, None,
                                 aspect=aspect, quality=quality)
        if lock:
            out = generator.lock_subject(UPLOAD_DIR / sample_name, out)
        result_name = f"{uuid.uuid4().hex}.png"
        (RESULT_DIR / result_name).write_bytes(out)
    except Exception as e:  # noqa: BLE001
        return jsonify({"error": str(e)[:400]}), 400

    # نُرجع البرومبت الخام للمستخدم (يُغلَّف تلقائيًا عند التطبيق على الدفعة)
    return jsonify(
        {"sample_name": sample_name, "result_name": result_name, "prompt": prompt}
    )


# ============ تعديل صورة مفردة (إعادة توليد ببرومبت مخصص) ============
@app.route("/api/images/<int:iid>/regenerate", methods=["POST"])
def api_regenerate(iid):
    img = store.get_image(iid)
    if not img:
        abort(404)
    batch = store.get_batch(img["batch_id"])

    # يقبل multipart (مع قناع منطقة) أو JSON (برومبت فقط)
    mask_file = None
    if request.content_type and "multipart" in request.content_type:
        custom_prompt = (request.form.get("prompt") or "").strip()
        mask_file = request.files.get("mask")
    else:
        data = request.get_json(force=True)
        custom_prompt = (data.get("prompt") or "").strip()

    api_key = _model_key(batch["model"])
    reference = _ref_path(batch.get("reference"))
    # برومبت مخصص من المستخدم يتقدّم؛ وإلا نستخدم برومبت الدفعة/الثبات
    if custom_prompt:
        prompt = build_prompt(generator.enhance_prompt(custom_prompt, _text_key()),
                              reference is not None, strict=False)
    else:
        raw = batch.get("prompt")
        if raw and not batch.get("strict"):
            raw = generator.enhance_prompt(raw, _text_key())
        prompt = build_prompt(raw, reference is not None, batch.get("strict"))

    store.update_image(iid, status="running", custom_prompt=custom_prompt or None)
    try:
        if mask_file and mask_file.filename:
            # تعديل منطقة محددة: يُدمج الجديد داخل القناع فوق النتيجة الحالية
            mask_name = f"mask_{uuid.uuid4().hex}.png"
            mask_file.save(UPLOAD_DIR / mask_name)
            base = RESULT_DIR / img["result"] if img.get("result") else UPLOAD_DIR / img["original"]
            out = generator.generate_region(
                batch["model"], api_key, prompt,
                UPLOAD_DIR / img["original"], reference,
                UPLOAD_DIR / mask_name, base,
                aspect=batch.get("aspect"), quality=batch.get("quality"),
            )
        else:
            out = generator.generate(
                batch["model"], api_key, prompt,
                UPLOAD_DIR / img["original"], reference,
                aspect=batch.get("aspect"), quality=batch.get("quality"),
            )
            if batch.get("lock_subject"):  # قفل المنتج (اختياري)
                out = generator.lock_subject(UPLOAD_DIR / img["original"], out)
        result_name = f"{uuid.uuid4().hex}.png"
        (RESULT_DIR / result_name).write_bytes(out)
        store.update_image(iid, status="done", result=result_name, error=None)
    except Exception as e:  # noqa: BLE001
        store.update_image(iid, status="failed", error=str(e)[:400])
    return jsonify(store.get_image(iid))


# ============ خدمة ملفات الصور ============
@app.route("/media/upload/<name>")
def media_upload(name):
    return send_file(UPLOAD_DIR / secure_filename(name))


@app.route("/media/result/<name>")
def media_result(name):
    return send_file(RESULT_DIR / secure_filename(name))


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    # 127.0.0.1 محليًا، و0.0.0.0 عند الاستضافة (عبر ضبط HOST)
    host = os.environ.get("HOST", "127.0.0.1")
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(host=host, port=port, debug=debug)
