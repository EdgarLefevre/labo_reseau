# Jounral de labo

## TD1
RAS
## TD2 
RAS
## TD3 
Soucis de paquet, tcpdump n'etait pas installé, conf modifiée dans topology.yml (et dans le .md du labo)
## TD4
Soucis de résolution dns pour ping le pc-srv depuis pc-user.
nslookup montre que le nxdomain n'etait pas bon -> dnsmasq conf pas bonne, il ne faut pas utiliser address dans ce cas mais host-record. 
