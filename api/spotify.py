from io import BytesIO
import os
import json
import hashlib
import hmac
import random
import re
import secrets
import time
import requests

from colorthief import ColorThief
from base64 import b64encode, urlsafe_b64decode, urlsafe_b64encode
from dotenv import load_dotenv, find_dotenv
from flask import Flask, Response, jsonify, redirect, render_template, request
from urllib.parse import urlencode

from spotify_tokens import SpotifyTokenStore, TokenStoreError

load_dotenv(find_dotenv())

# Spotify scopes:
#   user-read-currently-playing
#   user-read-recently-played
PLACEHOLDER_IMAGE = "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"
PLACEHOLDER_URL = "https://source.unsplash.com/random/300x300/?aerial"
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_SECRET_ID = os.getenv("SPOTIFY_SECRET_ID")
SPOTIFY_TOKEN = ""
SPOTIFY_REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI")
RECONNECT_SECRET = os.getenv("SPOTIFY_RECONNECT_SECRET")
REMINDER_SECRET = os.getenv("SPOTIFY_REMINDER_SECRET") or RECONNECT_SECRET
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")

FALLBACK_THEME = "spotify.html.j2"
ADMIN_COOKIE = "novatorem_spotify_admin"
SIGNED_VALUE_MAX_AGE_SECONDS = 30 * 60
STATE_MAX_AGE_SECONDS = 15 * 60

REFRESH_TOKEN_URL = "https://accounts.spotify.com/api/token"
NOW_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
RECENTLY_PLAYING_URL = (
    "https://api.spotify.com/v1/me/player/recently-played?limit=10"
)

app = Flask(__name__)
TOKEN_STORE = SpotifyTokenStore()


class SpotifyAuthError(RuntimeError):
    pass


def getAuth():
    return b64encode(f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_SECRET_ID}".encode()).decode(
        "ascii"
    )


def refreshToken():
    record = TOKEN_STORE.load()
    if not record or not record.get("refresh_token"):
        raise SpotifyAuthError("Spotify is not connected.")

    data = {
        "grant_type": "refresh_token",
        "refresh_token": record["refresh_token"],
    }

    headers = {"Authorization": "Basic {}".format(getAuth())}
    response = requests.post(
        REFRESH_TOKEN_URL, data=data, headers=headers, timeout=10
    )
    payload = response.json()

    if response.status_code != 200 or "access_token" not in payload:
        error = payload.get("error", "spotify_token_refresh_failed")
        print(json.dumps({"spotify_token_error": error}))
        raise SpotifyAuthError(error)

    # Spotify can rotate refresh tokens. Persist a replacement without changing
    # the original six-month authorization date.
    if payload.get("refresh_token"):
        TOKEN_STORE.rotate_refresh_token(payload["refresh_token"])

    return payload["access_token"]


def get(url):
    global SPOTIFY_TOKEN

    if (SPOTIFY_TOKEN == ""):
        SPOTIFY_TOKEN = refreshToken()

    response = requests.get(
        url, headers={"Authorization": f"Bearer {SPOTIFY_TOKEN}"}, timeout=10
    )

    if response.status_code == 401:
        SPOTIFY_TOKEN = refreshToken()
        response = requests.get(
            url,
            headers={"Authorization": f"Bearer {SPOTIFY_TOKEN}"},
            timeout=10,
        ).json()
        return response
    elif response.status_code == 204:
        raise Exception(f"{url} returned no data.")
    else:
        return response.json()


