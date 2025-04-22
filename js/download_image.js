import { app } from "/scripts/app.js";

app.registerExtension({
    name: "Comfy.DownloadImageDataUrlNode",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "DownloadImageDataUrl") {
            // Add progress overlay to node
            const onDrawForeground = nodeType.prototype.onDrawForeground;
            nodeType.prototype.onDrawForeground = function(ctx) {
                if (onDrawForeground) {
                    onDrawForeground.apply(this, arguments);
                }
                
                // Show download progress if active
                if (this.downloadStatus) {
                    const { text, progress } = this.downloadStatus;
                    const size = this.size;
                    
                    // Draw progress background
                    ctx.fillStyle = "rgba(0,0,0,0.5)";
                    ctx.fillRect(0, 0, size[0], size[1]);
                    
                    // Draw progress bar
                    if (progress > 0) {
                        ctx.fillStyle = "#2a9d8f";
                        const barWidth = size[0] * progress;
                        ctx.fillRect(0, size[1] - 10, barWidth, 10);
                    }
                    
                    // Draw text
                    ctx.fillStyle = "white";
                    ctx.font = "14px Arial";
                    ctx.textAlign = "center";
                    ctx.fillText(text, size[0] / 2, size[1] / 2);
                    
                    // Request redraw on next frame for animations
                    this.setDirtyCanvas(true);
                }
            };
            
            // Handle downloaded data
            const onExecuted = nodeType.prototype.onExecuted;
            nodeType.prototype.onExecuted = function(message) {
                if (onExecuted) {
                    onExecuted.apply(this, arguments);
                }
                
                // Clear any previous error state
                this.downloadStatus = null;
                
                // Handle error from Python side
                if (message?.error) {
                    this.downloadStatus = { text: `Error: ${message.error}`, progress: 0 };
                    console.error("DownloadImageDataUrl error:", message.error);
                    return;
                }
                
                // Process download URLs
                if (message?.data_urls && Array.isArray(message.data_urls)) {
                    const items = message.data_urls;
                    
                    if (items.length === 0) {
                        return;
                    }
                    
                    // Function to handle a single download
                    const downloadItem = (item) => {
                        return new Promise((resolve, reject) => {
                            try {
                                if (!item.data_url || !item.filename) {
                                    throw new Error("Missing data_url or filename");
                                }
                                
                                this.downloadStatus = { 
                                    text: `Downloading: ${item.filename}...`,
                                    progress: 0.2
                                };
                                
                                console.log(`Downloading: ${item.filename}`);
                                
                                // For large files, use blob approach for better memory handling
                                const isLarge = item.data_url.length > 5000000; // ~5MB in base64
                                
                                if (isLarge) {
                                    // Convert data URL to blob to handle memory better
                                    fetch(item.data_url)
                                        .then(response => {
                                            this.downloadStatus.progress = 0.5;
                                            return response.blob();
                                        })
                                        .then(blob => {
                                            const url = URL.createObjectURL(blob);
                                            this.downloadStatus.progress = 0.8;
                                            
                                            // Create download link
                                            const link = document.createElement('a');
                                            link.href = url;
                                            link.download = item.filename;
                                            document.body.appendChild(link);
                                            link.click();
                                            document.body.removeChild(link);
                                            
                                            // Clean up
                                            setTimeout(() => {
                                                URL.revokeObjectURL(url);
                                                this.downloadStatus.progress = 1.0;
                                                resolve();
                                            }, 100);
                                        })
                                        .catch(err => {
                                            reject(err);
                                        });
                                } else {
                                    // Simple direct download for smaller files
                                    const link = document.createElement('a');
                                    link.href = item.data_url;
                                    link.download = item.filename;
                                    document.body.appendChild(link);
                                    this.downloadStatus.progress = 0.8;
                                    
                                    setTimeout(() => {
                                        link.click();
                                        document.body.removeChild(link);
                                        this.downloadStatus.progress = 1.0;
                                        resolve();
                                    }, 100);
                                }
                            } catch (err) {
                                console.error("Download failed:", err);
                                reject(err);
                            }
                        });
                    };
                    
                    // Setup and start downloads
                    const downloadAll = async () => {
                        try {
                            // Update UI to show we're starting
                            this.downloadStatus = { text: "Preparing download...", progress: 0.1 };
                            
                            // Download each item sequentially
                            for (let i = 0; i < items.length; i++) {
                                await downloadItem(items[i]);
                            }
                            
                            // Show complete status briefly before clearing
                            this.downloadStatus = { 
                                text: `${items.length} file(s) downloaded!`, 
                                progress: 1.0 
                            };
                            
                            // Clear status after delay
                            setTimeout(() => {
                                this.downloadStatus = null;
                                this.setDirtyCanvas(true);
                            }, 3000);
                            
                        } catch (err) {
                            this.downloadStatus = { text: `Error: ${err.message}`, progress: 0 };
                            console.error("Download process failed:", err);
                        }
                    };
                    
                    // Start the download process
                    downloadAll();
                }
            };
        }
    },
});