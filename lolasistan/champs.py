"""Şampiyon veritabanı: hasar tipi, sınıf, roller, özellikler + counter tablosu."""
import json
import os
import re
import unicodedata
from dataclasses import dataclass, field

import sys

if getattr(sys, "frozen", False):          # PyInstaller ile .exe yapıldıysa
    KOK = os.path.dirname(sys.executable)   # yazılabilir: config, cache, maç geçmişi
    PAKET = getattr(sys, "_MEIPASS", KOK)   # salt okunur: data/, ui/
else:
    KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PAKET = KOK
VERI = os.path.join(PAKET, "data")

ROLLER = ["top", "jungle", "mid", "adc", "support"]
ROL_AD = {"top": "Top", "jungle": "Orman", "mid": "Mid", "adc": "ADC", "support": "Destek"}
ROL_TAKMA = {
    "top": "top", "ust": "top", "st": "top",
    "jungle": "jungle", "jg": "jungle", "jung": "jungle", "orman": "jungle",
    "mid": "mid", "middle": "mid", "orta": "mid",
    "adc": "adc", "bot": "adc", "bottom": "adc", "alt": "adc",
    "sup": "support", "supp": "support", "support": "support", "utility": "support", "destek": "support",
}
SINIF_AD = {
    "tank": "Tank", "fighter": "Dövüşçü", "assassin": "Suikastçı",
    "mage": "Büyücü", "marksman": "Nişancı", "enchanter": "Destek-büyücü",
}

TAKMA_ADLAR = {
    "mf": "MissFortune", "tf": "TwistedFate", "j4": "JarvanIV", "jarvan": "JarvanIV",
    "lee": "LeeSin", "yi": "MasterYi", "master": "MasterYi", "kha": "Khazix",
    "vel": "Velkoz", "ww": "Warwick", "voli": "Volibear", "morde": "Mordekaiser",
    "cassio": "Cassiopeia", "cass": "Cassiopeia", "heimer": "Heimerdinger", "kog": "KogMaw",
    "xin": "XinZhao", "asol": "AurelionSol", "gp": "Gangplank", "mundo": "DrMundo",
    "cho": "Chogath", "tahm": "TahmKench", "blitz": "Blitzcrank", "naut": "Nautilus",
    "ez": "Ezreal", "cait": "Caitlyn", "kai": "Kaisa", "trist": "Tristana",
    "vlad": "Vladimir", "malz": "Malzahar", "lb": "Leblanc", "fiddle": "Fiddlesticks",
    "wukong": "MonkeyKing", "wu": "MonkeyKing", "rek": "RekSai", "bel": "Belveth",
    "sera": "Seraphine", "eve": "Evelynn", "kat": "Katarina", "ori": "Orianna",
    "kass": "Kassadin", "liss": "Lissandra", "sej": "Sejuani", "zil": "Zilean",
    "ali": "Alistar", "aph": "Aphelios", "noc": "Nocturne", "nid": "Nidalee",
    "nida": "Nidalee", "hec": "Hecarim", "trynd": "Tryndamere", "tryn": "Tryndamere",
    "panth": "Pantheon", "renek": "Renekton", "gang": "Gangplank", "naafi": "Naafiri",
}

# LCU / Data Dragon sınıf etiketlerini bizim sınıflara çevirir (bilinmeyen şampiyonlar için)
_ETIKET = {"tank": "tank", "fighter": "fighter", "assassin": "assassin", "mage": "mage",
           "marksman": "marksman", "support": "enchanter"}
_SINIF_ROL = {"marksman": "adc", "mage": "mid", "assassin": "mid", "tank": "top",
              "fighter": "top", "enchanter": "support"}


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


