"""Sihirdar büyüsü önerisi (maç öncesi)."""
from dataclasses import dataclass, field

# id: (Türkçe ad, Data Dragon resim adı)
BUYU = {
    4: ("Sıçra", "SummonerFlash"), 14: ("Tutuştur", "SummonerDot"), 12: ("Işınlan", "SummonerTeleport"),
    7: ("Şifa", "SummonerHeal"), 3: ("Bitkinlik", "SummonerExhaust"), 21: ("Bariyer", "SummonerBarrier"),
    1: ("Arındır", "SummonerBoost"), 6: ("Hayalet", "SummonerHaste"), 11: ("Çarp", "SummonerSmite"),
}
SICRA = 4
KIRILGAN = {"adc_crit", "adc_onhit", "adc_spell", "ap_mage", "ap_onhit", "support_mage", "enchanter"}


@dataclass
class BuyuOnerisi:
    ikinci: int                 # Sıçra'nın yanındaki büyü
    neden: str
    sicra_d: bool = False       # Sıçra D tuşunda mı (istemcideki mevcut seçimden)
    notlar: list = field(default_factory=list)

    def idler(self):
        return (SICRA, self.ikinci) if self.sicra_d else (self.ikinci, SICRA)


def buyu_oner(sampiyon, arketip, rol, profil, rakip, sicra_d=False) -> BuyuOnerisi:
    a = arketip
    rakip_suikast = rakip is not None and (rakip.sinif == "assassin" or (rakip.var("burst") and rakip.var("dive")))

    if rol == "jungle":
        return BuyuOnerisi(11, "Ormancı: Çarp şart", sicra_d)

    if rol == "adc":
        if profil.cc >= 4:
            return BuyuOnerisi(1, f"Rakipte {profil.cc} CC'li şampiyon → Arındır", sicra_d)
        if profil.suikastci >= 2:
            return BuyuOnerisi(21, f"{profil.suikastci} suikastçı var → Bariyer patlamayı karşılar", sicra_d)
        return BuyuOnerisi(7, "Standart: Şifa (sen ve destek için)", sicra_d)

    if rol == "support":
        if a in ("enchanter",) and (profil.suikastci >= 1 or profil.dalis >= 3):
            return BuyuOnerisi(3, "Dalış/suikastçı var → Bitkinlik ile taşıyıcını koru", sicra_d)
        if a == "enchanter":
            return BuyuOnerisi(3, "Koruyucu destek: Bitkinlik", sicra_d)
        return BuyuOnerisi(14, "Koridorda öldürme baskısı: Tutuştur", sicra_d)

    # top / mid
    if rakip is not None and rakip.var("heal") and a in ("ad_bruiser", "ap_bruiser", "ad_crit_melee", "ad_lethality", "ap_burst"):
        return BuyuOnerisi(14, f"{rakip.ad} iyileşiyor → Tutuştur hem öldürür hem iyileşmeyi keser", sicra_d)
    if rol == "mid" and rakip_suikast and a in KIRILGAN:
        return BuyuOnerisi(21, f"{rakip.ad} sana dalacak → Bariyer", sicra_d)
    if profil.cc >= 4 and a in KIRILGAN:
        return BuyuOnerisi(1, f"Rakipte {profil.cc} CC'li şampiyon → Arındır", sicra_d)
    if a in ("ad_lethality", "ap_burst"):
        return BuyuOnerisi(14, "Suikastçı: Tutuştur ile öldürme garantisi", sicra_d)
    if rol == "mid" and a in ("ad_crit_melee",):
        return BuyuOnerisi(14, "Koridor baskısı: Tutuştur", sicra_d)
    return BuyuOnerisi(12, "Işınlan: koridora hızlı dönüş ve haritaya katılım", sicra_d)