def _signed_value(purpose):
    if not RECONNECT_SECRET:
        raise SpotifyAuthError("SPOTIFY_RECONNECT_SECRET is not configured.")
    payload = f"{purpose}:{int(time.time())}:{secrets.token_urlsafe(16)}"
    encoded = urlsafe_b64encode(payload.encode()).decode().rstrip("=")
    signature = hmac.new(
        RECONNECT_SECRET.encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _verify_signed_value(value, purpose, max_age):
    if not value or not RECONNECT_SECRET:
        return False
    try:
        encoded, signature = value.rsplit(".", 1)
        expected = hmac.new(
            RECONNECT_SECRET.encode(), encoded.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected):
            return False
        padded = encoded + "=" * (-len(encoded) % 4)
        payload = urlsafe_b64decode(padded.encode()).decode()
        signed_purpose, signed_at, _ = payload.split(":", 2)
        return signed_purpose == purpose and time.time() - int(signed_at) <= max_age
    except (TypeError, ValueError):
        return False


def _admin_authenticated():
    return _verify_signed_value(
        request.cookies.get(ADMIN_COOKIE),
        "admin",
        SIGNED_VALUE_MAX_AGE_SECONDS,
    )


def _route_path(suffix):
    if request.path.startswith("/api/spotify-admin/"):
        prefix = "/api/spotify-admin"
    elif request.path.startswith("/api/spotify/"):
        prefix = "/api/spotify"
    else:
        prefix = ""
    return f"{prefix}/{suffix.lstrip('/')}"


def _public_url(suffix):
    base_url = PUBLIC_BASE_URL or request.host_url.rstrip("/")
    return f"{base_url}/api/spotify-admin/{suffix.lstrip('/')}"


def _redirect_uri():
    return SPOTIFY_REDIRECT_URI or _public_url("callback")


def _management_response(**context):
    response = Response(
        render_template(
            "manage.html.j2",
            login_path=_route_path("login"),
            **context,
        ),
        mimetype="text/html",
    )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.route("/manage", methods=["GET", "POST"])
@app.route("/api/spotify/manage", methods=["GET", "POST"])
@app.route("/api/spotify-admin/manage", methods=["GET", "POST"])
def spotify_manage():
    authenticated = _admin_authenticated()

    if request.method == "POST":
        submitted = request.form.get("secret", "")
        if RECONNECT_SECRET and hmac.compare_digest(submitted, RECONNECT_SECRET):
            response = redirect(_route_path("manage"))
            response.set_cookie(
                ADMIN_COOKIE,
                _signed_value("admin"),
                max_age=SIGNED_VALUE_MAX_AGE_SECONDS,
                secure=request.is_secure,
                httponly=True,
                samesite="Lax",
            )
            response.headers["Cache-Control"] = "no-store"
            return response

        return _management_response(
            authenticated=False, status=TOKEN_STORE.status(), error=True
        ), 401

    return _management_response(
        authenticated=authenticated,
        status=TOKEN_STORE.status(),
        connected=request.args.get("connected") == "1",
        error=False,
    )


@app.route("/login")
@app.route("/api/spotify/login")
@app.route("/api/spotify-admin/login")
def spotify_login():
    if not _admin_authenticated():
        return redirect(_route_path("manage"))
    if not TOKEN_STORE.writable:
        return _management_response(
            authenticated=True,
            status=TOKEN_STORE.status(),
            connected=False,
            error=False,
        ), 503

    params = {
        "client_id": SPOTIFY_CLIENT_ID,
        "response_type": "code",
        "redirect_uri": _redirect_uri(),
        "scope": "user-read-currently-playing user-read-recently-played",
        "state": _signed_value("spotify_oauth"),
        "show_dialog": "true",
    }
    return redirect("https://accounts.spotify.com/authorize?" + urlencode(params))


@app.route("/callback")
@app.route("/api/spotify/callback")
@app.route("/api/spotify-admin/callback")
def spotify_callback():
    if request.args.get("error"):
        return Response("Spotify authorization was cancelled.", status=400)
    if not _verify_signed_value(
        request.args.get("state"), "spotify_oauth", STATE_MAX_AGE_SECONDS
    ):
        return Response("Invalid or expired authorization request.", status=400)

    code = request.args.get("code")
    if not code:
        return Response("Spotify did not return an authorization code.", status=400)

    response = requests.post(
        REFRESH_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
        },
        headers={"Authorization": "Basic {}".format(getAuth())},
        timeout=10,
    )
    payload = response.json()
    if response.status_code != 200 or not payload.get("refresh_token"):
        print(json.dumps({"spotify_authorization_error": payload.get("error")}))
        return Response("Spotify authorization could not be completed.", status=502)

    try:
        TOKEN_STORE.save_authorization(payload["refresh_token"])
    except TokenStoreError:
        return Response("The durable token store is not configured.", status=503)

    global SPOTIFY_TOKEN
    SPOTIFY_TOKEN = payload.get("access_token", "")
    return redirect(_public_url("manage") + "?connected=1")


@app.route("/status")
@app.route("/api/spotify/status")
@app.route("/api/spotify-admin/status")
def spotify_status():
    supplied = request.headers.get("Authorization", "").removeprefix("Bearer ")
    reminder_authenticated = bool(
        REMINDER_SECRET
        and supplied
        and hmac.compare_digest(supplied, REMINDER_SECRET)
    )
    if not (_admin_authenticated() or reminder_authenticated):
        return jsonify({"error": "unauthorized"}), 401

    response = jsonify(TOKEN_STORE.status())
    response.headers["Cache-Control"] = "no-store"
    return response


