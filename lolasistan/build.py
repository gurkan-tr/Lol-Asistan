"""Rakip takıma göre eşya dizilimi (build) oluşturur.

Eşya adları İngilizce yazılır ve çalışma anında güncel yamanın eşya listesinden
aranır. Bir eşya oyundan kalkmışsa otomatik atlanır ve listedeki bir sonraki
alternatif kullanılır. Böylece yeni yamalarda program bozulmaz."""
from dataclasses import dataclass, field

from .esya_bilgi import ACIKLAMA, CEKIRDEK_OZEL

# Her slot = alternatifler listesi (ilk bulunan kullanılır)
SABLON = {
    "adc_crit": {
        "ad": "Nişancı (kritik)",
        "bot": ["Berserker's Greaves"],
        "cekirdek": [["Yun Tal Wildarrows", "Kraken Slayer", "Galeforce"], ["Infinity Edge"],
                     ["Phantom Dancer", "Rapid Firecannon", "Runaan's Hurricane", "Navori Flickerblade"]],
        "gec": [["Lord Dominik's Regards"], ["Bloodthirster"], ["Guardian Angel"]],
    },
    "adc_onhit": {
        "ad": "Nişancı (on-hit)",
        "bot": ["Berserker's Greaves"],
        "cekirdek": [["Blade of The Ruined King"], ["Guinsoo's Rageblade"], ["Terminus", "Wit's End"]],
        "gec": [["Kraken Slayer"], ["Runaan's Hurricane"], ["Guardian Angel"]],
    },
    "adc_spell": {
        "ad": "Nişancı (yetenek odaklı)",
        "bot": ["Ionian Boots of Lucidity"],
        "cekirdek": [["Essence Reaver", "Trinity Force"], ["Manamune", "Muramana"],
                     ["Serylda's Grudge", "Black Cleaver"]],
        "gec": [["Lord Dominik's Regards"], ["Bloodthirster"], ["Guardian Angel"]],
    },
    "ad_bruiser": {
        "ad": "Dövüşçü (AD)",
        "bot": ["Plated Steelcaps"],
        "cekirdek": [["Sundered Sky", "Trinity Force", "Eclipse"], ["Black Cleaver"], ["Sterak's Gage"]],
        "gec": [["Death's Dance"], ["Spear of Shojin"], ["Guardian Angel"]],
    },
    "ad_crit_melee": {
        "ad": "Yakın dövüş kritik",
        "bot": ["Berserker's Greaves"],
        "cekirdek": [["Kraken Slayer", "Stormrazor", "Statikk Shiv"], ["Infinity Edge"], ["Bloodthirster"]],
        "gec": [["Death's Dance"], ["Immortal Shieldbow"], ["Guardian Angel"]],
    },
    "ad_onhit_melee": {
        "ad": "Yakın dövüş on-hit",
        "bot": ["Berserker's Greaves"],
        "cekirdek": [["Blade of The Ruined King"], ["Guinsoo's Rageblade"], ["Wit's End", "Terminus"]],
        "gec": [["Sterak's Gage"], ["Death's Dance"], ["Guardian Angel"]],
    },
    "ad_lethality": {
        "ad": "Suikastçı (öldürücülük)",
        "bot": ["Ionian Boots of Lucidity"],
        "cekirdek": [["Youmuu's Ghostblade", "Profane Hydra", "Voltaic Cyclosword"],
                     ["Hubris", "Opportunity", "The Collector"], ["Edge of Night", "Axiom Arc"]],
        "gec": [["Serylda's Grudge"], ["Lord Dominik's Regards"], ["Guardian Angel"]],
    },
    "ap_mage": {
        "ad": "Büyücü",
        "bot": ["Sorcerer's Shoes"],
        "cekirdek": [["Luden's Echo", "Luden's Companion", "Blackfire Torch", "Malignance"],
                     ["Shadowflame", "Horizon Focus", "Liandry's Torment"], ["Rabadon's Deathcap"]],
        "gec": [["Void Staff"], ["Zhonya's Hourglass"], ["Banshee's Veil"]],
    },
    "ap_burst": {
        "ad": "Büyü suikastçısı",
        "bot": ["Sorcerer's Shoes"],
        "cekirdek": [["Stormsurge", "Lich Bane", "Luden's Echo", "Luden's Companion"], ["Shadowflame"],
                     ["Zhonya's Hourglass"]],
        "gec": [["Rabadon's Deathcap"], ["Void Staff"], ["Banshee's Veil"]],
    },
    "ap_bruiser": {
        "ad": "Dövüşçü (AP)",
        "bot": ["Plated Steelcaps"],
        "cekirdek": [["Riftmaker", "Liandry's Torment"], ["Liandry's Torment", "Rylai's Crystal Scepter"],
                     ["Zhonya's Hourglass"]],
        "gec": [["Rabadon's Deathcap"], ["Void Staff"], ["Spirit Visage", "Force of Nature"]],
    },
    "ap_onhit": {
        "ad": "AP on-hit",
        "bot": ["Berserker's Greaves"],
        "cekirdek": [["Nashor's Tooth"], ["Rabadon's Deathcap"], ["Lich Bane", "Shadowflame"]],
        "gec": [["Void Staff"], ["Zhonya's Hourglass"], ["Banshee's Veil"]],
    },
    "tank": {
        "ad": "Tank",
        "bot": ["Plated Steelcaps"],
        "cekirdek": [["Sunfire Aegis", "Heartsteel", "Hollow Radiance"],
                     ["Unending Despair", "Jak'Sho, The Protean"], ["Thornmail", "Spirit Visage"]],
        "gec": [["Jak'Sho, The Protean"], ["Force of Nature"], ["Warmog's Armor"]],
    },
    "enchanter": {
        "ad": "Koruyucu destek",
        "bot": ["Ionian Boots of Lucidity"],
        "cekirdek": [["Moonstone Renewer", "Echoes of Helia", "Dream Maker"],
                     ["Ardent Censer", "Staff of Flowing Water"], ["Redemption"]],
        "gec": [["Mikael's Blessing"], ["Shurelya's Battlesong"], ["Locket of the Iron Solari"]],
    },
    "support_tank": {
        "ad": "Tank destek",
        "bot": ["Plated Steelcaps"],
        "cekirdek": [["Locket of the Iron Solari", "Celestial Opposition"], ["Knight's Vow"],
                     ["Zeke's Convergence", "Trailblazer"]],
        "gec": [["Thornmail"], ["Force of Nature"], ["Redemption"]],
    },
    "support_mage": {
        "ad": "Büyücü destek",
        "bot": ["Sorcerer's Shoes"],
        "cekirdek": [["Liandry's Torment", "Luden's Echo", "Luden's Companion"], ["Imperial Mandate", "Malignance"],
                     ["Zhonya's Hourglass"]],
        "gec": [["Rylai's Crystal Scepter"], ["Morellonomicon"], ["Void Staff"]],
    },
}

