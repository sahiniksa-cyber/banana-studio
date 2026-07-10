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
  x: '<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>',
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
  stopPoll();
  setActive(view);
  if (view === "batches") viewBatches();
  else if (view === "new-batch") viewNewBatch();
  else if (view === "templates") viewTemplates();
  else if (view === "settings") viewSettings();
}

function fmtDate(ts) {
  if (!ts) return "";
  try { return new Date(ts * 1000).toLocaleString("ar", { dateStyle: "medium", timeStyle: "short" }); }
  catch (e) { return ""; }
}
function modeLabel(b) {
  if (b.lock_subject) return "قفل المنتج";
  if (b.strict) return "قالب ثابت";
  return "طبيعي";
}

// ===== شاشة: المكتبة (كل التصاميم مع برومبتها وخياراتها) =====
async function viewBatches() {
  main.innerHTML = `<div class="page-title">المكتبة</div>
    <div class="page-sub">كل التصاميم التي أنشأتها — اضغط أيًّا منها لرؤية البرومبت والخيارات وإعادة الاستخدام</div>
    <div id="batches-list"><div class="empty">جارِ التحميل…</div></div>`;
  const batches = await api("/api/batches");
  const el = document.getElementById("batches-list");
  if (!batches.length) {
    el.innerHTML = `<div class="empty">
      <div class="big">${icon("inbox")}</div>
      <p>المكتبة فارغة. ابدأ بإنشاء أول تصميم.</p>
      <button class="btn" onclick="navigate('new-batch')">${icon("plus")}<span>أنشئ أول تصميم</span></button></div>`;
    return;
  }
  el.className = "grid-cards";
  el.innerHTML = batches.map((b) => `
    <div class="tile" onclick="openBatch(${b.id})">
      <div class="thumb">${icon("image")} ${b.total} صورة</div>
      <div class="body">
        <h4>${escapeHtml(b.name)}</h4>
        <p>${b.prompt ? escapeHtml(b.prompt) : "قالب مرجعي (بدون برومبت)"}</p>
        <div class="meta">
          <span class="badge">${escapeHtml(modeLabel(b))}</span>
          <span>${b.aspect || "1:1"}</span> ·
          <span>${b.done}/${b.total} جاهزة</span>
          <span class="badge ${b.status === "done" ? "done" : "running"}"><span class="dot"></span>${statusLabel(b.status)}</span>
        </div>
        <div class="meta" style="margin-top:4px;color:var(--muted-2)">${fmtDate(b.created_at)}</div>
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
// ===== نظام اختيار الصور مع معاينة مصغّرة وحذف =====
const PICK = {};  // inputId -> { files:[], previewId, multiple }

function wireDrop(dropId, inputId, previewId, multiple) {
  const drop = document.getElementById(dropId);
  const input = document.getElementById(inputId);
  PICK[inputId] = { files: [], previewId, multiple: !!multiple };

  drop.addEventListener("click", () => input.click());
  ["dragenter", "dragover"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("dragover"); })
  );
  ["dragleave", "dragend", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("dragover"); })
  );
  drop.addEventListener("drop", (e) => {
    if (e.dataTransfer && e.dataTransfer.files.length) addPicked(inputId, e.dataTransfer.files);
  });
  input.addEventListener("change", () => addPicked(inputId, input.files));
}

function _isImage(f) {
  return (f.type || "").startsWith("image/") ||
    /\.(png|jpe?g|webp|heic|heif|bmp|tiff?|gif|avif)$/i.test(f.name || "");
}
function addPicked(inputId, fileList) {
  const st = PICK[inputId];
  if (!st) return;
  const incoming = Array.from(fileList).filter(_isImage);
  st.files = st.multiple ? st.files.concat(incoming) : incoming.slice(0, 1);
  _syncPick(inputId);
  renderPick(inputId);
}
function removePicked(inputId, idx) {
  const st = PICK[inputId];
  if (!st) return;
  st.files.splice(idx, 1);
  _syncPick(inputId);
  renderPick(inputId);
}
function _syncPick(inputId) {
  const st = PICK[inputId];
  const dt = new DataTransfer();
  st.files.forEach((f) => dt.items.add(f));
  document.getElementById(inputId).files = dt.files;  // لا يُطلق حدث change
}
function renderPick(inputId) {
  const st = PICK[inputId];
  const el = document.getElementById(st.previewId);
  if (!el) return;
  el.className = "thumbs";
  el.innerHTML = st.files.map((f, i) => `
    <div class="thumb-item">
      <img src="${URL.createObjectURL(f)}" alt="">
      <button class="thumb-x" onclick="removePicked('${inputId}',${i})" title="حذف">${icon("x")}</button>
    </div>`).join("");
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
    الجودة الأعلى تعطي تفاصيل أدق (وتكلفة أعلى قليلًا).</div>`;
}
function lockToggle(id) {
  return `<label class="check-row" style="margin:6px 0 16px">
      <input type="checkbox" id="${id}">
      <span><b>قفل شكل المنتج</b> (اختياري) — فعّله فقط للمنتجات الصغيرة اللي تبيها
      <b>مطابقة 100%</b>. <br>الافتراضي: مظهر <b>طبيعي كأنه من ChatGPT</b> (الأمر يُطبَّق كاملًا) —
      وهو الأنسب للمنتجات اللي تملأ الصورة.</span>
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
          <div class="file-drop" id="d-drop">${icon("upload")}<span>اسحب صورة المنتج هنا أو اضغط للاختيار</span></div>
          <input type="file" id="d-sample" accept="image/*" class="hidden">
          <div id="d-sample-prev"></div>

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
      <div class="file-drop" id="d-batch-drop">${icon("upload")}<span>اسحب صور المنتجات هنا أو اضغط للاختيار</span></div>
      <input type="file" id="d-batch-files" multiple accept="image/*" class="hidden">
      <div id="d-batch-prev"></div>
      <button class="btn" id="d-run" onclick="designRun()">${icon("play")}<span>ابدأ التوليد على الكل</span></button>
    </div>`;

  design.model = "gpt_image";
  wireChoicePills("d-aspect", design, "aspect", "1:1");
  wireChoicePills("d-quality", design, "quality", "high");
  wireDrop("d-drop", "d-sample", "d-sample-prev", false);
  wireDrop("d-batch-drop", "d-batch-files", "d-batch-prev", true);

  // إعادة استخدام إعدادات دفعة سابقة (إن وُجدت)
  if (PREFILL) {
    document.getElementById("d-prompt").value = PREFILL.prompt;
    setChoice("d-aspect", design, "aspect", PREFILL.aspect);
    setChoice("d-quality", design, "quality", PREFILL.quality);
    document.getElementById("d-lock").checked = PREFILL.lock;
    PREFILL = null;
  }
}

function setChoice(id, stateObj, prop, val) {
  document.querySelectorAll(`#${id} .pill`).forEach((p) => {
    const on = p.dataset.val === val;
    p.classList.toggle("active", on);
    if (on) stateObj[prop] = val;
  });
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
  Object.assign(refMode, { model: "gpt_image" });
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
        <label>الصور المرجعية (تقدر تضيف عدة صور — يفهم الأسلوب المشترك بينها)</label>
        <div class="file-drop" id="r-ref-drop">${icon("upload")}<span>اسحب صور الأسلوب المرجعية هنا أو اضغط للاختيار</span></div>
        <input type="file" id="r-ref" multiple accept="image/*" class="hidden">
        <div id="r-ref-prev"></div>
      </div>

      <label>المقاس / نسبة الأبعاد</label>
      ${choicePills("r-aspect", ASPECTS, "1:1", true)}

      <label>الجودة</label>
      ${choicePills("r-quality", QUALITIES, "high")}
      ${qualityNote("r-qnote")}

      ${lockToggle("r-lock")}

      <label>صور المنتجات (20-50 صورة)</label>
      <div class="file-drop" id="r-drop">${icon("upload")}<span>اسحب صور المنتجات هنا أو اضغط للاختيار</span></div>
      <input type="file" id="r-files" multiple accept="image/*" class="hidden">
      <div id="r-prev"></div>

      <button class="btn" id="r-run" onclick="refRun()">${icon("play")}<span>ابدأ التوليد على الكل</span></button>
    </div>`;

  refMode.model = "gpt_image";
  wireChoicePills("r-aspect", refMode, "aspect", "1:1");
  wireChoicePills("r-quality", refMode, "quality", "high");
  wireDrop("r-ref-drop", "r-ref", "r-ref-prev", true);
  wireDrop("r-drop", "r-files", "r-prev", true);
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
  const refFiles = document.getElementById("r-ref").files;
  if (!tpl && !refFiles.length) return toast("اختر قالبًا محفوظًا أو ارفع صورة مرجعية");

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
  else for (const f of refFiles) fd.append("reference", f);  // عدة مراجع
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
  ensurePoll();
}

function ensurePoll() {
  if (!pollTimer) pollTimer = setInterval(renderBatchImages, 2500);
}
function stopPoll() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function renderBatch() {
  const b = await api(`/api/batches/${currentBatchId}`);
  main.innerHTML = `
    <div class="batch-head">
      <div>
        <div class="page-title" style="margin-bottom:2px">${escapeHtml(b.name)}</div>
        <div class="page-sub" style="margin-bottom:0">القالب: ${escapeHtml(b.template_name || "بدون")} ·
          ${modelLabel(b.model)}</div>
      </div>
      <div class="batch-actions">
        <button class="btn ghost" onclick="navigate('batches')">${icon("arrowRight")}<span>رجوع</span></button>
        <button class="btn ghost" onclick="reuseBatch(${b.id})">${icon("edit")}<span>صفحة البرومبت</span></button>
        <button class="btn ghost" onclick="document.getElementById('add-images-input').click()">${icon("plus")}<span>أضف صور</span></button>
        <button class="btn" onclick="downloadAllImages(${b.id})">${icon("download")}<span>تحميل الصور</span></button>
        <button class="btn danger" onclick="deleteBatch(${b.id})">${icon("trash")}<span>حذف</span></button>
      </div>
    </div>
    <input type="file" id="add-images-input" multiple accept="image/*" class="hidden"
      onchange="addImagesToBatch(${b.id}, this.files)">
    <div class="card recipe">
      <div class="recipe-head">
        <b>الوصفة (البرومبت + الخيارات)</b>
        <div class="row" style="flex:0">
          <button class="btn ghost sm" onclick='copyPrompt(${JSON.stringify(b.prompt || "")})'>${icon("copy")}<span>نسخ البرومبت</span></button>
          <button class="btn sm" onclick="reuseBatch(${b.id})">${icon("refresh")}<span>دفعة جديدة بنفس الإعدادات</span></button>
        </div>
      </div>
      <div class="recipe-prompt">${b.prompt ? escapeHtml(b.prompt) : "— قالب مرجعي بدون برومبت —"}</div>
      <div class="recipe-tags">
        <span class="badge">${icon("cpu")} ${modelLabel(b.model)}</span>
        <span class="badge">المقاس: ${b.aspect || "1:1"}</span>
        <span class="badge">الجودة: ${qualityLabel(b.quality)}</span>
        <span class="badge">الوضع: ${escapeHtml(modeLabel(b))}</span>
        <span class="badge">القالب: ${escapeHtml(b.template_name || "بدون")}</span>
        <span class="badge">${fmtDate(b.created_at)}</span>
      </div>
    </div>
    <div class="image-grid" id="img-grid"></div>`;
  renderBatchImages();
}

async function addImagesToBatch(bid, fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  const fd = new FormData();
  for (const f of files) fd.append("images", f);
  try {
    const r = await api(`/api/batches/${bid}/add-images`, { method: "POST", body: fd });
    toast(`تمت إضافة ${r.added} صورة — تُعالج بنفس البرومبت`);
    if (currentBatchId === bid) { ensurePoll(); renderBatchImages(); }
  } catch (e) { toast(e.message); }
}

function qualityLabel(q) { return { high: "عالية", medium: "متوسطة", low: "سريعة" }[q] || q || "عالية"; }

// تحميل كل صورة على حدة (بدون ملف مضغوط)
async function downloadAllImages(bid) {
  const b = await api(`/api/batches/${bid}`);
  const done = b.images.filter((i) => i.result);
  if (!done.length) return toast("لا توجد صور جاهزة للتحميل");
  toast(`جارِ تحميل ${done.length} صورة…`);
  const base = (b.name || "صورة").replace(/[\\/:*?"<>|]/g, "_");
  for (let i = 0; i < done.length; i++) {
    const a = document.createElement("a");
    a.href = `/media/result/${done[i].result}`;
    a.download = `${base}-${i + 1}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    await new Promise((r) => setTimeout(r, 500)); // فاصل بسيط بين كل تحميل
  }
}

