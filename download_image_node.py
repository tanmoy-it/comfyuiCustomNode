import server
import base64
import io
from PIL import Image
import numpy as np

class DownloadImageDataUrl:
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
            img_np = image.cpu().numpy()

            # Handle both (C, H, W) and (H, W, C) formats
            if img_np.ndim == 3:
                if img_np.shape[0] in [1, 3, 4]:  # (C, H, W)
                    if img_np.shape[0] == 1:  # Grayscale
                        img_np = np.squeeze(img_np, axis=0)
                        mode = "L"
                    elif img_np.shape[0] == 3:  # RGB
                        img_np = np.transpose(img_np, (1, 2, 0))
                        mode = "RGB"
                    elif img_np.shape[0] == 4:  # RGBA
                        img_np = np.transpose(img_np, (1, 2, 0))
                        mode = "RGBA"
                elif img_np.shape[2] in [1, 3, 4]:  # (H, W, C)
                    if img_np.shape[2] == 1:
                        img_np = np.squeeze(img_np, axis=2)
                        mode = "L"
                    elif img_np.shape[2] == 3:
                        mode = "RGB"
                    elif img_np.shape[2] == 4:
                        mode = "RGBA"
                else:
                    raise ValueError(f"Unsupported image shape: {img_np.shape}")
            elif img_np.ndim == 2:
                mode = "L"
            else:
                raise ValueError(f"Unsupported image shape: {img_np.shape}")

            img_pil = Image.fromarray((img_np * 255).clip(0, 255).astype(np.uint8), mode=mode)

            with io.BytesIO() as byte_stream:
                img_pil.save(byte_stream, format='PNG', compress_level=4)
                png_bytes = byte_stream.getvalue()

            base64_encoded_data = base64.b64encode(png_bytes).decode('utf-8')
            data_url = f"data:image/png;base64,{base64_encoded_data}"

            filename = f"{filename_prefix}_{counter:05}.png" if len(images) > 1 else f"{filename_prefix}.png"
            counter += 1

            results.append({
                "filename": filename,
                "data_url": data_url
            })

        # Return at the root level for JS compatibility
        return {"data_urls": results}

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}