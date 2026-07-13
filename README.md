# Sağlık Kurumları Anlaşma Takip Sistemi

Sigorta şirketlerimizin (AXA, HDI, Acıbadem, Türkiye, Anadolu, Allianz, Mapfre)
Tamamlayıcı Sağlık Sigortası (TSS) ve Özel Sağlık Sigortası (ÖSS) ürünlerinde
hangi sağlık kurumlarıyla (hastane, tıp merkezi, diş kliniği vb.) anlaşmalı
olduğunu takip eden Django backend'i. Veri, tamamlayicisaglik.com'un genel
kamuya açık internal API'sinden çekilir, kendi Postgres veritabanımızda tutulur
ve Next.js frontend'imize Bearer token korumalı bir REST API ile sunulur.

```
tamamlayicisaglik.com  --(scraper)-->  Django + Postgres  --(REST API)-->  Next.js
                                              ^
                                              |
                                    Django Admin Dashboard
                                    (manuel "Run now" tetikleme)
```

---

## 1. Klasör yapısı

```
healthCareContracte/
├── manage.py
├── requirements.txt
├── .env                      # gerçek ortam değişkenleri (git'e girmez)
├── .env.example               # şablon
├── Dockerfile
├── entrypoint.sh               # container başlarken: migrate → collectstatic → gunicorn
├── docker-compose.yml
├── config/                     # Django project (settings, urls, wsgi)
├── companies/                  # InsuranceCompany
├── geo/                        # City, District + seed/sync management command'ları
├── products/                   # ProductType, InstitutionType
├── institutions/                # HealthInstitution (asıl scrape edilen veri)
├── scraper/                    # ScrapeJob, HTTP client, servis katmanı, admin action
└── api/v1/                     # DRF: authentication, serializers, views, urls
```

Her app'in tek bir sorumluluğu var: `companies` = sigorta şirketi referans verisi,
`geo` = il/ilçe referans verisi, `products` = ürün tipi + kurum tipi referans verisi,
`institutions` = scrape edilen gerçek veri, `scraper` = veri çekme motoru,
`api` = Next.js'e sunulan salt-okunur sözleşme.

---

## 2. Veri kaynağı: tamamlayicisaglik.com internal API

Hiçbiri resmi/dokümante değil ama hepsi **kimlik doğrulama gerektirmeden** (cookie/CSRF
token olmadan) düz `GET` ile çalışıyor — bunu canlı test ederek doğruladık.

| Endpoint | Ne döndürür | Kullanım yeri |
|---|---|---|
| `GET /internal-api/cities` | `{"data": [{"id": 34, "name": "İstanbul"}, ...]}` — 81 il | `id` = **plaka kodu** (doğrulandı, örn. İstanbul=34) |
| `GET /internal-api/districts?cityId=34` | `{"data": [{"id": 420, "name": "Adalar"}, ...]}` | `sync_districts` komutuyla bir kerelik çekilip DB'ye yazılır |
| `GET /internal-api/hospital-types` | `{"data": [{"id": 1, "name": "Hastane", "defaultItem": true}, ...]}` — 9 kurum türü | `seed_reference_data` içine sabit olarak gömülü |
| `GET /internal-api/search-hospital?query=&companyIds[]=6&cityId=34&productTypeId=1&page=1&limit=50` | **Asıl anlaşmalı kurum listesi.** Düz (flat) şekil: `{"data":[...], "current_page":, "per_page":, "total":, "last_page":}` | `scraper/client.py: get_institutions()` |
| `GET /internal-api/company-list-results?...` | Şirket karşılaştırma widget'ı (iç içe şekil: `{"data":{"data":[...]}}`) | Sadece şirket id'lerini keşfetmek için kullanıldı, scraper akışında kullanılmıyor |
| `GET /internal-api/networks?companyIds[]=6&productTypeId=1` | Şirketin "network" (Altın/Gümüş gibi) tier'ları | Şu an kullanılmıyor, ileride genişletme için not edildi |

### Bilinen tuhaflık (kod içinde otomatik düzeltiliyor)

