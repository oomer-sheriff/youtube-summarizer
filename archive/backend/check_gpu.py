import torch

if torch.cuda.is_available():
    print("✅ PyTorch can see your GPU!")
    print(f"CUDA version used by PyTorch: {torch.version.cuda}")
    print(f"Device Name: {torch.cuda.get_device_name(0)}")
else:
    print("❌ PyTorch CANNOT see your GPU.")
    print("This is likely because you installed the CPU-only version of PyTorch.")
    print("Please reinstall it with CUDA support.")