ARKETIP_OZEL = {
    "Vayne": "adc_onhit", "KogMaw": "adc_onhit", "Kalista": "adc_onhit", "Twitch": "adc_onhit",
    "Ezreal": "adc_spell", "Corki": "adc_spell",
    "Yasuo": "ad_crit_melee", "Yone": "ad_crit_melee", "Tryndamere": "ad_crit_melee",
    "MasterYi": "ad_onhit_melee", "Belveth": "ad_onhit_melee",
    "Quinn": "ad_lethality", "Pantheon": "ad_lethality", "Jayce": "ad_lethality",
    "Kayle": "ap_onhit", "Teemo": "ap_onhit",
    "Gwen": "ap_bruiser", "Mordekaiser": "ap_bruiser", "Diana": "ap_bruiser", "Sylas": "ap_burst",
    "Rumble": "ap_mage", "Lillia": "ap_mage", "Kennen": "ap_mage",
    "Chogath": "tank", "Udyr": "tank", "Volibear": "ad_bruiser", "Shyvana": "ad_bruiser",
    "Graves": "adc_crit", "Kindred": "adc_crit", "Senna": "adc_crit", "Nilah": "adc_crit",
}

TASIYICI = {"adc_crit", "adc_onhit", "adc_spell", "ad_crit_melee", "ad_onhit_melee", "ad_lethality",
            "ap_mage", "ap_burst", "ap_onhit", "support_mage"}

