"""Çalıştır: python -m unittest discover tests"""
import os
import sys
import unittest
import unittest.mock

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


class GuncellemeTest(unittest.TestCase):
    def test_kurulum_kisisel_dosyalara_dokunmaz(self):
        import io, tempfile, zipfile
        from unittest import mock
        from lolasistan import guncelle
        with tempfile.TemporaryDirectory() as kok:
            for yol, icerik in {"config.json": "BENIM AYARIM", "kisisel/gecmis_x.json": "{}",
                                "surum.txt": "1.4.0", "main.py": "eski"}.items():
                os.makedirs(os.path.dirname(os.path.join(kok, yol)) or kok, exist_ok=True)
                open(os.path.join(kok, yol), "w").write(icerik)
            tampon = io.BytesIO()
            with zipfile.ZipFile(tampon, "w") as z:
                z.writestr("gurkan-tr-Lol-Asistan-abc123/surum.txt", "1.5.0")
                z.writestr("gurkan-tr-Lol-Asistan-abc123/main.py", "yeni")
                z.writestr("gurkan-tr-Lol-Asistan-abc123/config.json", "EZME")
                z.writestr("gurkan-tr-Lol-Asistan-abc123/ui/yeni.html", "<p>")
                z.writestr("gurkan-tr-Lol-Asistan-abc123/../../kotu.txt", "x")
            cevap = mock.Mock(status_code=200, content=tampon.getvalue(), text="1.5.0")
            with mock.patch.object(guncelle, "KOK", kok), mock.patch.object(guncelle, "PAKET", kok), \
                    mock.patch("requests.get", return_value=cevap), mock.patch("subprocess.run"):
                self.assertTrue(guncelle.kontrol("u/d", "t")["var"])
                self.assertEqual(guncelle.indir_ve_kur("u/d", "t"), "1.5.0")
            oku = lambda y: open(os.path.join(kok, y)).read()
            self.assertEqual(oku("main.py"), "yeni")
            self.assertEqual(oku("config.json"), "BENIM AYARIM")
            self.assertTrue(os.path.exists(os.path.join(kok, "kisisel/gecmis_x.json")))
            self.assertTrue(os.path.exists(os.path.join(kok, "ui/yeni.html")))
            self.assertFalse(os.path.exists(os.path.join(os.path.dirname(kok), "kotu.txt")))

    def test_surum_karsilastirma(self):
        from lolasistan.guncelle import _sayi
        self.assertGreater(_sayi("1.10.0"), _sayi("1.9.3"))
        self.assertGreater(_sayi("v2.0"), _sayi("1.99.99"))


