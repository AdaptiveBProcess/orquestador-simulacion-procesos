"""Registra una carpeta del usuario como artefacto (productor `usuario`).

    python -m shared.data_access.ingest --type declarative.event_log \\
        --log-name PurchasingExample --source /ruta/a/la/carpeta

Imprime la referencia del artefacto como JSON. Sin --run, crea una corrida nueva.
Almacén: --store, o la variable ORQ_STORE_PATH, o ./local_store.
"""
import argparse
import json
import sys

from .errors import DataAccessError
from .ids import new_id
from .local_disk import LocalDiskStore


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--type", required=True, help="tipo del catálogo, por ejemplo declarative.event_log")
    parser.add_argument("--source", required=True, help="carpeta con el contenido del artefacto")
    parser.add_argument("--run", help="run_id; por defecto, una corrida nueva")
    parser.add_argument("--store", help="raíz del almacén")
    parser.add_argument("--log-name")
    parser.add_argument("--scenario", choices=["AS-IS", "TO-BE"])
    parser.add_argument("--variant")
    parser.add_argument("--rule-kind")
    parser.add_argument("--rule-path")
    parser.add_argument("--rule-variation")
    parser.add_argument("--depends-on", action="append", default=[], metavar="RUN:ARTEFACTO")
    args = parser.parse_args(argv)

    rule = None
    if args.rule_kind or args.rule_path or args.rule_variation:
        rule = {"kind": args.rule_kind, "path": args.rule_path, "variation": args.rule_variation}
    depends = []
    for item in args.depends_on:
        run_id, _, artifact_id = item.partition(":")
        depends.append({"run_id": run_id, "artifact_id": artifact_id})
    try:
        ref = LocalDiskStore(root=args.store).guardar(
            run_id=args.run or new_id("run"), producer="usuario", type=args.type,
            status="completo", source_dir=args.source, log_name=args.log_name,
            scenario=args.scenario, rule=rule, variant=args.variant,
            depends_on=depends or None,
        )
    except DataAccessError as exc:
        print(json.dumps({"error": {"code": exc.code, "message": str(exc)}}, ensure_ascii=False))
        return 1
    print(json.dumps(ref))
    return 0


if __name__ == "__main__":
    sys.exit(main())
