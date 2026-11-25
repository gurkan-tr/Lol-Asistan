"""Ban önerisi ve maç planı kartı (ikisi de maç başlamadan gösterilir)."""
from dataclasses import dataclass, field

# Erken oyunda belirgin güçlü şampiyonlar (genel bilgi)
ERKEN = {"Draven", "LeeSin", "Renekton", "Pantheon", "Elise", "Kled", "Lucian", "Darius", "Olaf",
         "XinZhao", "Nidalee", "Jayce", "Talon", "Qiyana", "Blitzcrank", "Leona", "Nautilus",
         "Pyke", "Rengar", "Khazix", "Graves", "JarvanIV", "Shaco", "RekSai", "Kalista", "Samira",
         "Caitlyn", "Tristana", "Riven", "Sett", "Irelia", "Zed", "Naafiri", "Briar", "Camille", "Ambessa"}
SPLIT = {"Fiora", "Jax", "Tryndamere", "Yorick", "Camille", "Gwen", "Nasus", "Trundle", "Shen", "Ambessa"}


def guc_egrisi(s):
    """+1 erken, 0 orta, -1 geç."""
    if s.alias in ERKEN:
        return 1
    if s.var("scaling"):
        return -1
    if s.sinif in ("tank", "enchanter"):
        return 0
    return 0


@dataclass
class BanOnerisi:
    sampiyon: object
    puan: float
    nedenler: list = field(default_factory=list)


def ban_oner(db, rol, benim, takim_niyet, yasakli, gecmis_rakip=None, havuz=None, adet=3, genel_oran=0.5):
    """
    benim        : seçmeyi düşündüğün şampiyon (yoksa havuz/ustalıktan ilk sıradakiler)
    takim_niyet  : takım arkadaşlarının seçmek istediği şampiyonlar (onları banlama)
    gecmis_rakip : {alias: Sayac} — bu şampiyonlar rakibindeyken senin sonucun
    havuz        : koridordaki ana şampiyonların (alias, en çok oynanandan)
    """
    korunan = {s.alias for s in takim_niyet if s} | set(yasakli)
    if benim:
        korunan.add(benim.alias)
    puan = {}

    def ekle(alias, deger, neden):
        if alias in korunan or alias not in db.sampiyonlar:
            return
        b = puan.setdefault(alias, BanOnerisi(db.sampiyonlar[alias], 0.0))
        b.puan += deger
        if neden and neden not in b.nedenler:
            b.nedenler.append(neden)

    anaciklar = [benim] if benim else [db.sampiyonlar[a] for a in (havuz or [])[:3] if a in db.sampiyonlar]
    for i, c in enumerate(anaciklar):
        agirlik = 1.0 if i == 0 else 0.6
        for karsi in db.counterlayanlar(c):
            if rol in db.sampiyonlar[karsi].roller if karsi in db.sampiyonlar else False:
                ekle(karsi, 20 * agirlik, f"Ana şampiyonun {c.ad} için counter")
    for alias, s in (gecmis_rakip or {}).items():
        esik = min(0.45, genel_oran - 0.1)
        if s.mac >= 3 and s.oran <= esik:
            ekle(alias, (genel_oran - s.oran) * 80 + min(s.mac, 10),
                 f"Karşına çıktığı {s.mac} maçta kazanma oranın %{round(s.oran * 100)}")
    return sorted(puan.values(), key=lambda b: -b.puan)[:adet]


