"""Uygulamanın beyni: istemciyi dinler, analiz eder ve arayüze verilecek durumu hazırlar.
Arayüz (ui/index.html) bu durumu her saniye sorar ve ekrana çizer."""
import json
import os
import sys
import threading
import time

from .analiz import profil_cikar, rolleri_tahmin_et
from .build import arketip_bul, build_olustur
from .runler import RunDB, run_olustur
from .champs import KOK, ROL_AD, ROLLER, SINIF_AD, SampiyonDB, rol_coz
from .buyuler import BUYU, SICRA, buyu_oner
from .gecmis import Gecmis, sik_hatalar
from .oneri import sampiyon_oner
from .plan import ban_oner, mac_plani
from .veri import DD, DataDragon, EsyaDB

AYAR_YOLU = os.path.join(KOK, "config.json")
VARSAYILAN_AYAR = {
    "dil": "tr_TR", "varsayilan_rol": "mid",
    "havuz": {r: [] for r in ROLLER}, "sadece_havuz": False,
    "oneri_sayisi": 5, "secince_de_oner": True, "item_set_aktar": True, "run_aktar": True,
    "buyu_aktar": True,
    "github_depo": "gurkan-tr/Lol-Asistan", "github_anahtar": "",
    "lol_klasoru": "",
}


def ayar_yukle():
    ayar = json.loads(json.dumps(VARSAYILAN_AYAR))
    try:
        with open(AYAR_YOLU, encoding="utf-8") as f:
            ayar.update(json.load(f))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    return ayar


def ayar_yaz(ayar):
    with open(AYAR_YOLU, "w", encoding="utf-8") as f:
        json.dump(ayar, f, ensure_ascii=False, indent=2)


