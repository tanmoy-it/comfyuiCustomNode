import server
import base64
import io
from PIL import Image, PngImagePlugin
import numpy as np

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
        counter = 0

        for image in images:
            try:
                img_np = image.cpu().numpy()
                if img_np.shape[0] == 1:
                    img_np = np.squeeze(img_np, axis=0)
                img_pil = Image.fromarray((img_np * 255).astype(np.uint8))

                with io.BytesIO() as byte_stream:
                    pnginfo = None
                    if extra_pnginfo and isinstance(extra_pnginfo, dict):
                        pnginfo = PngImagePlugin.PngInfo()
                        # Embed all extra_pnginfo as text
                        for k, v in extra_pnginfo.items():
                            pnginfo.add_text(str(k), str(v))
                        # If workflow is present, embed it under the "workflow" key (ComfyUI convention)
                        if "workflow" in extra_pnginfo:
                            pnginfo.add_text("workflow", str(extra_pnginfo["workflow"]))
                    img_pil.save(byte_stream, format='PNG', compress_level=4, pnginfo=pnginfo)
                    png_bytes = byte_stream.getvalue()

                base64_encoded_data = base64.b64encode(png_bytes).decode('utf-8')
                data_url = f"data:image/png;base64,{base64_encoded_data}"

                filename = f"{filename_prefix}_{counter:05}.png"
                counter += 1

                results.append({
                    "filename": filename,
                    "data_url": data_url
                })
            except Exception as e:
                results.append({
                    "filename": f"{filename_prefix}_{counter:05}_error.txt",
                    "data_url": f"data:text/plain;base64,{base64.b64encode(str(e).encode()).decode()}"
                })
                counter += 1

        return {"ui": {"data_urls": results}}

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}