def mac_plani(rol, benim, takim, rakipler, rakip, kisisel_koridor=None):
    """Kısa maç planı: takım güç eğrisi, takım savaşı stili, koridor ipuçları."""
    from .analiz import profil_cikar
    satirlar = []
    biz = [s for s in list(takim) + ([benim] if benim else []) if s]
    onlar = [s for s in rakipler if s]
    if len(biz) >= 3 and len(onlar) >= 3:
        g_biz = sum(guc_egrisi(s) for s in biz) / len(biz)
        g_onlar = sum(guc_egrisi(s) for s in onlar) / len(onlar)
        if g_onlar - g_biz >= 0.3:
            satirlar.append(("zaman", "Rakip erken oyunda daha güçlü. İlk 15 dakika güvenli oyna, "
                                      "farmla ve objektifleri sadece avantajlıyken al."))
        elif g_biz - g_onlar >= 0.3:
            satirlar.append(("zaman", "Takımın erken oyunda daha güçlü. Baskı kur, ilk ejderha ve "
                                      "Vadi Gözcüsü'nü kovala, oyunu uzatma."))
        elif g_biz < g_onlar - 0.1 or (g_biz < 0 and g_biz <= g_onlar):
            satirlar.append(("zaman", "Takımın geç oyunda daha iyi ölçekleniyor. Erken kavgalardan kaçın, "
                                      "2-3 eşyadan sonra savaş."))
        pb, po = profil_cikar(biz), profil_cikar(onlar)
        if po.durtme >= 2 and pb.engage >= 1:
            satirlar.append(("savas", "Rakip uzaktan dürtme takımı. Beklemeyin, ilk fırsatta hızlı engage yapın."))
        if po.dalis >= 3:
            satirlar.append(("savas", "Rakip taşıyıcılarınıza dalacak. Savaşlarda ADC'ye yakın durun, peel önemli."))
        if pb.engage == 0 and po.engage >= 2:
            satirlar.append(("savas", "Rakibin engage'i sizden güçlü. Dar alanlarda savaşa girmeyin, savaşı onlar başlatsın, siz karşılık verin."))
        if any(s.alias in SPLIT for s in biz):
            ad = next(s.ad for s in biz if s.alias in SPLIT)
            satirlar.append(("savas", f"{ad} yan koridorda bölünmüş itiş (split push) yapabilir; diğerleri 4'lü baskı kursun."))

    if rakip is not None:
        if rakip.alias in ERKEN:
            satirlar.append(("koridor", f"{rakip.ad} ilk seviyelerde güçlü. Kısa takas yap, minyon dalgası seninle olmadan saldırma."))
        elif rakip.var("scaling") and benim is not None and guc_egrisi(benim) >= 0:
            satirlar.append(("koridor", f"{rakip.ad} geç güçleniyor. Erken baskı kur, ormancınla dalış planla."))
        if rakip.sinif == "assassin" or (rakip.var("burst") and rakip.var("dive")):
            satirlar.append(("koridor", f"{rakip.ad} 6. seviyede ultisiyle tehlikeli. 6'dan sonra çok ileride durma."))
        if benim is not None and rakip.menzilli and not benim.menzilli:
            satirlar.append(("koridor", f"{rakip.ad} menzil avantajlı. Minyonların arkasında kal, yaklaştığında tam saldırıya geç."))
        if rakip.var("heal"):
            satirlar.append(("koridor", f"{rakip.ad} iyileşiyor; uzun takas yerine kısa ve sert saldırılar yap."))
        if rakip.var("stealth"):
            satirlar.append(("koridor", f"{rakip.ad} görünmez olabiliyor; Kontrol Totemi taşı."))
    if kisisel_koridor and rakip is not None:
        s = kisisel_koridor.get(rakip.alias)
        if s and s.mac >= 2:
            satirlar.append(("kisisel", f"{rakip.ad} karşısında {s.mac} maçta %{round(s.oran * 100)} kazandın."))
    return satirlar


KISA = [
    ("Rakip erken oyunda daha güçlü", "Rakip erken güçlü: ilk 15 dk sakin oynayalım, objektifleri avantajlıyken alalım."),
    ("Takımın erken oyunda daha güçlü", "Erken güçlüyüz: baskı kuralım, ilk ejderha ve Vadi Gözcüsü'nü alalım."),
    ("Takımın geç oyunda", "Geç oyun bizim: erken kavgaya girmeyelim, 2-3 eşyadan sonra savaşalım."),
    ("Rakip uzaktan dürtme", "Rakip poke takımı: beklemeyelim, hızlı engage yapalım."),
    ("Rakip taşıyıcılarınıza dalacak", "Rakip dalış yapacak: savaşlarda ADC'nin yanında kalalım."),
    ("Rakibin engage'i", "Rakibin engage'i güçlü: dar alanda savaşmayalım, karşılık verelim."),
]


def takim_mesaji(satirlar):
    """Maç planının takım sohbetine yapıştırılacak kısa hali (koridor ve kişisel satırlar hariç)."""
    parcalar = []
    for tur, m in satirlar:
        if tur not in ("zaman", "savas"):
            continue
        for bas, kisa in KISA:
            if m.startswith(bas):
                parcalar.append(kisa)
                break
        else:
            if "split push" in m:
                parcalar.append(f"{m.split(' yan koridorda')[0]} split itsin, biz 4'lü baskı kuralım.")
    return " ".join(parcalar)
