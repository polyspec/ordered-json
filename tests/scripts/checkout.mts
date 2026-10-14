// A synthetic Git checkout for the tests of the tools: a temporary directory whose files are tracked, removed when the test ends.
import { execFileSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import type { TestContext } from 'node:test';

export type Checkout = {
  root: string;
  /** Writes `text` to `file` and tracks it. */
  write: (file: string, text: string | Uint8Array) => void;
  /** Writes `data` as JSON with a final newline and tracks it. */
  json: (file: string, data: unknown) => void;
};

/** A new checkout for the test `context`. */
export function checkout(context: TestContext): Checkout {
  const root = mkdtempSync(path.join(tmpdir(), 'ordered-json-test-'));
  context.after(() => rmSync(root, { recursive: true, force: true }));
  execFileSync('git', ['init', '--quiet'], { cwd: root });
  const write = (file: string, text: string | Uint8Array) => {
    mkdirSync(path.dirname(path.join(root, file)), { recursive: true });
    writeFileSync(path.join(root, file), text);
    execFileSync('git', ['add', '--', file], { cwd: root });
  };
  return { root, write, json: (file, data) => write(file, `${JSON.stringify(data, null, 2)}\n`) };
}
