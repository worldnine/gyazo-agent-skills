# gyazo

Gyazoの画像取得・ライブラリ検索・アップロードを行うマルチエージェント向けプラグイン（Claude Code / pi / Hermes 対応）。

## 含まれるスキル

| スキル | トリガー | トークン |
|---|---|---|
| `gyazo-reader` | Gyazo URL（`gyazo.com/...`、`{org}.gyazo.com/...`）が会話に含まれる | 不要（あれば撮影アプリ・元URL・日時等のメタデータも付加） |
| `gyazo-search` | 「あのスクショ探して」「Gyazoライブラリで○○」など（Gyazo公式のサーバーサイド全文検索、OCR・タイトル・元URL・アプリ・日付範囲） | **必須** |
| `gyazo-upload` | 「この画像をGyazoに上げて」など（タイトル・説明・元URL・アプリ名を付与可） | **必須** |

## インストール

### Claude Code

```
/plugin marketplace add worldnine/gyazo-agent-skills
/plugin install gyazo
```

### pi / Hermes など他エージェント（マルチ環境対応）

このプラグインは Claude Code 専用ではなく、**Agent Skills 標準（agentskills.io）に準拠**しています。
プラグインルート直下の `plugin.json` は Agent Plugins 1.0 形式です。
スキルは `skills/gyazo-reader`、`skills/gyazo-search`、`skills/gyazo-upload` の3つです。

まずリポジトリを任意の場所に clone します（以下、clone 先を `<REPO>` と表記）:

```bash
git clone https://github.com/worldnine/gyazo-agent-skills.git
```

**pi**: `~/.pi/agent/settings.json` の `skills` 配列にスキルディレクトリを追加:

```json
{
  "skills": [
    "<REPO>/plugins/gyazo/skills/gyazo-reader",
    "<REPO>/plugins/gyazo/skills/gyazo-search",
    "<REPO>/plugins/gyazo/skills/gyazo-upload"
  ]
}
```

**Hermes**: `~/.hermes/config.yaml` の `skills.external_dirs` にスキル親ディレクトリを追加:

```yaml
skills:
  external_dirs:
    - <REPO>/plugins/gyazo/skills
```

**トークン**: pi / Hermes はシェルの環境変数（`GYAZO_TEAMS_ACCESS_TOKEN` など）をそのまま引き継ぎます。
setup_token.py の `--target pi` で pi の設定ファイルに直接保存することもできます。

## セットアップ（メタデータ取得・検索を使う場合）

### 1. アクセストークンを発行

**この手順は公式の Gyazo MCP サーバー（[nota/gyazo-mcp-server](https://github.com/nota/gyazo-mcp-server)）と同じです**。
Gyazoはユーザー自身が開発者ページで無期限のパーソナルアクセストークン（PAT）を発行するモデルで、OAuthログインはありません。
公式READMEの手順（[Prerequisites](https://github.com/nota/gyazo-mcp-server#readme)）も参考になります。

**Gyazo Teams（your-org）の場合:**

`https://{your-org}.gyazo.com/oauth/applications` を開き、`claude-plugin` アプリの行で `Generate` ボタンをクリック。表示されたトークンをコピー。

> 共有アプリが見つからない場合は管理者に「アプリケーション設定をチームで共有」を有効にしてもらうか、自分でアプリを新規登録してください。

**個人Gyazoの場合:**

`https://gyazo.com/api`（または `https://gyazo.com/oauth/applications`）で自分用にアプリを新規登録（Callback URLは使わないので `http://localhost` などダミーで可）→ `Generate` でトークン発行。

> **トークンは共通で使い回せます**: 発行したトークンは当プラグイン（`GYAZO_TEAMS_ACCESS_TOKEN` / `GYAZO_ACCESS_TOKEN`）でも、公式 MCP サーバーの `GYAZO_ACCESS_TOKEN` でも同じものが使えます（APIは `api.gyazo.com` 統一で、トークンに個人/Teamsの所属が紐付くだけです）。

### 2. トークンをClaude Codeに設定

3つの方法があります。お好みで:

#### 方法A: 同梱の対話ヘルパーを使う（推奨）

```bash
# Gyazo Teams
python ~/.claude/plugins/<marketplace>/gyazo/scripts/setup_token.py --team your-org

# 個人Gyazo
python ~/.claude/plugins/<marketplace>/gyazo/scripts/setup_token.py
```

スクリプトがブラウザでGyazo設定ページを自動オープン → `Generate` 押下 → 表示されたトークンを貼り付け → `~/.claude/settings.json` の `env` フィールドに正しい変数名で自動保存。

シェルrc（`~/.zshrc` など）に export 形式で書き出したい場合は:

```bash
python ~/.claude/plugins/<marketplace>/gyazo/scripts/setup_token.py --team your-org --shellrc ~/.zshrc
```

pi の設定（`~/.pi/agent/settings.json`）に保存したい場合は:

```bash
python <プラグインルート>/scripts/setup_token.py --team your-org --target pi
```

#### 方法B: Claudeに頼む

Claude Codeで次のように頼むと、`~/.claude/settings.json` の `env` フィールドに書き込んでくれます:

```
GYAZO_TEAMS_ACCESS_TOKEN=<コピーしたトークン> を ~/.claude/settings.json の env に追加して
```

#### 方法C: 手動で settings.json を編集

`~/.claude/settings.json` を開いて:

```json
{
  "env": {
    "GYAZO_TEAMS_ACCESS_TOKEN": "発行されたトークン"
  }
}
```

個人Gyazoの場合は `GYAZO_ACCESS_TOKEN` という環境変数名に。両方使う人は両方設定してください。

### 3. Claude Code を再起動

設定の反映には再起動が必要です。

## 使い方

### 画像を見る

Gyazo URLを貼るだけ:

```
https://{your-org}.gyazo.com/abc123def456
```

→ プラグインが自動で画像を取得し、エージェントが画像を視覚的に理解します（画像を見られないモデルでも、トークン設定済みなら `ocr_text` メタデータで内容を把握できます）。
トークンを設定済みなら撮影アプリ・元ページURL・日時・OCRテキストも併せて文脈に取り込まれます。

### アップロード

画像ファイルを指定して:

```
このスクショをGyazoに上げて（タイトル: 会議メモ、アプリ: pi）
```

→ `gyazo-upload` がアップロードし、共有用permalinkを返します。参照元URL・説明も任意で付与できます。

### ライブラリを検索

```
Gyazoから「TAO」を含むスクショ探して
```

→ `gyazo-search` がライブラリを横断検索し、マッチした画像のURL一覧を返します。
そこから気になる1枚をClaudeに渡せば `gyazo-reader` が中身を表示してくれます。

## トークンを設定しないと?

`gyazo-reader` は**トークン無しでも動作**します（画像取得のみ、メタデータなし）。
`gyazo-search` はAPI叩くため**トークン必須**で、未設定時は明確なエラーで終了します。

## 環境変数まとめ

| 変数 | 用途 |
|---|---|
| `GYAZO_ACCESS_TOKEN` | 個人Gyazo |
| `GYAZO_TEAMS_ACCESS_TOKEN` | Gyazo Teams（無ければ `GYAZO_ACCESS_TOKEN` にフォールバック） |

## ライセンス

MIT
