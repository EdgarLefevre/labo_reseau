"""Sauvegarde les configurations dans un depot Git, avec detection de changements."""
import subprocess
from datetime import datetime
from pathlib import Path

from netlab.transport import DockerTransport, Transport

DEVICES = ["r-siege", "r-agence"]
COMMANDS = {
    "frr.conf": "vtysh -c 'show running-config'",
    "nftables.nft": "nft list ruleset",
    "routes.txt": "ip route",
    "wireguard.txt": "wg show",   # attention : jamais 'wg showconf' (contient la cle privee)
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, check=True).stdout


def backup(transport: Transport, repo: Path) -> list[str]:
    """Ecrit les configs, commit s'il y a des changements, retourne les fichiers modifies."""
    repo.mkdir(parents=True, exist_ok=True)
    if not (repo / ".git").exists():
        git(repo, "init")
    for device in DEVICES:
        (repo / device).mkdir(exist_ok=True)
        for filename, command in COMMANDS.items():
            (repo / device / filename).write_text(transport.run(device, command))
    changed = [line[3:] for line in git(repo, "status", "--porcelain").splitlines()]
    if changed:
        git(repo, "add", "-A")
        git(repo, "commit", "-m", f"Sauvegarde {datetime.now():%Y-%m-%d %H:%M}")
    return changed


if __name__ == "__main__":
    changes = backup(DockerTransport(), Path("backups"))
    print(f"{len(changes)} fichier(s) modifie(s)" if changes else "Aucun changement")