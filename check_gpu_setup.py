#!/usr/bin/env python3
"""Check GPU setup and install EasyOCR if needed."""
import sys
import subprocess

# Check GPU
try:
    import torch
    cuda_available = torch.cuda.is_available()
    if cuda_available:
        device_name = torch.cuda.get_device_name(0)
        print(f"[OK] GPU detected: {device_name}")
    else:
        print("[X] CUDA not available")
        sys.exit(1)
except ImportError:
    print("[X] PyTorch not installed")
    sys.exit(1)

# Check EasyOCR
try:
    import easyocr
    print("[OK] EasyOCR already installed")
except ImportError:
    print("[X] EasyOCR not installed - installing now...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "easyocr"])
        print("[OK] EasyOCR installed successfully")
    except Exception as e:
        print(f"[X] Failed to install EasyOCR: {e}")
        sys.exit(1)

print("\n[OK] GPU setup complete! Ready for GPU-accelerated extraction.")



