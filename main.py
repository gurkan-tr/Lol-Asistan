"""LoL Asistan — şampiyon seçiminde karşı takımı analiz edip şampiyon ve build önerir.

Kullanım:
  python main.py                      # canlı mod: LoL istemcisini dinler
  python main.py --demo               # istemci olmadan örnek maç
  python main.py --rol mid --rakip "Zed,LeeSin,Darius,Jinx,Thresh" [--takim "..."] [--sampiyon Ahri]
"""
import argparse
import json
import os
import sys
import time

from lolasistan.analiz import profil_cikar, rolleri_tahmin_et
from lolasistan.build import build_olustur
from lolasistan.champs import KOK, ROL_AD, SampiyonDB, rol_coz
from lolasistan.oneri import sampiyon_oner
from lolasistan.veri import DataDragon, EsyaDB

AYAR_YOLU = os.path.join(KOK, "config.json")


def ayar_yukle():
    try:
        with open(AYAR_YOLU, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def hesapla(db, esya, ayar, rol, takim, rakipler, yasakli=(), benim=None,
            sahip=None, ustalik=None, kilitli=False):
    rakip_roller = rolleri_tahmin_et(rakipler)
    profil = profil_cikar(rakipler)
    havuz_ham = (ayar.get("havuz") or {}).get(rol, [])
    havuz = [s.alias for s in (db.bul(x) for x in havuz_ham) if s]
    oneriler = []
    if not kilitli and (not benim or ayar.get("secince_de_oner", True)):
        oneriler = sampiyon_oner(db, rol, rakip_roller, takim, rakipler, set(yasakli),
                                 sahip, ustalik, havuz, ayar.get("sadece_havuz", False),
                                 ayar.get("oneri_sayisi", 5))
    hedef = benim or (oneriler[0].sampiyon if oneriler else None)
    build = build_olustur(hedef, rol, profil, rakip_roller.get(rol), esya, rakipler) if hedef else None
    return rakip_roller, profil, oneriler, build


def isimleri_coz(db, metin):
    sonuc = []
    for parca in (metin or "").split(","):
        parca = parca.strip()
        if not parca:
            continue
        s = db.bul(parca)
        if s is None:
            print(f"! '{parca}' şampiyonu tanınmadı, atlanıyor.")
        else:
            sonuc.append(s)
    return sonuc


def veri_hazirla(ayar):
    db = SampiyonDB()
    dd = DataDragon(ayar.get("dil", "tr_TR"))
    db.id_esle(dd.sampiyon_kayitlari())
    esya = EsyaDB(dd)
    return db, dd, esya


def manuel(args, ayar):
    from lolasistan import ekran
    db, dd, esya = veri_hazirla(ayar)
    if args.demo:
        rol = "mid"
        rakipler = isimleri_coz(db, "Zed,LeeSin,Darius,Jinx,Soraka")
        takim = isimleri_coz(db, "Garen,Graves,Caitlyn")
        benim = db.bul(args.sampiyon) if args.sampiyon else None
    else:
        rol = rol_coz(args.rol) or rol_coz(ayar.get("varsayilan_rol")) or "mid"
        rakipler = isimleri_coz(db, args.rakip)
        takim = isimleri_coz(db, args.takim)
        benim = db.bul(args.sampiyon) if args.sampiyon else None
    yasak = {s.alias for s in isimleri_coz(db, args.yasak)}
    rr, profil, oneriler, build = hesapla(db, esya, ayar, rol, takim, rakipler, yasak, benim)
    durum = f"yama {dd.surum}" if dd.surum else "çevrimdışı (eşya adları İngilizce)"
    ekran.goster(rol, benim, rr, profil, oneriler, build, durum)


def canli(args, ayar):
    import requests
    from lolasistan import ekran
    from lolasistan.lcu import LCU, item_set_aktar, secim_oku
    from lolasistan.mac_sonu import analiz_et, eog_coz, kaydet

    ekran.bekle("Veriler hazırlanıyor (güncel yama indiriliyor)...")
    db, dd, esya = veri_hazirla(ayar)
    yama = f"yama {dd.surum}" if dd.surum else "çevrimdışı"
    lcu, son, aktarilan = None, None, set()
    sahip, ustalik = None, {}
    ekran_durum, analiz_edilen = None, None
    son_build, son_rol = None, None

    while True:
        try:
            if lcu is None:
                lcu = LCU.bul(ayar.get("lol_klasoru", ""))
                if lcu is None:
                    ekran.bekle("LoL istemcisi bulunamadı.\nOyunu aç, bu pencere otomatik bağlanacak.\n\n"
                                "[dim](Çıkmak için Ctrl+C)[/]")
                    time.sleep(3)
                    continue
                db.id_esle(lcu.sampiyon_kayitlari())

            faz = lcu.faz()
            # --- MAÇ SIRASINDA: hiçbir oyun verisi okunmaz, hiçbir analiz yapılmaz ---
            if faz in ("GameStart", "InProgress", "Reconnect"):
                if ekran_durum != "oyun":
                    ekran.mac_icinde()
                    ekran_durum = "oyun"
                son = None
                if args.tek:
                    return
                time.sleep(5)
                continue
            # --- MAÇ BİTTİ: maç sonu ekranı verisiyle analiz ---
            if faz in ("WaitingForStats", "PreEndOfGame", "EndOfGame"):
                mac = eog_coz(lcu.mac_sonu_verisi())
                if mac and mac.oyun_id != analiz_edilen:
                    analiz_et(mac, db, esya, son_rol or rol_coz(ayar.get("varsayilan_rol")) or "mid", son_build)
                    try:
                        dosya = kaydet(mac)
                    except Exception:
                        dosya = None
                    ekran.mac_sonu_goster(mac, dosya)
                    analiz_edilen, ekran_durum = mac.oyun_id, "macsonu"
                if args.tek:
                    return
                time.sleep(3)
                continue

            oturum = lcu.secim_ekrani()
            if not oturum:
                if ekran_durum not in ("bekle", "macsonu"):
                    ekran.bekle(f"İstemciye bağlandı ✓  ({yama})\n\nŞampiyon seçimi bekleniyor...\n"
                                "Maç bulunduğunda analiz otomatik başlayacak.")
                    ekran_durum = "bekle"
                son = None
                if args.tek:
                    return
                time.sleep(2)
                continue

            if son is None:  # yeni seçim ekranı: sahiplik + ustalık bilgisini tazele
                ids = lcu.sahip_olunanlar()
                sahip = {db.id_ile(i).alias for i in ids if db.id_ile(i)} if ids else None
                ustalik = {db.id_ile(i).alias: p for i, p in lcu.ustaliklar().items() if db.id_ile(i)}
                aktarilan = set()

            d = secim_oku(oturum)
            rol = d.rol or rol_coz(args.rol) or rol_coz(ayar.get("varsayilan_rol")) or "mid"
            if d.anahtar() + (rol,) != son:
                son = d.anahtar() + (rol,)
                takim = [db.id_ile(i) for i in d.takim_ids if db.id_ile(i)]
                rakipler = [db.id_ile(i) for i in d.rakip_ids if db.id_ile(i)]
                yasak = {db.id_ile(i).alias for i in d.yasak_ids if db.id_ile(i)}
                benim = db.id_ile(d.benim_id)
                rr, profil, oneriler, build = hesapla(db, esya, ayar, rol, takim, rakipler,
                                                      yasak, benim, sahip, ustalik, d.kilitli)
                durum = yama + ("" if d.rol else "  ·  rol atanmadı, varsayılan kullanılıyor")
                ekran.goster(rol, benim, rr, profil, oneriler, build, durum, d.kilitli)
                ekran_durum = "secim"
                if benim:
                    son_build, son_rol = build, rol

                if (benim and d.kilitli and build and ayar.get("item_set_aktar", True)
                        and not esya.cevrimdisi and (benim.alias, len(rakipler)) not in aktarilan):
                    try:
                        item_set_aktar(lcu, benim, build)
                        aktarilan.add((benim.alias, len(rakipler)))
                        ekran.konsol.print("[green]✓ Build, oyun içi mağazaya eşya seti olarak eklendi.[/]")
                    except Exception as e:
                        ekran.konsol.print(f"[red]Eşya seti aktarılamadı: {e}[/]")
            if args.tek:
                return
            time.sleep(1.5)
        except requests.exceptions.ConnectionError:
            lcu, son = None, None
            time.sleep(2)
        except KeyboardInterrupt:
            print("\nGörüşürüz, iyi oyunlar!")
            return


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    p = argparse.ArgumentParser(description="LoL şampiyon seçimi asistanı")
    p.add_argument("--demo", action="store_true", help="istemci olmadan örnek bir maç göster")
    p.add_argument("--rol", help="koridorun: top / jungle / mid / adc / support")
    p.add_argument("--rakip", help="rakip şampiyonlar, virgülle: \"Zed,LeeSin,Darius\"")
    p.add_argument("--takim", help="takım arkadaşlarının şampiyonları, virgülle")
    p.add_argument("--yasak", help="yasaklanan şampiyonlar, virgülle")
    p.add_argument("--sampiyon", help="oynayacağın şampiyon (build için)")
    p.add_argument("--tek", action="store_true", help="canlı modda bir kez analiz edip çık")
    args = p.parse_args()
    ayar = ayar_yukle()
    try:
        if args.demo or args.rakip or args.sampiyon:
            manuel(args, ayar)
        else:
            canli(args, ayar)
    except KeyboardInterrupt:
        print("\nGörüşürüz, iyi oyunlar!")


if __name__ == "__main__":
    main()
