// ===== حالة عامة =====
let currentBatchId = null;
let currentImageId = null;
let pollTimer = null;

const main = document.getElementById("main");

// ============================================================
//  نظام الأيقونات (SVG خطّي احترافي)
// ============================================================
const ICONS = {
  image: '<rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
  download: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/>',
  trash: '<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>',
  arrowRight: '<line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/>',
  refresh: '<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>',
  check: '<polyline points="20 6 9 17 4 12"/>',
  wand: '<path d="M15 4V2"/><path d="M15 16v-2"/><path d="M8 9h2"/><path d="M20 9h2"/><path d="M17.8 11.8 19 13"/><path d="M15 9h.01"/><path d="M17.8 6.2 19 5"/><path d="m3 21 9-9"/><path d="M12.2 6.2 11 5"/>',
  edit: '<path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 0 1 3 3L7 19l-4 1 1-4Z"/>',
  copy: '<rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>',
  play: '<polygon points="5 3 19 12 5 21 5 3"/>',
  alert: '<path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>',
  save: '<path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"/><polyline points="17 21 17 13 7 13 7 21"/><polyline points="7 3 7 8 15 8"/>',
  inbox: '<polyline points="22 12 16 12 14 15 10 15 8 12 2 12"/><path d="M5.45 5.11 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"/>',
  plus: '<line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>',
  zap: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>',
  cpu: '<rect x="4" y="4" width="16" height="16" rx="2"/><rect x="9" y="9" width="6" height="6"/><line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/><line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/><line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/><line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>',
  upload: '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>',
  layers: '<path d="M12 2 2 7l10 5 10-5-10-5Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
};

function icon(name, cls = "ico") {
  return `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${ICONS[name] || ""}</svg>`;
}
function spinner() {
  return `<svg class="ico spin-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 12a9 9 0 1 1-6.219-8.56"/></svg>`;
}
// أيقونة نسبة الأبعاد (مستطيل بنفس النسبة)
function aspectIcon(ratio) {
  const [w, h] = ratio.split(":").map(Number);
  const maxW = 18, maxH = 14;
  let rw, rh;
  if (w / h >= 1) { rw = maxW; rh = maxW * h / w; } else { rh = maxH; rw = maxH * w / h; }
  const x = ((24 - rw) / 2).toFixed(1), y = ((24 - rh) / 2).toFixed(1);
  return `<svg class="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="${x}" y="${y}" width="${rw.toFixed(1)}" height="${rh.toFixed(1)}" rx="2"/></svg>`;
}

// أزرار مع حالة تحميل
function setLoading(btn, text) { btn.disabled = true; btn.innerHTML = spinner() + `<span>${text}</span>`; }
function setBtn(btn, iconName, text) { btn.disabled = false; btn.innerHTML = icon(iconName) + `<span>${text}</span>`; }

// ===== أدوات مساعدة =====
function toast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2600);
}

async function api(url, opts) {
  const res = await fetch(url, opts);
  if (!res.ok) {
    let msg = "خطأ في الطلب";
    try { msg = (await res.json()).error || msg; } catch (e) {}
    throw new Error(msg);
  }
  return res.json();
}

function statusLabel(s) {
  return { queued: "بالانتظار", running: "يعالج…", done: "جاهزة", failed: "فشلت" }[s] || s;
}

// هل يوجد مفتاح API مضبوط؟ (يُحدّث عند الإقلاع وبعد حفظ الإعدادات)
let HAS_KEY = false;
async function refreshKeys() {
  try {
    const s = await api("/api/settings");
    HAS_KEY = !!(s.gpt_image_key_set || s.nano_banana_key_set);
  } catch (e) {}
}
function noKeyBanner() {
  if (HAS_KEY) return "";
  return `<div class="demo-banner">${icon("alert")}
    <div><b>لا يوجد مفتاح API</b> — لن تتمكّن من إنشاء الصور حتى تضيف مفتاحًا.
    افتح <a onclick="navigate('settings')">الإعدادات</a> وأدخل مفتاح GPT-Image أو Nano Banana.</div></div>`;
}

// ===== التنقّل =====
document.querySelectorAll(".nav-item").forEach((btn) => {
  btn.addEventListener("click", () => navigate(btn.dataset.view));
});

function setActive(view) {
  document.querySelectorAll(".nav-item").forEach((b) =>
    b.classList.toggle("active", b.dataset.view === view)
  );
}

function navigate(view) {
  clearInterval(pollTimer);
  setActive(view);
  if (view === "batches") viewBatches();
  else if (view === "new-batch") viewNewBatch();
  else if (view === "templates") viewTemplates();
  else if (view === "settings") viewSettings();
}

