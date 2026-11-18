"""Kiểm nhanh file workflow n8n (stdlib, không cần n8n): JSON hợp lệ, tên node duy nhất, mọi kết nối
trỏ tới node có thật, và không chứa khoá/token. Chạy: python3 check_workflows.py"""

import json
import pathlib
import re
import sys

SECRET = re.compile(r"(sk-|AIza|eyJ[A-Za-z0-9_-]{20,}|Bearer\s+[A-Za-z0-9._-]{20,})")
errors: list[str] = []

for path in sorted(pathlib.Path(__file__).parent.glob("workflows/*.json")):
    text = path.read_text(encoding="utf-8")
    wf = json.loads(text)
    names = [n["name"] for n in wf["nodes"]]
    if len(names) != len(set(names)):
        errors.append(f"{path.name}: tên node trùng")
    for src, outs in wf["connections"].items():
        if src not in names:
            errors.append(f"{path.name}: kết nối từ node không có: {src}")
        for branch in outs.get("main", []):
            for c in branch:
                if c["node"] not in names:
                    errors.append(f"{path.name}: kết nối tới node không có: {c['node']}")
    if SECRET.search(text):
        errors.append(f"{path.name}: có chuỗi giống khoá/token")
    for n in wf["nodes"]:
        cred = n.get("credentials", {})
        for c in cred.values():
            if c.get("id") != "REPLACE_IN_N8N":
                errors.append(f"{path.name}: credential id phải là REPLACE_IN_N8N ({n['name']})")
    print(f"{path.name}: {len(names)} node")

if errors:
    print("\n".join(errors))
    sys.exit(1)
print("OK")
