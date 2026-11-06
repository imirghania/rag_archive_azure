// The upload page: hashes each file in the browser, opens the upload, sends 4 MB blocks through app-web (the browser never
// sees a storage address), resumes from the blocks the server holds, and presses Complete.
async function sha256(file) {
  const buf = await file.arrayBuffer();
  const h = await crypto.subtle.digest("SHA-256", buf);
  return [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join("");
}
const $ = id => document.getElementById(id);
const csrf = () => document.querySelector("meta[name=csrf]").content;
const hdr = (extra = {}) => ({ "X-CSRF-Token": csrf(), ...extra });
let upload = null;

$("go").onclick = async () => {
  const files = [...$("files").files];
  if (!files.length) return;
  $("log").textContent = "Hashing files…";
  const specs = [];
  for (const f of files) specs.push({ name: f.name, bytes: f.size, sha256: await sha256(f) });
  const body = { department: $("department").value, mode: $("mode").value, dossier_id: $("dossier").value || null, files: specs };
  const r = await fetch("/api/uploads", { method: "POST", headers: hdr({ "Content-Type": "application/json" }), body: JSON.stringify(body) });
  if (!r.ok) { $("log").textContent = (await r.json()).detail || "The upload could not be opened."; return; }
  upload = await r.json();
  $("summary").textContent = upload.decisive_line;
  $("confirm").hidden = false;
  window.__files = files;
};

$("confirm").onclick = async () => {
  $("confirm").hidden = true;
  const id = upload.upload_id, size = upload.block_bytes;
  const held = (await (await fetch(`/api/uploads/${id}`)).json()).files;
  for (const f of window.__files) {
    const have = new Set(held.find(x => x.name === f.name).blocks_held);
    const total = Math.max(1, Math.ceil(f.size / size));
    for (let n = 0; n < total; n++) {
      if (have.has(n)) continue;
      $("log").textContent = `${f.name}: block ${n + 1} of ${total}`;
      const r = await fetch(`/api/uploads/${id}/files/${encodeURIComponent(f.name)}/blocks/${n}`, { method: "PUT", headers: hdr(), body: f.slice(n * size, (n + 1) * size) });
      if (!r.ok) { $("log").textContent = "A block failed; press the button again to continue."; $("confirm").hidden = false; return; }
    }
  }
  const c = await fetch(`/api/uploads/${id}/complete`, { method: "POST", headers: hdr() });
  $("log").textContent = c.ok ? "Complete. The files are being checked." : (await c.json()).detail;
  if (c.ok) location.href = `/upload/${id}`;
};