`search-hospital`'ın arkası PHP/Laravel. PHP'de bir dizide index atlarsa (örn.
sunucu bir kaydı filtrelediğinde), `json_encode` o diziyi JSON **array** değil
JSON **object** (`{"0":..,"1":..,"48":..}`) olarak serialize ediyor. `limit=50`
ile bu gerçekten oluyor. `scraper/client.py` içindeki `_as_list()` fonksiyonu
her iki şekli de normalize ediyor — bu yoksa bazı sayfalarda sessizce çöküyordu.

### Doğrulanmış id eşlemeleri

**Şirketler** (`companies.InsuranceCompany.external_id`):

| Kod | external_id | slug |
|---|---|---|
| AXA | 6 | axa-sigorta |
| HDI | 17 | hdi-sigorta |
| ACIBADEM | 15 | acibadem-sigorta |
| TURKIYE | 32 | turkiye-sigorta |
| ANADOLU | 7 | anadolu-sigorta |
| ALLIANZ | 8 | allianz-sigorta |
| MAPFRE | 3 | mapfre-sigorta |

**Ürün tipleri** (`products.ProductType.external_id`) — canlı veriyle doğrulandı
(AXA/İstanbul: TSS=189 sonuç, ÖSS=563 sonuç, oranı beklenenle tutarlı):

| Kod | external_id (productTypeId) |
|---|---|
| TSS | 1 |
| OSS | 3 |

**Kurum tipleri** (`products.InstitutionType.external_id`) — `/internal-api/hospital-types`'tan:

| Kod | external_id | Ad |
|---|---|---|
| HASTANE | 1 | Hastane |
| FIZIK_TEDAVI | 2 | Fizik Tedavi Merkezi |
| TIP_MERKEZI | 4 | Tıp Merkezi & Poliklinik |
| DOKTOR | 6 | Doktor |
| DIS | 7 | Diş Hekimi & Kliniği |
| TANI_GORUNTULEME | 8 | Tanı & Görüntüleme Merkezi |
| EVDE_BAKIM | 10 | Evde Bakım |
| OPTIK | 11 | Optik |
| MEDIKAL | 12 | Medikal ve Tıbbi Malzeme |

**İller**: `geo.City.external_id == geo.City.plate_code` (81 il, birebir eşleşme doğrulandı).
**İlçeler**: `geo.District.external_id`, `sync_districts` komutuyla canlı çekilip yazılır (970 ilçe).

---

## 3. Veritabanı modelleri

- **`companies.InsuranceCompany`** — name, code, slug, external_id, is_active, raw_payload
- **`geo.City`** — name, plate_code (unique), external_id
- **`geo.District`** — city (FK), name, external_id — `unique(city, name)`
- **`products.ProductType`** — name, code (TSS/OSS), external_id
- **`products.InstitutionType`** — name, code, external_id
- **`institutions.HealthInstitution`** — company/product_type/institution_type/city/district (FK),
  external_id, name, slug, address/phone/latitude/longitude (search-hospital bunları vermiyor,
  şu an boş kalıyor), is_active, last_seen_at, last_scrape_job (FK), raw_payload (JSON).
  `unique(company, product_type, external_id)` — scrape sırasında bu anahtarla upsert edilir.
- **`scraper.ScrapeJob`** — company/product_type/city/district/institution_type (hepsi nullable
  FK — **boş = "hepsi"**), status (PENDING/RUNNING/SUCCESS/PARTIAL/FAILED), triggered_by,
  request_params (JSON), pages_fetched, created_count, updated_count, result_count,
  error_message, log (TextField, her adım append edilir), started_at/finished_at.

---

## 4. Scraper nasıl çalışır

