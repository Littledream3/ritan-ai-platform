"""
用法:
    python predict.py --image 图片路径.jpg
"""
import argparse
import os
import torch
import torch.nn as nn
from PIL import Image
from torchvision import transforms, models

CKPT = os.path.join(os.path.dirname(__file__), "best_model.pth")

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

_model = None

def _load_model():
    global _model
    if _model is not None:
        return _model
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 1)
    m.load_state_dict(torch.load(CKPT, map_location=device))
    m.to(device).eval()
    _model = m
    return _model

_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

def predict(image_path: str) -> float:
    model = _load_model()
    img = Image.open(image_path).convert("RGB")
    x = _transform(img).unsqueeze(0).to(device)
    with torch.no_grad():
        age = model(x).item()
    age = round(age, 1)
    print(f"图片: {os.path.basename(image_path)}")
    print(f"预测年龄: {age:.1f} 岁")
    return age


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True, help="人脸图片路径")
    args = parser.parse_args()
    predict(args.image)
