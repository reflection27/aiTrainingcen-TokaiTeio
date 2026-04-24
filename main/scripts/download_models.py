import os
import sys
import urllib.request
import zipfile

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

pretrained_dir = 'plugins/GPT-SoVITS/GPT_SoVITS/pretrained_models'

# fast_langdetect 缓存目录必须预先存在，否则运行时报 FileNotFoundError
os.makedirs(f'{pretrained_dir}/fast_langdetect', exist_ok=True)

from huggingface_hub import snapshot_download


def dl_file(url, dest_path, desc):
    if os.path.exists(dest_path):
        print(f'  {desc} 已存在，跳过')
        return
    print(f'  正在下载 {desc}...')
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)

    def progress(block_num, block_size, total_size):
        if total_size > 0:
            pct = min(block_num * block_size / total_size * 100, 100)
            print(f'\r    {pct:.1f}%', end='', flush=True)

    urllib.request.urlretrieve(url, dest_path, reporthook=progress)
    print(f'\r  {desc} 下载完成')


def dl_model(repo_id, local_dir, desc):
    if os.path.exists(local_dir) and os.listdir(local_dir):
        print(f'  {desc} 已存在，跳过')
        return
    print(f'  正在下载 {desc}...')
    snapshot_download(
        repo_id=repo_id,
        local_dir=local_dir,
        ignore_patterns=['*.h5', 'flax_model*', 'tf_model*', '*.msgpack']
    )
    print(f'  {desc} 下载完成')


# ── 语言检测模型 ──────────────────────────────────────────────────────────────
dl_file(
    'https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin',
    f'{pretrained_dir}/fast_langdetect/lid.176.bin',
    'fast_langdetect lid.176.bin (~900MB)'
)

# ── HuggingFace 底模 ──────────────────────────────────────────────────────────
dl_model('hfl/chinese-roberta-wwm-ext-large',
         f'{pretrained_dir}/chinese-roberta-wwm-ext-large',
         'chinese-roberta-wwm-ext-large')

dl_model('TencentGameMate/chinese-hubert-base',
         f'{pretrained_dir}/chinese-hubert-base',
         'chinese-hubert-base')

# ── v2Pro 说话人验证模型（使用 v2Pro 角色权重时必须）────────────────────────
dl_file(
    'https://hf-mirror.com/lj1995/GPT-SoVITS/resolve/main/sv/pretrained_eres2netv2w24s4ep4.ckpt',
    f'{pretrained_dir}/sv/pretrained_eres2netv2w24s4ep4.ckpt',
    'sv/pretrained_eres2netv2w24s4ep4.ckpt (~103MB，v2Pro 推理必需)'
)

# ── TokaiTeio 角色权重 ────────────────────────────────────────────────────────
weights_dir = 'character/TokaiTeio/weights'
if (os.path.exists(f'{weights_dir}/TokaiTeio-e15.ckpt') and
        os.path.exists(f'{weights_dir}/TokaiTeio_e20_s220.pth')):
    print('  TokaiTeio 权重已存在，跳过')
else:
    print('  正在下载 TokaiTeio 权重...')
    os.makedirs(weights_dir, exist_ok=True)
    url = 'https://github.com/reflection27/aiTrainingcen-TokaiTeio/releases/download/weights/TokaiTeio-weights.zip'
    zip_path = 'TokaiTeio-weights.zip'
    urllib.request.urlretrieve(url, zip_path)
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(weights_dir)
    os.remove(zip_path)
    print('  TokaiTeio 权重下载完成')