# Bu eşyalar oyuna girmeden işe yarayan erken bileşenler
ERKEN = {
    "Mortal Reminder": "Executioner's Calling", "Chempunk Chainsword": "Executioner's Calling",
    "Morellonomicon": "Oblivion Orb", "Thornmail": "Bramble Vest",
}


@dataclass
class BuildSonucu:
    arketip: str
    baslangic: list = field(default_factory=list)  # (id, ad, adet)
    bot: tuple = None                               # (id, ad, neden)
    esyalar: list = field(default_factory=list)     # (id, ad, neden)
    notlar: list = field(default_factory=list)
    atlanan: list = field(default_factory=list)
    b_plani: list = field(default_factory=list)     # (koşul, id, ad)
    arketip_kod: str = ""
    bilgi: dict = field(default_factory=dict)       # görünen ad -> {"aciklama", "alternatif": [ad]}


def arketip_bul(s, rol):
    a = ARKETIP_OZEL.get(s.alias)
    if a is None:
        if s.sinif == "marksman":
            a = "ap_onhit" if s.hasar == "AP" else "adc_crit"
        elif s.sinif == "fighter":
            a = "ap_bruiser" if s.hasar == "AP" else "ad_bruiser"
        elif s.sinif == "assassin":
            a = "ap_burst" if s.hasar == "AP" else "ad_lethality"
        elif s.sinif == "mage":
            a = "ap_mage"
        elif s.sinif == "tank":
            a = "tank"
        else:
            a = "enchanter"
    if rol == "support":
        a = {"tank": "support_tank", "ap_mage": "support_mage", "ap_burst": "support_mage"}.get(a, a)
        if s.alias == "Pyke":
            a = "ad_lethality"
    return a


def _hasar_tarafi(a):
    if a.startswith("adc") or a.startswith("ad_"):
        return "AD"
    if a.startswith("ap") or a == "support_mage":
        return "AP"
    if a in ("tank", "support_tank"):
        return "TANK"
    return "DESTEK"


