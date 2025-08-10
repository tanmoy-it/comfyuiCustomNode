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

			// Minimal ZIP (stored, no compression)
			const CRC_TABLE = (() => {
				const table = new Uint32Array(256);
				for (let n = 0; n < 256; n++) {
					let c = n;
					for (let k = 0; k < 8; k++) {
						c = (c & 1) ? (0xEDB88320 ^ (c >>> 1)) : (c >>> 1);
					}
					table[n] = c >>> 0;
				}
				return table;
			})();
			const crc32 = (u8) => {
				let c = 0 ^ (-1);
				for (let i = 0; i < u8.length; i++) c = (c >>> 8) ^ CRC_TABLE[(c ^ u8[i]) & 0xFF];
				return (c ^ (-1)) >>> 0;
			};
			const textEncoder = new TextEncoder();
			const dosDateTime = () => {
				// Basic DOS date/time fields
				const d = new Date();
				const dosTime = ((d.getHours() & 0x1f) << 11) | ((d.getMinutes() & 0x3f) << 5) | ((Math.floor(d.getSeconds() / 2)) & 0x1f);
				const dosDate = (((d.getFullYear() - 1980) & 0x7f) << 9) | (((d.getMonth() + 1) & 0xf) << 5) | ((d.getDate()) & 0x1f);
				return { dosTime, dosDate };
			};
			const numToLE = (num, bytes) => {
				const a = new Uint8Array(bytes);
				for (let i = 0; i < bytes; i++) a[i] = (num >>> (8 * i)) & 0xff;
				return a;
			};
			const zipFiles = async (files) => {
				// files: [{name, blob}]
				const chunks = [];
				const central = [];
				let offset = 0;
				const { dosTime, dosDate } = dosDateTime();
				for (const f of files) {
					const name = sanitizeFilename(f.name);
					const nameBytes = textEncoder.encode(name);
					const buf = new Uint8Array(await f.blob.arrayBuffer());
					const crc = crc32(buf);
					const compSize = buf.length; // stored
					const uncompSize = buf.length;

					// Local file header
					chunks.push(numToLE(0x04034b50, 4)); // signature
					chunks.push(numToLE(20, 2)); // version needed
					chunks.push(numToLE(0x0800, 2)); // general purpose bit flag (UTF-8)
					chunks.push(numToLE(0, 2)); // method: store
					chunks.push(numToLE(dosTime, 2));
					chunks.push(numToLE(dosDate, 2));
					chunks.push(numToLE(crc, 4));
					chunks.push(numToLE(compSize, 4));
					chunks.push(numToLE(uncompSize, 4));
					chunks.push(numToLE(nameBytes.length, 2));
					chunks.push(numToLE(0, 2)); // extra length
					chunks.push(nameBytes);
					chunks.push(buf);
					const localHeaderSize = 30 + nameBytes.length;
					const localStart = offset;
					offset += localHeaderSize + buf.length;

					// Central directory header
					const cen = [];
					cen.push(numToLE(0x02014b50, 4)); // signature
					cen.push(numToLE(20, 2)); // version made by
					cen.push(numToLE(20, 2)); // version needed
					cen.push(numToLE(0x0800, 2)); // UTF-8 flag
					cen.push(numToLE(0, 2)); // method
					cen.push(numToLE(dosTime, 2));
					cen.push(numToLE(dosDate, 2));
					cen.push(numToLE(crc, 4));
					cen.push(numToLE(compSize, 4));
					cen.push(numToLE(uncompSize, 4));
					cen.push(numToLE(nameBytes.length, 2));
					cen.push(numToLE(0, 2)); // extra
					cen.push(numToLE(0, 2)); // comment
					cen.push(numToLE(0, 2)); // disk number
					cen.push(numToLE(0, 2)); // internal attrs
					cen.push(numToLE(0, 4)); // external attrs
					cen.push(numToLE(localStart, 4)); // local header offset
					cen.push(nameBytes);
					const cenChunk = new Uint8Array(cen.reduce((acc, a) => acc + a.length, 0));
					let p = 0;
					for (const a of cen) { cenChunk.set(a, p); p += a.length; }
					central.push(cenChunk);
				}
				// Central directory
				const centralStart = offset;
				for (const c of central) {
					chunks.push(c);
					offset += c.length;
				}
				const centralSize = offset - centralStart;

				// End of central directory
				const count = files.length;
				const eocd = [];
				eocd.push(numToLE(0x06054b50, 4));
				eocd.push(numToLE(0, 2)); // disk
				eocd.push(numToLE(0, 2)); // start disk
				eocd.push(numToLE(count, 2)); // entries on disk
				eocd.push(numToLE(count, 2)); // total entries
				eocd.push(numToLE(centralSize, 4));
				eocd.push(numToLE(centralStart, 4));
				eocd.push(numToLE(0, 2)); // comment length
				chunks.push(...eocd);

				// Concat all parts
				const totalLen = chunks.reduce((s, a) => s + a.length, 0);
				const out = new Uint8Array(totalLen);
				let q = 0;
				for (const a of chunks) { out.set(a, q); q += a.length; }
				return new Blob([out], { type: "application/zip" });
			};

			// Save helpers
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

			const saveToFolder = async (files) => {
				if (!("showDirectoryPicker" in window)) throw new Error("File System Access API not supported");
				const dir = await window.showDirectoryPicker();
				for (const f of files) {
					const handle = await dir.getFileHandle(sanitizeFilename(f.name), { create: true });
					const writable = await handle.createWritable();
					await writable.write(f.blob);
					await writable.close();
				}
			};

			const copyFirstToClipboard = async (files) => {
				if (!navigator.clipboard || !window.ClipboardItem) throw new Error("Clipboard API not supported");
				const first = files[0];
				await navigator.clipboard.write([new ClipboardItem({ [first.blob.type]: first.blob })]);
			};

			const notify = (msg, thumbDataURL) => {
				try {
					if (window?.ComfyUI?.notify) {
						if (thumbDataURL) {
							// Include small thumbnail in message
							window.ComfyUI.notify(`${msg}\n`, { timeout: 4000 });
						} else {
							window.ComfyUI.notify(msg, { timeout: 3000 });
						}
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
					const options = message?.options || {};
					let items = [];

					if (filesPayload && Array.isArray(filesPayload)) {
						items = filesPayload
							.filter(it => it?.data_url && it?.filename)
							.map(it => ({
								name: sanitizeFilename(it.filename),
								mime: it.mime || (it.data_url.match(/^data:([^;]+);/) || [,"application/octet-stream"])[1],
								dataURL: it.data_url,
								blob: null, // lazy
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

					// Build blobs
					for (const it of items) {
						if (!it.blob) it.blob = dataURLToBlob(it.dataURL);
					}

					// Developer hook
					try {
						if (options?.developer_emit) {
							const detail = {
								files: items.map(it => ({ name: it.name, mime: it.mime, dataURL: it.dataURL })),
								blobs: items.map(it => it.blob),
							};
							window.dispatchEvent(new CustomEvent("Comfy:DownloadImage:ready", { detail }));
							window.ComfyLastDownloadJob = detail; // quick access
						}
					} catch (e) {
						console.warn("DownloadImageDataUrl: developer_emit failed", e);
					}

					// Notifications with tiny previews (first only to keep it light)
					try {
						if (options?.notify_thumbnails && items[0]?.dataURL) {
							notify(`Prepared ${items.length} file(s)`, items[0].dataURL);
						} else {
							notify(`Prepared ${items.length} file(s)`);
						}
					} catch {}

					// Actions
					(async () => {
						// Save to folder if requested
						if (options?.save_to_folder) {
							try {
								await saveToFolder(items.map(it => ({ name: it.name, blob: it.blob })));
								notify(`Saved ${items.length} file(s) to folder`);
							} catch (err) {
								console.error("DownloadImageDataUrl: save_to_folder failed", err);
								notify(`Save to folder failed: ${err.message}`);
							}
						}

						// Batch ZIP if requested
						if (options?.batch_zip) {
							try {
								const zipBlob = await zipFiles(items.map(it => ({ name: it.name, blob: it.blob })));
								const zipName = sanitizeFilename(options?.zip_filename || "ComfyUI_Images.zip");
								triggerDownload(zipBlob, zipName);
								notify(`Downloaded ZIP: ${zipName}`);
							} catch (err) {
								console.error("DownloadImageDataUrl: ZIP failed", err);
								notify(`ZIP failed: ${err.message}`);
								// Fallback: direct downloads
								for (const it of items) triggerDownload(it.blob, it.name);
							}
						} else if (!options?.save_to_folder) {
							// Standard direct downloads (no ZIP and not saved to folder)
							for (const it of items) {
								try {
									triggerDownload(it.blob, it.name);
								} catch (err) {
									console.error("DownloadImageDataUrl: Download failed for", it.name, err);
									notify(`Failed: ${it.name} - ${err.message}`);
								}
							}
							notify(`Downloaded ${items.length} file(s)`);
						}

						// Clipboard copy (first image)
						if (options?.clipboard) {
							try {
								await copyFirstToClipboard(items);
								notify(`Copied to clipboard: ${items[0].name}`);
							} catch (err) {
								console.error("DownloadImageDataUrl: Clipboard failed", err);
								notify(`Clipboard copy failed: ${err.message}`);
							}
						}

						// Open first in new tab for quick preview
						if (options?.open_in_new_tab && items[0]?.dataURL) {
							try {
								window.open(items[0].dataURL, "_blank", "noopener,noreferrer");
							} catch (err) {
								console.error("DownloadImageDataUrl: Open in new tab failed", err);
								notify(`Open preview failed: ${err.message}`);
							}
						}
					})();
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