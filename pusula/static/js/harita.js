/* Harita: demo modunda Leaflet + OpenStreetMap, gerçek veride Google Maps.
   (Google Places verisi Google dışı haritada gösterilemez.) */
(function () {
  "use strict";
  const bekleyenler = [];

  function kacis(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, (c) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
    })[c]);
  }
  function puanYazi(p) { return p == null ? "–" : String(p).replace(".", ","); }
  function isaretHtml(n, secili) {
    return '<div class="isaret ' + kacis(n.renk) + (secili ? " secili" : "") + '"><span>' +
      puanYazi(n.puan) + "</span></div>";
  }
  function balonHtml(n) {
    return '<a href="' + kacis(n.url) + '"><b>' + kacis(n.kat) + " " + kacis(n.ad) + "</b></a><br>" +
      "Pusula " + puanYazi(n.puan) + (n.google ? " · ★ " + puanYazi(n.google) : "") +
      (n.fiyat ? " · " + kacis(n.fiyat) : "");
  }

  function leafletKur(kutu, veri, secenek) {
    if (!window.L) {
      kutu.innerHTML = '<div class="harita-yok"><p>Harita kütüphanesi yüklenemedi. İnternet bağlantınızı kontrol edin.</p></div>';
      return null;
    }
    const harita = L.map(kutu, { scrollWheelZoom: false }).setView(veri.merkez, 13);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19, attribution: "&copy; OpenStreetMap katkıcıları"
    }).addTo(harita);
    const sinirlar = [];
    veri.noktalar.forEach(function (n, i) {
      const ikon = L.divIcon({ className: "", html: isaretHtml(n, veri.yakin && i === 0),
        iconSize: [34, 34], iconAnchor: [17, 40], popupAnchor: [0, -36] });
      L.marker([n.lat, n.lng], { icon: ikon, title: n.ad }).addTo(harita).bindPopup(balonHtml(n));
      sinirlar.push([n.lat, n.lng]);
    });
    if (veri.ref) {
      L.marker(veri.ref, { icon: L.divIcon({ className: "", html: '<div class="isaret ref"><span>⌂</span></div>',
        iconSize: [34, 34], iconAnchor: [17, 40] }), title: "Uzaklık bu noktaya göre" }).addTo(harita);
      sinirlar.push(veri.ref);
    }
    if (veri.rota && veri.noktalar.length > 1) {
      L.polyline(veri.noktalar.map((n) => [n.lat, n.lng]), { color: "#1f4ba5", weight: 3, dashArray: "6 6" }).addTo(harita);
    }
    if (sinirlar.length > 1) harita.fitBounds(sinirlar, { padding: [30, 30], maxZoom: 15 });
    harita.on("click", function (e) {
      if (secenek.noktaSec && secenek.noktaSec.aktif) secenek.noktaSec(e.latlng.lat, e.latlng.lng);
    });
    return { yenile: () => harita.invalidateSize() };
  }

  function googleKur(kutu, veri, secenek) {
    const harita = new google.maps.Map(kutu, {
      center: { lat: veri.merkez[0], lng: veri.merkez[1] }, zoom: 13,
      mapId: kutu.dataset.mapId || "DEMO_MAP_ID", gestureHandling: "cooperative"
    });
    const sinir = new google.maps.LatLngBounds();
    const balon = new google.maps.InfoWindow();
    veri.noktalar.forEach(function (n, i) {
      const tut = document.createElement("div");
      tut.innerHTML = isaretHtml(n, veri.yakin && i === 0);
      const isaret = new google.maps.marker.AdvancedMarkerElement({
        map: harita, position: { lat: n.lat, lng: n.lng }, content: tut.firstChild, title: n.ad });
      isaret.addListener("click", function () {
        balon.setContent(balonHtml(n));
        balon.open({ anchor: isaret, map: harita });
      });
      sinir.extend({ lat: n.lat, lng: n.lng });
    });
    if (veri.ref) {
      const tut = document.createElement("div");
      tut.innerHTML = '<div class="isaret ref"><span>⌂</span></div>';
      new google.maps.marker.AdvancedMarkerElement({ map: harita, position: { lat: veri.ref[0], lng: veri.ref[1] },
        content: tut.firstChild, title: "Uzaklık bu noktaya göre" });
      sinir.extend({ lat: veri.ref[0], lng: veri.ref[1] });
    }
    if (veri.rota && veri.noktalar.length > 1) {
      new google.maps.Polyline({ map: harita, path: veri.noktalar.map((n) => ({ lat: n.lat, lng: n.lng })),
        strokeColor: "#1f4ba5", strokeWeight: 3 });
    }
    if (veri.noktalar.length > 1) harita.fitBounds(sinir, 40);
    harita.addListener("click", function (e) {
      if (secenek.noktaSec && secenek.noktaSec.aktif) secenek.noktaSec(e.latLng.lat(), e.latLng.lng());
    });
    return { yenile: function () {} };
  }

  window.pusulaHarita = function (kutu, veri, secenek) {
    secenek = secenek || {};
    if (!kutu || !veri) return null;
    const mod = kutu.dataset.mod;
    if (mod === "leaflet") return leafletKur(kutu, veri, secenek);
    if (mod === "google") {
      if (window.google && google.maps && google.maps.marker) return googleKur(kutu, veri, secenek);
      bekleyenler.push([kutu, veri, secenek]);
    }
    return null;
  };
  window.pusulaGoogleHazir = function () {
    bekleyenler.splice(0).forEach((a) => googleKur(a[0], a[1], a[2]));
  };
})();
