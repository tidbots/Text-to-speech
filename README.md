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
- Ubuntu 20.04 / 22.04 / 24.04
- Python 3.9〜3.11（3.10 推奨）
- NVIDIA GPU（GPU使用したい場合）
```
sudo apt update
sudo apt install -y python3-venv python3-dev build-essential sox alsa-utils

cd ~/say   # 作業ディレクトリ（例）
python3 -m venv ttsenv
source ttsenv/bin/activate

pip install --upgrade pip
```

CUDA 12.1 の例（最も安定）
```
pip uninstall -y torch torchvision torchaudio
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
  --index-url https://download.pytorch.org/whl/cu121
```
確認
```
python - << 'PY'
import torch
print("torch:", torch.__version__)
print("cuda available:", torch.cuda.is_available())
if torch.cuda.is_available():
    print("gpu:", torch.cuda.get_device_name(0))
print("torch cuda:", torch.version.cuda)
PY
```
cuda available: True → OK 

GPU を使わない場合（CPUのみ）
```
pip uninstall -y torch torchvision torchaudio
pip install torch==2.5.1 torchvision==0.20.1 torchaudio==2.5.1 \
  --index-url https://download.pytorch.org/whl/cpu
```

transformers を固定（XTTS v2 必須）
pip uninstall -y transformers tokenizers
pip install transformers==4.36.2


確認：

python - << 'PY'
from transformers import BeamSearchScorer
print("transformers OK")
PY

Coqui TTS をインストール
pip install TTS


確認：

tts --list_models | grep xtts


出れば OK。
11️⃣ GPU 使用確認（重要）

別ターミナルで：

watch -n 0.5 nvidia-smi


python が 数GB GPUメモリ使用 → 成功

何も使っていない → torch が CPU版

12️⃣ キャッシュについて

WAV は ./.tts_cache_xtts/ に保存

同じ文・同じ話者・同じ言語 → 再生成されない

消したいとき：

rm -rf .tts_cache_xtts


XTTS v2 の話者クローンは、

短い参照音声（speaker_wav）を1つ与えるだけ

で、その声質を真似て英語を読み上げます。

追加学習 ❌ 不要

数秒〜数十秒の音声でOK

話者ID不要（speaker_wav を渡すだけ）


1️⃣ 参照音声（speaker_wav）を用意する
必須条件（重要）
項目	推奨
言語	英語
長さ	6〜15秒
話者	1人のみ
雑音	できるだけ少なく
形式	wav（16kHz or 22kHz, mono 推奨）

👉 長すぎる（1分以上）と 逆に不安定になります。

参照音声の作り方（簡単）
方法A：自分で録音（おすすめ）
arecord -f S16_LE -r 16000 -c 1 myvoice.wav
# 英語で10秒くらい読む
Ctrl+C


内容例：

“Hello. This is a reference voice sample for speech synthesis.”

方法B：既存の音声から切り出す
sox input.wav myvoice.wav trim 0 10

音声を整える（強く推奨）
sox myvoice.wav myvoice_norm.wav gain -n


以降は myvoice_norm.wav を使います。

2️⃣ CLI でまずテスト（超重要）

いきなりUIを使わず、まずCLIで確認してください。

source ttsenv/bin/activate

tts \
  --model_name tts_models/multilingual/multi-dataset/xtts_v2 \
  --text "This is a test of voice cloning. The result should sound similar." \
  --speaker_wav myvoice_norm.wav \
  --language_idx en \
  --out_path test_clone.wav

aplay test_clone.wav

ここで確認すること

声質が参照音声に近い

カタカナ英語になっていない

ノイズや歪みが少ない

❌ 変なら：

参照音声を 短く・クリアに

英語で録り直す






### Coqui TTS を使う

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

### XTTS v2版
- モデル：tts_models/multilingual/multi-dataset/xtts_v2
- GPU 自動使用（--cpu を付けた時だけCPU）
- --warmup all で 全行を .tts_cache_xtts/ に事前生成
- speaker は --speaker_wav（声クローン）優先、無ければ --speaker_idx

内蔵話者（簡単）
```
python3 say-xtts2.py command.txt --warmup all --lang en --speaker_idx "Ana Florence"
```
声クローン

```
python3 say-xtts2.py command.txt --warmup all --lang en --speaker_wav ./myvoice.wav
```



```
