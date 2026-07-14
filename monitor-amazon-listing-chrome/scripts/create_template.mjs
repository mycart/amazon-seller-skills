#!/usr/bin/env node

import { createExcelTemplate, resolveWorkspacePaths } from "./lib.mjs";

const output = process.argv.includes("--output")
  ? process.argv[process.argv.indexOf("--output") + 1]
  : resolveWorkspacePaths().excelPath;

createExcelTemplate(output);
console.log(JSON.stringify({ ok: true, output }, null, 2));
