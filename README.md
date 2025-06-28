# Panblog

Panblog, Markdown dosyalarından statik bir blog sitesi oluşturan basit bir sistemdir. Pandoc ve Python betikleri kullanarak içeriği HTML'e dönüştürür.

## Proje Yapısı

- `content/`: Blog yazılarınızı ve ana sayfa içeriğini `.md` formatında barındırır.
  - `index.md`: Ana sayfanın içeriğini belirler.
  - Diğer `.md` dosyaları: Her biri ayrı bir blog gönderisidir.
- `templates/`: HTML şablonlarını içerir.
  - `homepage.html`: Ana sayfanın şablonu.
  - `post.html`: Blog gönderilerinin şablonu.
- `public/`: Oluşturulan statik HTML dosyaları ve diğer varlıkların (resimler, stil dosyaları) bulunduğu dizin. Bu dizin, web sunucunuzun kök dizini olarak ayarlanmalıdır.
  - `assets/`: Resimler gibi statik varlıkları içerir.
  - `style.css`: Site için özel stil dosyası.
- `build.sh`: Siteyi oluşturan ana betik. Markdown dosyalarını işler, HTML'e dönüştürür ve `public` dizinine yerleştirir.
- `process_markdown.py`: Markdown dosyalarını işleyen, resim yollarını güncelleyen ve ana sayfayı oluşturan Python betiği.
- `cleanup_assets.py`: `public/assets` dizininde bulunup hiçbir yazıda referans verilmeyen (kullanılmayan) resimleri temizleyen Python betiği.

## Nasıl Çalışır?

1.  **İçerik Oluşturma**: `content` dizininde Markdown formatında (`.md`) yazılar oluşturulur. Yazıların başlığı, yazarı ve tarihi gibi meta veriler, dosyanın başına YAML formatında eklenir.
2.  **Siteyi Oluşturma**: `build.sh` betiği çalıştırılır.
    - Bu betik, `content` dizinindeki her bir Markdown dosyasını `process_markdown.py` ve `pandoc` kullanarak HTML'e dönüştürür.
    - `process_markdown.py`, resim yollarını `public/assets` dizinine kopyalar ve Markdown içindeki yolları günceller. Ayrıca, ana sayfayı (`index.html`) oluşturur.
    - `cleanup_assets.py`, kullanılmayan resimleri `public/assets` dizininden siler.
3.  **Yayınlama**: `public` dizininin içeriği bir web sunucusunda yayınlanır.

## Kullanılan Teknolojiler

- **Pandoc**: Markdown'dan HTML'e dönüştürme için kullanılır.
- **Python**: İçerik işleme, resim optimizasyonu ve dosya yönetimi için kullanılır.
  - **Pillow**: Resim optimizasyonu için.
  - **Markdown**: Markdown'ı HTML'e dönüştürmek için.
- **Bash**: Site oluşturma sürecini otomatikleştirmek için.
- **Pico.css**: Minimalist bir CSS iskeleti.

## Gelecekteki Geliştirmeler İçin Notlar

- **Navigasyon**: `Hakkımda` ve `Arşiv` gibi bağlantılar şu anda `#` olarak ayarlanmıştır. Bu sayfalar oluşturulduğunda bağlantılar güncellenmelidir.
- **YAML Meta Verileri**: Gönderilerde tutarlılık için `title`, `author`, ve `date` gibi meta verilerin kullanılması önemlidir.
- **Stil**: `public/style.css` dosyası, sitenin görünümünü özelleştirmek için kullanılabilir.
- **Bağlantılar**: Markdown dosyaları arasındaki iç bağlantılar, `[link metni](dosya-adi.md)` şeklinde olmalıdır. `build.sh` betiği, bu bağlantıları otomatik olarak `.html` uzantılı hale getirecektir.
