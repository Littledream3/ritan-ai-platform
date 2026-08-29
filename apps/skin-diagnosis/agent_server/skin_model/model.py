import os
import torch
import torch.nn as nn
import timm


class SkinMetricsModel(nn.Module):
    def __init__(self, num_metrics=18, pretrained=True, freeze_backbone=True,
                 backbone_ckpt=None):
        super().__init__()
        self.backbone = timm.create_model(
            'efficientnet_b0', pretrained=pretrained, num_classes=0
        )
        # 加载皮肤分类预训练骨干（阶段一产物）
        if backbone_ckpt and os.path.exists(backbone_ckpt):
            self.backbone.load_state_dict(
                torch.load(backbone_ckpt, map_location='cpu')
            )
            print(f"  骨干权重加载自: {backbone_ckpt}")

        feat_dim = self.backbone.num_features  # 1280

        if freeze_backbone:
            for p in self.backbone.parameters():
                p.requires_grad = False
            # Unfreeze last two blocks for slight fine-tuning
            for p in self.backbone.blocks[-2:].parameters():
                p.requires_grad = True

        self.head = nn.Sequential(
            nn.Linear(feat_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(512, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_metrics),
            # 不用 Sigmoid，让线性层自由输出，推理时 clamp 到 [0,5]
        )

    def forward(self, x):
        feat = self.backbone(x)
        out = self.head(feat)
        return out.clamp(0.0, 5.0)
