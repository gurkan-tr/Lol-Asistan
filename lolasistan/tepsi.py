"""Sistem tepsisi (saat yanındaki simge), bildirimler, Windows ile başlatma ve tek kopya kontrolü."""
import os
import socket
import sys
import threading

from .champs import KOK, PAKET

RUN_ANAHTARI = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_AD = "LoLAsistan"
TEK_KOPYA_PORT = 47913


# ---------------- Windows ile başlat ----------------
def _pythonw():
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        aday = exe[:-len("python.exe")] + "pythonw.exe"
        if os.path.exists(aday):
            return aday
    return exe


def oto_baslat_komutu():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --gizli'
    return f'"{_pythonw()}" "{os.path.join(KOK, "LoLAsistan.pyw")}" --gizli'


def oto_baslat_durumu():
    if sys.platform != "win32":
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_ANAHTARI) as k:
            winreg.QueryValueEx(k, RUN_AD)
            return True
    except OSError:
        return False


def oto_baslat_ayarla(acik):
    if sys.platform != "win32":
        return False
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_ANAHTARI, 0, winreg.KEY_SET_VALUE) as k:
        if acik:
            winreg.SetValueEx(k, RUN_AD, 0, winreg.REG_SZ, oto_baslat_komutu())
        else:
            try:
                winreg.DeleteValue(k, RUN_AD)
            except OSError:
                pass
    return oto_baslat_durumu()


# ---------------- tek kopya ----------------
def tek_kopya(goster, bekle=False):
    """İlk kopyaysa dinleyici başlatır ve True döner. Uygulama zaten açıksa onun
    penceresini öne getirmesini ister ve False döner. bekle=True: güncelleme sonrası
    yeniden başlarken eski kopyanın kapanmasını bekler."""
    import time
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for deneme in range(30 if bekle else 1):
        try:
            s.bind(("127.0.0.1", TEK_KOPYA_PORT))
            break
        except OSError:
            if deneme < (29 if bekle else 0):
                time.sleep(0.5)
    else:
        try:
            with socket.create_connection(("127.0.0.1", TEK_KOPYA_PORT), timeout=2) as c:
                c.sendall(b"goster")
        except OSError:
            pass
        return False
    s.listen(2)

    def dinle():
        while True:
            try:
                c, _ = s.accept()
                with c:
                    if c.recv(16) == b"goster":
                        goster()
            except OSError:
                return
    threading.Thread(target=dinle, daemon=True).start()
    return True


# ---------------- tepsi simgesi ----------------
class Tepsi:
    def __init__(self, goster, cikis):
        self._goster, self._cikis = goster, cikis
        self.simge = None

    def baslat(self):
        try:
            import pystray
            from PIL import Image
        except ImportError:
            return False
        try:
            resim = Image.open(os.path.join(PAKET, "ikon.ico"))
        except Exception:
            resim = Image.new("RGBA", (64, 64), (127, 214, 194, 255))
        menu = pystray.Menu(
            pystray.MenuItem("LoL Asistan'ı aç", lambda *_: self._goster(), default=True),
            pystray.MenuItem("Windows açılınca başlat", lambda *_: oto_baslat_ayarla(not oto_baslat_durumu()),
                             checked=lambda _: oto_baslat_durumu()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Çıkış", lambda *_: self._cikis()),
        )
        self.simge = pystray.Icon("LoLAsistan", resim, "LoL Asistan", menu)
        if hasattr(self.simge, "run_detached"):
            self.simge.run_detached()
        else:
            threading.Thread(target=self.simge.run, daemon=True).start()
        return True

    def bildir(self, baslik, mesaj):
        if self.simge:
            try:
                self.simge.notify(mesaj, baslik)
            except Exception:
                pass

    def durdur(self):
        if self.simge:
            try:
                self.simge.stop()
            except Exception:
                pass
