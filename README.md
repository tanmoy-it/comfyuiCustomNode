# ComfyUI Download Image (Direct/No Save) Node

This custom node allows you to download images directly from ComfyUI as PNG files via your browser, without saving to disk on the server.

## Features

-   Converts images to PNG and triggers browser download.
-   Supports batch image download.
-   Optionally embeds extra PNG metadata (toggle via "Add Metadata?").
-   Handles errors gracefully.

## Usage

1. Place this folder in your ComfyUI custom nodes directory.
2. Restart ComfyUI.
3. Add the "Download Image (Direct/No Save)" node to your workflow.
4. Connect image outputs and run.
5. Use the "Add Metadata?" checkbox to include or exclude prompt/workflow metadata in the PNG.

## Troubleshooting

-   If downloads do not start, check your browser's popup blocker.
-   For errors, check the browser console and ComfyUI logs.

---
