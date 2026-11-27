"""LoL istemcisinin (League Client) yerel API'sine bağlantı.

İstemci açıkken bilgisayarında 127.0.0.1 üzerinde bir API çalışır. Port ve şifre
ya çalışan işlemin komut satırından ya da oyun klasöründeki 'lockfile'dan okunur."""
import os
import re
import time
import uuid
from dataclasses import dataclass, field

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

POZISYON = {"top": "top", "jungle": "jungle", "middle": "mid", "bottom": "adc", "utility": "support"}

VARSAYILAN_KLASORLER = [
    r"C:\Riot Games\League of Legends",
    r"D:\Riot Games\League of Legends",
    r"E:\Riot Games\League of Legends",
    r"C:\Program Files\Riot Games\League of Legends",
    r"D:\Games\Riot Games\League of Legends",
    "/Applications/League of Legends.app/Contents/LoL",
]


class LCU:
    def __init__(self, port, sifre):
        self.taban = f"https://127.0.0.1:{port}"
        self.s = requests.Session()
        self.s.auth = ("riot", sifre)
        # İstemci kendi imzalı sertifikasını kullanır; yalnızca 127.0.0.1'e gidiyoruz.
        self.s.verify = False

    def get(self, yol):
        r = self.s.get(self.taban + yol, timeout=4)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def put(self, yol, govde):
        r = self.s.put(self.taban + yol, json=govde, timeout=6)
        r.raise_for_status()
        return r

    def post(self, yol, govde):
        r = self.s.post(self.taban + yol, json=govde, timeout=6)
        r.raise_for_status()
        return r.json() if r.content else None

    def delete(self, yol):
        r = self.s.delete(self.taban + yol, timeout=6)
        r.raise_for_status()

    @staticmethod
    def bul(lol_klasoru=""):
        # 1) Çalışan istemci işleminden
        try:
            import psutil
            for p in psutil.process_iter(["name", "cmdline"]):
                ad = (p.info.get("name") or "").lower()
                if not ad.startswith("leagueclientux"):
                    continue
                arg = " ".join(p.info.get("cmdline") or [])
                port = re.search(r"--app-port=(\d+)", arg)
                sifre = re.search(r"--remoting-auth-token=([\w\-_]+)", arg)
                if port and sifre:
                    return LCU(port.group(1), sifre.group(1))
        except Exception:
            pass
        # 2) lockfile'dan
        for k in [lol_klasoru] + VARSAYILAN_KLASORLER:
            if not k:
                continue
            yol = os.path.join(k, "lockfile")
            if os.path.exists(yol):
                try:
                    with open(yol, encoding="utf-8") as f:
                        _, _, port, sifre, _ = f.read().strip().split(":")
                    return LCU(port, sifre)
                except Exception:
                    continue
        return None

    # ---------- yardımcı uç noktalar ----------
    def sampiyon_kayitlari(self):
        """İstemcinin kendi şampiyon listesi (internet gerekmez)."""
        veri = self.get("/lol-game-data/assets/v1/champion-summary.json") or []
        return [(c["id"], c.get("alias"), c.get("name"), c.get("roles", []),
                 "mage" in (c.get("roles") or [])[:1]) for c in veri if c.get("id", -1) > 0]

    def sahip_olunanlar(self):
        try:
            veri = self.get("/lol-champions/v1/owned-champions-minimal") or []
        except Exception:
            return None
        ids = set()
        for c in veri:
            own = c.get("ownership") or {}
            if own.get("owned") or (own.get("rental") or {}).get("rented") or c.get("freeToPlay"):
                ids.add(c.get("id"))
        return ids or None

    def ustaliklar(self):
        try:
            veri = self.get("/lol-champion-mastery/v1/local-player/champion-mastery") or []
        except Exception:
            return {}
        return {c["championId"]: c.get("championPoints", 0) for c in veri if "championId" in c}

    def onerilen_sayfalar(self, sampiyon_id, rol):
        """İstemcinin bu şampiyon+koridor için önerdiği rün sayfaları (Riot istatistikleri).
        Büyü önerileri de içinde (summonerSpellIds)."""
        poz = {"top": "TOP", "jungle": "JUNGLE", "mid": "MIDDLE", "adc": "BOTTOM", "support": "UTILITY"}.get(rol, "MIDDLE")
        for p in (poz, poz.lower()):
            try:
                v = self.get(f"/lol-perks/v1/recommended-pages/champion/{sampiyon_id}/position/{p}/map/11")
            except Exception:
                v = None
            if v:
                return v
        return []

    def secim_ekrani(self):
        return self.get("/lol-champ-select/v1/session")

    def faz(self):
        """None, Lobby, Matchmaking, ChampSelect, InProgress, EndOfGame..."""
        try:
            return self.get("/lol-gameflow/v1/gameflow-phase")
        except Exception:
            return None

    def mac_sonu_verisi(self):
        """Sadece maç bittikten sonra, maç sonu ekranında dolu gelir."""
        try:
            return self.get("/lol-end-of-game/v1/eog-stats-block")
        except Exception:
            return None


@dataclass
class SecimDurumu:
    rol: str = None
    benim_id: int = 0
    kilitli: bool = False
    takim_ids: list = field(default_factory=list)
    takim_rolleri: dict = field(default_factory=dict)   # rol -> champ id
    rakip_ids: list = field(default_factory=list)
    yasak_ids: set = field(default_factory=set)
    ban_asamasi: bool = False      # benim ban sıram geldi / gelecek
    sicra_d: bool = False          # Sıçra şu an D tuşunda mı
    sira_bende: str = None         # "ban" / "pick": şu an benim sıram

    def anahtar(self):
        return (self.rol, self.benim_id, self.kilitli, tuple(self.takim_ids),
                tuple(self.rakip_ids), tuple(sorted(self.yasak_ids)), self.ban_asamasi, self.sira_bende)


