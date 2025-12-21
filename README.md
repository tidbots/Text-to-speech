# Text-to-speech

- テキストファイルの英文を読み上げる
- ファイルには１行に１文が書いてある
- スペースキーを押すと読み上げる
- 「← 」: 前の文
- 「→ 」: 次の文
- 「q」 : 終了

## macOS版（お勧め）
システム設定→アクセシビリティ→読み上げコンテンツから

読み上げ言語を英語あるいは日本語にする

システムの声を選ぶ

```
python3 say-m command.txt
```
```
 python3 say-m command.txt --voice Samantha --rate 180
```
声の種類はシステム設定→アクセシビリティ→読み上げコンテンツ→システムの声で確認



## Ubuntuの場合
espeak-ngを使う（品質は悪いが手軽なので・・・）
```
sudo apt update
sudo apt install -y espeak-ng
python3 say-u command.txt
```
速度変更：
```
python3 say-u command.txt --rate 150
```

## Ubuntuで比較的高品質なTTS（それでもまだmacのsayには敵わない・・・）
Coqui TTS を使う

- GPU環境がインストールされていればGPUを使用
- それ以外の場合CPUモード
- --cpu フラグでCPUモードに固定
  
```
python3 say-TTS.py command.txt
```

起動時に全部生成（おすすめ）
```
python3 say-cache.py command.txt --warmup all
```

CPU固定
```
python3 say-cache.py command.txt --warmup all --cpu
```

キャッシュ先を変える：
```
python3 say-TTS.py command.txt --cache_dir cache_wavs
```

先読みを止める：
```
python3 say-TTS.py command.txt --no_prefetch
```

キャッシュ削除：
```
rm -rf .tts_cache
```

