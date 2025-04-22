import server
import base64
import io
from PIL import Image
import numpy as np
import zipfile
import time
import traceback

class DownloadImageDataUrl:
    @classmethod
    def INPUT_TYPES(s):
        return {
            "required": {
                "images": ("IMAGE", ),
                "filename_prefix": ("STRING", {"default": "ComfyUI"}),
                "format": (["PNG", "JPEG", "WebP"], {"default": "PNG"}),
                "batch_mode": (["Individual Files", "Single ZIP"], {"default": "Individual Files"}),
            },
            "optional": {
                "quality": ("INT", {"default": 95, "min": 1, "max": 100, "step": 1}),
                "max_size": ("INT", {"default": 0, "min": 0, "max": 4096, "step": 1, 
                             "display": "Max Size (0=No Resize)"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "generate_data_url_and_trigger_download"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def generate_data_url_and_trigger_download(self, images, filename_prefix="ComfyUI", 
                                               format="PNG", batch_mode="Individual Files", 
                                               quality=95, max_size=0, prompt=None, extra_pnginfo=None):
        try:
            # Map format to PIL format and file extension
            format_map = {
                "PNG": {"format": "PNG", "ext": "png", "lossless": True},
                "JPEG": {"format": "JPEG", "ext": "jpg", "lossless": False},
                "WebP": {"format": "WEBP", "ext": "webp", "lossless": False}
            }
            
            format_info = format_map[format]
            results = []
            timestamp = int(time.time())
            
            # For single ZIP file containing all images
            if batch_mode == "Single ZIP" and len(images) > 1:
                zip_buffer = io.BytesIO()
                
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    for i, image in enumerate(images):
                        # Process image
                        img_pil = self._tensor_to_pil(image)
                        
                        # Optional resize
                        if max_size > 0:
                            img_pil = self._resize_image(img_pil, max_size)
                        
                        # Save image to in-memory buffer
                        img_buffer = io.BytesIO()
                        save_args = self._get_save_args(format_info, quality)
                        img_pil.save(img_buffer, **save_args)
                        img_buffer.seek(0)
                        
                        # Add to zip
                        file_ext = format_info["ext"]
                        zip_file.writestr(f"{filename_prefix}_{i:05d}.{file_ext}", img_buffer.getvalue())
                
                # Convert zip to base64
                zip_buffer.seek(0)
                base64_encoded_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
                
                # Create data URL
                batch_filename = f"{filename_prefix}_batch_{timestamp}.zip"
                data_url = f"data:application/zip;base64,{base64_encoded_data}"
                
                results.append({
                    "filename": batch_filename,
                    "data_url": data_url,
                    "type": "zip"
                })
            else:
                # Individual files
                for i, image in enumerate(images):
                    # Process image
                    img_pil = self._tensor_to_pil(image)
                    
                    # Optional resize
                    if max_size > 0:
                        img_pil = self._resize_image(img_pil, max_size)
                    
                    # Save to memory buffer
                    with io.BytesIO() as byte_stream:
                        save_args = self._get_save_args(format_info, quality)
                        img_pil.save(byte_stream, **save_args)
                        img_bytes = byte_stream.getvalue()
                    
                    # Encode as Base64
                    base64_encoded_data = base64.b64encode(img_bytes).decode('utf-8')
                    
                    # Create data URL with MIME type
                    mime_type = f"image/{format_info['ext']}"
                    data_url = f"data:{mime_type};base64,{base64_encoded_data}"
                    
                    # Prepare filename
                    file_ext = format_info["ext"]
                    filename = f"{filename_prefix}_{i:05d}.{file_ext}"
                    
                    results.append({
                        "filename": filename,
                        "data_url": data_url,
                        "type": "image"
                    })
            
            return {"ui": {"data_urls": results}}
        
        except Exception as e:
            print(f"Error in DownloadImageDataUrl node: {str(e)}")
            traceback.print_exc()
            # Return error information to display in UI
            return {"ui": {"error": str(e)}}
    
    def _tensor_to_pil(self, tensor):
        """Convert tensor to PIL Image safely"""
        img_np = tensor.cpu().numpy()
        # Handle different tensor shapes properly
        if len(img_np.shape) == 4:  # Batch, Channel, Height, Width
            img_np = img_np[0]  # Take first image in batch
        
        # Handle different channel configurations
        if img_np.shape[0] == 1:  # Single channel
            img_np = np.squeeze(img_np, axis=0)  # Grayscale
        elif img_np.shape[0] == 3:  # RGB
            img_np = np.transpose(img_np, (1, 2, 0))  # CHW -> HWC
        elif img_np.shape[0] == 4:  # RGBA
            img_np = np.transpose(img_np, (1, 2, 0))  # CHW -> HWC
        
        # Convert to uint8
        img_np = (img_np * 255).astype(np.uint8)
        
        # Create PIL Image
        return Image.fromarray(img_np)
    
    def _resize_image(self, img, max_size):
        """Resize image if either dimension exceeds max_size"""
        if max_size <= 0:
            return img
            
        w, h = img.size
        if w > max_size or h > max_size:
            ratio = min(max_size / w, max_size / h)
            new_size = (int(w * ratio), int(h * ratio))
            return img.resize(new_size, Image.LANCZOS)
        return img
    
    def _get_save_args(self, format_info, quality):
        """Get appropriate save arguments based on format"""
        if format_info["format"] == "PNG":
            return {"format": "PNG", "compress_level": min(9, int(10 - quality/10))}
        elif format_info["format"] == "WEBP":
            return {"format": "WEBP", "quality": quality, "method": 6}
        else:  # JPEG
            return {"format": "JPEG", "quality": quality, "optimize": True}

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}