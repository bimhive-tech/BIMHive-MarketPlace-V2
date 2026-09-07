"""
The platform's own generated domain (Railway's RAILWAY_PUBLIC_DOMAIN) has to end
up in ALLOWED_HOSTS/CSRF_TRUSTED_ORIGINS whether or not anyone remembered to
template it into the env vars — when it went missing, every state-changing
request served from that domain died with "CSRF Failed: Origin checking failed"
and nothing in the app surfaced why. See _merge_platform_domain in settings.
"""
from config.settings import _merge_platform_domain


def test_platform_origin_is_added_when_env_omits_it():
    origins = _merge_platform_domain(
        ["https://hub.bim-hive.com"], "app-production.up.railway.app", as_origin=True
    )
    assert "https://app-production.up.railway.app" in origins
    assert "https://hub.bim-hive.com" in origins


def test_platform_host_is_added_without_a_scheme():
    hosts = _merge_platform_domain(
        ["localhost", "hub.bim-hive.com"], "app-production.up.railway.app", as_origin=False
    )
    assert "app-production.up.railway.app" in hosts
    assert "https://app-production.up.railway.app" not in hosts


def test_no_duplicate_when_env_already_lists_the_platform_domain():
    origins = _merge_platform_domain(
        ["https://app-production.up.railway.app", "https://hub.bim-hive.com"],
        "app-production.up.railway.app",
        as_origin=True,
    )
    assert origins.count("https://app-production.up.railway.app") == 1


def test_configured_entries_survive_when_the_platform_var_is_absent():
    # Local dev / any non-Railway host: nothing to add, nothing dropped.
    origins = _merge_platform_domain(["http://localhost:3000"], "", as_origin=True)
    assert origins == ["http://localhost:3000"]


def test_order_is_preserved():
    origins = _merge_platform_domain(["https://a.example", "https://b.example"], "", as_origin=True)
    assert origins == ["https://a.example", "https://b.example"]
