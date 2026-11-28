"""Arranque del servicio Merger: `python -m components.merger.adapter.service`."""
import logging

from shared.data_access import LocalDiskStore
from shared.runtime import Runtime, serve

from components.merger.adapter.component import component


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
    serve(Runtime(component, LocalDiskStore()))


if __name__ == "__main__":
    main()