// ===== شاشة: الدفعات =====
async function viewBatches() {
  main.innerHTML = `<div class="page-title">الدفعات</div>
    <div class="page-sub">كل دفعات التوليد التي أنشأتها</div>
    <div id="batches-list"><div class="empty">جارِ التحميل…</div></div>`;
  const batches = await api("/api/batches");
  const el = document.getElementById("batches-list");
  if (!batches.length) {
    el.innerHTML = `<div class="empty">
      <div class="big">${icon("inbox")}</div>
      <p>لا توجد دفعات بعد. ابدأ بإنشاء دفعتك الأولى.</p>
      <button class="btn" onclick="navigate('new-batch')">${icon("plus")}<span>أنشئ أول دفعة</span></button></div>`;
    return;
  }
  el.className = "grid-cards";
  el.innerHTML = batches.map((b) => `
    <div class="tile" onclick="openBatch(${b.id})">
      <div class="thumb">${icon("image")} ${b.total} صورة</div>
      <div class="body">
        <h4>${escapeHtml(b.name)}</h4>
        <p>القالب: ${escapeHtml(b.template_name || "بدون")}</p>
        <div class="meta">
          <span>${modelLabel(b.model)}</span> ·
          <span>${b.done}/${b.total} جاهزة</span>
          <span class="badge ${b.status === "done" ? "done" : "running"}"><span class="dot"></span>${statusLabel(b.status)}</span>
        </div>
      </div>
    </div>`).join("");
}

// ===== شاشة: دفعة جديدة — اختيار الوضع =====
function viewNewBatch() {
  main.innerHTML = `
    ${noKeyBanner()}
    <div class="page-title">دفعة جديدة</div>
    <div class="page-sub">اختر طريقة العمل</div>
    <div class="mode-cards">
      <div class="mode-card" onclick="viewDesignMode()">
        <div class="m-icon">${icon("edit")}</div>
        <h3>صمّم قالبًا جديدًا</h3>
        <p>ابدأ بمنتج أو صورة واحدة، اكتب البرومبت، وعدّل حتى تعتمد التصميم.
           بعد الاعتماد يصير قالبًا يُطبَّق تلقائيًا على كل المنتجات.</p>
        <span class="tag">مع برومبت + تعديل قبل الاعتماد</span>
      </div>
      <div class="mode-card" onclick="viewReferenceMode()">
        <div class="m-icon">${icon("copy")}</div>
        <h3>استخدم قالبًا / صورة جاهزة</h3>
        <p>أعطِ المنصة صورة مرجعية تريد أن تشبهها كل المنتجات، وتُطبَّق عليها
           بثبات تام دون أن تكسر الطابع — بدون خانة برومبت.</p>
        <span class="tag">ثبات تام · بدون برومبت</span>
      </div>
    </div>`;
}

// أداة مساعدة: أزرار اختيار الموديل
const MODELS = {
  gpt_image: "GPT-Image",
  nano_banana: "Nano Banana",
  nano_banana_pro: "Nano Banana Pro",
};
function modelLabel(m) { return MODELS[m] || m; }

function modelPills(id) {
  return `<div class="pill-choice wrap" id="${id}">
      <div class="pill active" data-model="gpt_image">${icon("cpu")}<span>GPT-Image</span></div>
      <div class="pill" data-model="nano_banana">${icon("zap")}<span>Nano Banana</span></div>
      <div class="pill" data-model="nano_banana_pro">${icon("zap")}<span>Nano Banana Pro</span></div>
    </div>`;
}
function wireModelPills(id, stateObj) {
  stateObj.model = "gpt_image";
  document.querySelectorAll(`#${id} .pill`).forEach((p) => {
    p.addEventListener("click", () => {
      document.querySelectorAll(`#${id} .pill`).forEach((x) => x.classList.remove("active"));
      p.classList.add("active");
      stateObj.model = p.dataset.model;
    });
  });
}
function wireDrop(dropId, inputId, countId) {
  const input = document.getElementById(inputId);
  document.getElementById(dropId).addEventListener("click", () => input.click());
  if (countId) input.addEventListener("change", () => {
    document.getElementById(countId).textContent =
      input.files.length ? `${input.files.length} صورة مختارة` : "";
  });
}

