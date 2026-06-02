# Changelog

All notable changes to the ProxyPool project are documented here.

## [2.4.0] - 2026-04-24

### Added

#### 65 Proxy Sources

Expanded the proxy pool with 65 active proxy source crawlers covering a wide range of free proxy providers:

- `freeProxy03` - KXDaili (开心代理)
- `freeProxy05` - ProxyListPlus
- `freeProxy07` - ProxyScrape
- `freeProxy10` - 89IP
- `freeProxy11` - IP3366
- `freeProxy12` - Xiladaili (西拉代理)
- `freeProxy13` - Kuaidaili (快代理)
- `freeProxy15` - Premproxy
- `freeProxy17` - ProxyList
- `freeProxy18` - 66IP
- `freeProxyScdn` - SCDN proxies
- `freeProxy43` through `freeProxy100` - Additional free proxy sources from various providers worldwide

These sources are configured in `setting.py` under `PROXY_FETCHER`.

#### API Endpoints (11 total)

| Endpoint | Method | Description |
|---|---|---|
| `/` | GET | API index with endpoint list |
| `/get/` | GET | Get a proxy (supports `type=https` filter) |
| `/pop/` | GET | Get and remove a proxy from the pool |
| `/delete/` | GET | Delete a specific proxy (`proxy=ip:port`) |
| `/all/` | GET | Get all proxies (supports `type=https` filter) |
| `/count/` | GET | Get proxy count with HTTP/HTTPS and source breakdown |
| `/get_status/` | GET | Detailed pool status (health, speed stats, distribution) |
| `/proxy_use_count/` | GET | Proxy use count ranking (`limit=N`) |
| `/export/` | GET | Export proxies in JSON or TXT format with filters |
| `/refresh/` | GET | Refresh placeholder (handled by scheduler) |
| `/refresh_pool/` | GET | Manually trigger proxy pool refresh |

#### Infrastructure

- **Dockerfile**: Multi-stage build based on `python:3.13-slim` with gunicorn entrypoint
- **docker-compose.yml**: Redis + App services with health checks, persistent Redis volume
- **Health checks**: Both Redis and the application include Docker HEALTHCHECK directives

### Changed

- Improved proxy validation with configurable timeout (`VERIFY_TIMEOUT`)
- Enhanced proxy metadata tracking (speed, last_status, use_count, region)
- Better error handling in proxy fetchers with graceful degradation
- Gunicorn integration for production-grade WSGI serving (4 workers)

### Technical Details

- **Framework**: Flask + APScheduler
- **Database**: Redis on port 6380 with password authentication
- **API Port**: 5010
- **Python**: 3.13 compatible
- **Timezone**: Asia/Shanghai (scheduler)
