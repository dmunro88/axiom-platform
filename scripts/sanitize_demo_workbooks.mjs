import fs from "node:fs/promises";
import path from "node:path";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const [profilePath, sourcePath, destinationPath, renderDir] = process.argv.slice(2);
if (!profilePath || !sourcePath || !destinationPath) {
  throw new Error(
    "Usage: node sanitize_demo_workbooks.mjs PROFILE INPUT.xlsx OUTPUT.xlsx [RENDER_DIR]",
  );
}

const profile = JSON.parse(await fs.readFile(profilePath, "utf8"));
if (!profile.replacements || Object.keys(profile.replacements).length === 0) {
  throw new Error(
    "The migration profile must contain a non-empty replacements object. " +
    "The canonical demo_profile.json intentionally contains no retired data.",
  );
}
const replacements = Object.entries(profile.replacements)
  .sort(([left], [right]) => right.length - left.length);

function fictionalize(value) {
  if (typeof value !== "string") return value;
  let result = value;
  for (const [original, fictional] of replacements) {
    result = result.split(original).join(fictional);
  }
  return result;
}

const input = await FileBlob.load(sourcePath);
const workbook = await SpreadsheetFile.importXlsx(input);
const sheetReport = await workbook.inspect({
  kind: "sheet",
  include: "id,name",
  maxChars: 30000,
});
const sheets = sheetReport.ndjson
  .split(/\r?\n/)
  .filter(Boolean)
  .map((line) => JSON.parse(line));

let replacementCount = 0;
for (const sheetInfo of sheets) {
  const sheet = workbook.worksheets.getItem(sheetInfo.name);
  const used = sheet.getUsedRange();
  if (!used) continue;

  const values = used.values;
  const formulas = used.formulas;
  for (let row = 0; row < values.length; row += 1) {
    for (let column = 0; column < values[row].length; column += 1) {
      const formula = formulas?.[row]?.[column];
      const value = values[row][column];
      const cell = used.getCell(row, column);

      if (typeof formula === "string" && formula.startsWith("=")) {
        const fictionalFormula = fictionalize(formula);
        if (fictionalFormula !== formula) {
          cell.formulas = [[fictionalFormula]];
          replacementCount += 1;
        }
        continue;
      }

      const fictionalValue = fictionalize(value);
      if (fictionalValue !== value) {
        cell.values = [[fictionalValue]];
        replacementCount += 1;
      }
    }
  }
}

await fs.mkdir(path.dirname(destinationPath), { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(destinationPath);

if (renderDir) {
  await fs.mkdir(renderDir, { recursive: true });
  for (const sheetName of [
    "Intake",
    "market",
    "sales",
    "lease_comps",
    "subject_units",
    "land",
    "land_sales",
    "outputs",
  ]) {
    if (!sheets.some((sheet) => sheet.name === sheetName)) continue;
    const preview = await workbook.render({
      sheetName,
      autoCrop: "all",
      scale: 1,
      format: "png",
    });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    await fs.writeFile(path.join(renderDir, `${sheetName}.png`), bytes);
  }
}

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 300 },
  summary: "formula-error scan after fictionalization",
  maxChars: 30000,
});

console.log(JSON.stringify({
  source: sourcePath,
  destination: destinationPath,
  replacementCount,
  formulaErrorCount: errorScan.ndjson
    ? errorScan.ndjson.split(/\r?\n/).filter(Boolean).length
    : 0,
}));
