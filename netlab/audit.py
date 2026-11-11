"""Controles de conformite sur les configurations reseau."""
import ipaddress
import json
import re
import sys
from dataclasses import dataclass

ALLOWED_NETWORKS = [ipaddress.ip_network(n) for n in (
    "10.10.0.0/16", "10.20.0.0/16", "10.99.0.0/30",
    "198.51.100.0/30", "203.0.113.0/30", "192.0.2.0/24",
)]
_POLICY_RE = re.compile(r"hook (\w+) priority [^;]+; policy (\w+);")
_ANY_ACCEPT_RE = re.compile(r"^(counter(?: packets \d+ bytes \d+)? )?accept$")


@dataclass(frozen=True)
class Finding:
    severity: str   # HIGH ou MEDIUM
    rule: str
    message: str


def check_default_policies(ruleset: str) -> list[Finding]:
    policies = dict(_POLICY_RE.findall(ruleset))
    return [
        Finding("HIGH", "default-policy",
                f"chaine {hook} : politique {policies.get(hook, 'absente')} au lieu de drop")
        for hook in ("input", "forward")
        if policies.get(hook) != "drop"
    ]


def check_any_any(ruleset: str) -> list[Finding]:
    return [
        Finding("HIGH", "any-any", "regle 'accept' sans aucune condition")
        for line in ruleset.splitlines()
        if _ANY_ACCEPT_RE.match(line.strip())
    ]


def check_addressing(ip_json: str) -> list[Finding]:
    findings = []
    for iface in json.loads(ip_json):
        if iface["ifname"] in ("lo", "eth0"):
            continue
        for addr in iface.get("addr_info", []):
            if addr["family"] != "inet":
                continue
            ip = ipaddress.ip_address(addr["local"])
            if not any(ip in net for net in ALLOWED_NETWORKS):
                findings.append(Finding("MEDIUM", "addressing",
                                        f"{iface['ifname']} : {ip} hors du plan d'adressage"))
    return findings


def check_snmp(config: str) -> list[Finding]:
    if re.search(r"snmp.*community\s+public", config, re.IGNORECASE):
        return [Finding("HIGH", "snmp", "communaute SNMP par defaut 'public'")]
    return []


def run_audit(transport, device: str) -> list[Finding]:
    ruleset = transport.run(device, "nft list ruleset")
    ip_json = transport.run(device, "ip -j addr")
    config = transport.run(device, "vtysh -c 'show running-config'")
    return (check_default_policies(ruleset) + check_any_any(ruleset)
            + check_addressing(ip_json) + check_snmp(config))


if __name__ == "__main__":
    from netlab.transport import DockerTransport
    findings = run_audit(DockerTransport(), "r-siege")
    for f in findings:
        print(f"[{f.severity}] {f.rule}: {f.message}")
    print("Conforme" if not findings else f"{len(findings)} ecart(s)")
    sys.exit(1 if any(f.severity == "HIGH" for f in findings) else 0)