def secim_oku(oturum) -> SecimDurumu:
    d = SecimDurumu()
    hucre = oturum.get("localPlayerCellId")
    for o in oturum.get("myTeam", []):
        cid = o.get("championId") or o.get("championPickIntent") or 0
        pos = POZISYON.get((o.get("assignedPosition") or "").lower())
        if o.get("cellId") == hucre:
            d.rol = pos
            d.benim_id = cid
            d.sicra_d = o.get("spell1Id") == 4
        elif cid:
            d.takim_ids.append(cid)
            if pos:
                d.takim_rolleri[pos] = cid
    for o in oturum.get("theirTeam", []):
        if o.get("championId"):
            d.rakip_ids.append(o["championId"])
    bans = oturum.get("bans") or {}
    d.yasak_ids |= set(bans.get("myTeamBans", []) or []) | set(bans.get("theirTeamBans", []) or [])
    for grup in oturum.get("actions", []) or []:
        for a in grup:
            if a.get("type") == "ban" and a.get("completed") and a.get("championId"):
                d.yasak_ids.add(a["championId"])
            if a.get("type") == "pick" and a.get("actorCellId") == hucre and a.get("completed"):
                d.kilitli = True
            if a.get("type") == "ban" and a.get("actorCellId") == hucre and not a.get("completed"):
                d.ban_asamasi = True
            if a.get("actorCellId") == hucre and a.get("isInProgress") and not a.get("completed") \
                    and a.get("type") in ("ban", "pick"):
                d.sira_bende = a["type"]
    d.yasak_ids.discard(0)
    return d


BASLIK = "LoL Asistan -"


def item_set_aktar(lcu: LCU, sampiyon, build):
    """Build'i istemciye eşya seti olarak yazar (mağazada 'Eşya Setleri' altında görünür).
    Kendi eski setlerini siler, senin diğer setlerine dokunmaz."""
    ben = lcu.get("/lol-summoner/v1/current-summoner")
    yol = f"/lol-item-sets/v1/item-sets/{ben['summonerId']}/sets"
    mevcut = lcu.get(yol) or {}
    setler = [s for s in mevcut.get("itemSets", []) if not str(s.get("title", "")).startswith(BASLIK)]

    def blok(ad, liste):
        return {"type": ad, "items": [{"id": str(i), "count": c} for i, c in liste if i]}

    bloklar = [
        blok("Başlangıç", [(i, adet) for i, _, adet in build.baslangic]),
        blok("Bot + Eşyalar (sırayla)", ([(build.bot[0], 1)] if build.bot else []) +
             [(i, 1) for i, _, _ in build.esyalar]),
        blok("B planı — Tab'a bak, karar senin", [(i, 1) for _, i, _ in build.b_plani]),
        blok("Kontrol Totemi", [("2055", 2)]),
    ]
    setler.append({
        "title": f"{BASLIK} {sampiyon.ad}",
        "associatedChampions": [sampiyon.id],
        "associatedMaps": [11],
        "blocks": [b for b in bloklar if b["items"]],
        "map": "any", "mode": "any", "preferredItemSlots": [], "sortrank": 0,
        "startedFrom": "blank", "type": "custom", "uid": str(uuid.uuid4()),
    })
    lcu.put(yol, {"accountId": mevcut.get("accountId", ben.get("accountId", 0)),
                  "itemSets": setler, "timestamp": int(time.time() * 1000)})


RUN_BASLIK = "LoL Asistan"


def run_sayfasi_yaz(lcu: LCU, sampiyon, sayfa):
    """Rün sayfasını istemciye yazar ve seçili yapar. Önce kendi eski sayfamızı siler;
    senin oluşturduğun sayfalara dokunmaz."""
    sayfalar = lcu.get("/lol-perks/v1/pages") or []
    for p in sayfalar:
        if str(p.get("name", "")).startswith(RUN_BASLIK) and p.get("isDeletable", True):
            lcu.delete(f"/lol-perks/v1/pages/{p['id']}")
    govde = {"name": f"{RUN_BASLIK}: {sampiyon.ad}"[:25], "primaryStyleId": sayfa.ana["id"],
             "subStyleId": sayfa.yan["id"], "selectedPerkIds": sayfa.perk_ids(), "current": True}
    try:
        yeni = lcu.post("/lol-perks/v1/pages", govde)
    except requests.HTTPError:
        raise RuntimeError("Boş rün sayfası yeri yok. İstemcide kullanmadığın bir rün sayfasını sil, "
                           "sonra 'Rünleri uygula'ya tekrar bas.")
    if yeni and yeni.get("id"):
        try:
            lcu.put("/lol-perks/v1/currentpage", yeni["id"])
        except Exception:
            pass


def buyuleri_yaz(lcu: LCU, buyu):
    """Sihirdar büyülerini seçim ekranında ayarlar (Sıçra'yı alıştığın tuşta bırakır)."""
    b1, b2 = buyu.idler()
    r = lcu.s.patch(lcu.taban + "/lol-champ-select/v1/session/my-selection",
                    json={"spell1Id": b1, "spell2Id": b2}, timeout=5)
    if r.status_code >= 400:
        raise RuntimeError("Büyüler ayarlanamadı (seçim ekranı kapanmış olabilir).")