def durum_kurallari(a, profil, rakip):
    """(öncelik, [alternatifler], neden) listesi + bot değişikliği döner."""
    taraf = _hasar_tarafi(a)
    k = []
    bot = None
    adc = a.startswith("adc")

    # ---- saldırı ----
    if profil.iyilesme >= 2:
        alt = {"AD": ["Mortal Reminder"] if adc else ["Chempunk Chainsword", "Mortal Reminder"],
               "AP": ["Morellonomicon"], "TANK": ["Thornmail"], "DESTEK": []}[taraf]
        if alt:
            k.append((90 + profil.iyilesme, alt, f"Anti-heal: {profil.iyilesme} şampiyon iyileşiyor", "saldiri"))
    if profil.tank >= 2:
        alt = {"AD": ["Lord Dominik's Regards"] if adc else ["Serylda's Grudge", "Black Cleaver", "Lord Dominik's Regards"],
               "AP": ["Void Staff", "Liandry's Torment"], "TANK": [], "DESTEK": []}[taraf]
        if a in ("adc_onhit", "ad_onhit_melee"):
            alt = ["Blade of The Ruined King"]
        if alt:
            k.append((80 + profil.tank, alt, f"Delme: karşıda {profil.tank} tank", "saldiri"))
    if profil.kalkan >= 3 and taraf == "AD":
        k.append((60, ["Serpent's Fang"], "Bol kalkan var", "saldiri"))

    # ---- savunma ----
    if profil.sayi >= 2 and profil.ad_orani >= 0.65:
        alt = {"AD": ["Guardian Angel"] if adc else ["Death's Dance", "Randuin's Omen"],
               "AP": ["Zhonya's Hourglass"],
               "TANK": ["Frozen Heart", "Randuin's Omen", "Thornmail"],
               "DESTEK": ["Knight's Vow", "Locket of the Iron Solari"]}[taraf]
        k.append((70 + int(profil.ad_orani * 10), alt, "Rakip ağırlıklı fiziksel hasar", "savunma"))
        if not adc:
            bot = (["Plated Steelcaps"], "Rakip AD ağırlıklı → zırhlı bot")
    if profil.sayi >= 2 and profil.ap_orani >= 0.65:
        alt = {"AD": ["Wit's End", "Mercurial Scimitar"] if adc else ["Maw of Malmortius", "Wit's End"],
               "AP": ["Banshee's Veil"],
               "TANK": ["Force of Nature", "Kaenic Rookern", "Spirit Visage"],
               "DESTEK": ["Mikael's Blessing", "Locket of the Iron Solari"]}[taraf]
        k.append((70 + int(profil.ap_orani * 10), alt, "Rakip ağırlıklı büyü hasarı", "savunma"))
        bot = (["Mercury's Treads"], "Rakip AP ağırlıklı → büyü dirençli bot")
    if profil.cc >= 4 or (profil.cc >= 3 and profil.ad_orani < 0.75):
        if bot is None or "Mercury" not in bot[0][0]:
            bot = (["Mercury's Treads"], f"Rakipte bol CC ({profil.cc}) → Merkür Botları (inat)")
        if adc:
            k.append((65, ["Mercurial Scimitar", "Quicksilver Sash"], "Kitle kontrolünden arınma", "savunma"))
        elif taraf == "DESTEK":
            k.append((65, ["Mikael's Blessing"], "Takım arkadaşını CC'den kurtar", "savunma"))
    if profil.suikastci >= 2:
        alt = {"AD": ["Guardian Angel", "Immortal Shieldbow"] if adc else ["Sterak's Gage", "Edge of Night", "Guardian Angel"],
               "AP": ["Zhonya's Hourglass", "Banshee's Veil"],
               "TANK": [], "DESTEK": ["Locket of the Iron Solari", "Redemption"]}[taraf]
        if alt:
            k.append((68, alt, f"{profil.suikastci} suikastçıya karşı hayatta kalma", "savunma"))
    if profil.nisanci >= 2 and taraf == "TANK":
        k.append((62, ["Randuin's Omen", "Frozen Heart"], "Saldırı hızlı / kritik taşıyıcılar", "savunma"))
    return k, bot


def baslangic_esyalari(a, rol, rakip):
    if rol == "jungle":
        if a in ("tank", "support_tank"):
            pet = "Mosstomper Seedling"
        elif a in ("ad_lethality", "ap_burst"):
            pet = "Scorchclaw Pup"
        else:
            pet = "Gustwalker Hatchling"
        return [([pet], 1), (["Health Potion"], 1)]
    if rol == "support":
        return [(["World Atlas"], 1), (["Health Potion"], 2)]
    if a.startswith("ap") or a == "support_mage":
        return [(["Doran's Ring"], 1), (["Health Potion"], 2)]
    if a == "tank" or (a == "ad_bruiser" and rakip is not None and rakip.menzilli):
        return [(["Doran's Shield"], 1), (["Health Potion"], 1)]
    return [(["Doran's Blade"], 1), (["Health Potion"], 1)]


