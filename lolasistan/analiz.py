"""Takım analizi: rakiplerin rol tahmini ve takım profili."""
from dataclasses import dataclass
from itertools import permutations

from .champs import ROLLER, ROL_AD


def rol_uyum(s, rol) -> float:
    if not s.roller:
        return 0.5
    if rol in s.roller:
        return [3.0, 2.0, 1.2, 1.0, 1.0][s.roller.index(rol)]
    return 0.0


def rolleri_tahmin_et(sampiyonlar, bilinen: dict = None) -> dict:
    """Rakip takım şampiyonlarını en olası koridorlara dağıtır. {rol: Sampiyon}"""
    bilinen = dict(bilinen or {})
    sonuc = {r: s for r, s in bilinen.items() if s}
    kalan = [s for s in sampiyonlar if s and s not in sonuc.values()][:5]
    bos = [r for r in ROLLER if r not in sonuc]
    if not kalan:
        return sonuc
    en_iyi, en_iyi_perm = -1.0, None
    for perm in permutations(bos, min(len(kalan), len(bos))):
        p = sum(rol_uyum(s, r) for s, r in zip(kalan, perm))
        if p > en_iyi:
            en_iyi, en_iyi_perm = p, perm
    for s, r in zip(kalan, en_iyi_perm or []):
        sonuc[r] = s
    return sonuc


@dataclass
class TakimProfili:
    sayi: int = 0
    ad: float = 0.0
    ap: float = 0.0
    tank: int = 0
    iyilesme: int = 0
    cc: int = 0
    suikastci: int = 0
    nisanci: int = 0
    kalkan: int = 0
    gorunmezlik: int = 0
    durtme: int = 0
    dalis: int = 0
    engage: int = 0
    menzilli: int = 0

    @property
    def ad_orani(self) -> float:
        t = self.ad + self.ap
        return self.ad / t if t else 0.5

    @property
    def ap_orani(self) -> float:
        return 1 - self.ad_orani

    def notlar(self) -> list:
        if not self.sayi:
            return ["Henüz rakip şampiyon seçilmedi."]
        n = [f"Hasar dağılımı: %{round(self.ad_orani * 100)} fiziksel (AD) / "
             f"%{round(self.ap_orani * 100)} büyü (AP)"]
        if self.sayi >= 2 and self.ad_orani >= 0.7:
            n.append("Ağırlıklı FİZİKSEL hasar → zırh çok değerli")
        if self.sayi >= 2 and self.ap_orani >= 0.7:
            n.append("Ağırlıklı BÜYÜ hasarı → büyü direnci çok değerli")
        if self.iyilesme >= 2:
            n.append(f"{self.iyilesme} şampiyon ciddi iyileşiyor → iyileşme azaltma (anti-heal) şart")
        if self.tank >= 2:
            n.append(f"Kalın ön cephe ({self.tank} tank) → zırh/büyü delme ve %can hasarı")
        if self.cc >= 3:
            n.append(f"Bol kitle kontrolü ({self.cc} CC'li şampiyon) → Merkür Botları / arınma")
        if self.suikastci >= 2:
            n.append(f"{self.suikastci} suikastçı/patlama tehdidi → hayatta kalma eşyası")
        if self.gorunmezlik >= 1:
            n.append("Görünmezlik kullanan var → Kâhin Merceği ve Kontrol Totemi al")
        if self.durtme >= 2:
            n.append("Uzaktan dürtme (poke) ağır → can yenilemesi / hızlı engage önemli")
        if self.engage >= 3:
            n.append("Güçlü engage'leri var → pozisyonuna dikkat et, kaçış/peel değerli")
        if self.kalkan >= 3:
            n.append("Bol kalkan var → kalkan kırıcı eşyalar işe yarar")
        return n


def profil_cikar(sampiyonlar) -> TakimProfili:
    p = TakimProfili()
    for s in sampiyonlar:
        if not s:
            continue
        p.sayi += 1
        agirlik = 0.6 if s.sinif == "tank" else 0.5 if s.sinif == "enchanter" else 1.0
        if s.hasar == "AD":
            p.ad += agirlik
        elif s.hasar == "AP":
            p.ap += agirlik
        else:
            p.ad += agirlik / 2
            p.ap += agirlik / 2
        p.tank += s.tanky
        p.iyilesme += s.var("heal")
        p.cc += s.var("cc")
        p.suikastci += s.sinif == "assassin" or (s.var("burst") and s.var("dive"))
        p.nisanci += s.sinif == "marksman"
        p.kalkan += s.var("shield")
        p.gorunmezlik += s.var("stealth")
        p.durtme += s.var("poke")
        p.dalis += s.var("dive")
        p.engage += s.var("engage")
        p.menzilli += s.menzilli
    return p


def rol_etiketi(rol):
    return ROL_AD.get(rol, rol)
