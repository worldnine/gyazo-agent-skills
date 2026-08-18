"""gyazo プラグインの共通ユーティリティ（標準ライブラリのみ）"""

import json
import os
import re
import sys
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

USER_AGENT = "Mozilla/5.0 (claude-skills/gyazo)"

TEAMS_PATTERN = re.compile(
    r"^https?://([a-zA-Z0-9_-]+)\.gyazo\.com/([a-f0-9]+)(?:\.[a-z0-9]+)?$"
)
PERSONAL_PATTERN = re.compile(
    r"^https?://gyazo\.com/([a-f0-9]+)(?:\.[a-z0-9]+)?$"
)


def parse_gyazo_url(url: str) -> tuple[str, str | None]:
    """Gyazo URLから (image_id, org) を返す。個人Gyazoは org=None。"""
    m = PERSONAL_PATTERN.match(url)
    if m:
        return m.group(1), None

    m = TEAMS_PATTERN.match(url)
    if m:
        org, image_id = m.group(1), m.group(2)
        if org in ("i", "t"):
            return image_id, None
        return image_id, org

    print(f"エラー: 対応していないGyazo URLです: {url}", file=sys.stderr)
    sys.exit(1)


def page_url_for(image_id: str, org: str | None) -> str:
    if org:
        return f"https://{org}.gyazo.com/{image_id}"
    return f"https://gyazo.com/{image_id}"


def http_get(url: str, *, timeout: int = 15) -> bytes:
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:200]
        except Exception:
            pass
        msg = f"エラー: 取得に失敗しました (HTTP {e.code}): {url}"
        if body:
            msg += f"\n  詳細: {body}"
        print(msg, file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"エラー: 接続に失敗しました: {e.reason}", file=sys.stderr)
        sys.exit(1)


def get_access_token(org: str | None) -> str | None:
    """環境変数からアクセストークンを取得。未設定ならNone。"""
    if org:
        return os.environ.get("GYAZO_TEAMS_ACCESS_TOKEN") or os.environ.get("GYAZO_ACCESS_TOKEN")
    return os.environ.get("GYAZO_ACCESS_TOKEN")


def require_access_token(org: str | None) -> str:
    """トークン未設定時はエラー終了。"""
    token = get_access_token(org)
    if not token:
        env_name = "GYAZO_TEAMS_ACCESS_TOKEN または GYAZO_ACCESS_TOKEN" if org else "GYAZO_ACCESS_TOKEN"
        print(f"エラー: 環境変数 {env_name} が必要です", file=sys.stderr)
        print("Gyazoの『設定 → 開発者向け』でアクセストークンを発行してください", file=sys.stderr)
        sys.exit(1)
    return token


def api_get(path: str, *, org: str | None, token: str, params: dict | None = None) -> dict | list:
    """Gyazo API GET（access_tokenを自動付与してJSON返却）

    APIエンドポイントは個人/Teams問わず api.gyazo.com 統一。トークン側に
    所属（個人 or Teams）情報が紐付くため、ホスト分岐は不要。
    """
    query = {"access_token": token}
    if params:
        query.update(params)
    url = f"https://api.gyazo.com{path}?{urlencode(query)}"
    body = http_get(url, timeout=20).decode("utf-8", errors="replace")
    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        print(f"エラー: APIレスポンスをJSONとして解析できませんでした: {e}", file=sys.stderr)
        sys.exit(1)
