"""Connect this mirror to your account by scanning a QR code with your phone.
No password is typed on the mirror.

    python -m easyweight.pair --name "Home mirror"

The mirror makes its own token and sends the server only its hash. The server
answers with a short code, which the mirror shows as a big QR code. Scan it
with your phone (signed in to the site), press Connect, and the mirror saves
its token to data/device.json. Codes last 10 minutes.

For a backend on your own computer, give both addresses, using the computer's
address on your network (not localhost) so the phone can open the link:

    python -m easyweight.pair --api-url http://192.168.1.20:8000 --site http://192.168.1.20:5173
"""
import argparse
import hashlib
import secrets
import sys
import time
import urllib.error

from .sync import DEVICE_CONFIG, api_request, save_device_config

API_URL = "https://easyweight-api.onrender.com"
SITE_URL = "https://easyweight.onrender.com"
POLL_SECONDS = 2


class PairingFailed(Exception):
    pass


def pretty(code):
    """'K7QM3XPA' → 'K7QM-3XPA', easier to read and type"""
    return f"{code[:4]}-{code[4:]}"


def pair(api_url, site_url, name, show, wait, request=api_request):
    """Asks for a code, calls show(link, code) to put it on screen, then asks
    every few seconds whether it was claimed, calling wait(seconds) in between
    (wait returns False to give up). Returns the device config to save"""
    api_url = api_url.rstrip("/")
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    status, body = request("POST", api_url + "/api/v1/pairing",
                           {"token_hash": token_hash, "name": name})
    if status != 201:
        raise PairingFailed(f"The server refused: HTTP {status} {body}")
    code = body["code"]
    show(f"{site_url.rstrip('/')}/pair/{code}", pretty(code))
    while wait(POLL_SECONDS):
        status, body = request("GET", f"{api_url}/api/v1/pairing/{code}", token=token)
        if status == 404:
            raise PairingFailed("The code expired. Run this again for a new one")
        if status == 200 and body["status"] == "paired":
            device = body["device"]
            return {"api_url": api_url, "device_id": device["id"], "name": device["name"],
                    "token": token}
        # Anything else (the network blinked, the server woke up): ask again
    raise PairingFailed("Cancelled")


# Showing the code

def qr_image(link, size):
    """A square image (white background, black modules) of the link's QR code"""
    import numpy as np
    import segno

    matrix = np.array(list(segno.make(link, error="m").matrix), dtype=np.uint8)
    matrix = np.pad(matrix, 4)  # the quiet zone a scanner needs around the code
    cell = max(1, size // len(matrix))
    image = np.where(np.kron(matrix, np.ones((cell, cell), np.uint8)) == 1, 0, 255)
    return image.astype(np.uint8)


class Window:
    """The QR code on the mirror's screen, big and centered on black"""

    def __init__(self, fullscreen):
        import cv2

        self.cv2 = cv2
        self.name = "EasyWeight: connect this mirror"
        cv2.namedWindow(self.name, cv2.WINDOW_NORMAL)
        if fullscreen:
            cv2.setWindowProperty(self.name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)
        self.frame = None

    def show(self, link, code):
        import numpy as np

        cv2 = self.cv2
        w, h = 1280, 720
        frame = np.zeros((h, w, 3), np.uint8)
        qr = cv2.cvtColor(qr_image(link, 440), cv2.COLOR_GRAY2BGR)
        y0, x0 = 70, (w - qr.shape[1]) // 2
        frame[y0:y0 + qr.shape[0], x0:x0 + qr.shape[1]] = qr
        lines = [("Scan with your phone to connect this mirror", 1.0, (200, 200, 200), 40),
                 (code, 1.6, (255, 210, 60), 600), ("Q to cancel", 0.7, (140, 140, 140), 690)]
        for text, scale, color, y in lines:
            thickness = 3 if scale > 1.2 else 2
            (tw, _), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_DUPLEX, scale, thickness)
            cv2.putText(frame, text, ((w - tw) // 2, y), cv2.FONT_HERSHEY_DUPLEX, scale,
                        color, thickness, cv2.LINE_AA)
        self.frame = frame
        cv2.imshow(self.name, frame)

    def wait(self, seconds):
        """Keeps the window responsive. False when Q or Esc is pressed"""
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            if self.cv2.waitKey(50) & 0xFF in (ord("q"), ord("Q"), 27):
                return False
        return True

    def close(self):
        self.cv2.destroyWindow(self.name)


def show_in_terminal(link, code):
    import segno

    segno.make(link, error="m").terminal(compact=True)
    print(f"\nScan the code with your phone, or open {link}")
    print(f"Code: {code}. Waiting for you to connect it (Ctrl+C to cancel)...")


def main(argv=None):
    p = argparse.ArgumentParser(description="Connect this mirror to your account with a QR code")
    p.add_argument("--name", default="Mirror", help='a name for this mirror (default: %(default)s)')
    p.add_argument("--api-url", default=API_URL, help="the backend (default: %(default)s)")
    p.add_argument("--site", default=SITE_URL, help="the web app (default: %(default)s)")
    p.add_argument("--terminal", action="store_true",
                   help="print the QR code in the terminal instead of opening a window")
    p.add_argument("--fullscreen", action="store_true", help="show the window fullscreen")
    p.add_argument("--config", default=DEVICE_CONFIG,
                   help="where to save the token (default: %(default)s)")
    args = p.parse_args(argv)

    window = None if args.terminal else Window(args.fullscreen)
    show = window.show if window else show_in_terminal
    wait = window.wait if window else lambda s: time.sleep(s) or True
    try:
        config = pair(args.api_url, args.site, args.name, show, wait)
    except PairingFailed as e:
        sys.exit(str(e))
    except (urllib.error.URLError, OSError) as e:
        sys.exit(f"Couldn't reach {args.api_url}: {e}")
    except KeyboardInterrupt:
        sys.exit("Cancelled")
    finally:
        if window:
            window.close()
    save_device_config(config, args.config)
    print(f'Connected "{config["name"]}". Saved its token to {args.config}.')
    print("The app will now send your workouts to your account.")


if __name__ == "__main__":
    main()
