# -*- coding: utf-8 -*-
"""Production adapter for the ConvNeXt-Tiny + binary/CORN DFU model."""
from __future__ import annotations

import io
import os
from pathlib import Path
from threading import Lock

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from torchvision import models, transforms


MODEL_VERSION = "convnext-tiny-corn-v4-finetune-calibrated"
MODEL_PATH = Path(
    os.getenv(
        "DFU_MODEL_V2_PATH",
        "/home/ubuntu/dfu-v2/dfu_update_model/models/corn_v4_finetune/best_model_calibrated.pth",
    )
)
BINARY_THRESHOLD = float(os.getenv("DFU_MODEL_V2_BINARY_THRESHOLD", "0.5"))
INPUT_SIZE = 224
CLASS_NAMES = [
    "Normal",
    "Grade 0",
    "Grade 1",
    "Grade 2",
    "Grade 3",
    "Grade 4",
    "Grade 5",
]
NUM_CLASSES = len(CLASS_NAMES)

_MEAN = [0.485, 0.456, 0.406]
_STD = [0.229, 0.224, 0.225]
INFER_TRANSFORM = transforms.Compose(
    [
        transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(_MEAN, _STD),
    ]
)

_DEVICE: torch.device | None = None
_MODEL: "DFUModel | None" = None
_MODEL_INFO: dict | None = None
_LOAD_LOCK = Lock()


class CORNHead(nn.Module):
    """CORN head with shared weights and monotonic biases."""

    def __init__(self, in_features: int, num_classes: int = NUM_CLASSES):
        super().__init__()
        self.num_classes = num_classes
        self.num_tasks = num_classes - 1
        self.linear = nn.Linear(in_features, 1)
        self.base_bias = nn.Parameter(torch.zeros(1))
        self.bias_deltas = nn.Parameter(torch.zeros(self.num_tasks - 1))

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        shared = self.linear(features)
        biases = [self.base_bias]
        for delta in self.bias_deltas:
            biases.append(biases[-1] - F.softplus(delta))
        return shared + torch.cat(biases)

    def predict_proba(self, logits: torch.Tensor) -> torch.Tensor:
        thresholds = torch.sigmoid(logits)
        probabilities = [1 - thresholds[:, 0]]
        probabilities.extend(
            thresholds[:, index - 1] - thresholds[:, index]
            for index in range(1, self.num_classes - 1)
        )
        probabilities.append(thresholds[:, -1])
        result = torch.stack(probabilities, dim=1).clamp_min(0)
        return result / result.sum(dim=1, keepdim=True).clamp_min(1e-8)


class BinaryHead(nn.Module):
    def __init__(self, in_features: int, dropout: float = 0.5):
        super().__init__()
        self.fc = nn.Sequential(nn.Dropout(dropout), nn.Linear(in_features, 1))

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.fc(features).squeeze(-1)


