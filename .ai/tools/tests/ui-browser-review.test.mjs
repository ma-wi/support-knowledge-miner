import assert from "node:assert/strict";
import { mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  comparePixelArrays,
  isAllowedBrowserRequest,
  isAllowedBrowserSocket,
  parseActiveWorkDirectory,
  safeBrowserRequestLabel,
  validateBaselineFile,
  validateBaseUrl,
} from "../ui-browser-review.mjs";

const TEST_DIRECTORY = path.dirname(fileURLToPath(import.meta.url));
const frontendRequire = createRequire(
  path.resolve(TEST_DIRECTORY, "../../../frontend/package.json"),
);

test("active work path accepts one bounded child below .ai/work", () => {
  assert.deepEqual(
    parseActiveWorkDirectory(
      "# Current work\n\n- Work directory: `.ai/work/CHG-safe_1/`\n",
    ),
    {
      relative: ".ai/work/CHG-safe_1",
      changeId: "CHG-safe_1",
    },
  );
});

test("active work path rejects traversal and inactive state", () => {
  assert.throws(
    () =>
      parseActiveWorkDirectory(
        "# Current work\n\n- Work directory: `.ai/work/../outside/`\n",
      ),
    /one direct child/,
  );
  assert.throws(
    () =>
      parseActiveWorkDirectory("# Current work\n\nNo active requirement.\n"),
    /active work item/,
  );
});

test("base URL is restricted to an explicit loopback HTTP root", () => {
  assert.equal(
    validateBaseUrl("http://127.0.0.1:5173").href,
    "http://127.0.0.1:5173/",
  );
  for (const value of [
    "https://127.0.0.1:5173",
    "http://localhost:5173",
    "http://example.com:5173",
    "http://user@127.0.0.1:5173",
    "http://127.0.0.1:5173/path",
  ]) {
    assert.throws(() => validateBaseUrl(value), /loopback root/);
  }
});

test("browser request allowlist rejects every external origin", () => {
  const baseUrl = validateBaseUrl("http://127.0.0.1:5173");
  assert.equal(
    isAllowedBrowserRequest("http://127.0.0.1:5173/assets/app.js", baseUrl),
    true,
  );
  assert.equal(
    isAllowedBrowserRequest("http://127.0.0.1:8080/api/health", baseUrl),
    false,
  );
  assert.equal(
    isAllowedBrowserRequest("https://example.com/telemetry", baseUrl),
    false,
  );
  assert.equal(
    isAllowedBrowserSocket("ws://127.0.0.1:5173/hmr", baseUrl),
    true,
  );
  assert.equal(
    isAllowedBrowserSocket("wss://example.com/telemetry", baseUrl),
    false,
  );
  assert.equal(
    safeBrowserRequestLabel(
      "https://example.com/telemetry?token=must-not-be-logged#secret",
    ),
    "https://example.com/telemetry",
  );
});

test("pixel comparison reports bounded changes and rejects shape mismatch", () => {
  const expected = Uint8Array.from([0, 0, 0, 255, 255, 255, 255, 255]);
  const sameWithinThreshold = Uint8Array.from([
    10, 0, 0, 255, 255, 255, 255, 255,
  ]);
  const changed = Uint8Array.from([32, 0, 0, 255, 255, 255, 255, 255]);

  assert.deepEqual(comparePixelArrays(expected, sameWithinThreshold), {
    differentPixels: 0,
    totalPixels: 2,
    ratio: 0,
  });
  assert.deepEqual(comparePixelArrays(expected, changed), {
    differentPixels: 1,
    totalPixels: 2,
    ratio: 0.5,
  });
  assert.throws(
    () => comparePixelArrays(expected, Uint8Array.from([0, 0, 0, 255])),
    /equally sized/,
  );
});

test("accessibility engine reports an injected button-name violation", async () => {
  const { chromium } = frontendRequire("playwright-core");
  const AxeBuilder = frontendRequire("@axe-core/playwright").default;
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.setContent("<main><button></button></main>");
    const result = await new AxeBuilder({ page })
      .withRules(["button-name"])
      .analyze();
    assert.deepEqual(
      result.violations.map((violation) => violation.id),
      ["button-name"],
    );
  } finally {
    await browser.close();
  }
});

test("visual baseline validation rejects symbolic links", async () => {
  const temporary = await mkdtemp(
    path.join(os.tmpdir(), "skm-ui-runner-test-"),
  );
  try {
    const target = path.join(temporary, "target.png");
    const link = path.join(temporary, "baseline.png");
    await writeFile(target, Buffer.from([137, 80, 78, 71, 13, 10, 26, 10, 0]));
    await symlink(target, link);
    await assert.rejects(
      () => validateBaselineFile(link),
      /bounded regular file/,
    );
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
});