// خيارات المقاس والجودة
const ASPECTS = [
  { val: "1:1", label: "مربّع 1:1" },
  { val: "3:4", label: "طولي 3:4" },
  { val: "4:3", label: "أفقي 4:3" },
  { val: "9:16", label: "ستوري 9:16" },
  { val: "16:9", label: "عريض 16:9" },
];
const QUALITIES = [
  { val: "high", label: "عالية" },
  { val: "medium", label: "متوسطة" },
  { val: "low", label: "سريعة" },
];

function choicePills(id, options, activeVal, useAspectIcon) {
  return `<div class="pill-choice wrap" id="${id}">` +
    options.map((o) =>
      `<div class="pill${o.val === activeVal ? " active" : ""}" data-val="${o.val}">` +
      `${useAspectIcon ? aspectIcon(o.val) : ""}<span>${o.label}</span></div>`
    ).join("") + `</div>`;
}
function wireChoicePills(id, stateObj, prop, defaultVal) {
  stateObj[prop] = defaultVal;
  document.querySelectorAll(`#${id} .pill`).forEach((p) => {
    p.addEventListener("click", () => {
      document.querySelectorAll(`#${id} .pill`).forEach((x) => x.classList.remove("active"));
      p.classList.add("active");
      stateObj[prop] = p.dataset.val;
    });
  });
}
function qualityNote(id) {
  return `<div id="${id}" class="page-sub" style="margin-top:-8px;font-size:0.78rem">
    الجودة تؤثر في GPT-Image (وفي التكلفة). Nano Banana يولّد بأعلى جودة تلقائيًا.</div>`;
}
function lockToggle(id) {
  return `<label class="check-row" style="margin:6px 0 16px">
      <input type="checkbox" id="${id}" checked>
      <span><b>قفل شكل المنتج</b> — منتجك يبقى مطابقًا 100% (الذكاء يغيّر الخلفية فقط).
      <br>أطفئه لمظهر <b>طبيعي أكثر كأنه من ChatGPT</b> (قد يغيّر المنتج بسيط).</span>
    </label>`;
}

// ===== الوضع "أ": استوديو تصميم القالب =====
const design = {};
function viewDesignMode() {
  Object.assign(design, { model: "nano_banana", sampleName: null, resultName: null, prompt: "" });
  main.innerHTML = `
    <button class="back-link" onclick="viewNewBatch()">${icon("arrowRight")}<span>رجوع لاختيار الوضع</span></button>
    ${noKeyBanner()}
    <div class="page-title">صمّم قالبًا جديدًا</div>
    <div class="page-sub">جرّب على صورة واحدة حتى تعتمد الشكل، بعدها طبّقه على كل المنتجات</div>

    <div class="card">
      <div class="step-head"><span class="step-num">1</span><span>صمّم على صورة واحدة</span></div>
      <div class="studio">
        <div>
          <label>صورة العيّنة</label>
          <div class="file-drop" id="d-drop">${icon("upload")}<span>اختر صورة منتج للتجربة</span></div>
          <input type="file" id="d-sample" accept="image/*" class="hidden">
          <div id="d-sample-name" class="page-sub"></div>

          <label>الموديل</label>
          ${modelPills("d-model")}

          <label>المقاس / نسبة الأبعاد</label>
          ${choicePills("d-aspect", ASPECTS, "1:1", true)}

          <label>الجودة</label>
          ${choicePills("d-quality", QUALITIES, "high")}
          ${qualityNote("d-qnote")}

          ${lockToggle("d-lock")}

          <label>البرومبت</label>
          <textarea id="d-prompt" placeholder="صف الشكل/الأسلوب المطلوب…"></textarea>
          <button class="btn" id="d-gen" onclick="designGenerate()">${icon("wand")}<span>ولّد التصميم</span></button>
        </div>
        <div>
          <label>المعاينة</label>
          <div class="preview-frame" id="d-preview">ستظهر النتيجة هنا</div>
          <div id="d-actions" class="hidden row" style="margin-top:14px">
            <button class="btn ghost" onclick="designGenerate()">${icon("refresh")}<span>جرّب مرة ثانية</span></button>
            <button class="btn" onclick="designApprove()">${icon("check")}<span>اعتمد وطبّق على المنتجات</span></button>
          </div>
        </div>
      </div>
    </div>

    <div class="card hidden" id="d-step2">
      <div class="step-head"><span class="step-num">2</span><span>طبّق القالب على كل المنتجات</span></div>
      <label>اسم الدفعة</label>
      <input type="text" id="d-batch-name" placeholder="مثال: منتجات أكتوبر">
      <label>صور المنتجات (20-50 صورة)</label>
      <div class="file-drop" id="d-batch-drop">${icon("upload")}<span>اضغط لاختيار صور المنتجات</span></div>
      <input type="file" id="d-batch-files" multiple accept="image/*" class="hidden">
      <div id="d-batch-count" class="page-sub"></div>
      <button class="btn" id="d-run" onclick="designRun()">${icon("play")}<span>ابدأ التوليد على الكل</span></button>
    </div>`;

  wireModelPills("d-model", design);
  wireChoicePills("d-aspect", design, "aspect", "1:1");
  wireChoicePills("d-quality", design, "quality", "high");
  wireDrop("d-drop", "d-sample", null);
  document.getElementById("d-sample").addEventListener("change", (e) => {
    document.getElementById("d-sample-name").textContent = e.target.files[0]?.name || "";
  });
  wireDrop("d-batch-drop", "d-batch-files", "d-batch-count");
}

