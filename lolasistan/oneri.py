"""Senin koridorun için şampiyon önerisi."""
import math
from dataclasses import dataclass, field

from .analiz import profil_cikar


@dataclass
class Oneri:
    sampiyon: object
    puan: float = 0.0
    nedenler: list = field(default_factory=list)

    def ekle(self, deger, neden=None):
        self.puan += deger
        if neden:
            self.nedenler.append((deger, neden))

    def ana_nedenler(self, n=3):
        return sorted(self.nedenler, key=lambda x: -abs(x[0]))[:n]


def sampiyon_oner(db, rol, rakip_roller: dict, takim: list, rakipler: list,
                  yasakli: set = (), sahip: set = None, ustalik: dict = None,
                  havuz: list = None, sadece_havuz=False, adet=5, kisisel: dict = None,
                  kisisel_koridor: dict = None, eslesme: dict = None):
    """
    rakip_roller : {rol: Sampiyon} (tahmini)
    takim        : senin takım arkadaşlarının şampiyonları (sen hariç)
    sahip        : sahip olduğun şampiyon alias'ları (None = filtre yok)
    ustalik      : {alias: ustalık puanı}
    havuz        : config'teki favori şampiyonların (alias)
    kisisel      : {alias: Sayac} — senin bu şampiyonla son maçlardaki sonucun
    eslesme      : {alias: (kazanma_orani, maç)} — adayın koridor rakibine karşı GERÇEK sonucu (OP.GG)
    """
    eslesme = eslesme or {}
    kisisel = kisisel or {}
    ustalik = ustalik or {}
    havuz = set(havuz or [])
    kullanilan = {s.alias for s in list(takim) + list(rakipler) if s} | set(yasakli)
    rakip = rakip_roller.get(rol)
    takim = [s for s in takim if s]
    rakipler = [s for s in rakipler if s]
    tp = profil_cikar(takim)
    rp = profil_cikar(rakipler)

    adaylar = [s for s in db.rol_sampiyonlari(rol) if s.alias not in kullanilan]
    if sahip is not None:
        adaylar = [s for s in adaylar if s.alias in sahip]
    if sadece_havuz and havuz:
        adaylar = [s for s in adaylar if s.alias in havuz]

    sonuc = []
    for c in adaylar:
        o = Oneri(c)
        # 1) Ana rol mü?
        if c.roller and c.roller[0] == rol:
            o.ekle(4)
        # 2) Koridor rakibi
        if rakip:
            veri = eslesme.get(c.alias)
            if veri:
                oran, mac = veri
                guvenilir = (oran * mac + 0.5 * 60) / (mac + 60)       # az maçlıyı ortalamaya çek
                fark = max(-30.0, min(30.0, (guvenilir - 0.5) * 400))
                yuzde = f"{oran * 100:.1f}".replace(".", ",")
                o.ekle(fark, f"{rakip.ad} karşısında %{yuzde} kazanıyor ({mac} maç)" if abs(fark) >= 2 else None)
            else:
                if db.iyi_mi(c, rakip):
                    o.ekle(20, f"{rakip.ad} karşısında güçlü (counter)")
                if db.iyi_mi(rakip, c):
                    o.ekle(-20, f"{rakip.ad} tarafından counterlanıyor")
            if rol in ("top", "mid") and c.menzilli and not rakip.menzilli:
                o.ekle(4, f"Yakın dövüşçü rakibe ({rakip.ad}) karşı menzil avantajı")
            if rakip.tanky and (c.var("hp") or c.var("true")):
                o.ekle(6, f"Tank rakibe ({rakip.ad}) karşı %can / gerçek hasar")
            if rakip.sinif == "assassin" and (c.tanky or c.var("cc")):
                o.ekle(3, f"Suikastçı rakibe ({rakip.ad}) karşı dayanıklı / CC'li")
        else:
            # Rakip henüz seçmedi: counter'ı az olan = güvenli kör seçim
            n = len(db.counterlayanlar(c))
            if n <= 2:
                o.ekle(5, "Kör seçim (blind pick) için güvenli")
            else:
                o.ekle(-1.0 * (n - 2))

        # 3) Kendi takımının dengesi
        if tp.sayi >= 2:
            if tp.ad_orani >= 0.7 and c.hasar in ("AP", "MIX"):
                o.ekle(12, "Takımın AD ağırlıklı → büyü hasarı dengeler")
            elif tp.ap_orani >= 0.7 and c.hasar in ("AD", "MIX"):
                o.ekle(12, "Takımın AP ağırlıklı → fiziksel hasar dengeler")
            elif tp.ad_orani >= 0.7 and c.hasar == "AD" and c.sinif != "tank":
                o.ekle(-6, "Takım zaten çok AD")
            elif tp.ap_orani >= 0.7 and c.hasar == "AP" and c.sinif not in ("tank", "enchanter"):
                o.ekle(-6, "Takım zaten çok AP")
        if tp.sayi >= 2 and tp.tank == 0 and c.tanky and rol in ("top", "jungle", "support"):
            o.ekle(10, "Takımında ön cephe (tank) yok")
        if tp.sayi >= 2 and tp.engage == 0 and c.var("engage"):
            o.ekle(6, "Takımında engage (savaş başlatan) yok")

        # 4) Rakip kompozisyonuna uyum
        if rp.tank >= 2 and (c.var("hp") or c.var("true")):
            o.ekle(10, f"Karşıda {rp.tank} tank var → %can / gerçek hasar")
        if rp.suikastci >= 2 and (c.var("peel") or c.tanky or c.var("shield")):
            o.ekle(6, "Rakip suikastçılara karşı dayanıklı / koruyucu")
        if rp.iyilesme >= 3 and c.var("burst"):
            o.ekle(4, "Patlama hasarı iyileşmeyi geçer")
        if rp.durtme >= 2 and c.var("engage"):
            o.ekle(5, "Dürtme (poke) takımına hızlı giriş yapar")
        if rp.dalis >= 3 and c.var("cc") and c.var("peel"):
            o.ekle(5, "Dalış (dive) takımına karşı CC/peel")

        # 5) Kişisel geçmiş: bu şampiyonla gerçekten kazanıyor musun?
        k = kisisel.get(c.alias)
        if k and k.mac >= 3:
            fark = max(-12.0, min(12.0, (k.oran - 0.5) * 40))
            o.ekle(fark + min(4, k.mac / 5), f"Son {k.mac} maçta %{round(k.oran * 100)} kazandın")
        elif k and k.mac:
            o.ekle(1)

        # 6) Rahatlık: ustalık puanı / havuz
        puan = ustalik.get(c.alias, 0)
        if puan > 0:
            bonus = min(15.0, 3 * math.log10(puan + 1))
            o.ekle(bonus, f"Ustalık: {puan:,} puan".replace(",", "."))
        elif c.alias in havuz:
            o.ekle(8, "Şampiyon havuzunda")
        if c.tahmini:
            o.ekle(-3)
        sonuc.append(o)

    sonuc.sort(key=lambda x: x.puan, reverse=True)
    return sonuc[:adet]
