import server
import base64
import io
from PIL import Image, PngImagePlugin
import numpy as np
import json
import datetime  # Added for timestamp

class DownloadImageDataUrl:
    """
    ComfyUI Output Node: DownloadImageDataUrl
    Converts images to PNG data URLs and triggers download in the browser.
    """
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "generate_data_url_and_trigger_download"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def generate_data_url_and_trigger_download(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        results = []
        # counter = 0  # No longer needed

        for image in images:
            try:
                img_np = image.cpu().numpy()
                if img_np.shape[0] == 1:
                    img_np = np.squeeze(img_np, axis=0)
                img_pil = Image.fromarray((img_np * 255).astype(np.uint8))

                with io.BytesIO() as byte_stream:
                    pnginfo = PngImagePlugin.PngInfo()
                    # Embed extra_pnginfo as JSON under "extra_pnginfo"
                    if extra_pnginfo and isinstance(extra_pnginfo, dict):
                        # Embed the entire extra_pnginfo as JSON
                        # pnginfo.add_text("extra_pnginfo", json.dumps(extra_pnginfo)) #not needed for workflow embedding
                        # If workflow is present, embed as JSON string under "workflow"
                        if "workflow" in extra_pnginfo:
                            pnginfo.add_text("workflow", json.dumps(extra_pnginfo["workflow"]))
                        # If prompt is present, embed as JSON string under "prompt"
                        if "prompt" in extra_pnginfo:
                            pnginfo.add_text("prompt", json.dumps(extra_pnginfo["prompt"]))
                        # Optionally, embed all other keys as plain text for reference
                        for k, v in extra_pnginfo.items():
                            if k not in ("workflow", "prompt"):
                                pnginfo.add_text(str(k), str(v))
                    img_pil.save(byte_stream, format='PNG', compress_level=4, pnginfo=pnginfo)
                    png_bytes = byte_stream.getvalue()

                base64_encoded_data = base64.b64encode(png_bytes).decode('utf-8')
                data_url = f"data:image/png;base64,{base64_encoded_data}"

                # Generate filename with timestamp (YYYYmmdd_HHMMSS_mmm)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                filename = f"{filename_prefix}_{timestamp}.png"

                results.append({
                    "filename": filename,
                    "data_url": data_url
                })
            except Exception as e:
                # Error filename also uses timestamp
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                results.append({
                    "filename": f"{filename_prefix}_{timestamp}_error.txt",
                    "data_url": f"data:text/plain;base64,{base64.b64encode(str(e).encode()).decode()}"
                })

        return {"ui": {"data_urls": results}}

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}