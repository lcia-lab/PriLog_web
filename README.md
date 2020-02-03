# PriLog_web
Thanks to Neilsaw

# Description
Fork元をカスタマイズして自サーバー(Google Cloud Platform)上で動作させることを目的とする

# How To Use
※Google Cloud Platformのアカウントがあるかつ、課金が有効となっていることを前提条件とする

事前準備
Cloud SDKをインストールする
https://cloud.google.com/sdk/docs/?hl=ja

## GAE上で動かす
① gcloud app deploy
② y を入力
③ deploy完了まで待機

## Cloud Functions上で動かす
① gcloud functions deploy remoteAnalyze --runtime python37 --trigger-http --timeout 300 --region asia-northeast1 --memory 2048MB
② y を入力
③ deploy完了まで待機

# Note
・GAEで動かす場合、デフォルトの設定だとインスタンスがStandard F4_HIGHMEMとなっているため、無料インスタンス時間28時間 / 6 (6倍の費用のため) = 約4.5時間分のインスタンス時間以降は課金要素となります。専用サーバーとして動かすならばインスタンス時間はそこまでかからないので十分だと思いますが、長時間動かすことを目的とするなら環境スペックを下げることをお勧めします。

・Cloud Functionsもリクエスト回数により、課金要素が発生する恐れがあるため注意してください。

