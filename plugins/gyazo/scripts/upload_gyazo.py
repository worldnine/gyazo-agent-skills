#!/usr/bin/env python3
"""Gyazoに画像をアップロードするスクリプト（標準ライブラリのみ）

POST https://upload.gyazo.com/api/upload （multipart/form-data）
公式 MCP サーバー（nota/gyazo-mcp-server）の gyazo_upload と同じAPI仕様。

使い方:
  python upload_gyazo.py <image_file> [--title "..."] [--desc "..."] [--referer URL] [--app "App"] [--team <org>]

引数:
  image        アップロードする画像ファイルパス（PNG/JPEG/GIF等）
  --title      タイトル（任意）
  --desc       説明文（任意）
  --referer    元ページURL（任意）
  --app        アプリ名（任意）
  --team       Teams Gyazoの組織名（例: your-org）。省略時は個人Gyazo

環境変数:
  GYAZO_ACCESS_TOKEN          個人Gyazo
  GYAZO_TEAMS_ACCESS_TOKEN    Teams Gyazo（--team指定時に優先）

出力: permalink・image_id・type・created_at
"""

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from _gyazo_common import USER_AGENT, require_access_token

UPLOAD_URL = "https://upload.gyazo.com/api/upload"


def build_multipart(fields: dict[str, str], file_path: Path) -> tuple[bytes, str]:
    """multipart/form-data ボディを組み立てる（標準ライブラリのみ）"""
    boundary = "----GyazoPluginBoundary" + uuid.uuid4().hex
    buf = bytearray()

    for name, value in fields.items():
        buf += (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"\r\n'
            f'\r\n{value}\r\n'
        ).encode("utf-8")

    content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
    buf += (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="imagedata"; filename="{file_path.name}"\r\n'
        f'Content-Type: {content_type}\r\n'
        f'\r\n'
    ).encode("utf-8")
    buf += file_path.read_bytes()
    buf += f'\r\n--{boundary}--\r\n'.encode("utf-8")
    return bytes(buf), boundary


def main() -> None:
    parser = argparse.ArgumentParser(description="Gyazoに画像をアップロード")
    parser.add_argument("image", help="アップロードする画像ファイルパス")
    parser.add_argument("--title", default=None, help="タイトル（任意）")
    parser.add_argument("--desc", default=None, help="説明文（任意）")
    parser.add_argument("--referer", default=None, dest="referer_url", help="元ページURL（任意）")
    parser.add_argument("--app", default=None, help="アプリ名（任意）")
    parser.add_argument("--team", default=None, help="Teams Gyazoの組織名（例: your-org）")
    args = parser.parse_args()

    org = args.team
    token = require_access_token(org)

    path = Path(args.image)
    if not path.exists():
        print(f"エラー: ファイルが見つかりません: {path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_file():
        print(f"エラー: ファイルではありません: {path}", file=sys.stderr)
        sys.exit(1)

    fields: dict[str, str] = {"access_token": token}
    for key, value in (
        ("title", args.title),
        ("desc", args.desc),
        ("referer_url", args.referer_url),
        ("app", args.app),
    ):
        if value:
            fields[key] = value

    body, boundary = build_multipart(fields, path)
    req = Request(
        UPLOAD_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "User-Agent": USER_AGENT,
        },
    )

    print(f"アップロード中: {path}（{path.stat().st_size:,} bytes）...", file=sys.stderr)
    try:
        with urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")[:300]
        print(f"エラー: アップロード失敗 (HTTP {e.code}): {detail}", file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"エラー: 接続に失敗しました: {e.reason}", file=sys.stderr)
        sys.exit(1)

    permalink = data.get("permalink_url", "-")
    image_id = data.get("image_id", "")
    if image_id and org:
        permalink = f"https://{org}.gyazo.com/{image_id}"

    print("=== アップロード結果 ===")
    print(f"permalink : {permalink}")
    print(f"image_id  : {image_id}")
    print(f"type      : {data.get('type', '-')}")
    print(f"created_at: {data.get('created_at', '-')}")


if __name__ == "__main__":
    main()