async function copyPrompt(text) {
  try { await navigator.clipboard.writeText(text || ""); toast("تم نسخ البرومبت"); }
  catch (e) { toast("تعذّر النسخ"); }
}

// فتح صفحة البرومبت لدفعة سابقة: بالصورة الأساسية + البرومبت + كل الإعدادات
let PREFILL = null;
async function reuseBatch(bid) {
  const b = await api(`/api/batches/${bid}`);
  PREFILL = { prompt: b.prompt || "", aspect: b.aspect || "1:1", quality: b.quality || "high", lock: !!b.lock_subject };
  setActive("new-batch");
  viewDesignMode();
  // عرض الصورة الأساسية (أول مرجع) وتمكين الاعتماد المباشر
  if (b.reference) {
    const firstRef = String(b.reference).split(",")[0].trim();
    design.resultName = firstRef;
    design.prompt = b.prompt || "";
    document.getElementById("d-preview").innerHTML =
      `<img src="/media/ref/${firstRef}?t=${Date.now()}" alt="">`;
    document.getElementById("d-actions").classList.remove("hidden");
  }
  toast("عدّل الإعدادات أو البرومبت، ثم ولّد من جديد أو اعتمد");
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
  // نستمر بالتحديث ما دامت أي صورة قيد المعالجة (يشمل التعديلات بعد اكتمال الدفعة)
  const anyRunning = b.images.some((i) => i.status === "running" || i.status === "queued");
  if (!anyRunning) stopPoll();
}

