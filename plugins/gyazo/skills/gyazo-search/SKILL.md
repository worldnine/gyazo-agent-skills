---
name: gyazo-search
description: ユーザーが過去に撮ったGyazoのスクショ・画像をキーワードで探すときに使用する。「あのスクショ」「先週のXXのキャプチャ」「OCRで○○って書いてあった画像」などライブラリ内検索の指示があった場合にトリガーされる。Gyazo公式のサーバーサイド全文検索APIを使用し、OCRテキスト・タイトル・元ページURL・アプリ名・日付範囲で検索できる。アクセストークン必須（GYAZO_ACCESS_TOKEN または GYAZO_TEAMS_ACCESS_TOKEN）。
---

# Gyazo Library Search

ユーザーが自分のGyazoライブラリから特定の画像を探したいときに使う。Gyazo公式の
サーバーサイド全文検索API（`GET /api/search`）を使うため、OCRテキストもGyazo側で
インデックス検索される（クライアント側フィルタリングは不要）。

## トリガー条件

以下のような指示でトリガーする:
- 「Gyazoから○○のスクショ探して」
- 「あの○○のキャプチャ画像どこだっけ」
- 「Gyazoライブラリで『hoge』を含むやつ」
- 「先週撮った○○の画面」（時期＋内容で絞り込み）
- 「OCRに『xxx』って書いてあった画像」

URLが既にメッセージに含まれている場合は **gyazo-reader** スキル側の出番なので、こちらは使わない。

## 手順

1. ユーザーの要望から検索クエリを組み立てる。**時期の指定があれば `since:` / `until:` で絞る**（例: 先週 → `since:YYYY-MM-DD`）。フィールドを特定できるなら `title:` / `app:` / `url:` を使う
2. Teams検索なら `--team <org>` オプションを付ける（例: your-org）。個人Gyazoならオプションなし
3. `scripts/search_gyazo.py "<query>" [--team <org>]` を実行する（実行方法は「使い方」参照）
4. 出力結果から候補をユーザーに提示し、必要なら **gyazo-reader** で実際の画像取得につなげる

## 使い方

`scripts/search_gyazo.py` はプラグインルート直下の `scripts/` にある。スキルディレクトリの場所（この SKILL.md を読んだパス）からプラグインルートを特定して実行する。

```bash
# 汎用（プラグインルートを直接指定。ghq 管理下の例）
python3 ~/ghq/github.com/worldnine/gyazo-plugin/plugins/gyazo/scripts/search_gyazo.py "TAO"
python3 ~/ghq/github.com/worldnine/gyazo-plugin/plugins/gyazo/scripts/search_gyazo.py "TAO" --team your-org

# Claude Code のプラグイン環境では ${CLAUDE_PLUGIN_ROOT} がプラグインルートを指す
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/search_gyazo.py" "invoice" --limit 5
```

### クエリ構文（Gyazo公式サーバーサイド検索）

- プレーンキーワード: `TAO`（OCR・タイトル・alt_text などの全文検索）
- フィールド指定: `title:TAO` / `app:"Google Chrome"` / `url:google.com`
- 日付範囲: `TAO since:2026-03-19 until:2026-03-20`（`since` だけ / `until` だけも可）

### 出力例

```
4件マッチ（上位3件表示）

1. https://{your-org}.gyazo.com/550de223175eda69927cae900c38b70e
   2026-08-18T04:22:40+0000 | app=Ghostty
   ocr: 行 Error: Could not find aerospace binary. Set the path in extension prefe…

2. https://{your-org}.gyazo.com/773ef2ad2030f7f7382afdd72c9b768f
   2026-08-17T06:13:11+0000 | app=Gyazo Menu
   title: ...
   source: https://example.com/some-article
   ocr: …クエリ周辺のOCR本文抜粋…
```

結果は**関連度順**。`ocr:` 行はクエリがOCR本文にヒットした場合の周辺抜粋。タイトル・元URLが取れる場合は併記される。

## 検索のコツ

- **ヒットしないときはクエリを言い換えて複数回試す**: サーバーサイド検索でも表記ゆれ・英日差異で漏れることがある
- **時期を指定する**: 「先週の○○」のような指示には `since:` で絞ると精度が上がる
- **OCRは文脈の手がかり**: GyazoのOCRは精度ばらつきがあるため、OCRのみに頼らずタイトル・元URLと組み合わせて判断する
- **`--max` で件数を増やす**: デフォルト500件まで取得。`--max 1000` で拡大可能

## 環境変数（必須）

- 個人Gyazo: `GYAZO_ACCESS_TOKEN`
- Gyazo Teams: `GYAZO_TEAMS_ACCESS_TOKEN`（無ければ `GYAZO_ACCESS_TOKEN` にフォールバック）

未設定で呼ばれた場合は明確なエラーで終了する。

トークン発行手順:
1. https://gyazo.com/api （Teamsの場合は `https://{org}.gyazo.com/oauth/applications`）でアプリ登録
2. Callback URL は使わないので `http://localhost` などダミーで可
3. Teamsの場合は「アプリケーション設定をチームで共有」にチェックすると、チームメンバーが各自トークンを取れるようになる
4. 登録後の画面に表示される `Your access token` を環境変数に設定

> 手順は公式 MCP サーバー（nota/gyazo-mcp-server）と同じものです。発行したトークンは
> 公式サーバーの `GYAZO_ACCESS_TOKEN` にもそのまま使い回せます。

## 注意事項

- 検索APIのページ上限は100件/ページ、`--max` は総取得件数の上限（デフォルト500）
- Teams検索はアクセストークンにTeams所属が必要（チーム共有アプリのトークンなど）
- Python標準ライブラリのみ使用
