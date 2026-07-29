from django.core.management.base import BaseCommand
from django.db import transaction

from companies.models import InsuranceCompany, Network, PolicyApplication
from products.models import ProductType


# 1. Şirketler Listesi
INSURANCE_COMPANIES = [
    {"code": "AXA", "name": "AXA Sigorta", "slug": "axa-sigorta"},
    {"code": "HDI", "name": "HDI Sigorta", "slug": "hdi-sigorta"},
    {"code": "ACIBADEM", "name": "Acıbadem Sigorta", "slug": "acibadem-sigorta"},
    {"code": "TURKIYE", "name": "Türkiye Sigorta", "slug": "turkiye-sigorta"},
    {"code": "ANADOLU", "name": "Anadolu Sigorta", "slug": "anadolu-sigorta"},
    {"code": "ALLIANZ", "name": "Allianz Sigorta", "slug": "allianz-sigorta"},
    {"code": "MAPFRE", "name": "Mapfre Sigorta", "slug": "mapfre-sigorta"},
]

# 2. Networkler Listesi
NETWORKS = [
    # AXA - Tamamlayıcı Sağlık Sigortası (TSS) Networkleri
    {"company_code": "AXA", "product_type_code": "TSS", "name": "Sağlığım Tamam Sigortası", "external_id": 17},
    {"company_code": "AXA", "product_type_code": "TSS", "name": "AXA Sağlığım Tamam Tutumlu Sigortası", "external_id": 24},
    {"company_code": "AXA", "product_type_code": "TSS", "name": "Grup Sağlığım Tamam Sigortası", "external_id": 81},

    # AXA - Özel Sağlık Sigortası (ÖSS) Networkleri
    {"company_code": "AXA", "product_type_code": "OSS", "name": "Network 1", "external_id": 34},
    {"company_code": "AXA", "product_type_code": "OSS", "name": "Network 2", "external_id": 38},
    {"company_code": "AXA", "product_type_code": "OSS", "name": "Network 3", "external_id": 44},

    # Allianz - Tamamlayıcı Sağlık Sigortası (STSS) Networkleri
    {"company_code": "ALLIANZ", "product_type_code": "TSS", "name": "Turkuaz Network", "external_id": 44},
    {"company_code": "ALLIANZ", "product_type_code": "TSS", "name": "Turuncu Network", "external_id": 19},
    {"company_code": "ALLIANZ", "product_type_code": "TSS", "name": "Kırmızı Network", "external_id": 55},

    # Allianz - Modüler Sağlık Sigortası (MDSG / bizde Özel Sağlık - OSS) Networkleri
    {"company_code": "ALLIANZ", "product_type_code": "OSS", "name": "Mavi Network", "external_id": 18},
    {"company_code": "ALLIANZ", "product_type_code": "OSS", "name": "Yeşil Network", "external_id": 17},
    {"company_code": "ALLIANZ", "product_type_code": "OSS", "name": "Sarı Network", "external_id": 16},
    {"company_code": "ALLIANZ", "product_type_code": "OSS", "name": "Beyaz Network", "external_id": 15},

    # Anadolu - Tamamlayıcı Sağlık Sigortası (TSS) Networkleri
    # external_id burada Anadolu'nun networkCodes payload'ındaki metinsel kod (string)
    {"company_code": "ANADOLU", "product_type_code": "TSS", "name": "Tamamlayıcı Network", "external_id": "TSS_Tamamlayıcı"},
    {"company_code": "ANADOLU", "product_type_code": "TSS", "name": "Tamamlayıcı Eko Network", "external_id": "TSS_Tamamlayıcı_Eko"},

    # Anadolu - Özel Sağlık Sigortası (ÖSS) Networkleri
    {"company_code": "ANADOLU", "product_type_code": "OSS", "name": "Geniş Network", "external_id": "AHN"},
    {"company_code": "ANADOLU", "product_type_code": "OSS", "name": "Tüm Network", "external_id": "S"},
    {"company_code": "ANADOLU", "product_type_code": "OSS", "name": "Eko Network", "external_id": "E"},
    {"company_code": "ANADOLU", "product_type_code": "OSS", "name": "VKV Network", "external_id": "VKV"},

    # Mapfre - Özel Sağlık Sigortası (OSS) Networkleri
    {"company_code": "MAPFRE", "product_type_code": "OSS", "name": "A Network", "external_id": "65"},
    {"company_code": "MAPFRE", "product_type_code": "OSS", "name": "B Network", "external_id": "68"},
    {"company_code": "MAPFRE", "product_type_code": "OSS", "name": "C Network", "external_id": "72"},
    {"company_code": "MAPFRE", "product_type_code": "OSS", "name": "B1 Network", "external_id": "114"},

    # Mapfre - Tamamlayıcı Sağlık Sigortası (TSS) Networkleri
    {"company_code": "MAPFRE", "product_type_code": "TSS", "name": "TSS Eko Network", "external_id": "82"},
    {"company_code": "MAPFRE", "product_type_code": "TSS", "name": "TSS Katılımlı Network", "external_id": "107"},
    {"company_code": "MAPFRE", "product_type_code": "TSS", "name": "TSS Standart Network", "external_id": "73"},

    # HDI - Özel Sağlık Sigortası (ÖSS) Networkleri
    {"company_code": "HDI", "product_type_code": "OSS", "name": "HDI SÜPER-TEMEL-AKILLI SAĞLIK", "external_id": "366"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "HDI PLATINIUM-GOLD-SILVER SAĞLIK", "external_id": "369"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "HDI PROMEDICO", "external_id": "373"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Size Özel Doğum", "external_id": "383"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Size Özel Seçimli Teminat ve Acil Sağlık", "external_id": "384"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Size Özel Sağlık A1", "external_id": "385"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Size Özel Sağlık A2", "external_id": "397"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Size Özel Sağlık A3", "external_id": "400"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Size Özel Sağlık A4", "external_id": "401"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "Yabancılara Özel Sağlık A6", "external_id": "403"},
    # HDI - Tamamlayıcı Sağlık Sigortası (TSS) Networkleri
    {"company_code": "HDI", "product_type_code": "TSS", "name": "Size Özel Tamamlayıcı Sağlık", "external_id": "405"},
    # HDI - Hibrit Ürün (538): Hem TSS hem ÖSS kapsamında — her iki network'e eklenir
    {"company_code": "HDI", "product_type_code": "TSS", "name": "HDI SİZE ÖZEL 2Sİ 1 ARADA SAĞLIK (TSS)", "external_id": "538"},
    {"company_code": "HDI", "product_type_code": "OSS", "name": "HDI SİZE ÖZEL 2Sİ 1 ARADA SAĞLIK (ÖSS)", "external_id": "538"},
]

