# استوديو الصور — توليد بقالب موحّد

منصّة عربية بسيطة لتوليد كمية كبيرة من الصور (20–50 صورة دفعة واحدة) بأسلوب/قالب موحّد
باستخدام الذكاء الاصطناعي (Nano Banana من Google، أو GPT-Image من OpenAI).

## المزايا

- **دفعة جديدة بوضعين:**
  - **صمّم قالبًا جديدًا:** جرّب على صورة واحدة + برومبت حتى تعتمد الشكل، ثم طبّقه على كل المنتجات.
  - **قالب / صورة جاهزة:** أعطِ صورة مرجعية تُطبَّق على كل المنتجات بثبات تام بدون برومبت.
- **موديلان:** Nano Banana (Gemini) و GPT-Image (OpenAI).
- **خيارات المقاس** (1:1 / 3:4 / 4:3 / 9:16 / 16:9) **والجودة** (عالية / متوسطة / سريعة).
- **معرض النتائج** مع تعديل أي صورة: برومبت مخصص + **فرشاة لتحديد منطقة** يُعاد توليدها فقط.
- **مكتبة قوالب** محفوظة لإعادة الاستخدام.
- **تنزيل** صورة مفردة أو الدفعة كاملة (ZIP).
- **وضع تجربة** يعمل بدون مفاتيح API (معاينة محلية) لتجربة المنصة.

## التشغيل محليًا (Windows)

أسهل طريقة: انقر مزدوجًا على `تشغيل.bat` — يثبّت المتطلبات ويشغّل المنصة ويفتح المتصفح.

أو يدويًا:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

ثم افتح: `http://localhost:5001`

> ملاحظة: هذا مشروع **Python / Flask** وليس Node، فلا يوجد `npm install` أو `npm run build`.

## المفاتيح (API)

تُدخَل من داخل التطبيق: **الإعدادات ⚙️** — وتُحفظ في `data/settings.json` (ملف دائم لا يُرفع على GitHub).

- **Nano Banana (Gemini):** من [aistudio.google.com/apikey](https://aistudio.google.com/apikey) — يبدأ بـ `AIza`
- **GPT-Image (OpenAI):** من [platform.openai.com/api-keys](https://platform.openai.com/api-keys) — يبدأ بـ `sk-`

عند حفظ مفتاح يُطفأ وضع التجربة تلقائيًا ويعمل التوليد الحقيقي.

## متغيرات البيئة (اختيارية)

انظر `.env.example`:

- `DATA_DIR` — مجلد حفظ البيانات (اربطه بقرص دائم عند الاستضافة).
- `PORT` / `HOST` — منفذ وعنوان التشغيل.

## الاستضافة

المشروع جاهز للاستضافة على أي منصة تدعم Python (Railway / Render / …):

```bash
gunicorn --workers 1 --threads 4 --timeout 600 --bind 0.0.0.0:$PORT app:app
```

(موجود في `Procfile`.) استخدم عاملًا واحدًا (worker) لأن التخزين محلي، واربط `DATA_DIR`
بقرص دائم حتى لا تُفقد القوالب والدفعات.

## البنية

```
banana_studio/
├─ app.py            # خادم Flask والمسارات
├─ generator.py      # تكامل Nano Banana / GPT-Image + وضع التجربة
├─ store.py          # قاعدة بيانات SQLite + إعدادات JSON دائمة
├─ templates/        # index.html
├─ static/           # style.css + app.js
└─ data/             # (لا يُرفع) قاعدة البيانات + الصور + settings.json
```