class DFUModel(nn.Module):
    def __init__(self, backbone: nn.Module, in_features: int):
        super().__init__()
        self.backbone = backbone
        self.binary_head = BinaryHead(in_features)
        self.ordinal_head = CORNHead(in_features)

    def forward(self, images: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        features = self.backbone(images)
        return self.binary_head(features), self.ordinal_head(features)


def _build_model() -> DFUModel:
    backbone = models.convnext_tiny(weights=None)
    in_features = backbone.classifier[2].in_features
    backbone.classifier = nn.Flatten(start_dim=1)
    return DFUModel(backbone, in_features)


def get_device() -> torch.device:
    global _DEVICE
    if _DEVICE is None:
        _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _DEVICE


def load_model() -> DFUModel:
    global _MODEL, _MODEL_INFO
    if _MODEL is not None:
        return _MODEL
    with _LOAD_LOCK:
        if _MODEL is not None:
            return _MODEL
        if not MODEL_PATH.is_file():
            raise FileNotFoundError(f"新模型权重不存在: {MODEL_PATH}")
        device = get_device()
        checkpoint = torch.load(MODEL_PATH, map_location="cpu", weights_only=True)
        state = checkpoint.get("model_state_dict", checkpoint)
        model = _build_model()
        model.load_state_dict(state, strict=True)
        model.to(device).eval()
        temperature = float(checkpoint.get("temperature", 1.0))
        _MODEL = model
        _MODEL_INFO = {
            "model_version": MODEL_VERSION,
            "architecture": "ConvNeXt-Tiny + BinaryHead + CORN",
            "classes": CLASS_NAMES,
            "checkpoint": str(MODEL_PATH),
            "checkpoint_epoch": checkpoint.get("epoch"),
            "temperature": temperature,
            "binary_threshold": BINARY_THRESHOLD,
            "validation": {
                "accuracy": checkpoint.get("val_acc"),
                "macro_f1": checkpoint.get("val_f1"),
                "quadratic_kappa": checkpoint.get("val_kappa"),
                "binary_accuracy": checkpoint.get("val_bin_acc"),
                "binary_f1": checkpoint.get("val_bin_f1"),
            },
            "device": str(device),
        }
        print(
            "[DFU Model V2] loaded "
            f"version={MODEL_VERSION}, epoch={checkpoint.get('epoch')}, "
            f"temperature={temperature:.4f}, device={device}"
        )
    return _MODEL


def get_model_info(load: bool = True) -> dict:
    if load:
        load_model()
    return dict(_MODEL_INFO or {"model_version": MODEL_VERSION, "checkpoint": str(MODEL_PATH)})


def validate_clinical_image(image: Image.Image) -> dict:
    """Check technical image quality without rejecting Normal or Wagner 0 feet."""
    rgb = image.convert("RGB")
    if rgb.width < 320 or rgb.height < 320:
        return {"valid": False, "reason": "图片宽高不能低于320像素"}
    if rgb.width * rgb.height > 25_000_000:
        return {"valid": False, "reason": "图片像素尺寸过大，请压缩后重试"}

    sample = rgb.copy()
    sample.thumbnail((512, 512))
    array = np.asarray(sample, dtype=np.float32)
    gray = array.mean(axis=2)
    variance = float(gray.var())
    brightness = float(gray.mean())
    texture_std = float(array.std())

    reasons = []
    if variance < 20:
        reasons.append("图片内容过于单一或严重失焦")
    if brightness < 18:
        reasons.append("图片过暗")
    if brightness > 242:
        reasons.append("图片过曝")
    if texture_std < 8:
        reasons.append("图片缺少可辨识纹理")
    if reasons:
        return {
            "valid": False,
            "reason": "；".join(dict.fromkeys(reasons)),
            "brightness": round(brightness, 2),
            "variance": round(variance, 2),
        }
    return {
        "valid": True,
        "brightness": round(brightness, 2),
        "variance": round(variance, 2),
    }


def _combine_heads(
    ordinal_probabilities: torch.Tensor, binary_probability: float
) -> torch.Tensor:
    """Combine binary screening mass with conditional seven-class CORN probabilities."""
    probabilities = ordinal_probabilities.clone()
    benign = probabilities[:2]
    ulcer = probabilities[2:]
    benign = benign / benign.sum().clamp_min(1e-8)
    ulcer = ulcer / ulcer.sum().clamp_min(1e-8)
    probabilities[:2] = benign * (1.0 - binary_probability)
    probabilities[2:] = ulcer * binary_probability
    return probabilities / probabilities.sum().clamp_min(1e-8)


def predict_from_pil(image: Image.Image) -> dict:
    quality = validate_clinical_image(image)
    if not quality["valid"]:
        return {"status": "rejected", **quality}

    model = load_model()
    info = get_model_info(load=False)
    device = get_device()
    tensor = INFER_TRANSFORM(image.convert("RGB")).unsqueeze(0).to(device)

    with torch.inference_mode():
        binary_logit, ordinal_logits = model(tensor)
        binary_probability = float(torch.sigmoid(binary_logit).item())
        temperature = max(float(info.get("temperature", 1.0)), 1e-6)
        ordinal_probabilities = model.ordinal_head.predict_proba(
            ordinal_logits / temperature
        ).squeeze(0)
        probabilities = _combine_heads(ordinal_probabilities, binary_probability)

    if binary_probability >= BINARY_THRESHOLD:
        branch_offset = 2
        grade_index = branch_offset + int(torch.argmax(probabilities[2:]).item())
    else:
        grade_index = int(torch.argmax(probabilities[:2]).item())

    sorted_probabilities, sorted_indices = torch.sort(probabilities, descending=True)
    confidence = float(probabilities[grade_index].item())
    secondary_index = int(sorted_indices[0].item())
    if secondary_index == grade_index:
        secondary_index = int(sorted_indices[1].item())
        secondary_probability = float(sorted_probabilities[1].item())
    else:
        secondary_probability = float(sorted_probabilities[0].item())
    is_borderline = abs(confidence - secondary_probability) < 0.15

    return {
        "status": "ok",
        "grade": CLASS_NAMES[grade_index],
        "grade_index": grade_index,
        "confidence": round(confidence, 4),
        "probabilities": [round(float(value), 4) for value in probabilities.cpu()],
        "is_borderline": is_borderline,
        "secondary_grade": CLASS_NAMES[secondary_index] if is_borderline else None,
        "secondary_confidence": round(secondary_probability, 4) if is_borderline else None,
        "binary_probability_ulcer": round(binary_probability, 4),
        "is_ulcer": binary_probability >= BINARY_THRESHOLD,
        "ordinal_probabilities": [
            round(float(value), 4) for value in ordinal_probabilities.cpu()
        ],
        "model_version": MODEL_VERSION,
        "quality": quality,
    }


def predict(image_path: str) -> dict:
    with Image.open(image_path) as image:
        return predict_from_pil(image)