# 3. Poliçe Uygulamaları (Policy Applications) Listesi
POLICY_AXA_APPLICATIONS = [
    # --- AXA TSS Poliçe Uygulamaları (network'ün kendisi doğrudan poliçe uygulamasıdır, alt kırılım yok) ---
    {
        "company_code": "AXA",
        "product_type_code": "TSS",
        "network_name": "Sağlığım Tamam Sigortası",
        "name": "Sağlığım Tamam Sigortası",
        "code": "AXA_TSS_SAGLIGIM_TAMAM",
        "service_id": "17",
    },
    {
        "company_code": "AXA",
        "product_type_code": "TSS",
        "network_name": "AXA Sağlığım Tamam Tutumlu Sigortası",
        "name": "AXA Sağlığım Tamam Tutumlu Sigortası",
        "code": "AXA_TSS_TUTUMLU",
        "service_id": "24",
    },
    {
        "company_code": "AXA",
        "product_type_code": "TSS",
        "network_name": "Grup Sağlığım Tamam Sigortası",
        "name": "Grup Sağlığım Tamam Sigortası",
        "code": "AXA_TSS_GRUP",
        "service_id": "81",
    },

    # --- AXA ÖSS Poliçe Uygulamaları ---
    # Network 1
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "1. Derece Yakınlara İndirimli Kurumlar",
        "code": "AXA_OSS_N1_YAKINLARA_INDIRIMLI",
        "service_id": "83",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "Kontrol Mamografi + USG",
        "code": "AXA_OSS_N1_MAMOGRAFI_USG",
        "service_id": "35",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "Kontrol Mamografi / Kontrol PSA",
        "code": "AXA_OSS_N1_MAMOGRAFI_PSA",
        "service_id": "36",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "Kontrol Kemik Yoğunluğu",
        "code": "AXA_OSS_N1_KEMIK_YOGUNLUGU",
        "service_id": "37",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "Ayakta Tedavi %100",
        "code": "AXA_OSS_N1_AYAKTA_TEDAVI",
        "service_id": "33",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "CHECK UP",
        "code": "AXA_OSS_N1_CHECK_UP",
        "service_id": "56",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 1",
        "name": "VIP CHECK UP",
        "code": "AXA_OSS_N1_VIP_CHECK_UP",
        "service_id": "60",
    },

    # Network 2
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 2",
        "name": "1. Derece Yakınlara İndirimli Kurumlar",
        "code": "AXA_OSS_N2_YAKINLARA_INDIRIMLI",
        "service_id": "83",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 2",
        "name": "Kontrol Mamografi + USG",
        "code": "AXA_OSS_N2_MAMOGRAFI_USG",
        "service_id": "39",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 2",
        "name": "Kontrol Mamografi / Kontrol PSA",
        "code": "AXA_OSS_N2_MAMOGRAFI_PSA",
        "service_id": "40",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 2",
        "name": "Kontrol Kemik Yoğunluğu",
        "code": "AXA_OSS_N2_KEMIK_YOGUNLUGU",
        "service_id": "41",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 2",
        "name": "CHECK UP",
        "code": "AXA_OSS_N2_CHECK_UP",
        "service_id": "57",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 2",
        "name": "VIP CHECK UP",
        "code": "AXA_OSS_N2_VIP_CHECK_UP",
        "service_id": "61",
    },

    # Network 3
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 3",
        "name": "1. Derece Yakınlara İndirimli Kurumlar",
        "code": "AXA_OSS_N3_YAKINLARA_INDIRIMLI",
        "service_id": "83",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 3",
        "name": "Kontrol Mamografi + USG",
        "code": "AXA_OSS_N3_MAMOGRAFI_USG",
        "service_id": "45",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 3",
        "name": "Kontrol Mamografi / Kontrol PSA",
        "code": "AXA_OSS_N3_MAMOGRAFI_PSA",
        "service_id": "46",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 3",
        "name": "Kontrol Kemik Yoğunluğu",
        "code": "AXA_OSS_N3_KEMIK_YOGUNLUGU",
        "service_id": "47",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 3",
        "name": "Ayakta Tedavi %100",
        "code": "AXA_OSS_N3_AYAKTA_TEDAVI",
        "service_id": "43",
    },
    {
        "company_code": "AXA",
        "product_type_code": "OSS",
        "network_name": "Network 3",
        "name": "CHECK UP",
        "code": "AXA_OSS_N3_CHECK_UP",
        "service_id": "58",
    },
]

