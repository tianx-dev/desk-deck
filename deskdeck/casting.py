"""Optional Cast transport. The community DashCast receiver is a trust dependency."""

import json
import logging
import time
import uuid
from urllib.parse import quote
from urllib.request import Request, urlopen


def pairing_url(config):
    url = config.public_url.rstrip("/") + "/"
    return (
        url + "#key=" + quote(config.pairing_key, safe="")
        if config.pairing_key
        else url
    )


def cast(config):
    try:
        import pychromecast
        from pychromecast.controllers.dashcast import DashCastController
    except ImportError:
        raise ValueError(
            'Install the optional transport with: python3 -m pip install -e ".[cast]"'
        ) from None
    if not config.device_host or not config.pairing_key:
        raise ValueError(
            "Cast requires LAN configuration, a device host, and a pairing key"
        )
    # Avoid third-party diagnostic logs accidentally including the private launch URL.
    logging.getLogger("pychromecast").setLevel(logging.CRITICAL)
    with urlopen(
        f"http://{config.device_host}:8008/setup/eureka_info", timeout=5
    ) as response:
        info = json.load(response)
    device_id = uuid.UUID(info["ssdp_udn"])
    cast_device = pychromecast.get_chromecast_from_host(
        (
            config.device_host,
            8009,
            device_id,
            "Google Nest Hub",
            config.device_name or info.get("name"),
        )
    )
    try:
        cast_device.wait(timeout=15)
        cast_device.quit_app()
        time.sleep(2)
        controller = DashCastController()
        cast_device.register_handler(controller)
        launched_at = time.time()
        controller.load_url(pairing_url(config), force=True)
        print(
            "Cast launch requested. Waiting for a page receipt, not just an app-launch acknowledgement.",
            flush=True,
        )
        received = False
        for _ in range(25):
            time.sleep(1)
            try:
                request = Request(
                    f"http://127.0.0.1:{config.port}/api/health",
                    headers={"Authorization": "Bearer " + config.pairing_key},
                )
                with urlopen(request, timeout=2) as response:
                    health = json.load(response)
                receipt = health.get("display_receipts", {}).get(config.device_host, {})
                if receipt.get("at", 0) >= launched_at:
                    print(
                        f"Page received: {receipt.get('width')} × {receipt.get('height')}, touch points: {receipt.get('touch')}. Test a physical tap next.",
                        flush=True,
                    )
                    received = True
                    break
            except (OSError, ValueError):
                continue
        if not received:
            print(
                "No page receipt yet. Check the display and the troubleshooting guide.",
                flush=True,
            )
        print(
            "Keeping the sender connected. Ctrl-C disconnects this sender; use the display Home gesture to leave the page.",
            flush=True,
        )
        while True:
            time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        cast_device.disconnect()
