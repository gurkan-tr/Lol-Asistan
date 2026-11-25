"""Çalıştır: python -m unittest discover tests"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lolasistan.analiz import profil_cikar, rolleri_tahmin_et
from lolasistan.build import build_olustur
from lolasistan.champs import SampiyonDB
from lolasistan.lcu import item_set_aktar, secim_oku
from lolasistan.oneri import sampiyon_oner
from lolasistan.veri import EsyaDB


class SahteDD:
    """Data Dragon taklidi: Luden's Companion ve Opportunity bu yamada YOK."""
    dil = "tr_TR"

    def esyalar(self, dil):
        isimler = ["Luden's Echo", "Shadowflame", "Rabadon's Deathcap", "Void Staff",
                   "Zhonya's Hourglass", "Sorcerer's Shoes", "Mercury's Treads", "Plated Steelcaps",
                   "Doran's Ring", "Health Potion", "Morellonomicon", "Oblivion Orb", "Banshee's Veil"]
        data = {str(1000 + i): {"name": ("TR-" if dil == "tr_TR" else "") + n,
                                "maps": {"11": True}, "gold": {"purchasable": True}}
                for i, n in enumerate(isimler)}
        # Arena kopyası: harita 11'de değil, seçilmemeli
        data["223100"] = {"name": "Void Staff", "maps": {"30": True}, "gold": {"purchasable": True}}
        if dil == "tr_TR":
            for v in data.values():
                v["name"] = v["name"] if v["name"].startswith("TR-") else v["name"]
        return {"data": data}


class Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SampiyonDB()
        cls.db.id_esle([(238, "Zed", "Zed", [], False), (64, "LeeSin", "Lee Sin", [], False),
                        (122, "Darius", "Darius", [], False), (222, "Jinx", "Jinx", [], False),
                        (16, "Soraka", "Soraka", [], True), (127, "Lissandra", "Lissandra", [], True),
                        (86, "Garen", "Garen", [], False), (9999, "YeniSampiyon", "Yeni", ["Mage"], True)])

    def test_isim_cozme(self):
        self.assertEqual(self.db.bul("lee sin").alias, "LeeSin")
        self.assertEqual(self.db.bul("mf").alias, "MissFortune")
        self.assertEqual(self.db.bul("Wukong").alias, "MonkeyKing")
        self.assertEqual(self.db.bul("kha'zix").alias, "Khazix")

    def test_yeni_sampiyon_tahmini(self):
        s = self.db.id_ile(9999)
        self.assertTrue(s.tahmini)
        self.assertEqual((s.sinif, s.hasar), ("mage", "AP"))

    def test_counter_tablosu_gecerli(self):
        for anahtar, liste in self.db.counters.items():
            self.assertIn(anahtar, self.db.sampiyonlar, anahtar)
            for x in liste:
                self.assertIn(x, self.db.sampiyonlar, f"{anahtar} -> {x}")

    def test_rol_tahmini(self):
        rr = rolleri_tahmin_et([self.db.bul(x) for x in ["Jinx", "Zed", "Soraka", "LeeSin", "Darius"]])
        self.assertEqual({r: s.alias for r, s in rr.items()},
                         {"top": "Darius", "jungle": "LeeSin", "mid": "Zed", "adc": "Jinx", "support": "Soraka"})

    def test_oneri_counter(self):
        rak = [self.db.bul(x) for x in ["Zed", "Darius"]]
        o = sampiyon_oner(self.db, "mid", rolleri_tahmin_et(rak), [], rak)
        self.assertIn(o[0].sampiyon.alias, self.db.counters["Zed"])

    def test_sahiplik_filtresi(self):
        rak = [self.db.bul("Zed")]
        o = sampiyon_oner(self.db, "mid", rolleri_tahmin_et(rak), [], rak, sahip={"Ahri", "Lux"})
        self.assertEqual({x.sampiyon.alias for x in o}, {"Ahri", "Lux"})

    def test_build_eksik_esya_atlanir(self):
        esya = EsyaDB(SahteDD())
        rak = [self.db.bul(x) for x in ["Zed", "LeeSin", "Darius", "Jinx", "Soraka"]]
        b = build_olustur(self.db.bul("Lissandra"), "mid", profil_cikar(rak), self.db.bul("Zed"), esya)
        adlar = [a for _, a, _ in b.esyalar]
        self.assertIn("TR-Luden's Echo", adlar)           # Companion yok → Echo
        self.assertIn("TR-Morellonomicon", adlar)         # 3 iyileşen → anti-heal
        self.assertIn("TR-Zhonya's Hourglass", adlar)     # AD ağır
        self.assertTrue(all(i for i, _, _ in b.esyalar))  # hepsinin id'si var
        self.assertNotIn("223100", [i for i, _, _ in b.esyalar])

    def test_lcu_oturum(self):
        oturum = {
            "localPlayerCellId": 2,
            "myTeam": [{"cellId": 0, "championId": 86, "assignedPosition": "top"},
                       {"cellId": 2, "championId": 0, "championPickIntent": 127, "assignedPosition": "middle"}],
            "theirTeam": [{"cellId": 5, "championId": 238}, {"cellId": 6, "championId": 0}],
            "bans": {"myTeamBans": [64], "theirTeamBans": [0]},
            "actions": [[{"type": "pick", "actorCellId": 2, "completed": False, "championId": 127}]],
        }
        d = secim_oku(oturum)
        self.assertEqual((d.rol, d.benim_id, d.kilitli), ("mid", 127, False))
        self.assertEqual(d.rakip_ids, [238])
        self.assertEqual(d.yasak_ids, {64})

    def test_item_set_eski_setleri_korur(self):
        esya = EsyaDB(SahteDD())
        b = build_olustur(self.db.bul("Lissandra"), "mid", profil_cikar([]), None, esya)

        class SahteLCU:
            yazilan = None

            def get(self, yol):
                if "current-summoner" in yol:
                    return {"summonerId": 1, "accountId": 2}
                return {"accountId": 2, "itemSets": [{"title": "Benim setim"},
                                                     {"title": "LoL Asistan - Eski"}]}

            def put(self, yol, govde):
                SahteLCU.yazilan = (yol, govde)

        item_set_aktar(SahteLCU(), self.db.bul("Lissandra"), b)
        yol, govde = SahteLCU.yazilan
        basliklar = [s["title"] for s in govde["itemSets"]]
        self.assertEqual(basliklar, ["Benim setim", "LoL Asistan - Lissandra"])
        self.assertEqual(govde["itemSets"][1]["associatedChampions"], [127])


