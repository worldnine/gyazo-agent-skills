---
name: gyazo-reader
description: ユーザーがGyazo URLを貼り付けた時に使用する。Gyazo画像をダウンロードしてエージェントが画像として読み込めるようにする。gyazo.com、i.gyazo.com、または {org}.gyazo.com（Gyazo Teams）のURLが会話に含まれている場合にトリガーされる。アクセストークンが設定されていれば撮影アプリ・元ページURL・日時・OCRテキストなどのメタデータも併せて返す。
---

# Gyazo Image Reader

ユーザーがGyazo URLを貼り付けた場合、このスキルを使って画像を取得・表示する。

## トリガー条件

以下のパターンのURLがメッセージに含まれている場合に自動的に使用する:
- `https://gyazo.com/{image_id}` — 個人Gyazo
- `https://i.gyazo.com/{image_id}.png` または `.jpg` — 個人Gyazo（直接画像URL）
- `https://{org}.gyazo.com/{image_id}` — Gyazo Teams（企業アカウント）

## 手順

1. `scripts/fetch_gyazo.py <url>` を実行する（実行方法は「使い方」参照）
2. 標準出力の **1行目に画像ファイルパス**、**2行目以降にメタデータ（KEY: VALUE 形式）** が出力される
3. 画像を視覚認識できるモデルなら、ファイルパスを Read tool で読み込む。**画像を見られないモデルでは読み込む必要はない**
4. メタデータを回答に活かす。**`ocr_text`（画像内テキストのOCR結果）は「画像が見られないモデル」のフォールバック情報**であり、テキスト情報のみ把握できる。ただし: (a) Gyazo公式OCRは**英語は比較的読めるが日本語は精度が低くノイズ混じり**、(b) OCRは**視覚情報（レイアウト・色・デザイン・状態）を伝えない**。視覚的な内容が重要な場合は、視覚対応モデルでの読み取りか、ユーザーへの画像ファイル提示・質問を優先する
5. `source_url` があれば「このスクショの元ページ」を示しているので、必要なら WebFetch で参照しに行ってもよい

## 使い方

`scripts/fetch_gyazo.py` はプラグインルート直下の `scripts/` にある。スキルディレクトリの場所（この SKILL.md を読んだパス）からプラグインルートを特定して実行する。

```bash
# 汎用（プラグインルートを直接指定。ghq 管理下の例）
python3 ~/ghq/github.com/worldnine/gyazo-plugin/plugins/gyazo/scripts/fetch_gyazo.py "https://gyazo.com/abc123def456"
python3 ~/ghq/github.com/worldnine/gyazo-plugin/plugins/gyazo/scripts/fetch_gyazo.py "https://{your-org}.gyazo.com/abc123def456"

# Claude Code のプラグイン環境では ${CLAUDE_PLUGIN_ROOT} がプラグインルートを指す
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/fetch_gyazo.py" "https://gyazo.com/abc123def456"
```

### 出力例

トークン未設定時:
```
/var/folders/.../gyazo/abc123def456.jpg
```

トークン設定時（メタデータ・OCR付き）:
```
/var/folders/.../gyazo/abc123def456.jpg
created_at: 2026-04-27T02:25:07.973Z
type: png
app: Chrome
title: 例: ページタイトル
source_url: https://example.com/some-article
ocr_locale: ja
ocr_text:
（画像内テキストのOCR結果。複数行）
```

メタデータが付いている場合、それらは元のキャプチャ文脈を表す。`ocr_text` は画像内に写っているテキストそのものなので、画像を見られないモデルはこれを読んで内容を把握する。

## 環境変数（メタデータ取得時のみ）

メタデータ取得には Gyazo API を使うためアクセストークンが必要:

- 個人Gyazo: `GYAZO_ACCESS_TOKEN`
- Gyazo Teams: `GYAZO_TEAMS_ACCESS_TOKEN`（未設定時は `GYAZO_ACCESS_TOKEN` にフォールバック）

トークンはGyazoの「設定 → 開発者向け」から発行する。**未設定でも画像取得は壊れずに動く**（メタデータ行が出力されないだけ）。

## 注意事項

- python.org 公式インストーラの Python（3.11 等）では証明書が未リンクのため `SSL: CERTIFICATE_VERIFY_FAILED` で接続失敗することがある。その場合は certifi の CA バンドルを指定して実行する:
  ```bash
  SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())") python3 <プラグインルート>/scripts/fetch_gyazo.py "<url>"
  ```
- 画像はOSの一時ディレクトリ配下に保存される（再起動時に自動削除）
- Gyazoサーバー側のサムネイル（長辺1200px, JPEG）を取得するため、画像を直接貼り付けた場合と同等のトークン消費量
- Python標準ライブラリのみ使用（外部パッケージ依存なし、全OS対応）
