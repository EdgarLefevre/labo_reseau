"""Genere une documentation Markdown a partir de l'etat reel des routeurs."""
import json
from datetime import datetime
from pathlib import Path

from netlab.transport import DockerTransport, Transport


def interfaces_table(ip_json: str) -> str:
    rows = ["| Interface | Etat | Adresses |", "|---|---|---|"]
    for iface in json.loads(ip_json):
        addrs = ", ".join(f"{a['local']}/{a['prefixlen']}"
                          for a in iface.get("addr_info", []) if a["family"] == "inet")
        rows.append(f"| {iface['ifname']} | {iface['operstate']} | {addrs or '-'} |")
    return "\n".join(rows)


def generate(transport: Transport, device: str) -> str:
    return (f"# {device}\n\n*Genere le {datetime.now():%Y-%m-%d %H:%M}*\n\n"
            f"## Interfaces\n\n{interfaces_table(transport.run(device, 'ip -j addr'))}\n\n"
            f"## Table de routage\n\n```\n{transport.run(device, 'ip route')}```\n")


if __name__ == "__main__":
    Path("docs").mkdir(exist_ok=True)
    for dev in ("r-siege", "r-agence"):
        Path(f"docs/{dev}.md").write_text(generate(DockerTransport(), dev))