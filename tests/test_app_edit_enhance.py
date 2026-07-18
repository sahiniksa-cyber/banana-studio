"""اختبار مسار التعديل (مع التحقق) والتحسين ومساعد البرومبت على مستوى التطبيق."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402
import generator  # noqa: E402
import store  # noqa: E402
from conftest import CHANGED, SAME  # noqa: E402


# ---------- التعديل: يتأكد أنه نُفِّذ ----------
def test_edit_marks_done_when_change_applied(env, monkeypatch):
    _, iid = env["make_image"]()
    monkeypatch.setattr(generator, "generate", lambda *a, **k: CHANGED)
    app_module._do_edit(iid, "اجعل الخلفية بيضاء", None)
    img = store.get_image(iid)
    assert img["status"] == "done"
    assert (env["res"] / img["result"]).read_bytes() == CHANGED


def test_edit_retries_then_succeeds(env, monkeypatch):
    _, iid = env["make_image"]()
    # الجودة السريعة (low) لا تعدّل؛ المصعّدة (medium) تعدّل
    def fake_generate(model, api_key, prompt, *a, **k):
        return CHANGED if k.get("quality") == "medium" else SAME
    monkeypatch.setattr(generator, "generate", fake_generate)
    app_module._do_edit(iid, "شيل الانعكاس", None)
    img = store.get_image(iid)
    assert img["status"] == "done"
    assert (env["res"] / img["result"]).read_bytes() == CHANGED


def test_edit_reports_failure_when_model_never_edits(env, monkeypatch):
    _, iid = env["make_image"]()
    monkeypatch.setattr(generator, "generate", lambda *a, **k: SAME)  # يستهبل دائمًا
    app_module._do_edit(iid, "غيّر شيئًا", None)
    img = store.get_image(iid)
    assert img["status"] == "failed"
    assert "لم يُنفَّذ" in (img["error"] or "")


# ---------- التحسين بالذكاء ----------
def test_enhance_produces_new_result(env, monkeypatch):
    _, iid = env["make_image"]()
    monkeypatch.setattr(generator, "generate", lambda *a, **k: CHANGED)
    app_module._do_enhance(iid, "medium")
    img = store.get_image(iid)
    assert img["status"] == "done"
    assert img["result"] != "base.png"
    assert (env["res"] / img["result"]).read_bytes() == CHANGED


def test_enhance_endpoint_validates_and_returns_running(env, monkeypatch):
    _, iid = env["make_image"]()
    monkeypatch.setattr(app_module.threading, "Thread",
                        lambda *a, **k: type("T", (), {"start": lambda self: None})())
    client = app_module.app.test_client()
    r = client.post(f"/api/images/{iid}/enhance", json={"level": "strong"})
    assert r.status_code == 200
    assert r.get_json()["status"] == "running"


# ---------- مساعد البرومبت ----------
def test_prompt_assist_endpoint_returns_professional_prompt(env):
    client = app_module.app.test_client()
    r = client.post("/api/prompt-assist", json={"brief": "خلفية رخام فاخرة للعطر"})
    assert r.status_code == 200
    out = r.get_json()["prompt"]
    assert len(out) > 40
    assert "رخام" in out  # فهم طلب العميل (عبر الصيغة الاحتياطية بلا مفتاح)


def test_prompt_assist_rejects_empty(env):
    client = app_module.app.test_client()
    r = client.post("/api/prompt-assist", json={"brief": "   "})
    assert r.status_code == 400
