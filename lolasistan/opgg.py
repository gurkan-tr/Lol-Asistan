"""OP.GG istatistikleri (genel ve koridor rakibine karşı). Ham cevap 6 saat önbellekte tutulur."""
import json
import os
import time

from .champs import KOK

API = "https://lol-api-champion.op.gg/api/{bolge}/champions/ranked/{cid}/{poz}"
POZ = {"top": "top", "jungle": "jungle", "mid": "mid", "adc": "adc", "support": "support"}
ONBELLEK = os.path.join(KOK, "cache", "opgg")
SURE = 6 * 3600
BASLIK = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) LoLAsistan", "Accept": "application/json"}


def _veri_kismi(ham):
    """Alanlar bazen data altında, bazen data.summary altında gelebiliyor."""
    d = (ham or {}).get("data") or {}
    if d.get("core_items"):
        return d
    return d.get("summary") or d


def ham_getir(sampiyon_id, rol, bolge="global", lig="emerald_plus", hedef=None):
    poz = POZ.get(rol)
    if not poz or not sampiyon_id:
        return None
    yol = os.path.join(ONBELLEK, f"{sampiyon_id}_{poz}_{hedef or 0}_{bolge}_{lig}.json")
    try:
        if os.path.exists(yol) and time.time() - os.path.getmtime(yol) < SURE:
            with open(yol, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    import requests
    for b in dict.fromkeys([bolge, "global", "TR"]):
        for parametre in ({"tier": lig}, {}):
            if hedef:
                parametre = dict(parametre, target_champion=hedef)
            try:
                r = requests.get(API.format(bolge=b, cid=sampiyon_id, poz=poz), params=parametre,
                                 headers=BASLIK, timeout=6)
                if r.status_code != 200:
                    continue
                ham = r.json()
                if _veri_kismi(ham).get("core_items"):
                    os.makedirs(ONBELLEK, exist_ok=True)
                    with open(yol, "w", encoding="utf-8") as f:
                        json.dump(ham, f)
                    return ham
            except Exception:
                continue
    try:
        with open(yol, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def adaylar(ham, kaynak="OP.GG"):
    """OP.GG cevabını ortak aday biçimine çevirir (kaynaklar.py birleştirir)."""
    d = _veri_kismi(ham)
    if not d.get("core_items"):
        return None
    m = lambda e: (e.get("play") or 0, e.get("win") or 0)
    out = {"kaynak": kaynak, "yama": ((ham or {}).get("meta") or {}).get("version"),
           "cekirdek": [], "bot": [], "baslangic": [], "son": [], "run": [], "buyu": [], "yetenek": []}
    for e in d.get("core_items") or []:
        if e.get("ids"):
            out["cekirdek"].append({"ids": list(e["ids"]), "mac": m(e)[0], "kazanma": m(e)[1]})
    for e in d.get("boots") or []:
        if e.get("ids"):
            out["bot"].append({"ids": [e["ids"][0]], "mac": m(e)[0], "kazanma": m(e)[1]})
    for e in d.get("starter_items") or []:
        if e.get("ids"):
            out["baslangic"].append({"ids": list(e["ids"]), "mac": m(e)[0], "kazanma": m(e)[1]})
    for e in d.get("last_items") or []:
        for i in e.get("ids") or []:
            out["son"].append({"ids": [i], "mac": m(e)[0], "kazanma": m(e)[1]})
    for e in d.get("runes") or []:
        if e.get("primary_rune_ids") and e.get("secondary_rune_ids") and e.get("stat_mod_ids"):
            out["run"].append({"ana": e.get("primary_page_id"), "yan": e.get("secondary_page_id"),
                               "ana_ids": list(e["primary_rune_ids"]), "yan_ids": list(e["secondary_rune_ids"]),
                               "parca_ids": list(e["stat_mod_ids"]), "mac": m(e)[0], "kazanma": m(e)[1]})
    for e in d.get("summoner_spells") or []:
        if len(e.get("ids") or []) == 2:
            out["buyu"].append({"ids": list(e["ids"]), "mac": m(e)[0], "kazanma": m(e)[1]})
    for e in d.get("skills") or []:
        if e.get("order"):
            out["yetenek"].append({"sira": list(e["order"]), "mac": m(e)[0], "kazanma": m(e)[1]})
    return out


def maks_sirasi(sira):
    """['Q','E','W','Q',...] -> 'Q > W > E' (önce hangisi maksa ulaşıyor)."""
    sayac, biten = {}, []
    for y in sira:
        if y == "R":
            continue
        sayac[y] = sayac.get(y, 0) + 1
        if sayac[y] == 5 and y not in biten:
            biten.append(y)
    for y in sorted(sayac, key=lambda y: -sayac[y]):
        if y not in biten:
            biten.append(y)
    return " > ".join(biten)


def eslesmeler(ham):
    """Bir şampiyonun sayfasındaki 'counters' listesi: {rakip_id: (maç, bu şampiyonun galibiyeti)}.
    Liste bazen data altında, bazen data.summary ya da pozisyonların altında gelir."""
    d = (ham or {}).get("data") or {}
    adaylar = [d.get("counters"), (d.get("summary") or {}).get("counters")]
    for p in (d.get("summary") or {}).get("positions") or d.get("positions") or []:
        if isinstance(p, dict):
            adaylar.append(p.get("counters"))
    out = {}
    for liste in adaylar:
        for e in liste or []:
            if isinstance(e, dict) and e.get("champion_id") and e.get("play"):
                cid = int(e["champion_id"])
                if cid not in out or e["play"] > out[cid][0]:
                    out[cid] = (int(e["play"]), int(e.get("win") or 0))
    return out
