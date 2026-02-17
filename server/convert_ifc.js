/**
 * IFC to Fragment (.frag) converter.
 *
 * Usage: node convert_ifc.js <input.ifc> <output.frag>
 *
 * Uses @thatopen/fragments IfcLoader to convert IFC files
 * into the Fragment format used by the That Open Company viewer.
 */

const fs = require("fs");
const path = require("path");

async function convert(inputPath, outputPath) {
  // Dynamic imports for ESM modules
  const OBC = await import("@thatopen/components");
  const WEBIFC = await import("web-ifc");

  const components = new OBC.Components();
  const ifcLoader = components.get(OBC.IfcLoader);

  // Configure web-ifc WASM
  await ifcLoader.setup();

  // Read IFC file
  const ifcData = fs.readFileSync(inputPath);
  const buffer = new Uint8Array(ifcData);

  console.log(`Converting ${inputPath} (${(ifcData.length / 1024 / 1024).toFixed(1)} MB)...`);

  // Convert IFC to fragments
  const model = await ifcLoader.load(buffer);

  // Export fragments
  const fragmentsManager = components.get(OBC.FragmentsManager);
  const fragData = fragmentsManager.export(model);

  // Write output
  fs.writeFileSync(outputPath, Buffer.from(fragData));
  console.log(`Fragment written to ${outputPath} (${(fragData.byteLength / 1024 / 1024).toFixed(1)} MB)`);

  // Cleanup
  components.dispose();
}

// CLI entry point
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: node convert_ifc.js <input.ifc> <output.frag>");
  process.exit(1);
}

convert(args[0], args[1])
  .then(() => {
    console.log("Conversion complete.");
    process.exit(0);
  })
  .catch((err) => {
    console.error("Conversion failed:", err.message);
    process.exit(1);
  });
