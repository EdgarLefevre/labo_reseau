.PHONY: up down test lint audit backup

up:
	sudo containerlab deploy -t td4/topology.yml
	sudo docker exec clab-td4-r-siege nft -f /firewall.nft

down:
	sudo containerlab destroy -t td4/topology.yml --cleanup

test:
	pytest -q

lint:
	ruff check .

audit:
	python -m netlab.audit

backup:
	python -m netlab.backup