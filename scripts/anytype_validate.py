#!/usr/bin/env python3
"""gsdo data-model validation against Anytype Local API."""
import sys, time, json, os
sys.path.insert(0, os.path.dirname(__file__))
from anytype_test import call

results = {}
def rec(name, ok, detail=""):
    results[name] = (ok, detail)
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")

st, body = call("GET", "/spaces")
sid = body["data"][0]["id"]
print(f"space={sid[:24]}…\n")

def mkprop(name, fmt):
    st, b = call("POST", f"/spaces/{sid}/properties", {"name": name, "format": fmt})
    key = (b.get("property") or {}).get("key") if isinstance(b, dict) else None
    rec(f"create property {name} ({fmt})", st in (200,201) and bool(key), f"status={st} key={key}")
    return key

print("== 1. CREATE CUSTOM PROPERTIES ==")
k_dur   = mkprop("GSDO Duration min", "number")
k_clar  = mkprop("GSDO Needs clarifying", "checkbox")
k_reach = mkprop("GSDO Reaching for", "objects")   # the alignment link
k_loc   = mkprop("GSDO Location mode", "select")

print("\n== 2. CREATE A CUSTOM TYPE (Goal) ==")
st, b = call("POST", f"/spaces/{sid}/types",
             {"name": "GSDO Goal", "plural_name": "GSDO Goals", "layout": "basic"})
goal_type_key = (b.get("type") or {}).get("key") if isinstance(b, dict) else None
rec("create type GSDO Goal", st in (200,201) and bool(goal_type_key), f"status={st} key={goal_type_key}")

print("\n== 3. CREATE A GOAL OBJECT ==")
st, b = call("POST", f"/spaces/{sid}/objects",
             {"type_key": goal_type_key or "page", "name": "Finish the dissertation chapter",
              "body": "reaching_for: the degree, on my own timeline"})
goal_id = (b.get("object") or {}).get("id") if isinstance(b, dict) else None
rec("create Goal object", st in (200,201) and bool(goal_id), f"status={st} id={str(goal_id)[:24]}")

print("\n== 4. CREATE A TASK linked to the Goal (the critical test) ==")
props = [{"key": "done", "checkbox": False}]
if k_dur:   props.append({"key": k_dur, "number": 30})
if k_clar:  props.append({"key": k_clar, "checkbox": True})
if k_reach and goal_id: props.append({"key": k_reach, "objects": [goal_id]})
st, b = call("POST", f"/spaces/{sid}/objects",
             {"type_key": "task", "name": "Draft section 3.2",
              "body": "messy first pass, don't polish", "properties": props})
task_id = (b.get("object") or {}).get("id") if isinstance(b, dict) else None
rec("create Task w/ props+link", st in (200,201) and bool(task_id), f"status={st} id={str(task_id)[:24]}")

print("\n== 5. READ BACK & VERIFY persistence ==")
if task_id:
    st, b = call("GET", f"/spaces/{sid}/objects/{task_id}")
    obj = b.get("object", {}) if isinstance(b, dict) else {}
    pv = {p.get("key"): p for p in obj.get("properties", [])}
    dur_ok   = k_dur in pv and pv[k_dur].get("number") == 30
    clar_ok  = k_clar in pv and pv[k_clar].get("checkbox") is True
    # objects-relation read-back
    reach_vals = pv.get(k_reach, {}).get("objects") if k_reach in pv else None
    reach_ok = bool(reach_vals) and goal_id in reach_vals
    rec("duration persisted", dur_ok, f"{pv.get(k_dur,{}).get('number')}")
    rec("needs-clarifying persisted", clar_ok, f"{pv.get(k_clar,{}).get('checkbox')}")
    rec("REACHING_FOR link persisted", reach_ok, f"objects={reach_vals}")

print("\n== 6. UPDATE (mark done, change duration) & re-verify ==")
if task_id:
    st, b = call("PATCH", f"/spaces/{sid}/objects/{task_id}",
                 {"properties": [{"key": "done", "checkbox": True},
                                 {"key": k_dur, "number": 15}] if k_dur else
                                [{"key": "done", "checkbox": True}]})
    st2, b2 = call("GET", f"/spaces/{sid}/objects/{task_id}")
    pv = {p.get("key"): p for p in (b2.get("object",{}) if isinstance(b2,dict) else {}).get("properties", [])}
    done_ok = pv.get("done", {}).get("checkbox") is True
    dur2_ok = (not k_dur) or pv.get(k_dur, {}).get("number") == 15
    rec("update done->true persisted", done_ok, f"patch_status={st} done={pv.get('done',{}).get('checkbox')}")
    rec("update duration->15 persisted", dur2_ok, f"{pv.get(k_dur,{}).get('number')}")

print("\n== 7. BATCH RELIABILITY (20 task creates) ==")
t0 = time.time(); ok = 0; errs = []
batch_ids = []
for i in range(20):
    st, b = call("POST", f"/spaces/{sid}/objects",
                 {"type_key": "task", "name": f"GSDO batch task {i}",
                  "properties": [{"key": k_dur, "number": i}] if k_dur else []})
    if st in (200,201) and isinstance(b, dict) and b.get("object",{}).get("id"):
        ok += 1; batch_ids.append(b["object"]["id"])
    else:
        errs.append((i, st))
dt = time.time() - t0
rec("batch 20 creates", ok == 20, f"{ok}/20 ok in {dt:.1f}s ({dt/20*1000:.0f}ms each); errors={errs[:5]}")

print("\n== 8. CLEANUP (delete the 20 batch tasks; keep demo task+goal visible) ==")
deld = 0
for oid in batch_ids:
    st, _ = call("DELETE", f"/spaces/{sid}/objects/{oid}")
    if st in (200, 204): deld += 1
rec("cleanup batch", deld == len(batch_ids), f"deleted {deld}/{len(batch_ids)}")

print("\n" + "="*50)
passed = sum(1 for ok,_ in results.values() if ok)
print(f"SUMMARY: {passed}/{len(results)} checks passed")
crit = ["create property GSDO Reaching for (objects)", "create Task w/ props+link", "REACHING_FOR link persisted", "batch 20 creates"]
print("CRITICAL checks:")
for c in crit:
    if c in results:
        ok, d = results[c]; print(f"  [{'PASS' if ok else 'FAIL'}] {c} — {d}")
