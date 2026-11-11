# Jounral de labo

## TD1
RAS
## TD2 
RAS
## TD3 
Soucis de paquet, tcpdump n'etait pas installé, conf modifiée dans topology.yml (et dans le .md du labo)
## TD4
### Seance 5
Soucis de résolution dns pour ping le pc-srv depuis pc-user (dig marche mais pas ping, ping ip marche mais pas ping nom de domaine).
nslookup montre que le nxdomain n'etait pas bon -> dnsmasq conf pas bonne, il ne faut pas utiliser address dans ce cas mais host-record. 
### Seance 6 
#### Bug 1
Ping pc a ne marche pas
Ping r-agence ne marche pas 
Ping r-siege marche

ip link sur le routeur r-siege montre eth2 down -> liaison cassée, verifier cable
#### Bug 2 
PC-user ne peut ping personne mais pc-srv peut ping pc-a (reseau fonctionne entre les 2 routeurs)
Comparaison de ip route sur PC-user et R-siege, on voit que les masques reseaux ne correspondent pas. Je modifie sur PC-user (pc-srv peut ping pc-a donc je suppose que le routeur est bien configuré)

Une fois le masque modifié, je ne peux toujours pas ping les autres pc. 
Il manque la route par default qui a été supprimée par le flush. Il faut l'ajouter.

#### Bug 3
Le fichier resolv.conf n'etait pas bon sur pc-srv et pc-a, modification de topology.yml pour que les fichiers soient bon (sh -c 'cmd', cmd seule ne marchait pas).

En comparant ip route r-agence avec ip route r-siege, on voit que siege a tous les reseaux et pas r-agence; il faut donc ajouter le reseau du vlan20 au routeur agence pour retablir le lien. 
### Seance 7 
Pas de soucis avec topology.yml, je n'avais pas enlevé le ospf donc les pcs pouvaient se ping entre eux (pas bon, si un seul routeur / site pas de ospf).
### Seance 8 s
Le sujet n'etait pas clair (avec des coquilles), j'ai passé pas mal de temps à obtenir les resultats voulus. 
Le fichier firewall n'est pas encore bien maitrisé.
### Seance 9 
Concept clairs, le sujet faisait la configuration avec des one-liners qui ne passaient pas, en faisant plusieurs commandes c'est passé.
### Seance 10 
RAS
### Seance 11
Les clefs publiques du VPN ont bougees, surement une mauvaise manip de ma part, point a checker si un vpn ne fonctionne plus. Grafana + prometheus + alerts -> Chose deja mise en place avec ROS pour la robocup et autres projets.