class Motor:
    def __init__(self):
        self.ayar = ayar_yukle()
        self.db = self.dd = self.esya = self.rundb = None
        self._lcu = None
        self._sayfalar = {}        # alias -> RunSayfasi (son analizde hesaplanan)
        self._buyuler = {}         # alias -> BuyuOnerisi
        self._sicra_d = False
        self.gecmis = Gecmis()
        self.gecmis_durum = ""     # "Maç geçmişi okunuyor 12/40" gibi
        self._gecmis_calisiyor = False
        self._son_secim = None     # seçim ekranında hazırlanan son plan (maç sırasında gösterilir)
        self._kilit = threading.Lock()
        self._surum = 0
        self._durum = {"ekran": "baglaniyor", "baslik": "Hazırlanıyor",
                       "mesaj": "Güncel yama verileri indiriliyor…"}
        self._canli = dict(self._durum)
        self.elle = False          # demo / elle giriş ekranda mı
        self.baglanti = False
        self._baglam = None        # son analizin bağlamı (alternatif build için)

    # ---------------- durum yayını ----------------
    def _yayinla(self, d, canli=True):
        d = dict(d)
        d["baglanti"] = self.baglanti
        d["yama"] = self.dd.surum if self.dd else None
        d["elle"] = not canli
        if canli:
            self._canli = d
            if self.elle:
                return
        with self._kilit:
            self._surum += 1
            d["surum"] = self._surum
            self._durum = d

    def durum(self):
        with self._kilit:
            return self._durum

    def canliya_don(self):
        self.elle = False
        self._yayinla(self._canli)

    # ---------------- veri ----------------
    def hazirla(self):
        self.db = SampiyonDB()
        self.dd = DataDragon(self.ayar.get("dil", "tr_TR"))
        self.db.id_esle(self.dd.sampiyon_kayitlari())
        self.esya = EsyaDB(self.dd)
        self.rundb = RunDB(self.dd)
        self.gecmis.son_yukle()

    def _ikon_s(self, s):
        if not s or not self.dd or not self.dd.surum:
            return None
        return f"{DD}/cdn/{self.dd.surum}/img/champion/{s.alias}.png"

    def _ikon_e(self, iid):
        if not iid or not self.dd or not self.dd.surum or self.esya.cevrimdisi:
            return None
        return f"{DD}/cdn/{self.dd.surum}/img/item/{iid}.png"

    def _s(self, s):
        if not s:
            return None
        return {"alias": s.alias, "ad": s.ad, "ikon": self._ikon_s(s),
                "sinif": SINIF_AD.get(s.sinif, s.sinif), "hasar": s.hasar}

    def _run_json(self, sayfa):
        if not sayfa:
            return None
        return {"ana": sayfa.ana, "yan": sayfa.yan, "kilit": sayfa.kilit, "ana_runler": sayfa.ana_runler,
                "yan_runler": sayfa.yan_runler, "parcalar": sayfa.parcalar, "nedenler": sayfa.nedenler,
                "uygulanabilir": sayfa.uygulanabilir}

    def _sayfa(self, s, rol, profil, rakip):
        sayfa = run_olustur(s, arketip_bul(s, rol), rol, profil, rakip, self.rundb)
        self._sayfalar[s.alias] = sayfa
        return sayfa

    def _buyu_json(self, b):
        if not b:
            return None
        v = self.dd.surum if self.dd else None
        j = lambda i: {"id": i, "ad": BUYU[i][0], "ikon": f"{DD}/cdn/{v}/img/spell/{BUYU[i][1]}.png" if v else None}
        return {"d": j(b.idler()[0]), "f": j(b.idler()[1]), "neden": b.neden}

    def _buyu(self, s, rol, profil, rakip):
        b = buyu_oner(s, arketip_bul(s, rol), rol, profil, rakip, self._sicra_d)
        self._buyuler[s.alias] = b
        return b

    # ---------- kişisel istatistik yardımcıları ----------
    def _alias_sozluk(self, idli):
        out = {}
        for cid, v in idli.items():
            c = self.db.id_ile(cid)
            if c:
                out[c.alias] = v
        return out

    def _kisisel(self):
        if not self.gecmis.maclar:
            return {}, {}, {}
        return (self._alias_sozluk(self.gecmis.sampiyon_istatistik()),
                self._alias_sozluk(self.gecmis.koridor_rakibi_istatistik()),
                self._alias_sozluk(self.gecmis.rakip_istatistik()))

    def _ana_sampiyonlar(self, rol, ustalik=None, kisisel=None):
        """Bu koridordaki ana şampiyonların: favoriler, en çok oynadıkların, ustalık."""
        sira = [s.alias for s in (self.db.bul(x) for x in (self.ayar.get("havuz") or {}).get(rol, [])) if s]
        for a, k in sorted((kisisel or {}).items(), key=lambda x: -x[1].mac):
            if a in self.db.sampiyonlar and rol in self.db.sampiyonlar[a].roller and a not in sira:
                sira.append(a)
        for a, _ in sorted((ustalik or {}).items(), key=lambda x: -x[1]):
            if a in self.db.sampiyonlar and rol in self.db.sampiyonlar[a].roller and a not in sira:
                sira.append(a)
        return sira

    def _build_json(self, hedef, build, sayfa=None, buyu=None):
        if not build:
            return None
        e = lambda i, ad, **k: {"id": i, "ad": ad, "ikon": self._ikon_e(i), **k}
        return {
            "hedef": self._s(hedef), "arketip": build.arketip,
            "baslangic": [e(i, ad, adet=n) for i, ad, n in build.baslangic],
            "bot": e(build.bot[0], build.bot[1], neden=build.bot[2]) if build.bot else None,
            "esyalar": [e(i, ad, neden=n, durum=n not in ("Çekirdek", "Geç oyun")) for i, ad, n in build.esyalar],
            "b_plani": [e(i, ad, kosul=k) for k, i, ad in build.b_plani],
            "notlar": build.notlar,
            "runler": self._run_json(sayfa),
            "buyu": self._buyu_json(buyu),
        }

    # ---------------- analiz ----------------
    def hesapla(self, rol, takim, rakipler, yasakli=(), benim=None, sahip=None,
                ustalik=None, kilitli=False, ban_asamasi=False):
        a = self.ayar
        rr = rolleri_tahmin_et(rakipler)
        profil = profil_cikar(rakipler)
        havuz = [s.alias for s in (self.db.bul(x) for x in (a.get("havuz") or {}).get(rol, [])) if s]
        k_sampiyon, k_koridor, k_rakip = self._kisisel()
        oneriler = []
        if not kilitli and (not benim or a.get("secince_de_oner", True)):
            oneriler = sampiyon_oner(self.db, rol, rr, takim, rakipler, set(yasakli), sahip, ustalik,
                                     havuz, a.get("sadece_havuz", False), int(a.get("oneri_sayisi", 5)),
                                     kisisel=k_sampiyon)
        hedef = benim or (oneriler[0].sampiyon if oneriler else None)
        rakip = rr.get(rol)
        build = build_olustur(hedef, rol, profil, rakip, self.esya, rakipler) if hedef else None
        sayfa = self._sayfa(hedef, rol, profil, rakip) if hedef else None
        buyu = self._buyu(hedef, rol, profil, rakip) if hedef else None
        self._baglam = (rol, profil, rr, rakipler)
        banlar = []
        if ban_asamasi:
            banlar = ban_oner(self.db, rol, benim, takim, yasakli, k_rakip,
                              self._ana_sampiyonlar(rol, ustalik, k_sampiyon),
                              genel_oran=self.gecmis.genel().oran if self.gecmis.maclar else 0.5)
        plan = mac_plani(rol, hedef, takim, rakipler, rakip, k_koridor) if hedef else []
        d = {
            "ekran": "secim", "rol": rol, "rol_ad": ROL_AD.get(rol, rol), "kilitli": kilitli,
            "benim": self._s(benim), "rakibim": self._s(rr.get(rol)),
            "rakipler": [dict(self._s(rr.get(r)) or {}, rol=r, rol_ad=ROL_AD[r], bos=rr.get(r) is None,
                              rakibim=(r == rol)) for r in ROLLER],
            "takim": [self._s(s) for s in takim],
            "oran_ad": round(profil.ad_orani * 100) if profil.sayi else None,
            "notlar": profil.notlar()[1:] if profil.sayi else [],
            "oneriler": [dict(self._s(o.sampiyon), puan=round(o.puan),
                              nedenler=[{"arti": d_ >= 0, "m": m} for d_, m in o.ana_nedenler(4)])
                         for o in oneriler],
            "build": self._build_json(hedef, build, sayfa, buyu),
            "plan": [{"tur": t, "m": m} for t, m in plan],
            "ban_asamasi": ban_asamasi,
            "banlar": [dict(self._s(b.sampiyon), nedenler=b.nedenler[:2]) for b in banlar],
        }
        return d, build

    def build_icin(self, alias):
        """Alternatif bir öneriye tıklanınca onun buildini hazırlar."""
        s = self.db.bul(alias) if self.db else None
        if not s or not self._baglam:
            return None
        rol, profil, rr, rakipler = self._baglam
        return self._build_json(s, build_olustur(s, rol, profil, rr.get(rol), self.esya, rakipler),
                                self._sayfa(s, rol, profil, rr.get(rol)), self._buyu(s, rol, profil, rr.get(rol)))

    def runleri_uygula(self, alias):
        """Arayüzdeki 'Rünleri uygula' düğmesi."""
        from .lcu import run_sayfasi_yaz
        s = self.db.bul(alias) if self.db else None
        sayfa = self._sayfalar.get(s.alias) if s else None
        if not sayfa:
            return {"ok": False, "mesaj": "Önce bir analiz gerekli."}
        if not sayfa.uygulanabilir:
            return {"ok": False, "mesaj": "Rün verisi indirilemedi (internet yok); sayfayı elle kurabilirsin."}
        if not self._lcu:
            return {"ok": False, "mesaj": "LoL istemcisi açık değil."}
        try:
            run_sayfasi_yaz(self._lcu, s, sayfa)
            return {"ok": True, "mesaj": f"{s.ad} rün sayfası istemciye eklendi ve seçildi."}
        except Exception as e:
            return {"ok": False, "mesaj": str(e)}

    def buyuleri_uygula(self, alias):
        from .lcu import buyuleri_yaz
        s = self.db.bul(alias) if self.db else None
        b = self._buyuler.get(s.alias) if s else None
        if not b:
            return {"ok": False, "mesaj": "Önce bir analiz gerekli."}
        if not self._lcu:
            return {"ok": False, "mesaj": "LoL istemcisi açık değil."}
        try:
            buyuleri_yaz(self._lcu, b)
            return {"ok": True, "mesaj": f"Büyüler ayarlandı: {BUYU[b.ikinci][0]} + Sıçra."}
        except Exception as e:
            return {"ok": False, "mesaj": str(e)}

    def uygula(self, alias):
        """'Rünleri ve büyüleri uygula' düğmesi."""
        r, b = self.runleri_uygula(alias), self.buyuleri_uygula(alias)
        return {"ok": r["ok"] and b["ok"], "mesaj": r["mesaj"] + " " + b["mesaj"]}

    # ---------------- güncelleme ----------------
    def guncelleme_kontrol(self):
        from . import guncelle
        anahtar = (self.ayar.get("github_anahtar") or "").strip()
        sonuc = {"var": False, "yerel": guncelle.yerel_surum(), "uzak": None, "mesaj": ""}
        if not anahtar:
            sonuc["mesaj"] = "Otomatik güncelleme için Ayarlar'a GitHub anahtarını gir."
            return sonuc
        try:
            sonuc.update(guncelle.kontrol(self.ayar.get("github_depo", ""), anahtar))
            if not sonuc.get("mesaj"):
                sonuc["mesaj"] = (f"Yeni sürüm var: {sonuc['uzak']}" if sonuc["var"]
                                  else f"Güncelsin (sürüm {sonuc['yerel']}).")
        except Exception as e:
            sonuc["mesaj"] = f"Güncelleme kontrol edilemedi: {e}"
        return sonuc

    def guncelle_kur(self):
        from . import guncelle
        try:
            yeni = guncelle.indir_ve_kur(self.ayar.get("github_depo", ""), self.ayar.get("github_anahtar", "").strip())
            return {"ok": True, "mesaj": f"Sürüm {yeni} kuruldu. Uygulama yeniden başlatılıyor…"}
        except Exception as e:
            return {"ok": False, "mesaj": f"Güncelleme kurulamadı: {e}"}

    # ---------------- performans sayfası ----------------
    def performans(self):
        if not self.db:
            return {"hazir": False, "mesaj": "Veriler hazırlanıyor…"}
        g = self.gecmis
        if not g.maclar:
            return {"hazir": False, "calisiyor": self._gecmis_calisiyor, "mesaj": self.gecmis_durum or (
                "Henüz maç geçmişi okunmadı. LoL istemcisi açıkken burası son maçlarınla dolacak."
                if not self.baglanti else "Maç geçmişi okunuyor…")}
        genel = g.genel()
        champ = sorted(g.sampiyon_istatistik().items(), key=lambda x: (-x[1].mac, -x[1].oran))
        sj = lambda cid, st, **k: dict(self._s(self.db.id_ile(cid)) or {"ad": f"#{cid}", "ikon": None},
                                       mac=st.mac, oran=round(st.oran * 100), kda=round(st.kda, 2), **k)
        esik = min(0.4, genel.oran - 0.1)
        koridor = [(c, st) for c, st in g.koridor_rakibi_istatistik().items() if st.mac >= 2 and st.oran <= esik]
        koridor.sort(key=lambda x: (x[1].oran, -x[1].mac))
        rakip = [(c, st) for c, st in g.rakip_istatistik().items() if st.mac >= 3 and st.oran <= min(0.45, genel.oran - 0.1)]
        rakip.sort(key=lambda x: (x[1].oran, -x[1].mac))
        roller = {}
        for r in g.sirali(60):
            if r.get("rol"):
                roller[r["rol"]] = roller.get(r["rol"], 0) + 1
        ana_rol = max(roller, key=roller.get) if roller else rol_coz(self.ayar.get("varsayilan_rol")) or "mid"
        k_s, _, k_r = self._kisisel()
        banlar = ban_oner(self.db, ana_rol, None, [], set(), k_r, self._ana_sampiyonlar(ana_rol, None, k_s),
                          genel_oran=genel.oran)
        toplam_analiz, hatalar = sik_hatalar()
        son = g.sirali(10)
        return {
            "hazir": True, "calisiyor": self._gecmis_calisiyor, "mesaj": self.gecmis_durum,
            "genel": {"mac": genel.mac, "oran": round(genel.oran * 100), "kda": round(genel.kda, 2)},
            "ana_rol": ROL_AD.get(ana_rol, ana_rol),
            "son": [dict(self._s(self.db.id_ile(r["sampiyon"])) or {"ad": "?", "ikon": None},
                         kazandi=r["kazandi"], kda=f'{r["k"]}/{r["d"]}/{r["a"]}') for r in son],
            "sampiyonlar": [sj(c, st) for c, st in champ[:8]],
            "zor_koridor": [sj(c, st) for c, st in koridor[:5]],
            "zor_rakip": [sj(c, st) for c, st in rakip[:5]],
            "banlar": [dict(self._s(b.sampiyon), nedenler=b.nedenler[:2]) for b in banlar],
            "hatalar": {"toplam": toplam_analiz, "liste": [{"ad": a, "sayi": n} for a, n in hatalar[:4]]},
        }

    def gecmisi_yenile(self):
        if not self._lcu or self._gecmis_calisiyor:
            return False
        threading.Thread(target=self._gecmis_guncelle, args=(self._lcu,), daemon=True).start()
        return True

    def _gecmis_guncelle(self, lcu):
        self._gecmis_calisiyor = True
        try:
            def ilerle(n, t):
                self.gecmis_durum = f"Maç geçmişi okunuyor: {n}/{t}"
            yeni = self.gecmis.guncelle(lcu, 100, ilerle)
            self.gecmis_durum = f"{len(self.gecmis.maclar)} maç analiz edildi" + (f" ({yeni} yeni)" if yeni else "")
        except Exception as e:
            self.gecmis_durum = f"Maç geçmişi okunamadı: {e}"
        finally:
            self._gecmis_calisiyor = False

    # ---------------- elle / demo ----------------
    def _isimler(self, metin, hatalar):
        out = []
        for p in (metin or "").replace("\n", ",").split(","):
            p = p.strip()
            if not p:
                continue
            s = self.db.bul(p)
            (out.append(s) if s else hatalar.append(p))
        return out

    def manuel(self, rol, rakip, takim, sampiyon):
        if not self.db:
            return {"hata": ["Veriler henüz hazır değil, birkaç saniye sonra tekrar dene."]}
        hatalar = []
        rol = rol_coz(rol) or "mid"
        rakipler = self._isimler(rakip, hatalar)[:5]
        tk = self._isimler(takim, hatalar)[:4]
        benim = self.db.bul(sampiyon) if sampiyon else None
        if sampiyon and not benim:
            hatalar.append(sampiyon)
        if not rakipler and not benim:
            return {"hata": hatalar or ["En az bir rakip şampiyon yaz."]}
        d, _ = self.hesapla(rol, tk, rakipler, benim=benim)
        self.elle = True
        self._yayinla(d, canli=False)
        return {"hata": hatalar}

    def demo(self):
        return self.manuel("mid", "Zed, Lee Sin, Darius, Jinx, Soraka", "Garen, Graves, Caitlyn", "")

    def sampiyon_adlari(self):
        return sorted(s.ad for s in self.db.sampiyonlar.values()) if self.db else []

    def gecmis_ac(self):
        klasor = os.path.join(KOK, "mac_gecmisi")
        os.makedirs(klasor, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(klasor)  # noqa
        return klasor

    # ---------------- canlı döngü ----------------
    def baslat(self):
        threading.Thread(target=self._calis, daemon=True).start()

    def _calis(self):
        import requests
        from .lcu import LCU, item_set_aktar, secim_oku
        from .mac_sonu import analiz_et, eog_coz, kaydet

        try:
            self.hazirla()
        except Exception as e:
            self._yayinla({"ekran": "hata", "baslik": "Veriler yüklenemedi", "mesaj": str(e)})
            return
        lcu, son, aktarilan, analiz_edilen = None, None, set(), None
        sahip, ustalik, son_build, son_rol = None, {}, None, None
        ekran = None

        while True:
            try:
                if lcu is None:
                    lcu = LCU.bul(self.ayar.get("lol_klasoru", ""))
                    if lcu is None:
                        self.baglanti = False
                        if ekran != "istemci_yok":
                            self._yayinla({"ekran": "istemci_yok", "baslik": "LoL istemcisi kapalı",
                                           "mesaj": "Oyunu açtığında otomatik bağlanacağım. "
                                                    "Beklerken demo maça bakabilir ya da takımları elle girebilirsin."})
                            ekran = "istemci_yok"
                        time.sleep(3)
                        continue
                    self.db.id_esle(lcu.sampiyon_kayitlari())
                    self.baglanti, ekran = True, None
                    self._lcu = lcu
                    self.gecmisi_yenile()

                faz = lcu.faz()
                # Maç sırasında hiçbir oyun verisi okunmaz, analiz yapılmaz.
                # Sadece seçim ekranında hazırlanmış (değişmeyen) plan gösterilir.
                if faz in ("GameStart", "InProgress", "Reconnect"):
                    if ekran != "oyun":
                        self._yayinla({"ekran": "oyun", "baslik": "Maç devam ediyor",
                                       "mesaj": "Riot kuralları gereği maç sırasında analiz yapmıyorum. "
                                                "B planı mağazadaki eşya setinde: Tab'a bak, kararı sen ver. "
                                                "Maç bitince ne daha iyi olabilirdi, burada göstereceğim.",
                                       "hazirlik": self._son_secim})
                        ekran = "oyun"
                    son = None
                    time.sleep(5)
                    continue
                if faz in ("WaitingForStats", "PreEndOfGame", "EndOfGame"):
                    mac = eog_coz(lcu.mac_sonu_verisi())
                    if mac and mac.oyun_id != analiz_edilen:
                        analiz_et(mac, self.db, self.esya, son_rol or self.ayar.get("varsayilan_rol", "mid"), son_build)
                        try:
                            dosya = kaydet(mac)
                        except Exception:
                            dosya = None
                        ben = next(o for o in mac.oyuncular if o.ben)
                        self._yayinla({"ekran": "macsonu", "ozet": mac.ozet, "kazandi": ben.kazandi,
                                       "sampiyon": self._s(self.db.id_ile(ben.champ_id)),
                                       "kda": f"{ben.k} / {ben.d} / {ben.a}",
                                       "analiz": [{"tur": t, "m": m} for t, m in mac.analiz], "dosya": dosya})
                        analiz_edilen, ekran = mac.oyun_id, "macsonu"
                        self.gecmisi_yenile()
                    time.sleep(3)
                    continue

                oturum = lcu.secim_ekrani()
                if not oturum:
                    if ekran not in ("bekle", "macsonu"):
                        self._yayinla({"ekran": "bekle", "baslik": "Maç bekleniyor",
                                       "mesaj": "İstemciye bağlandım. Seçim ekranı açılınca karşı takımı "
                                                "analiz edip şampiyon ve build önereceğim."})
                        ekran = "bekle"
                    son = None
                    time.sleep(2)
                    continue

                if son is None:  # yeni seçim ekranı
                    self._son_secim = None
                    ids = lcu.sahip_olunanlar()
                    sahip = {self.db.id_ile(i).alias for i in ids if self.db.id_ile(i)} if ids else None
                    ustalik = {self.db.id_ile(i).alias: p for i, p in lcu.ustaliklar().items() if self.db.id_ile(i)}
                    aktarilan = set()
                    self.elle = False   # gerçek seçim başlayınca demo ekranını kapat

                d = secim_oku(oturum)
                self._sicra_d = d.sicra_d
                rol = d.rol or rol_coz(self.ayar.get("varsayilan_rol")) or "mid"
                anahtar = d.anahtar() + (rol,)
                if anahtar != son:
                    son, ekran = anahtar, "secim"
                    v = lambda ids: [self.db.id_ile(i) for i in ids if self.db.id_ile(i)]
                    benim = self.db.id_ile(d.benim_id)
                    durum, build = self.hesapla(rol, v(d.takim_ids), v(d.rakip_ids),
                                                {s.alias for s in v(d.yasak_ids)}, benim,
                                                sahip, ustalik, d.kilitli, d.ban_asamasi)
                    durum["rol_atanmadi"] = not d.rol
                    if benim:
                        son_build, son_rol = build, rol
                        self._son_secim = {k: durum.get(k) for k in ("build", "plan", "rakipler", "rol_ad", "benim")}
                    # Kilitledikten sonra (rakip yeni seçim yaptıkça güncellenir)
                    anahtar_set = (benim.alias, len(d.rakip_ids)) if benim else None
                    if benim and d.kilitli and build and anahtar_set not in aktarilan:
                        aktarilan.add(anahtar_set)
                        if self.ayar.get("item_set_aktar", True) and not self.esya.cevrimdisi:
                            try:
                                item_set_aktar(lcu, benim, build)
                                durum["itemset"] = "Build mağazaya eşya seti olarak eklendi"
                            except Exception as e:
                                durum["itemset"] = f"Eşya seti eklenemedi: {e}"
                        if self.ayar.get("run_aktar", True):
                            durum["runset"] = self.runleri_uygula(benim.alias)
                        if self.ayar.get("buyu_aktar", True):
                            durum["buyuset"] = self.buyuleri_uygula(benim.alias)
                    self._yayinla(durum)
                time.sleep(1.5)
            except requests.exceptions.ConnectionError:
                lcu, son, ekran = None, None, None
                self._lcu = None
                self.baglanti = False
                time.sleep(2)
            except Exception as e:  # beklenmedik hata: göster ama çökme
                self._yayinla({"ekran": "hata", "baslik": "Bir şeyler ters gitti",
                               "mesaj": f"{type(e).__name__}: {e}. Birkaç saniye içinde yeniden deneyeceğim."})
                ekran = "hata"
                time.sleep(4)
