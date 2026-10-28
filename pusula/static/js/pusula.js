/* Lezzet Pusulası — sayfa davranışları (JavaScript olmadan da formlar çalışır). */
(function () {
  "use strict";
  const $ = (s, k) => (k || document).querySelector(s);
  const $$ = (s, k) => Array.from((k || document).querySelectorAll(s));

  // ---------- filtre formu: değişince otomatik uygula ----------
  const form = $("#filtre-form");
  const gonderHemen = () => { if (form.requestSubmit) form.requestSubmit(); else form.submit(); };
  if (form) {
    let zaman;
    const gonder = () => { clearTimeout(zaman); zaman = setTimeout(gonderHemen, 350); };
    form.addEventListener("change", (e) => { if (e.target.name !== "q") gonder(); });
    const q = form.elements.q;
    if (q) q.addEventListener("input", () => { clearTimeout(zaman); zaman = setTimeout(gonderHemen, 700); });
    // Boş alanları adres çubuğuna taşımamak için
    form.addEventListener("submit", () => {
      Array.from(form.elements).forEach((el) => {
        if (el.name && el.type !== "checkbox" && (el.value === "" || (el.name === "ref" && el.value === "merkez"))) el.disabled = true;
      });
    });
    const sirala = $("[data-sirala]");
    if (sirala) sirala.addEventListener("change", gonderHemen);

    const konum = $("#konumum");
    if (konum && navigator.geolocation) {
      konum.addEventListener("click", () => {
        konum.textContent = "Konum alınıyor…";
        navigator.geolocation.getCurrentPosition((p) => {
          form.elements.ref.value = "konum";
          form.elements.lat.value = p.coords.latitude.toFixed(6);
          form.elements.lng.value = p.coords.longitude.toFixed(6);
          if (form.elements.sirala) form.elements.sirala.value = "mesafe";
          gonderHemen();
        }, () => { konum.textContent = "Konum alınamadı (izin verilmedi)"; }, { timeout: 10000 });
      });
    } else if (konum) { konum.hidden = true; }
    const merkez = $("#merkeze-don");
    if (merkez) merkez.addEventListener("click", () => {
      form.elements.ref.value = "merkez"; form.elements.lat.value = ""; form.elements.lng.value = ""; gonderHemen();
    });
  }

  // Mobilde filtre paneli kapalı başlasın (aktif filtre yoksa)
  const panel = $("#filtre-paneli");
  if (panel && window.matchMedia("(max-width: 960px)").matches && !/\(\d+\)/.test($("summary", panel).textContent)) {
    panel.open = false;
  }

  // ---------- liste / harita görünümü ----------
  const haritaKutu = $("#harita");
  const veriEl = $("#harita-verisi");
  let harita = null;
  const noktaSec = function (lat, lng) {
    form.elements.ref.value = "nokta"; form.elements.lat.value = lat.toFixed(6); form.elements.lng.value = lng.toFixed(6);
    if (form.elements.sirala) form.elements.sirala.value = "mesafe";
    gonderHemen();
  };
  noktaSec.aktif = false;
  function haritaAc() {
    if (!haritaKutu) return;
    haritaKutu.hidden = false;
    if (!harita && veriEl) harita = window.pusulaHarita(haritaKutu, JSON.parse(veriEl.textContent), { noktaSec: noktaSec });
    if (harita) setTimeout(harita.yenile, 50);
  }
  function gorunumSec(g) {
    $$("[data-gorunum]").forEach((x) => x.setAttribute("aria-pressed", String(x.dataset.gorunum === g)));
    if (g === "harita") haritaAc(); else if (haritaKutu) haritaKutu.hidden = true;
    try { localStorage.setItem("pusula-gorunum", g); } catch (e) { /* gizli sekme */ }
  }
  $$("[data-gorunum]").forEach((b) => b.addEventListener("click", () => gorunumSec(b.dataset.gorunum)));
  try { if (localStorage.getItem("pusula-gorunum") === "harita") gorunumSec("harita"); } catch (e) { /* yok say */ }
  const secDugme = $("#nokta-sec");
  if (secDugme) secDugme.addEventListener("click", () => {
    gorunumSec("harita");
    noktaSec.aktif = true;
    secDugme.textContent = "Şimdi haritada bir noktaya tıkla";
    haritaKutu.scrollIntoView({ behavior: "smooth", block: "center" });
  });

  // Her zaman görünen haritalar (mekan sayfası, gezi listesi)
  $$("[data-harita-hemen]").forEach((kutu) => {
    const v = document.getElementById(kutu.dataset.veri);
    if (v) window.pusulaHarita(kutu, JSON.parse(v.textContent));
  });

  // ---------- gezi listesi düğmeleri ----------
  document.addEventListener("submit", (e) => {
    const f = e.target;
    if (!f.classList || !f.classList.contains("liste-form")) return;
    e.preventDefault();
    fetch(f.action, { method: "POST", headers: { "X-Requested-With": "fetch" }, credentials: "same-origin" })
      .then((r) => r.json())
      .then((v) => {
        const b = $("button", f);
        b.setAttribute("aria-pressed", String(v.ekli));
        b.textContent = v.ekli ? "Listemde" : "Listeme ekle";
        const sayac = $("#liste-sayac");
        if (sayac) { sayac.textContent = v.adet; sayac.hidden = v.adet === 0; }
      })
      .catch(() => f.submit());
  });

  // ---------- karşılaştırma ----------
  const kutular = $$(".karsilastir-kutu");
  const cubuk = $("#karsilastir-cubugu");
  function karsilastirGuncelle() {
    const secili = kutular.filter((k) => k.checked);
    kutular.forEach((k) => { k.disabled = !k.checked && secili.length >= 3; });
    if (cubuk) { cubuk.hidden = secili.length < 2; $("span", cubuk).textContent = secili.length; }
  }
  kutular.forEach((k) => k.addEventListener("change", karsilastirGuncelle));
  karsilastirGuncelle();

  // ---------- ağırlık kaydırıcıları ----------
  $$(".kaydirici input[type=range]").forEach((r) => {
    const cikti = r.parentElement.querySelector("output");
    r.addEventListener("input", () => { cikti.textContent = (r.hasAttribute("data-yuzde") ? "%" : "") + r.value; });
  });

  // ---------- ana ekrana eklenebilme (PWA) ----------
  if ("serviceWorker" in navigator && (location.protocol === "https:" || location.hostname === "127.0.0.1" || location.hostname === "localhost")) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }

  // ---------- arka plan işi takibi ----------
  const isKutu = $("#is-kutu");
  if (isKutu) {
    const cubukEl = $(".ilerleme span", isKutu), mesaj = $(".is-mesaj", isKutu), log = $(".is-log", isKutu);
    const sorgula = () => fetch(isKutu.dataset.api).then((r) => r.json()).then((d) => {
      cubukEl.style.width = d.ilerleme + "%";
      $(".ilerleme", isKutu).setAttribute("aria-valuenow", d.ilerleme);
      mesaj.textContent = d.mesaj || "Başlıyor…";
      if (log) { log.textContent = d.log || ""; log.scrollTop = log.scrollHeight; }
      if (d.durum === "bitti" && d.sonuc_url) { window.location = d.sonuc_url; return; }
      if (d.durum === "hata") { $(".hata-kutu", isKutu).hidden = false; $(".hata-kutu span", isKutu).textContent = d.mesaj; return; }
      setTimeout(sorgula, 1200);
    }).catch(() => setTimeout(sorgula, 3000));
    sorgula();
  }
})();
