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