def barGen(barCount):
    barCSS = ""
    left = 1
    for i in range(1, barCount + 1):
        anim = random.randint(500, 1000)
        # below code generates random cubic-bezier values
        x1 = random.random()
        y1 = random.random()*2
        x2 = random.random()
        y2 = random.random()*2
        barCSS += (
            ".bar:nth-child({})  {{ left: {}px; animation-duration: 15s, {}ms; animation-timing-function: ease, cubic-bezier({},{},{},{}); }}".format(
                i, left, anim, x1, y1, x2, y2
            )
        )
        left += 4
    return barCSS


def gradientGen(albumArtURL, color_count):
    colortheif = ColorThief(
        BytesIO(requests.get(albumArtURL, timeout=10).content)
    )
    palette = colortheif.get_palette(color_count)
    return palette


def getTemplate():
    try:
        file = open("api/templates.json", "r")
        templates = json.loads(file.read())
        return templates["templates"][templates["current-theme"]]
    except Exception as e:
        print(f"Failed to load templates.\r\n```{e}```")
        return FALLBACK_THEME

def loadImageB64(url):
    response = requests.get(url, timeout=10)
    return b64encode(response.content).decode("ascii")


def normalizeColor(value, fallback):
    return value if re.fullmatch(r"[0-9a-fA-F]{6}", value or "") else fallback


def makeErrorSVG(background_color, border_color):
    return render_template(
        "spotify-error.html.j2",
        background_color=background_color,
        border_color=border_color,
    )


def makeSVG(data, background_color, border_color):
    barCount = 84
    contentBar = "".join(["<div class='bar'></div>" for _ in range(barCount)])
    barCSS = barGen(barCount)

    if not "is_playing" in data:
        #contentBar = "" #Shows/Hides the EQ bar if no song is currently playing
        currentStatus = "Recently played:"
        recentPlays = get(RECENTLY_PLAYING_URL)
        recentPlaysLength = len(recentPlays["items"])
        itemIndex = random.randint(0, recentPlaysLength - 1)
        item = recentPlays["items"][itemIndex]["track"]
    else:
        item = data["item"]
        currentStatus = "Vibing to:"

    if item["album"]["images"] == []:
        image = PLACEHOLDER_IMAGE
        barPalette = gradientGen(PLACEHOLDER_URL, 4)
        songPalette = gradientGen(PLACEHOLDER_URL, 2)
    else:
        image = loadImageB64(item["album"]["images"][1]["url"])
        barPalette = gradientGen(item["album"]["images"][1]["url"], 4)
        songPalette = gradientGen(item["album"]["images"][1]["url"], 2)

    artistName = item["artists"][0]["name"].replace("&", "&amp;")
    songName = item["name"].replace("&", "&amp;")
    songURI = item["external_urls"]["spotify"]
    artistURI = item["artists"][0]["external_urls"]["spotify"]

    dataDict = {
        "contentBar": contentBar,
        "barCSS": barCSS,
        "artistName": artistName,
        "songName": songName,
        "songURI": songURI,
        "artistURI": artistURI,
        "image": image,
        "status": currentStatus,
        "background_color": background_color,
        "border_color": border_color,
        "barPalette": barPalette,
        "songPalette": songPalette
    }

    return render_template(getTemplate(), **dataDict)


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
@app.route('/with_parameters')
def catch_all(path):
    background_color = normalizeColor(
        request.args.get('background_color'), "181414"
    )
    border_color = normalizeColor(request.args.get('border_color'), "181414")

    try:
        try:
            data = get(NOW_PLAYING_URL)
        except Exception:
            data = get(RECENTLY_PLAYING_URL)
        svg = makeSVG(data, background_color, border_color)
        spotify_status_header = "connected"
    except Exception as error:
        print(json.dumps({"spotify_card_fallback": type(error).__name__}))
        svg = makeErrorSVG(background_color, border_color)
        spotify_status_header = "reconnect-required"

    resp = Response(svg, mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "s-maxage=1"
    resp.headers["X-Spotify-Status"] = spotify_status_header

    return resp


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=os.getenv("PORT") or 5000)
