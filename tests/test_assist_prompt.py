"""اختبار مساعد البرومبت: يحوّل وصفًا عاميًّا إلى برومبت احترافي، ولا يُرجع 'هبد'."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import generator  # noqa: E402


class _Resp:
    def __init__(self, status, content):
        self.status_code = status
        self._content = content
        self.text = content or ""

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


def test_fallback_when_no_key_still_returns_usable_prompt():
    out = generator.assist_prompt("خلفية بيضاء نظيفة للمنتج", openai_key="")
    assert isinstance(out, str)
    assert len(out) > 40          # برومبت حقيقي لا مجرد كلمة
    assert "خلفية بيضاء" in out    # يحتوي وصف العميل


def test_uses_model_output_when_valid(monkeypatch):
    good = ("Studio product shot on a seamless white background, soft key light from "
            "the left, gentle reflection, 85mm lens, keep the product unchanged.")
    monkeypatch.setattr(generator.requests, "post",
                        lambda *a, **k: _Resp(200, good))
    out = generator.assist_prompt("خلفية بيضاء", openai_key="sk-test")
    assert out == good


def test_rejects_apology_and_falls_back(monkeypatch):
    monkeypatch.setattr(generator.requests, "post",
                        lambda *a, **k: _Resp(200, "Sorry, I cannot help with that."))
    out = generator.assist_prompt("خلفية بيضاء", openai_key="sk-test")
    assert "Sorry" not in out
    assert len(out) > 40          # رجع للصيغة الاحتياطية بدل الاعتذار


def test_rejects_too_short_output_and_falls_back(monkeypatch):
    monkeypatch.setattr(generator.requests, "post",
                        lambda *a, **k: _Resp(200, "white bg"))
    out = generator.assist_prompt("خلفية بيضاء احترافية", openai_key="sk-test")
    assert out != "white bg"
    assert len(out) > 40


def test_network_error_falls_back(monkeypatch):
    def _boom(*a, **k):
        raise generator.requests.RequestException("no net")
    monkeypatch.setattr(generator.requests, "post", _boom)
    out = generator.assist_prompt("منتج على رخام فاخر", openai_key="sk-test")
    assert len(out) > 40
    assert "رخام" in out