# --- Allianz Poliçe Uygulamaları ---
# Allianz API'sinde ServiceId bazlı alt kırılım yoktur; her Network (networkType)
# doğrudan bir PolicyApplication'dır (AXA TSS ile aynı desen — network kendisi poliçe uygulamasıdır).
POLICY_ALLIANZ_APPLICATIONS = [
    # STSS (Tamamlayıcı Sağlık Sigortası)
    {
        "company_code": "ALLIANZ",
        "product_type_code": "TSS",
        "network_name": "Turkuaz Network",
        "name": "Turkuaz Network",
        "code": "ALLIANZ_STSS_TURKUAZ",
        "service_id": "44",
    },
    {
        "company_code": "ALLIANZ",
        "product_type_code": "TSS",
        "network_name": "Turuncu Network",
        "name": "Turuncu Network",
        "code": "ALLIANZ_STSS_TURUNCU",
        "service_id": "19",
    },
    {
        "company_code": "ALLIANZ",
        "product_type_code": "TSS",
        "network_name": "Kırmızı Network",
        "name": "Kırmızı Network",
        "code": "ALLIANZ_STSS_KIRMIZI",
        "service_id": "55",
    },

    # MDSG (Modüler Sağlık Sigortası — bizde Özel Sağlık / OSS)
    {
        "company_code": "ALLIANZ",
        "product_type_code": "OSS",
        "network_name": "Mavi Network",
        "name": "Mavi Network",
        "code": "ALLIANZ_MDSG_MAVI",
        "service_id": "18",
    },
    {
        "company_code": "ALLIANZ",
        "product_type_code": "OSS",
        "network_name": "Yeşil Network",
        "name": "Yeşil Network",
        "code": "ALLIANZ_MDSG_YESIL",
        "service_id": "17",
    },
    {
        "company_code": "ALLIANZ",
        "product_type_code": "OSS",
        "network_name": "Sarı Network",
        "name": "Sarı Network",
        "code": "ALLIANZ_MDSG_SARI",
        "service_id": "16",
    },
    {
        "company_code": "ALLIANZ",
        "product_type_code": "OSS",
        "network_name": "Beyaz Network",
        "name": "Beyaz Network",
        "code": "ALLIANZ_MDSG_BEYAZ",
        "service_id": "15",
    },
]


