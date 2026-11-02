# Labo Réseau

Ce dépot contient un laboratoire réseau multi-sites (FRRouting, nftables, WireGuard, VLAN, double opérateur avec bascule mesurée), supervisé par Prometheus/Grafana, avec outillage d’automatisation en Python testé en CI, déploiement Azure par Terraform et un serveur MCP en lecture seule.

## Installation 

```sh
# Mise à jour et outils de base
sudo apt update
sudo apt install -y docker.io git make tcpdump python3-venv curl

# Installer Containerlab (script officiel)
bash -c "$(curl -sL https://get.containerlab.dev)"

# Vérifications
docker run --rm hello-world
containerlab version
```
