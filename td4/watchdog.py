#!/usr/bin/env python3
"""Surveille les deux liens operateurs et bascule la route par defaut."""
import subprocess
import time

CONTAINER = "clab-td4-r-siege"
LINKS = [
    {"name": "ISP-A", "dev": "eth3", "gw": "198.51.100.1", "metric": 10, "probe": "192.0.2.2"},
    {"name": "ISP-B", "dev": "eth4", "gw": "203.0.113.1",  "metric": 20, "probe": "192.0.2.6"},
]
FAILS_TO_DOWN = 3
OKS_TO_UP = 3
state = {l["name"]: {"up": True, "fails": 0, "oks": 0} for l in LINKS}


def sh(cmd: str) -> int:
    return subprocess.run(["docker", "exec", CONTAINER, "sh", "-c", cmd],
                          capture_output=True).returncode


def probe(link) -> bool:
    # La route /32 vers la sonde force le chemin par CET operateur.
    return sh(f"ping -c1 -W1 -I {link['dev']} {link['probe']}") == 0


def setup():
    for l in LINKS:
        sh(f"ip route replace {l['probe']}/32 via {l['gw']} dev {l['dev']}")
        print(f"ip route replace {l['probe']}/32 via {l['gw']} dev {l['dev']}")
        sh(f"ip route replace default via {l['gw']} dev {l['dev']} metric {l['metric']}")
        print(f"ip route replace default via {l['gw']} dev {l['dev']} metric {l['metric']}")


def main():
    setup()
    print("watchdog demarre")
    while True:
        for l in LINKS:
            s = state[l["name"]]
            if probe(l):
                s["fails"], s["oks"] = 0, s["oks"] + 1
                if not s["up"] and s["oks"] >= OKS_TO_UP:
                    sh(f"ip route replace default via {l['gw']} dev {l['dev']} metric {l['metric']}")
                    print(f"ip route replace default via {l['gw']} dev {l['dev']} metric {l['metric']}")
                    s["up"] = True
                    subprocess.run(["docker", "exec", "clab-td4-isp-a", "sh", "-c", "ip route replace default via 192.0.2.2 dev eth2"], capture_output=True)
                    print(time.strftime("%H:%M:%S"), l["name"], "RETABLI")
            else:
                s["oks"], s["fails"] = 0, s["fails"] + 1
                if s["up"] and s["fails"] >= FAILS_TO_DOWN:
                    sh(f"ip route del default via {l['gw']} dev {l['dev']} metric {l['metric']}")
                    print(f"ip route del default via {l['gw']} dev {l['dev']} metric {l['metric']}")
                    s["up"] = False
                    print(time.strftime("%H:%M:%S"), l["name"], "TOMBE")
        time.sleep(1)


if __name__ == "__main__":
    main()