import { app } from "/scripts/app.js";

app.registerExtension({
	name: "Comfy.DownloadImageDataUrlNode",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "DownloadImageDataUrl") {
			const onExecuted = nodeType.prototype.onExecuted;

			// Utility: data URL -> Blob
			const dataURLToBlob = (dataURL) => {
				const [head, body] = dataURL.split(",");
				const mime = (head.match(/data:([^;]+);/) || [,"application/octet-stream"])[1];
				const bin = atob(body);
				const len = bin.length;
				const bytes = new Uint8Array(len);
				for (let i = 0; i < len; i++) bytes[i] = bin.charCodeAt(i);
				return new Blob([bytes], { type: mime });
			};
			// Utility: filename sanitization (mirror server)
			const sanitizeFilename = (name, maxLen = 128) => {
				name = (name || "image").replace(/[\\/:*?"<>|]+/g, "_").trim();
				name = name.replace(/\s+/g, " ");
				if (!name) name = "image";
				if (name.length > maxLen) name = name.slice(0, maxLen);
				return name;
			};

			// Save helper: trigger direct download
			const triggerDownload = (blob, filename) => {
				const url = URL.createObjectURL(blob);
				const a = document.createElement("a");
				a.href = url;
				a.download = sanitizeFilename(filename);
				document.body.appendChild(a);
				a.click();
				document.body.removeChild(a);
				URL.revokeObjectURL(url);
			};

			// Simple notifier
			const notify = (msg) => {
				try {
					if (window?.ComfyUI?.notify) {
						window.ComfyUI.notify(msg, { timeout: 3000 });
					} else {
						console.log("[DownloadImageDataUrl]", msg);
					}
				} catch (e) {
					console.log("[DownloadImageDataUrl]", msg);
				}
			};

			nodeType.prototype.onExecuted = function (message) {
				console.log("DownloadImageDataUrl node executed, message:", message);

				try {
					// Prefer new payload
					const filesPayload = message?.files || null;
					let items = [];

					if (filesPayload && Array.isArray(filesPayload)) {
						items = filesPayload
							.filter(it => it?.data_url && it?.filename)
							.map(it => ({
								name: sanitizeFilename(it.filename),
								mime: it.mime || (it.data_url.match(/^data:([^;]+);/) || [,"application/octet-stream"])[1],
								dataURL: it.data_url,
								blob: null,
							}));
					} else if (message?.data_urls) {
						// Backward compatibility
						items = message.data_urls
							.filter(it => it?.data_url && it?.filename)
							.map(it => ({
								name: sanitizeFilename(it.filename),
								mime: (it.data_url.match(/^data:([^;]+);/) || [,"application/octet-stream"])[1],
								dataURL: it.data_url,
								blob: null,
							}));
					}

					if (!items.length) {
						console.log("DownloadImageDataUrl: No files/data_urls found in the execution message.");
						return;
					}

					// Build blobs and download
					for (const it of items) {
						try {
							if (!it.blob) it.blob = dataURLToBlob(it.dataURL);
							triggerDownload(it.blob, it.name);
						} catch (err) {
							console.error("DownloadImageDataUrl: Download failed for", it.name, err);
						}
					}
					notify(`Downloaded ${items.length} file(s)`);
				} catch (e) {
					console.error("DownloadImageDataUrl: unexpected error", e);
					try {
						if (window?.ComfyUI?.notify) window.ComfyUI.notify(`Download error: ${e.message}`);
					} catch {}
				}
			};
		}
	},
});