async function deleteBatch(bid) {
  if (!confirm("حذف هذه الدفعة وكل صورها؟")) return;
  stopPoll();
  await api(`/api/batches/${bid}`, { method: "DELETE" });
  toast("تم حذف الدفعة");
  navigate("batches");
}

// ===== نافذة التعديل =====
// حالة أدوات التحديد
let brushOn = false;
let maskDirty = false;
let brushTool = "brush";  // brush | rect | erase

function setTool(t) {
  brushTool = t;
  document.querySelectorAll("#tool-group .tool").forEach((b) =>
    b.classList.toggle("active", b.dataset.tool === t)
  );
  if (!brushOn) toggleBrush();  // تفعيل وضع التحديد تلقائيًا
  const hints = { brush: "ارسم فوق المنطقة", rect: "اسحب لرسم مستطيل", erase: "امسح من التحديد" };
  document.getElementById("brush-hint").textContent = "— " + (hints[t] || "");
}

function selectAllMask() {
  const c = maskCanvas();
  if (!brushOn) toggleBrush();
  const ctx = c.getContext("2d");
  ctx.globalCompositeOperation = "source-over";
  ctx.fillStyle = "rgba(37,99,235,0.5)";
  ctx.fillRect(0, 0, c.width, c.height);
  maskDirty = true;
}

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
  setBtn(document.getElementById("regen-btn"), "refresh", "إعادة توليد");
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
  brushTool = "brush";
  const c = maskCanvas();
  c.classList.remove("active");
  document.getElementById("brush-toggle").classList.remove("on");
  document.getElementById("brush-hint").textContent = "";
  document.querySelectorAll("#tool-group .tool").forEach((b) =>
    b.classList.toggle("active", b.dataset.tool === "brush")
  );
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

