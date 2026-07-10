#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";
import { spawnSync } from "node:child_process";

const REQUIRED_PACKAGES = ["playwright", "xlsx", "yaml", "nodemailer"];

export function workspaceRoot() {
  return process.env.ASIN_MONITOR_WORKSPACE || process.cwd();
}

export function runtimeDir(workspace = workspaceRoot()) {
  return process.env.ASIN_MONITOR_RUNTIME_DIR || path.join(workspace, ".amazon_availability_monitor_runtime");
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    stdio: "inherit",
    cwd: options.cwd || workspaceRoot(),
    env: process.env,
  });
  if (result.status !== 0) {
    throw new Error(`${command} ${args.join(" ")} failed with exit code ${result.status}`);
  }
}

export function ensureRuntime(packages = REQUIRED_PACKAGES) {
  const dir = runtimeDir();
  fs.mkdirSync(dir, { recursive: true });
  const packageJson = path.join(dir, "package.json");
  const requireAnchor = path.join(dir, "runtime-require.cjs");
  if (!fs.existsSync(packageJson)) {
    fs.writeFileSync(
      packageJson,
      JSON.stringify(
        {
          private: true,
          type: "module",
          dependencies: {},
        },
        null,
        2,
      ),
    );
  }
  if (!fs.existsSync(requireAnchor)) {
    fs.writeFileSync(requireAnchor, "// Anchor file for createRequire().\n", "utf8");
  }

  const requireFromRuntime = createRequire(requireAnchor);
  const missing = packages.filter((pkg) => {
    try {
      requireFromRuntime.resolve(pkg);
      return false;
    } catch {
      return true;
    }
  });

  if (missing.length) {
    console.log(`[setup] Installing monitor dependencies in ${dir}: ${missing.join(", ")}`);
    run("npm", ["install", "--prefix", dir, "--no-audit", "--no-fund", ...missing]);
  }

  return createRequire(requireAnchor);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  ensureRuntime();
  console.log(`[setup] Runtime ready: ${runtimeDir()}`);
}
