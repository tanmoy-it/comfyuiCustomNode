import { app } from "/scripts/app.js";

app.registerExtension({
	name: "Comfy.DownloadImageDataUrlNode", // Use a distinct name
	async beforeRegisterNodeDef(nodeType, nodeData, app) {
		// Check if this is our custom data URL node
		if (nodeData.name === "DownloadImageDataUrl") { // Match the Python class name
            const onExecuted = nodeType.prototype.onExecuted;

            nodeType.prototype.onExecuted = function (message) {
                // onExecuted?.apply(this, arguments); // Optional: Call original if needed

                console.log("DownloadImageDataUrl node executed, message:", message);

                // --- FIX: Look for message.ui.data_urls (batch support) ---
                const dataUrls = message?.ui?.data_urls;
                if (Array.isArray(dataUrls) && dataUrls.length > 0) {
                    dataUrls.forEach(item => {
                        if (item.data_url && item.filename) {
                            console.log("DownloadImageDataUrl: Triggering download for:", item.filename);

                            // Create a temporary link element
                            const link = document.createElement('a');
                            link.href = item.data_url; // Use the data: URL directly
                            link.download = item.filename; // Set the desired filename

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