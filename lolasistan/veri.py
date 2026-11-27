"""Data Dragon (Riot'un resmi statik verisi): güncel yama, şampiyon ve eşya listeleri.
İnternet yoksa önbellekteki son yamayı kullanır; o da yoksa çevrimdışı modda çalışır."""
import json
import os

from .champs import KOK, norm

DD = "https://ddragon.leagueoflegends.com"
ONBELLEK = os.path.join(KOK, "cache")


def _surum_anahtar(v):
    return [int(x) for x in v.split(".") if x.isdigit()]


class DataDragon:
    def __init__(self, dil="tr_TR"):
        self.dil = dil
        self.surum = None
        self.cevrimici = False
        try:
            import requests
            r = requests.get(f"{DD}/api/versions.json", timeout=8)
            r.raise_for_status()
            self.surum = r.json()[0]
            self.cevrimici = True
        except Exception:
            if os.path.isdir(ONBELLEK):
                surumler = sorted((d for d in os.listdir(ONBELLEK) if d[:1].isdigit()), key=_surum_anahtar)
                self.surum = surumler[-1] if surumler else None

    def _veri(self, tur, dil):
        if not self.surum:
            return None
        yol = os.path.join(ONBELLEK, self.surum, f"{tur}_{dil}.json")
        if os.path.exists(yol):
            with open(yol, encoding="utf-8") as f:
                return json.load(f)
        if not self.cevrimici:
            return None
        try:
            import requests
            r = requests.get(f"{DD}/cdn/{self.surum}/data/{dil}/{tur}.json", timeout=15)
            r.raise_for_status()
            veri = r.json()
            os.makedirs(os.path.dirname(yol), exist_ok=True)
            with open(yol, "w", encoding="utf-8") as f:
                json.dump(veri, f, ensure_ascii=False)
            return veri
        except Exception:
            return None

    def sampiyon_kayitlari(self):
        veri = self._veri("champion", self.dil) or self._veri("champion", "en_US")
        if not veri:
            return []
        out = []
        for c in veri["data"].values():
            info = c.get("info", {})
            out.append((int(c["key"]), c["id"], c["name"], c.get("tags", []),
                        info.get("magic", 0) > info.get("attack", 0)))
        return out

    def esyalar(self, dil):
        return self._veri("item", dil)


class EsyaDB:
    """İngilizce eşya adıyla arama yapar, Türkçe (veya seçilen dilde) ad döndürür."""

    def __init__(self, dd: DataDragon = None):
        self.isimden = {}
        self.bilgi = {}   # id -> {"en", "ad", "zirh", "mr", "tamam"}
        self.cevrimdisi = True
        if dd is None:
            return
        en = dd.esyalar("en_US")
        if not en:
            return
        yerel = dd.esyalar(dd.dil) if dd.dil != "en_US" else en
        self.cevrimdisi = False
        veri = en["data"]
        yerel_ad = lambda iid, varsayilan: ((yerel or {}).get("data", {}).get(iid) or {}).get("name", varsayilan)
        # 1) id -> bilgi: TÜM eşyalar (sitelerin istatistiklerinde dönüşmüş eşyalar da geçer:
        #    Seraph's Embrace, Muramana... bunlar mağazada satılmaz ama tanınmaları gerekir)
        for iid, it in veri.items():
            st = it.get("stats", {})
            satin_id = iid
            if not it.get("gold", {}).get("purchasable", True):
                kok = it.get("specialRecipe") or (it.get("from") or [None])[0]
                if kok and str(kok) in veri and veri[str(kok)].get("gold", {}).get("purchasable", False):
                    satin_id = str(kok)
            ad = yerel_ad(iid, it["name"])
            if satin_id != iid:
                ad = f"{yerel_ad(satin_id, veri[satin_id]['name'])} (→ {ad})"
            self.bilgi[str(iid)] = {
                "en": it["name"], "en_satin": veri[satin_id]["name"], "ad": ad, "satin_id": satin_id,
                "zirh": st.get("FlatArmorMod", 0) > 0, "mr": st.get("FlatSpellBlockMod", 0) > 0,
                "tamam": it.get("gold", {}).get("total", 0) >= 2000 or not it.get("into"),
            }
        # 2) isim -> (id, ad): sadece Sihirdar Vadisi mağazasında satılanlar
        for iid, it in veri.items():
            if not it.get("maps", {}).get("11"):
                continue
            if not it.get("gold", {}).get("purchasable", False):
                continue
            if it.get("requiredChampion") or it.get("requiredAlly"):
                continue
            anahtar = norm(it["name"])
            ad = yerel_ad(iid, it["name"])
            if anahtar not in self.isimden or int(iid) < int(self.isimden[anahtar][0]):
                self.isimden[anahtar] = (iid, ad)

    def bul(self, isim):
        """(id, görünen_ad) ya da bu yamada yoksa None. Çevrimdışıyken (None, isim)."""
        if self.cevrimdisi:
            return (None, isim)
        return self.isimden.get(norm(isim))

    def id_bilgi(self, iid):
        return self.bilgi.get(str(iid))
