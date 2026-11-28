"""Lectura y reescritura de la configuración de Simod.

La configuración de ejemplo fija `common.train_log_path: ./PurchasingExample.csv.gz`,
lo que acopla la configuración al nombre del log. Aquí se reescribe esa línea
(sin tocar el resto del texto ni sus comentarios) para que apunte al log recibido.
Requiere PyYAML, que ya trae el entorno de Simod.
"""
import json
import re

import yaml

DEFAULT_CASE_COLUMN = "case_id"  # la que Simod espera si la configuración no define otra

_TRAIN_LOG = re.compile(r"^([ \t]+train_log_path:[ \t]*)(.*?)([ \t]*#.*)?$", re.MULTILINE)


class ConfigError(Exception):
    """La configuración no tiene la forma esperada."""


def load(text):
    try:
        config = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise ConfigError("la configuración no es YAML válido (%s)" % exc.__class__.__name__)
    if not isinstance(config, dict) or not isinstance(config.get("common"), dict):
        raise ConfigError("la configuración no tiene la sección `common`")
    if not config["common"].get("train_log_path"):
        raise ConfigError("la configuración no define `common.train_log_path`")
    return config


def case_column(config):
    log_ids = config["common"].get("log_ids")
    if isinstance(log_ids, dict) and log_ids.get("case"):
        return str(log_ids["case"])
    return DEFAULT_CASE_COLUMN


def with_train_log(text, filename):
    """Devuelve el texto con `train_log_path` apuntando a `./<filename>` (relativo a la configuración)."""
    matches = _TRAIN_LOG.findall(text)
    if len(matches) != 1:
        raise ConfigError("se esperaba exactamente una línea `train_log_path`, hay %d" % len(matches))
    new_value = json.dumps("./" + filename)  # una cadena JSON es una cadena YAML válida
    rewritten = _TRAIN_LOG.sub(lambda m: m.group(1) + new_value + (m.group(3) or ""), text, count=1)
    if load(rewritten)["common"]["train_log_path"] != "./" + filename:
        raise ConfigError("no se pudo reescribir `train_log_path`")
    return rewritten
