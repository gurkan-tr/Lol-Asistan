"""Birden fazla kaynağı (OP.GG genel, OP.GG koridor rakibine karşı, U.GG) birleştirir.

Puanlama: her seçenek için 'güvenilir kazanma oranı' hesaplanır. Az maçlı seçenekler
ortalamaya doğru çekilir (Bayes düzeltmesi), böylece 5 maçta %100 kazanmış bir build
1000 maçta %55 kazanmış olanı geçemez. Üstüne oynanma sayısı için küçük bir pay ve
koridor rakibine karşı yeterli veri varsa eşleşme payı eklenir. Aynı seçenek birden
fazla kaynakta varsa maçları toplanır ve 'iki sitede de önde' payı alır."""
import math

ONCEL = 60          # Bayes ön bilgisi: 60 maçlık "ortalama" varsayımı
ESLESME_PAYI = 0.025
UYUM_PAYI = 0.01
EN_AZ_ESLESME = 12  # rakibe özel veri için en az maç


def guvenilir_oran(kazanma, mac, ortalama=0.5):
    return (kazanma + ONCEL * ortalama) / (mac + ONCEL)


def _anahtar(ids, sirali=True):
    return tuple(sorted(ids)) if sirali else tuple(ids)


def sec(listeler, sirali=True, ortalama=0.5):
    """listeler: [(kaynak_etiketi, eslesme_mi, [aday,...])]; aday: {'ids', 'mac', 'kazanma', ...}
    En iyi adayı ve kısa açıklamasını döner."""
    havuz = {}
    for etiket, eslesme, adaylar in listeler:
        for a in adaylar or []:
            ids = a.get("ids") or a.get("sira")
            if not ids or not a.get("mac"):
                continue
            k = _anahtar(ids, sirali)
            h = havuz.setdefault(k, {"aday": a, "mac": 0, "kazanma": 0, "kaynaklar": [], "eslesme": None})
            if eslesme:
                if a["mac"] >= EN_AZ_ESLESME:
                    h["eslesme"] = (a["mac"], a["kazanma"])
                if etiket not in h["kaynaklar"]:
                    h["kaynaklar"].append(etiket)
                continue  # eşleşme maçları genel maçların alt kümesi; tekrar sayma
            h["mac"] += a["mac"]
            h["kazanma"] += a["kazanma"]
            if etiket not in h["kaynaklar"]:
                h["kaynaklar"].append(etiket)
    if not havuz:
        return None
    toplam = sum(h["mac"] for h in havuz.values()) or 1
    en_iyi, en_puan = None, -1
    for h in havuz.values():
        if not h["mac"] and not h["eslesme"]:
            continue
        p = guvenilir_oran(h["kazanma"], h["mac"], ortalama)
        p += 0.02 * math.sqrt(h["mac"] / toplam)                 # popülerlik (çok oynanan = denenmiş)
        if h["eslesme"]:
            em, ek = h["eslesme"]
            p = 0.5 * p + 0.5 * guvenilir_oran(ek, em, ortalama) + ESLESME_PAYI
        if len([k for k in h["kaynaklar"] if "karşı" not in k]) >= 2:
            p += UYUM_PAYI
        h["puan"] = p
        if p > en_puan:
            en_iyi, en_puan = h, p
    if not en_iyi:
        return None
    mac, kaz = en_iyi["mac"], en_iyi["kazanma"]
    if en_iyi["eslesme"] and not mac:
        mac, kaz = en_iyi["eslesme"]
    sonuc = dict(en_iyi["aday"])
    sonuc.update({"mac": mac, "oran": round(kaz / mac * 100) if mac else None,
                  "kaynaklar": en_iyi["kaynaklar"],
                  "eslesme": ({"mac": en_iyi["eslesme"][0], "oran": round(en_iyi["eslesme"][1] / en_iyi["eslesme"][0] * 100)}
                              if en_iyi["eslesme"] else None)})
    return sonuc


def etiket(secim, rakip_ad=None):
    """'OP.GG + U.GG · %54 kazanma · 1.240 maç · Darius'a karşı %61 (34 maç)'"""
    if not secim:
        return ""
    genel = [k for k in secim["kaynaklar"] if "karşı" not in k]
    parcalar = [" + ".join(genel) or "OP.GG"]
    if secim.get("oran") is not None:
        parcalar.append(f"%{secim['oran']} kazanma, {secim['mac']:,} maç".replace(f"{secim['mac']:,}", f"{secim['mac']:,}".replace(",", ".")))
    if secim.get("eslesme") and rakip_ad:
        e = secim["eslesme"]
        parcalar.append(f"{rakip_ad} karşısında %{e['oran']} ({e['mac']} maç)")
    return " · ".join(parcalar)


