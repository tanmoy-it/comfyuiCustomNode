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

    RETURN_TYPES = () # This node doesn't pass data along the chain
    FUNCTION = "generate_data_url_and_trigger_download"
    OUTPUT_NODE = True # Mark this as a terminal node
    CATEGORY = "image"

    def generate_data_url_and_trigger_download(self, images, filename_prefix="ComfyUI", prompt=None, extra_pnginfo=None):
        results = []
        counter = 0 # Simple counter if batching images

        for image in images:
            # Convert tensor to PIL Image
            img_np = image.cpu().numpy()
            img_pil = Image.fromarray((img_np.squeeze(0) * 255.).astype(np.uint8))

            # --- Generate PNG bytes in memory ---
            with io.BytesIO() as byte_stream:
                # Add metadata if available (Optional - PNGInfo might not be standard for data URLs)
                # metadata = None
                # if prompt is not None and extra_pnginfo is not None:
                #    from nodes import SaveImage # Import might be needed
                #    metadata = SaveImage.create_metadata(prompt, extra_pnginfo, img_np)
                # if metadata:
                #    img_pil.save(byte_stream, format='PNG', pnginfo=metadata, compress_level=4)
                # else:
                img_pil.save(byte_stream, format='PNG', compress_level=4) # Save to memory buffer

                png_bytes = byte_stream.getvalue() # Get bytes from buffer

            # --- Encode bytes as Base64 ---
            base64_encoded_data = base64.b64encode(png_bytes).decode('utf-8')

            # --- Create data: URL ---
            data_url = f"data:image/png;base64,{base64_encoded_data}"

            # --- Prepare filename ---
            # You might want a more sophisticated filename based on prompt/metadata if available
            filename = f"{filename_prefix}_{counter:05}.png"
            counter += 1

            results.append({
                "filename": filename,
                "data_url": data_url
            })

        # Return the data URL info wrapped in 'ui' -> 'data_urls' (using a custom key)
        return {"ui": {"data_urls": results}}

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}