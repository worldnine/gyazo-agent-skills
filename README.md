# gyazo-agent-skills

Gyazo のエージェント連携プラグイン（Agent Skills 標準 / Agent Plugins 1.0 対応）。

> 非公式（unofficial）のコミュニティプラグインです。Gyazo は Nota, Inc. の商標です。
> 公式の連携は [nota/gyazo-mcp-server](https://github.com/nota/gyazo-mcp-server) を参照してください。

- **gyazo-reader**: Gyazo URL を貼ると画像を取得し、メタデータ（撮影アプリ・元URL・日時・OCRテキスト）を返す
- **gyazo-search**: Gyazo公式のサーバーサイド全文検索（OCR・タイトル・元URL・アプリ・日付範囲）
- **gyazo-upload**: 画像をアップロードして共有 URL を発行（タイトル・説明・元URL・アプリ名を付与可）

**特徴**
- **Gyazo Teams 対応**（`{org}.gyazo.com` URL の組み立て・`--team` 指定）
- **MCP 不要**: Agent Skills 標準（agentskills.io）なので Claude Code / pi / Hermes / Codex 等、SKILL.md を読めるエージェントならどこでも動く
- **OCR テキスト出力**: 画像非対応モデルでもスクショのテキスト内容を把握できる（フォールバック。視覚情報は視覚対応モデルで）
- Python 標準ライブラリのみ（依存なし・全OS対応）

## インストール

### Claude Code

```
/plugin marketplace add worldnine/gyazo-agent-skills
/plugin install gyazo
```

### pi / Hermes など（Claude Code 以外）

まずリポジトリを任意の場所に clone します:

```bash
git clone https://github.com/worldnine/gyazo-agent-skills.git
# ghq ユーザーなら: ghq get worldnine/gyazo-agent-skills
```

以下、clone 先を `<REPO>` と表記します（例: `~/gyazo-agent-skills`）。

**pi**: `~/.pi/agent/settings.json` の `skills` 配列に追加:

```json
{
  "skills": [
    "<REPO>/plugins/gyazo/skills/gyazo-reader",
    "<REPO>/plugins/gyazo/skills/gyazo-search",
    "<REPO>/plugins/gyazo/skills/gyazo-upload"
  ]
}
```

**Hermes**: `~/.hermes/config.yaml` の `skills.external_dirs` に追加:

```yaml
skills:
  external_dirs:
    - <REPO>/plugins/gyazo/skills
```

> プラグインのバージョンは `.claude-plugin/marketplace.json` の `plugins[].version` が正です
> （`metadata.version` はマーケットプレイス定義自体のバージョン）。

## セットアップ（アクセストークン）

Gyazo の開発者ページでパーソナルアクセストークン（PAT）を発行して環境変数に設定します。
手順は公式 MCP サーバー（[nota/gyazo-mcp-server](https://github.com/nota/gyazo-mcp-server)）と同じです。
発行したトークンは公式サーバーの `GYAZO_ACCESS_TOKEN` にもそのまま使い回せます。

- 個人Gyazo: `GYAZO_ACCESS_TOKEN`
- Gyazo Teams: `GYAZO_TEAMS_ACCESS_TOKEN`（未設定時は `GYAZO_ACCESS_TOKEN` にフォールバック）

トークン発行は `plugins/gyazo/scripts/setup_token.py` の対話ヘルパーが案内します
（`--team` で Teams 対応、`--target claude|pi|shellrc` で保存先選択）。

詳細は [plugins/gyazo/README.md](plugins/gyazo/README.md) を参照してください。

## ライセンス

MIT