async function designGenerate() {
  const prompt = document.getElementById("d-prompt").value.trim();
  if (!prompt) return toast("اكتب البرومبت");
  const sampleFile = document.getElementById("d-sample").files[0];
  if (!design.sampleName && !sampleFile) return toast("اختر صورة العيّنة");

  const btn = document.getElementById("d-gen");
  setLoading(btn, "جارِ التوليد…");
  document.getElementById("d-preview").innerHTML = `${spinner()} <span style="margin-inline-start:8px">يعالج…</span>`;

  const fd = new FormData();
  fd.append("model", design.model);
  fd.append("prompt", prompt);
  fd.append("aspect", design.aspect);
  fd.append("quality", design.quality);
  fd.append("lock", document.getElementById("d-lock").checked ? "1" : "0");
  if (sampleFile) fd.append("sample", sampleFile);
  else fd.append("sample_name", design.sampleName);

  try {
    const r = await api("/api/design", { method: "POST", body: fd });
    design.sampleName = r.sample_name;
    design.resultName = r.result_name;
    design.prompt = r.prompt;
    document.getElementById("d-preview").innerHTML =
      `<img src="/media/result/${r.result_name}?t=${Date.now()}" alt="">`;
    document.getElementById("d-actions").classList.remove("hidden");
  } catch (e) {
    toast(e.message);
    document.getElementById("d-preview").textContent = "فشل التوليد";
  }
  setBtn(btn, "wand", "ولّد التصميم");
}

function designApprove() {
  if (!design.resultName) return toast("ولّد تصميمًا أولًا");
  document.getElementById("d-step2").classList.remove("hidden");
  document.getElementById("d-step2").scrollIntoView({ behavior: "smooth" });
  toast("تم اعتماد التصميم — ارفع المنتجات الآن");
}

async function designRun() {
  const files = document.getElementById("d-batch-files").files;
  if (!files.length) return toast("ارفع صور المنتجات");
  const btn = document.getElementById("d-run");
  setLoading(btn, "جارِ الرفع…");

  const fd = new FormData();
  fd.append("name", document.getElementById("d-batch-name").value);
  fd.append("model", design.model);
  fd.append("reference_name", design.resultName); // التصميم المعتمد يصير المرجع
  fd.append("prompt", design.prompt);
  fd.append("aspect", design.aspect);
  fd.append("quality", design.quality);
  fd.append("lock", document.getElementById("d-lock").checked ? "1" : "0");
  for (const f of files) fd.append("images", f);

  try {
    const { id } = await api("/api/batches", { method: "POST", body: fd });
    toast("بدأ التوليد!");
    openBatch(id);
  } catch (e) {
    toast(e.message);
    setBtn(btn, "play", "ابدأ التوليد على الكل");
  }
}