if __name__ == "__main__":
    unittest.main()


class SahteDD2:
    """Zırh/büyü direnci bilgisi olan eşyalar."""
    dil = "en_US"
    ESYA = {  # id: (ad, zırh, mr)
        "3157": ("Zhonya's Hourglass", 1, 0), "3135": ("Void Staff", 0, 0), "3089": ("Rabadon's Deathcap", 0, 0),
        "6655": ("Luden's Echo", 0, 0), "4645": ("Shadowflame", 0, 0), "3165": ("Morellonomicon", 0, 0),
        "3075": ("Thornmail", 1, 0), "3143": ("Randuin's Omen", 1, 0), "3110": ("Frozen Heart", 1, 0),
        "4401": ("Force of Nature", 0, 1), "3065": ("Spirit Visage", 0, 1), "3020": ("Sorcerer's Shoes", 0, 0),
        "3047": ("Plated Steelcaps", 1, 0), "3111": ("Mercury's Treads", 0, 1), "3102": ("Banshee's Veil", 0, 1),
        "3031": ("Infinity Edge", 0, 0), "3036": ("Lord Dominik's Regards", 0, 0), "6672": ("Kraken Slayer", 0, 0),
        "1056": ("Doran's Ring", 0, 0), "2003": ("Health Potion", 0, 0),
    }

    def esyalar(self, dil):
        return {"data": {i: {"name": n, "maps": {"11": True}, "gold": {"purchasable": True, "total": 3000},
                             "stats": {"FlatArmorMod": 40 * z, "FlatSpellBlockMod": 40 * m}}
                         for i, (n, z, m) in self.ESYA.items()}}


