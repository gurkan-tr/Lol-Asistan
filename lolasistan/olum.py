"""Ölüm analizi (MAÇ SONRASI): maçın zaman çizelgesinden ne zaman, nerede ve kime
öldüğünü çıkarır. Sadece bitmiş maçlar için çalışır."""
from collections import Counter

HARITA = 14870  # Sihirdar Vadisi koordinat genişliği (yaklaşık)

BOLGE_AD = {"ust_koridor": "üst koridor", "alt_koridor": "alt koridor", "orta_koridor": "orta koridor",
            "nehir": "nehir", "kendi_orman": "kendi ormanın", "rakip_orman": "rakip orman",
            "kendi_us": "kendi üssün", "rakip_us": "rakip üs"}


def bolge(x, y, takim):
    """Koordinatı kabaca bir bölgeye çevirir. takim: 100 (mavi, sol alt) / 200 (kırmızı, sağ üst)."""
    toplam = x + y
    mavi_taraf = toplam < HARITA
    if toplam < 4200:
        return "kendi_us" if takim == 100 else "rakip_us"
    if toplam > 2 * HARITA - 4200:
        return "kendi_us" if takim == 200 else "rakip_us"
    if x < 2300 or y > HARITA - 2300:
        return "ust_koridor"
    if y < 2300 or x > HARITA - 2300:
        return "alt_koridor"
    if abs(x - y) < 1700:
        return "orta_koridor"
    if abs(toplam - HARITA) < 1900:
        return "nehir"
    return "kendi_orman" if mavi_taraf == (takim == 100) else "rakip_orman"


def olumleri_cikar(oyun, zaman_cizelgesi, puuid):
    """oyun: /lol-match-history/v1/games/{id}, zaman_cizelgesi: /game-timelines/{id}"""
    kimlik = {p["participantId"]: (p.get("player") or {}).get("puuid") for p in oyun.get("participantIdentities", [])}
    katilimci = {p["participantId"]: p for p in oyun.get("participants", [])}
    ben = next((pid for pid, pu in kimlik.items() if pu == puuid), None)
    if ben is None:
        return None
    takim = katilimci[ben].get("teamId", 100)
    olumler = []
    for kare in zaman_cizelgesi.get("frames", []):
        for o in kare.get("events", []):
            if o.get("type") != "CHAMPION_KILL" or o.get("victimId") != ben:
                continue
            poz = o.get("position") or {}
            x, y = poz.get("x", 0), poz.get("y", 0)
            katil = katilimci.get(o.get("killerId"), {}).get("championId")
            olumler.append({"dk": round(o.get("timestamp", 0) / 60000, 1), "x": x, "y": y,
                            "bolge": bolge(x, y, takim), "katil": katil,
                            "yardim": len(o.get("assistingParticipantIds") or [])})
    olumler.sort(key=lambda d: d["dk"])
    return {"takim": takim, "olumler": olumler}


def yorumla(sonuc, ad_bul):
    """Ölümlerden Türkçe öneriler çıkarır. ad_bul: championId -> görünen ad"""
    if not sonuc:
        return []
    ol = sonuc["olumler"]
    if not ol:
        return [("iyi", "Bu maçta hiç ölmedin. 👏")]
    notlar = []
    erken = [o for o in ol if o["dk"] < 14]
    if len(erken) >= 3:
        notlar.append(("uyari", f"İlk 14 dakikada {len(erken)} kez öldün. Koridor evresinde rakibin "
                                "ormancısını takip et; görüşün yokken dalgayı ileri itme."))
    riskli = [o for o in ol if o["bolge"] in ("rakip_orman", "nehir")]
    if len(riskli) >= 2:
        yer = Counter(BOLGE_AD[o["bolge"]] for o in riskli).most_common(1)[0][0]
        notlar.append(("uyari", f"{len(riskli)} ölümün nehirde ya da rakip ormanında; en çok {yer}. "
                                "Bu bölgelere görüşsüz girme, önce totem koy ya da takımla gir."))
    tek = [o for o in ol if o["yardim"] == 0]
    if len(tek) >= 3:
        notlar.append(("uyari", f"{len(tek)} ölümün tek bir rakibe karşı (yardımsız). "
                                "Bire bir savaşları daha seçici gir."))
    katiller = Counter(o["katil"] for o in ol if o["katil"])
    if katiller:
        kim, kac = katiller.most_common(1)[0]
        if kac >= 3:
            notlar.append(("uyari", f"{ad_bul(kim)} seni {kac} kez öldürdü. Onun güçlü olduğu anlarda "
                                    "(ulti hazırken, eşya avantajındayken) mesafeni koru."))
    gec = [o for o in ol if o["dk"] >= 25]
    if len(gec) >= 3:
        notlar.append(("bilgi", f"Geç oyunda {len(gec)} kez öldün. Geç oyunda tek ölüm bile baron ya da "
                                "ejderha kaybettirebilir; yan koridorlarda tek başına kalma."))
    if not notlar:
        notlar.append(("iyi", f"{len(ol)} ölümün belirgin bir kalıp göstermiyor."))
    return notlar
