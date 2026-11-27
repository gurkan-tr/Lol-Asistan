"""U.GG istatistikleri. Veri etiketsiz dizilerle gelir; her alan biçim kontrolünden geçer,
beklenmeyen bir şey gelirse o alan atlanır (program diğer kaynaklarla devam eder)."""
import json
import os
import time

from .champs import KOK

API = "https://stats2.u.gg/lol/1.5/overview/{yama}/ranked_solo_5x5/{cid}/1.5.0.json"
ROL = {"jungle": "1", "support": "2", "adc": "3", "top": "4", "mid": "5"}
BOLGELER = ["12", "1"]                  # 12: dünya geneli
LIGLER = ["17", "10", "11", "8"]        # zümrüt+, platin+, elmas+, genel
ONBELLEK = os.path.join(KOK, "cache", "ugg")
SURE = 6 * 3600
BASLIK = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LoLAsistan"}


def _yamalar(surum):
    """'16.23.1' -> ['16_23', '16_22']"""
    try:
        a, b = (int(x) for x in str(surum).split(".")[:2])
    except Exception:
        return []
    return [f"{a}_{b}"] + ([f"{a}_{b - 1}"] if b > 1 else [])


def ham_getir(sampiyon_id, surum):
    if not sampiyon_id:
        return None
    for yama in _yamalar(surum):
        yol = os.path.join(ONBELLEK, f"{sampiyon_id}_{yama}.json")
        try:
            if os.path.exists(yol) and time.time() - os.path.getmtime(yol) < SURE:
                with open(yol, encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        try:
            import requests
            r = requests.get(API.format(yama=yama, cid=sampiyon_id), headers=BASLIK, timeout=8)
            if r.status_code == 200:
                ham = r.json()
                os.makedirs(ONBELLEK, exist_ok=True)
                with open(yol, "w", encoding="utf-8") as f:
                    json.dump(ham, f)
                return ham
        except Exception:
            continue
    return None


def _mw(a, b):
    """(maç, galibiyet) — galibiyet maçtan büyük olamaz."""
    a, b = int(a or 0), int(b or 0)
    return (a, b) if b <= a else (b, a)


def _int_liste(x):
    return isinstance(x, list) and all(isinstance(i, (int, str)) and str(i).isdigit() for i in x)


def adaylar(ham, rol):
    if not isinstance(ham, dict) or rol not in ROL:
        return None
    veri = None
    for bolge in BOLGELER:
        for lig in LIGLER:
            try:
                yaprak = ham[bolge][lig][ROL[rol]]
                d = yaprak[0] if isinstance(yaprak, list) and isinstance(yaprak[0], list) else None
                if d and len(d) >= 5:
                    veri = d
                    break
            except (KeyError, IndexError, TypeError):
                continue
        if veri:
            break
    if not veri:
        return None
    out = {"kaynak": "U.GG", "cekirdek": [], "bot": [], "baslangic": [], "son": [], "run": [],
           "buyu": [], "yetenek": [], "parca": None}
    try:
        r = veri[0]
        if len(r) >= 5 and _int_liste(r[4]) and len(r[4]) == 6:
            mac, kaz = _mw(r[0], r[1])
            out["run"].append({"ana": int(r[2]), "yan": int(r[3]), "karisik_ids": [int(i) for i in r[4]],
                               "mac": mac, "kazanma": kaz})
    except Exception:
        pass
    try:
        b = veri[1]
        if _int_liste(b[2]) and len(b[2]) == 2:
            mac, kaz = _mw(b[0], b[1])
            out["buyu"].append({"ids": [int(i) for i in b[2]], "mac": mac, "kazanma": kaz})
    except Exception:
        pass
    try:
        s = veri[2]
        if _int_liste(s[2]) and s[2]:
            mac, kaz = _mw(s[0], s[1])
            out["baslangic"].append({"ids": [int(i) for i in s[2]], "mac": mac, "kazanma": kaz})
    except Exception:
        pass
    try:
        c = veri[3]
        if _int_liste(c[2]) and len(c[2]) >= 2:
            mac, kaz = _mw(c[0], c[1])
            out["cekirdek"].append({"ids": [int(i) for i in c[2]], "mac": mac, "kazanma": kaz})
    except Exception:
        pass
    try:
        y = veri[4]
        if isinstance(y[2], list) and all(t in ("Q", "W", "E", "R") for t in y[2]) and len(y[2]) >= 9:
            mac, kaz = _mw(y[0], y[1])
            out["yetenek"].append({"sira": list(y[2]), "mac": mac, "kazanma": kaz})
    except Exception:
        pass
    try:
        for yuva in veri[5]:
            for e in yuva:
                if isinstance(e, list) and len(e) >= 3 and str(e[0]).isdigit():
                    mac, kaz = _mw(e[2], e[1])       # [id, galibiyet, maç]
                    out["son"].append({"ids": [int(e[0])], "mac": mac, "kazanma": kaz})
    except Exception:
        pass
    try:
        p = veri[8]
        if _int_liste(p[2]) and len(p[2]) == 3:
            out["parca"] = [int(i) for i in p[2]]
    except Exception:
        pass
    return out if (out["cekirdek"] or out["run"]) else None
