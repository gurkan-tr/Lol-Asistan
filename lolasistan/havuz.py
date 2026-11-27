"""Şampiyon havuzu önerisi: ana şampiyonun + onun zor eşleşmelerini kapatan iki şampiyon.

Ana şampiyon senin maç geçmişinden seçilir. Zor eşleşmeleri ve onlara karşı kimin iyi
olduğu OP.GG'nin gerçek eşleşme verisinden gelir; internet yoksa elle yazılmış counter
tablosuna düşülür."""


def _guvenilir(galibiyet, mac, onsel=10):
    return (galibiyet + 0.5 * onsel) / (mac + onsel)


def havuz_oner(db, rol, kisisel, eslesme_getir=None, favoriler=None):
    """
    kisisel        : {alias: Sayac} — senin son maçlardaki sonuçların
    eslesme_getir  : f(Sampiyon) -> {rakip_id: (maç, o şampiyonun galibiyeti)} ya da None
    Dönüş: {"ana": {...}, "yedekler": [{...}, {...}], "kaynak": "OP.GG" | "tablo"} ya da None
    """
    rol_sampiyonlari = {s.alias: s for s in db.rol_sampiyonlari(rol)}
    # 1) ana şampiyon: bu koridorda en güvenilir kazandığın
    adaylar = [(a, k) for a, k in (kisisel or {}).items() if a in rol_sampiyonlari and k.mac >= 3]
    adaylar.sort(key=lambda x: -(_guvenilir(x[1].galibiyet, x[1].mac) + 0.01 * min(x[1].mac, 20)))
    if adaylar:
        ana_alias, ana_k = adaylar[0]
        ana_neden = f"Bu koridorda en iyi gittiğin şampiyon: {ana_k.mac} maçta %{round(ana_k.oran * 100)}"
    else:
        fav = [db.bul(x) for x in (favoriler or [])]
        fav = [s for s in fav if s and s.alias in rol_sampiyonlari]
        if not fav:
            return None
        ana_alias, ana_neden = fav[0].alias, "Favori listendeki ilk şampiyon"
    ana = db.sampiyonlar[ana_alias]

    # 2) ana şampiyonun zor eşleşmeleri
    veri = eslesme_getir(ana) if eslesme_getir else None
    zor = []
    kaynak = "OP.GG"
    if veri:
        for cid, (mac, kaz) in veri.items():
            o = db.id_ile(cid)
            if o and mac >= 40 and o.alias in rol_sampiyonlari and kaz / mac <= 0.475:
                zor.append((o, kaz / mac, mac))
        zor.sort(key=lambda x: x[1])
        zor = zor[:4]
    if not zor:
        kaynak = "tablo"
        zor = [(db.sampiyonlar[a], None, 0) for a in db.counterlayanlar(ana)
               if a in db.sampiyonlar and a in rol_sampiyonlari][:4]
    if not zor:
        return {"ana": {"alias": ana.alias, "neden": ana_neden}, "yedekler": [], "kaynak": kaynak, "zor": []}

    # 3) her zor rakibe karşı kim iyi?
    karsi = {}   # rakip alias -> {aday alias: kazanma oranı}
    for o, _, _ in zor:
        tablo = {}
        v = eslesme_getir(o) if (eslesme_getir and kaynak == "OP.GG") else None
        if v:
            for cid, (mac, kaz) in v.items():
                c = db.id_ile(cid)
                if c and mac >= 30 and c.alias in rol_sampiyonlari and c.alias != ana.alias:
                    tablo[c.alias] = 1 - kaz / mac        # c'nin o'ya karşı kazanma oranı
        else:
            for a in db.counterlayanlar(o):
                if a in rol_sampiyonlari and a != ana.alias:
                    tablo[a] = 0.56
        karsi[o.alias] = tablo

    def aday_puani(c, hedefler):
        p = sum(karsi[h].get(c, 0.5) - 0.5 for h in hedefler)
        k = (kisisel or {}).get(c)
        if k and k.mac:
            p += 0.015 * min(k.mac, 10) / 10 + 0.02 * (k.oran - 0.5)   # tanıdık şampiyon tercih edilir
        return p

    secilen, kalan = [], [o.alias for o, _, _ in zor]
    for _ in range(2):
        hedef = kalan or [o.alias for o, _, _ in zor]
        adaylar = {c for t in karsi.values() for c in t} - {s["alias"] for s in secilen}
        if not adaylar:
            break
        en = max(adaylar, key=lambda c: aday_puani(c, hedef))
        kapsadigi = [h for h in hedef if karsi[h].get(en, 0) >= 0.515]
        if not kapsadigi:
            break
        detay = ", ".join(f"{db.sampiyonlar[h].ad} (%{round(karsi[h][en] * 100)})" if kaynak == "OP.GG"
                          else db.sampiyonlar[h].ad for h in kapsadigi)
        k = (kisisel or {}).get(en)
        secilen.append({"alias": en, "kapsadigi": kapsadigi,
                        "neden": f"Ana şampiyonunun zorlandığı {detay} karşısında iyi"
                                 + (f"; sen bununla {k.mac} maç oynadın" if k and k.mac else "")})
        kalan = [h for h in kalan if h not in kapsadigi]
    return {"ana": {"alias": ana.alias, "neden": ana_neden}, "yedekler": secilen, "kaynak": kaynak,
            "zor": [{"alias": o.alias, "oran": round(oran * 100) if oran is not None else None, "mac": mac}
                    for o, oran, mac in zor]}
