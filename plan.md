şimdi biz bir sigorta şirketiyiz bizim iş yaptığımız sigorta şirketleri  axa, hdi, acıbadem, türkiye, anadolu, allinaz, mapfre

bunlardır ve sigorta türü ise Tammalayıcı Sağlık Sigortası ve Özel Sağlık Sigortası
bizim ihtiyacımız olan veri anlaşmalı kurumlar verisi 

bu sistemi en güzel hepsinin iç içe olduğu yapı  https://www.tamamlayicisaglik.com/ bu sistede mevcut birden fazla şirketi destekliyor parametrele daya bir sistem
amacımız fast api ile bir sistem kurup bizim ui sistemimizen gelen parametrele göre bu siste istek atıp verileri bizim ui gönderecek olan bir ara servis yazmak bizimm sistem nextjs biz buna bir endpoint vereceğiz master key vereceğiz berare ile fast api ye istek atacak tokenla koruma olacka 

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/axa-sigorta

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/hdi-sigorta

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/acibadem-sigorta

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/turkiye-sigorta

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/anadolu-sigorta

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/allianz-sigorta

https://www.tamamlayicisaglik.com/anlasmali-saglik-kurumlari/sonuclar/sigorta-sirketi/mapfre-sigorta

bunlar bize lazım olan şirketlerin endpointi
formlar mevcut her birinin sayfasında

https://www.tamamlayicisaglik.com/internal-api/company-list-results?page=1&limit=5&exceptCompanyId=3&cityId=34&productTypeId=2 

