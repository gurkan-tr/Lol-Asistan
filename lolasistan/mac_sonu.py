"""Maç SONU analizi: maç bittikten sonra, istemcinin maç sonu ekranındaki verilerle
'bir dahaki sefere ne farklı yapabilirdin' özetini çıkarır.

Riot'un kuralı: önce oyna, sonra analiz et. Bu modül yalnızca maç bittikten sonra çalışır.
Maç sürerken program hiçbir oyun verisi okumaz."""
import os
import time
from dataclasses import dataclass, field

from .build import (ANTIHEAL_ADLARI, DELME_ADLARI, antiheal_esyasi, arketip_bul,
                    delme_esyasi, savunma_esyasi)
from .champs import KOK, norm


@dataclass
class Oyuncu:
    champ_id: int
    takim: int
    esyalar: list
    k: int = 0
    d: int = 0
    a: int = 0
    fiziksel: int = 0
    buyu: int = 0
    gercek: int = 0
    altin: int = 0
    ben: bool = False
    kazandi: bool = None

    @property
    def toplam_hasar(self):
        return self.fiziksel + self.buyu + self.gercek


@dataclass
class MacSonu:
    oyun_id: int
    oyuncular: list
    analiz: list = field(default_factory=list)   # (tür, mesaj) tür: iyi / uyari / bilgi
    ozet: str = ""


def _stat(st, *anahtarlar):
    for k in anahtarlar:
        if k in st and st[k] is not None:
            try:
                return int(st[k])
            except (TypeError, ValueError):
                pass
    return 0


def eog_coz(veri):
    """/lol-end-of-game/v1/eog-stats-block verisini ortak biçime çevirir."""
    if not veri or not veri.get("teams"):
        return None
    ben_id = (veri.get("localPlayer") or {}).get("championId")
    ben_takim = (veri.get("localPlayer") or {}).get("teamId")
    oyuncular = []
    for t in veri["teams"]:
        for p in t.get("players", []):
            st = p.get("stats", {}) or {}
            o = Oyuncu(
                champ_id=p.get("championId", 0), takim=p.get("teamId", t.get("teamId")),
                esyalar=[i for i in (p.get("items") or []) if i],
                k=_stat(st, "CHAMPIONS_KILLED", "kills"), d=_stat(st, "NUM_DEATHS", "deaths"),
                a=_stat(st, "ASSISTS", "assists"),
                fiziksel=_stat(st, "PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS", "physicalDamageDealtToChampions"),
                buyu=_stat(st, "MAGIC_DAMAGE_DEALT_TO_CHAMPIONS", "magicDamageDealtToChampions"),
                gercek=_stat(st, "TRUE_DAMAGE_DEALT_TO_CHAMPIONS", "trueDamageDealtToChampions"),
                altin=_stat(st, "GOLD_EARNED", "goldEarned"),
                kazandi=t.get("isWinningTeam"),
            )
            o.ben = (o.champ_id == ben_id and o.takim == ben_takim)
            oyuncular.append(o)
    if not any(o.ben for o in oyuncular):
        return None
    return MacSonu(oyun_id=veri.get("gameId", 0), oyuncular=oyuncular)


