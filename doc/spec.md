# Kindle でハイライトした内容を Notion に取り込む WEB アプリ

[English version](spec.en.md)

## 概要
- Kindleハイライトのサイト（https://read.amazon.co.jp/notebook）にログインし、自分でハイライトした情報を Notion に送る
- 次回実行時は、差分のみ取り込みたい

## アーキテクチャ

```
[Kindle Notebook] → ブックマークレットでハイライト抽出
       ↓ (POST)
[nginx (HTTPS)] → [Python HTTPサーバー] → Notion API
       ↓
[Notion データベース]
```

## ファイル構成

```
highlights/
├── server.py           # メインサーバー（全機能を1ファイルに集約）
├── README.md           # README（EN）
├── README.ja.md        # README（JA）
├── LICENSE             # MIT ライセンス
├── .env.example        # 設定テンプレート
├── .env                # 実際の設定（Git管理外）
├── .gitignore
├── deploy_setup.sh     # Lightsail セットアップスクリプト
├── deploy_guide.md     # デプロイガイド（EN）
├── deploy_guide.ja.md  # デプロイガイド（JA）
├── doc/
│   ├── spec.md         # 仕様書（JA）
│   └── spec.en.md      # 仕様書（EN）
├── data/               # 自動生成（Git管理外）
│   ├── highlights.json
│   ├── sent.json
│   └── config.json
└── static/             # 自動生成（Git管理外）
    ├── index.html
    ├── style.css
    └── app.js
```

## ローカルで使う

### 1. Notion の準備
1. https://www.notion.so/my-integrations で Internal Integration を作成
2. データベースを作成（推奨プロパティ: Name=title, Book=text, Author=text, Location=text, Color=select）
3. データベースに Integration を接続

### 2. サーバー起動
```bash
python server.py
```
→ http://localhost:8000 にアクセス

### 3. ハイライト取得
1. 管理画面で Notion API キーとデータベース ID を設定
2. ブックマークレットをブラウザに登録
3. Kindle ノートブックページで本を選択 → ブックマークレットをクリック
4. 管理画面で確認 → 「Notion に送信」

## Lightsail にデプロイ

[deploy_guide.ja.md](../deploy_guide.ja.md) を参照

## 設定項目（.env）

| 項目 | 説明 | デフォルト |
|---|---|---|
| HOST | バインドアドレス | localhost |
| PORT | ポート番号 | 8000 |
| BASE_URL | 外部公開時のURL | 自動 |
| BASIC_AUTH_USER | Basic認証ユーザー名 | (無効) |
| BASIC_AUTH_PASS | Basic認証パスワード | (無効) |

## 技術構成
- **バックエンド**: Python 標準ライブラリ（http.server, urllib, json）
- **フロントエンド**: HTML/CSS/JavaScript（フレームワークなし）
- **ハイライト取得**: ブックマークレット（DOM 解析）
- **差分管理**: ハイライトのハッシュ値で重複判定（data/sent.json）
- **バックアップ/リストア**: Web UI からデータ・設定の保存と復元（JSON形式）
- **認証**: Basic 認証（外部公開時）
- **デプロイ**: AWS Lightsail + nginx + Let's Encrypt
- **多言語対応**: 英語 / 日本語（UI で切り替え可能）
