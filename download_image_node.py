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
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"}, # Keep hidden inputs if you want metadata in filename potentially
        }

    RETURN_TYPES = ()
    FUNCTION = "generate_data_url_and_trigger_download"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def generate_data_url_and_trigger_download(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        results = []
        counter = 0

        try:
            for image in images:
                # Convert tensor to NumPy array
                img_np = image.cpu().numpy()

                # Handle image dimensions properly
                if img_np.shape[0] == 1:  # Single channel
                    img_np = np.squeeze(img_np, axis=0)
                elif img_np.shape[0] == 3:  # RGB
                    img_np = np.transpose(img_np, (1, 2, 0))  # CHW to HWC format for PIL

                # Convert NumPy array to PIL Image
                img_pil = Image.fromarray((img_np * 255).astype(np.uint8))

                # Generate PNG bytes in memory
                with io.BytesIO() as byte_stream:
                    img_pil.save(byte_stream, format='PNG', compress_level=4)
                    png_bytes = byte_stream.getvalue()

                # Encode bytes as Base64
                base64_encoded_data = base64.b64encode(png_bytes).decode('utf-8')
                data_url = f"data:image/png;base64,{base64_encoded_data}"

                # Prepare filename
                filename = f"{filename_prefix}_{counter:05}.png"
                counter += 1

                results.append({
                    "filename": filename,
                    "data_url": data_url
                })
        except Exception as e:
            print(f"Error in DownloadImageDataUrl node: {str(e)}")
            # Return empty results on error
            return {"ui": {"data_urls": []}}

        # Return the data URL info wrapped in 'ui' -> 'data_urls'
        return {"ui": {"data_urls": results}}

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}