// ===== الوضع "ب": قالب / صورة جاهزة (ثبات تام، بدون برومبت) =====
const refMode = {};
async function viewReferenceMode() {
  const templates = await api("/api/templates");
  Object.assign(refMode, { model: "nano_banana" });
  main.innerHTML = `
    <button class="back-link" onclick="viewNewBatch()">${icon("arrowRight")}<span>رجوع لاختيار الوضع</span></button>
    ${noKeyBanner()}
    <div class="page-title">قالب / صورة جاهزة</div>
    <div class="page-sub">المرجع يُطبَّق على كل المنتجات بثبات تام — لا توجد خانة برومبت</div>

    <div class="card">
      <label>اسم الدفعة</label>
      <input type="text" id="r-name" placeholder="مثال: منتجات أكتوبر">

      <label>القالب المحفوظ (اختياري)</label>
      <select id="r-template" onchange="onRefTemplateChange()">
        <option value="">— أو ارفع صورة مرجعية بالأسفل —</option>
        ${templates.map((t) => `<option value="${t.id}">${escapeHtml(t.name)}</option>`).join("")}
      </select>

      <div id="r-ref-block">
        <label>الصورة المرجعية</label>
        <div class="file-drop" id="r-ref-drop">${icon("upload")}<span>اختر الصورة المرجعية</span></div>
        <input type="file" id="r-ref" accept="image/*" class="hidden">
        <div id="r-ref-name" class="page-sub"></div>
      </div>

      <label>الموديل</label>
      ${modelPills("r-model")}

      <label>المقاس / نسبة الأبعاد</label>
      ${choicePills("r-aspect", ASPECTS, "1:1", true)}

      <label>الجودة</label>
      ${choicePills("r-quality", QUALITIES, "high")}
      ${qualityNote("r-qnote")}

      ${lockToggle("r-lock")}

      <label>صور المنتجات (20-50 صورة)</label>
      <div class="file-drop" id="r-drop">${icon("upload")}<span>اضغط لاختيار صور المنتجات</span></div>
      <input type="file" id="r-files" multiple accept="image/*" class="hidden">
      <div id="r-count" class="page-sub"></div>

      <button class="btn" id="r-run" onclick="refRun()">${icon("play")}<span>ابدأ التوليد على الكل</span></button>
    </div>`;

  wireModelPills("r-model", refMode);
  wireChoicePills("r-aspect", refMode, "aspect", "1:1");
  wireChoicePills("r-quality", refMode, "quality", "high");
  wireDrop("r-ref-drop", "r-ref", null);
  document.getElementById("r-ref").addEventListener("change", (e) => {
    document.getElementById("r-ref-name").textContent = e.target.files[0]?.name || "";
  });
  wireDrop("r-drop", "r-files", "r-count");
}

function onRefTemplateChange() {
  // عند اختيار قالب محفوظ نخفي رفع المرجع (القالب يوفّره)
  const hasTpl = !!document.getElementById("r-template").value;
  document.getElementById("r-ref-block").classList.toggle("hidden", hasTpl);
}

async function refRun() {
  const files = document.getElementById("r-files").files;
  if (!files.length) return toast("ارفع صور المنتجات");
  const tpl = document.getElementById("r-template").value;
  const refFile = document.getElementById("r-ref").files[0];
  if (!tpl && !refFile) return toast("اختر قالبًا محفوظًا أو ارفع صورة مرجعية");

  const btn = document.getElementById("r-run");
  setLoading(btn, "جارِ الرفع…");

  const fd = new FormData();
  fd.append("name", document.getElementById("r-name").value);
  fd.append("model", refMode.model);
  fd.append("aspect", refMode.aspect);
  fd.append("quality", refMode.quality);
  fd.append("lock", document.getElementById("r-lock").checked ? "1" : "0");
  fd.append("strict", "1"); // ثبات تام — الخادم يستخدم تعليمة صارمة بدون برومبت مستخدم
  if (tpl) fd.append("template_id", tpl);
  else if (refFile) fd.append("reference", refFile);
  for (const f of files) fd.append("images", f);

  try {
    const { id } = await api("/api/batches", { method: "POST", body: fd });
    toast("بدأ التوليد!");
    openBatch(id);
  } catch (e) {
    toast(e.message);
    setBtn(btn, "play", "ابدأ التوليد على الكل");
  }
}

// ===== شاشة: معرض دفعة =====
async function openBatch(bid) {
  currentBatchId = bid;
  setActive("batches");
  await renderBatch();
  pollTimer = setInterval(renderBatchImages, 2500);
}

async function renderBatch() {
  const b = await api(`/api/batches/${currentBatchId}`);
  main.innerHTML = `
    <div class="row" style="justify-content:space-between; align-items:center; margin-bottom:22px">
      <div>
        <div class="page-title" style="margin-bottom:2px">${escapeHtml(b.name)}</div>
        <div class="page-sub" style="margin-bottom:0">القالب: ${escapeHtml(b.template_name || "بدون")} ·
          ${modelLabel(b.model)}</div>
      </div>
      <div class="row" style="flex:0">
        <button class="btn ghost" onclick="navigate('batches')">${icon("arrowRight")}<span>رجوع</span></button>
        <button class="btn danger" onclick="deleteBatch(${b.id})">${icon("trash")}<span>حذف</span></button>
        <a class="btn" href="/api/batches/${b.id}/download">${icon("download")}<span>تحميل الكل</span></a>
      </div>
    </div>
    <div class="image-grid" id="img-grid"></div>`;
  renderBatchImages();
}

