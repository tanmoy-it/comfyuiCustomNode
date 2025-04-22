import { app } from "/scripts/app.js";

app.registerExtension({
	name: "Comfy.DownloadImageDataUrlNode", 
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		if (nodeData.name === "DownloadImageDataUrl") {
			const onExecuted = nodeType.prototype.onExecuted;

			nodeType.prototype.onExecuted = function (message) {
				// Call original if it exists
				if (onExecuted) {
					onExecuted.apply(this, arguments);
				}

				console.log("DownloadImageDataUrl node executed, message:", message);

				// Look for our custom data through the ui.data_urls path
				if (message?.ui?.data_urls) {
					message.ui.data_urls.forEach(item => {
						if (item.data_url && item.filename) {
                            console.log("DownloadImageDataUrl: Triggering download for:", item.filename);

							// Create a temporary link element
							const link = document.createElement('a');
							link.href = item.data_url;
							link.download = item.filename;

							// Append to body, click, and remove
							document.body.appendChild(link);
							link.click();
							document.body.removeChild(link);
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