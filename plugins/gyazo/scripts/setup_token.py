#!/usr/bin/env python3
"""Gyazoアクセストークンをエージェント設定に保存する対話式セットアップヘルパー

Gyazoはアクセストークンをユーザー自身が設定画面で発行するモデル（無期限・OAuth不要）。
このスクリプトは下記を自動化する:
  1. ブラウザで該当のGyazo設定ページを開く
  2. ユーザーがそこで `Generate` ボタンを押し、表示されたトークンを貼り付ける
  3. 指定された保存先の env フィールドに正しい変数名で保存する

保存先は --target で選択する（既定は claude）:
  --target claude   ~/.claude/settings.json（Claude Code）
  --target pi       ~/.pi/agent/settings.json（pi）
  --target shellrc  シェルrc（--shellrc オプションと同等・後方互換）

使い方:
  python setup_token.py                       # 個人Gyazo → ~/.claude/settings.json
  python setup_token.py --team your-org   # Gyazo Teams
  python setup_token.py --target pi           # pi の設定に保存
  python setup_token.py --shellrc ~/.zshrc    # シェルrc に export 形式で書き出し
"""

import argparse
import getpass
import json
import sys
import webbrowser
from pathlib import Path

CLAUDE_SETTINGS = Path.home() / ".claude" / "settings.json"
PI_SETTINGS = Path.home() / ".pi" / "agent" / "settings.json"


def open_gyazo_settings(team: str | None) -> str:
    if team:
        url = f"https://{team}.gyazo.com/oauth/applications"
    else:
        url = "https://gyazo.com/oauth/applications"
    print(f"ブラウザで Gyazo 設定ページを開きます: {url}")
    print()
    print("画面の指示にしたがってください:")
    if team:
        print(f"  1. 既に共有アプリが登録されていれば、そのアプリ行を開く")
        print(f"     （無ければ管理者に「アプリケーション設定をチームで共有」を有効化してもらう、")
        print(f"      または自分で新規アプリ登録）")
    else:
        print(f"  1. 既存アプリを開く（無ければ「Register a new application」で新規作成）")
        print(f"     Callback URL は使わないので http://localhost などダミーで可")
    print(f"  2. 「Your access token」の Generate ボタンをクリック")
    print(f"  3. 表示されたトークン文字列をコピー")
    print()
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"（ブラウザを自動で開けませんでした: {e}。上記URLを手動で開いてください）")
    return url


def prompt_token() -> str:
    print("発行されたアクセストークンを貼り付けてください")
    print("（入力中の文字は端末に表示されません）:")
    while True:
        token = getpass.getpass("Token: ").strip()
        if not token:
            print("空のトークンは保存できません。やり直してください。")
            continue
        if any(ch.isspace() for ch in token):
            print("トークンに空白文字が含まれています。改行や前後の空白がないか確認してください。")
            continue
        return token


def save_to_settings(settings_path: Path, env_var: str, token: str) -> Path:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings: dict = {}
    if settings_path.exists():
        try:
            settings = json.loads(settings_path.read_text(encoding="utf-8"))
            if not isinstance(settings, dict):
                print(f"警告: {settings_path} の内容がオブジェクトでないため上書きします", file=sys.stderr)
                settings = {}
        except json.JSONDecodeError as e:
            print(f"エラー: {settings_path} のJSON解析に失敗: {e}", file=sys.stderr)
            print("ファイルを手動で修正してから再実行してください", file=sys.stderr)
            sys.exit(1)

    env = settings.setdefault("env", {})
    if not isinstance(env, dict):
        print(f"エラー: {settings_path} の env フィールドがオブジェクトではありません", file=sys.stderr)
        sys.exit(1)
    env[env_var] = token

    settings_path.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return settings_path


def append_to_shellrc(path: Path, env_var: str, token: str) -> Path:
    expanded = path.expanduser().resolve()
    expanded.parent.mkdir(parents=True, exist_ok=True)

    existing_lines: list[str] = []
    if expanded.exists():
        existing_lines = expanded.read_text(encoding="utf-8").splitlines()

    # 同じ env_var の export 行があれば置換、なければ末尾に追加
    new_line = f'export {env_var}="{token}"'
    replaced = False
    out_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith(f"export {env_var}=") or stripped.startswith(f"{env_var}="):
            out_lines.append(new_line)
            replaced = True
        else:
            out_lines.append(line)
    if not replaced:
        if out_lines and out_lines[-1].strip() != "":
            out_lines.append("")
        out_lines.append(f"# Added by gyazo plugin setup_token.py")
        out_lines.append(new_line)

    expanded.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return expanded


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gyazoアクセストークンを取得してエージェント設定に保存する対話式ヘルパー",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--team", default=None, help="Gyazo Teamsの組織名（例: your-org）")
    parser.add_argument(
        "--target",
        choices=["claude", "pi", "shellrc"],
        default="claude",
        help="保存先（既定: claude = ~/.claude/settings.json、pi = ~/.pi/agent/settings.json、shellrc = シェルrc）",
    )
    parser.add_argument(
        "--shellrc",
        default=None,
        help="[後方互換] 保存先をシェルrcにする（--target shellrc と同じ）",
    )
    args = parser.parse_args()

    target = "shellrc" if args.shellrc else args.target
    env_var = "GYAZO_TEAMS_ACCESS_TOKEN" if args.team else "GYAZO_ACCESS_TOKEN"
    print(f"=== Gyazo アクセストークン セットアップ ({'Teams: ' + args.team if args.team else '個人Gyazo'}) ===")
    print(f"環境変数名: {env_var}")
    print()

    open_gyazo_settings(args.team)
    token = prompt_token()

    if target == "shellrc":
        path = append_to_shellrc(Path(args.shellrc), env_var, token)
        print()
        print(f"✓ {path} に export {env_var} を追記しました")
        print(f"  反映には新しいシェルセッションを開いてください")
    else:
        settings_path = PI_SETTINGS if target == "pi" else CLAUDE_SETTINGS
        path = save_to_settings(settings_path, env_var, token)
        print()
        print(f"✓ {path} の env.{env_var} に保存しました")
        app = "Claude Code" if target == "claude" else "pi"
        print(f"  反映には {app} を再起動してください")


if __name__ == "__main__":
    main()
