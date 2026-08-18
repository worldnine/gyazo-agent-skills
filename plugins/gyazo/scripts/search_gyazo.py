#!/usr/bin/env python3
"""Gyazoライブラリを全文検索するスクリプト（要アクセストークン）

Gyazo公式のサーバーサイド全文検索API（GET /api/search）を使用する。
OCRテキスト・タイトル・元URL・アプリ名・alt_text をGyazo側でインデックス検索するため、
全件取得してのクライアント側フィルタリングは不要（旧実装の制約を解消）。

使い方:
  python search_gyazo.py <query> [--team <org>] [--max <N>] [--limit <N>]

引数:
  query        検索クエリ。プレーンなキーワードのほか、フィールド指定と日付範囲が使える:
                 title:cat              タイトル
                 app:"Google Chrome"    アプリ名
                 url:google.com         元ページURL
                 cat since:2024-01-01   開始日
                 until:2024-12-31       終了日
  --team       Teams Gyazoの組織名（例: your-org）。省略時は個人Gyazo
  --max        検索結果の最大取得件数（デフォルト 500）
  --limit      検索結果の最大表示件数（デフォルト 20）

環境変数:
  GYAZO_ACCESS_TOKEN          個人Gyazo（または--team未指定時のフォールバック）
  GYAZO_TEAMS_ACCESS_TOKEN    Teams Gyazo（--team指定時に優先）

出力: 一致した画像を関連度順で表示。各エントリに permalink・日時・アプリ・タイトル・元URL・OCR該当箇所を含む。
"""

import argparse
import re
import sys

from _gyazo_common import api_get, require_access_token

SEARCH_PER_PAGE = 100  # API上限

# クエリ中のフィールド指定・日付演算子（title: / app: / url: / since: / until:）
FIELD_TOKEN = re.compile(r'(?:title|app|url|since|until):(?:"[^"]*"|\S+)', re.IGNORECASE)


def plain_keywords(query: str) -> list[str]:
    """フィールド構文を除いたプレーンなキーワード一覧（OCR抜粋の照合用・小文字）"""
    rest = FIELD_TOKEN.sub(" ", query)
    return [w.lower() for w in rest.split() if w]


def search_page(query: str, *, org: str | None, token: str, page: int) -> list[dict]:
    result = api_get(
        "/api/search",
        org=org,
        token=token,
        params={"query": query, "page": page, "per": SEARCH_PER_PAGE},
    )
    if not isinstance(result, list):
        return []
    return result


def ocr_snippet(text: str, keywords: list[str], *, ctx: int = 40) -> str:
    """OCR本文の中でキーワード周辺を抜粋（最初にヒットしたキーワードを使用）。"""
    if not text or not keywords:
        return ""
    text_lc = text.lower()
    for kw in keywords:
        idx = text_lc.find(kw)
        if idx < 0:
            continue
        start = max(0, idx - ctx)
        end = min(len(text), idx + len(kw) + ctx)
        snippet = text[start:end].replace("\n", " ").strip()
        if start > 0:
            snippet = "…" + snippet
        if end < len(text):
            snippet = snippet + "…"
        return snippet
    return ""


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gyazoライブラリを全文検索（サーバーサイド・OCR込み）"
    )
    parser.add_argument("query", help="検索キーワード（title:/app:/url: 指定や since:/until: の日付範囲も可）")
    parser.add_argument("--team", default=None, help="Teams Gyazoの組織名（your-org など）")
    parser.add_argument("--max", type=int, default=500, dest="max_total", help="検索結果の最大取得件数（デフォルト500）")
    parser.add_argument("--limit", type=int, default=20, help="表示する最大件数（デフォルト20）")
    args = parser.parse_args()

    org = args.team
    token = require_access_token(org)

    if not args.query.strip():
        print("エラー: 空のクエリは指定できません", file=sys.stderr)
        sys.exit(1)

    # サーバーサイド全文検索でページング取得
    results: list[dict] = []
    page = 1
    while len(results) < args.max_total:
        batch = search_page(args.query, org=org, token=token, page=page)
        if not batch:
            break
        results.extend(batch)
        if len(batch) < SEARCH_PER_PAGE:
            break
        page += 1
    results = results[: args.max_total]

    if not results:
        print(f"『{args.query}』にマッチする画像はありませんでした")
        return

    # len(results) はサーバー総ヒット数ではなく取得件数（--max が上限）
    print(f"{len(results)}件取得（上位{min(args.limit, len(results))}件表示、取得上限 --max={args.max_total}）")
    print()
    keywords = plain_keywords(args.query)
    for i, item in enumerate(results[: args.limit], start=1):
        meta = item.get("metadata") or {}
        ocr = item.get("ocr") or {}
        # Teams画像はAPIが返す permalink_url が gyazo.com ドメインで実際は404になるため
        # image_id と --team から正しいホストでURLを組み直す
        image_id = item.get("image_id") or ""
        if image_id and org:
            permalink = f"https://{org}.gyazo.com/{image_id}"
        elif image_id:
            permalink = f"https://gyazo.com/{image_id}"
        else:
            permalink = item.get("permalink_url") or item.get("url") or ""
        created = item.get("created_at") or ""
        app = meta.get("app") or ""
        title = meta.get("title") or ""
        source_url = meta.get("url") or ""

        print(f"{i}. {permalink}")
        line2_parts = []
        if created:
            line2_parts.append(created)
        if app:
            line2_parts.append(f"app={app}")
        print("   " + " | ".join(line2_parts))
        if title:
            print(f"   title: {title}")
        if source_url:
            print(f"   source: {source_url}")
        snippet = ocr_snippet(ocr.get("description") or "", keywords)
        if snippet:
            print(f"   ocr: {snippet}")
        print()


if __name__ == "__main__":
    main()
