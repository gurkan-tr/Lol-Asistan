# LoL Asistan

Seçim ekranında karşı takımı analiz eder, koridoruna göre şampiyon önerir ve
o maça özel build çıkarır. Maç bitince de "bir dahaki sefere ne daha iyi olurdu"
analizini gösterir.

## Kurulum (bir kere)

1. Bu klasörü bir yere çıkar (örneğin Belgeler).
2. **`KURULUM.bat`** dosyasına çift tıkla.
   - Bilgisayarında Python yoksa kurulum onu da otomatik kurar (önce Windows'un winget'iyle, olmazsa python.org'dan indirerek).
   - Windows "Bilgisayarınız korundu" uyarısı gösterirse **Ek bilgi → Yine de çalıştır**'a bas. İnternetten indirilen her .bat dosyasında bu uyarı çıkar.

Kurulum bitince masaüstünde **LoL Asistan** kısayolu oluşur. Bundan sonra sadece ona tıklaman yeterli.

## Kullanım

- Uygulamayı aç, sonra LoL'ü aç (sıra fark etmez). Uygulama istemciye kendisi bağlanır.
- Seçim ekranı açılınca her şey otomatik gelir:
  - **Solda** karşı takım, koridorlarıyla birlikte. Senin rakibin nane yeşiliyle işaretli.
  - **Ortada** sana önerilen şampiyon ve nedenleri. Diğer seçeneklere tıklayınca onların buildi görünür.
  - **Altta** build sırası. Turuncu çerçeveli eşyalar bu maça özel seçildi. Altındaki **B planı**, maçta Tab'a bakıp karar vermen için hazırlandı.
- **Rünler**: Build'in altında, rakiplere göre ayarlanmış bir rün sayfası var. Örneğin:
  - patlama hasarlı bir koridor rakibine karşı Kemik Kaplama
  - uzaktan dürten bir rakibe karşı İkinci Rüzgar
  - tanklara karşı Kesici
  - bol CC'ye karşı İnat parçası
  
  Neden seçildiği altında yazıyor.
- **Ban sırası** sana geldiğinde solda **ban önerisi** çıkar. Öneriler ana şampiyonlarını counterlayanlara ve maç geçmişinde sana en çok kaybettirenlere göre seçilir.
- **Maç planı**: oyunun temposu (erken mi geç mi güçlüsünüz), takım savaşı stili, koridor rakibine karşı ipuçları ve o rakiple geçmiş sonuçların.
- **Sihirdar büyüleri**: rakibe göre önerilir (Zed'e karşı Bariyer, çok CC'ye karşı Arındır gibi). Sıçra'yı alıştığın tuşta (D veya F) bırakır.
- Şampiyonunu kilitleyince build, oyun içi mağazaya **eşya seti** olarak eklenir. Rün sayfası
  da istemcide **"LoL Asistan: Şampiyon"** adıyla oluşturulup seçilir. Senin kendi rün
  sayfalarına dokunmaz. İstersen **"Rünleri istemciye uygula"** düğmesiyle elle de uygulayabilirsin.
- Maç sırasında uygulama, seçim ekranında hazırlanan planı (build, nedenleri, B planı, rünler) gösterir. Bu plan maç içinde değişmez; uygulama maç sırasında oyunu analiz etmez. Maç bitince sonuç ekranı açılır.

### Arka planda çalışma

Pencereyi kapatınca uygulama kapanmaz, saatin yanındaki simgeye küçülür. Maç bulununca
bildirim gönderir ve pencereyi öne getirir. Tamamen kapatmak için simgeye sağ tıkla ve
**Çıkış**'ı seç. Ayarlar'dan **Windows açılınca başlat** seçeneğini açarsan bilgisayar açılınca
simge durumunda kendiliğinden başlar.

### Takıma kopyala

Maç planı kartındaki **Takıma kopyala** düğmesi planın kısa halini panoya kopyalar, sen de
seçim ekranı sohbetine Ctrl+V ile yapıştırırsın. Örnek: "Rakip erken güçlü: ilk 15 dk sakin
oynayalım, objektifleri avantajlıyken alalım."

### Ölüm haritası

Maç bitince maçın zaman çizelgesine bakılır ve her ölümün dakikası, yeri ve seni kimin
öldürdüğü küçük bir haritada gösterilir. Altında öneriler çıkar, örneğin "İlk 14 dakikada 3 kez
öldün" ya da "Ölümlerinin çoğu nehirde, görüşsüz girme".

### Performansım sekmesi

Program son 100 maçını okur ve şunları gösterir:
- genel kazanma oranın ve KDA'n
- son 10 maçın
- şampiyon bazında sonuçların
- zorlandığın koridor rakipleri
- sana en çok kaybettiren şampiyonlar
- ban önerilerin
- maç sonu analizlerinde en sık tekrarladığın hata

Şampiyon önerileri de artık bu verileri kullanıyor: ustalık puanı yüksek ama kazanamadığın
bir şampiyon geri düşer, iyi gittiğin şampiyonlar öne çıkar. Okunan maçlar `kisisel/` klasörüne
kaydedilir, sonraki açılışlarda sadece yeni maçlar indirilir.

İstemci kapalıyken **"Örnek maçı göster"** ya da **"Takımları elle gir"** ile deneyebilirsin.

## Ayarlar

Uygulamadaki **Ayarlar** düğmesinden:
- Rol atanmayan modlar (normal, ARAM dışı özel oyunlar) için varsayılan koridorun
- Her koridor için favori şampiyonların
- Eşya seti, rün sayfası ve sihirdar büyülerinin otomatik ayarlanıp ayarlanmayacağı
- Oyun farklı bir klasördeyse oyun klasörü

## Otomatik güncelleme

Uygulama açılışta GitHub deposundaki `surum.txt` dosyasına bakar. Daha yeni bir sürüm varsa
üstte **"Güncelle"** düğmesi çıkar. Düğmeye basınca yeni sürüm indirilip kurulur ve uygulama
yeniden açılır. Ayarların, maç geçmişin ve önbellek dosyaların silinmez.

Depo herkese açıksa (public) hiçbir ayar gerekmez, güncellemeler herkese otomatik gelir.
Depo gizliyse Ayarlar → Güncelleme kısmına okuma yetkili bir **GitHub anahtarı** girilmelidir;
anahtar sadece o bilgisayarda (`config.json` içinde) saklanır ve GitHub'a yüklenmez.

**Yeni sürüm yayınlamak:** GitHub'da depo sayfasında **Add file → Upload files** yolunu izle.
Yeni sürümün içindeki her şeyi sürükle ve **Commit changes**'a bas. Eski dosyaların
üzerine yazılır.

## Sorun giderme

- **Kısayol çalışmıyor / pencere açılmıyor:** `KURULUM.bat`'ı tekrar çalıştır. Hâlâ olmazsa Python 3.12 kullandığından emin ol.
- **"LoL istemcisi kapalı" diyor ama açık:** Ayarlar → Oyun klasörü kısmına oyunun kurulu olduğu klasörü yaz.
- **"Boş rün sayfası yeri yok" diyor:** İstemcide kullanmadığın bir rün sayfasını sil ve düğmeye tekrar bas.
  Program bundan sonra hep aynı sayfayı güncelleyeceği için bunu bir kere yapman yeterli.
- **Resimler görünmüyor:** İnternet bağlantısı gerekiyor; resimler Riot'un sunucusundan gelir.

## Kurallar hakkında

Uygulama yalnızca seçim ekranı ve maç sonu ekranı bilgilerini okur, rün sayfası, sihirdar büyüleri ve eşya seti ayarlar, kendi maç geçmişini okur, maç sırasında
analiz yapmaz ve oyun dosyalarına dokunmaz. Riot Games tarafından onaylanmamıştır.

---
*İleri seviye:* `araclar/EXE_YAP.bat` ile Python gerektirmeyen tek bir `.exe` üretebilirsin.
Komut satırı sürümü `main.py` olarak duruyor. Counter tablosu `data/counters.json`,
şampiyon bilgileri `data/champions.txt` dosyasında ve düzenlenebilir.
