"""Rakip takıma göre rün sayfası.

Rünler İngilizce 'key' adlarıyla seçilir ve çalışma anında güncel yamanın rün listesinden
(Data Dragon runesReforged.json) aranır. Bir rün oyundan kalkmışsa aynı satırdaki başka
bir rüne düşülür; böylece yeni yamalarda bozulmaz."""
import re
from dataclasses import dataclass, field

DD_IMG = "https://ddragon.leagueoflegends.com/cdn/img/"

# İnternet yokken kullanılan yedek yapı (sadece görüntü için; istemciye uygulanmaz)
YEDEK_AGAC = {
    "Precision": (8000, [["PressTheAttack", "LethalTempo", "FleetFootwork", "Conqueror"],
                         ["AbsorbLife", "Triumph", "PresenceOfMind"],
                         ["LegendAlacrity", "LegendHaste", "LegendBloodline"],
                         ["CoupDeGrace", "CutDown", "LastStand"]]),
    "Domination": (8100, [["Electrocute", "DarkHarvest", "HailOfBlades"],
                          ["CheapShot", "TasteOfBlood", "SuddenImpact"],
                          ["SixthSense", "GrislyMementos", "DeepWard"],
                          ["TreasureHunter", "RelentlessHunter", "UltimateHunter"]]),
    "Sorcery": (8200, [["SummonAery", "ArcaneComet", "PhaseRush"],
                       ["NullifyingOrb", "ManaflowBand", "NimbusCloak"],
                       ["Transcendence", "Celerity", "AbsoluteFocus"],
                       ["Scorch", "Waterwalking", "GatheringStorm"]]),
    "Resolve": (8400, [["GraspOfTheUndying", "VeteranAftershock", "Guardian"],
                       ["Demolish", "FontOfLife", "ShieldBash"],
                       ["Conditioning", "SecondWind", "BonePlating"],
                       ["Overgrowth", "Revitalize", "Unflinching"]]),
    "Inspiration": (8300, [["GlacialAugment", "UnsealedSpellbook", "FirstStrike"],
                           ["MagicalFootwear", "CashBack", "PerfectTiming"],
                           ["TripleTonic", "TimeWarpTonic", "BiscuitDelivery"],
                           ["CosmicInsight", "ApproachVelocity", "JackOfAllTrades"]]),
}
AGAC_TR = {"Precision": "Kesinlik", "Domination": "Hükmetme", "Sorcery": "Büyücülük",
           "Resolve": "Azim", "Inspiration": "İlham"}

# İstatistik parçaları (2024'ten beri bu set)
PARCA = {5008: "Uyarlanabilir Güç", 5005: "Saldırı Hızı", 5007: "Yetenek Hızı",
         5010: "Hareket Hızı", 5001: "Ölçeklenen Can", 5011: "Can (+65)",
         5013: "İnat ve Yavaşlatma Direnci"}

