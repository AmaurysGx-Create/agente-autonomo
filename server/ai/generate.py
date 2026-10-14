"""Generación de video con IA local (open source, gratis) usando diffusers.

Modelo por defecto: Lightricks/LTX-Video (texto→video e imagen→video).
Requiere GPU NVIDIA con ~8 GB+ de VRAM (con offload) y `pip install -r server/ai/requirements.txt`.
Uso: python generate.py <params.json>   (imprime "PROGRESS <0-1>" en stdout)
"""
import json
import sys

import torch
from diffusers import LTXImageToVideoPipeline, LTXPipeline
from diffusers.utils import export_to_video, load_image

ASPECTS = {"16:9": (768, 512), "9:16": (512, 768), "1:1": (512, 512), "4:3": (640, 480)}
FPS = 24


def main(path):
    p = json.load(open(path, encoding="utf-8"))
    width, height = ASPECTS.get(p.get("aspect", "16:9"), ASPECTS["16:9"])
    # LTX exige frames = 8k + 1
    frames = int(round(p.get("duration", 5) * FPS / 8)) * 8 + 1
    steps = int(p.get("steps", 30))
    model = p.get("model", "Lightricks/LTX-Video")
    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32

    image = p.get("imagePath")
    cls = LTXImageToVideoPipeline if image else LTXPipeline
    pipe = cls.from_pretrained(model, torch_dtype=dtype)
    if torch.cuda.is_available():
        pipe.enable_model_cpu_offload()  # cabe en GPUs modestas
        pipe.vae.enable_tiling()
    print("PROGRESS 0.05", flush=True)

    def cb(_pipe, step, _t, kwargs):
        print(f"PROGRESS {0.05 + 0.9 * (step + 1) / steps:.3f}", flush=True)
        return kwargs

    args = dict(
        prompt=p["prompt"],
        negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted",
        width=width,
        height=height,
        num_frames=frames,
        num_inference_steps=steps,
        callback_on_step_end=cb,
    )
    if p.get("seed") is not None:
        args["generator"] = torch.Generator().manual_seed(int(p["seed"]))
    if image:
        args["image"] = load_image(image)

    video = pipe(**args).frames[0]
    export_to_video(video, p["output"], fps=FPS)
    print("PROGRESS 1", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
