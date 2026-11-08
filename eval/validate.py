"""Kiểm tra nhất quán giữa corpus, bộ câu hỏi và hợp đồng (docs/DATA-CONTRACT.md).
Đây là kiểm tra dữ liệu, không chấm câu trả lời của mô hình. Chạy: python eval/validate.py"""
import json, re, sys, pathlib
root=pathlib.Path(__file__).resolve().parent.parent
ROLES={"visitor","customer","support","finance","manager"}
errs=[]
def err(m): errs.append(m)
docs={}
for p in sorted((root/"data/corpus").glob("*.md")):
    t=p.read_text(encoding="utf-8")
    m=re.match(r"---\n(.*?)\n---\n(.*)",t,re.S)
    if not m: err(f"{p.name}: thiếu frontmatter"); continue
    fm={}
    for line in m.group(1).splitlines():
        k,_,v=line.partition(": "); fm[k.strip()]=v.strip()
    for k in ["doc_id","title","language","allowed_roles","kind","source","license","version","updated"]:
        if k not in fm: err(f"{p.name}: thiếu {k}")
    if fm.get("doc_id")!=p.stem: err(f"{p.name}: doc_id không khớp tên file")
    roles=[r.strip() for r in fm.get("allowed_roles","").strip("[]").split(",") if r.strip()]
    for r in roles:
        if r not in ROLES: err(f"{p.name}: vai trò lạ {r}")
    if fm.get("kind") in ("order","ticket","invoice") and "owner_customer_id" not in fm: err(f"{p.name}: thiếu owner_customer_id")
    if fm.get("source")!="synthetic": err(f"{p.name}: source phải là synthetic")
    docs[p.stem]={"roles":roles,"owner":fm.get("owner_customer_id"),"body":m.group(2)}
def can(asker,d):
    r=asker["role"]
    if r not in d["roles"]: return False
    if r=="customer" and d["owner"]: return d["owner"]==asker.get("customer_id")
    return True
qs=[json.loads(l) for l in (root/"eval/questions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
ids=[x["id"] for x in qs]
if len(ids)!=len(set(ids)): err("ID câu hỏi trùng")
byid={x["id"]:x for x in qs}
cnt={}; vi=0
for x in qs:
    i=x["id"]; e=x["expected"]; a=x["asker"]
    cnt[x["group"]]=cnt.get(x["group"],0)+1
    vi+= x["lang"]=="vi"
    if a["role"] not in ROLES: err(f"{i}: vai trò lạ")
    if a["role"]=="customer" and not a.get("customer_id"): err(f"{i}: customer thiếu customer_id")
    for k in e["source_doc_ids"]+e["restricted_doc_ids"]:
        if k not in docs: err(f"{i}: doc không tồn tại {k}")
    if e["type"]=="answer":
        for k in e["source_doc_ids"]:
            if k in docs and not can(a,docs[k]): err(f"{i}: asker không có quyền với nguồn {k}")
        if not e["source_doc_ids"]: err(f"{i}: answer cần source_doc_ids")
        srctext=" ".join(docs[k]["body"] for k in e["source_doc_ids"] if k in docs)
        for kf in e["key_facts"]:
            if kf.startswith("~"): continue
            if not any(alt in srctext for alt in kf.split("|")): err(f"{i}: key_fact không có trong nguồn: {kf}")
    if e["type"]=="deny":
        for k in e["restricted_doc_ids"]:
            if k in docs and can(a,docs[k]): err(f"{i}: tài liệu 'bị chặn' {k} lại truy cập được")
        if not e["restricted_doc_ids"] and e.get("target_exists") is not False and not e.get("system_canary"):
            err(f"{i}: deny không có tài liệu bị chặn (đặt target_exists=false hoặc system_canary)")
    if e["type"]!="answer" or e["must_not_contain"]:
        for tok in e["must_not_contain"]:
            if tok in x["question"]: err(f"{i}: token cấm xuất hiện trong câu hỏi: {tok}")
            if e.get("injection_canary") or e.get("system_canary"): continue
            if not any(tok in docs[k]["body"] for k in e["restricted_doc_ids"] if k in docs): err(f"{i}: token cấm không nằm trong tài liệu bị chặn: {tok}")
            for k,d in docs.items():
                if can(a,d) and tok in d["body"]: err(f"{i}: token cấm '{tok}' xuất hiện trong tài liệu asker được xem ({k}): sẽ chấm nhầm")
    for f in ("pair_with","control","control_for"):
        if f in e and e[f] not in byid: err(f"{i}: {f} trỏ tới câu không có: {e[f]}")
    if "pair_with" in e and e["pair_with"] in byid:
        o=byid[e["pair_with"]]
        if o["asker"]["role"]!=a["role"]: err(f"{i}: cặp {e['pair_with']} khác vai trò người hỏi")
        if o["expected"].get("expected_class")!=e.get("expected_class"): err(f"{i}: cặp {e['pair_with']} khác lớp phản hồi kỳ vọng")
# canary không được nằm trong corpus
for k,d in docs.items():
    if "CANARY-SP-4410" in d["body"]: err(f"{k}: canary của system prompt nằm trong corpus")
# không tài liệu công khai chứa token của tài liệu bị chặn (đã bắt ở trên qua can())
print("tài liệu:",len(docs),"| câu hỏi:",len(qs),"| theo nhóm:",dict(sorted(cnt.items())),"| tiếng Việt:",vi)
if vi<10: err("ít hơn 10 câu tiếng Việt")
if errs:
    print("LỖI:"); [print(" -",m) for m in errs]; sys.exit(1)
print("OK: corpus và bộ câu hỏi nhất quán")
