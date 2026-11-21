"""Register this mirror to your account on the backend, once. Signs in with
your email and password, then saves the server address and the mirror's own
token to data/device.json, which the app then uses. Your password is not saved.

    python -m easyweight.register --name "Home mirror" --email you@example.com

No account yet? Create one in the web dashboard, or at /docs on the backend.
"""
import argparse
import getpass
import sys
import urllib.error

from .sync import DEVICE_CONFIG, api_request, save_device_config


def main(argv=None):
    p = argparse.ArgumentParser(description="Register this mirror to your EasyWeight account")
    p.add_argument("--api-url", default="http://localhost:8000",
                   help="the backend's address (default: %(default)s)")
    p.add_argument("--name", required=True, help='a name for this mirror, e.g. "Home mirror"')
    p.add_argument("--email", required=True, help="your account's email")
    p.add_argument("--password", help="your password (asked for when left out, which is "
                                      "safer: it then isn't kept in your shell history)")
    p.add_argument("--config", default=DEVICE_CONFIG,
                   help="where to save the token (default: %(default)s)")
    args = p.parse_args(argv)

    url = args.api_url.rstrip("/")
    password = args.password or getpass.getpass(f"Password for {args.email}: ")
    try:
        status, body = api_request("POST", url + "/api/v1/auth/login",
                                   form={"username": args.email, "password": password})
        if status == 401:
            sys.exit("Wrong email or password")
        if status != 200:
            sys.exit(f"Couldn't sign in: HTTP {status} {body}")
        status, body = api_request("POST", url + "/api/v1/devices", {"name": args.name},
                                   token=body["access_token"])
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"Couldn't reach {url}: {e}\nIs the backend running? (docker compose up)")
    if status != 201:
        sys.exit(f"The server refused: HTTP {status} {body}")
    save_device_config({"api_url": url, "device_id": body["id"], "name": body["name"],
                        "token": body["token"]}, args.config)
    print(f'Registered "{body["name"]}" ({body["id"]}) to {args.email}.')
    print(f"Saved its token to {args.config}. The app will now send workouts to {url}")


if __name__ == "__main__":
    main()
