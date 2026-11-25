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

    def performans(self):
        return self._m.performans()

    def gecmisi_yenile(self):
        return self._m.gecmisi_yenile()

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


def main():
    motor = Motor()
    webview.create_window(
        "LoL Asistan", os.path.join(PAKET, "ui", "index.html"), js_api=Api(motor),
        width=1240, height=860, min_size=(1000, 680), background_color="#0E1820",
    )
    webview.start(motor.baslat)


if __name__ == "__main__":
    main()
