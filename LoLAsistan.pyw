"""LoL Asistan — pencereli uygulama. Çift tıklayınca komut ekranı açılmadan çalışır."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import webview  # noqa: E402

from lolasistan.champs import PAKET  # noqa: E402
from lolasistan.motor import Motor, ayar_yaz  # noqa: E402


class Api:
    """Arayüzdeki JavaScript'in çağırabildiği fonksiyonlar."""

    def __init__(self, motor):
        self._m = motor
        self._tepsi = None
        self._cikis = lambda: [w.destroy() for w in list(webview.windows)]

    def durum(self):
        return self._m.durum()

    def demo(self):
        return self._m.demo()

    def manuel(self, rol, rakip, takim, sampiyon):
        return self._m.manuel(rol, rakip, takim, sampiyon)

    def canliya_don(self):
        self._m.canliya_don()

    def build_icin(self, alias):
        return self._m.build_icin(alias)

    def runleri_uygula(self, alias):
        return self._m.runleri_uygula(alias)

    def uygula(self, alias):
        return self._m.uygula(alias)

    def ses(self):
        return self._m.ses()

    def performans(self):
        return self._m.performans()

    def gecmisi_yenile(self):
        return self._m.gecmisi_yenile()

    def guncelleme_kontrol(self):
        return self._m.guncelleme_kontrol()

    def guncelle_kur(self):
        return self._m.guncelle_kur()

    def yeniden_baslat(self):
        """Güncellemeden sonra: yeni kopyayı başlat, bu kopyayı tamamen kapat
        (tepsi simgesi dahil; yoksa eski kopya arka planda canlı kalıyor)."""
        import threading
        from lolasistan.guncelle import yeniden_baslat
        yeniden_baslat()
        if self._tepsi:
            self._tepsi.durdur()
        self._cikis()
        threading.Timer(1.5, lambda: os._exit(0)).start()

    def sampiyon_adlari(self):
        return self._m.sampiyon_adlari()

    def ayarlar(self):
        return self._m.ayar

    def ayar_kaydet(self, yeni):
        self._m.ayar.update(yeni)
        ayar_yaz(self._m.ayar)
        return True

    def gecmis_ac(self):
        return self._m.gecmis_ac()

    def oto_baslat_durumu(self):
        from lolasistan.tepsi import oto_baslat_durumu
        return oto_baslat_durumu()

    def oto_baslat(self, acik):
        from lolasistan.tepsi import oto_baslat_ayarla
        return oto_baslat_ayarla(bool(acik))


def main():
    from lolasistan.tepsi import Tepsi, tek_kopya
    gizli = "--gizli" in sys.argv            # Windows açılışında simge durumunda başla
    durum = {"pencere": None, "cikis": False, "uyarildi": False}

    def goster():
        w = durum["pencere"]
        if w:
            w.show()
            w.restore()

    if not tek_kopya(goster, bekle="--bekle" in sys.argv):
        return  # zaten açık: onun penceresi öne getirildi

    motor = Motor()

    def cikis():
        durum["cikis"] = True
        tepsi.durdur()
        if durum["pencere"]:
            durum["pencere"].destroy()
        # Tepsi iş parçacığı süreci açık tutmasın: kısa süre sonra tamamen kapan
        import threading
        threading.Timer(2.0, lambda: os._exit(0)).start()

    tepsi = Tepsi(goster, cikis)
    tepsi_var = tepsi.baslat()

    def olay(tur, baslik, mesaj):
        """Motorun bildirimleri: yeni seçim ekranı vb."""
        tepsi.bildir(baslik, mesaj)
        # Maç bulunduğunda pencereyi öne getirme: LoL'deki "Kabul et" düğmesini kapatabilir.
        if tur == "secim" and motor.ayar.get("secimde_one_getir", True):
            goster()

    motor.olay = olay

    def kapaniyor():
        # Kapat düğmesi: simge durumuna küçül (Çıkış tepsi menüsünden)
        if tepsi_var and not durum["cikis"] and motor.ayar.get("kapatinca_simgeye", True):
            durum["pencere"].hide()
            if not durum["uyarildi"]:
                tepsi.bildir("LoL Asistan arka planda çalışıyor",
                             "Maç bulununca haber vereceğim. Tamamen kapatmak için simgeye sağ tıkla → Çıkış.")
                durum["uyarildi"] = True
            return False
        tepsi.durdur()
        return True

    api = Api(motor)
    api._tepsi = tepsi
    api._cikis = cikis
    w = webview.create_window(
        "LoL Asistan", os.path.join(PAKET, "ui", "index.html"), js_api=api,
        width=1260, height=880, min_size=(1000, 680), background_color="#171B27", hidden=gizli,
    )
    w.events.closing += kapaniyor
    durum["pencere"] = w
    webview.start(motor.baslat)


if __name__ == "__main__":
    main()