def build_olustur(sampiyon, rol, profil, rakip, esya_db, rakipler=None) -> BuildSonucu:
    a = arketip_bul(sampiyon, rol)
    sab = SABLON[a]
    b = BuildSonucu(arketip=sab["ad"], arketip_kod=a)

    def coz(alternatifler):
        for i, isim in enumerate(alternatifler):
            r = esya_db.bul(isim)
            if r:
                diger = [x[1] for x in (esya_db.bul(a) for a in alternatifler[i + 1:]) if x]
                b.bilgi.setdefault(r[1], {"aciklama": ACIKLAMA.get(isim, ""), "alternatif": diger})
                return r
        b.atlanan.extend(alternatifler)
        return None

    for alt, adet in baslangic_esyalari(a, rol, rakip):
        r = coz(alt)
        if r:
            b.baslangic.append((r[0], r[1], adet))

    kurallar, bot_degisim = durum_kurallari(a, profil, rakip)
    bot_alt, bot_neden = (bot_degisim if bot_degisim else (sab["bot"], "Standart"))
    r = coz(bot_alt)
    if r:
        b.bot = (r[0], r[1], bot_neden)

    cekirdek_sablon = CEKIRDEK_OZEL.get(sampiyon.alias, sab["cekirdek"])
    cekirdek = [x for x in (coz(s) for s in cekirdek_sablon) if x]
    gec = [x for x in (coz(s) for s in sab["gec"]) if x]
    durum = []
    for _, alt, neden, tur in sorted(kurallar, key=lambda x: -x[0]):
        r = coz(alt)
        if r:
            durum.append((r, neden, tur))

    secilen, adlar = [], set()
    maks = 6 if rol == "adc" else 5  # 2026'da ADC rol görevi ekstra eşya yuvası verir

    def ekle(r, neden):
        if r and r[1] not in adlar and len(secilen) < maks:
            secilen.append((r[0], r[1], neden))
            adlar.add(r[1])

    saldiri = [(r, n) for r, n, t in durum if t == "saldiri"]
    savunma = [(r, n) for r, n, t in durum if t == "savunma"]
    if a in TASIYICI:
        # Hasar taşıyanlar önce çekirdek hasarı bitirir; savunma 4. eşyadan sonra
        sira = saldiri[:1] + [(r, "Çekirdek") for r in cekirdek[2:]] + saldiri[1:] + savunma
    else:
        # Tank/dövüşçü: en önemli duruma özel eşya 3. sırada olabilir
        hepsi = [(r, n) for r, n, _ in durum]
        sira = hepsi[:1] + [(r, "Çekirdek") for r in cekirdek[2:]] + hepsi[1:]
    for r in cekirdek[:2]:
        ekle(r, "Çekirdek")
    for r, n in sira:
        ekle(r, n)
    for r in gec:
        ekle(r, "Geç oyun")
    b.esyalar = secilen

    # Notlar
    for r, neden, _ in durum[:3]:
        on = ERKEN.get(_ingilizce(r, esya_db))
        if on and esya_db.bul(on):
            b.notlar.append(f"{neden.split(':')[0]} için erken '{esya_db.bul(on)[1]}' al, sonra tamamla.")
    if profil.gorunmezlik:
        b.notlar.append("Görünmez rakip var: tılsımı Kâhin Merceği (Oracle Lens) yap, Kontrol Totemi taşı.")
    if rakip is not None:
        b.notlar.append(f"Koridor rakibin büyük ihtimalle {rakip.ad}.")
    b.b_plani = b_plani(a, b, profil, rakipler or [], esya_db)
    return b


def _ingilizce(r, esya_db):
    """Çözülmüş eşyanın İngilizce adını bulur (ERKEN tablosu için)."""
    for isim in ERKEN:
        if esya_db.bul(isim) == r:
            return isim
    return None


# ------------------------------------------------------------------
# Ortak eşya seçimleri (B planı ve maç sonu analizi de bunları kullanır)
# ------------------------------------------------------------------
def savunma_esyasi(a, hasar_tipi):
    """Senin build tipine göre, verilen hasar tipine (AD/AP) karşı savunma eşyası."""
    taraf, adc = _hasar_tarafi(a), a.startswith("adc")
    if hasar_tipi == "AD":
        return {"AD": ["Guardian Angel", "Immortal Shieldbow"] if adc else ["Death's Dance", "Randuin's Omen"],
                "AP": ["Zhonya's Hourglass"], "TANK": ["Frozen Heart", "Randuin's Omen", "Thornmail"],
                "DESTEK": ["Knight's Vow", "Locket of the Iron Solari"]}[taraf]
    return {"AD": ["Wit's End", "Mercurial Scimitar"] if adc else ["Maw of Malmortius", "Wit's End"],
            "AP": ["Banshee's Veil"], "TANK": ["Force of Nature", "Kaenic Rookern", "Spirit Visage"],
            "DESTEK": ["Mikael's Blessing", "Locket of the Iron Solari"]}[taraf]


