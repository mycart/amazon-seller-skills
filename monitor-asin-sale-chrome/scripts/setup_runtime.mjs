#!/usr/bin/env node
import fs from "node:fs";
import path from "node:path";
import Module, { createRequire } from "node:module";
import { spawnSync } from "node:child_process";

const REQUIRED_PACKAGES = ["xlsx", "yaml", "nodemailer"];

export function workspaceRoot() {
  return process.cwd();
}

export function runtimeDir(workspace = workspaceRoot()) {
  return path.join(workspace, ".amazon_availability_monitor_runtime");
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

function packageEntry(dir, pkg) {
  const packageJson = path.join(dir, "node_modules", pkg, "package.json");
  if (!fs.existsSync(packageJson)) return null;
  const data = JSON.parse(fs.readFileSync(packageJson, "utf8"));
  return path.join(path.dirname(packageJson), data.main || "index.js");
}

function createRuntimeRequire(dir, requireAnchor) {
  const baseRequire = createRequire(requireAnchor);
  const runtimeRequire = (pkg) => {
    try {
      return baseRequire(pkg);
    } catch (error) {
      const entry = packageEntry(dir, pkg);
      if (!entry) throw error;
      return baseRequire(entry);
    }
  };
  runtimeRequire.resolve = (pkg) => {
    try {
      return baseRequire.resolve(pkg);
    } catch (error) {
      const entry = packageEntry(dir, pkg);
      if (!entry) throw error;
      return entry;
    }
  };
  return runtimeRequire;
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

  const requireFromRuntime = createRuntimeRequire(dir, requireAnchor);
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
    if (Module._pathCache) {
      for (const key of Object.keys(Module._pathCache)) delete Module._pathCache[key];
    }
    const installedRequire = createRuntimeRequire(dir, requireAnchor);
    for (const pkg of missing) installedRequire.resolve(pkg);
    return installedRequire;
  }

  return createRuntimeRequire(dir, requireAnchor);
}

if (import.meta.url === `file://${process.argv[1]}`) {
  ensureRuntime();
  console.log(`[setup] Runtime ready: ${runtimeDir()}`);
}