async function renderBatchImages() {
  const b = await api(`/api/batches/${currentBatchId}`);
  const grid = document.getElementById("img-grid");
  if (!grid) return;
  grid.innerHTML = b.images.map((img) => {
    const src = img.result ? `/media/result/${img.result}` : `/media/upload/${img.original}`;
    const overlay = img.status === "running" || img.status === "queued"
      ? `<div class="spin">${spinner()} ${statusLabel(img.status)}</div>` : "";
    return `<div class="img-cell" onclick="openImage(${img.id})">
      <img src="${src}" alt="">
      <span class="status ${img.status}">${statusLabel(img.status)}</span>
      ${overlay}
    </div>`;
  }).join("");
  if (b.status === "done") clearInterval(pollTimer);
}

async function deleteBatch(bid) {
  if (!confirm("حذف هذه الدفعة وكل صورها؟")) return;
  clearInterval(pollTimer);
  await api(`/api/batches/${bid}`, { method: "DELETE" });
  toast("تم حذف الدفعة");
  navigate("batches");
}

// ===== نافذة التعديل =====
// حالة الفرشاة
let brushOn = false;
let maskDirty = false;

async function openImage(iid) {
  currentImageId = iid;
  const b = await api(`/api/batches/${currentBatchId}`);
  const img = b.images.find((x) => x.id === iid);
  document.getElementById("modal-original").src = `/media/upload/${img.original}`;
  const resultImg = document.getElementById("modal-result");
  resultImg.src = img.result ? `/media/result/${img.result}?t=${Date.now()}` : "";
  document.getElementById("modal-prompt").value = img.custom_prompt || "";

  const err = document.getElementById("modal-error");
  if (img.status === "failed" && img.error) {
    err.innerHTML = icon("alert") + `<span>فشلت هذه الصورة: ${escapeHtml(img.error)}</span>`;
    err.classList.remove("hidden");
  } else err.classList.add("hidden");

  const dl = document.getElementById("dl-single");
  if (img.result) { dl.href = `/media/result/${img.result}`; dl.classList.remove("hidden"); }
  else dl.classList.add("hidden");

  resetBrush();
  resultImg.onload = sizeMaskCanvas;
  document.getElementById("overlay").classList.add("open");
}

function closeModal() {
  document.getElementById("overlay").classList.remove("open");
}

// ===== الفرشاة =====
function maskCanvas() { return document.getElementById("mask-canvas"); }

function sizeMaskCanvas() {
  const c = maskCanvas();
  const img = document.getElementById("modal-result");
  const w = img.clientWidth || img.getBoundingClientRect().width;
  const h = img.clientHeight || img.getBoundingClientRect().height;
  if (!w || !h) return;
  c.width = w; c.height = h;
  const ctx = c.getContext("2d");
  ctx.clearRect(0, 0, w, h);
  maskDirty = false;
}

function resetBrush() {
  brushOn = false;
  maskDirty = false;
  const c = maskCanvas();
  c.classList.remove("active");
  document.getElementById("brush-toggle").classList.remove("on");
}

function toggleBrush() {
  brushOn = !brushOn;
  const c = maskCanvas();
  c.classList.toggle("active", brushOn);
  document.getElementById("brush-toggle").classList.toggle("on", brushOn);
  if (brushOn) sizeMaskCanvas();
  document.getElementById("brush-hint").textContent =
    brushOn ? "— ارسم فوق المنطقة المراد تعديلها" : "";
}

function clearMask() {
  const c = maskCanvas();
  c.getContext("2d").clearRect(0, 0, c.width, c.height);
  maskDirty = false;
}

// رسم بالفرشاة
(function setupBrushDrawing() {
  let drawing = false;
  function pos(e) {
    const c = maskCanvas();
    const r = c.getBoundingClientRect();
    const p = e.touches ? e.touches[0] : e;
    return { x: (p.clientX - r.left) * (c.width / r.width),
             y: (p.clientY - r.top) * (c.height / r.height) };
  }
  function dot(x, y) {
    const c = maskCanvas();
    const ctx = c.getContext("2d");
    const size = +document.getElementById("brush-size").value;
    ctx.fillStyle = "rgba(37,99,235,0.5)";
    ctx.beginPath();
    ctx.arc(x, y, size / 2, 0, Math.PI * 2);
    ctx.fill();
    maskDirty = true;
  }
  const attach = () => {
    const c = maskCanvas();
    if (!c || c._wired) return;
    c._wired = true;
    const start = (e) => { if (!brushOn) return; drawing = true; const q = pos(e); dot(q.x, q.y); e.preventDefault(); };
    const move = (e) => { if (!brushOn || !drawing) return; const q = pos(e); dot(q.x, q.y); e.preventDefault(); };
    const end = () => { drawing = false; };
    c.addEventListener("mousedown", start);
    c.addEventListener("mousemove", move);
    window.addEventListener("mouseup", end);
    c.addEventListener("touchstart", start, { passive: false });
    c.addEventListener("touchmove", move, { passive: false });
    c.addEventListener("touchend", end);
  };
  if (document.readyState !== "loading") attach();
  else document.addEventListener("DOMContentLoaded", attach);
})();

