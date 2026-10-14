"""Texto→imagen con Stable Diffusion (diffusers). Uso: python image.py <params.json>

Modelo por defecto: stabilityai/sdxl-turbo (1-4 pasos; rápido, funciona incluso en CPU).
Cámbialo con la variable SD_MODEL, p. ej. stable-diffusion-v1-5/stable-diffusion-v1-5.
"""
import json
import sys

import torch
from diffusers import AutoPipelineForText2Image

SIZES = {"16:9": (1024, 576), "9:16": (576, 1024), "1:1": (768, 768), "4:3": (896, 672)}


def main(path):
    p = json.load(open(path, encoding="utf-8"))
    model = p["model"]
    turbo = "turbo" in model.lower()
    cuda = torch.cuda.is_available()
    w, h = SIZES.get(p.get("aspect", "1:1"), SIZES["1:1"])
    if not cuda:  # en CPU se reduce el tamaño para que termine en tiempo razonable
        w, h = (w // 2 // 8) * 8, (h // 2 // 8) * 8
    steps = int(p.get("steps") or (4 if turbo else 25))

    pipe = AutoPipelineForText2Image.from_pretrained(
        model, torch_dtype=torch.float16 if cuda else torch.float32, **({"variant": "fp16"} if cuda and turbo else {})
    )
    if cuda:
        pipe.enable_model_cpu_offload()
    print("PROGRESS 0.1", flush=True)

    def cb(_pipe, step, _t, kwargs):
        print(f"PROGRESS {0.1 + 0.85 * (step + 1) / steps:.3f}", flush=True)
        return kwargs

    args = dict(prompt=p["prompt"], width=w, height=h, num_inference_steps=steps, callback_on_step_end=cb)
    args["guidance_scale"] = 0.0 if turbo else 7.5
    if p.get("negative") and not turbo:
        args["negative_prompt"] = p["negative"]
    if p.get("seed") is not None:
        args["generator"] = torch.Generator().manual_seed(int(p["seed"]))
    pipe(**args).images[0].save(p["output"])
    print("PROGRESS 1", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
