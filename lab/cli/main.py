#!/usr/bin/env python3
"""lab/cli/main.py — CLI через сервис (план v0.3 §22: писатель один — сервис).

Каждый вызов — короткое in-process соединение с ControlPlane2 (тот же
сервисный слой, что используют агенты). Вывод: JSON в stdout; ошибка
контракта (CtlError) — JSON в stderr и код 1. Файлы-аргументы читаются как
UTF-8 JSON. БД по умолчанию: LAB_DB или lab/state/control.db.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from pathlib import Path


def _json_file(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lab-cli",
        description="CLI лаборатории: единственный писатель — сервис control plane")
    p.add_argument("--db", default=os.environ.get("LAB_DB", "lab/state/control.db"))
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="создать/мигрировать БД")

    st = sub.add_parser("status", help="сводка очереди")
    st.add_argument("--json", action="store_true")

    pub = sub.add_parser("publish", help="опубликовать task/v1 из JSON-файла")
    pub.add_argument("file")

    cl = sub.add_parser("claim", help="взять задачу")
    cl.add_argument("--agent", required=True)
    cl.add_argument("--instance", default="")
    cl.add_argument("--department", required=True)
    cl.add_argument("--idem-key", default=None)

    hb = sub.add_parser("heartbeat", help="продлить lease")
    hb.add_argument("--lease", required=True)
    hb.add_argument("--epoch", type=int, required=True)
    hb.add_argument("--agent", required=True)
    hb.add_argument("--department", default=None)

    rel = sub.add_parser("release", help="добровольно вернуть задачу")
    rel.add_argument("--lease", required=True)
    rel.add_argument("--epoch", type=int, required=True)
    rel.add_argument("--agent", required=True)
    rel.add_argument("--reason", default="")

    sb = sub.add_parser("submit", help="отправить submission из JSON-файла")
    sb.add_argument("file")
    sb.add_argument("--idem-key", required=True)

    wm = sub.add_parser("waiting-main", help="задача ждёт решение main")
    wm.add_argument("--lease", required=True)
    wm.add_argument("--epoch", type=int, required=True)
    wm.add_argument("--agent", required=True)
    wm.add_argument("--timeout", type=int, required=True)

    cx = sub.add_parser("cancel", help="отмена задачи main (graceful)")
    cx.add_argument("--task", required=True)
    cx.add_argument("--actor", default="main")
    cx.add_argument("--reason", default="")

    ac = sub.add_parser("acknowledge-cancel", help="исполнитель подтверждает отмену")
    ac.add_argument("--lease", required=True)
    ac.add_argument("--epoch", type=int, required=True)
    ac.add_argument("--agent", required=True)

    pc = sub.add_parser("proposal-create", help="создать proposal/v1 из файла")
    pc.add_argument("file")

    pu = sub.add_parser("proposal-update", help="CAS-обновление draft-части")
    pu.add_argument("file")
    pu.add_argument("--author", required=True)
    pu.add_argument("--revision", type=int, required=True)

    pr = sub.add_parser("proposal-review", help="решение main по proposal")
    pr.add_argument("--id", required=True)
    pr.add_argument("--actor", default="main")
    pr.add_argument("--decision", required=True,
                    choices=["published", "rejected", "changes_requested"])
    pr.add_argument("--revision", type=int, required=True)
    pr.add_argument("--note", default="")

    pg = sub.add_parser("proposal-get", help="proposal/v1 целиком")
    pg.add_argument("--id", required=True)

    dc = sub.add_parser("decision", help="Decision/v1: решение main по submission")
    dc.add_argument("--submission", required=True)
    dc.add_argument("--validation", required=True)
    dc.add_argument("--decision", required=True,
                    choices=["accepted", "needs_work", "rejected"])
    dc.add_argument("--reason", required=True)

    ist = sub.add_parser("integration-start", help="зафиксировать начало Integration")
    ist.add_argument("--submission", required=True)
    ist.add_argument("--head-before", required=True)

    ifn = sub.add_parser("integration-finish", help="зафиксировать успешную Integration")
    ifn.add_argument("--integration", required=True)
    ifn.add_argument("--head-after", required=True)
    ifn.add_argument("--files-json", required=True,
                     help="JSON-файл с массивом фактически изменённых относительных путей")

    ifl = sub.add_parser("integration-fail", help="зафиксировать integration_failed")
    ifl.add_argument("--integration", required=True)
    ifl.add_argument("--reason", required=True)

    rd = sub.add_parser("message-read", help="отметить прочитанным")
    rd.add_argument("--message", required=True)
    rd.add_argument("--agent", required=True)

    ak = sub.add_parser("message-ack", help="подтвердить сообщение")
    ak.add_argument("--message", required=True)
    ak.add_argument("--agent", required=True)

    sm = sub.add_parser("message-send", help="отправить сообщение из файла")
    sm.add_argument("file")

    sub.add_parser("reap", help="просрочить leases и вернуть задачи в очередь")

    pj = sub.add_parser("projections", help="выгрузить файловые проекции")
    pj.add_argument("--out", default="lab/state/projections")

    gc = sub.add_parser("gc", help="sweep нессылочных blobs и .part")
    gc.add_argument("--grace", type=float, default=3600.0)

    bk = sub.add_parser("backup", help="снапшот БД через Backup API")
    bk.add_argument("--dest", required=True)

    return p


def run(args, cp) -> dict:
    cmd = args.cmd
    if cmd == "init":
        cp.init()
        return {"initialized": True, "user_version": cp.user_version()}
    if cmd == "status":
        return cp.status()
    if cmd == "publish":
        return cp.publish_task(_json_file(args.file))
    if cmd == "claim":
        return cp.claim(args.agent, args.instance, args.department,
                        idem_key=args.idem_key or f"cli-{uuid.uuid4().hex[:12]}")
    if cmd == "heartbeat":
        return cp.heartbeat(args.lease, args.epoch, args.agent,
                            department=args.department)
    if cmd == "release":
        return cp.release(args.lease, args.epoch, args.agent, reason=args.reason)
    if cmd == "submit":
        return cp.submit(_json_file(args.file), idem_key=args.idem_key)
    if cmd == "waiting-main":
        return cp.waiting_main(args.lease, args.epoch, args.agent, args.timeout)
    if cmd == "cancel":
        return cp.cancel_task(args.task, actor=args.actor, reason=args.reason)
    if cmd == "acknowledge-cancel":
        return cp.acknowledge_cancel(args.lease, args.epoch, args.agent)
    if cmd == "proposal-create":
        return cp.create_proposal(_json_file(args.file))
    if cmd == "proposal-update":
        doc = _json_file(args.file)
        return cp.update_proposal(doc["id"], args.author, args.revision,
                                   doc.get("payload", {}))
    if cmd == "proposal-review":
        return cp.review_proposal(args.id, args.actor, args.decision,
                                   args.revision, review_note=args.note)
    if cmd == "proposal-get":
        return cp.get_proposal(args.id)
    if cmd == "decision":
        return cp.decide_submission(
            args.submission, args.validation, args.decision, args.reason, actor="main")
    if cmd == "integration-start":
        return cp.start_integration(args.submission, args.head_before, actor="main")
    if cmd == "integration-finish":
        return cp.finish_integration(
            args.integration, args.head_after, _json_file(args.files_json), actor="main")
    if cmd == "integration-fail":
        return cp.fail_integration(args.integration, args.reason, actor="main")
    if cmd == "message-read":
        return cp.mark_read(args.message, args.agent)
    if cmd == "message-ack":
        return cp.ack(args.message, args.agent)
    if cmd == "message-send":
        return cp.send_message(_json_file(args.file))
    if cmd == "reap":
        return cp.reap()
    if cmd == "projections":
        return cp.write_projections(Path(args.out))
    if cmd == "gc":
        return cp.gc_blobs(grace_seconds=args.grace)
    if cmd == "backup":
        cp.backup(Path(args.dest))
        return {"backup": args.dest}
    raise AssertionError(f"unknown command {cmd}")


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from lab.service.control import CtlError
    from lab.service.v2_ops import ControlPlane2
    cp = ControlPlane2(Path(args.db))
    try:
        out = run(args, cp)
        print(json.dumps(out, ensure_ascii=False, sort_keys=True))
        return 0
    except CtlError as e:
        print(json.dumps({"error": e.code, "message": str(e)},
                         ensure_ascii=False), file=sys.stderr)
        return 1
    finally:
        cp.close()


if __name__ == "__main__":
    sys.exit(main())