# arketip -> (ana ağaç, kilit taşı tercihleri, 3 satır tercihleri, yan ağaç, yan tercihler, parçalar)
SABLON = {
    "adc_crit": ("Precision", ["LethalTempo", "PressTheAttack"],
                 [["AbsorbLife", "PresenceOfMind"], ["LegendAlacrity", "LegendBloodline"], ["CoupDeGrace", "CutDown"]],
                 "Inspiration", ["MagicalFootwear", "CosmicInsight", "BiscuitDelivery"], [5005, 5008, 5011]),
    "adc_onhit": ("Precision", ["LethalTempo", "PressTheAttack"],
                  [["PresenceOfMind", "AbsorbLife"], ["LegendAlacrity"], ["CutDown", "CoupDeGrace"]],
                  "Resolve", ["BonePlating", "Overgrowth", "SecondWind"], [5005, 5008, 5011]),
    "adc_spell": ("Inspiration", ["FirstStrike"],
                  [["MagicalFootwear"], ["BiscuitDelivery", "TripleTonic"], ["CosmicInsight"]],
                  "Precision", ["PresenceOfMind", "LegendHaste", "CoupDeGrace"], [5007, 5008, 5011]),
    "ad_bruiser": ("Precision", ["Conqueror"],
                   [["Triumph"], ["LegendHaste", "LegendAlacrity"], ["LastStand"]],
                   "Resolve", ["SecondWind", "Overgrowth", "BonePlating"], [5008, 5008, 5011]),
    "ad_crit_melee": ("Precision", ["LethalTempo", "Conqueror"],
                      [["Triumph"], ["LegendAlacrity"], ["LastStand", "CoupDeGrace"]],
                      "Resolve", ["SecondWind", "Overgrowth", "BonePlating"], [5005, 5008, 5011]),
    "ad_onhit_melee": ("Precision", ["LethalTempo", "Conqueror"],
                       [["Triumph"], ["LegendAlacrity"], ["CoupDeGrace", "CutDown"]],
                       "Domination", ["SuddenImpact", "TreasureHunter", "TasteOfBlood"], [5005, 5008, 5011]),
    "ad_lethality": ("Domination", ["Electrocute", "DarkHarvest"],
                     [["SuddenImpact", "TasteOfBlood"], ["GrislyMementos", "SixthSense"], ["UltimateHunter", "TreasureHunter"]],
                     "Precision", ["Triumph", "CoupDeGrace", "LegendHaste"], [5008, 5008, 5011]),
    "ap_mage": ("Sorcery", ["ArcaneComet", "SummonAery"],
                [["ManaflowBand"], ["Transcendence"], ["Scorch", "GatheringStorm"]],
                "Inspiration", ["BiscuitDelivery", "CosmicInsight", "MagicalFootwear"], [5008, 5008, 5011]),
    "ap_mage_burst": ("Domination", ["Electrocute"],
                      [["TasteOfBlood", "CheapShot"], ["GrislyMementos", "SixthSense"], ["UltimateHunter", "TreasureHunter"]],
                      "Sorcery", ["ManaflowBand", "Transcendence", "GatheringStorm"], [5008, 5008, 5011]),
    "ap_burst": ("Domination", ["Electrocute", "DarkHarvest"],
                 [["CheapShot", "TasteOfBlood"], ["GrislyMementos", "SixthSense"], ["UltimateHunter", "TreasureHunter"]],
                 "Sorcery", ["Transcendence", "GatheringStorm", "ManaflowBand"], [5008, 5008, 5011]),
    "ap_bruiser": ("Precision", ["Conqueror"],
                   [["Triumph"], ["LegendHaste", "LegendAlacrity"], ["LastStand"]],
                   "Resolve", ["SecondWind", "Overgrowth", "BonePlating"], [5008, 5008, 5011]),
    "ap_onhit": ("Precision", ["LethalTempo", "PressTheAttack"],
                 [["PresenceOfMind", "Triumph"], ["LegendAlacrity"], ["LastStand", "CoupDeGrace"]],
                 "Sorcery", ["Transcendence", "GatheringStorm"], [5005, 5008, 5011]),
    "tank": ("Resolve", ["GraspOfTheUndying", "VeteranAftershock"],
             [["Demolish", "FontOfLife"], ["SecondWind", "BonePlating", "Conditioning"], ["Overgrowth", "Revitalize"]],
             "Inspiration", ["MagicalFootwear", "CosmicInsight", "BiscuitDelivery"], [5007, 5001, 5011]),
    "support_tank": ("Resolve", ["VeteranAftershock", "Guardian"],
                     [["FontOfLife", "ShieldBash"], ["BonePlating", "Conditioning"], ["Unflinching", "Revitalize"]],
                     "Inspiration", ["BiscuitDelivery", "CosmicInsight", "MagicalFootwear"], [5007, 5001, 5011]),
    "enchanter": ("Sorcery", ["SummonAery"],
                  [["ManaflowBand"], ["Transcendence"], ["Scorch"]],
                  "Resolve", ["FontOfLife", "Revitalize", "BonePlating"], [5007, 5008, 5011]),
    "support_mage": ("Sorcery", ["ArcaneComet"],
                     [["ManaflowBand"], ["Transcendence"], ["Scorch"]],
                     "Inspiration", ["BiscuitDelivery", "CosmicInsight", "MagicalFootwear"], [5007, 5008, 5011]),
}
SAKAT = {"adc_crit", "adc_onhit", "adc_spell", "ap_mage", "ap_mage_burst", "support_mage", "enchanter", "ap_onhit"}


