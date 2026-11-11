"""Acces aux equipements : une interface, plusieurs implementations."""
import subprocess
from typing import Protocol


class Transport(Protocol):
    def run(self, device: str, command: str) -> str: ...


class DockerTransport:
    """Execute les commandes dans les conteneurs Containerlab (labo)."""

    def __init__(self, lab: str = "td4") -> None:
        self.lab = lab

    def run(self, device: str, command: str) -> str:
        result = subprocess.run(
            ["docker", "exec", f"clab-{self.lab}-{device}", "sh", "-c", command],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"{device}: {command!r} a echoue: {result.stderr.strip()}")
        return result.stdout

'''
Pour la production, une implémentation SSH ressemblerait à ceci (à garder en tête, pas à tester dans le labo) :

from netmiko import ConnectHandler

class SshTransport:
    def __init__(self, hosts: dict, username: str, key_file: str) -> None:
        self.hosts, self.username, self.key_file = hosts, username, key_file

    def run(self, device: str, command: str) -> str:
        with ConnectHandler(device_type="linux", host=self.hosts[device],
                            username=self.username, use_keys=True,
                            key_file=self.key_file) as conn:
            return conn.send_command(command)
'''