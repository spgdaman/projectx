/**
 * Generates brand-colored PNG assets for the Expo app.
 * Run once with: node scripts/gen-assets.js
 */
const zlib = require("zlib");
const fs = require("fs");
const path = require("path");

// CRC32 table
const crcTable = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c;
  }
  return t;
})();

function crc32(buf) {
  let c = 0xffffffff;
  for (let i = 0; i < buf.length; i++) c = crcTable[(c ^ buf[i]) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}

function chunk(type, data) {
  const t = Buffer.from(type, "ascii");
  const len = Buffer.allocUnsafe(4);
  len.writeUInt32BE(data.length);
  const crcInput = Buffer.concat([t, data]);
  const crcBuf = Buffer.allocUnsafe(4);
  crcBuf.writeUInt32BE(crc32(crcInput));
  return Buffer.concat([len, t, data, crcBuf]);
}

function makePng(width, height, r, g, b) {
  const sig = Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]);

  const ihdrData = Buffer.allocUnsafe(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;  // 8-bit depth
  ihdrData[9] = 2;  // RGB color type
  ihdrData[10] = 0; // deflate compression
  ihdrData[11] = 0; // filter method
  ihdrData[12] = 0; // no interlace

  // Build raw scanlines: filter byte (0) + RGB per pixel
  const scanline = Buffer.allocUnsafe(1 + width * 3);
  scanline[0] = 0;
  for (let x = 0; x < width; x++) {
    scanline[1 + x * 3] = r;
    scanline[1 + x * 3 + 1] = g;
    scanline[1 + x * 3 + 2] = b;
  }
  const raw = Buffer.concat(Array(height).fill(scanline));
  const compressed = zlib.deflateSync(raw, { level: 9 });

  return Buffer.concat([
    sig,
    chunk("IHDR", ihdrData),
    chunk("IDAT", compressed),
    chunk("IEND", Buffer.alloc(0)),
  ]);
}

const OUT = path.join(__dirname, "..", "assets");

// Brand primary #E54416 = rgb(229, 68, 22)
const [r, g, b] = [0xe5, 0x44, 0x16];
// White = rgb(255, 255, 255)
const [wr, wg, wb] = [0xff, 0xff, 0xff];

const assets = [
  { file: "icon.png",          w: 1024, h: 1024, rgb: [r, g, b] },
  { file: "adaptive-icon.png", w: 1024, h: 1024, rgb: [wr, wg, wb] },
  { file: "splash.png",        w: 1284, h: 2778, rgb: [r, g, b] },
  { file: "favicon.png",       w:   64, h:   64, rgb: [r, g, b] },
];

for (const { file, w, h, rgb } of assets) {
  const png = makePng(w, h, rgb[0], rgb[1], rgb[2]);
  fs.writeFileSync(path.join(OUT, file), png);
  console.log(`✓ ${file}  (${w}×${h}, ${png.length} bytes)`);
}

console.log("Done.");
