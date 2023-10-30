# Misskey Trigram Bot

Misskey で動く日本語おしゃべり Bot です。
タイムラインのノートの内容を学習して、学習した内容を元に発言します。

## Dependencies

- Python 3.11 or above
- Redis

## Setup

### Install dependencies

```bash
pip3 install -r requirements.txt
```

### Get API Token

Misskey > 設定 > API から`アクセストークンの発行`を選択します。以下の権限を付与します。

- `ノートを作成・削除する`

## Run

```bash
# 利用する環境に応じて、以下の環境変数を適切に設定してください
export SERVER_URL="wss://misskey.io/streaming"
export API_TOKEN="上記で取得したアクセストークン"

export REDIS_HOST="localhost"
export REDIS_DB="0"

export SPEAK_INTERVAL="3600"

python3 main.py
```
