import server
import base64
import io
from PIL import Image, PngImagePlugin
import numpy as np
import json
import datetime  # Added for timestamp
import re  # filename sanitization

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
                "include_timestamp": ("BOOLEAN", {"default": True}),
                # Metadata selection
                "metadata_mode": (["all", "workflow", "prompt", "none"], {"default": "all"}),
                # Format & quality
                "output_format": (["PNG", "JPEG", "WEBP"], {"default": "PNG"}),
                "quality": ("INT", {"default": 90, "min": 1, "max": 100, "step": 1, "display": "slider"}),
                "png_compress_level": ("INT", {"default": 4, "min": 0, "max": 9}),
                "webp_lossless": ("BOOLEAN", {"default": False}),
                # Filename/index controls
                "index_suffix": ("BOOLEAN", {"default": True}),
                "start_index": ("INT", {"default": 1, "min": 0, "max": 10_000}),
                "zero_padding": ("INT", {"default": 4, "min": 1, "max": 8}),
                # Client-side actions
                "batch_zip": ("BOOLEAN", {"default": False, "label": "Batch ZIP (one file)"}),
                "zip_filename": ("STRING", {"default": "ComfyUI_Images.zip"}),
            },
            "hidden": {"prompt": "PROMPT", "extra_pnginfo": "EXTRA_PNGINFO"},
        }

    RETURN_TYPES = ()
    FUNCTION = "generate_data_url_and_trigger_download"
    OUTPUT_NODE = True
    CATEGORY = "image"

    def _sanitize_filename(self, name: str, max_len: int = 128) -> str:
        # Allow alnum, space, - _ . and remove others; collapse spaces; trim length
        name = re.sub(r'[\\/:*?"<>|]+', '_', name)
        name = re.sub(r'\s+', ' ', name).strip()
        if not name:
            name = "image"
        return name[:max_len]

    def _tensor_to_pil(self, image_tensor):
        arr = image_tensor
        if hasattr(image_tensor, "cpu"):
            arr = image_tensor.cpu().numpy()
        else:
            arr = np.asarray(image_tensor)
        # Accept shapes: (H,W,C) or (1,H,W,C)
        if arr.ndim == 4 and arr.shape[0] == 1:
            arr = np.squeeze(arr, axis=0)
        if arr.ndim != 3 or arr.shape[2] not in (3, 4):
            raise ValueError(f"Unsupported image tensor shape: {arr.shape}")
        arr = np.clip(arr, 0.0, 1.0)
        arr_u8 = (arr * 255).astype(np.uint8)
        mode = "RGBA" if arr_u8.shape[2] == 4 else "RGB"
        return Image.fromarray(arr_u8, mode=mode)

    def _build_pnginfo(self, metadata_mode, prompt, extra_pnginfo):
        # Ensure metadata is discoverable by tools expecting tEXt (ASCII) and/or iTXt (UTF-8)
        if metadata_mode == "none":
            return None
        pnginfo = PngImagePlugin.PngInfo()
        added = False

        def to_json_ascii(obj):
            try:
                # ASCII-safe JSON so add_text (tEXt) never fails
                return json.dumps(obj, ensure_ascii=True, separators=(",", ":"))
            except Exception:
                try:
                    return json.dumps(str(obj), ensure_ascii=True)
                except Exception:
                    return None

        def add_both_chunks(key, obj):
            nonlocal added
            s_ascii = to_json_ascii(obj)
            if not s_ascii:
                return
            try:
                # tEXt (ASCII-safe)
                pnginfo.add_text(key, s_ascii)
            except Exception:
                pass
            try:
                # iTXt (UTF-8, uncompressed)
                pnginfo.add_itxt(key, s_ascii, lang="", tkey=key, compressed=False)
            except Exception:
                pass
            added = True

        if isinstance(extra_pnginfo, dict):
            if metadata_mode in ("all", "workflow") and "workflow" in extra_pnginfo:
                add_both_chunks("workflow", extra_pnginfo.get("workflow"))
            if metadata_mode in ("all", "prompt") and "prompt" in extra_pnginfo:
                add_both_chunks("prompt", extra_pnginfo.get("prompt"))
        else:
            if metadata_mode in ("all", "prompt") and prompt is not None:
                add_both_chunks("prompt", prompt)

        return pnginfo if added else None

    def generate_data_url_and_trigger_download(
        self,
        images,
        filename_prefix="ComfyUI",
        include_timestamp=True,
        metadata_mode="all",
        output_format="PNG",
        quality=90,
        png_compress_level=4,
        webp_lossless=False,
        index_suffix=True,
        start_index=1,
        zero_padding=4,
        batch_zip=False,
        zip_filename="ComfyUI_Images.zip",
        prompt=None,
        extra_pnginfo=None,
        # Back-compat: ignore old add_metadata if present in older workflows
        add_metadata=True,
    ):
        results = []

        fmt = (output_format or "PNG").upper()
        if fmt not in ("PNG", "JPEG", "WEBP"):
            fmt = "PNG"
        # Ensure workflow/prompt can be embedded and later detected on drop
        if metadata_mode != "none" and fmt != "PNG":
            fmt = "PNG"

        prefix = self._sanitize_filename(str(filename_prefix or "ComfyUI"))
        ext_map = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}
        mime_map = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}

        # Prepare timestamp once per batch
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3] if include_timestamp else None

        counter = int(start_index) if isinstance(start_index, int) else 1
        pad = max(1, min(int(zero_padding), 8))

        for idx, image in enumerate(images):
            try:
                img_pil = self._tensor_to_pil(image)
                # Adjust for format
                save_kwargs = {}
                if fmt == "PNG":
                    save_kwargs["compress_level"] = int(png_compress_level)
                    pnginfo = self._build_pnginfo(metadata_mode, prompt, extra_pnginfo)
                else:
                    pnginfo = None

                if fmt == "JPEG":
                    if img_pil.mode == "RGBA":
                        img_pil = img_pil.convert("RGB")
                    save_kwargs["quality"] = int(max(1, min(quality, 100)))
                    save_kwargs["optimize"] = True
                elif fmt == "WEBP":
                    if img_pil.mode not in ("RGB", "RGBA"):
                        img_pil = img_pil.convert("RGBA")
                    if webp_lossless:
                        save_kwargs["lossless"] = True
                        # quality ignored when lossless
                    else:
                        save_kwargs["quality"] = int(max(1, min(quality, 100)))

                with io.BytesIO() as byte_stream:
                    if fmt == "PNG":
                        img_pil.save(byte_stream, format="PNG", pnginfo=pnginfo, **save_kwargs)
                    else:
                        img_pil.save(byte_stream, format=fmt, **save_kwargs)
                    img_bytes = byte_stream.getvalue()

                b64 = base64.b64encode(img_bytes).decode("utf-8")
                data_url = f"data:{mime_map[fmt]};base64,{b64}"

                # Filename construction
                parts = [prefix]
                if index_suffix:
                    parts.append(str(counter).zfill(pad))
                if ts:
                    parts.append(ts)
                filename = "_".join(parts) + ext_map[fmt]
                filename = self._sanitize_filename(filename)
                counter += 1

                results.append({
                    "filename": filename,
                    "mime": mime_map[fmt],
                    "data_url": data_url,
                })
            except Exception as e:
                err_ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
                results.append({
                    "filename": self._sanitize_filename(f"{prefix}_{err_ts}_error.txt"),
                    "mime": "text/plain",
                    "data_url": "data:text/plain;base64," + base64.b64encode(str(e).encode()).decode(),
                    "error": str(e),
                })

        # Prepare options for frontend actions (only ZIP retained)
        options = {
            "batch_zip": bool(batch_zip),
            "zip_filename": self._sanitize_filename(zip_filename if zip_filename else "ComfyUI_Images.zip"),
        }

        # Back-compat: also provide data_urls for older JS handlers
        legacy = [{"filename": f["filename"], "data_url": f["data_url"]} for f in results]

        return {
            "ui": {
                "files": results,
                "options": options,
                "data_urls": legacy,
            }
        }

# --- Node Registration ---
NODE_CLASS_MAPPINGS = {
    "DownloadImageDataUrl": DownloadImageDataUrl
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "DownloadImageDataUrl": "Download Image (Direct/No Save)"
}