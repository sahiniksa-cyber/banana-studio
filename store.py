"""تخزين القوالب والدفعات والصور في SQLite.

ملاحظة مهمة: الإعدادات (مفاتيح API + وضع التجربة) تُحفظ في ملف JSON مستقل
(settings.json) وليست داخل قاعدة البيانات — حتى لا تُفقد أبدًا حتى لو
أُعيد إنشاء قاعدة البيانات.
"""
import sqlite3
import json
import time
from pathlib import Path

_DB_PATH = None
_SETTINGS_PATH = None


def init_db(db_path: Path):
    global _DB_PATH, _SETTINGS_PATH
    _DB_PATH = Path(db_path)
    _SETTINGS_PATH = _DB_PATH.parent / "settings.json"
    conn = _connect()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS templates (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            reference   TEXT,                 -- اسم ملف الصورة المرجعية
            prompt      TEXT NOT NULL,
            created_at  REAL NOT NULL
        );

        CREATE TABLE IF NOT EXISTS batches (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT NOT NULL,
            template_id INTEGER,
            model       TEXT NOT NULL,        -- 'nano_banana' أو 'gpt_image'
            status      TEXT NOT NULL,        -- pending / running / done
            reference   TEXT,                 -- مرجع خاص بالدفعة (يتجاوز القالب)
            prompt      TEXT,                 -- برومبت خاص بالدفعة (يتجاوز القالب)
            strict      INTEGER DEFAULT 0,    -- 1 = وضع الثبات التام (بدون برومبت مستخدم)
            aspect      TEXT,                 -- نسبة الأبعاد: 1:1 / 3:4 / 4:3 / 9:16 / 16:9
            quality     TEXT,                 -- الجودة: low / medium / high
            lock_subject INTEGER DEFAULT 1,   -- 1 = قفل المنتج (لا يتغيّر شكله إطلاقًا)
            created_at  REAL NOT NULL,
            FOREIGN KEY (template_id) REFERENCES templates(id)
        );

        CREATE TABLE IF NOT EXISTS images (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id      INTEGER NOT NULL,
            original      TEXT NOT NULL,       -- اسم ملف الصورة الأصلية
            result        TEXT,                -- اسم ملف النتيجة
            status        TEXT NOT NULL,       -- queued / running / done / failed
            error         TEXT,
            custom_prompt TEXT,                -- برومبت مخصص عند التعديل
            FOREIGN KEY (batch_id) REFERENCES batches(id)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    _migrate(conn)
    conn.close()


def _migrate(conn):
    """ترقية آمنة للمخطّط: يضيف الأعمدة الناقصة بدون حذف أي بيانات."""
    wanted = {
        "batches": {
            "reference": "TEXT",
            "prompt": "TEXT",
            "strict": "INTEGER DEFAULT 0",
            "aspect": "TEXT",
            "quality": "TEXT",
            "lock_subject": "INTEGER DEFAULT 1",
        },
    }
    for table, cols in wanted.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        for col, decl in cols.items():
            if col not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    conn.commit()


def _connect():
    # timeout ينتظر على قفل قاعدة البيانات عند الكتابة المتوازية من عدة خيوط
    conn = sqlite3.connect(_DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    return conn


# ---------- الإعدادات (مفاتيح API) — تُحفظ في ملف JSON دائم ----------
def _load_settings():
    if _SETTINGS_PATH and _SETTINGS_PATH.exists():
        try:
            return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def get_setting(key, default=None):
    return _load_settings().get(key, default)


def set_setting(key, value):
    data = _load_settings()
    data[key] = value
    _SETTINGS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- القوالب ----------
def create_template(name, reference, prompt):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO templates (name, reference, prompt, created_at) VALUES (?, ?, ?, ?)",
        (name, reference, prompt, time.time()),
    )
    conn.commit()
    tid = cur.lastrowid
    conn.close()
    return tid


def list_templates():
    conn = _connect()
    rows = conn.execute("SELECT * FROM templates ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_template(tid):
    conn = _connect()
    row = conn.execute("SELECT * FROM templates WHERE id = ?", (tid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_template(tid):
    conn = _connect()
    conn.execute("DELETE FROM templates WHERE id = ?", (tid,))
    conn.commit()
    conn.close()


# ---------- الدفعات ----------
def create_batch(name, template_id, model, reference=None, prompt=None, strict=False,
                 aspect=None, quality=None, lock_subject=True):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO batches (name, template_id, model, status, reference, prompt, strict, "
        "aspect, quality, lock_subject, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (name, template_id, model, "pending", reference, prompt, 1 if strict else 0,
         aspect, quality, 1 if lock_subject else 0, time.time()),
    )
    conn.commit()
    bid = cur.lastrowid
    conn.close()
    return bid


def set_batch_status(bid, status):
    conn = _connect()
    conn.execute("UPDATE batches SET status = ? WHERE id = ?", (status, bid))
    conn.commit()
    conn.close()


def list_batches():
    conn = _connect()
    rows = conn.execute(
        """
        SELECT b.*, t.name AS template_name,
               (SELECT COUNT(*) FROM images WHERE batch_id = b.id) AS total,
               (SELECT COUNT(*) FROM images WHERE batch_id = b.id AND status = 'done') AS done
        FROM batches b LEFT JOIN templates t ON t.id = b.template_id
        ORDER BY b.created_at DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_batch(bid):
    conn = _connect()
    conn.execute("DELETE FROM images WHERE batch_id = ?", (bid,))
    conn.execute("DELETE FROM batches WHERE id = ?", (bid,))
    conn.commit()
    conn.close()


def get_batch(bid):
    conn = _connect()
    row = conn.execute(
        "SELECT b.id, b.name, b.template_id, b.model, b.status, b.strict, b.created_at, "
        "       b.aspect, b.quality, b.lock_subject, "
        "       t.name AS template_name, "
        "       COALESCE(b.reference, t.reference) AS reference, "
        "       COALESCE(b.prompt, t.prompt)       AS prompt "
        "FROM batches b LEFT JOIN templates t ON t.id = b.template_id WHERE b.id = ?",
        (bid,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------- الصور ----------
def add_image(batch_id, original):
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO images (batch_id, original, status) VALUES (?, ?, 'queued')",
        (batch_id, original),
    )
    conn.commit()
    iid = cur.lastrowid
    conn.close()
    return iid


def list_images(batch_id):
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM images WHERE batch_id = ? ORDER BY id", (batch_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_image(iid):
    conn = _connect()
    row = conn.execute("SELECT * FROM images WHERE id = ?", (iid,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_image(iid, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [iid]
    conn = _connect()
    conn.execute(f"UPDATE images SET {cols} WHERE id = ?", vals)
    conn.commit()
    conn.close()
