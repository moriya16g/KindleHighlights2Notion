# Kindle Highlights → Notion

[English README](README.md)

Kindle のハイライトを Notion データベースに送信する Web アプリです。

## 仕組み

```
[Kindle Notebook ページ] → ブックマークレットで DOM からハイライトを抽出
         ↓ (POST)
[Python HTTP サーバー]    → Notion API にプロキシ送信
         ↓
[Notion データベース]
```

1. [Kindle ノートブック](https://read.amazon.co.jp/notebook) に通常通りログイン
2. ブックマークレットをクリックしてハイライトを抽出
3. Web UI で確認し、Notion に送信
4. 次回実行時は送信済みハイライトを自動スキップ（差分取り込み）
5. ハイライト・設定・.env を Web UI からバックアップ・リストア

## クイックスタート

```bash
# リポジトリをクローン
git clone https://github.com/<your-username>/kindle-highlights-notion.git
cd kindle-highlights-notion

# (任意) .env ファイルをテンプレートから作成
cp .env.example .env

# サーバーを起動
python server.py
```

ブラウザで http://localhost:8000 を開きます。

## セットアップ

### 1. Notion の準備

1. [Notion Integrations](https://www.notion.so/my-integrations) で Internal Integration を作成
2. 以下のプロパティを持つデータベースを作成（推奨）：

   | プロパティ | 型 |
   |-----------|------|
   | Name | Title |
   | Book | Text |
   | Author | Text |
   | Location | Text |
   | Color | Select |

3. データベースに Integration を接続（Share → Invite）

### 2. アプリの設定

1. http://localhost:8000 を開く
2. Notion API キーとデータベース ID を入力
3. 「接続テスト」で動作確認

### 3. ハイライトの取得

1. [Kindle ノートブック](https://read.amazon.co.jp/notebook) を開き対象の本を選択
2. ブックマークレット「📖 Kindle→取得」をクリック
3. アプリに戻って確認 → Notion に送信

### 4. バックアップ / リストア

Web UI の下部に **バックアップ / リストア** セクションがあります。

- **バックアップをダウンロード** — ハイライト・送信履歴・Notion 設定・`.env` を1つの JSON としてダウンロード
- **バックアップからリストア** — 以前ダウンロードした JSON をアップロードしてデータを復元

サーバー移行やデータ復旧時に便利です。

## 設定（.env）

| 項目 | 説明 | デフォルト |
|------|------|-----------|
| `HOST` | バインドアドレス | `localhost` |
| `PORT` | ポート番号 | `8000` |
| `BASE_URL` | 外部公開時の URL（ブックマークレット用） | 自動 |
| `BASIC_AUTH_USER` | Basic 認証ユーザー名 | (無効) |
| `BASIC_AUTH_PASS` | Basic 認証パスワード | (無効) |

## AWS Lightsail にデプロイ

[deploy_guide.ja.md](deploy_guide.ja.md) を参照してください。

## 技術構成

- **バックエンド**: Python 標準ライブラリのみ（`http.server`, `urllib`, `json`）
- **フロントエンド**: HTML/CSS/JavaScript（フレームワークなし）
- **ハイライト取得**: ブックマークレット（DOM 解析）
- **差分管理**: ハイライトの SHA256 ハッシュで重複判定
- **バックアップ/リストア**: Web UI からデータと設定の保存・復元
- **多言語対応**: 英語 / 日本語（UI で切り替え可能）

## プロジェクト構成

```
├── server.py           # メインサーバー（オールインワン）
├── .env.example        # 設定テンプレート
├── .env                # 個人設定（Git 管理外）
├── .gitignore
├── LICENSE             # MIT ライセンス
├── deploy_setup.sh     # Lightsail セットアップスクリプト
├── deploy_guide.md     # デプロイガイド（EN）
├── deploy_guide.ja.md  # デプロイガイド（JA）
├── doc/
│   ├── spec.md         # 仕様書（JA）
│   └── spec.en.md      # 仕様書（EN）
├── data/               # 自動生成（Git 管理外）
└── static/             # 自動生成（Git 管理外）
```

## ライセンス

MIT
