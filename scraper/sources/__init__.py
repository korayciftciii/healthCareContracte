"""Scraper plugin mimarisi.

Her şirkete ait scraper, BaseScraper'ı implement eden ayrı bir modülde
tanımlanır ve @register decorator'ı ile SCRAPER_REGISTRY'e kaydedilir.

Kullanım:
    from scraper.sources.registry import get_scraper
    ScraperClass = get_scraper("axa")
    ScraperClass().run(job)
"""