def analiz_et(mac: MacSonu, db, esya, rol, tahmini_build=None):
    ben = next(o for o in mac.oyuncular if o.ben)
    rakipler = [o for o in mac.oyuncular if o.takim != ben.takim]
    sampiyon = db.id_ile(ben.champ_id)
    if sampiyon is None or not rakipler:
        mac.analiz.append(("bilgi", "Bu maç için yeterli veri yok."))
        return mac
    a = arketip_bul(sampiyon, rol)
    benim_en = {(esya.id_bilgi(i) or {}).get("en", "") for i in ben.esyalar}
    ad = lambda o: (db.id_ile(o.champ_id).ad if db.id_ile(o.champ_id) else f"#{o.champ_id}")
    sonuc = "Kazandın 🎉" if ben.kazandi else "Kaybettin" if ben.kazandi is False else ""
    mac.ozet = f"{sampiyon.ad} · {ben.k}/{ben.d}/{ben.a} {('· ' + sonuc) if sonuc else ''}"
    A = mac.analiz

    def oner(alternatifler):
        for isim in alternatifler:
            r = esya.bul(isim)
            if r:
                return r[1]
        return None

    # 1) Gerçek hasar dağılımı
    fz = sum(o.fiziksel for o in rakipler)
    by = sum(o.buyu for o in rakipler)
    tp = fz + by + sum(o.gercek for o in rakipler)
    if tp:
        A.append(("bilgi", f"Rakiplerin gerçek hasar dağılımı: %{round(fz * 100 / tp)} fiziksel, "
                           f"%{round(by * 100 / tp)} büyü, %{round((tp - fz - by) * 100 / tp)} gerçek."))
    benim_zirh = sum(1 for i in ben.esyalar if (esya.id_bilgi(i) or {}).get("zirh") and (esya.id_bilgi(i) or {}).get("tamam"))
    benim_mr = sum(1 for i in ben.esyalar if (esya.id_bilgi(i) or {}).get("mr") and (esya.id_bilgi(i) or {}).get("tamam"))

    # 2) Kasılan rakip
    def tehdit(o):
        pay = o.toplam_hasar / tp if tp else 0
        return o.k * 2 + o.a * 0.5 - o.d * 1.5 + pay * 30
    en_tehlikeli = max(rakipler, key=tehdit)
    pay = en_tehlikeli.toplam_hasar / tp if tp else 0
    if en_tehlikeli.k >= 6 or (pay >= 0.3 and en_tehlikeli.k >= en_tehlikeli.d):
        tip = "AD" if en_tehlikeli.fiziksel >= en_tehlikeli.buyu else "AP"
        var = benim_zirh if tip == "AD" else benim_mr
        mesaj = (f"{ad(en_tehlikeli)} kasıldı ({en_tehlikeli.k}/{en_tehlikeli.d}/{en_tehlikeli.a}, "
                 f"takımının hasarının %{round(pay * 100)}'i, {tip} hasar).")
        if var:
            A.append(("iyi", mesaj + f" Buildinde {'zırh' if tip == 'AD' else 'büyü direnci'} vardı, iyi."))
        else:
            e = oner(savunma_esyasi(a, tip))
            A.append(("uyari", mesaj + (f" Buildinde ona karşı savunma yoktu → bir dahakine öne çek: {e}"
                                         if e else " Ona karşı savunma eşyası düşünebilirdin.")))

    # 3) Rakiplerin direnç yığması
    tamam = [(esya.id_bilgi(i) or {}) for o in rakipler for i in o.esyalar]
    tamam = [x for x in tamam if x.get("tamam")]
    zirh_say = sum(1 for x in tamam if x.get("zirh"))
    mr_say = sum(1 for x in tamam if x.get("mr"))
    delme_var = any(e in benim_en for e in DELME_ADLARI)
    for direnc, sayi, ad_tr in (("zirh", zirh_say, "zırh"), ("mr", mr_say, "büyü direnci")):
        alt = delme_esyasi(a, direnc)
        if alt and sayi >= 5:
            if delme_var:
                A.append(("iyi", f"Rakipler {sayi} {ad_tr} eşyası aldı, sen de delme eşyası almışsın."))
            else:
                A.append(("uyari", f"Rakipler toplam {sayi} {ad_tr} eşyası aldı ama sende delme yoktu "
                                   f"→ '{oner(alt)}' hasarını ciddi artırırdı."))

    # 4) İyileşme
    iyilesen = [ad(o) for o in rakipler if db.id_ile(o.champ_id) and db.id_ile(o.champ_id).var("heal")]
    ah_var = any(e in benim_en for e in ANTIHEAL_ADLARI)
    if len(iyilesen) >= 2:
        if ah_var:
            A.append(("iyi", f"Anti-heal almışsın ({', '.join(iyilesen)} iyileşiyordu), iyi."))
        else:
            e = oner(antiheal_esyasi(a))
            if e:
                A.append(("uyari", f"{', '.join(iyilesen)} iyileşiyordu ama anti-heal almadın → '{e}'."))

    # 5) Çok ölüm
    if ben.d >= 8 and not (benim_zirh or benim_mr):
        A.append(("uyari", f"{ben.d} kez öldün ve hiç savunma eşyan yoktu. Bir savunma eşyası "
                           "(ya da Zhonya/GA gibi hayatta kalma eşyası) denemeye değer."))

    # 6) Önerilen buildle karşılaştırma
    if tahmini_build:
        alinan = {(esya.id_bilgi(i) or {}).get("ad") for i in ben.esyalar}
        eksik = [ad_ for _, ad_, _ in tahmini_build.esyalar[:3] if ad_ not in alinan]
        if eksik and len(ben.esyalar) >= 4:
            A.append(("bilgi", "Önerilen ilk 3 eşyadan almadıkların: " + ", ".join(eksik)))
    if not any(t == "uyari" for t, _ in A):
        A.append(("iyi", "Build tarafında belirgin bir hata görünmüyor. 👍"))
    return mac


def kaydet(mac: MacSonu, yol=None):
    klasor = os.path.join(KOK, "mac_gecmisi")
    os.makedirs(klasor, exist_ok=True)
    yol = yol or os.path.join(klasor, time.strftime("%Y-%m-%d_%H-%M") + f"_{norm(mac.ozet.split('·')[0]) or 'mac'}.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(mac.ozet + "\n\n")
        for tur, m in mac.analiz:
            f.write({"iyi": "[✓] ", "uyari": "[!] ", "bilgi": "[i] "}[tur] + m + "\n")
    return yol