// رسم أدوات التحديد (فرشاة / مستطيل / ممحاة)
(function setupBrushDrawing() {
  let drawing = false;
  let rectStart = null;
  let rectSnap = null;
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
    ctx.globalCompositeOperation = brushTool === "erase" ? "destination-out" : "source-over";
    ctx.fillStyle = "rgba(37,99,235,0.5)";
    ctx.beginPath();
    ctx.arc(x, y, size / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.globalCompositeOperation = "source-over";
    maskDirty = true;
  }
  function drawRect(a, b) {
    const c = maskCanvas();
    const ctx = c.getContext("2d");
    ctx.putImageData(rectSnap, 0, 0);            // استعادة ما قبل السحب
    ctx.fillStyle = "rgba(37,99,235,0.5)";
    ctx.fillRect(Math.min(a.x, b.x), Math.min(a.y, b.y), Math.abs(b.x - a.x), Math.abs(b.y - a.y));
  }
  const attach = () => {
    const c = maskCanvas();
    if (!c || c._wired) return;
    c._wired = true;
    const start = (e) => {
      if (!brushOn) return;
      drawing = true; e.preventDefault();
      const q = pos(e);
      if (brushTool === "rect") {
        rectStart = q;
        rectSnap = c.getContext("2d").getImageData(0, 0, c.width, c.height);
      } else dot(q.x, q.y);
    };
    const move = (e) => {
      if (!brushOn || !drawing) return;
      e.preventDefault();
      const q = pos(e);
      if (brushTool === "rect") drawRect(rectStart, q);
      else dot(q.x, q.y);
    };
    const end = () => {
      if (drawing && brushTool === "rect") maskDirty = true;
      drawing = false; rectStart = null; rectSnap = null;
    };
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

// تعديل بالخلفية: يبدأ التعديل ثم يغلق النافذة فورًا حتى تكمل التصفح وتعدّل غيرها
async function regenerate() {
  const imageId = currentImageId;
  const prompt = document.getElementById("modal-prompt").value;
  const useMask = maskDirty;
  const maskBlob = useMask ? await new Promise((res) => buildMaskBlob(res)) : null;

  closeModal();          // حرّر المستخدم فورًا
  ensurePoll();          // المعرض يحدّث نفسه ويُظهر "يعالج…"
  markCellRunning(imageId);
  toast("بدأ التعديل في الخلفية…");

  try {
    let img;
    if (maskBlob) {
      const fd = new FormData();
      fd.append("prompt", prompt);
      fd.append("mask", maskBlob, "mask.png");
      img = await api(`/api/images/${imageId}/regenerate`, { method: "POST", body: fd });
    } else {
      img = await api(`/api/images/${imageId}/regenerate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });
    }
    if (currentBatchId) renderBatchImages();
    toast(img.status === "failed" ? "فشل تعديل صورة" : "تم تعديل صورة ✓");
  } catch (e) {
    toast(e.message);
    if (currentBatchId) renderBatchImages();
  }
}

// تعليم الخلية كمعالجة فورًا (قبل أول دورة تحديث)
function markCellRunning(iid) {
  const grid = document.getElementById("img-grid");
  if (!grid) return;
  const cell = grid.querySelector(`.img-cell[onclick="openImage(${iid})"]`);
  if (cell && !cell.querySelector(".spin")) {
    const s = document.createElement("div");
    s.className = "spin";
    s.innerHTML = `${spinner()} يعالج…`;
    cell.appendChild(s);
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
      <div class="file-drop" id="t-drop">${icon("upload")}<span>اسحب الصورة المرجعية هنا أو اضغط للاختيار</span></div>
      <input type="file" id="t-ref" accept="image/*" class="hidden">
      <div id="t-ref-prev"></div>
      <label>البرومبت</label>
      <textarea id="t-prompt" placeholder="صف الأسلوب المطلوب تطبيقه على كل الصور…"></textarea>
      <button class="btn" onclick="createTemplate()">${icon("save")}<span>حفظ القالب</span></button>
    </div>
    <div id="templates-list" class="grid-cards"></div>`;

  wireDrop("t-drop", "t-ref", "t-ref-prev", false);
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
    if (PICK["t-ref"]) { PICK["t-ref"].files = []; _syncPick("t-ref"); renderPick("t-ref"); }
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

// منع المتصفح من فتح الصورة عند إفلاتها خارج منطقة الرفع
["dragover", "drop"].forEach((ev) =>
  window.addEventListener(ev, (e) => {
    if (!e.target.closest || !e.target.closest(".file-drop")) e.preventDefault();
  })
);

// إغلاق النافذة بالضغط خارجها
document.getElementById("overlay").addEventListener("click", (e) => {
  if (e.target.id === "overlay") closeModal();
});

// البداية
refreshKeys().then(() => navigate("batches"));
