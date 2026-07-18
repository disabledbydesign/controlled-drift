import type { PlanItem } from '../../fixtures/index.ts';
import { Interstitial } from './Interstitial.tsx';
import { TaskRow } from './TaskRow.tsx';
import { WorkBlock } from './WorkBlock.tsx';
import type { TodayCtx } from './types.ts';

export interface PlanEntryProps {
  ctx: TodayCtx;
  item: PlanItem;
  entryKey: string;
  showProj: boolean;
  bandIndex: number;
  itemIndex: number;
}

/**
 * v4 `planEntry(it,key,showProj)` (~1067):
 *   if(it.kind==='block')return this.workBlock(it,key);
 *   if(it.kind==='break')return this.interstitial(it,key);
 *   return this.taskRow(it,key,showProj);
 *
 * The one dispatch point over the plan's three item grains. `task` is the fallthrough, so an
 * item with an unrecognised `kind` renders as a task — v4's behaviour, kept.
 */
export function PlanEntry({
  ctx,
  item,
  entryKey,
  showProj,
  bandIndex,
  itemIndex,
}: PlanEntryProps) {
  if (item.kind === 'block') {
    return (
      <WorkBlock
        ctx={ctx}
        item={item}
        entryKey={entryKey}
        bandIndex={bandIndex}
        itemIndex={itemIndex}
      />
    );
  }
  if (item.kind === 'break') return <Interstitial ctx={ctx} item={item} />;
  return <TaskRow ctx={ctx} item={item} entryKey={entryKey} showProj={showProj} />;
}
