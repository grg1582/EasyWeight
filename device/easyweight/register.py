"""Register this mirror with the backend, once. Saves the server address and
the mirror's token to data/device.json, which the app then uses.

    python -m easyweight.register --api-url http://localhost:8000 --name "Home mirror"
"""
import argparse
import sys
import urllib.error

from .sync import DEVICE_CONFIG, api_request, save_device_config


def main(argv=None):
    p = argparse.ArgumentParser(description="Register this mirror with the EasyWeight backend")
    p.add_argument("--api-url", default="http://localhost:8000",
                   help="the backend's address (default: %(default)s)")
    p.add_argument("--name", required=True, help='a name for this mirror, e.g. "Home mirror"')
    p.add_argument("--config", default=DEVICE_CONFIG,
                   help="where to save the token (default: %(default)s)")
    args = p.parse_args(argv)

    url = args.api_url.rstrip("/")
    try:
        status, body = api_request("POST", url + "/api/v1/devices", {"name": args.name})
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"Couldn't reach {url}: {e}\nIs the backend running? (docker compose up)")
    if status != 201:
        sys.exit(f"The server refused: HTTP {status} {body}")
    save_device_config({"api_url": url, "device_id": body["id"], "name": body["name"],
                        "token": body["token"]}, args.config)
    print(f'Registered "{body["name"]}" ({body["id"]}).')
    print(f"Saved its token to {args.config}. The app will now send workouts to {url}")


if __name__ == "__main__":
    main()
