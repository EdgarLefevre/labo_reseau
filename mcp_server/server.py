"""Serveur MCP en lecture seule pour le labo reseau."""
import functools
import json
import logging

import requests
from mcp.server.fastmcp import FastMCP

from netlab.audit import run_audit
from netlab.transport import DockerTransport

PROM = "http://localhost:9090"
logging.basicConfig(filename="mcp_audit.log", level=logging.INFO,
                    format="%(asctime)s %(message)s")
mcp = FastMCP("reseau-lab")


def audited(fn):
    """Journalise chaque appel d'outil."""
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        logging.info("tool=%s args=%s", fn.__name__, json.dumps(kwargs))
        return fn(*args, **kwargs)
    return wrapper


def prom_query(expr: str) -> list:
    r = requests.get(f"{PROM}/api/v1/query", params={"query": expr}, timeout=5)
    r.raise_for_status()
    return r.json()["data"]["result"]


@mcp.tool()
@audited
def get_link_status() -> dict:
    """Etat de chaque lien surveille (1 = joignable, 0 = injoignable)."""
    return {s["metric"].get("cible", "?"): float(s["value"][1])
            for s in prom_query("probe_success")}


@mcp.tool()
@audited
def get_latency_ms() -> dict:
    """Latence mesuree vers chaque cible, en millisecondes."""
    return {s["metric"].get("cible", "?"): round(float(s["value"][1]) * 1000, 1)
            for s in prom_query("probe_duration_seconds")}


@mcp.tool()
@audited
def get_active_alerts() -> list:
    """Alertes Prometheus actuellement declenchees."""
    r = requests.get(f"{PROM}/api/v1/alerts", timeout=5)
    r.raise_for_status()
    return [{"alert": a["labels"].get("alertname"), "state": a["state"],
             "cible": a["labels"].get("cible"), "summary": a["annotations"].get("summary")}
            for a in r.json()["data"]["alerts"]]


@mcp.tool()
@audited
def run_config_audit() -> list:
    """Controle de conformite du pare-feu et de l'adressage de r-siege."""
    return [f.__dict__ for f in run_audit(DockerTransport(), "r-siege")]


if __name__ == "__main__":
    mcp.run()