@dataclass
class Sampiyon:
    alias: str
    hasar: str            # AD / AP / MIX
    sinif: str
    roller: list
    ozellik: set = field(default_factory=set)
    ad: str = ""          # ekranda görünen isim
    id: int = 0
    tahmini: bool = False  # veritabanında yoksa etiketlerden tahmin edildi

    def __post_init__(self):
        if not self.ad:
            self.ad = self.alias

    def var(self, oz: str) -> bool:
        return oz in self.ozellik

    @property
    def tanky(self) -> bool:
        return self.sinif == "tank" or "tank" in self.ozellik

    @property
    def menzilli(self) -> bool:
        return "ranged" in self.ozellik or self.sinif == "marksman"

    def __hash__(self):
        return hash(self.alias)

    def __eq__(self, o):
        return isinstance(o, Sampiyon) and o.alias == self.alias


class SampiyonDB:
    def __init__(self, veri_klasoru: str = VERI):
        self.sampiyonlar: dict[str, Sampiyon] = {}
        self._id: dict[int, Sampiyon] = {}
        self._yukle_tablo(os.path.join(veri_klasoru, "champions.txt"))
        with open(os.path.join(veri_klasoru, "counters.json"), encoding="utf-8") as f:
            ham = json.load(f)
        self.counters = {k: v for k, v in ham.items() if not k.startswith("_")}

    # ---------- yükleme ----------
    def _yukle_tablo(self, yol):
        with open(yol, encoding="utf-8") as f:
            for satir in f:
                satir = satir.strip()
                if not satir or satir.startswith("#"):
                    continue
                p = satir.split()
                if len(p) < 4:
                    continue
                alias, hasar, sinif, roller = p[0], p[1].upper(), p[2], p[3]
                oz = p[4] if len(p) > 4 else "-"
                self.sampiyonlar[alias] = Sampiyon(
                    alias=alias, hasar=hasar, sinif=sinif,
                    roller=[r for r in roller.split(",") if r and r != "-"],
                    ozellik={o for o in oz.split(",") if o and o != "-"},
                )

    def id_esle(self, kayitlar):
        """kayitlar: (id, alias, gorunen_ad, sinif_etiketleri, ap_mi) listesi.
        Veritabanında olmayan yeni şampiyonları etiketlerden tahmin ederek ekler."""
        for cid, alias, ad, etiketler, ap_mi in kayitlar:
            if cid is None or int(cid) <= 0:
                continue
            s = self.sampiyonlar.get(alias)
            if s is None:
                siniflar = [_ETIKET[e.lower()] for e in etiketler if e.lower() in _ETIKET]
                sinif = siniflar[0] if siniflar else "fighter"
                s = Sampiyon(alias=alias, hasar="AP" if ap_mi else "AD", sinif=sinif,
                             roller=[_SINIF_ROL.get(sinif, "top")],
                             ozellik={"ranged"} if sinif in ("marksman", "mage") else set(),
                             tahmini=True)
                self.sampiyonlar[alias] = s
            s.id = int(cid)
            if ad:
                s.ad = ad
            self._id[int(cid)] = s

    # ---------- erişim ----------
    def id_ile(self, cid):
        if not cid:
            return None
        return self._id.get(int(cid))

    def bul(self, metin: str):
        if not metin:
            return None
        n = norm(metin)
        if not n:
            return None
        for s in self.sampiyonlar.values():
            if norm(s.alias) == n or norm(s.ad) == n:
                return s
        if n in TAKMA_ADLAR:
            return self.sampiyonlar.get(TAKMA_ADLAR[n])
        adaylar = [s for s in self.sampiyonlar.values()
                   if norm(s.alias).startswith(n) or norm(s.ad).startswith(n)]
        return adaylar[0] if len(adaylar) == 1 else None

    def counterlayanlar(self, s: Sampiyon) -> list:
        """s'ye karşı iyi olan şampiyon alias'ları."""
        return self.counters.get(s.alias, [])

    def iyi_mi(self, aday: Sampiyon, rakip: Sampiyon) -> bool:
        return aday.alias in self.counters.get(rakip.alias, [])

    def rol_sampiyonlari(self, rol: str) -> list:
        return [s for s in self.sampiyonlar.values() if rol in s.roller]


def rol_coz(metin: str):
    if not metin:
        return None
    return ROL_TAKMA.get(norm(metin))
