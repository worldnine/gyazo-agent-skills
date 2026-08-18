---
name: gyazo-upload
description: ユーザーが画像ファイルをGyazoにアップロードしたいときに使用する。「この画像をGyazoに上げて」「スクショをアップロードして共有URLが欲しい」などアップロードの指示があった場合にトリガーされる。タイトル・説明・元ページURL・アプリ名を任意で付与できる。アクセストークン必須（GYAZO_ACCESS_TOKEN または GYAZO_TEAMS_ACCESS_TOKEN）。
---

# Gyazo Upload

画像ファイルをGyazoにアップロードし、共有用のpermalink URLを返す。

## トリガー条件

- 「この画像をGyazoに上げて」
- 「スクショをアップロードして共有したい」
- 「GyazoのURLを発行して」

## 手順

1. アップロード対象の画像ファイルパスを特定する（ユーザーの指定、または作業中の生成物）
2. 必要ならメタデータを決める: タイトル（`--title`）、説明（`--desc`）、元ページURL（`--referer`）、アプリ名（`--app`）
3. Teamsアカウントに上げるなら `--team <org>` を付ける（例: your-org）
4. `scripts/upload_gyazo.py <image_file> [オプション]` を実行する（実行方法は「使い方」参照）
5. 出力された **permalink URL をユーザーに提示**する

## 使い方

`scripts/upload_gyazo.py` はプラグインルート直下の `scripts/` にある。スキルディレクトリの場所（この SKILL.md を読んだパス）からプラグインルートを特定して実行する。

```bash
# 汎用（プラグインルートを直接指定。ghq 管理下の例）
python3 ~/ghq/github.com/worldnine/gyazo-plugin/plugins/gyazo/scripts/upload_gyazo.py /tmp/screenshot.png
python3 ~/ghq/github.com/worldnine/gyazo-plugin/plugins/gyazo/scripts/upload_gyazo.py /tmp/screenshot.png --title "会議メモ" --app "pi" --team your-org

# Claude Code のプラグイン環境では ${CLAUDE_PLUGIN_ROOT} がプラグインルートを指す
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/upload_gyazo.py" /tmp/report.png --title "報告書"
```

### 出力例

```
アップロード中: /tmp/screenshot.png（1,234,567 bytes）...
=== アップロード結果 ===
permalink : https://{your-org}.gyazo.com/550de223175eda69927cae900c38b70e
image_id  : 550de223175eda69927cae900c38b70e
type      : png
created_at: 2026-08-18T13:30:00.000Z
```

## メタデータの付け方

- **`--referer`（元ページURL）**: アップロード元のWebページがある場合に指定すると、検索の `url:` フィールドでヒットするようになる
- **`--title`**: 検索の `title:` フィールドでヒットする（スクショ検索の精度が上がる）
- **`--app`**: どのアプリから上げたかの記録

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

- 対応画像形式: PNG / JPEG / GIF など（`imagedata` フィールドで送信、API仕様は公式 gyazo_upload と同一）
- **重複排除**: 同一バイト列の画像を再度アップロードしても新規作成されず、既存の image_id が返る（タイトル等の更新は不可）
- **検索インデックス遅延**: アップロード直後は検索（/api/search）に反映されるまで数分かかることがある。permalink 自体は即時有効（取得・表示はすぐ可能）
- Python標準ライブラリのみ使用（外部パッケージ依存なし、全OS対応）