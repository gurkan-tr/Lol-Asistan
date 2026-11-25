"""Senin maç geçmişin: şampiyon başına kazanma oranı, zorlandığın eşleşmeler,
sana en çok kaybettiren şampiyonlar. İstemciden yalnızca BİTMİŞ maçlar okunur.
Okunan maçlar diske kaydedilir; her seferinde sadece yeni maçlar indirilir."""
import json
import os
import re
from collections import defaultdict
from dataclasses import dataclass, field

from .champs import KOK

KLASOR = os.path.join(KOK, "kisisel")
POZ = {"TOP": "top", "JUNGLE": "jungle", "MIDDLE": "mid", "MID": "mid"}


def _rol(timeline):
    lane = (timeline or {}).get("lane", "").upper()
    role = (timeline or {}).get("role", "").upper()
    if lane in POZ:
        return POZ[lane]
    if lane in ("BOTTOM", "BOT"):
        return "support" if "SUPPORT" in role else "adc"
    return None


def mac_coz(oyun, puuid=None):
    """LCU /lol-match-history/v1/games/{id} cevabını sade bir kayda çevirir."""
    if oyun.get("mapId") not in (11, None):
        return None
    kimlik = {p["participantId"]: (p.get("player") or {}) for p in oyun.get("participantIdentities", [])}
    ben = None
    for p in oyun.get("participants", []):
        pl = kimlik.get(p["participantId"], {})
        if puuid and pl.get("puuid") == puuid:
            ben = p
    if ben is None:
        if len(oyun.get("participants", [])) == 1:
            ben = oyun["participants"][0]
        else:
            return None
    rol = _rol(ben.get("timeline"))
    rakipler = [p for p in oyun.get("participants", []) if p.get("teamId") != ben.get("teamId")]
    koridor = None
    if rol:
        for p in rakipler:
            if _rol(p.get("timeline")) == rol:
                koridor = p["championId"]
                break
    st = ben.get("stats", {})
    return {
        "id": oyun.get("gameId"), "zaman": oyun.get("gameCreation", 0), "kuyruk": oyun.get("queueId"),
        "sampiyon": ben.get("championId"), "rol": rol, "kazandi": bool(st.get("win")),
        "k": st.get("kills", 0), "d": st.get("deaths", 0), "a": st.get("assists", 0),
        "rakipler": [p["championId"] for p in rakipler], "koridor_rakibi": koridor,
    }


@dataclass
class Sayac:
    mac: int = 0
    galibiyet: int = 0
    k: int = 0
    d: int = 0
    a: int = 0

    def ekle(self, r):
        self.mac += 1
        self.galibiyet += r["kazandi"]
        self.k += r["k"]
        self.d += r["d"]
        self.a += r["a"]

    @property
    def oran(self):
        return self.galibiyet / self.mac if self.mac else 0.0

    @property
    def kda(self):
        return (self.k + self.a) / max(1, self.d)


@dataclass
class Gecmis:
    puuid: str = ""
    maclar: dict = field(default_factory=dict)   # id -> kayıt

    # ---------- disk ----------
    def _yol(self):
        return os.path.join(KLASOR, f"gecmis_{re.sub(r'[^A-Za-z0-9-]', '', self.puuid) or 'yerel'}.json")

    def yukle(self, puuid):
        self.puuid = puuid
        try:
            with open(self._yol(), encoding="utf-8") as f:
                self.maclar = {int(k): v for k, v in json.load(f).items()}
        except (FileNotFoundError, json.JSONDecodeError, ValueError):
            self.maclar = {}

    def son_yukle(self):
        """Program açılırken, istemci bağlanmadan önce en son kaydedilen geçmişi yükler."""
        if not os.path.isdir(KLASOR):
            return
        dosyalar = [os.path.join(KLASOR, f) for f in os.listdir(KLASOR) if f.startswith("gecmis_")]
        if dosyalar:
            son = max(dosyalar, key=os.path.getmtime)
            self.yukle(os.path.basename(son)[7:-5])

    def kaydet(self):
        os.makedirs(KLASOR, exist_ok=True)
        with open(self._yol(), "w", encoding="utf-8") as f:
            json.dump(self.maclar, f)

    # ---------- istemciden oku ----------
    def guncelle(self, lcu, en_fazla=100, ilerleme=None):
        """Yeni maçları indirir. Dönüş: eklenen maç sayısı."""
        ben = lcu.get("/lol-summoner/v1/current-summoner") or {}
        puuid = ben.get("puuid", "")
        if puuid != self.puuid:
            self.yukle(puuid)
        idler = []
        for bas in range(0, en_fazla, 20):
            veri = lcu.get(f"/lol-match-history/v1/products/lol/current-summoner/matches"
                           f"?begIndex={bas}&endIndex={bas + 20}") or {}
            oyunlar = (veri.get("games") or {}).get("games") or []
            if not oyunlar:
                break
            idler += [g["gameId"] for g in oyunlar if g.get("mapId", 11) == 11]
            if len(oyunlar) < 20:
                break
        yeni = [i for i in idler if i not in self.maclar]
        for n, gid in enumerate(yeni, 1):
            if ilerleme:
                ilerleme(n, len(yeni))
            try:
                oyun = lcu.get(f"/lol-match-history/v1/games/{gid}")
            except Exception:
                continue
            kayit = mac_coz(oyun or {}, puuid)
            if kayit:
                self.maclar[gid] = kayit
        if yeni:
            self.kaydet()
        return len(yeni)

    # ---------- istatistikler ----------
    def sirali(self, adet=None):
        m = sorted(self.maclar.values(), key=lambda r: -r["zaman"])
        return m[:adet] if adet else m

    def sampiyon_istatistik(self, adet=60):
        s = defaultdict(Sayac)
        for r in self.sirali(adet):
            s[r["sampiyon"]].ekle(r)
        return dict(s)

    def koridor_rakibi_istatistik(self, adet=100):
        s = defaultdict(Sayac)
        for r in self.sirali(adet):
            if r.get("koridor_rakibi"):
                s[r["koridor_rakibi"]].ekle(r)
        return dict(s)

    def rakip_istatistik(self, adet=100):
        """Rakip takımda gördüğün her şampiyona karşı senin sonucun."""
        s = defaultdict(Sayac)
        for r in self.sirali(adet):
            for c in r.get("rakipler", []):
                s[c].ekle(r)
        return dict(s)

    def genel(self, adet=60):
        s = Sayac()
        for r in self.sirali(adet):
            s.ekle(r)
        return s


def sik_hatalar():
    """Maç sonu analizlerinde en sık tekrarlanan uyarılar."""
    klasor = os.path.join(KOK, "mac_gecmisi")
    tur = {"anti-heal": "Anti-heal almamak", "delme": "Delme eşyası almamak",
           "savunma yoktu": "Kasılan rakibe karşı savunma almamak", "kez öldün": "Çok ölmek"}
    say = defaultdict(int)
    toplam = 0
    if os.path.isdir(klasor):
        for ad in os.listdir(klasor):
            if not ad.endswith(".txt"):
                continue
            toplam += 1
            with open(os.path.join(klasor, ad), encoding="utf-8") as f:
                metin = f.read()
            for anahtar, etiket in tur.items():
                if any(anahtar in satir for satir in metin.splitlines() if satir.startswith("[!]")):
                    say[etiket] += 1
    return toplam, sorted(say.items(), key=lambda x: -x[1])