def _okunur(key):
    return re.sub(r"(?<!^)(?=[A-Z])", " ", key)


class RunDB:
    def __init__(self, dd=None):
        self.cevrimdisi = True
        self.agac = {}   # key -> {"id","ad","ikon","satirlar":[[rune_key,...] x4]}
        self.run = {}    # key -> {"id","ad","ikon"}
        en = dd._veri("runesReforged", "en_US") if dd else None
        yerel = dd._veri("runesReforged", dd.dil) if dd and dd.dil != "en_US" else en
        if en:
            self.cevrimdisi = False
            yerel_ad, yerel_agac = {}, {}
            for st in (yerel or []):
                yerel_agac[st["id"]] = st["name"]
                for sl in st["slots"]:
                    for r in sl["runes"]:
                        yerel_ad[r["id"]] = r["name"]
            for st in en:
                self.agac[st["key"]] = {"id": st["id"], "ad": yerel_agac.get(st["id"], st["name"]),
                                        "ikon": DD_IMG + st["icon"],
                                        "satirlar": [[r["key"] for r in sl["runes"]] for sl in st["slots"]]}
                for sl in st["slots"]:
                    for r in sl["runes"]:
                        self.run[r["key"]] = {"id": r["id"], "ad": yerel_ad.get(r["id"], r["name"]),
                                              "ikon": DD_IMG + r["icon"]}
        else:
            for k, (sid, satirlar) in YEDEK_AGAC.items():
                self.agac[k] = {"id": sid, "ad": AGAC_TR[k], "ikon": None, "satirlar": satirlar}
                for sat in satirlar:
                    for r in sat:
                        self.run[r] = {"id": None, "ad": _okunur(r), "ikon": None}

    def satir_bul(self, agac, key):
        for i, sat in enumerate(self.agac[agac]["satirlar"]):
            if key in sat:
                return i
        return None


@dataclass
class RunSayfasi:
    ana: dict
    yan: dict
    kilit: dict
    ana_runler: list
    yan_runler: list
    parcalar: list
    nedenler: list = field(default_factory=list)
    uygulanabilir: bool = True

    def perk_ids(self):
        return ([self.kilit["id"]] + [r["id"] for r in self.ana_runler] +
                [r["id"] for r in self.yan_runler] + [p["id"] for p in self.parcalar])