class SurumBesTest(unittest.TestCase):
    def test_bolgeler(self):
        from lolasistan.olum import bolge
        self.assertEqual(bolge(1000, 1000, 100), "kendi_us")
        self.assertEqual(bolge(13800, 13800, 100), "rakip_us")
        self.assertEqual(bolge(1200, 9000, 100), "ust_koridor")
        self.assertEqual(bolge(9000, 1000, 100), "alt_koridor")
        self.assertEqual(bolge(7400, 7400, 100), "orta_koridor")
        self.assertEqual(bolge(4600, 10200, 100), "nehir")
        self.assertEqual(bolge(9500, 11500, 100), "rakip_orman")
        self.assertEqual(bolge(9500, 11500, 200), "kendi_orman")

    def test_olum_cikar_ve_yorum(self):
        from lolasistan.olum import olumleri_cikar, yorumla
        oyun = {"participantIdentities": [{"participantId": 3, "player": {"puuid": "ben"}}],
                "participants": [{"participantId": 3, "teamId": 100, "championId": 103},
                                 {"participantId": 7, "teamId": 200, "championId": 238}]}
        olay = lambda dk, x, y, yardim=(): {"type": "CHAMPION_KILL", "victimId": 3, "killerId": 7,
                                             "timestamp": dk * 60000, "position": {"x": x, "y": y},
                                             "assistingParticipantIds": list(yardim)}
        zc = {"frames": [{"events": [olay(4, 4600, 10200), olay(9, 9500, 11500), olay(12, 7400, 7400),
                                     {"type": "CHAMPION_KILL", "victimId": 7, "killerId": 3, "timestamp": 1}]}]}
        s = olumleri_cikar(oyun, zc, "ben")
        self.assertEqual([o["dk"] for o in s["olumler"]], [4, 9, 12])
        metin = " ".join(m for _, m in yorumla(s, lambda c: {238: "Zed"}[c]))
        self.assertIn("İlk 14 dakikada 3 kez", metin)
        self.assertIn("nehirde ya da rakip ormanında", metin)
        self.assertIn("Zed seni 3 kez", metin)

    def test_takim_mesaji(self):
        from lolasistan.plan import takim_mesaji
        m = takim_mesaji([("zaman", "Rakip erken oyunda daha güçlü. ..."), ("koridor", "Zed ..."),
                          ("savas", "Fiora yan koridorda bölünmüş itiş (split push) yapabilir; ...")])
        self.assertTrue(m.startswith("Rakip erken güçlü"))
        self.assertIn("Fiora split itsin", m)
        self.assertNotIn("Zed", m)

    def test_tek_kopya(self):
        from lolasistan import tepsi
        cagri = []
        import socket
        with socket.socket() as bos:
            bos.bind(("127.0.0.1", 0))
            port = bos.getsockname()[1]
        with unittest.mock.patch.object(tepsi, "TEK_KOPYA_PORT", port):
            self.assertTrue(tepsi.tek_kopya(lambda: cagri.append(1)))
            self.assertFalse(tepsi.tek_kopya(lambda: None))   # ikinci kopya açılmaz
            import time
            time.sleep(0.3)
        self.assertEqual(cagri, [1])                           # ilk kopyaya "öne gel" gitti


class AnahtarsizGuncellemeTest(unittest.TestCase):
    def test_public_depo_anahtarsiz(self):
        from lolasistan import guncelle
        cevap = unittest.mock.Mock(status_code=200, text="9.9.9", headers={})
        with unittest.mock.patch("requests.get", return_value=cevap) as get:
            self.assertTrue(guncelle.kontrol("gurkan-tr/Lol-Asistan", "")["var"])
            self.assertNotIn("Authorization", get.call_args.kwargs["headers"])


OPGG_ORNEK = {"meta": {"version": "16.23"}, "data": {
    "core_items": [{"ids": [3153, 6672, 6333], "play": 557, "win": 319, "pick_rate": 0.2}],
    "boots": [{"ids": [3047], "play": 2309, "win": 1137}],
    "starter_items": [{"ids": [1055, 2003], "play": 3214, "win": 1590}],
    "last_items": [{"ids": [3053], "play": 400, "win": 220}, {"ids": [6333], "play": 300, "win": 150},
                   {"ids": [3036], "play": 200, "win": 110}],
    "runes": [{"id": 8010, "primary_page_id": 8000, "primary_rune_ids": [8010, 9111, 9104, 8299],
               "secondary_page_id": 8400, "secondary_rune_ids": [8242, 8473], "stat_mod_ids": [5005, 5008, 5001],
               "play": 1442, "win": 712}],
    "summoner_spells": [{"ids": [4, 14], "win": 1651, "play": 3261}],
    "skills": [{"order": ["Q", "E", "W", "Q", "Q", "R", "Q", "W", "Q", "W", "R", "W", "W", "E", "E"], "play": 1172, "win": 596}]}}


