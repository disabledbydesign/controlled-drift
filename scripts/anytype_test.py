#!/usr/bin/env python3
"""Anytype Local API validation for gsdo. Loads key from project .env (var get_shit_done)."""
import json, sys, urllib.request, urllib.error, re, os

ENV_PATH = "/Users/june/Documents/GitHub/cyborg-memory/controlled-drift/.env"
BASE = "http://localhost:31009/v1"
VERSION = "2025-11-08"

def load_key():
    with open(ENV_PATH) as f:
        txt = f.read()
    # handle: get_shit_done=val | get_shit_done = val | export get_shit_done="val" | get_shit_done: val
    m = re.search(r'(?:export\s+)?get_shit_done\s*[:=]\s*(.+)', txt)
    if m:
        val = m.group(1).strip()
        # strip straight AND smart quotes that editors auto-insert
        val = val.strip('"\'“”‘’ ')
        return val
    if not m:
        print("COULD NOT PARSE KEY. .env structure (values masked):")
        for line in txt.splitlines():
            if line.strip():
                k = re.split(r'[:=]', line, 1)[0]
                print(f"  line startswith: {k!r}  (len {len(line)})")
        sys.exit(1)
    return m.group(1).strip()

KEY = load_key()
HEADERS = {"Authorization": f"Bearer {KEY}", "Anytype-Version": VERSION,
           "Content-Type": "application/json"}

def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            raw = r.read().decode()
            try: return r.status, json.loads(raw)
            except: return r.status, raw
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try: return e.code, json.loads(raw)
        except: return e.code, raw
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"

def show(label, st, body, limit=2500):
    print(f"\n=== {label} -> status={st} ===")
    print(json.dumps(body, indent=2)[:limit] if isinstance(body,(dict,list)) else str(body)[:limit])

if __name__ == "__main__":
    print(f"[key loaded, len={len(KEY)}]")
    st, body = call("GET", "/spaces")
    sid = body["data"][0]["id"]
    print(f"space_id={sid}")

    st, body = call("GET", f"/spaces/{sid}/types?limit=100")
    if isinstance(body, dict) and "data" in body:
        print("\n=== TYPES (name -> key/id) ===")
        for t in body["data"]:
            print(f"  {t.get('name')!r:30} key={t.get('key')!r} id={t.get('id')!r}")
    else:
        show("GET types", st, body)

    # probe for an OpenAPI spec to learn create-body schemas
    print("\n=== OpenAPI spec probe ===")
    for spec in ["http://localhost:31009/openapi.json","http://localhost:31009/openapi",
                 "http://localhost:31009/v1/openapi.json","http://localhost:31009/swagger.json",
                 "http://localhost:31009/docs/openapi.json"]:
        try:
            req = urllib.request.Request(spec, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=5) as r:
                print(f"  FOUND {spec} (status {r.status}, {len(r.read())} bytes)")
                break
        except Exception as e:
            print(f"  miss {spec.split('31009')[1]}: {type(e).__name__}")

    # Task type detail (shows its properties + how values are shaped)
    tt = "bafyreifu7jdohgic26qdgziuxrxse4suk4soijbrgvetnbl6wpejdcob2u"
    show("GET task type detail", *call("GET", f"/spaces/{sid}/types/{tt}"))