# --- Anadolu Poliçe Uygulamaları ---
# Anadolu API'sinde de (Allianz gibi) ServiceId bazlı alt kırılım yoktur; her Network
# doğrudan bir PolicyApplication'dır. external_service_id, networkCodes payload'ında
# gönderilen metinsel network kodudur (örn. "TSS_Tamamlayıcı", "AHN").
POLICY_ANADOLU_APPLICATIONS = [
    # TSS (Tamamlayıcı Sağlık Sigortası)
    {
        "company_code": "ANADOLU",
        "product_type_code": "TSS",
        "network_name": "Tamamlayıcı Network",
        "name": "Tamamlayıcı Network",
        "code": "ANADOLU_TSS_TAMAMLAYICI",
        "service_id": "TSS_Tamamlayıcı",
    },
    {
        "company_code": "ANADOLU",
        "product_type_code": "TSS",
        "network_name": "Tamamlayıcı Eko Network",
        "name": "Tamamlayıcı Eko Network",
        "code": "ANADOLU_TSS_TAMAMLAYICI_EKO",
        "service_id": "TSS_Tamamlayıcı_Eko",
    },

    # ÖSS (Özel Sağlık Sigortası)
    {
        "company_code": "ANADOLU",
        "product_type_code": "OSS",
        "network_name": "Geniş Network",
        "name": "Geniş Network",
        "code": "ANADOLU_OSS_GENIS",
        "service_id": "AHN",
    },
    {
        "company_code": "ANADOLU",
        "product_type_code": "OSS",
        "network_name": "Tüm Network",
        "name": "Tüm Network",
        "code": "ANADOLU_OSS_TUM",
        "service_id": "S",
    },
    {
        "company_code": "ANADOLU",
        "product_type_code": "OSS",
        "network_name": "Eko Network",
        "name": "Eko Network",
        "code": "ANADOLU_OSS_EKO",
        "service_id": "E",
    },
    {
        "company_code": "ANADOLU",
        "product_type_code": "OSS",
        "network_name": "VKV Network",
        "name": "VKV Network",
        "code": "ANADOLU_OSS_VKV",
        "service_id": "VKV",
    },
]


