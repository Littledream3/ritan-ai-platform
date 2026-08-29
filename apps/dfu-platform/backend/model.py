# -*- coding: utf-8 -*-
"""Compatibility entry point for the deployed ConvNeXt-Tiny Binary/CORN model.

The production implementation lives in :mod:`model_v2`.  This module remains
only so older scripts importing ``model`` cannot accidentally load the retired
four-class implementation or its obsolete checkpoint.
"""
from __future__ import annotations

try:
    from .model_v2 import (
        BINARY_THRESHOLD,
        CLASS_NAMES,
        INFER_TRANSFORM,
        INPUT_SIZE,
        MODEL_PATH,
        MODEL_VERSION,
        NUM_CLASSES,
        DFUModel,
        _build_model,
        get_device,
        get_model_info,
        load_model,
        predict,
        predict_from_pil,
        validate_clinical_image,
    )
except ImportError:
    from model_v2 import (
        BINARY_THRESHOLD,
        CLASS_NAMES,
        INFER_TRANSFORM,
        INPUT_SIZE,
        MODEL_PATH,
        MODEL_VERSION,
        NUM_CLASSES,
        DFUModel,
        _build_model,
        get_device,
        get_model_info,
        load_model,
        predict,
        predict_from_pil,
        validate_clinical_image,
    )

# Historical names retained for callers that imported them from model.py.
CKPT_PATH = str(MODEL_PATH)
validate_wound_image = validate_clinical_image

__all__ = [
    "BINARY_THRESHOLD",
    "CLASS_NAMES",
    "CKPT_PATH",
    "DFUModel",
    "INFER_TRANSFORM",
    "INPUT_SIZE",
    "MODEL_PATH",
    "MODEL_VERSION",
    "NUM_CLASSES",
    "_build_model",
    "get_device",
    "get_model_info",
    "load_model",
    "predict",
    "predict_from_pil",
    "validate_clinical_image",
    "validate_wound_image",
]