def run_olustur(sampiyon, arketip, rol, profil, rakip, db: RunDB) -> RunSayfasi:
    a = arketip
    if a == "ap_mage" and sampiyon.var("burst") and not sampiyon.var("poke"):
        a = "ap_mage_burst"
    if a not in SABLON:
        a = "ad_bruiser"
    ana, kilitler, satirlar, yan, yan_tercih, parca = SABLON[a]
    satirlar = [list(s) for s in satirlar]
    yan_tercih = list(yan_tercih)
    parca = list(parca)
    neden = []
    rakip_patlama = rakip is not None and (rakip.sinif == "assassin" or (rakip.var("burst") and rakip.var("dive")))
    rakip_durtme = rakip is not None and rakip.menzilli and (rakip.var("poke") or rakip.sinif in ("mage", "marksman"))

    # Orman / destek tankları: Grasp yerine Aftershock
    if a == "tank" and rol in ("jungle", "support"):
        kilitler = ["VeteranAftershock", "GraspOfTheUndying"]
    # Ormancılar: yan ağaçta Hükmetme (av ve erken hasar)
    if rol == "jungle" and ana not in ("Domination", "Resolve") and a not in ("tank",):
        yan, yan_tercih = "Domination", ["SuddenImpact", "TreasureHunter", "TasteOfBlood"]

    # Kalın ön cephe → Kesici
    if ana == "Precision" and (profil.tank >= 2 or (rakip is not None and rakip.tanky)):
        satirlar[2] = ["CutDown"] + [x for x in satirlar[2] if x != "CutDown"]
        neden.append("Karşıda tanklar var → Kesici (Cut Down)")

    # Patlama hasarlı koridor rakibi + kırılgan sen → Azim yan ağaç, Kemik Kaplama
    if rakip_patlama and a in SAKAT and ana != "Resolve":
        yan = "Resolve"
        yan_tercih = ["BonePlating", "Revitalize" if a in ("enchanter",) else "Overgrowth", "SecondWind"]
        neden.append(f"{rakip.ad} patlama hasarı yapıyor → Kemik Kaplama")
    # Uzaktan dürten rakip + yakın dövüşçü sen → İkinci Rüzgar
    elif rakip_durtme and not sampiyon.menzilli and rol in ("top", "mid"):
        if ana == "Resolve":
            satirlar[1] = ["SecondWind"] + [x for x in satirlar[1] if x != "SecondWind"]
        else:
            yan, yan_tercih = "Resolve", ["SecondWind", "Overgrowth", "BonePlating"]
        neden.append(f"{rakip.ad} uzaktan dürtecek → İkinci Rüzgar (Second Wind)")

    # Bol CC → İnat parçası (+ Azim'de Yılmazlık)
    if profil.cc >= 3:
        parca[2] = 5013
        if "Resolve" in (ana, yan):
            if ana == "Resolve":
                satirlar[2] = ["Unflinching"] + [x for x in satirlar[2] if x != "Unflinching"]
            else:
                yan_tercih = ["Unflinching"] + [x for x in yan_tercih if x != "Unflinching"]
        neden.append(f"Rakipte {profil.cc} CC'li şampiyon → İnat parçası")
    if yan == ana:  # güvenlik
        yan = "Inspiration" if ana != "Inspiration" else "Resolve"
        yan_tercih = ["CosmicInsight", "BiscuitDelivery", "MagicalFootwear", "BonePlating", "SecondWind"]

    # ---- veritabanına göre çöz ----
    A = db.agac[ana]
    kilit_key = next((k for k in kilitler if k in A["satirlar"][0]), A["satirlar"][0][0])
    ana_run = []
    for i, tercih in enumerate(satirlar, start=1):
        mevcut = A["satirlar"][i] if i < len(A["satirlar"]) else []
        k = next((t for t in tercih if t in mevcut), mevcut[0] if mevcut else None)
        if k:
            ana_run.append(db.run[k])
    Y = db.agac[yan]
    yan_run, kullanilan_satir = [], set()
    adaylar = yan_tercih + [k for sat in Y["satirlar"][1:] for k in sat]
    for k in adaylar:
        s = db.satir_bul(yan, k)
        if s and s >= 1 and s not in kullanilan_satir and k in db.run:
            yan_run.append(db.run[k])
            kullanilan_satir.add(s)
        if len(yan_run) == 2:
            break
    return RunSayfasi(
        ana={"id": A["id"], "ad": A["ad"], "ikon": A["ikon"]},
        yan={"id": Y["id"], "ad": Y["ad"], "ikon": Y["ikon"]},
        kilit=db.run[kilit_key], ana_runler=ana_run, yan_runler=yan_run,
        parcalar=[{"id": p, "ad": PARCA[p]} for p in parca], nedenler=neden,
        uygulanabilir=not db.cevrimdisi,
    )