class OpggDD:
    dil = "en_US"
    ESYA = {"3153": "Blade of The Ruined King", "6672": "Kraken Slayer", "6333": "Death's Dance",
            "3047": "Plated Steelcaps", "1055": "Doran's Blade", "2003": "Health Potion", "3053": "Sterak's Gage",
            "3036": "Lord Dominik's Regards", "6609": "Chempunk Chainsword", "3033": "Mortal Reminder",
            "3111": "Mercury's Treads", "3075": "Thornmail"}

    def esyalar(self, dil):
        return {"data": {i: {"name": n, "maps": {"11": True}, "gold": {"purchasable": True, "total": 3000},
                             "stats": {}} for i, n in self.ESYA.items()}}


UGG_ORNEK = {"12": {"17": {"4": [[
    [900, 470, 8000, 8400, [8473, 9111, 8010, 8242, 9104, 8299]],     # rünler (karışık sırada)
    [3000, 1500, [4, 12]],                                           # büyüler
    [2800, 1400, [1055, 2003]],                                      # başlangıç
    [700, 400, [3153, 6672, 6333]],                                  # çekirdek (OP.GG ile aynı → toplanır)
    [600, 320, ["Q", "E", "W", "Q", "Q", "R", "Q", "W", "Q", "W", "R", "W", "W", "E", "E"], "QWE"],
    [[[3053, 300, 520], [3036, 60, 100]], [[3075, 40, 70]], []],     # 4/5/6. eşya seçenekleri [id, galibiyet, maç]
    [1500, 3000], 0, [3000, 1500, ["5005", "5008", "5001"]]], "2026-11-26T22:56:19Z"]}}}


