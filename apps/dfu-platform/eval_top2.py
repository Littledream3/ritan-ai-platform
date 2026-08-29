#!/usr/bin/env python3
"""Quick top-2 accuracy evaluation for finetune calibrated model."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "dfu_update_model", "src"))

import torch
import numpy as np
from torch.utils.data import DataLoader
from tqdm import tqdm

from backend.model_v2 import DFUModel, _build_model, get_device
from dataset import DFUDataset, IDX_TO_LABEL, NUM_CLASSES

CHECKPOINT = "/home/ubuntu/dfu-v2/dfu_update_model/models/corn_v4_finetune/best_model_calibrated.pth"
DATA_DIR = "/home/ubuntu/dfu-v2/dfu_data/processed"
BATCH_SIZE = 64

device = get_device()
print(f"Device: {device}")
print(f"Checkpoint: {CHECKPOINT}")

# Load model
checkpoint = torch.load(CHECKPOINT, map_location="cpu", weights_only=True)
state = checkpoint.get("model_state_dict", checkpoint)
model = _build_model()
model.load_state_dict(state, strict=True)
model.to(device).eval()

temperature = float(checkpoint.get("temperature", 1.0))
print(f"Epoch: {checkpoint.get('epoch')}, Temperature: {temperature:.4f}")

# Data
test_ds = DFUDataset(DATA_DIR, "test", input_size=224, binary=False)
test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False,
                         num_workers=min(4, os.cpu_count() or 4), pin_memory=True)

# Evaluate
all_labels = []
all_probs = []

with torch.inference_mode():
    for images, labels in tqdm(test_loader, desc="Running inference"):
        images = images.to(device)
        binary_logit, ordinal_logits = model(images)
        probs = model.ordinal_head.predict_proba(ordinal_logits / temperature)
        all_probs.append(probs.cpu().numpy())
        all_labels.extend(labels.numpy())

all_probs = np.concatenate(all_probs, axis=0)
all_labels = np.array(all_labels)

# Top-1 accuracy
top1_preds = all_probs.argmax(axis=1)
top1_acc = (top1_preds == all_labels).mean()

# Top-2 accuracy
top2_indices = np.argsort(-all_probs, axis=1)[:, :2]
top2_correct = np.array([all_labels[i] in top2_indices[i] for i in range(len(all_labels))])
top2_acc = top2_correct.mean()

print(f"\n{'='*50}")
print(f"  Test set: {len(all_labels)} samples")
print(f"  Top-1 Accuracy: {top1_acc:.4f} ({top1_acc*100:.2f}%)")
print(f"  Top-2 Accuracy: {top2_acc:.4f} ({top2_acc*100:.2f}%)")
print(f"{'='*50}")

# Per-class top-1 accuracy
print(f"\n  {'Class':<12} {'Top-1':>8} {'Top-2':>8} {'Support':>8}")
print(f"  {'-'*42}")
for i in range(NUM_CLASSES):
    mask = all_labels == i
    if mask.sum() > 0:
        t1 = (top1_preds[mask] == i).mean()
        t2_correct = np.array([all_labels[j] in top2_indices[j] for j in np.where(mask)[0]])
        t2 = t2_correct.mean()
        print(f"  {IDX_TO_LABEL[i]:<12} {t1:>8.4f} {t2:>8.4f} {mask.sum():>8d}")
    else:
        print(f"  {IDX_TO_LABEL[i]:<12} {'—':>8} {'—':>8} {'(empty)':>8}")
