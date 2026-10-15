// present reads a value that the tools know to be there, such as the group of a regular expression that matched or an entry
// of a list under noUncheckedIndexedAccess, with a check: a missing value throws with what was expected. It follows present
// of polyspec/kit (scripts/kit/present.mts of the package, K156), which the package does not export.

/** The value, or an Error that names what was expected when it is undefined. */
export function present<T>(value: T | undefined, expected: string): T {
  if (value === undefined) throw new Error(`expected ${expected}`);
  return value;
}