// تحويل رسم الفرشاة إلى قناع (أسود = ثابت، أبيض = يُعاد توليده)
function buildMaskBlob(cb) {
  const src = maskCanvas();
  const off = document.createElement("canvas");
  off.width = src.width; off.height = src.height;
  const octx = off.getContext("2d");
  octx.fillStyle = "#000";
  octx.fillRect(0, 0, off.width, off.height);
  const srcData = src.getContext("2d").getImageData(0, 0, src.width, src.height).data;
  const out = octx.getImageData(0, 0, off.width, off.height);
  const od = out.data;
  for (let i = 0; i < srcData.length; i += 4) {
    const white = srcData[i + 3] > 10;
    od[i] = od[i + 1] = od[i + 2] = white ? 255 : 0;
    od[i + 3] = 255;
  }
  octx.putImageData(out, 0, 0);
  off.toBlob(cb, "image/png");
}

async function regenerate() {
  const btn = document.getElementById("regen-btn");
  setLoading(btn, "جارِ التوليد…");
  const prompt = document.getElementById("modal-prompt").value;

  const finish = (img) => {
    if (img.status === "failed") {
      toast("فشل التوليد");
      const err = document.getElementById("modal-error");
      err.innerHTML = icon("alert") + `<span>فشل: ${escapeHtml(img.error || "")}</span>`;
      err.classList.remove("hidden");
    } else {
      toast("تم التوليد!");
      document.getElementById("modal-error").classList.add("hidden");
      document.getElementById("modal-result").src = `/media/result/${img.result}?t=${Date.now()}`;
      clearMask();
    }
    renderBatchImages();
    setBtn(btn, "refresh", "إعادة توليد");
  };

  try {
    if (maskDirty) {
      // إرسال قناع المنطقة
      buildMaskBlob(async (blob) => {
        const fd = new FormData();
        fd.append("prompt", prompt);
        fd.append("mask", blob, "mask.png");
        try { finish(await api(`/api/images/${currentImageId}/regenerate`, { method: "POST", body: fd })); }
        catch (e) { toast(e.message); setBtn(btn, "refresh", "إعادة توليد"); }
      });
    } else {
      const img = await api(`/api/images/${currentImageId}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
      finish(img);
    }
  } catch (e) {
    toast(e.message);
    setBtn(btn, "refresh", "إعادة توليد");
  }
}

// ===== شاشة: مكتبة القوالب =====
async function viewTemplates() {
  main.innerHTML = `
    <div class="page-title">مكتبة القوالب</div>
    <div class="page-sub">القالب = صورة مرجعية (تحدد الأسلوب) + برومبت ثابت</div>
    <div class="card">
      <h4>قالب جديد</h4>
      <label>اسم القالب</label>
      <input type="text" id="t-name" placeholder="مثال: خلفية بيضاء استوديو">
      <label>الصورة المرجعية (اختيارية)</label>
      <div class="file-drop" id="t-drop">${icon("upload")}<span>اختر الصورة المرجعية</span></div>
      <input type="file" id="t-ref" accept="image/*" class="hidden">
      <div id="t-ref-name" class="page-sub"></div>
      <label>البرومبت</label>
      <textarea id="t-prompt" placeholder="صف الأسلوب المطلوب تطبيقه على كل الصور…"></textarea>
      <button class="btn" onclick="createTemplate()">${icon("save")}<span>حفظ القالب</span></button>
    </div>
    <div id="templates-list" class="grid-cards"></div>`;

  const refInput = document.getElementById("t-ref");
  document.getElementById("t-drop").addEventListener("click", () => refInput.click());
  refInput.addEventListener("change", () => {
    document.getElementById("t-ref-name").textContent = refInput.files[0]?.name || "";
  });
  loadTemplates();
}

async function loadTemplates() {
  const templates = await api("/api/templates");
  const el = document.getElementById("templates-list");
  if (!templates.length) { el.innerHTML = `<div class="empty" style="grid-column:1/-1">لا توجد قوالب محفوظة بعد.</div>`; return; }
  el.innerHTML = templates.map((t) => `
    <div class="tile">
      <div class="thumb" style="${t.reference ? `background-image:url(/media/upload/${t.reference})` : ""}">
        ${t.reference ? "" : icon("bookmark")}</div>
      <div class="body">
        <h4>${escapeHtml(t.name)}</h4>
        <p>${escapeHtml(t.prompt)}</p>
        <div class="meta"><button class="btn danger sm" onclick="deleteTemplate(${t.id})">${icon("trash")}<span>حذف</span></button></div>
      </div>
    </div>`).join("");
}

async function createTemplate() {
  const name = document.getElementById("t-name").value.trim();
  const prompt = document.getElementById("t-prompt").value.trim();
  if (!name || !prompt) return toast("الاسم والبرومبت مطلوبان");
  const fd = new FormData();
  fd.append("name", name);
  fd.append("prompt", prompt);
  const ref = document.getElementById("t-ref").files[0];
  if (ref) fd.append("reference", ref);
  try {
    await api("/api/templates", { method: "POST", body: fd });
    toast("تم حفظ القالب");
    document.getElementById("t-name").value = "";
    document.getElementById("t-prompt").value = "";
    document.getElementById("t-ref-name").textContent = "";
    loadTemplates();
  } catch (e) { toast(e.message); }
}

async function deleteTemplate(tid) {
  await api(`/api/templates/${tid}`, { method: "DELETE" });
  loadTemplates();
}

// ===== شاشة: الإعدادات =====
function keyRow(label, id, envSet, keySet, ph) {
  if (envSet) {
    return `<label>${label}</label>
      <div class="env-key">${icon("check")}<span>مُدار من Railway (متغيّر بيئة) — آمن، ولا يظهر في المنصة</span></div>`;
  }
  return `<label>${label}</label>
    <input type="password" id="${id}" placeholder="${keySet ? "•••••••• (محفوظ)" : ph}">`;
}

async function viewSettings() {
  const s = await api("/api/settings");
  const anyEditable = !s.gpt_image_key_env || !s.nano_banana_key_env;
  main.innerHTML = `
    <div class="page-title">الإعدادات</div>
    <div class="page-sub">المفاتيح تُدار من Railway (متغيّرات بيئة) — الأأمن والموصى به</div>
    <div class="card">
      ${keyRow("مفتاح Nano Banana (Google Gemini API)", "s-nano", s.nano_banana_key_env, s.nano_banana_key_set, "AIza...")}
      ${keyRow("مفتاح GPT-Image (OpenAI API)", "s-gpt", s.gpt_image_key_env, s.gpt_image_key_set, "sk-...")}
      ${anyEditable ? `<button class="btn" onclick="saveSettings()">${icon("save")}<span>حفظ</span></button>` : ""}
    </div>
    <div class="card hint-card">
      <b>الطريقة الموصى بها — ضع المفاتيح في Railway (لا تظهر في المنصة):</b><br>
      Railway → الخدمة <code>web</code> → <b>Variables</b> → أضف:<br>
      • <code>OPENAI_API_KEY</code> = مفتاح GPT-Image (يبدأ بـ <code>sk-</code>)<br>
      • <code>GEMINI_API_KEY</code> = مفتاح Nano Banana (يبدأ بـ <code>AIza</code>)<br>
      بعد الحفظ تُعيد الخدمة النشر وتُقرأ المفاتيح تلقائيًا.<br><br>
      <b>مصادر المفاتيح:</b><br>
      • Gemini: <a href="https://aistudio.google.com/apikey" target="_blank">aistudio.google.com/apikey</a><br>
      • OpenAI: <a href="https://platform.openai.com/api-keys" target="_blank">platform.openai.com/api-keys</a>
    </div>`;
}

async function saveSettings() {
  const body = {};
  const nanoEl = document.getElementById("s-nano");
  const gptEl = document.getElementById("s-gpt");
  const nano = nanoEl ? nanoEl.value.trim() : "";
  const gpt = gptEl ? gptEl.value.trim() : "";
  if (nano) body.nano_banana_key = nano;
  if (gpt) body.gpt_image_key = gpt;
  await api("/api/settings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await refreshKeys();
  toast(HAS_KEY ? "تم حفظ المفتاح — التوليد الحقيقي جاهز" : "تم الحفظ");
  viewSettings();
}

function escapeHtml(s) {
  return (s || "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// إغلاق النافذة بالضغط خارجها
document.getElementById("overlay").addEventListener("click", (e) => {
  if (e.target.id === "overlay") closeModal();
});

// البداية
refreshKeys().then(() => navigate("batches"));
