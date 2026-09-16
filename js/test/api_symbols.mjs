// Reports the declared public API of the package, one symbol per line.
// index.d.ts is the published surface, so the list comes from it.
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {dirname, join} from 'node:path';

const declaration = readFileSync(join(dirname(fileURLToPath(import.meta.url)), '..', 'index.d.ts'), 'utf8');
const symbols = new Set();
let current = null;
for (const raw of declaration.split('\n')) {
  const line = raw.trim();
  if (!line || line.startsWith('//')) continue;
  const named = line.match(/^export (?:declare )?(?:abstract )?(class|interface|type|const|function) ([A-Za-z_$][\w$]*)/);
  if (named) {
    symbols.add(named[2]);
    current = line.endsWith('{') ? named[2] : null;
    continue;
  }
  if (line === '}') { current = null; continue; }
  if (!current) continue;
  const member = line.match(/^(?:private |static |readonly )*([A-Za-z_$][\w$]*)\s*[(:?]/);
  if (member && member[1] !== 'constructor') {
    symbols.add(`${current}.${member[1]}`);
  }
}
console.log([...symbols].sort().join('\n'));