şeklide istek alabaliriz bu yazdıpım sigorta sayfalraı aynı yere bağlı company id değişiyor cityId plakaya göre zaten ürün tipleri var araştırılması gerkeen 

 "data": {
        "current_page": 1,
        "data": [
            {
                "id": 24,
                "name": "Generali",
                "svg_name": "logo-horizontal_02042024103127",
                "is_active": true,
                "show_on_filter": 1,
                "tss_active": true,
                "oss_active": 0,
                "ds_active": false,
                "order_num": 35,
                "old_id": 8,
                "emergency_number": null,
                "created_at": "2020-05-17T22:37:23.000000Z",
                "updated_at": "2025-09-10T11:25:23.000000Z",
                "deleted_at": null,
                "customer_service_number": "0850 555 55 55",
                "home_active": true,
                "cs_active": 0,
                "about_us": "<h2>Generali Sigorta Anla\u015fmal\u0131 Hastaneler A\u011f\u0131<\/h2>\r\n\r\n<p>Hastaneye gitmeden &ouml;nce tedaviniz i&ccedil;in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. Ana Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli&ccedil;enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda direkt hastaneye &ouml;denir.<\/p>\r\n\r\n<p>Sayfam\u0131zda sunulan t&uuml;m bilgi ve anla\u015fmal\u0131 kurum listeleri bilgilendirme ama&ccedil;l\u0131d\u0131r. S&ouml;z konusu i&ccedil;erikler sigorta \u015firketleri taraf\u0131ndan sa\u011flanan kamuya a&ccedil;\u0131k bilgilerden derlenmekte ve g&uuml;ncellenmektedir. Herhangi bir sa\u011fl\u0131k kurulu\u015funa ba\u015fvurmadan &ouml;nce, sigorta \u015firketinizin anla\u015fmas\u0131n\u0131n ge&ccedil;erlili\u011fini teyit etmenizi &ouml;neririz. Ya\u015fanabilecek aksakl\u0131klardan tamamlayicisaglik.com sorumlu de\u011fildir.<\/p>\r\n\r\n<h4>Generali Sigorta Tamamlay\u0131c\u0131 Sa\u011fl\u0131k Sigortas\u0131 Anla\u015fmal\u0131 Hastaneler<\/h4>\r\n\r\n<p>Generali Sigorta <a href=\"https:\/\/www.tamamlayicisaglik.com\/anlasmali-saglik-kurumlari\">anla\u015fmal\u0131 sa\u011fl\u0131k kurumlar\u0131<\/a>;&nbsp;Generali Sigorta ile <a href=\"https:\/\/www.tamamlayicisaglik.com\/tamamlayici-saglik-sigortasi\">tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131<\/a>na &ouml;zel anla\u015fmas\u0131 bulunan ve bu anla\u015fma &ccedil;er&ccedil;evesinde sa\u011fl\u0131k hizmeti sunan kurumlar\u0131 ifade eder. Anla\u015fmal\u0131 sa\u011fl\u0131k kurumlar\u0131nda yat\u0131\u015fl\u0131 veya yat\u0131\u015fs\u0131z tedavi hizmetinden do\u011fan masraflar, sigorta \u015firketi taraf\u0131ndan SGK kurallar\u0131 esas al\u0131narak hastaneye &ouml;denir. Generali Sigorta tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131n\u0131n ge&ccedil;erli oldu\u011fu hastanelerde ve SGK ile t&uuml;m bran\u015flarda anla\u015fmas\u0131 bulunan sa\u011fl\u0131k kurumlar\u0131nda poli&ccedil;enizi kullanabilirsiniz.&nbsp;<\/p>\r\n\r\n<p>Generali Sigorta tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131 anla\u015fmal\u0131 hastaneler; Geni\u015fletilmi\u015f network ve standart network olmak &uuml;zere 2 farkl\u0131 kurum listesinden olu\u015fur. Geni\u015fletilmi\u015f network en kapsaml\u0131 hastane a\u011f\u0131na sahipken standart network de baz\u0131 kurumlar yoktur. Poli&ccedil;e sat\u0131n almadan &ouml;nce sa\u011fl\u0131k hizmeti almak istedi\u011finiz kurumun hangi networkte yer ald\u0131\u011f\u0131n\u0131 incelemenizi tavsiye ederiz.<\/p>\r\n\r\n<p><a href=\"https:\/\/www.tamamlayicisaglik.com\/ozel-saglik-sigortasi\">&Ouml;zel Sa\u011fl\u0131k Sigortas\u0131<\/a> hakk\u0131nda detayl\u0131 bilgi i&ccedil;in t\u0131klay\u0131n\u0131z.<\/p>",
                "slug": "generali-sigorta",
                "active_on_hospitals": true,
                "website": "https:\/\/www.generali.com.tr\/",
                "network_description_tss": null,
                "network_description_ds": null,
                "network_description_oss": null,
                "last_crawler_ran_at": "2024-04-02T00:24:10.000000Z",
                "active_on_insurance_reminder": 1,
                "gss_active": 0,
                "offer_validity_days": 5,
                "renewal_offer_validity_days": 60,
                "rpa_included": 0,
                "yss_active": 0,
                "active_on_insurance_offer": true,
                "active_on_traffic_insurance_offer": true,
                "seo_schema_description": null,
                "seo_schema_article_body": null,
                "blog_active": 1,
                "faq_active": 1,
                "about_active": 1,
                "sss_active": 0,
                "pet_active": 0,
                "health_plan_network_description": "Generali Sigorta anla\u015fmal\u0131 hastaneler hakk\u0131nda bilgi mi ar\u0131yorsunuz? Generali Sigorta anla\u015fmal\u0131 hastaneleri listelemek i\u00e7in hemen t\u0131klay\u0131n!",
                "disambiguating_description": "Generali Sigorta anla\u015fmal\u0131 hastaneler hakk\u0131nda bilgi mi ar\u0131yorsunuz? Generali Sigorta anla\u015fmal\u0131 hastaneleri listelemek i\u00e7in hemen t\u0131klay\u0131n!",
                "health_plan_network_id_text": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. Ana Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda direkt hastaneye \u00f6denir.",
                "health_plan_network_tier": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. Ana Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda direkt hastaneye \u00f6denir.",
                "subject_of": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. Ana Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda direkt hastaneye \u00f6denir.",
                "crawled_hospitals_count": 162,
                "svg_url": "https:\/\/www.tamamlayicisaglik.com\/assets\/images\/company\/logo-horizontal_02042024103127.svg"
            },
            {
                "id": 32,
                "name": "T\u00fcrkiye",
                "svg_name": "turkiye",
                "is_active": true,
                "show_on_filter": 1,
                "tss_active": true,
                "oss_active": 1,
                "ds_active": true,
                "order_num": 4,
                "old_id": null,
                "emergency_number": null,
                "created_at": "2020-09-16T04:59:02.000000Z",
                "updated_at": "2026-06-26T06:30:23.000000Z",
                "deleted_at": null,
                "customer_service_number": "0 (850) 202 20 20",
                "home_active": true,
                "cs_active": 0,
                "about_us": "<h1>T&uuml;rkiye Sigorta Anla\u015fmal\u0131 Hastaneler ve Kurumlar<\/h1>\r\n\r\n<p>T&uuml;rkiye Sigorta A.\u015e&nbsp;<a href=\"https:\/\/www.tamamlayicisaglik.com\/anlasmali-saglik-kurumlari\">anla\u015fmal\u0131 sa\u011fl\u0131k kurumlar\u0131<\/a>; sigortal\u0131lar\u0131n SGK destekli olarak &ouml;zel hastane ve t\u0131p merkezlerinde belirli \u015fartlarla hizmet alabildi\u011fi sa\u011fl\u0131k a\u011f\u0131d\u0131r. T&uuml;rkiye Sigorta, &uuml;lke &ccedil;ap\u0131nda &ouml;zel hastane, t\u0131p merkezi, poliklinik ve eczanelerden olu\u015fan yakla\u015f\u0131k 5.500 anla\u015fmal\u0131 kurum zinciri ile olduk&ccedil;a b&uuml;y&uuml;k bir a\u011fa sahiptir.<\/p>\r\n\r\n<p>Bu kapsamda T&uuml;rkiye Sigorta poli&ccedil;esine sahip ki\u015filer, \u0130stanbul, Ankara ve \u0130zmir ba\u015fta olmak &uuml;zere anla\u015fmal\u0131 sa\u011fl\u0131k kurumlar\u0131nda provizyon onay\u0131 ile muayene ve tedavi hizmetlerinden yararlanabilir. T&uuml;rkiye sigorta anla\u015fmal\u0131 kurumlar listesi, poli&ccedil;e t&uuml;r&uuml;ne ve teminat kapsam\u0131na g&ouml;re de\u011fi\u015fiklik g&ouml;sterebilir.<\/p>\r\n\r\n<p>Sayfam\u0131zda sunulan t&uuml;m bilgi ve anla\u015fmal\u0131 kurum listeleri bilgilendirme ama&ccedil;l\u0131d\u0131r. S&ouml;z konusu i&ccedil;erikler sigorta \u015firketleri taraf\u0131ndan sa\u011flanan kamuya a&ccedil;\u0131k bilgilerden derlenmekte ve g&uuml;ncellenmektedir. Herhangi bir sa\u011fl\u0131k kurulu\u015funa ba\u015fvurmadan &ouml;nce, sigorta \u015firketinizin anla\u015fmas\u0131n\u0131n ge&ccedil;erlili\u011fini teyit etmenizi &ouml;neririz. Ya\u015fanabilecek aksakl\u0131klardan tamamlayicisaglik.com sorumlu de\u011fildir.<\/p>\r\n\r\n<h2>T&uuml;rkiye Sigorta Anla\u015fmal\u0131 Kurumlar\u0131 Bulun<\/h2>\r\n\r\n<p>T&uuml;rkiye Sigorta anla\u015fmal\u0131 kurumlar\u0131 bulmak i&ccedil;in &ouml;ncelikle sahip oldu\u011funuz poli&ccedil;e t&uuml;r&uuml;n&uuml; (tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131 veya &ouml;zel sa\u011fl\u0131k sigortas\u0131) ve bulundu\u011funuz konumu belirlemeniz gerekir. &Ccedil;&uuml;nk&uuml; T&uuml;rkiye Sigorta&#39;n\u0131n kapsad\u0131\u011f\u0131 hastaneler, t\u0131p merkezi ve di\u011fer sa\u011fl\u0131k kurumlar\u0131 &uuml;r&uuml;n kapsam\u0131na ve \u015fehre g&ouml;re farkl\u0131l\u0131k g&ouml;sterebilir.<\/p>\r\n\r\n<p>T&uuml;rkiye Sigorta&#39;n\u0131n ge&ccedil;ti\u011fi &ouml;zel hastaneler hakk\u0131nda bilgi i&ccedil;in kullan\u0131c\u0131lar, T&uuml;rkiye Sigorta&rsquo;n\u0131n resmi web sitesi veya mobil uygulamas\u0131 &uuml;zerinden il (\u0130stanbul, Ankara, \u0130zmir gibi), il&ccedil;e ve bran\u015f se&ccedil;imi yaparak kendilerine en yak\u0131n anla\u015fmal\u0131 sa\u011fl\u0131k kurumlar\u0131n\u0131 kolayca listeleyebilir. Ayr\u0131ca provizyon s&uuml;re&ccedil;lerinin sorunsuz ilerlemesi i&ccedil;in tercih edilen kurumun poli&ccedil;eye dahil olup olmad\u0131\u011f\u0131 kontrol edilmelidir.<\/p>\r\n\r\n<p>Arama s\u0131ras\u0131nda hastane, t\u0131p merkezi, laboratuvar veya eczane gibi kurum t&uuml;rlerine g&ouml;re filtreleme yap\u0131labilir. B&ouml;ylece ihtiya&ccedil; duyulan sa\u011fl\u0131k hizmetine en uygun T&uuml;rkiye Sigorta anla\u015fmal\u0131 kurumlara h\u0131zl\u0131 ve do\u011fru \u015fekilde ula\u015fmak m&uuml;mk&uuml;n olur.<\/p>\r\n\r\n<h2>T&uuml;rkiye Sigorta Anla\u015fmal\u0131 Hastaneler A\u011f\u0131<\/h2>\r\n\r\n<p>T&uuml;rkiye Sigorta&rsquo;n\u0131n anla\u015fmal\u0131 sa\u011fl\u0131k kurum a\u011f\u0131; hastane, t\u0131p merkezi, doktor, laboratuvar ve di\u011fer sa\u011fl\u0131k kurulu\u015flar\u0131ndan olu\u015fur. Bu geni\u015f yap\u0131 i&ccedil;erisinde yer alan anla\u015fmal\u0131 hastane, t\u0131p merkezi ve laboratuvar se&ccedil;enekleri; poli&ccedil;e t&uuml;r&uuml;ne, teminat detaylar\u0131na ve SGK ile olan entegrasyona g&ouml;re farkl\u0131l\u0131k g&ouml;sterebilir. Bu nedenle sa\u011fl\u0131k hizmeti almadan &ouml;nce ilgili kurumun aktif anla\u015fmas\u0131n\u0131n bulunup bulunmad\u0131\u011f\u0131 kontrol edilmeli ve provizyon s&uuml;reci i&ccedil;in &ouml;n onay al\u0131nmal\u0131d\u0131r.<\/p>\r\n\r\n<p>T&uuml;rkiye sigorta anla\u015fmal\u0131 hastaneler a\u011f\u0131 i&ccedil;erisinde sunulan hizmetler; ayakta tedavi ve yatarak tedavi teminatlar\u0131na g&ouml;re \u015fekillenir. <a href=\"https:\/\/www.tamamlayicisaglik.com\/tamamlayici-saglik-sigortasi\">Tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131<\/a> (TSS), SGK ile anla\u015fmal\u0131 kurumlarda ge&ccedil;erli olup fark &uuml;cretlerini minimize ederken; <a href=\"https:\/\/www.tamamlayicisaglik.com\/ozel-saglik-sigortasi\">&ouml;zel sa\u011fl\u0131k sa\u011fl\u0131k sigortas\u0131<\/a>&nbsp; (&Ouml;SS) daha geni\u015f bir doktor a\u011f\u0131 ve kurum se&ccedil;ene\u011fi sunarak SGK ba\u011f\u0131 olmadan da hizmet alabilme imk&acirc;n\u0131 sa\u011flar.<\/p>\r\n\r\n<p>Kullan\u0131c\u0131lar, ihtiya&ccedil;lar\u0131na uygun sa\u011fl\u0131k kurulu\u015funu bulabilmek i&ccedil;in \u015fehir-il&ccedil;e filtreleme yaparak kendilerine en yak\u0131n anla\u015fmal\u0131 hastane veya t\u0131p merkezi se&ccedil;eneklerini listeleyebilir. Ayr\u0131ca poli&ccedil;e limiti, teminat kapsam\u0131 ve provizyon onay\u0131 gibi detaylar\u0131n &ouml;nceden kontrol edilmesi, sa\u011fl\u0131k hizmetlerinden sorunsuz yararlanabilmek a&ccedil;\u0131s\u0131ndan olduk&ccedil;a &ouml;nemlidir.<\/p>\r\n\r\n<h3>T&uuml;rkiye Sigorta Tamamlay\u0131c\u0131 Sa\u011fl\u0131k Sigortas\u0131 Anla\u015fmal\u0131 Hastaneler<\/h3>\r\n\r\n<p><a href=\"https:\/\/tamamlayicisaglik.com\/sigorta-sirketleri\/turkiye-sigorta-tamamlayici-saglik-sigortasi\">T&uuml;rkiye Sigorta tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131<\/a> Anla\u015fmal\u0131 Hastaneler, TSS poli&ccedil;esi bulunan sigortal\u0131lar\u0131n SGK ile anla\u015fmal\u0131 &ouml;zel hastane, t\u0131p merkezi ve laboratuvarlarda ek &uuml;cret &ouml;demeden ya da minimum farkla sa\u011fl\u0131k hizmeti alabildi\u011fi kurumlard\u0131r. Bu sistemde hem SGK hem de T&uuml;rkiye Sigorta ile &ccedil;ift anla\u015fmas\u0131 bulunan sa\u011fl\u0131k kurulu\u015flar\u0131 tercih edilir. &Ouml;rne\u011fin; b&uuml;y&uuml;k \u015fehirlerde yer alan anla\u015fmal\u0131 &ouml;zel hastane ve yayg\u0131n t\u0131p merkezi zincirleri bu kapsama dahil olabilir. Sigortal\u0131lar, provizyon onay\u0131 alarak ayakta tedavi ve yatarak tedavi hizmetlerinden poli&ccedil;e limitleri dahilinde yararlanabilir.<\/p>\r\n\r\n<p>T&uuml;rkiye Sigorta TSS anla\u015fmal\u0131 hastaneler kapsam\u0131nda sunulan hizmetler genellikle Alt\u0131n network gibi geni\u015f anla\u015fmal\u0131 kurum a\u011f\u0131 &uuml;zerinden sa\u011flan\u0131r ve bu a\u011f; doktor, t\u0131p merkezi ve laboratuvar se&ccedil;eneklerini i&ccedil;erir. Ayakta tedavi teminat\u0131; muayene, tetkik ve kontrol s&uuml;re&ccedil;lerini kapsarken, yatarak tedavi teminat\u0131 daha kapsaml\u0131 hastane hizmetlerini i&ccedil;erir. Ancak her sa\u011fl\u0131k kurumunun her poli&ccedil;ede ge&ccedil;erli olmayabilece\u011fi unutulmamal\u0131, hizmet &ouml;ncesinde provizyon al\u0131narak ilgili kurumun aktif anla\u015fmas\u0131 teyit edilmelidir.<\/p>\r\n\r\n<p>T&uuml;rkiye Sigorta Tamamlay\u0131c\u0131 Sa\u011fl\u0131k Sigortas\u0131 kapsam\u0131nda sunulan sa\u011fl\u0131k hizmetleri, SUT (Sa\u011fl\u0131k Uygulama Tebli\u011fi) h&uuml;k&uuml;mleri do\u011frultusunda SGK&#39;n\u0131n kar\u015f\u0131lad\u0131\u011f\u0131 i\u015flemler esas al\u0131narak de\u011ferlendirilir. Poli&ccedil;e kapsam\u0131, teminat limitleri ve provizyon s&uuml;re&ccedil;leri SBM (Sigorta Bilgi ve G&ouml;zetim Merkezi) kay\u0131tlar\u0131 ile uyumlu \u015fekilde y&uuml;r&uuml;t&uuml;l&uuml;rken, sigortac\u0131l\u0131k faaliyetleri SEDDK (Sigortac\u0131l\u0131k ve &Ouml;zel Emeklilik D&uuml;zenleme ve Denetleme Kurumu) taraf\u0131ndan belirlenen mevzuata uygun olarak ger&ccedil;ekle\u015ftirilir.<\/p>\r\n\r\n<p>T&uuml;rkiye Sigorta tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131 anla\u015fmal\u0131 hastaneler ve T&uuml;rkiye Sigorta &ouml;zel sa\u011fl\u0131k sigortas\u0131 anla\u015fmal\u0131 hastaneler&nbsp;SB (Sa\u011fl\u0131k Bakanl\u0131\u011f\u0131) taraf\u0131ndan ruhsatland\u0131r\u0131lm\u0131\u015f kurumlar aras\u0131ndan se&ccedil;ilir. Ayr\u0131ca sekt&ouml;r genelinde uygulanan standartlar ve uygulama esaslar\u0131 TSB (T&uuml;rkiye Sigorta Birli\u011fi) taraf\u0131ndan yay\u0131mlanan bilgiler do\u011frultusunda desteklenir.<\/p>\r\n\r\n<h3>T&uuml;rkiye Sigorta &Ouml;zel Sa\u011fl\u0131k Sigortas\u0131 Anla\u015fmal\u0131 Hastaneler<\/h3>\r\n\r\n<p>T&uuml;rkiye sigorta &ouml;zel sa\u011fl\u0131k sigortas\u0131 anla\u015fmal\u0131 hastaneler; sigortal\u0131lar\u0131n geni\u015f bir hastane a\u011f\u0131na eri\u015fim sa\u011flayabildi\u011fi, SGK&rsquo;ya ba\u011fl\u0131 olmadan hizmet alabildi\u011fi ve y&uuml;ksek standartl\u0131 sa\u011fl\u0131k kurumlar\u0131n\u0131 kapsayan sistemdir. Bu kapsamda sunulan avantajlar aras\u0131nda geni\u015f doktor a\u011f\u0131, kapsaml\u0131 ayakta tedavi ve yatarak tedavi teminatlar\u0131 ile esnek kullan\u0131m yer al\u0131r. T&uuml;rkiye Sigorta &Ouml;SS anla\u015fmal\u0131 hastaneler ile sigortal\u0131lar; anla\u015fmal\u0131 &ouml;zel hastane ve &uuml;st segment sa\u011fl\u0131k kurulu\u015flar\u0131nda do\u011frudan provizyon ile hizmet alabilir, anla\u015fma d\u0131\u015f\u0131 kurumlarda ise geri &ouml;deme y&ouml;ntemiyle masraflar\u0131n\u0131 poli&ccedil;e limitleri dahilinde tahsil edebilir.<\/p>\r\n\r\n<p>&Ouml;SS kapsam\u0131nda network ayr\u0131m\u0131 &ouml;nemli bir kriterdir. Daha geni\u015f network se&ccedil;enekleri, daha fazla hastane ve premium sa\u011fl\u0131k kurulu\u015funa eri\u015fim anlam\u0131na gelir. &Ouml;rne\u011fin Amerikan Hastanesi, Ac\u0131badem Hastaneleri ve Florence Nightingale Hastaneleri gibi &uuml;st segment kurumlar genellikle &uuml;st network planlar\u0131nda yer al\u0131r. Anla\u015fmal\u0131 hastanelerde provizyon ile h\u0131zl\u0131 hizmet al\u0131n\u0131rken, anla\u015fmas\u0131z hastanelerde sigortal\u0131 &ouml;demeyi yapar ve sonras\u0131nda geri &ouml;deme s&uuml;reci ba\u015flat\u0131l\u0131r.&nbsp;<a href=\"https:\/\/tamamlayicisaglik.com\/sigorta-sirketleri\/turkiye-sigorta-ozel-saglik-sigortasi\">T&uuml;rkiye Sigorta &Ouml;zel Sa\u011fl\u0131k Sigortas\u0131<\/a>, A ve B olmak &uuml;zere 2 networkten olu\u015fur. A network Amerikan Hastanesi&#39;nin de dahil oldu\u011fu en geni\u015f anla\u015fmal\u0131 sa\u011fl\u0131k kurumu listesidir. B network kapsam\u0131nda ise&nbsp;Amerikan Hastanesi hari&ccedil; tutulmu\u015ftur.&nbsp;<\/p>\r\n\r\n<h3>T&uuml;rkiye Sigorta &Ouml;zel Sa\u011fl\u0131k Sigortas\u0131 Do\u011fum Teminat\u0131 Anla\u015fmal\u0131 Hastaneler<\/h3>\r\n\r\n<p>T&uuml;rkiye sigorta do\u011fum teminatl\u0131 anla\u015fmal\u0131 hastaneler, &Ouml;zel Sa\u011fl\u0131k Sigortas\u0131 kapsam\u0131nda do\u011fum teminat\u0131 bulunan sigortal\u0131lar\u0131n; hamilelik s&uuml;recinden do\u011fuma kadar t&uuml;m sa\u011fl\u0131k hizmetlerini kar\u015f\u0131layabildi\u011fi anla\u015fmal\u0131 sa\u011fl\u0131k kurumlar\u0131n\u0131 ifade eder. T&uuml;rkiye sigorta do\u011fum sigortas\u0131 anla\u015fmal\u0131 hastaneler i&ccedil;erisinde; Ac\u0131badem Hastaneleri gibi geli\u015fmi\u015f altyap\u0131ya sahip &ouml;zel hastaneler, kad\u0131n do\u011fum bran\u015f\u0131nda uzman doktor kadrosu ve kapsaml\u0131 gebelik takibi hizmetleri ile &ouml;ne &ccedil;\u0131kar. Bu hastanelerde gebelik s&uuml;recine ait rutin kontroller, do\u011fum ve hastane yat\u0131\u015f i\u015flemleri poli&ccedil;e kapsam\u0131na g&ouml;re kar\u015f\u0131lan\u0131r.<\/p>\r\n\r\n<p>Do\u011fum teminat\u0131 planlar\u0131nda limitli ve limitsiz se&ccedil;enekler bulunur. Limitli planlarda do\u011fum ve gebelik giderleri belirli bir poli&ccedil;e limiti ile s\u0131n\u0131rland\u0131r\u0131l\u0131rken, limitsiz planlarda daha geni\u015f kapsam sunulur.<\/p>\r\n\r\n<p>Sigorta kapsam\u0131nda do\u011fum teminat\u0131ndan yararlanabilmek i&ccedil;in genellikle belirli bir bekleme s&uuml;resi uygulan\u0131r (&ccedil;o\u011funlukla 9-12 ay). Bu nedenle poli&ccedil;enin hamile kalmadan &ouml;nce ba\u015flat\u0131lmas\u0131 gerekir. Hizmet al\u0131nmadan &ouml;nce hastane ile ileti\u015fime ge&ccedil;ilerek provizyon s&uuml;reci ba\u015flat\u0131lmal\u0131 ve do\u011fum teminat\u0131n\u0131n aktif olup olmad\u0131\u011f\u0131 teyit edilmelidir. B&ouml;ylece hem gebelik takibi hem de do\u011fum s&uuml;reci boyunca sa\u011fl\u0131k hizmetlerinden sorunsuz \u015fekilde faydalan\u0131labilir.&nbsp;<a href=\"https:\/\/www.tamamlayicisaglik.com\/dogum-sigortasi\">Do\u011fum Sigortas\u0131<\/a>&nbsp;sayfam\u0131z\u0131 da incelemenizi tavsiye ederiz.<\/p>\r\n\r\n<h3>T&uuml;rkiye Sigorta Anla\u015fmal\u0131 Eczaneler<\/h3>\r\n\r\n<p>T&uuml;rkiye Sigorta anla\u015fmal\u0131 eczaneler, sigortal\u0131lar\u0131n poli&ccedil;e kapsam\u0131ndaki ila&ccedil; ve medikal &uuml;r&uuml;n ihtiya&ccedil;lar\u0131n\u0131 belirli \u015fartlar dahilinde kar\u015f\u0131layabildi\u011fi hizmet noktalar\u0131d\u0131r. Bu eczanelerde i\u015flem yap\u0131labilmesi i&ccedil;in re&ccedil;etenin SGK ile uyumlu olmas\u0131 ve poli&ccedil;eye uygun teminatlar\u0131n bulunmas\u0131 gerekir. Provizyon s&uuml;reci sonras\u0131nda, ila&ccedil; bedelleri poli&ccedil;e kapsam\u0131na g&ouml;re kar\u015f\u0131lan\u0131r veya katk\u0131 pay\u0131 ile temin edilir.<\/p>\r\n\r\n<p>Anla\u015fmal\u0131 eczaneler a\u011f\u0131; \u015fehir, il&ccedil;e ve poli&ccedil;e t&uuml;r&uuml;ne g&ouml;re de\u011fi\u015fiklik g&ouml;sterebilir. Bu nedenle ila&ccedil; temini &ouml;ncesinde ilgili eczanenin T&uuml;rkiye Sigorta ile aktif anla\u015fmas\u0131n\u0131n olup olmad\u0131\u011f\u0131 kontrol edilmelidir. &Ouml;zellikle tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131 (TSS) kapsam\u0131nda SGK entegrasyonu &ouml;nemli bir rol oynar ve i\u015flemler bu do\u011frultuda ilerler.<\/p>\r\n\r\n<h3>T&uuml;rkiye Sigorta Anla\u015fmal\u0131 Di\u015f Hastaneleri<\/h3>\r\n\r\n<p>T&uuml;rkiye Sigorta anla\u015fmal\u0131 di\u015f hastaneleri, sigortal\u0131lar\u0131n a\u011f\u0131z ve di\u015f sa\u011fl\u0131\u011f\u0131 hizmetlerinden poli&ccedil;e teminatlar\u0131 kapsam\u0131nda yararlanabildi\u011fi sa\u011fl\u0131k kurumlar\u0131n\u0131 kapsar. Bu kurumlar; di\u015f hastaneleri, di\u015f klinikleri ve baz\u0131 t\u0131p merkezlerinin di\u015f b&ouml;l&uuml;mlerinden olu\u015fur.<\/p>\r\n\r\n<p>Di\u015f teminat\u0131 genellikle ek paket olarak sunulur ve her poli&ccedil;ede standart olarak bulunmayabilir. Kapsam dahilinde muayene, di\u015f ta\u015f\u0131 temizli\u011fi, r&ouml;ntgen ve baz\u0131 temel tedaviler kar\u015f\u0131lanabilirken; ileri seviye i\u015flemler (implant, ortodonti vb.) &ccedil;o\u011funlukla ek teminat gerektirir. Hizmet al\u0131nmadan &ouml;nce provizyon al\u0131nmas\u0131 ve se&ccedil;ilen di\u015f hastanesinin poli&ccedil;e kapsam\u0131nda yer ald\u0131\u011f\u0131n\u0131n teyit edilmesi &ouml;nemlidir.<br \/>\r\n&nbsp;<\/p>",
                "slug": "turkiye-sigorta",
                "active_on_hospitals": true,
                "website": "https:\/\/turkiyesigorta.com.tr\/",
                "network_description_tss": "<p>T&uuml;rkiye Sigorta taraf\u0131ndan belirlenmi\u015f kurumlarda tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortan\u0131z sayesinde y&uuml;ksek primler &ouml;demeden standard\u0131 y&uuml;ksek sa\u011fl\u0131k hizmeti alabilirsiniz. Hizmet almak istedi\u011finiz &ouml;zel hastanenin ve doktorun hem SGK hem de T&uuml;rkiye Sigorta ile s&ouml;zle\u015fmeli olmas\u0131 yeterlidir.<\/p>\r\n\r\n<p>T&uuml;rkiye Sigorta tamamlay\u0131c\u0131 sa\u011fl\u0131k sigortas\u0131 anla\u015fmal\u0131 hastaneleri Alt\u0131n&nbsp;network ve G&uuml;m&uuml;\u015f&nbsp;network olmak &uuml;zere 2&rsquo;ye ayr\u0131l\u0131r. T&uuml;rkiye&nbsp;Sigorta&#39;n\u0131n hangi hastanelerde ge&ccedil;erli oldu\u011funu sayfam\u0131zda bulunan g&uuml;ncel kurum listesinden inceleyebilirsiniz.<\/p>",
                "network_description_ds": null,
                "network_description_oss": null,
                "last_crawler_ran_at": "2024-12-25T08:00:26.000000Z",
                "active_on_insurance_reminder": 1,
                "gss_active": 1,
                "offer_validity_days": 15,
                "renewal_offer_validity_days": 60,
                "rpa_included": 1,
                "yss_active": 1,
                "active_on_insurance_offer": true,
                "active_on_traffic_insurance_offer": true,
                "seo_schema_description": null,
                "seo_schema_article_body": null,
                "blog_active": 1,
                "faq_active": 1,
                "about_active": 1,
                "sss_active": 0,
                "pet_active": 0,
                "health_plan_network_description": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. T\u00fcrkiye Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda do\u011frudan hastaneye \u00f6denir.",
                "disambiguating_description": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. T\u00fcrkiye Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda do\u011frudan hastaneye \u00f6denir.",
                "health_plan_network_id_text": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. T\u00fcrkiye Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda do\u011frudan hastaneye \u00f6denir.",
                "health_plan_network_tier": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. T\u00fcrkiye Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda do\u011frudan hastaneye \u00f6denir.",
                "subject_of": "Hastaneye gitmeden \u00f6nce tedaviniz i\u00e7in tercih edece\u011finiz hastane, t\u0131p merkezi, doktor veya di\u011fer sa\u011fl\u0131k kurumlar\u0131n\u0131n sigorta \u015firketiniz ile anla\u015fmal\u0131 olup olmad\u0131\u011f\u0131n\u0131 kontrol etmeniz gerekir. T\u00fcrkiye Sigorta ile anla\u015fmal\u0131 bir sa\u011fl\u0131k kurumuna gitti\u011finizde tedavi masraflar\u0131n\u0131z poli\u00e7enizde yazan teminat kapsam\u0131 ve limitleri do\u011frultusunda do\u011frudan hastaneye \u00f6denir.",
                "crawled_hospitals_count": 6,
                "svg_url": "https:\/\/www.tamamlayicisaglik.com\/assets\/images\/company\/turkiye.svg"
            }
        ,
        "first_page_url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=1",
        "from": 1,
        "last_page": 4,
        "last_page_url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=4",
        "links": [
            {
                "url": null,
                "label": "&laquo; \u00d6nceki",
                "active": false
            },
            {
                "url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=1",
                "label": "1",
                "active": true
            },
            {
                "url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=2",
                "label": "2",
                "active": false
            },
            {
                "url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=3",
                "label": "3",
                "active": false
            },
            {
                "url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=4",
                "label": "4",
                "active": false
            },
            {
                "url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=2",
                "label": "Sonraki &raquo;",
                "active": false
            }
        ],
        "next_page_url": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results?page=2",
        "path": "https:\/\/www.tamamlayicisaglik.com\/internal-api\/company-list-results",
        "per_page": "5",
        "prev_page_url": null,
        "to": 5,
        "total": 17
    }
} şeklinde mesela örnek olarak bu sistemi kurmalıyız benim öğrenip sana vermem gerkeen bilgiler vardır elbette bunlar nelerdir bana bunları söyle sana o bilgilier elde edeyim ve sende bu scraperı tasarala