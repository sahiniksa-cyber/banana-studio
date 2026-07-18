"""تهيئة اختبارات على مستوى التطبيق: قاعدة بيانات ومجلدات معزولة + مفتاح وهمي."""
import io
import os
import sys

import pytest
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_module  # noqa: E402
import store  # noqa: E402


def png(color, size=(200, 260)):
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, "PNG")
    return buf.getvalue()


CHANGED = png((30, 30, 30))
SAME = png((180, 180, 180))
BASE_COLOR = (180, 180, 180)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    """يعزل التخزين في مجلد مؤقّت ويحيّد المفاتيح والتوازي."""
    up = tmp_path / "uploads"
    res = tmp_path / "results"
    up.mkdir(); res.mkdir()
    store.init_db(tmp_path / "studio.db")
    monkeypatch.setattr(app_module, "UPLOAD_DIR", up)
    monkeypatch.setattr(app_module, "RESULT_DIR", res)
    monkeypatch.setattr(app_module, "_model_key", lambda model: "sk-test")
    monkeypatch.setattr(app_module, "_text_key", lambda: "")  # مساعد البرومبت → احتياطي

    def make_image(model="gpt_image", with_result=True):
        bid = store.create_batch("t", None, model, prompt="p", aspect="1:1", quality="high")
        iid = store.add_image(bid, "orig.png")
        (up / "orig.png").write_bytes(png(BASE_COLOR))
        if with_result:
            (res / "base.png").write_bytes(png(BASE_COLOR))
            store.update_image(iid, status="done", result="base.png")
        return bid, iid

    return {"app": app_module, "up": up, "res": res, "make_image": make_image}