def delme_esyasi(a, direnc):
    """direnc: 'zirh' ya da 'mr'. Senin hasar tipin uymuyorsa boş liste."""
    taraf, adc = _hasar_tarafi(a), a.startswith("adc")
    if direnc == "zirh" and taraf == "AD":
        return ["Lord Dominik's Regards"] if adc else ["Serylda's Grudge", "Black Cleaver", "Lord Dominik's Regards"]
    if direnc == "mr" and taraf == "AP":
        return ["Void Staff", "Cryptbloom"]
    return []


def antiheal_esyasi(a):
    taraf, adc = _hasar_tarafi(a), a.startswith("adc")
    return {"AD": ["Mortal Reminder"] if adc else ["Chempunk Chainsword", "Mortal Reminder"],
            "AP": ["Morellonomicon"], "TANK": ["Thornmail"], "DESTEK": []}[taraf]


ANTIHEAL_ADLARI = ["Mortal Reminder", "Chempunk Chainsword", "Morellonomicon", "Thornmail",
                   "Executioner's Calling", "Oblivion Orb", "Bramble Vest"]
DELME_ADLARI = ["Lord Dominik's Regards", "Serylda's Grudge", "Black Cleaver", "Void Staff",
                "Cryptbloom", "Terminus", "Last Whisper"]


def b_plani(a, b, profil, rakipler, esya_db):
    """Maç ÖNCESİ hazırlanan 'şu olursa bunu al' listesi. Oyun sırasında hiçbir veri
    okunmaz; Tab ekranına bakıp kararı oyuncu kendisi verir."""
    plan, kullanilan = [], {ad for _, ad, _ in b.esyalar[:3]}
    sonra = {ad for _, ad, _ in b.esyalar[3:]}

    def ekle(kosul, alternatifler):
        for isim in alternatifler:
            r = esya_db.bul(isim)
            if r:
                b.bilgi.setdefault(r[1], {"aciklama": ACIKLAMA.get(isim, ""), "alternatif": []})
                if r[1] not in kullanilan:
                    plan.append((kosul, r[0], r[1] + (" (buildde var, öne çek)" if r[1] in sonra else "")))
                    kullanilan.add(r[1])
                return

    # 1) Tehlikeli taşıyıcılar kasılırsa
    tehdit = [e for e in rakipler if e and e.sinif in ("assassin", "marksman", "mage", "fighter") and not e.tanky]
    for tip in ("AD", "AP"):
        grup = [e.ad for e in tehdit if e.hasar in (tip, "MIX")][:3]
        if grup:
            ekle(f"{' veya '.join(grup)} kasılırsa ({tip} hasar)", savunma_esyasi(a, tip))
    # 2) Rakipler direnç yığarsa
    ekle("Tab'da rakipler zırh yığıyorsa (Thornmail, Randuin, Frozen Heart...)", delme_esyasi(a, "zirh"))
    ekle("Tab'da rakipler büyü direnci yığıyorsa (Force of Nature, Kaenic Rookern...)", delme_esyasi(a, "mr"))
    # 3) İyileşenler
    iyilesen = [e.ad for e in rakipler if e and e.var("heal")]
    if iyilesen:
        ekle(f"{', '.join(iyilesen[:3])} çok iyileşiyorsa", antiheal_esyasi(a))
    # 4) CC
    merkur = esya_db.bul("Mercury's Treads")
    if profil.cc >= 2 and merkur and not (b.bot and b.bot[1] == merkur[1]):
        ekle("Sürekli CC yiyip ölüyorsan (bot değiştir)", ["Mercury's Treads"])
    return plan
