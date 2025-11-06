"""
Validate saved NIM endpoints by performing a simple HTTP GET/HEAD.

Usage:
    python -m BudgetGuard_TechOps.tools.validate_endpoints
"""

import ssl
import socket
import urllib.request
from typing import Tuple

from BudgetGuard_TechOps.config_manager import ConfigManager


def _check_url(url: str, timeout: float = 5.0) -> Tuple[bool, int]:
    try:
        req = urllib.request.Request(url, method='HEAD')
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return True, resp.getcode() or 200
    except urllib.error.HTTPError as e:
        return False, e.code
    except (urllib.error.URLError, socket.timeout):
        return False, 0


def main():
    cfg_mgr = ConfigManager()
    endpoints = cfg_mgr.load_endpoints()
    if not endpoints:
        print('No endpoints saved.')
        return
    if isinstance(endpoints, dict):
        all_items = []
        for _, v in endpoints.items():
            if isinstance(v, list):
                all_items.extend(v)
            else:
                all_items.append(v)
        endpoints = all_items

    ok = 0
    fail = 0
    for item in endpoints:
        node = item.get('node_type')
        provider = item.get('provider')
        url = item.get('endpoint')
        healthy, code = _check_url(url)
        status = 'OK' if healthy else f'FAIL ({code})'
        print(f"{node} → {provider}: {url} -> {status}")
        if healthy:
            ok += 1
        else:
            fail += 1

    print(f"Validation complete: {ok} OK, {fail} FAIL")


if __name__ == '__main__':
    main()