- **`scraper/client.py` → `TamamlayiciSaglikClient`** — `requests.Session` tabanlı ince HTTP
  istemci. Retry/backoff (429/5xx için 3 deneme), tüm endpoint path'leri `settings.SCRAPER_CONFIG`'ten
  okunur (kod değiştirmeden `.env`'den override edilebilir). `get_institutions()` asıl kullanılan metod.
- **`scraper/services.py` → `ScrapeJobRunner.run(job)`** — job'daki boş bırakılmış filtreleri
  "hepsi" olarak çözer (örn. company boşsa 7 şirketin hepsi), her (şirket × ürün tipi × il)
  kombinasyonu için `search-hospital`'ı sayfalayarak çeker, `HealthInstitution.objects.update_or_create(...)`
  ile veritabanına yazar. İlçe adı (`district_name` string) ve kurum tipi (`hospital_type.id`)
  job'da belirtilmişse **client-side** filtrelenir (server-side garanti değil).
- **`scraper/runner.py` → `launch_job_async(job_id)`** — job'ı bir `threading.Thread` içinde
  arka planda çalıştırır (Celery/Redis **yok**, bilinçli tercih — basitlik için). Admin'in
  "Run now" action'ı bunu çağırır, sayfa bloklanmaz.
  `close_old_connections()` her thread başında/sonunda çağrılır (Django'nun per-request DB
  connection yönetimi thread'lere miras kalmıyor).
- **`scraper/exceptions.py`** — `ScraperNotConfigured` (endpoint path boşsa), `ScraperHTTPError`,
  `ScraperParseError`.

---

## 5. Dashboard (Django Admin + django-unfold)

`https://<domain>/admin/` — `/admin/scraper/scrapejob/add/` üzerinden yeni bir scrape işi
oluşturulur. **Herhangi bir filtre alanı boş bırakılırsa "hepsi" anlamına gelir**:

- Company boş → 7 şirketin hepsi
- Product Type boş → TSS + ÖSS
- City boş → 81 ilin hepsi (**büyük iş**, saatler sürebilir)
- District/Institution Type boş → filtrelenmez

Kaydettikten sonra listeden job'ı seçip **"Şimdi çalıştır (Run now)"** bulk action'ını
çalıştır. Durum takibi için sayfayı birkaç saniyede bir yenile (canlı otomatik yenileme
yok — bilinçli olarak basit tutuldu, websocket/polling eklemedik).

Diğer admin ekranları: `InsuranceCompany`, `City` (District inline), `ProductType`,
`InstitutionType`, `HealthInstitution` (filtrelenebilir/aranabilir liste).

---

## 6. DRF API (Next.js için)

Tüm endpoint'ler `Authorization: Bearer <NEXTJS_MASTER_TOKEN>` header'ı ister
(`api/v1/authentication.py: StaticBearerTokenAuthentication` — tek sabit token,
`constant_time_compare` ile karşılaştırılır; token yoksa/yanlışsa 401).

```
GET /api/v1/institutions/?company__code=AXA&city__plate_code=34&product_type__code=TSS&district=&institution_type__code=&search=&page=1&page_size=20
GET /api/v1/companies/
GET /api/v1/cities/
GET /api/v1/districts/?city=<id>
GET /api/v1/product-types/
GET /api/v1/institution-types/
```

### 6.1 Swagger / OpenAPI dokümantasyonu

`drf-spectacular` ile otomatik üretiliyor, kod değiştikçe kendiliğinden güncel kalır:

| URL | Ne işe yarar |
|---|---|
| `/api/docs/` | **Swagger UI** — interaktif, sağ üstteki "Authorize" butonuna `NEXTJS_MASTER_TOKEN`'ı girip endpoint'leri tarayıcıdan gerçekten çağırabilirsin ("Try it out") |
| `/api/redoc/` | **Redoc** — salt-okunur, daha sade/okunaklı statik dokümantasyon görünümü |
| `/api/schema/` | Ham OpenAPI 3 şeması (YAML) — Next.js tarafında TypeScript tip üretimi (`openapi-typescript` vb.) için kullanılabilir |

Next.js tarafında tip-güvenli client üretmek istersen:
```bash
npx openapi-typescript https://api.sigortafi.net/api/schema/ -o types/api.ts
```

---

## 7. Ortam değişkenleri (`.env`)

| Değişken | Açıklama |
|---|---|
| `DJANGO_SECRET_KEY` | Django secret key, prod'da mutlaka değiştirilmeli |
| `DEBUG` | `False` olmalı (prod) |
| `ALLOWED_HOSTS` | Virgülle ayrılmış domain listesi |
| `CSRF_TRUSTED_ORIGINS` | `https://` dahil tam origin listesi (Django 4+ zorunlu) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Postgres bağlantı bilgileri, ayrık değişkenler (production'da bunlar kullanılır) |
| `DATABASE_URL` | Alternatif tek-string format (`postgres://user:pass@host:port/dbname`) — sadece `DB_NAME` boşsa fallback olarak devreye girer, sadece basit şifreli yerel geliştirmede kullan |
| `NEXTJS_MASTER_TOKEN` | Next.js'in API'ye erişirken kullanacağı Bearer token |
| `TSS_INSTITUTION_LIST_PATH` vb. | tamamlayicisaglik.com endpoint path'leri, default'ları zaten doğru |
| `TSS_EXTRA_HEADERS` | Gerekirse ek HTTP header (JSON) — şu an boş `{}`, gerek yok |
| `TSS_REQUEST_DELAY_SECONDS` | Sayfalar arası nezaket bekletmesi (default 0.5sn) |

---

## 8. Yerel geliştirme (Windows, venv ile)

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
copy .env.example .env   # DATABASE_URL'i yerel Postgres'e göre düzenle
venv\Scripts\python manage.py migrate
venv\Scripts\python manage.py seed_reference_data
venv\Scripts\python manage.py sync_districts
venv\Scripts\python manage.py createsuperuser
venv\Scripts\python manage.py runserver
```

---

## 9. Docker + Production Deploy (Hestia)

Postgres **Hestia'da, host'un kendi üzerinde** çalışıyor (container değil). `docker-compose.yml`
sadece `web` servisini tanımlıyor ve `network_mode: host` kullanıyor — bu sayede container,
host'un `127.0.0.1`'ini doğrudan görür, Postgres'i dışarıya açmaya **gerek yok**.

### 9.1 Repoyu sunucuya çekmek

```bash
cd /home/<hestia-kullanici>/web/<domain>/public_html
git clone <repo-url> .
```

### 9.2 `.env` oluşturmak

```bash
cp .env.example .env
nano .env
```

```
DJANGO_SECRET_KEY=<python3 -c "import secrets; print(secrets.token_urlsafe(48))">
DEBUG=False
ALLOWED_HOSTS=domain.com,www.domain.com
CSRF_TRUSTED_ORIGINS=https://domain.com,https://www.domain.com
DB_NAME=<hestia_db_adi>
DB_USER=<hestia_db_user>
DB_PASSWORD=<hestia_db_sifre>
DB_HOST=127.0.0.1
DB_PORT=5432
NEXTJS_MASTER_TOKEN=<python3 -c "import secrets; print(secrets.token_urlsafe(48))">
```

`DB_PASSWORD`'ü **olduğu gibi, hiçbir encode işlemi yapmadan** yapıştır — Hestia'nın
ürettiği şifrede `/ # ? |` gibi karakterler olsa bile ayrık `DB_*` değişkenleri
kullanıldığı için URL parse sorunu yaşanmaz (tek-string `DATABASE_URL` formatında
bu tür karakterler port/host parse'ını kırıyordu, bu yüzden ayrık değişkenlere geçtik).

### 9.3 Build + ayağa kaldırma

```bash
docker compose up -d --build
docker compose logs -f web     # migrate/collectstatic/gunicorn loglarını izle
```

`entrypoint.sh` otomatik olarak: Postgres'i bekler → `migrate` → `collectstatic` →
gunicorn'u `0.0.0.0:8000`'de başlatır (host network sayesinde bu host'un 8000 portu demek).

### 9.4 Hestia'da reverse proxy (domain → gunicorn)

Hestia panelinde **Web → domain → Edit → Advanced/Proxy → "Additional Nginx Directives"**:

```nginx
location /static/ {
    alias /home/<hestia-kullanici>/web/<domain>/public_html/staticfiles/;
}

location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

Panelde bulunamazsa: `/home/<user>/conf/web/<domain>/nginx.<domain>.conf` dosyasını elle
düzenle, `nginx -t && systemctl reload nginx`.

### 9.5 SSL

Hestia → domain → **SSL Support → Let's Encrypt Support**. SSL Nginx seviyesinde
sonlanıyor; Django tarafı `SECURE_PROXY_SSL_HEADER` ile bunun farkında (`config/settings.py`).

### 9.6 Güvenlik

Hestia **Firewall**'dan 8000 portunu dışarıya **kapat** (sadece 80/443/22 açık kalsın) —
`network_mode: host` container'ı host ağına bağladığı için, firewall olmazsa biri
Nginx/SSL'i atlayıp gunicorn'a doğrudan gidebilir.

### 9.7 İlk kurulum (bir kere)

```bash
docker compose exec web python manage.py seed_reference_data
docker compose exec web python manage.py sync_districts
docker compose exec web python manage.py createsuperuser
```

### 9.8 Test

```
https://domain.com/admin/                 → giriş ekranı
https://domain.com/api/v1/companies/      → token'sız 401 dönmeli
```

### 9.9 Kod güncellemesi geldiğinde

```bash
cd /home/<user>/web/<domain>/public_html
git pull
docker compose up -d --build
```

Veri Hestia'daki Postgres'te kalıcı olduğu için kaybolmaz; migrate otomatik çalışır.

---

## 10. Komut referansı

| Komut | Ne yapar |
|---|---|
| `manage.py migrate` | Şema migrasyonlarını uygular (entrypoint'te otomatik) |
| `manage.py seed_reference_data` | 7 şirket + 81 il + 2 ürün tipi + 9 kurum tipini bilinen id'lerle yazar (idempotent) |
| `manage.py sync_districts [--delay 0.3]` | 81 il için gerçek ilçe listesini canlı çeker (970 ilçe, ~30sn) |
| `manage.py run_full_scrape [--company KOD] [--city PLAKA] [--district AD] [--product-type KOD] [--institution-type KOD]` | Parametrelere göre bir `ScrapeJob` oluşturup **senkron** (terminali bloklayarak) çalıştırır — CLI/cron için |
| `manage.py createsuperuser` | Admin kullanıcısı oluşturur |
| Dashboard "Run now" action | Aynı işi admin panelinden **arka planda** (thread) tetikler |

**Örnek — sadece İstanbul, tüm şirketler, tüm ürünler:**
```bash
docker compose exec web python manage.py run_full_scrape --city 34
```

**Örnek — tek şirket, tek il, tek ürün:**
```bash
docker compose exec web python manage.py run_full_scrape --company HDI --city 6 --product-type TSS
```

**Tüm Türkiye'yi tek seferde çekmek** (7 şirket × 2 ürün × 81 il — saatler sürer,
`REQUEST_DELAY_SECONDS` nezaket bekletmesi var):
```bash
docker compose exec web python manage.py run_full_scrape
```

---

## 11. Bilinen kısıtlar / açık noktalar

- **Adres/telefon/koordinat yok** — `search-hospital` bu alanları döndürmüyor, sadece
  isim + ilçe + kurum tipi + hangi "network"lerde olduğu bilgisi var.
- **`districtId` filtresi server-side garanti değil** — gözlemlenen parametre isimlendirme
  desenine göre gönderiliyor ama kesin çalıştığı doğrulanmadı; bu yüzden `district_name`
  üzerinden client-side'da da filtreleniyor (çift güvenceli).
- **Zamanlama yok** — Celery/cron eklenmedi (bilinçli tercih). Otomatik/periyodik çekim
  istenirse `run_full_scrape` zaten CLI'dan çalıştığı için VM'de bir `cron` satırıyla
  kod değişikliği gerekmeden eklenebilir.
- **Türkçe "İ/i" arama kısıtı** — DRF'nin serbest metin arama filtresi (`?search=`) Postgres'in
  standart `UPPER()` davranışı yüzünden "ist" ile "İstanbul"u eşleştiremiyor. Exact-match
  filtreleri (company/city/product_type kodu) bundan etkilenmiyor.
