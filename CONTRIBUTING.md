# Contributing to ProxyPool

Thank you for your interest in contributing! This guide will help you get started.

## Development Environment Setup

### Prerequisites

- Python 3.10+
- Redis server (running on port 6380 with password `pwd`, or configure your own)
- Git

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-repo/proxy_pool.git
cd proxy_pool

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Ensure Redis is running, then start the scheduler
python proxyPool.py schedule

# In another terminal, start the API server
python proxyPool.py server
```

### Using Docker (Alternative)

```bash
docker-compose up -d
```

This starts both Redis and the app with all dependencies configured.

## How to Add a New Proxy Source

Proxy sources are defined in `fetcher/proxyFetcher.py`. Each source is a **static method** on the `ProxyFetcher` class.

### Step-by-step

1. Open `fetcher/proxyFetcher.py`
2. Add a new static method following the naming convention `freeProxyXX`:

```python
@staticmethod
def freeProxy101():
    """ Your Source Name - description """
    # Scrape or fetch proxies from the source
    # Each method must yield proxy strings in "ip:port" format
    url = "https://example.com/proxies"
    html = WebRequest().get(url).text
    # Parse the response to extract ip:port pairs
    for proxy in extracted_proxies:
        yield proxy
```

3. Register the new source in `setting.py` by adding the method name to the `PROXY_FETCHER` list:

```python
PROXY_FETCHER = [
    # ... existing sources ...
    "freeProxy101",
]
```

4. Test your source:

```bash
python -c "from fetcher.proxyFetcher import ProxyFetcher; print(list(ProxyFetcher.freeProxy101()))"
```

### Guidelines for Proxy Sources

- **Naming**: Use `freeProxyXX` where XX is the next available number.
- **Return format**: Methods must `yield` or `return` proxy strings as `"ip:port"`.
- **Docstring**: Include the source name and a brief description.
- **Error handling**: Wrap network calls in try/except; yield nothing on failure rather than raising.
- **Rate limiting**: Use `sleep()` if the source is sensitive to frequent requests.
- **Legality**: Only scrape sources that allow it. Respect robots.txt and terms of service.

## API Endpoints

When adding new API endpoints, add them to `api/proxyApi.py` and update the `api_list` shown on the index page (`/`).

## Code Style

- Follow PEP 8 conventions.
- Keep methods focused and concise.
- Add docstrings to new functions and classes.

## Submitting Changes

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes: `git commit -m "Add: description"`
4. Push to your fork: `git push origin feature/my-feature`
5. Open a Pull Request with a clear description of your changes.

## Reporting Issues

Please open an issue with:

- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
