"""Otomatik güncelleme: GitHub'daki depoda daha yeni bir sürüm varsa indirip kurar.

Depo herkese açıksa (public) anahtar gerekmez. Gizliyse okuma yetkili bir GitHub
anahtarı (token) gerekir; anahtar sadece bu bilgisayardaki config.json'da durur.
Kişisel dosyalar (ayarlar, maç geçmişi, önbellek) güncellemede asla silinmez."""
import io
import os
import shutil
import subprocess
import sys
import zipfile

from .champs import KOK, PAKET

API = "https://api.github.com"
KORUNAN = {"config.json", "kisisel", "cache", "mac_gecmisi", ".git", "__pycache__"}


def yerel_surum():
    try:
        with open(os.path.join(PAKET, "surum.txt"), encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "0.0.0"


def _sayi(v):
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except ValueError:
        return (0,)


def _istek(yol, anahtar, ham=False, zaman=15):
    import requests
    h = {"X-GitHub-Api-Version": "2022-11-28",
         "Accept": "application/vnd.github.raw" if ham else "application/vnd.github+json"}
    if anahtar:
        h["Authorization"] = f"Bearer {anahtar}"
    r = requests.get(API + yol, headers=h, timeout=zaman)
    if r.status_code == 401:
        raise RuntimeError("GitHub anahtarı geçersiz ya da süresi dolmuş. Ayarlardan yeni anahtar gir "
                           "ya da depo herkese açıksa anahtar kutusunu boş bırak.")
    if r.status_code == 404:
        raise RuntimeError("Depo bulunamadı. Depo gizliyse Ayarlar'a okuma yetkili bir anahtar girmen gerekir.")
    if r.status_code == 403 and r.headers.get("X-RateLimit-Remaining") == "0":
        raise RuntimeError("GitHub kısa süreliğine sınır koydu; bir saat sonra tekrar dene.")
    r.raise_for_status()
    return r


def kontrol(depo, anahtar):
    """{'var': bool, 'yerel': '1.3.0', 'uzak': '1.4.0'} döner."""
    if getattr(sys, "frozen", False):
        return {"var": False, "yerel": yerel_surum(), "uzak": None,
                "mesaj": ".exe sürümü kendini güncelleyemez; yeni .exe'yi EXE_YAP.bat ile üret."}
    uzak = _istek(f"/repos/{depo}/contents/surum.txt", anahtar, ham=True).text.strip()
    yerel = yerel_surum()
    return {"var": _sayi(uzak) > _sayi(yerel), "yerel": yerel, "uzak": uzak}


def indir_ve_kur(depo, anahtar):
    """Depodaki son hali indirir, kişisel dosyalara dokunmadan üstüne yazar."""
    r = _istek(f"/repos/{depo}/zipball", anahtar, zaman=60)
    hedef = os.path.realpath(KOK)
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for uye in z.infolist():
            parca = uye.filename.split("/", 1)       # ilk klasör: kullanici-depo-sha/
            if len(parca) < 2 or not parca[1]:
                continue
            goreli = parca[1]
            if goreli.split("/")[0] in KORUNAN:
                continue
            yol = os.path.realpath(os.path.join(hedef, goreli))
            if not yol.startswith(hedef + os.sep):    # zip dışına yazmayı engelle
                continue
            if uye.is_dir():
                os.makedirs(yol, exist_ok=True)
                continue
            os.makedirs(os.path.dirname(yol), exist_ok=True)
            with z.open(uye) as kaynak, open(yol, "wb") as cikti:
                shutil.copyfileobj(kaynak, cikti)
    # Yeni paket gerektiyse sessizce kur
    gizli = 0x08000000 if sys.platform == "win32" else 0   # CREATE_NO_WINDOW
    try:
        subprocess.run([_python(), "-m", "pip", "install", "-q", "-r", os.path.join(hedef, "requirements.txt")],
                       creationflags=gizli, timeout=300, check=False)
    except Exception:
        pass
    return yerel_surum()


def _python():
    """pythonw.exe ile çalışıyorsak pip için python.exe'yi kullan."""
    exe = sys.executable
    if exe.lower().endswith("pythonw.exe"):
        aday = exe[:-len("pythonw.exe")] + "python.exe"
        if os.path.exists(aday):
            return aday
    return exe


def yeniden_baslat():
    gizli = 0x08000000 if sys.platform == "win32" else 0
    subprocess.Popen([sys.executable, os.path.join(KOK, "LoLAsistan.pyw"), "--bekle"], cwd=KOK, creationflags=gizli)
