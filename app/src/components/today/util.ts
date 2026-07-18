/**
 * v4 `tset(name,key)` (~1040):
 *   const s=new Set(this.st[name]||[]); s.has(key)?s.delete(key):s.add(key); this.up({[name]:s});
 *
 * v4 copies the Set before mutating it, so the semantics are already immutable — only the
 * container differs. The three Today membership sets (`heldOpen`, `chunked`, `blocksOpen`)
 * are readonly records here rather than `Set`s, matching `collapsed` / `pickerExpanded` in
 * the same state bag, so this is the record equivalent: absent key = off.
 */
export function toggleKey(
  rec: Readonly<Record<string, true>>,
  key: string,
): Readonly<Record<string, true>> {
  if (rec[key]) {
    const next = { ...rec };
    delete next[key];
    return next;
  }
  return { ...rec, [key]: true };
}
