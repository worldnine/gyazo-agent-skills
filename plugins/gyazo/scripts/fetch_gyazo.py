#!/usr/bin/env python3
"""Gyazo画像をダウンロードするスクリプト（標準ライブラリのみ、全OS対応）

使い方: python fetch_gyazo.py <gyazo_url>

出力（標準出力）:
  1行目: ダウンロードした画像の絶対パス
  2行目以降（トークン設定時のみ）: メタデータ（KEY: VALUE 形式）
    例: created_at, app, source_url, title, desc, ocr_locale, ocr_text（画像内テキスト）

対応URL:
  https://gyazo.com/{id}              - 個人Gyazo
  https://i.gyazo.com/{id}.png|.jpg   - 個人Gyazo（直接画像）
  https://{org}.gyazo.com/{id}        - Gyazo Teams

画像の取得方法:
  - トークン設定時: Gyazo API（/api/images/{id}）が返す画像URLを優先
  - トークン未設定時 / API失敗時: 公開ページの og:image からフォールバック取得

メタデータ取得には以下の環境変数が必要:
  - 個人Gyazo: GYAZO_ACCESS_TOKEN
  - Teams Gyazo: GYAZO_TEAMS_ACCESS_TOKEN（無ければ GYAZO_ACCESS_TOKEN にフォールバック）
未設定時は画像のみダウンロードし、メタデータ行は出力しない（壊れない）。
メタデータ取得の失敗は致命的ではない（画像取得にフォールバックして続行する）。
"""

import re
import sys
import tempfile
from pathlib import Path

from _gyazo_common import (
    GyazoRequestError,
    api_get,
    get_access_token,
    http_get,
    page_url_for,
    parse_gyazo_url,
)

DEST_DIR = Path(tempfile.gettempdir()) / "gyazo"

OG_IMAGE_PATTERN = re.compile(
    r'<meta[^>]*\bproperty=["\']og:image["\'][^>]*\bcontent=["\']([^"\']+)["\']'
    r'|<meta[^>]*\bcontent=["\']([^"\']+)["\'][^>]*\bproperty=["\']og:image["\']',
    re.IGNORECASE,
)


def fetch_thumb_url(page_url: str) -> str:
    """公開ページのHTMLから og:image のURLを抽出する（フォールバック用）"""
    html = http_get(page_url, timeout=15).decode("utf-8", errors="replace")
    m = OG_IMAGE_PATTERN.search(html)
    if not m:
        print(f"エラー: 画像URLを抽出できませんでした: {page_url}", file=sys.stderr)
        sys.exit(1)
    return m.group(1) or m.group(2)


def save_image(image_url: str, image_id: str, *, raise_on_error: bool = False) -> Path:
    """画像URLをダウンロードして一時ディレクトリに保存する"""
    ext = Path(image_url.split("?")[0]).suffix.lower() or ".jpg"
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    dest_file = DEST_DIR / f"{image_id}{ext}"
    if dest_file.exists() and dest_file.stat().st_size > 0:
        return dest_file
    data = http_get(image_url, timeout=30, on_error="raise" if raise_on_error else "exit")
    dest_file.write_bytes(data)
    return dest_file


def fetch_api_data(image_id: str, org: str | None, token: str) -> dict | None:
    """APIから画像情報（画像URL＋メタデータ）を取得。失敗しても致命的ではないのでNone"""
    try:
        data = api_get(f"/api/images/{image_id}", org=org, token=token, on_error="raise")
    except GyazoRequestError as e:
        print(f"# API取得をスキップ（ページ取得にフォールバック）: {e}", file=sys.stderr)
        return None
    return data if isinstance(data, dict) else None


def download_image(image_id: str, org: str | None, api_data: dict | None) -> Path:
    # トークン設定時: APIレスポンスの画像URLを第一候補にする
    # （非公開・Teams画像でもページのHTML構造に依存せず取得できる）
    if api_data:
        for image_url in (api_data.get("url"), api_data.get("thumb_url")):
            if not image_url:
                continue
            try:
                return save_image(image_url, image_id, raise_on_error=True)
            except GyazoRequestError as e:
                print(f"# API画像URLからの取得に失敗、ページから再試行: {e}", file=sys.stderr)
    # フォールバック: 公開ページの og:image から取得
    return save_image(fetch_thumb_url(page_url_for(image_id, org)), image_id)


def print_metadata(data: dict) -> None:
    """APIレスポンスからメタデータを KEY: VALUE 形式で出力"""
    meta = data.get("metadata") or {}
    # Gyazo API は OCR を metadata.ocr 配下に返す（トップレベルに無い場合もあるため両対応）
    ocr = meta.get("ocr") or data.get("ocr") or {}

    fields: list[tuple[str, str]] = []
    if data.get("created_at"):
        fields.append(("created_at", data["created_at"]))
    if data.get("type"):
        fields.append(("type", data["type"]))
    if meta.get("app"):
        fields.append(("app", meta["app"]))
    if meta.get("title"):
        fields.append(("title", meta["title"]))
    if meta.get("url"):
        fields.append(("source_url", meta["url"]))
    if meta.get("desc"):
        fields.append(("desc", meta["desc"]))
    if ocr.get("locale"):
        fields.append(("ocr_locale", ocr["locale"]))

    for key, value in fields:
        # 改行を含む値は1行に潰す
        value = " ".join(str(value).splitlines()).strip()
        print(f"{key}: {value}")

    ocr_desc = ocr.get("description") or ""
    if ocr_desc.strip():
        # OCR本文は複数行のまま出力する（画像を見られないモデルが内容を把握するため）
        print("ocr_text:")
        print(ocr_desc.rstrip())


def main() -> None:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        sys.exit(0 if len(sys.argv) >= 2 else 1)

    url = sys.argv[1]
    image_id, org = parse_gyazo_url(url)

    token = get_access_token(org)
    api_data = fetch_api_data(image_id, org, token) if token else None

    dest = download_image(image_id, org, api_data)
    print(dest)

    if api_data:
        print_metadata(api_data)


if __name__ == "__main__":
    main()
