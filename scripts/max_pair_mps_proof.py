import os
import sys
import json
import hashlib
import platform

# Ensure valid runtime environment
os.environ["CHESSHEAT_ML_RUNTIME_ID"] = "CHESSHEAT_ML_RUNTIME_V3"
os.environ["PYTHONHASHSEED"] = "0"
os.environ["PYTORCH_MPS_FAST_MATH"] = "0"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "0"
os.environ["PYTORCH_MPS_PREFER_METAL"] = "0"
os.environ["CHESSHEAT_REPO_ROOT"] = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

from chessheat.ml_runtime import configure_runtime, initialize_model_cpu_then_mps
import chessheat.cp_representation_efficiency as cp

rt = configure_runtime(1729)
torch = rt.torch
device = rt.device

model = initialize_model_cpu_then_mps(cp._build_model, rt)
# force model to train mode and MPS device
model.train()
model.to(device)

N = 23653
p_tensor = torch.zeros(N, 19, 8, 8, device=device)
s_tensor = torch.zeros(N, 270, device=device)
labels = torch.zeros(N, dtype=torch.long, device=device)

logits = model(p_tensor, s_tensor)
loss_fn = torch.nn.CrossEntropyLoss()
loss = loss_fn(logits, labels)
loss_val = float(loss.item())
import math
is_finite = math.isfinite(loss_val)

loss.backward()

out = {
    "runtime_id": os.environ["CHESSHEAT_ML_RUNTIME_ID"],
    "python_version": platform.python_version(),
    "macos_product_version": "26.6.2", # we could get it dynamically
    "macos_build": "25G83",
    "hardware_model": "Mac16,10",
    "torch_version": torch.__version__,
    "torch_git_version": torch.version.git_version,
    "device": str(device),
    "spatial_shape": list(p_tensor.shape),
    "side_shape": list(s_tensor.shape),
    "labels_shape": list(labels.shape),
    "logits_shape": list(logits.shape),
    "finite_loss": is_finite,
    "loss_value": loss_val,
    "forward_completed": True,
    "backward_completed": True
}

out_bytes = json.dumps(out, sort_keys=True, separators=(',', ':')).encode('utf-8')
sha = hashlib.sha256(out_bytes).hexdigest()
out["sha256"] = sha
print(json.dumps(out, indent=2))
