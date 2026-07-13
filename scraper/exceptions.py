class ScraperError(Exception):
    """Base class for all scraper-related errors."""


class ScraperNotConfigured(ScraperError):
    """Raised when a required scraper config value (e.g. an endpoint path) is missing."""


class ScraperHTTPError(ScraperError):
    """Raised when the upstream site returns a non-2xx response."""


class ScraperParseError(ScraperError):
    """Raised when the upstream response body doesn't match the expected shape."""
