/**
 * v4 `fmtDate(v)` (~840):
 *   if(!v)return '—'; const s=''+v; const d=new Date(s.length<=10?s+'T00:00':s);
 *   return isNaN(d.getTime())?s:d.toLocaleDateString('en-US',{month:'short',day:'numeric'});
 *
 * The `+'T00:00'` on a bare `YYYY-MM-DD` is load-bearing: without it the string parses as UTC
 * midnight and renders as the previous day for anyone west of Greenwich. Unparseable input
 * falls through to the raw string rather than "Invalid Date".
 *
 * Lives here rather than in `components/today` because both the Today slot and every focus
 * screen format dates with it. `today/FocusSlot.tsx` re-exports it so its existing import
 * surface is unchanged.
 */
export function fmtDate(v: string | undefined | null): string {
  if (!v) return '—';
  const s = '' + v;
  const d = new Date(s.length <= 10 ? s + 'T00:00' : s);
  return isNaN(d.getTime()) ? s : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}