class MacSonuTest(unittest.TestCase):
    def test_kasilan_rakip_ve_direnc(self):
        from lolasistan.mac_sonu import analiz_et, eog_coz
        db = SampiyonDB()
        db.id_esle([(127, "Lissandra", "Lissandra", [], True), (238, "Zed", "Zed", [], False),
                    (122, "Darius", "Darius", [], False), (64, "LeeSin", "Lee Sin", [], False),
                    (222, "Jinx", "Jinx", [], False), (16, "Soraka", "Soraka", [], True)])
        esya = EsyaDB(SahteDD2())

        def oyuncu(cid, takim, esyalar, k, d, a, fz, by):
            return {"championId": cid, "teamId": takim, "items": esyalar,
                    "stats": {"CHAMPIONS_KILLED": k, "NUM_DEATHS": d, "ASSISTS": a,
                              "PHYSICAL_DAMAGE_DEALT_TO_CHAMPIONS": fz, "MAGIC_DAMAGE_DEALT_TO_CHAMPIONS": by}}
        veri = {"gameId": 42, "localPlayer": {"championId": 127, "teamId": 100},
                "teams": [
                    {"teamId": 100, "isWinningTeam": False, "players": [
                        oyuncu(127, 100, [6655, 4645, 3089, 3020], 3, 9, 4, 0, 15000)]},
                    {"teamId": 200, "isWinningTeam": True, "players": [
                        oyuncu(238, 200, [6672, 3031], 14, 2, 3, 30000, 0),
                        oyuncu(122, 200, [3075, 3143, 3047], 4, 4, 5, 15000, 0),
                        oyuncu(64, 200, [4401, 3065, 3111], 3, 5, 9, 9000, 0),
                        oyuncu(222, 200, [3031, 3102], 5, 3, 4, 20000, 0),
                        oyuncu(16, 200, [4401, 3102], 0, 3, 12, 0, 6000)]}]}
        mac = analiz_et(eog_coz(veri), db, esya, "mid")
        metin = " ".join(m for _, m in mac.analiz)
        self.assertIn("Zed kasıldı", metin)
        self.assertIn("Zhonya", metin)           # AD'ye karşı savunma önerisi
        self.assertIn("Void Staff", metin)       # rakipler 6 MR eşyası aldı, delme yok
        self.assertIn("anti-heal almadın", metin)
        self.assertTrue(any(t == "uyari" for t, _ in mac.analiz))


class RunTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from lolasistan.runler import RunDB
        cls.db = SampiyonDB()
        cls.runler = RunDB(None)   # çevrimdışı yedek yapı

    def sayfa(self, ben, rol, rakipler, rakip):
        from lolasistan.build import arketip_bul
        from lolasistan.runler import run_olustur
        rak = [self.db.bul(x) for x in rakipler]
        return run_olustur(self.db.bul(ben), arketip_bul(self.db.bul(ben), rol), rol,
                           profil_cikar(rak), self.db.bul(rakip) if rakip else None, self.runler)

    def adlar(self, s):
        return [s.kilit["ad"]] + [r["ad"] for r in s.ana_runler + s.yan_runler]

    def test_dokuz_rün_ve_farkli_satirlar(self):
        s = self.sayfa("Darius", "top", ["Garen"], "Garen")
        self.assertEqual(len(s.perk_ids()), 9)
        self.assertNotEqual(s.ana["id"], s.yan["id"])

    def test_patlama_rakibine_kemik_kaplama(self):
        s = self.sayfa("Lux", "mid", ["Zed"], "Zed")
        self.assertEqual(s.yan["ad"], "Azim")
        self.assertIn("Bone Plating", self.adlar(s))

    def test_tanklara_kesici(self):
        s = self.sayfa("Jinx", "adc", ["Ornn", "Sion", "Leona"], "Sion")
        self.assertIn("Cut Down", self.adlar(s))

    def test_cok_cc_inat(self):
        s = self.sayfa("Jinx", "adc", ["Leona", "Ashe", "Lissandra", "Amumu"], "Ashe")
        self.assertIn(5013, [p["id"] for p in s.parcalar])

    def test_dürtme_ikinci_ruzgar(self):
        s = self.sayfa("Darius", "top", ["Teemo"], "Teemo")
        self.assertIn("Second Wind", self.adlar(s))

    def test_orman_tank_aftershock(self):
        s = self.sayfa("Sejuani", "jungle", ["Zed"], None)
        self.assertEqual(s.kilit["ad"], "Veteran Aftershock")

    def test_istemciye_yazma(self):
        from lolasistan.lcu import run_sayfasi_yaz
        from lolasistan.runler import RunSayfasi
        cagri = []

        class F:
            def get(self, y):
                return [{"id": 1, "name": "Benim sayfam"}, {"id": 2, "name": "LoL Asistan: Eski", "isDeletable": True}]

            def delete(self, y):
                cagri.append(("del", y))

            def post(self, y, g):
                cagri.append(("post", g))
                return {"id": 9}

            def put(self, y, g):
                cagri.append(("put", y, g))
        s = RunSayfasi(ana={"id": 8000}, yan={"id": 8400}, kilit={"id": 8010},
                       ana_runler=[{"id": 9111}, {"id": 9105}, {"id": 8299}],
                       yan_runler=[{"id": 8444}, {"id": 8451}],
                       parcalar=[{"id": 5008}, {"id": 5008}, {"id": 5011}])
        run_sayfasi_yaz(F(), self.db.bul("Darius"), s)
        self.assertEqual(cagri[0], ("del", "/lol-perks/v1/pages/2"))   # sadece kendi sayfamız
        self.assertEqual(cagri[1][1]["selectedPerkIds"], [8010, 9111, 9105, 8299, 8444, 8451, 5008, 5008, 5011])
        self.assertEqual(cagri[2], ("put", "/lol-perks/v1/currentpage", 9))


class YeniOzellikTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SampiyonDB()

    def b(self, ben, rol, rakipler, rakip, sicra_d=False):
        from lolasistan.build import arketip_bul
        from lolasistan.buyuler import buyu_oner
        rak = [self.db.bul(x) for x in rakipler]
        return buyu_oner(self.db.bul(ben), arketip_bul(self.db.bul(ben), rol), rol, profil_cikar(rak),
                         self.db.bul(rakip) if rakip else None, sicra_d)

    def test_buyuler(self):
        self.assertEqual(self.b("LeeSin", "jungle", [], None).ikinci, 11)                 # Çarp
        self.assertEqual(self.b("Lux", "mid", ["Zed"], "Zed").ikinci, 21)                 # Bariyer
        self.assertEqual(self.b("Darius", "top", ["Aatrox"], "Aatrox").ikinci, 14)        # Tutuştur
        self.assertEqual(self.b("Jinx", "adc", ["Leona", "Ashe", "Lissandra", "Amumu"], "Ashe").ikinci, 1)
        self.assertEqual(self.b("Ornn", "top", ["Gnar"], "Gnar").ikinci, 12)              # Işınlan

    def test_sicra_tusu_korunur(self):
        self.assertEqual(self.b("Jinx", "adc", [], None, sicra_d=True).idler(), (4, 7))
        self.assertEqual(self.b("Jinx", "adc", [], None, sicra_d=False).idler(), (7, 4))

    def test_ban_onerisi(self):
        from lolasistan.gecmis import Sayac
        from lolasistan.plan import ban_oner
        kotu = Sayac(mac=5, galibiyet=1)
        b = ban_oner(self.db, "mid", self.db.bul("Ahri"), [self.db.bul("Fizz")], set(), {"Talon": kotu})
        adlar = [x.sampiyon.alias for x in b]
        self.assertEqual(adlar[0], "Talon")                 # geçmişte %20 → ilk sıra
        self.assertNotIn("Fizz", adlar)                     # takım arkadaşının seçeceğini banlama
        self.assertIn("Kassadin", adlar)                    # Ahri'yi counterlıyor

    def test_mac_plani(self):
        from lolasistan.plan import mac_plani
        biz = [self.db.bul(x) for x in ["Kayle", "Kassadin", "Jinx"]]
        onlar = [self.db.bul(x) for x in ["Renekton", "LeeSin", "Draven", "Leona", "Zed"]]
        p = mac_plani("mid", biz[1], biz[::2], onlar, self.db.bul("Zed"))
        turler = [t for t, _ in p]
        self.assertIn("zaman", turler)
        self.assertTrue(any("6. seviye" in m for _, m in p))

    def test_mac_gecmisi_cozme(self):
        from lolasistan.gecmis import Gecmis, mac_coz
        oyun = {"gameId": 1, "mapId": 11, "gameCreation": 5, "queueId": 420,
                "participantIdentities": [{"participantId": 1, "player": {"puuid": "ben"}},
                                          {"participantId": 6, "player": {"puuid": "o"}}],
                "participants": [
                    {"participantId": 1, "championId": 103, "teamId": 100, "timeline": {"lane": "MIDDLE", "role": "SOLO"},
                     "stats": {"win": True, "kills": 5, "deaths": 1, "assists": 3}},
                    {"participantId": 6, "championId": 238, "teamId": 200, "timeline": {"lane": "MIDDLE", "role": "SOLO"},
                     "stats": {"win": False}}]}
        r = mac_coz(oyun, "ben")
        self.assertEqual((r["rol"], r["kazandi"], r["koridor_rakibi"]), ("mid", True, 238))
        self.assertIsNone(mac_coz(dict(oyun, mapId=12), "ben"))   # ARAM sayılmaz
        g = Gecmis(maclar={1: r, 2: dict(r, id=2, kazandi=False, zaman=4)})
        self.assertEqual(g.sampiyon_istatistik()[103].mac, 2)
        self.assertEqual(g.koridor_rakibi_istatistik()[238].oran, 0.5)

    def test_kisisel_puan_oneriyi_etkiler(self):
        from lolasistan.gecmis import Sayac
        rak = [self.db.bul("Garen")]
        rr = rolleri_tahmin_et(rak)
        normal = sampiyon_oner(self.db, "mid", rr, [], rak, adet=200)
        iyi = sampiyon_oner(self.db, "mid", rr, [], rak, adet=200, kisisel={"Annie": Sayac(mac=20, galibiyet=15)})
        sira = lambda l: [o.sampiyon.alias for o in l].index("Annie")
        self.assertLess(sira(iyi), sira(normal))