# --- Mapfre Poliçe Uygulamaları ---
# Mapfre API'sinde de (Allianz/Anadolu gibi) ServiceId bazlı alt kırılım yoktur;
# her Network (networkTypeCode) doğrudan bir PolicyApplication'dır.
POLICY_MAPFRE_APPLICATIONS = [
    # OSS (Özel Sağlık Sigortası)
    {
        "company_code": "MAPFRE",
        "product_type_code": "OSS",
        "network_name": "A Network",
        "name": "A Network",
        "code": "MAPFRE_OSS_A",
        "service_id": "65",
    },
    {
        "company_code": "MAPFRE",
        "product_type_code": "OSS",
        "network_name": "B Network",
        "name": "B Network",
        "code": "MAPFRE_OSS_B",
        "service_id": "68",
    },
    {
        "company_code": "MAPFRE",
        "product_type_code": "OSS",
        "network_name": "C Network",
        "name": "C Network",
        "code": "MAPFRE_OSS_C",
        "service_id": "72",
    },
    {
        "company_code": "MAPFRE",
        "product_type_code": "OSS",
        "network_name": "B1 Network",
        "name": "B1 Network",
        "code": "MAPFRE_OSS_B1",
        "service_id": "114",
    },

    # TSS (Tamamlayıcı Sağlık Sigortası)
    {
        "company_code": "MAPFRE",
        "product_type_code": "TSS",
        "network_name": "TSS Eko Network",
        "name": "TSS Eko Network",
        "code": "MAPFRE_TSS_EKO",
        "service_id": "82",
    },
    {
        "company_code": "MAPFRE",
        "product_type_code": "TSS",
        "network_name": "TSS Katılımlı Network",
        "name": "TSS Katılımlı Network",
        "code": "MAPFRE_TSS_KATILIMLI",
        "service_id": "107",
    },
    {
        "company_code": "MAPFRE",
        "product_type_code": "TSS",
        "network_name": "TSS Standart Network",
        "name": "TSS Standart Network",
        "code": "MAPFRE_TSS_STANDART",
        "service_id": "73",
    },
]


# --- HDI Poliçe Uygulamaları ---
# HDI API'sinde her productId doğrudan bir PolicyApplication'dır.
# service_id = productId (string olarak gönderilir).
# Hibrit ürün (productId=538) hem TSS hem ÖSS olarak ikişer kez tanımlanır.
POLICY_HDI_APPLICATIONS = [
    # ÖSS (Özel Sağlık Sigortası)
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "HDI SÜPER-TEMEL-AKILLI SAĞLIK",
        "name": "HDI SÜPER-TEMEL-AKILLI SAĞLIK",
        "code": "HDI_OSS_366",
        "service_id": "366",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "HDI PLATINIUM-GOLD-SILVER SAĞLIK",
        "name": "HDI PLATINIUM-GOLD-SILVER SAĞLIK",
        "code": "HDI_OSS_369",
        "service_id": "369",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "HDI PROMEDICO",
        "name": "HDI PROMEDICO",
        "code": "HDI_OSS_373",
        "service_id": "373",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Size Özel Doğum",
        "name": "Size Özel Doğum",
        "code": "HDI_OSS_383",
        "service_id": "383",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Size Özel Seçimli Teminat ve Acil Sağlık",
        "name": "Size Özel Seçimli Teminat ve Acil Sağlık",
        "code": "HDI_OSS_384",
        "service_id": "384",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Size Özel Sağlık A1",
        "name": "Size Özel Sağlık A1",
        "code": "HDI_OSS_385",
        "service_id": "385",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Size Özel Sağlık A2",
        "name": "Size Özel Sağlık A2",
        "code": "HDI_OSS_397",
        "service_id": "397",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Size Özel Sağlık A3",
        "name": "Size Özel Sağlık A3",
        "code": "HDI_OSS_400",
        "service_id": "400",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Size Özel Sağlık A4",
        "name": "Size Özel Sağlık A4",
        "code": "HDI_OSS_401",
        "service_id": "401",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "Yabancılara Özel Sağlık A6",
        "name": "Yabancılara Özel Sağlık A6",
        "code": "HDI_OSS_403",
        "service_id": "403",
    },
    # TSS (Tamamlayıcı Sağlık Sigortası)
    {
        "company_code": "HDI",
        "product_type_code": "TSS",
        "network_name": "Size Özel Tamamlayıcı Sağlık",
        "name": "Size Özel Tamamlayıcı Sağlık",
        "code": "HDI_TSS_405",
        "service_id": "405",
    },
    # Hibrit ürün (productId=538): hem TSS hem ÖSS kapsamında ikişer kayıt
    {
        "company_code": "HDI",
        "product_type_code": "TSS",
        "network_name": "HDI SİZE ÖZEL 2Sİ 1 ARADA SAĞLIK (TSS)",
        "name": "HDI SİZE ÖZEL 2Sİ 1 ARADA SAĞLIK SİGORTASI",
        "code": "HDI_TSS_538",
        "service_id": "538",
    },
    {
        "company_code": "HDI",
        "product_type_code": "OSS",
        "network_name": "HDI SİZE ÖZEL 2Sİ 1 ARADA SAĞLIK (ÖSS)",
        "name": "HDI SİZE ÖZEL 2Sİ 1 ARADA SAĞLIK SİGORTASI",
        "code": "HDI_OSS_538",
        "service_id": "538",
    },
]