def birlestir(opgg_genel, opgg_eslesme, ugg, rakip_ad=None, run_sirala=None):
    """Kaynaklardan tek bir öneri seti üretir. Biçim build_opgg'nin beklediği gibidir."""
    kaynaklar = [k for k in (opgg_genel, ugg) if k]
    if not kaynaklar and not opgg_eslesme:
        return None
    esl_etiket = f"{rakip_ad} karşısında" if rakip_ad else "rakip karşısında"

    def liste(alan):
        out = [(k["kaynak"], False, k.get(alan)) for k in kaynaklar]
        if opgg_eslesme:
            out.append((esl_etiket, True, opgg_eslesme.get(alan)))
        return out

    # U.GG rünlerini satır sırasına diz (karışık geliyor)
    if ugg and ugg.get("run") and run_sirala:
        duzgun = []
        for r in ugg["run"]:
            s = run_sirala(r["ana"], r["yan"], r["karisik_ids"])
            if s:
                duzgun.append(dict(r, ana_ids=s[0], yan_ids=s[1], parca_ids=ugg.get("parca") or []))
        ugg = dict(ugg, run=duzgun)
        kaynaklar = [k for k in (opgg_genel, ugg) if k]

    def run_listesi():
        out = []
        for k in kaynaklar:
            out.append((k["kaynak"], False, [dict(r, ids=r["ana_ids"] + r["yan_ids"]) for r in k.get("run") or []
                                              if r.get("ana_ids") and r.get("yan_ids")]))
        if opgg_eslesme:
            out.append((esl_etiket, True, [dict(r, ids=r["ana_ids"] + r["yan_ids"]) for r in opgg_eslesme.get("run") or []]))
        return out

    cek = sec(liste("cekirdek"))
    if not cek:
        return None
    sonuc = {
        "yama": (opgg_genel or opgg_eslesme or {}).get("yama"),
        "kaynak_adlari": sorted({k["kaynak"] for k in kaynaklar} | ({esl_etiket} if opgg_eslesme else set())),
        "cekirdek": dict(cek, etiket=etiket(cek, rakip_ad)),
        "bot": sec(liste("bot")),
        "baslangic": sec(liste("baslangic"), sirali=True),
        "buyu": sec(liste("buyu")),
        "yetenek": sec([(e, m, [dict(a, ids=a["sira"]) for a in (l or [])]) for e, m, l in liste("yetenek")], sirali=False),
        "run": sec(run_listesi()),
    }
    for alan in ("bot", "buyu", "yetenek", "run"):
        if sonuc[alan]:
            sonuc[alan]["etiket"] = etiket(sonuc[alan], rakip_ad)
    if sonuc["run"] and not sonuc["run"].get("parca_ids"):
        # parça bilgisi yoksa OP.GG'nin en iyi sayfasından al
        for k in (opgg_genel, opgg_eslesme):
            for r in (k or {}).get("run") or []:
                if r.get("parca_ids"):
                    sonuc["run"]["parca_ids"] = r["parca_ids"]
                    break
    # geç oyun eşyaları: tüm kaynaklardaki tekil eşyaları puanla
    tek = {}
    for _, eslesme, l in liste("son"):
        for a in l or []:
            i = a["ids"][0]
            t = tek.setdefault(i, [0, 0])
            if not eslesme:
                t[0] += a["mac"]
                t[1] += a["kazanma"]
    cekirdek_ids = set(cek["ids"])
    son = [{"id": i, "mac": m, "oran": round(k / m * 100) if m else None, "puan": guvenilir_oran(k, m) + 0.01 * math.log10(m + 1)}
           for i, (m, k) in tek.items() if i not in cekirdek_ids and m]
    son.sort(key=lambda e: -e["puan"])
    sonuc["son"] = son[:8]
    # şampiyonun verisinde görülen bütün eşyalar (rakibe özel eşya seçiminde tercih edilir)
    havuz = set()
    for _, _, l in liste("cekirdek") + liste("son"):
        for a in l or []:
            havuz.update(a.get("ids") or [])
    sonuc["havuz"] = havuz
    return sonuc
