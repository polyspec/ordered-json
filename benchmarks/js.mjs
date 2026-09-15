import fs from 'node:fs';
import { performance } from 'node:perf_hooks';
import { createHash } from 'node:crypto';
import { parse, stringify } from '../js/index.js';

const iterations = Number(process.env.OJ_BENCH_ITERATIONS ?? 1000);
const files = process.argv.slice(2);
let sink;
const digest = value => createHash('sha256').update(value).digest('hex');
const measure = fn => {
  const start = performance.now();
  let result;
  for (let i = 0; i < iterations; i++) result = fn();
  return [(performance.now() - start) * 1e6 / iterations, result];
};
for (const file of files) {
  const source = fs.readFileSync(file, 'utf8');
  const [parseNs] = measure(() => { sink = parse(source); return sink; });
  const value = parse(source);
  const [stringifyNs, output] = measure(() => stringify(value));
  const [roundtripNs, roundtrip] = measure(() => stringify(parse(source)));
  const nativeValue = JSON.parse(source);
  const [nativeParseNs] = measure(() => JSON.parse(source));
  const [nativeStringifyNs, nativeOutput] = measure(() => JSON.stringify(nativeValue));
  const [nativeRoundtripNs] = measure(() => JSON.stringify(JSON.parse(source)));
  console.log([file, 'ordered-json', parseNs, stringifyNs, roundtripNs, digest(output), Buffer.byteLength(source), Buffer.byteLength(output)].join('\t'));
  console.log([file, 'native-json', nativeParseNs, nativeStringifyNs, nativeRoundtripNs, digest(nativeOutput), Buffer.byteLength(source), Buffer.byteLength(nativeOutput)].join('\t'));
}
