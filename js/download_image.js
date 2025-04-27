import { app } from "/scripts/app.js";

app.registerExtension({
	name: "Comfy.DownloadImageDataUrlNode",
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "DownloadImageDataUrl") {
			const onExecuted = nodeType.prototype.onExecuted;

			nodeType.prototype.onExecuted = function (message) {
				console.log("DownloadImageDataUrl node executed, message:", message);

				if (message?.data_urls) {
					message.data_urls.forEach(item => {
						if (item.data_url && item.filename) {
							try {
								const link = document.createElement('a');
								link.href = item.data_url;
								link.download = item.filename;
								document.body.appendChild(link);
								link.click();
								document.body.removeChild(link);
								// User feedback (non-intrusive)
								if (window?.ComfyUI && typeof window.ComfyUI.notify === "function") {
									window.ComfyUI.notify(`Downloaded: ${item.filename}`);
								}
							} catch (err) {
								console.error("DownloadImageDataUrl: Download failed for", item.filename, err);
								alert(`Failed to download ${item.filename}: ${err.message}`);
							}
						} else {
							console.warn("DownloadImageDataUrl: Received item is missing required fields (data_url, filename).", item);
						}
					});
				} else {
					console.log("DownloadImageDataUrl: No data_urls found in the execution message.");
				}
			};
		}
	},
});