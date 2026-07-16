#!/usr/bin/env python3
"""Return a privacy-preserving operator identifier for cloud-drive audit logs."""

from __future__ import annotations

import getpass
import hashlib
import json
import platform
import re
import subprocess


def mac_platform_uuid() -> str | None:
    if platform.system() != "Darwin":
        return None
    completed = subprocess.run(
        ["ioreg", "-rd1", "-c", "IOPlatformExpertDevice"], capture_output=True, text=True, check=False
    )
    match = re.search(r'"IOPlatformUUID"\s*=\s*"([^"]+)"', completed.stdout)
    return match.group(1) if completed.returncode == 0 and match else None


def main() -> int:
    raw_identifier = mac_platform_uuid()
    if raw_identifier:
        digest = hashlib.sha256(raw_identifier.encode("utf-8")).hexdigest()[:16]
        result = {"operator_id": f"device-{digest}", "identity_source": "hashed_io_platform_uuid"}
    else:
        result = {"operator_id": getpass.getuser(), "identity_source": "local_account_fallback"}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