class CokluKaynakTest(unittest.TestCase):
    def test_opgg_adaylar_ve_maks(self):
        from lolasistan.opgg import adaylar, maks_sirasi
        v = adaylar(OPGG_ORNEK)
        self.assertEqual(v["cekirdek"][0]["ids"], [3153, 6672, 6333])
        self.assertEqual(maks_sirasi(v["yetenek"][0]["sira"]), "Q > W > E")
        # alanlar data.summary altında gelirse de okunur
        self.assertTrue(adaylar({"data": {"summary": OPGG_ORNEK["data"]}})["cekirdek"])

    def test_ugg_cozme(self):
        from lolasistan.ugg import adaylar
        u = adaylar(UGG_ORNEK, "top")
        self.assertEqual(u["cekirdek"][0], {"ids": [3153, 6672, 6333], "mac": 700, "kazanma": 400})
        self.assertEqual(u["buyu"][0]["ids"], [4, 12])
        self.assertEqual(u["parca"], [5005, 5008, 5001])
        self.assertIn({"ids": [3053], "mac": 520, "kazanma": 300}, u["son"])
        self.assertIsNone(adaylar(UGG_ORNEK, "mid"))           # o rolde veri yok
        self.assertIsNone(adaylar({"bozuk": 1}, "top"))

    def test_iki_sitede_ayni_build_toplanir(self):
        from lolasistan import kaynaklar, opgg, ugg
        v = kaynaklar.birlestir(opgg.adaylar(OPGG_ORNEK), None, ugg.adaylar(UGG_ORNEK, "top"))
        self.assertEqual(v["cekirdek"]["mac"], 557 + 700)
        self.assertEqual(sorted(v["cekirdek"]["kaynaklar"]), ["OP.GG", "U.GG"])
        self.assertIn("OP.GG + U.GG", v["cekirdek"]["etiket"])

    def test_az_macli_yuzde_yuz_one_gecemez(self):
        from lolasistan.kaynaklar import sec
        s = sec([("OP.GG", False, [{"ids": [1, 2, 3], "mac": 1000, "kazanma": 560},
                                   {"ids": [4, 5, 6], "mac": 6, "kazanma": 6}])])
        self.assertEqual(s["ids"], [1, 2, 3])

    def test_rakibe_karsi_iyi_olan_one_gecer(self):
        from lolasistan.kaynaklar import sec
        genel = [{"ids": [1, 2, 3], "mac": 1000, "kazanma": 520}, {"ids": [1, 2, 9], "mac": 800, "kazanma": 410}]
        esl = [{"ids": [1, 2, 9], "mac": 60, "kazanma": 42}, {"ids": [1, 2, 3], "mac": 50, "kazanma": 22}]
        s = sec([("OP.GG", False, genel), ("Darius karşısında", True, esl)])
        self.assertEqual(s["ids"], [1, 2, 9])
        self.assertEqual(s["eslesme"], {"mac": 60, "oran": 70})

    def test_build_veriyle_ve_rakibe_ozel_esya_veride_olandan(self):
        from lolasistan import kaynaklar, opgg
        from lolasistan.build import build_opgg
        db = SampiyonDB()
        esya = EsyaDB(OpggDD())
        rak = [db.bul(x) for x in ["Darius", "Soraka", "Aatrox", "Jinx", "Zed"]]
        genel = opgg.adaylar(OPGG_ORNEK)
        genel["son"].append({"ids": [3033], "mac": 150, "kazanma": 80})   # bu şampiyon Mortal Reminder da alıyor
        v = kaynaklar.birlestir(genel, None, None, "Darius")
        b = build_opgg(db.bul("Irelia"), "top", profil_cikar(rak), db.bul("Darius"), esya, rak, v)
        adlar = [a for _, a, _ in b.esyalar]
        self.assertEqual(adlar[:3], ["Blade of The Ruined King", "Kraken Slayer", "Death's Dance"])
        self.assertIn("Mortal Reminder", adlar)     # anti-heal: şablondaki ilk seçenek değil, verideki
        self.assertNotIn("Chempunk Chainsword", adlar)
        self.assertEqual(b.kaynak, "opgg")

    def test_ugg_runleri_siraya_dizilir(self):
        from lolasistan.runler import RunDB, YEDEK_AGAC
        ID = {"Conqueror": 8010, "Triumph": 9111, "LegendAlacrity": 9104, "LastStand": 8299,
              "BonePlating": 8473, "Unflinching": 8242}

        class DD:
            dil = "en_US"

            def _veri(self, t, d):
                return [{"id": sid, "key": k, "name": k, "icon": "x", "slots": [
                    {"runes": [{"id": ID.get(r, sid * 10 + i * 3 + j), "key": r, "name": r, "icon": "y"}
                               for j, r in enumerate(sat)]} for i, sat in enumerate(satirlar)]}
                        for k, (sid, satirlar) in YEDEK_AGAC.items()]
        db = RunDB(DD())
        self.assertEqual(db.sirala(8000, 8400, [8473, 9111, 8010, 8242, 9104, 8299]),
                         ([8010, 9111, 9104, 8299], [8473, 8242]))

    def test_kaynak_yoksa_kendi_builde_duser(self):
        from lolasistan.build import build_opgg
        db = SampiyonDB()
        self.assertIsNone(build_opgg(db.bul("Irelia"), "top", profil_cikar([]), None, EsyaDB(None), [], None))


class SurumDokuzTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.db = SampiyonDB()
        cls.db.id_esle([(39, "Irelia", "Irelia", [], False), (122, "Darius", "Darius", [], False),
                        (24, "Jax", "Jax", [], False), (54, "Malphite", "Malphite", [], True),
                        (58, "Renekton", "Renekton", [], False), (114, "Fiora", "Fiora", [], False),
                        (86, "Garen", "Garen", [], False), (150, "Gnar", "Gnar", [], False)])

    def test_eslesmeler_cozme(self):
        from lolasistan.opgg import eslesmeler
        ham = {"data": {"summary": {"counters": [{"champion_id": 122, "play": 134, "win": 72}],
                                    "positions": [{"counters": [{"champion_id": 54, "play": 122, "win": 42}]}]}}}
        self.assertEqual(eslesmeler(ham), {122: (134, 72), 54: (122, 42)})

    def test_gercek_eslesme_oneriyi_belirler(self):
        rak = [self.db.bul("Darius")]
        rr = rolleri_tahmin_et(rak)
        # tabloya göre Malphite iyi olsa bile gerçek veri Garen'in çok daha iyi olduğunu söylüyor
        esl = {"Garen": (0.56, 900), "Malphite": (0.44, 800), "Irelia": (0.51, 1000)}
        o = sampiyon_oner(self.db, "top", rr, [], rak, sahip={"Garen", "Malphite", "Irelia"}, eslesme=esl)
        self.assertEqual([x.sampiyon.alias for x in o], ["Garen", "Irelia", "Malphite"])
        self.assertTrue(any("%56,0 kazanıyor (900 maç)" in m for _, m in o[0].nedenler))

    def test_havuz_onerisi(self):
        from lolasistan.gecmis import Sayac
        from lolasistan.havuz import havuz_oner
        kisisel = {"Irelia": Sayac(mac=20, galibiyet=12), "Jax": Sayac(mac=3, galibiyet=1)}
        veri = {
            39: {122: (500, 210), 54: (400, 170), 86: (300, 160)},       # Irelia: Darius ve Malphite zor
            122: {24: (400, 180), 114: (300, 170), 58: (200, 100)},      # Darius'a karşı Jax %55, Fiora %43
            54: {114: (300, 120), 24: (250, 140), 150: (200, 90)},       # Malphite'a karşı Fiora %60
        }
        h = havuz_oner(self.db, "top", kisisel, lambda c: veri.get(c.id))
        self.assertEqual(h["ana"]["alias"], "Irelia")
        self.assertEqual([z["alias"] for z in h["zor"]], ["Darius", "Malphite"])
        yedekler = [y["alias"] for y in h["yedekler"]]
        self.assertIn("Jax", yedekler)        # Darius'a karşı %55
        self.assertIn("Gnar", yedekler)       # Malphite'a karşı %55 ve Darius'a karşı nötr;
        self.assertNotIn("Fiora", yedekler)   # Fiora Malphite'a iyi ama Darius'a karşı %43 → dengesiz
        kapsanan = {k for y in h["yedekler"] for k in y["kapsadigi"]}
        self.assertEqual(kapsanan, {"Darius", "Malphite"})
        self.assertEqual(h["kaynak"], "OP.GG")

    def test_havuz_internetsiz_tabloya_duser(self):
        from lolasistan.gecmis import Sayac
        from lolasistan.havuz import havuz_oner
        h = havuz_oner(self.db, "top", {"Darius": Sayac(mac=10, galibiyet=6)}, lambda c: None)
        self.assertEqual(h["kaynak"], "tablo")
        self.assertTrue(h["yedekler"])

    def test_gelisim(self):
        from lolasistan.gecmis import Gecmis, mac_coz
        oyun = lambda gid, cs, gorus, kaz: {"gameId": gid, "mapId": 11, "gameCreation": gid, "gameDuration": 1800,
            "participantIdentities": [{"participantId": 1, "player": {"puuid": "ben"}}],
            "participants": [{"participantId": 1, "championId": 39, "teamId": 100, "timeline": {"lane": "TOP"},
                              "stats": {"win": kaz, "totalMinionsKilled": cs, "neutralMinionsKilled": 0, "visionScore": gorus}}]}
        g = Gecmis(maclar={i: mac_coz(oyun(i, 150 + i * 10, 15, i % 2 == 0), "ben") for i in range(1, 6)})
        gl = g.gelisim()
        self.assertEqual([x["cs_dk"] for x in gl], [5.33, 5.67, 6.0, 6.33, 6.67])
        self.assertEqual(gl[0]["gorus_dk"], 0.5)

    def test_sira_bende(self):
        oturum = {"localPlayerCellId": 1, "myTeam": [{"cellId": 1, "championId": 0}], "theirTeam": [],
                  "actions": [[{"type": "ban", "actorCellId": 1, "completed": False, "isInProgress": True}]]}
        self.assertEqual(secim_oku(oturum).sira_bende, "ban")