class Command(BaseCommand):
    help = "Şirketler, Networkler ve Poliçe Uygulamalarını veritabanına seed eder."

    @transaction.atomic
    def handle(self, *args, **options):
        # 1. Şirketleri Ekle / Güncelle
        company_count = 0
        for comp_data in INSURANCE_COMPANIES:
            _, created = InsuranceCompany.objects.update_or_create(
                code=comp_data["code"],
                defaults={
                    "name": comp_data["name"],
                    "slug": comp_data["slug"],
                    "is_active": True,
                },
            )
            if created:
                company_count += 1

        # 2. Networkleri Ekle / Güncelle
        network_count = 0
        for net_data in NETWORKS:
            try:
                company = InsuranceCompany.objects.get(code=net_data["company_code"])
                product_type = ProductType.objects.get(code=net_data["product_type_code"])
            except (InsuranceCompany.DoesNotExist, ProductType.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f"Network atlandı ({net_data['name']}): Şirket veya Ürün Tipi bulunamadı ({e})"))
                continue

            _, created = Network.objects.update_or_create(
                company=company,
                product_type=product_type,
                name=net_data["name"],
                defaults={
                    "external_id": net_data.get("external_id"),
                    "shown_by_default": True,
                },
            )
            if created:
                network_count += 1

        # 3. Poliçe Uygulamalarını Ekle / Güncelle
        policy_app_count = 0
        for app_data in POLICY_AXA_APPLICATIONS + POLICY_ALLIANZ_APPLICATIONS + POLICY_ANADOLU_APPLICATIONS + POLICY_MAPFRE_APPLICATIONS + POLICY_HDI_APPLICATIONS:
            try:
                company = InsuranceCompany.objects.get(code=app_data["company_code"])
                product_type = ProductType.objects.get(code=app_data["product_type_code"])
            except (InsuranceCompany.DoesNotExist, ProductType.DoesNotExist) as e:
                self.stdout.write(self.style.WARNING(f"Poliçe uygulaması atlandı ({app_data['name']}): Şirket veya Ürün Tipi bulunamadı ({e})"))
                continue

            network = None
            if app_data.get("network_name"):
                network = Network.objects.filter(
                    company=company,
                    product_type=product_type,
                    name=app_data["network_name"],
                ).first()

            _, created = PolicyApplication.objects.update_or_create(
                company=company,
                product_type=product_type,
                external_service_id=str(app_data["service_id"]),
                defaults={
                    "network": network,
                    "name": app_data["name"],
                    "code": app_data["code"],
                    "is_active": True,
                },
            )
            if created:
                policy_app_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seed başarıyla tamamlandı!\n"
                f"Yeni eklenenler -> Şirket: {company_count}, Network: {network_count}, Poliçe Uygulaması: {policy_app_count}\n"
                f"Tüm veriler güncellendi."
            )
        )
