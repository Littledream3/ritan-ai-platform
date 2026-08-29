"""
用法:
    python predict.py --image 你的图片路径.jpg
"""
import argparse
import os
import sys
import torch
from PIL import Image
from torchvision import transforms

sys.path.insert(0, os.path.dirname(__file__))
from dataset import METRIC_NAMES
from model import SkinMetricsModel

CKPT_DIR = os.path.join(os.path.dirname(__file__), "checkpoints")
_MEAN, _STD = [0.485, 0.456, 0.406], [0.229, 0.224, 0.225]

# 5种TTA变换
TTA_TRANSFORMS = [
    transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224),
        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD),
    ]),
    transforms.Compose([
        transforms.RandomHorizontalFlip(p=1.0),
        transforms.Resize(256), transforms.CenterCrop(224),
        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD),
    ]),
    transforms.Compose([
        transforms.Resize(256), transforms.RandomResizedCrop(224, scale=(0.88, 1.0)),
        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD),
    ]),
    transforms.Compose([
        transforms.Resize(256), transforms.CenterCrop(224),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD),
    ]),
    transforms.Compose([
        transforms.RandomHorizontalFlip(p=1.0),
        transforms.Resize(256), transforms.RandomResizedCrop(224, scale=(0.88, 1.0)),
        transforms.ToTensor(), transforms.Normalize(_MEAN, _STD),
    ]),
]

METRIC_CN = [
    '痘痘严重度', '黑头', '白头粉刺', '毛孔粗大', '过度出油',
    '皮肤刺激', '皮肤敏感度', '泛红程度', '眼周细纹', '眼部浮肿',
    '黑眼圈', '额头皱纹', '皮肤弹性', '缺水程度', '色斑',
    '痘印', '肤色不均', '雀斑',
]


def predict(image_path, device='cuda'):
    if not os.path.exists(image_path):
        print(f"找不到图片: {image_path}")
        return

    device = torch.device(device if torch.cuda.is_available() else 'cpu')
    img = Image.open(image_path).convert('RGB')

    # 加载全部5个折叠模型
    fold_preds = []
    for fold in range(1, 6):
        ckpt = os.path.join(CKPT_DIR, f"fold{fold}_best.pth")
        if not os.path.exists(ckpt):
            print(f"  警告: fold{fold} 权重不存在，跳过")
            continue
        model = SkinMetricsModel(pretrained=False).to(device)
        model.load_state_dict(torch.load(ckpt, map_location=device))
        model.eval()

        # 每个模型跑5次TTA
        tta_preds = []
        with torch.no_grad():
            for tf in TTA_TRANSFORMS:
                x = tf(img).unsqueeze(0).to(device)
                tta_preds.append(model(x).cpu())
        fold_preds.append(torch.stack(tta_preds).mean(0))

    if not fold_preds:
        print("没有可用的模型权重！")
        return

    # 5模型 × 5TTA 平均
    final_pred = torch.stack(fold_preds).mean(0).squeeze(0)

    print(f"\n图片: {os.path.basename(image_path)}")
    print(f"{'='*48}")
    print(f"  {'指标':<12} {'英文':<22} {'评分':>5}  {'等级'}")
    print(f"  {'-'*46}")
    for i, (cn, en) in enumerate(zip(METRIC_CN, METRIC_NAMES)):
        score = final_pred[i].item()
        if score < 1.0:
            level = "正常"
        elif score < 2.5:
            level = "轻度"
        elif score < 4.0:
            level = "中度"
        else:
            level = "严重"
        print(f"  {cn:<12} {en:<22} {score:>5.2f}  {level}")
    print(f"{'='*48}")
    print(f"  综合平均分: {final_pred.mean().item():.2f} / 5.00")

    return final_pred


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--image', required=True, help='人脸图片路径')
    parser.add_argument('--device', default='cuda')
    args = parser.parse_args()
    predict(args.image, args.device)
