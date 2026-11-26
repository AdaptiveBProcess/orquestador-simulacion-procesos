"""Cliente mínimo para probar a mano los servicios de ejemplo.

Solo biblioteca estándar. Imprime siempre JSON. Ejemplos:

    python -m shared.runtime.examples.client enviar http://127.0.0.1:8001 producer.generar --param text=hola
    python -m shared.runtime.examples.client consultar http://127.0.0.1:8001 task_...
    python -m shared.runtime.examples.client capacidades http://127.0.0.1:8001
    python -m shared.runtime.examples.client salud http://127.0.0.1:8001
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from shared.data_access.ids import new_id

FINAL_STATES = ("exitosa", "parcial", "fallida")


def request(method, url, body=None):
    """Devuelve (estado HTTP, JSON). Los errores HTTP también devuelven su JSON."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"} if data else {})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def submit(base_url, body):
    return request("POST", base_url.rstrip("/") + "/tasks", body)


def wait(base_url, task_id, run_id=None, timeout=120, poll=0.5):
    """Consulta hasta que la tarea llega a un estado final (o se agota el tiempo)."""
    url = "%s/tasks/%s" % (base_url.rstrip("/"), task_id)
    if run_id:
        url += "?run_id=" + run_id
    deadline = time.time() + timeout
    while True:
        status, record = request("GET", url)
        if status != 200 or record.get("status") in FINAL_STATES or time.time() > deadline:
            return status, record
        time.sleep(poll)


def _parse_value(text):
    try:
        return json.loads(text)
    except ValueError:
        return text


def _show(payload):
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("enviar", help="envía una tarea y espera su resultado")
    send.add_argument("url")
    send.add_argument("task", help="por ejemplo producer.generar")
    send.add_argument("--run", help="run_id; por defecto, uno nuevo")
    send.add_argument("--task-id", help="task_id; por defecto, uno nuevo")
    send.add_argument("--input", action="append", default=[], metavar="NOMBRE=RUN:ARTEFACTO")
    send.add_argument("--param", action="append", default=[], metavar="CLAVE=VALOR")
    send.add_argument("--retry-of")
    send.add_argument("--no-wait", action="store_true", help="no esperar al estado final")
    send.add_argument("--timeout", type=float, default=120)

    get = sub.add_parser("consultar", help="consulta una tarea")
    get.add_argument("url")
    get.add_argument("task_id")
    get.add_argument("--run")

    for name in ("capacidades", "salud"):
        sub.add_parser(name).add_argument("url")

    args = parser.parse_args(argv)
    base = args.url.rstrip("/")

    if args.command == "salud":
        _show(request("GET", base + "/health")[1])
        return 0
    if args.command == "capacidades":
        _show(request("GET", base + "/capabilities")[1])
        return 0
    if args.command == "consultar":
        status, record = request("GET", "%s/tasks/%s%s" % (base, args.task_id, "?run_id=" + args.run if args.run else ""))
        _show(record)
        return 0 if status == 200 else 1

    inputs = {}
    for item in args.input:
        name, _, ref = item.partition("=")
        run_id, _, artifact_id = ref.partition(":")
        inputs[name] = {"run_id": run_id, "artifact_id": artifact_id}
    params = {}
    for item in args.param:
        key, _, value = item.partition("=")
        params[key] = _parse_value(value)
    body = {"run_id": args.run or new_id("run"), "task_id": args.task_id or new_id("task"),
            "task": args.task, "inputs": inputs, "params": params}
    if args.retry_of:
        body["retry_of"] = args.retry_of

    status, record = submit(base, body)
    if status not in (200, 202):
        _show(record)
        return 1
    if not args.no_wait and record["status"] not in FINAL_STATES:
        status, record = wait(base, record["task_id"], record["run_id"], timeout=args.timeout)
    _show(record)
    return 0 if record.get("status") in ("exitosa", "parcial") else 1


if __name__ == "__main__":
    sys.exit(main())
