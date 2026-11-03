# TD Réseau : de zéro à l’architecture multi-sites

*Labo pratique sur Ubuntu 26.04, Containerlab et FRRouting. Niveau : débutant en réseau, à l’aise en développement.*

## Comment utiliser ce TD

Ce document fonctionne comme un cours encadré : chaque séance suit le même schéma.

- **L’idée** : ce qu’il faut comprendre avant de toucher au clavier.
- **Manipulation** : les commandes à taper, avec leur explication.
- **Questions** : à traiter *avant* de lire le corrigé. C’est là que l’apprentissage se fait.
- **Corrigé** : à lire après avoir cherché.
- **Checkpoint** : un critère simple pour savoir si tu peux passer à la suite.

**Rythme conseillé** : 8 à 10 h par semaine. Séances 0 à 6 = semaine 2, séances 7 à 11 = semaine 3, séances 12 à 15 = semaine 4.

**Règle d’or** : tiens un fichier `journal.md` dans ton dépôt Git. À chaque séance, note ce que tu as fait, ce qui a cassé, et comment tu l’as réparé. C’est ce journal qui deviendra ta matière d’entretien.

**Organisation du dépôt**

```
reseau-lab/
  journal.md
  td1/   (séance 2)
  td2/   (séances 3 et 4)
  ...
```

---

# SEMAINE 2 : LE SOCLE RÉSEAU

## Séance 0 : le vocabulaire et l’adressage IP (1 h 30, sans ordinateur)

### L’idée

Un réseau, c’est des machines qui s’échangent des **paquets** (des petits morceaux de données avec une adresse de départ et une adresse d’arrivée). Pour un développeur, l’analogie la plus utile : **une adresse IP est comme une adresse postale, et le routeur est le bureau de poste qui décide dans quelle direction envoyer chaque lettre.**

| Terme | Rôle | Analogie |
| --- | --- | --- |
| **Adresse IP** | Identifie une machine sur un réseau (ex. `10.10.10.10`) | Adresse postale |
| **Masque / CIDR** | Dit quelle partie de l’adresse désigne le réseau et laquelle désigne la machine (ex. `/24`) | « Le code postal et la rue » vs « le numéro » |
| **Switch** | Relie des machines du **même** réseau, travaille avec les adresses MAC | Couloir d’un immeuble |
| **Routeur** | Relie des réseaux **différents**, travaille avec les adresses IP | Bureau de poste |
| **Passerelle (gateway)** | L’adresse du routeur vers lequel une machine envoie tout ce qui n’est pas local | « Si tu ne connais pas, donne à celui-là » |
| **DHCP** | Distribue automatiquement les adresses IP | Réception qui attribue des badges |
| **DNS** | Traduit un nom (`serveur.lab.local`) en adresse IP | Annuaire |
| **NAT** | Remplace les adresses privées par une adresse publique à la sortie | Standard téléphonique d’entreprise |
| **VLAN** | Découpe un switch en plusieurs réseaux logiques séparés | Cloisons dans un open space |
| **Port** | Numéro qui désigne un service sur une machine (443 = HTTPS, 22 = SSH) | Numéro de bureau |

### Lire une notation CIDR

`10.10.10.0/24` signifie : les **24 premiers bits** désignent le réseau, les **8 bits restants** désignent la machine.

- Il reste 8 bits pour les machines : 2⁸ = 256 adresses.
- On enlève 2 adresses réservées : l’adresse du réseau (la première, `.0`) et l’adresse de broadcast (la dernière, `.255`). Il reste **254 machines utilisables**.

Règle générale : un `/N` laisse `32 - N` bits pour les machines, donc `2^(32-N) - 2` hôtes utilisables.

| CIDR | Masque | Adresses totales | Hôtes utilisables |
| --- | --- | --- | --- |
| /16 | 255.255.0.0 | 65 536 | 65 534 |
| /24 | 255.255.255.0 | 256 | 254 |
| /26 | 255.255.255.192 | 64 | 62 |
| /30 | 255.255.255.252 | 4 | 2 |

Le `/30` est très utilisé pour les liaisons point à point entre deux routeurs (2 hôtes utilisables, pas de gaspillage).

**Adresses privées** (non routées sur Internet) : `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`.

### Exercices

1. Pour `192.168.1.0/24` : donne le masque, le nombre d’hôtes utilisables et l’adresse de broadcast.
2. Pour `10.10.10.0/26` : donne la plage des hôtes utilisables et le broadcast.
3. À quel réseau /26 appartient la machine `10.10.10.70` ?
4. Combien de réseaux /24 peut-on découper dans `10.10.0.0/16` ?
5. Deux machines `192.168.1.10/24` et `192.168.2.10/24` sont branchées sur le même switch. Peuvent-elles se parler directement ? Pourquoi ?
6. Tu dois prévoir un réseau pour 100 serveurs. Quel plus petit CIDR choisis-tu ?

### Corrigé

1. Masque `255.255.255.0`, 254 hôtes, broadcast `192.168.1.255`.
2. Un /26 fait des blocs de 64 adresses. Le réseau `10.10.10.0/26` couvre `.0` à `.63`. Hôtes utilisables : `.1` à `.62`. Broadcast : `10.10.10.63`.
3. Les blocs /26 démarrent à 0, 64, 128, 192. Le `.70` est dans le bloc qui commence à `.64` : réseau `10.10.10.64/26` (hôtes `.65` à `.126`, broadcast `.127`).
4. 2^(24-16) = 2⁸ = **256** réseaux /24.
5. **Non**, pas directement. Elles sont dans deux réseaux IP différents : la machine `192.168.1.10` ne verra pas `192.168.2.10` comme « locale » et enverra le trafic à sa passerelle. Sans routeur, rien ne passe.
6. 100 hôtes : un /25 donne 126 hôtes utilisables, c’est le plus petit qui convient (un /26 n’en donne que 62). En pratique, prends un /24 pour garder de la marge.

### Checkpoint

Tu sais expliquer à voix haute la différence entre un switch et un routeur, et calculer le nombre d’hôtes d’un CIDR sans aide. Sinon, refais les exercices 2 et 3 avec d’autres valeurs.

---

## Séance 1 : installer l’environnement (1 h)

### L’idée

Plutôt que d’acheter des équipements, on les **simule avec des conteneurs Docker**. **Containerlab** lit un fichier YAML qui décrit la topologie (les machines et les câbles entre elles) et construit le labo en quelques secondes. **FRRouting (FRR)** est un logiciel de routage professionnel (utilisé en production) qui transforme un conteneur Linux en vrai routeur. Pour toi qui connais Kubernetes, c’est la même logique « déclaratif et reproductible ».

### Manipulation

```bash
# Mise à jour et outils de base
sudo apt update
sudo apt install -y docker.io git make tcpdump python3-venv curl

# Autoriser ton utilisateur à utiliser Docker sans sudo
sudo usermod -aG docker $USER
# Puis déconnecte-toi / reconnecte-toi (ou : newgrp docker)

# Installer Containerlab (script officiel)
bash -c "$(curl -sL https://get.containerlab.dev)"

# Vérifications
docker run --rm hello-world
containerlab version
```

Si le script d’installation échoue ou si un paquet manque sur Ubuntu 26.04, consulte la documentation sur containerlab.dev : les méthodes d’installation sont à jour là-bas.

Télécharge les images dont on aura besoin :

```bash
docker pull quay.io/frrouting/frr:10.2.1      # le routeur (vérifie sur quay.io qu’un tag plus récent n’existe pas)
docker pull nicolaka/netshoot                  # la « machine utilisateur » avec tous les outils réseau
```

Crée le dépôt :

```bash
mkdir -p ~/reseau-lab/td1 && cd ~/reseau-lab
git init
echo "# Journal de labo" > journal.md
```

### Questions

1. Pourquoi utilise-t-on `netshoot` pour simuler un poste utilisateur plutôt qu’une image minimale ?
2. Quelle différence entre un conteneur et une VM, et pourquoi cela convient-il pour simuler un routeur ?

### Corrigé

1. `netshoot` contient `ping`, `traceroute`, `tcpdump`, `dig`, `ip`, `nmap`… Une image minimale n’a pas ces outils et il faudrait les installer à chaque fois.
2. Un conteneur partage le noyau de l’hôte et démarre en quelques secondes, avec peu de mémoire. Linux sait faire du routage dans son noyau, donc un conteneur avec FRR se comporte comme un vrai routeur logiciel. Limite : on ne simule pas le matériel (pas de ASIC, pas de CLI Cisco).

### Checkpoint

`docker run --rm hello-world` fonctionne sans sudo et `containerlab version` affiche un numéro de version.

---

## Séance 2 : ton premier réseau, un routeur et deux sous-réseaux (1 h 30)

### L’idée

On construit le plus petit réseau intéressant :

```
 pc1 (10.10.10.10/24) ---- r1 ---- pc2 (10.10.20.10/24)
                    .1 (eth1)   (eth2) .1
```

`pc1` et `pc2` sont dans **deux réseaux différents**. Pour se parler, ils doivent passer par `r1`, qui possède une adresse dans chaque réseau (`10.10.10.1` et `10.10.20.1`). Ces adresses sont les **passerelles** de chaque poste.

Note sur Containerlab : l’interface `eth0` de chaque conteneur est l’interface de gestion (réseau Docker). **Tes vrais câbles de labo commencent à `eth1`.**

**Autre particularité : les outils.** L’image FRR est minimale (Alpine) et ne contient ni `tcpdump`, ni `nft`, ni `wg`. Les postes `netshoot`, eux, ont tout. C’est pourquoi, dans les topologies de ce TD, la première ligne `exec` des routeurs est `sh -c "apk add --no-cache tcpdump && sysctl ..."` : elle installe les outils au démarrage (le routeur a accès à Internet via le réseau Docker). Si tu tombes sur `executable file not found`, deux solutions de secours, sans toucher au routeur :

```bash
# tcpdump de ton Ubuntu, dans l’espace réseau du routeur
sudo nsenter -t $(docker inspect -f '{{.State.Pid}}' clab-td2-r-siege) -n tcpdump -nei eth1 -c 10

# ou un conteneur netshoot qui partage le réseau du routeur
docker run --rm -it --network container:clab-td2-r-siege nicolaka/netshoot tcpdump -nei eth1 -c 10
```

### Manipulation

Dans `~/reseau-lab/td1/`, crée la structure :

```bash
cd ~/reseau-lab/td1
mkdir r1
```

**Fichier `r1/daemons`** (dit à FRR quels services démarrer) :

```
zebra=yes
staticd=yes
ospfd=yes
bgpd=no
ospf6d=no
ripd=no
ripngd=no
isisd=no
pimd=no
ldpd=no
nhrpd=no
eigrpd=no
babeld=no
sharpd=no
pbrd=no
bfdd=no
fabricd=no
vrrpd=no
pathd=no
vtysh_enable=yes
zebra_options="  -A 127.0.0.1 -s 90000000"
ospfd_options="   -A 127.0.0.1"
staticd_options="-A 127.0.0.1"
```

**Fichier `r1/frr.conf`** (configuration minimale) :

```
frr defaults traditional
hostname r1
log stdout
service integrated-vtysh-config
!
line vty
!
```

**Fichier `topology.yml`** :

```yaml
name: td1
topology:
  nodes:
    r1:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds:
        - r1/daemons:/etc/frr/daemons
        - r1/frr.conf:/etc/frr/frr.conf
      exec:
        - sh -c "apk add --no-cache tcpdump && sysctl -w net.ipv4.ip_forward=1"
        - ip addr add 10.10.10.1/24 dev eth1
        - ip addr add 10.10.20.1/24 dev eth2
    pc1:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.10.10.10/24 dev eth1
        - ip route replace default via 10.10.10.1
    pc2:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.10.20.10/24 dev eth1
        - ip route replace default via 10.10.20.1
  links:
    - endpoints: ["pc1:eth1", "r1:eth1"]
    - endpoints: ["pc2:eth1", "r1:eth2"]
```

Décryptage :

- `ip_forward=1` : autorise Linux à **transmettre** des paquets d’une interface à l’autre. Sans cela, ce n’est pas un routeur, juste une machine.
- `ip addr add … dev ethX` : donne une adresse IP à une interface.
- `ip route replace default via …` : « tout ce que tu ne connais pas, envoie-le à cette passerelle ».
- `links` : les câbles. `pc1:eth1` est relié à `r1:eth1`.

Lance le labo :

```bash
sudo containerlab deploy -t topology.yml
sudo containerlab inspect -t topology.yml
```

Les conteneurs s’appellent `clab-td1-pc1`, `clab-td1-pc2`, `clab-td1-r1`. Pour y entrer :

```bash
docker exec -it clab-td1-pc1 bash
```

**Expériences à faire (dans l’ordre) :**

```bash
# 1. Depuis pc1 : ping de la passerelle, puis de pc2
docker exec clab-td1-pc1 ping -c 3 10.10.10.1
docker exec clab-td1-pc1 ping -c 3 10.10.20.10

# 2. Observer le chemin
docker exec clab-td1-pc1 traceroute -n 10.10.20.10

# 3. Observer la table de routage et la table ARP de pc1
docker exec clab-td1-pc1 ip route
docker exec clab-td1-pc1 ip neigh

# 4. Capturer le trafic pendant un ping (deux terminaux)
# Terminal A :
docker exec clab-td1-pc2 tcpdump -ni eth1 -c 10
# Terminal B :
docker exec clab-td1-pc1 ping -c 3 10.10.20.10
```

**Casse volontairement quelque chose :**

```bash
# Supprime la passerelle de pc1 puis retente le ping vers pc2
docker exec clab-td1-pc1 ip route del default
docker exec clab-td1-pc1 ping -c 2 10.10.20.10

# Rétablis-la
docker exec clab-td1-pc1 ip route add default via 10.10.10.1
```

### Questions

1. Dans le résultat du `ping` vers `10.10.20.10`, quelle est la valeur du TTL ? Que te dit-elle ?
2. Que montre `traceroute` ? Combien de sauts ?
3. Dans la capture `tcpdump` sur `pc2`, quelle est l’adresse source des paquets ICMP ? Est-ce `10.10.10.10` ou `10.10.20.1` ? Pourquoi ?
4. Que contient la table `ip neigh` de `pc1` ? À quoi sert ARP ?
5. Après suppression de la route par défaut, quel message obtiens-tu ? Pourquoi `10.10.10.1` reste-t-il joignable alors que `10.10.20.10` ne l’est plus ?

### Corrigé

1. Le TTL est de **63**. Il part de 64 et chaque routeur traversé le décrémente de 1 : un TTL de 63 prouve qu’un routeur a été traversé. Le TTL sert à éviter qu’un paquet tourne indéfiniment en cas de boucle.
2. Deux lignes : d’abord `10.10.10.1` (le routeur `r1`), puis `10.10.20.10`. Deux sauts.
3. L’adresse source est `10.10.10.10`. Un routeur **ne change pas l’adresse IP source** (sauf NAT, vu plus tard). Il change en revanche les **adresses MAC** à chaque saut.
4. `ip neigh` contient la correspondance IP → adresse MAC des voisins directs (ici la passerelle `10.10.10.1`). **ARP** permet à une machine de demander « qui possède l’IP 10.10.10.1 ? » pour apprendre son adresse MAC, car sur un réseau local les trames circulent par adresses MAC.
5. `Network is unreachable`. `10.10.10.1` est dans le même sous-réseau que `pc1` : il est joignable directement, sans passerelle. `10.10.20.10` est dans un autre réseau : sans route par défaut, `pc1` ne sait pas par où l’envoyer.

### Checkpoint

`pc1` joint `pc2`, et tu sais expliquer pourquoi (passerelle, routage, TTL). Fais un `git commit` et ajoute 5 lignes dans `journal.md`.

Pour arrêter le labo : `sudo containerlab destroy -t topology.yml --cleanup`.

---

## Séance 3 : deux sites, du routage statique à OSPF (2 h)

### L’idée

Une entreprise a un **siège** et une **agence**. Chaque site a son propre routeur et ses propres réseaux. Pour que les deux sites communiquent, chaque routeur doit **connaître les réseaux de l’autre**. Il y a deux façons de le lui dire :

- **Routage statique** : tu écris à la main « pour joindre le réseau X, passe par Y ». Simple, mais à refaire à chaque changement, et rien ne s’adapte en cas de panne.
- **Routage dynamique (OSPF)** : les routeurs *s’échangent* automatiquement leurs réseaux et recalculent seuls les chemins si un lien tombe. C’est ce qu’on trouve dans presque toutes les entreprises.

Vocabulaire OSPF minimal :

- **Voisin (neighbor)** : un routeur directement connecté avec lequel on échange.
- **Zone** : un groupe de routeurs. On utilise la **zone 0** (aussi appelée *backbone*), la plus simple.
- **Router-ID** : le nom unique d’un routeur dans OSPF, souvent écrit comme une adresse IP (ex. `1.1.1.1`).
- **Full** : l’état d’un voisinage qui fonctionne parfaitement.

### Le plan d’adressage (à respecter)

Un bon plan d’adressage est écrit **avant** de construire. Voici le nôtre :

| Zone | Réseau | Usage |
| --- | --- | --- |
| Siège | `10.10.10.0/24` | VLAN 10, utilisateurs |
| Siège | `10.10.20.0/24` | VLAN 20, serveurs |
| Siège | `10.10.99.0/24` | VLAN 99, management |
| Agence | `10.20.10.0/24` | VLAN 10, utilisateurs |
| Agence | `10.20.99.0/24` | VLAN 99, management |
| Lien siège-agence | `172.16.0.0/30` | siège `.1`, agence `.2` |

Logique : `10.10.x.x` = siège, `10.20.x.x` = agence, le 3e octet = le VLAN. Quelqu’un qui lit une adresse sait tout de suite où elle se trouve : c’est le but d’un plan lisible.

Pour cette séance, on simplifie : un seul réseau par site (les VLAN arrivent en séance 4).

```
pc-s (10.10.10.10) --- r-siege --- (172.16.0.0/30) --- r-agence --- pc-a (10.20.10.10)
                   .1                .1          .2                 .1
```

### Manipulation, partie A : routage statique

```bash
cd ~/reseau-lab && mkdir -p td2/r-siege td2/r-agence && cd td2
cp ../td1/r1/daemons r-siege/daemons
cp ../td1/r1/daemons r-agence/daemons
```

**`r-siege/frr.conf`** :

```
frr defaults traditional
hostname r-siege
log stdout
service integrated-vtysh-config
!
ip route 10.20.10.0/24 172.16.0.2
!
line vty
!
```

**`r-agence/frr.conf`** :

```
frr defaults traditional
hostname r-agence
log stdout
service integrated-vtysh-config
!
ip route 10.10.10.0/24 172.16.0.1
!
line vty
!
```

La ligne `ip route <réseau> <prochain saut>` se lit : « pour joindre ce réseau, envoie au routeur dont l’adresse est celle-ci ».

**`topology.yml`** :

```yaml
name: td2
topology:
  nodes:
    r-siege:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds:
        - r-siege/daemons:/etc/frr/daemons
        - r-siege/frr.conf:/etc/frr/frr.conf
      exec:
        - sh -c "apk add --no-cache tcpdump && sysctl -w net.ipv4.ip_forward=1"
        - ip addr add 10.10.10.1/24 dev eth1
        - ip addr add 172.16.0.1/30 dev eth2
    r-agence:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds:
        - r-agence/daemons:/etc/frr/daemons
        - r-agence/frr.conf:/etc/frr/frr.conf
      exec:
        - sh -c "apk add --no-cache tcpdump && sysctl -w net.ipv4.ip_forward=1"
        - ip addr add 10.20.10.1/24 dev eth1
        - ip addr add 172.16.0.2/30 dev eth2
    pc-s:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.10.10.10/24 dev eth1
        - ip route replace default via 10.10.10.1
    pc-a:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.20.10.10/24 dev eth1
        - ip route replace default via 10.20.10.1
  links:
    - endpoints: ["pc-s:eth1", "r-siege:eth1"]
    - endpoints: ["r-siege:eth2", "r-agence:eth2"]
    - endpoints: ["pc-a:eth1", "r-agence:eth1"]
```

```bash
sudo containerlab deploy -t topology.yml
docker exec clab-td2-pc-s ping -c 3 10.20.10.10
docker exec clab-td2-pc-s traceroute -n 10.20.10.10
# Entrer dans la console du routeur FRR
docker exec -it clab-td2-r-siege vtysh
#   puis :   show ip route     (taper exit pour sortir)
```

### Manipulation, partie B : on passe à OSPF

Supprime les routes statiques et remplace-les par OSPF. Édite les `frr.conf` :

**`r-siege/frr.conf`** :

```
frr defaults traditional
hostname r-siege
log stdout
service integrated-vtysh-config
!
router ospf
 ospf router-id 1.1.1.1
 network 10.10.10.0/24 area 0
 network 172.16.0.0/30 area 0
 passive-interface eth1
!
line vty
!
```

**`r-agence/frr.conf`** : même chose avec `hostname r-agence`, `ospf router-id 2.2.2.2`, `network 10.20.10.0/24 area 0` et `network 172.16.0.0/30 area 0`, `passive-interface eth1`.

Explications :

- `network X area 0` : « active OSPF sur les interfaces dont l’adresse est dans X, et annonce ce réseau ».
- `passive-interface eth1` : on annonce le réseau des utilisateurs *sans* chercher de voisin OSPF de ce côté. Les postes n’ont pas à parler OSPF, et c’est une bonne pratique de sécurité.

Redéploie et vérifie :

```bash
sudo containerlab destroy -t topology.yml --cleanup
sudo containerlab deploy -t topology.yml

docker exec clab-td2-r-siege vtysh -c "show ip ospf neighbor"
docker exec clab-td2-r-siege vtysh -c "show ip route"
docker exec clab-td2-pc-s ping -c 3 10.20.10.10
```

OSPF met quelques secondes (environ 10 à 40 s) à établir le voisinage : si le premier test échoue, patiente et recommence.

### Questions

1. Dans `show ip route`, que signifient les lettres `C`, `S` et `O` en début de ligne ?
2. Quel est l’état du voisin OSPF dans `show ip ospf neighbor` ?
3. Coupe l’interface du lien (`docker exec clab-td2-r-agence ip link set eth2 down`), attends quelques secondes, regarde `show ip route` sur `r-siege`. Qu’observes-tu ? Remets ensuite le lien (`up`).
4. Pourquoi OSPF est-il préférable au routage statique quand il y a 20 sites ? Et quand n’y en a-t-il qu’un seul ?

### Corrigé

1. `C` = *connected* (réseau directement attaché à une interface du routeur), `S` = *static* (route écrite à la main), `O` = *OSPF* (route apprise dynamiquement d’un voisin).
2. `Full`. C’est l’état attendu : les deux routeurs ont synchronisé leurs informations. Si tu vois `Init` ou `2-Way` de façon persistante, vérifie les masques et les `network` des deux côtés.
3. La route `O` vers `10.20.10.0/24` disparaît : OSPF a détecté la perte du voisin et a retiré la route. Avec une route statique, elle serait restée dans la table (pointant vers un lien mort). Quand le lien revient, OSPF la réapprend seul.
4. Avec 20 sites, le statique demande de maintenir des dizaines de routes à la main et de les modifier à chaque ajout. OSPF s’adapte automatiquement. Avec un seul lien et deux sites, le statique est plus simple, plus léger et plus prévisible : choisir la complexité adaptée au besoin fait partie du métier.

### Checkpoint

`pc-s` joint `pc-a`, `show ip ospf neighbor` affiche `Full`, et tu as vu une route disparaître puis revenir. Commit + journal.

---

## Séance 4 : les VLAN (2 h)

### L’idée

Imagine un switch unique dans un bâtiment. Sans VLAN, **tous** les postes branchés dessus sont dans le même réseau : un invité branché dans la salle de réunion pourrait voir les serveurs. Un **VLAN** (Virtual LAN) découpe ce switch en plusieurs réseaux logiques étanches : un VLAN pour les utilisateurs, un pour les serveurs, un pour l’administration.

- Chaque trame est étiquetée avec un numéro de VLAN (norme **802.1Q**).
- Un port **access** appartient à un seul VLAN (le poste ne voit pas l’étiquette).
- Un port **trunk** transporte plusieurs VLAN en même temps, avec étiquettes : c’est le lien entre un switch et un routeur, ou entre deux switchs.
- **Les VLAN sont isolés** : pour passer de l’un à l’autre, il faut un routeur. C’est le **routage inter-VLAN**, et c’est là qu’on place les règles de filtrage.

On utilise ici le modèle « **router-on-a-stick** » : un seul câble (trunk) entre le switch et le routeur, et le routeur a une **sous-interface** par VLAN.

```
 pc-user (VLAN 10) --\
                      switch ==== trunk ==== r-siege
 pc-srv  (VLAN 20) --/             (eth1.10 / eth1.20)
```

### Manipulation

Dans `td2/`, on remplace `pc-s` par deux postes et un switch Linux VLAN-aware.

Créer un nouveau dossier `td3` : `mkdir -p ~/reseau-lab/td3 && cd ~/reseau-lab/td3` (copie-y `td2/r-siege`, `td2/r-agence` avec leurs `daemons` et `frr.conf` OSPF).

**Dans `r-siege/frr.conf`**, mets à jour les réseaux OSPF :

```
router ospf
 ospf router-id 1.1.1.1
 network 10.10.10.0/24 area 0
 network 10.10.20.0/24 area 0
 network 172.16.0.0/30 area 0
 passive-interface eth1.10
 passive-interface eth1.20
```

**`topology.yml`** :

```yaml
name: td3
topology:
  nodes:
    sw1:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip link add br0 type bridge vlan_filtering 1
        - ip link set eth1 master br0
        - ip link set eth2 master br0
        - ip link set eth3 master br0
        - ip link set br0 up
        - bridge vlan add dev eth1 vid 10 pvid untagged
        - bridge vlan add dev eth2 vid 20 pvid untagged
        - bridge vlan add dev eth3 vid 10
        - bridge vlan add dev eth3 vid 20
        - bridge vlan del dev eth1 vid 1
        - bridge vlan del dev eth2 vid 1
        - bridge vlan del dev eth3 vid 1
    r-siege:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds:
        - r-siege/daemons:/etc/frr/daemons
        - r-siege/frr.conf:/etc/frr/frr.conf
      exec:
        - sh -c "apk add --no-cache tcpdump && sysctl -w net.ipv4.ip_forward=1"
        - ip link set eth1 up
        - ip link add link eth1 name eth1.10 type vlan id 10
        - ip link add link eth1 name eth1.20 type vlan id 20
        - ip addr add 10.10.10.1/24 dev eth1.10
        - ip addr add 10.10.20.1/24 dev eth1.20
        - ip link set eth1.10 up
        - ip link set eth1.20 up
        - ip addr add 172.16.0.1/30 dev eth2
    r-agence:
      kind: linux
      image: quay.io/frrouting/frr:10.2.1
      binds:
        - r-agence/daemons:/etc/frr/daemons
        - r-agence/frr.conf:/etc/frr/frr.conf
      exec:
        - sh -c "apk add --no-cache tcpdump && sysctl -w net.ipv4.ip_forward=1"
        - ip addr add 10.20.10.1/24 dev eth1
        - ip addr add 172.16.0.2/30 dev eth2
    pc-user:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.10.10.10/24 dev eth1
        - ip route replace default via 10.10.10.1
    pc-srv:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.10.20.10/24 dev eth1
        - ip route replace default via 10.10.20.1
    pc-a:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 10.20.10.10/24 dev eth1
        - ip route replace default via 10.20.10.1
  links:
    - endpoints: ["pc-user:eth1", "sw1:eth1"]
    - endpoints: ["pc-srv:eth1", "sw1:eth2"]
    - endpoints: ["sw1:eth3", "r-siege:eth1"]
    - endpoints: ["r-siege:eth2", "r-agence:eth2"]
    - endpoints: ["pc-a:eth1", "r-agence:eth1"]
```

Ce que fait le switch `sw1` :

- `bridge ... vlan_filtering 1` : transforme un pont Linux en switch qui comprend les VLAN.
- `eth1` : port *access* VLAN 10 (`pvid untagged`) → `pc-user`.
- `eth2` : port *access* VLAN 20 → `pc-srv`.
- `eth3` : port *trunk* (VLAN 10 et 20 étiquetés) → le routeur.

Sur le routeur, `eth1.10` et `eth1.20` sont les **sous-interfaces** : la partie `.10` correspond au numéro de VLAN.

```bash
sudo containerlab deploy -t topology.yml
docker exec clab-td3-sw1 bridge vlan show
docker exec clab-td3-pc-user ping -c 3 10.10.10.1
docker exec clab-td3-pc-user ping -c 3 10.10.20.10
docker exec clab-td3-pc-user ping -c 3 10.20.10.10
```

**Expérience : observer les étiquettes 802.1Q**

```bash
# Terminal A : capturer sur le trunk (côté routeur) avec l’affichage des VLAN
docker exec clab-td3-r-siege tcpdump -nei eth1 -c 10 icmp
# Terminal B :
docker exec clab-td3-pc-user ping -c 3 10.10.20.10
```

### Questions

1. Dans la capture sur le trunk, quel numéro de VLAN voit-on devant les trames ? Que voit `pc-user` de son côté (a-t-il connaissance du VLAN) ?
2. `pc-user` et `pc-srv` sont sur le même switch. Pourquoi doivent-ils passer par le routeur pour se parler ?
3. Que se passe-t-il si tu changes `pc-srv` pour qu’il utilise l’adresse `10.10.10.50/24` sans toucher au switch ?
4. Pourquoi sépare-t-on les VLAN utilisateurs et serveurs d’un point de vue sécurité ?

### Corrigé

1. La capture montre `vlan 10` (puis `vlan 20` pour le trafic retour). `pc-user` ne voit rien : le port *access* retire l’étiquette avant de livrer la trame.
2. Parce qu’ils sont dans des VLAN différents, donc des réseaux IP différents (`10.10.10.0/24` et `10.10.20.0/24`). Le switch ne fait pas passer les trames d’un VLAN à l’autre.
3. Rien de bon : `pc-srv` a une adresse du réseau 10.10.10.0/24 mais est dans le VLAN 20. Le switch ne transporte pas ses trames dans le VLAN 10, donc il n’atteint personne. Cela illustre qu’une adresse IP **doit** correspondre au VLAN où le port est configuré. C’est une panne classique de terrain.
4. Parce que tout le trafic entre les deux doit passer par le routeur, où l’on peut appliquer un pare-feu (semaine 3). Un poste utilisateur compromis ne peut pas scanner directement le réseau des serveurs.

### Checkpoint

Les trois pings fonctionnent, tu as vu les étiquettes VLAN dans `tcpdump`, et tu sais expliquer la différence port *access* / *trunk*. Commit + journal.

---

## Séance 5 : DHCP, DNS et NAT (2 h)

### L’idée

Jusqu’ici, on a tapé les adresses à la main. En entreprise, ce n’est pas possible pour des centaines de postes. Trois services rendent le réseau « vivant » :

- **DHCP** : un poste qui se branche demande « donne-moi une adresse ». Le serveur répond avec : une IP, un masque, une passerelle, un serveur DNS.
- **DNS** : on tape `srv.lab.local` plutôt que `10.10.20.10`.
- **NAT** (*masquerade*) : les adresses privées (`10.x.x.x`) ne sont pas routées sur Internet. À la sortie, le routeur remplace l’adresse source par sa propre adresse publique, et mémorise la correspondance pour renvoyer les réponses au bon poste.

On utilise **dnsmasq**, qui fait DHCP et DNS en un seul programme.

### Manipulation

On ajoute à la topologie du TD3 :

- un nœud `inet` (un « routeur Internet » simulé) avec une adresse `203.0.113.1/24` (plage réservée à la documentation) ;
- un lien `r-siege:eth3 ↔ inet:eth1` avec `r-siege eth3 = 203.0.113.2/24` ;
- un service DHCP/DNS (dnsmasq) qui tourne **sur `r-siege`**, dans le VLAN 10 (voir plus bas).

**Ajouts dans `topology.yml`** :

```yaml
    inet:
      kind: linux
      image: nicolaka/netshoot
      exec:
        - ip addr add 203.0.113.1/24 dev eth1
        - ip addr add 8.8.8.8/32 dev lo
```

et dans `links` : `- endpoints: ["r-siege:eth3", "inet:eth1"]`, et pour `r-siege` ajoute `exec: ip addr add 203.0.113.2/24 dev eth3` et `ip route add default via 203.0.113.1`.

Ajoute dans `inet` une route de retour pour que les réponses puissent revenir (vers l’adresse publique du routeur, qui est directement connectée : ici rien à ajouter). L’adresse `8.8.8.8/32` sur `lo` simule un « serveur Internet ».

**NAT avec nftables, sur `r-siege`** :

```bash
docker exec clab-td3-r-siege sh -c '
nft add table ip nat
nft add chain ip nat postrouting { type nat hook postrouting priority 100 \; }
nft add rule ip nat postrouting oifname "eth3" masquerade
'
```

(Le conteneur FRR est basé sur Alpine et n’a pas `nft` par défaut : dans la ligne `apk add` de l’`exec` de `r-siege`, ajoute `nftables`, soit `apk add --no-cache tcpdump nftables dnsmasq`. À défaut, `iptables -t nat -A POSTROUTING -o eth3 -j MASQUERADE` fait la même chose.)

Test :

```bash
docker exec clab-td3-pc-user ping -c 3 8.8.8.8
# Sur inet, capturer et regarder l’adresse source
docker exec clab-td3-inet tcpdump -ni eth1 -c 6 icmp
```

**DHCP et DNS avec dnsmasq, sur `r-siege`**

Quand un poste démarre sans adresse, il envoie un message en *broadcast* : « y a-t-il un serveur DHCP ? ». Ce message reste dans son VLAN et ne traverse pas un routeur. Le serveur DHCP doit donc se trouver **dans le même VLAN que les postes**. Le plus simple est de le placer sur `r-siege`, qui a déjà une interface dans le VLAN 10 (`eth1.10`, `10.10.10.1`). Un serveur placé ailleurs (par exemple sur `pc-srv`, dans le VLAN 20) exigerait un *relais DHCP* sur le routeur : on n’en a pas besoin ici.

L’échange tient en quatre messages : **Discover** (le poste demande), **Offer** (le serveur propose), **Request** (le poste accepte), **Ack** (le serveur confirme).

**Étape 1 : le fichier de configuration.** Crée `td3/dnsmasq.conf` :

```
interface=eth1.10
bind-interfaces
no-resolv
domain=lab.local
local=/lab.local/
dhcp-range=10.10.10.100,10.10.10.200,255.255.255.0,12h
dhcp-option=option:router,10.10.10.1
dhcp-option=option:dns-server,10.10.10.1
address=/srv.lab.local/10.10.20.10
address=/pc-a.lab.local/10.20.10.10
```

| Ligne | Rôle |
| --- | --- |
| `interface=eth1.10` et `bind-interfaces` | n’écouter que sur le VLAN 10 |
| `no-resolv` | ne pas chercher de DNS externe (le labo n’a pas de vrai Internet) |
| `domain` et `local` | le domaine `lab.local` est géré par ce serveur |
| `dhcp-range` | adresses distribuées de `.100` à `.200`, bail de 12 h |
| `dhcp-option router` | la passerelle donnée aux postes |
| `dhcp-option dns-server` | le serveur DNS donné aux postes (le routeur lui-même) |
| `address=/nom/IP` | les enregistrements DNS du labo |

**Étape 2 : le monter dans le routeur.** Dans `topology.yml`, pour le nœud `r-siege` : ajoute le fichier dans `binds`, ajoute `nftables dnsmasq` à la ligne `apk add`, et lance le service en **dernière** ligne de l’`exec` (une fois les interfaces créées).

```yaml
    r-siege:
      binds:
        - r-siege/daemons:/etc/frr/daemons
        - r-siege/frr.conf:/etc/frr/frr.conf
        - dnsmasq.conf:/etc/dnsmasq.conf
      exec:
        - sh -c "apk add --no-cache tcpdump nftables dnsmasq && sysctl -w net.ipv4.ip_forward=1"
        # ... les lignes ip link / ip addr / ip route inchangées ...
        - dnsmasq
```

**Étape 3 : redéployer et vérifier.**

```bash
sudo containerlab destroy -t topology.yml --cleanup
sudo containerlab deploy -t topology.yml
docker exec clab-td3-r-siege pgrep -a dnsmasq     # doit afficher un processus
```

Si rien ne s’affiche, lance-le à la main : `docker exec clab-td3-r-siege dnsmasq`.

**Étape 4 : tester.** `pc-user` a une adresse fixe donnée par la topologie : on la retire pour qu’il doive la demander.

```bash
docker exec clab-td3-pc-user ip addr flush dev eth1
docker exec clab-td3-pc-user ip addr show eth1        # plus d’adresse IPv4
docker exec clab-td3-pc-user udhcpc -i eth1 -n -q     # ou : dhclient -v eth1
docker exec clab-td3-pc-user ip addr show eth1        # une adresse entre .100 et .200
docker exec clab-td3-pc-user ip route                 # la passerelle a été configurée

# Le DNS : dig interroge directement le serveur indiqué avec @
docker exec clab-td3-pc-user dig @10.10.10.1 srv.lab.local +short    # 10.10.20.10

# ping, lui, utilise /etc/resolv.conf : dans un conteneur, udhcpc ne le met pas à jour
docker exec clab-td3-pc-user cat /etc/resolv.conf     # un autre serveur que 10.10.10.1
docker exec clab-td3-pc-user sh -c 'echo "nameserver 10.10.10.1" > /etc/resolv.conf'
docker exec clab-td3-pc-user ping -c 2 srv.lab.local  # fonctionne maintenant
```

Sur un vrai poste, le client DHCP écrit lui-même le serveur DNS dans la configuration de la machine. Ici, c’est un conteneur dont Docker gère `resolv.conf` : on le fait à la main. Retiens l’idée générale : `dig @serveur` teste **le serveur DNS**, alors que `ping nom` teste **la configuration DNS du poste**. Quand l’un marche et pas l’autre, le problème est côté poste.

**Étape 5 : voir les quatre messages.** Dans un second terminal, lance la capture, puis relance `udhcpc` :

```bash
docker exec clab-td3-r-siege tcpdump -ni eth1.10 port 67 or port 68
```

Tu verras le Discover partir de `0.0.0.0` vers `255.255.255.255` : le poste n’a pas encore d’adresse et s’adresse à tout le monde.

### Questions

1. Dans la capture sur `inet`, quelle adresse source voit-on pour le ping de `pc-user` ? Pourquoi ?
2. Pourquoi le NAT n’est-il pas nécessaire entre le siège et l’agence ?
3. Pourquoi un broadcast DHCP ne traverse-t-il pas un routeur, et comment contourne-t-on cela ?
4. Que se passe-t-il si le serveur DNS tombe ? Les pings par IP fonctionnent-ils encore ?

### Corrigé

1. L’adresse source est `203.0.113.2`, celle du routeur, et non `10.10.10.10`. Le NAT a remplacé l’adresse privée. `inet` ne connaît d’ailleurs pas `10.10.10.0/24` : il ne pourrait pas répondre sans cette traduction.
2. Parce que les deux sites utilisent des adresses privées dans le même plan d’adressage, et que les routeurs les connaissent via OSPF. Le NAT ne sert qu’à sortir vers un réseau qui ne connaît pas nos adresses.
3. Un broadcast est limité à son réseau local par conception. On installe un **relais DHCP** (*DHCP relay*, `ip helper-address` chez Cisco) sur le routeur, qui transmet la demande en unicast vers le serveur.
4. Les pings par IP continuent de fonctionner : le DNS n’est qu’un annuaire. Seule la résolution des noms échoue. Savoir distinguer « le réseau est en panne » de « le DNS est en panne » est un réflexe essentiel : `ping 8.8.8.8` fonctionne mais `ping google.com` échoue, c’est le DNS.

### Checkpoint

`pc-user` accède à `8.8.8.8` via NAT, et `dig` résout `srv.lab.local`. Commit + journal.

---

## Séance 6 : les pannes volontaires (1 h 30)

### L’idée

Un technicien réseau passe une grande partie de son temps à **diagnostiquer**. La méthode est toujours la même : partir du bas (physique) vers le haut (applications), et **isoler** où ça casse.

**La méthode en 5 questions :**

1. L’interface est-elle `up` ? (`ip link`)
2. Ai-je une bonne adresse et un bon masque ? (`ip addr`)
3. Ai-je une route vers la destination ? (`ip route`)
4. La destination répond-elle, et où s’arrêtent les paquets ? (`ping`, `traceroute`, `mtr`)
5. Si les noms échouent mais pas les IP, c’est le DNS (`dig`).

En dernier recours : `tcpdump` pour voir ce qui passe réellement.

### Manipulation : trois incidents à provoquer puis résoudre

Fais-toi **casser le labo par un camarade imaginaire** : provoque la panne, ferme les yeux sur la cause, puis diagnostique comme si tu ne la connaissais pas (attends 1 minute entre les deux pour oublier).

**Incident 1 : lien coupé**

```bash
docker exec clab-td3-r-agence ip link set eth2 down
```

Symptôme à constater : `pc-user` ne joint plus `pc-a`. Utilise la méthode pour retrouver la cause, puis répare avec `ip link set eth2 up`.

**Incident 2 : mauvais masque**

```bash
docker exec clab-td3-pc-user ip addr flush dev eth1
docker exec clab-td3-pc-user ip addr add 10.10.10.10/16 dev eth1
```

Symptôme : certains pings marchent, d’autres non, de façon inexplicable. Cherche pourquoi (indice : regarde `ip route`).

**Incident 3 : route manquante**

```bash
docker exec clab-td3-r-siege vtysh -c "conf t" -c "router ospf" -c "no network 10.10.20.0/24 area 0"
```

Symptôme : l’agence ne joint plus le VLAN 20 mais joint le VLAN 10. Retrouve pourquoi avec `show ip route` sur `r-agence`.

### Le format du journal d’incident (à remplir pour chaque panne)

| Champ | Contenu |
| --- | --- |
| Symptôme | Ce que l’utilisateur constate |
| Hypothèses | Ce que tu as pensé en premier |
| Commandes utilisées | Et ce qu’elles ont montré |
| Cause racine | La vraie cause |
| Correction | Ce que tu as fait |
| Prévention | Comment éviter que ça se reproduise (supervision, documentation…) |

### Corrigé

- **Incident 1** : `ip link` montre `eth2` en `DOWN` côté agence. `show ip ospf neighbor` n’affiche plus de voisin. Cause : lien physique. Prévention : supervision de l’état des liens (semaine 3).
- **Incident 2** : le masque `/16` fait croire à `pc-user` que `10.10.20.10` est **local** (même réseau). Il l’appelle donc directement en ARP au lieu de passer par la passerelle, et ça échoue. Règle : un masque faux produit des pannes **partielles** et déroutantes, les plus difficiles à trouver.
- **Incident 3** : `r-agence` n’a plus la route `10.10.20.0/24` car le siège ne l’annonce plus. Prévention : documenter le plan d’adressage et vérifier la table de routage avec un script (semaine 4).

### Checkpoint et bilan de la semaine 2

Tu as : un dépôt Git avec topologies et configs, un plan d’adressage, un schéma (à dessiner avec draw.io) et un journal de 3 incidents. Prépare aussi un **document d’architecture d’une page** : objectif, schéma, plan d’adressage, protocoles utilisés (OSPF, VLAN, NAT, DHCP/DNS).

Autoévaluation : tu es prêt pour la semaine 3 si tu peux expliquer, sans notes, ce qui se passe quand `pc-user` ping `8.8.8.8` (ARP, passerelle, VLAN, routage, NAT, retour).

---

# SEMAINE 3 : SÉCURITÉ, RÉSILIENCE ET SUPERVISION

À partir d’ici, le TD te guide moins pas à pas : tu as appris les gestes en semaine 2, tu les appliques maintenant. Quand une configuration est difficile ou longue, elle est fournie. Sinon, c’est à toi d’écrire (indices à l’appui). C’est exactement ce qu’on attend sur le terrain.

## Séance 7 : la topologie « production » avec deux opérateurs (2 h)

### L’idée

En entreprise, on ne dépend jamais d’un seul lien Internet. On souscrit **deux opérateurs** (ISP-A principal, ISP-B secours). Le routeur de bordure choisit lequel utiliser et bascule si l’un tombe. C’est exactement la mission « suivi proactif des liens opérateurs » de l’annonce.

Dans le labo, `r-siege` joue le rôle de **routeur de bordure + pare-feu** (en production, ce sont souvent deux équipements distincts, mais le principe est identique).

```
                         isp-a ----+
                        /           \
  LAN (VLAN10/20) -- r-siege         internet ---- attacker
                   |    \           /      \
                  DMZ    isp-b ----+        r-agence -- LAN agence
                (srv-dmz)
```

### Plan d’adressage à respecter

| Lien | Réseau | Côté 1 | Côté 2 |
| --- | --- | --- | --- |
| r-siege ↔ isp-a | `198.51.100.0/30` | r-siege eth3 = `.2` | isp-a eth1 = `.1` |
| r-siege ↔ isp-b | `203.0.113.0/30` | r-siege eth4 = `.2` | isp-b eth1 = `.1` |
| isp-a ↔ internet | `192.0.2.0/30` | isp-a eth2 = `.1` | internet eth1 = `.2` |
| isp-b ↔ internet | `192.0.2.4/30` | isp-b eth2 = `.5` | internet eth2 = `.6` |
| internet ↔ r-agence | `192.0.2.8/30` | internet eth3 = `.9` | r-agence eth2 = `.10` |
| internet ↔ attacker | `192.0.2.12/30` | internet eth4 = `.13` | attacker eth1 = `.14` |
| r-siege ↔ DMZ | `10.10.30.0/24` | r-siege eth5 = `.1` | srv-dmz eth1 = `.10` |
| Tunnel WireGuard | `10.99.0.0/30` | siège `.1` | agence `.2` |

Le LAN (sw1, pc-user, pc-srv) et l’agence (`10.20.10.0/24`) reprennent le TD3. Le lien direct `r-siege:eth2 ↔ r-agence:eth2` **disparaît** : désormais, siège et agence se parlent à travers Internet, donc **via un VPN**.

### À faire

1. Dans `~/reseau-lab/td4/`, écris `topology.yml` (nom `td4`) en t’inspirant du TD3. Les adresses ci-dessus sont ton cahier des charges. Les nœuds `isp-a`, `isp-b` et `internet` sont de simples routeurs `netshoot` avec `ip_forward=1`.
2. Sur `r-siege`, **supprime la route par défaut de gestion** de Containerlab avant d’ajouter les tiennes : `ip route del default` (l’interface `eth0` reste joignable, c’est un réseau directement connecté).
3. Ajoute les routes manquantes (indice : chaque routeur doit savoir joindre les réseaux qui ne lui sont pas directement connectés) :
   - `isp-a` : `default via 192.0.2.2` ; `isp-b` : `default via 192.0.2.6`
   - `internet` : `198.51.100.0/30 via 192.0.2.1` et `203.0.113.0/30 via 192.0.2.5`
   - `r-siege` : deux routes par défaut, voir séance 10 (pour l’instant, une seule via `isp-a`)
   - `r-agence` : `default via 192.0.2.9`
4. Active le NAT (masquerade) sur `r-siege` pour `eth3` et `eth4`, et sur `r-agence` pour `eth2`.
5. Ajoute `8.8.8.8/32` sur l’interface `lo` du nœud `internet` pour simuler un serveur public.

**Outils sur les routeurs.** Dans la ligne `apk add` de l’`exec` de `r-siege` et de `r-agence`, installe tout ce qui servira : `apk add --no-cache tcpdump nftables wireguard-tools iperf3`. Cette ligne doit rester **la première** : une fois la route par défaut de gestion supprimée (étape 2), `apk` n’a plus accès à Internet.

### Questions

1. Pourquoi `internet` a-t-il besoin de routes vers `198.51.100.0/30` et `203.0.113.0/30` ?
2. Qu’arrive-t-il aux paquets de `pc-user` vers `8.8.8.8` si tu oublies le NAT sur `r-siege` ?

### Corrigé

1. Il ne connaît que ses réseaux directement connectés. Pour répondre à `r-siege` (adresse source `198.51.100.2` ou `203.0.113.2`), il doit savoir qu’il faut renvoyer par `isp-a` ou `isp-b`. Sans route de retour, les paquets partent mais les réponses se perdent : le symptôme classique du « ça sort, mais ça ne revient pas ».
2. Les paquets partent avec l’adresse source privée `10.10.10.10`. `internet` n’a aucune route vers ce réseau privé, ou les routeurs d’Internet ignorent ces adresses : pas de réponse. En capture, on voit les requêtes sortir mais aucune réponse.

### Checkpoint

`pc-user` joint `8.8.8.8` via `isp-a`. `pc-a` (agence) joint `8.8.8.8` aussi. Le siège et l’agence ne se joignent pas encore directement (c’est normal : pas de VPN).

---

## Séance 8 : le pare-feu et la DMZ (2 h)

### L’idée

Un pare-feu applique une règle simple : **tout ce qui n’est pas explicitement autorisé est interdit** (politique `drop` par défaut). On découpe le réseau en **zones** et on décide quels flux sont permis entre elles.

| Zone | Réseau | Niveau de confiance |
| --- | --- | --- |
| LAN utilisateurs | `10.10.10.0/24` | Moyen |
| LAN serveurs | `10.10.20.0/24` | Élevé (à protéger) |
| DMZ | `10.10.30.0/24` | Faible (exposé à Internet) |
| WAN (Internet) | `eth3`, `eth4` | Aucun |

La **DMZ** (zone démilitarisée) héberge ce qui doit être joignable depuis Internet (un site web, un serveur de messagerie). Si la DMZ est compromise, l’attaquant reste coincé : elle n’a pas le droit d’aller vers le LAN.

Pour le pare-feu on utilise **nftables**, l’outil par défaut sous Linux récent. Sa logique : des **tables** contiennent des **chaînes** (`input` = vers le routeur lui-même, `forward` = qui traverse le routeur, `output` = émis par le routeur), qui contiennent des **règles** lues de haut en bas.

### La matrice de flux (à remplir *avant* d’écrire les règles)

| Source → Destination | Autorisé ? | Port |
| --- | --- | --- |
| LAN utilisateurs → Internet | Oui | tout |
| LAN utilisateurs → LAN serveurs | Oui | TCP 80, 443 |
| LAN serveurs → LAN utilisateurs | Non (sauf réponses) | – |
| Internet → DMZ | Oui | TCP 443 uniquement |
| DMZ → LAN (tous) | Non | – |
| DMZ → Internet | Oui, limité | TCP 443, UDP 53 |
| Agence (via VPN) → LAN serveurs | Oui | TCP 443 |
| Internet → routeur lui-même | Seulement WireGuard | UDP 51820 |

### Manipulation

Crée `td4/firewall.nft` :

```
flush ruleset

table inet filter {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    iifname "lo" accept
    iifname "eth0" accept                      # gestion Containerlab / supervision
    ip protocol icmp icmp type echo-request limit rate 10/second accept
    iifname { "eth3", "eth4" } udp dport 51820 accept   # WireGuard
    log prefix "FW-INPUT-DROP " limit rate 5/second
  }

  chain forward {
    type filter hook forward priority 0; policy drop;
    ct state established,related accept

    # LAN utilisateurs
    iifname "eth1.10" oifname { "eth3", "eth4" } accept
    iifname "eth1.10" oifname "eth1.20" tcp dport { 80, 443 } accept

    # Internet vers DMZ (apres DNAT : adresse de destination 10.10.30.10)
    iifname { "eth3", "eth4" } oifname "eth5" ip daddr 10.10.30.10 tcp dport 443 accept

    # DMZ vers Internet (limite)
    iifname "eth5" oifname { "eth3", "eth4" } tcp dport 443 accept
    iifname "eth5" oifname { "eth3", "eth4" } udp dport 53 accept

    # Agence via VPN
    iifname "wg0" oifname "eth1.20" tcp dport 443 accept
    iifname "wg0" oifname "eth1.10" accept
    iifname "eth1.10" oifname "wg0" accept

    log prefix "FW-FWD-DROP " limit rate 5/second
  }
}

table ip nat {
  chain prerouting {
    type nat hook prerouting priority -100;
    iifname { "eth3", "eth4" } tcp dport 443 dnat to 10.10.30.10
  }
  chain postrouting {
    type nat hook postrouting priority 100;
    oifname { "eth3", "eth4" } masquerade
  }
}
```

Ce qu’il faut comprendre dans ce fichier :

- `policy drop` : tout est refusé tant qu’une règle ne l’autorise pas.
- `ct state established,related accept` : on laisse passer les **réponses** à des connexions déjà autorisées (le pare-feu est *à états*, il se souvient des connexions). Sans cette ligne, rien ne revient.
- `dnat to` : redirige le trafic arrivant sur le port 443 de l’adresse publique vers le serveur de la DMZ (le serveur n’a pas d’adresse publique).
- La dernière règle `log` de chaque chaîne enregistre les paquets refusés (utile pour diagnostiquer).

Charge-le : `docker cp td4/firewall.nft clab-td4-r-siege:/firewall.nft` puis `docker exec clab-td4-r-siege nft -f /firewall.nft`.

**Serveur de test en DMZ** (ce n’est pas du vrai TLS ; l’objet est le port, pas le chiffrement) :

```bash
docker exec -d clab-td4-srv-dmz socat TCP-LISTEN:443,fork,reuseaddr \
  SYSTEM:'printf "HTTP/1.1 200 OK\r\nContent-Length: 6\r\n\r\nDMZ OK\n"'
```

**Test depuis l’« Internet » (nœud `attacker`)** :

```bash
docker exec clab-td4-attacker nmap -Pn -p 22,80,443,3389 198.51.100.2
docker exec clab-td4-attacker curl -sk --max-time 3 https://198.51.100.2 || true
```

### Questions

1. Que montre `nmap` pour les ports 22, 80 et 3389, et pour le port 443 ? Quelle différence entre un port **filtered** et un port **closed** ?
2. Pourquoi ne mettons-nous pas le serveur web directement dans le LAN serveurs ?
3. Depuis `pc-srv`, essaie de joindre `pc-user` (ping). Pourquoi échoue-t-il alors que l’inverse (`pc-user` → `pc-srv` sur le port 443) réussit ?
4. Comment retrouver les paquets bloqués ? (indice : `dmesg` ou `nft monitor` dans le conteneur)

### Corrigé

1. Les ports 22, 80, 3389 apparaissent `filtered` (le pare-feu ignore silencieusement les paquets), et 443 `open`. Un port `closed` répond activement « personne n’écoute ici » (RST) ; `filtered` ne répond rien : c’est le comportement d’un `drop`. En production, `drop` complique la tâche des scanners.
2. Si le serveur exposé est compromis, l’attaquant serait déjà dans le réseau interne. La DMZ **limite le rayon d’explosion** : de là, aucun accès vers le LAN.
3. La règle `forward` n’autorise `eth1.20 → eth1.10` que pour les réponses (`ct state established`). Une nouvelle connexion initiée par le serveur est refusée. Un serveur ne devrait pas initier de connexions vers les postes : c’est ce qui empêche un serveur compromis de se propager.
4. Les lignes `log` produisent des messages noyau (`dmesg`). Dans un conteneur, on peut aussi utiliser `nft monitor trace` après avoir activé `meta nftrace set 1` sur le flux. Dans tous les cas : les refus doivent être *visibles* quelque part.

### Checkpoint

`nmap` depuis `attacker` ne montre que le 443 ouvert ; `pc-user` joint le serveur en 443 mais pas en 22. Sauvegarde `firewall.nft` dans Git (commit + journal).

---

## Séance 9 : le VPN site-à-site avec WireGuard (1 h 30)

### L’idée

Le siège et l’agence sont reliés **à travers Internet**, un réseau public. Pour que leur trafic interne reste confidentiel, on crée un **tunnel chiffré** entre les deux routeurs : un **VPN site-à-site**. Les paquets inter-sites sont chiffrés, encapsulés dans de l’UDP, et envoyés d’un routeur à l’autre. Aux deux bouts, les postes ne voient rien : ils pensent être sur un même réseau.

**WireGuard** est un VPN moderne, intégré au noyau Linux. Chaque extrémité a une **paire de clés** (privée, publique). On échange uniquement les clés publiques, et on déclare pour chaque pair les **AllowedIPs** (les adresses qu’il a le droit de joindre à travers le tunnel). Les `AllowedIPs` jouent à la fois le rôle de route et de contrôle d’accès.

### Manipulation

(Si `wg` est absent du conteneur, installe-le avec `apk add wireguard-tools`.)

```bash
# --- Générer les clés (sur ton hôte, par exemple) ---
wg genkey | tee priv_s | wg pubkey > pub_s
wg genkey | tee priv_a | wg pubkey > pub_a

# --- Siège (r-siege) ---
docker cp priv_s clab-td4-r-siege:/priv
docker exec clab-td4-r-siege sh -c '
ip link add wg0 type wireguard
ip addr add 10.99.0.1/30 dev wg0
wg set wg0 listen-port 51820 private-key /priv \
  peer '"$(cat pub_a)"' allowed-ips 10.99.0.2/32,10.20.10.0/24 \
  endpoint 192.0.2.10:51820 persistent-keepalive 25
ip link set wg0 up mtu 1380
ip route add 10.20.10.0/24 dev wg0
'

# --- Agence (r-agence) ---
docker cp priv_a clab-td4-r-agence:/priv
docker exec clab-td4-r-agence sh -c '
ip link add wg0 type wireguard
ip addr add 10.99.0.2/30 dev wg0
wg set wg0 listen-port 51820 private-key /priv \
  peer '"$(cat pub_s)"' allowed-ips 10.99.0.1/32,10.10.10.0/24,10.10.20.0/24 \
  endpoint 198.51.100.2:51820 persistent-keepalive 25
ip link set wg0 up mtu 1380
ip route add 10.10.10.0/24 dev wg0
ip route add 10.10.20.0/24 dev wg0
'
```

Un `mtu 1380` (au lieu de 1500) laisse la place pour l’en-tête d’encapsulation ; un MTU trop grand provoque des problèmes subtils (grosses requêtes qui bloquent, petits pings qui passent).

Note : on utilise des **routes statiques** via `wg0` entre les sites. OSPF fonctionne aussi à l’intérieur de chaque site, mais le faire passer dans un tunnel WireGuard demande des réglages supplémentaires (pas de multicast natif) : on garde ça pour plus tard.

Vérifications :

```bash
docker exec clab-td4-r-siege wg show
docker exec clab-td4-pc-user ping -c 3 10.20.10.10

# Preuve du chiffrement : capturer sur le « réseau Internet »
docker exec clab-td4-internet tcpdump -ni eth1 -c 8
# (pendant qu’un ping tourne dans une autre fenêtre)
```

### Questions

1. Dans la capture sur `internet`, voit-on des paquets ICMP ou UDP ? Peut-on lire les adresses `10.x.x.x` ?
2. Dans `wg show`, que signifie la ligne `latest handshake` ? Que se passe-t-il si elle dépasse plusieurs minutes alors que `persistent-keepalive` est actif ?
3. Pourquoi les `AllowedIPs` sont-elles différentes d’un côté à l’autre ?
4. Le pare-feu de `r-siege` doit autoriser deux choses pour que le tunnel fonctionne. Lesquelles ?

### Corrigé

1. On ne voit que des paquets **UDP** entre `198.51.100.2` (ou `192.0.2.x`) et `192.0.2.10`, sur le port 51820. Les `10.x.x.x` sont invisibles : tout est chiffré à l’intérieur. C’est ta preuve concrète de confidentialité.
2. C’est l’horodatage de la dernière négociation de clés réussie. Si elle dépasse plusieurs minutes malgré le keepalive, le tunnel est probablement coupé (pare-feu, route, ISP).
3. Chaque côté déclare ce qu’il accepte de recevoir de l’autre : le siège accepte l’agence (`10.20.10.0/24`), l’agence accepte le siège (`10.10.10.0/24` et `10.10.20.0/24`). Ce sont les réseaux **distants** vus de chaque côté.
4. L’**entrée** UDP 51820 sur la chaîne `input` (pour le tunnel lui-même) et le **transit** `wg0 ↔ LAN` sur la chaîne `forward` (pour le trafic à l’intérieur du tunnel). Oublier l’un des deux est une erreur très fréquente.

### Checkpoint

`pc-user` joint `pc-a` ; la capture sur `internet` ne montre que de l’UDP 51820 ; `pc-a` ne peut joindre le LAN serveurs que sur le port 443. Commit + journal.

---

## Séance 10 : la bascule entre opérateurs et les conditions réelles (2 h)

### L’idée

Le routeur de bordure a deux routes par défaut, avec des **métriques** différentes : celle qui a la métrique **la plus basse** est préférée.

```bash
ip route del default
ip route add default via 198.51.100.1 dev eth3 metric 10   # ISP-A (principal)
ip route add default via 203.0.113.1  dev eth4 metric 20   # ISP-B (secours)
```

**Problème** : si `isp-a` perd sa liaison *vers Internet* mais que le câble entre `r-siege` et `isp-a` reste actif, l’interface `eth3` est toujours `up` : le noyau ne retire pas la route. Le trafic part dans le vide. C’est une panne **silencieuse** typique (l’opérateur a un souci en amont, ton routeur ne le voit pas). Il faut donc une **sonde** qui teste réellement la joignabilité de bout en bout, et retire la route si la sonde échoue.

### Manipulation, partie A : la sonde de bascule (en Python)

Le script tourne sur ton hôte et pilote les conteneurs. Crée `td4/watchdog.py` :

```python
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
        sh(f"ip route replace default via {l['gw']} dev {l['dev']} metric {l['metric']}")


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
                    s["up"] = True
                    print(time.strftime("%H:%M:%S"), l["name"], "RETABLI")
            else:
                s["oks"], s["fails"] = 0, s["fails"] + 1
                if s["up"] and s["fails"] >= FAILS_TO_DOWN:
                    sh(f"ip route del default via {l['gw']} dev {l['dev']} metric {l['metric']}")
                    s["up"] = False
                    print(time.strftime("%H:%M:%S"), l["name"], "TOMBE")
        time.sleep(1)


if __name__ == "__main__":
    main()
```

Points à observer dans ce code : l’**hystérésis** (3 échecs avant de déclarer le lien mort, 3 succès avant de le rétablir) évite d’osciller à la moindre perte. La route `/32` vers la sonde force le chemin par l’opérateur testé : sans elle, tu testerais toujours le lien principal.

### Manipulation, partie B : mesurer le temps de bascule

```bash
# Terminal 1 : le watchdog
python3 td4/watchdog.py

# Terminal 2 : un ping continu toutes les 200 ms, avec horodatage
docker exec clab-td4-pc-user ping -D -i 0.2 8.8.8.8 | tee ping.log

# Terminal 3 : simuler une panne de l’opérateur A en amont (le lien r-siege/isp-a reste up !)
docker exec clab-td4-isp-a ip link set eth2 down
```

Compte les paquets perdus (`icmp_seq` manquants) × 0,2 s = durée de la coupure. Remets le lien : `ip link set eth2 up` sur `isp-a`.

### Manipulation, partie C : simuler La Réunion avec `tc netem`

Les liaisons vers la métropole ou l’international ont une **latence élevée** (de l’ordre de 150 ms et plus, selon le chemin). `tc netem` permet de simuler cela :

```bash
# +150 ms de latence avec 10 ms de variation, 2 % de perte, sur le lien isp-a -> internet
docker exec clab-td4-isp-a tc qdisc add dev eth2 root netem delay 150ms 10ms loss 2%

# Mesurer
docker exec clab-td4-pc-user ping -c 20 8.8.8.8
docker exec clab-td4-internet iperf3 -s -D
docker exec clab-td4-pc-user iperf3 -c 8.8.8.8 -t 10

# Retirer la simulation
docker exec clab-td4-isp-a tc qdisc del dev eth2 root
```

### Questions

1. Combien de temps a duré la coupure mesurée ? Quel paramètre du script l’influence (donne une formule approximative) ?
2. Les connexions TCP en cours (par exemple une session SSH) survivent-elles à la bascule ? Pourquoi (indice : le NAT) ?
3. Compare le débit `iperf3` avec et sans `netem`. Pourquoi 2 % de perte et 150 ms de latence réduisent-ils autant le débit TCP ?
4. Comment réduire la durée de coupure ? Cite deux pistes.

### Corrigé

1. Environ `FAILS_TO_DOWN × (1 s de pause + 1 s de timeout du ping)` = quelques secondes, plus le délai de propagation. La durée dépend de l’intervalle de sonde et du nombre d’échecs requis : plus le seuil est bas, plus la bascule est rapide, mais plus le risque de fausse alerte est élevé (arbitrage classique).
2. En général **non** : le NAT utilise l’adresse de l’opérateur A pour la connexion ; après la bascule, les paquets sortent avec l’adresse de l’opérateur B, et le serveur distant ne reconnaît plus la connexion. Les applications doivent savoir se reconnecter. (Les VPN WireGuard, eux, survivent grâce à l’itinérance : l’agence apprend la nouvelle adresse source du siège via le keepalive.)
3. TCP réduit sa fenêtre à chaque perte et attend des acquittements qui mettent 150 ms à revenir : le débit est borné par `fenêtre / RTT`. Latence et perte multiplient leurs effets. C’est une raison importante pour laquelle une application sensible à la latence n’est pas utilisée de la même façon à La Réunion qu’en métropole.
4. Réduire l’intervalle de sonde et le seuil d’échec ; utiliser **BFD** avec un protocole de routage (BGP, OSPF) pour des détections sous la seconde ; ou utiliser du SD-WAN qui mesure en continu la qualité de chaque lien.

### Checkpoint

Tu as une durée de coupure chiffrée, le tunnel survit à la bascule, et tu as constaté l’effet de la latence sur `iperf3`. Rédige ton **rapport de bascule** (symptôme, durée mesurée, amélioration proposée).

---

## Séance 11 : supervision, alertes et analyse du contexte local (2 h)

### L’idée

Sans supervision, tu apprends les pannes **par les utilisateurs**, c’est trop tard. La supervision surveille en continu et prévient *avant* ou *dès* la panne : c’est le « suivi proactif » de l’annonce.

Notre pile :

- **node\_exporter** : expose les métriques d’un système (état et débit des interfaces).
- **blackbox\_exporter** : « sonde » (ping, HTTP) vers des cibles, pour la latence et la disponibilité.
- **Prometheus** : collecte et stocke ces métriques, évalue les alertes.
- **Grafana** : tableaux de bord.

### Manipulation

Les exporters partagent l’espace réseau du routeur, pour voir ses interfaces et ses routes :

```bash
docker run -d --name nodeexp --network container:clab-td4-r-siege prom/node-exporter
docker run -d --name bbexp --network container:clab-td4-r-siege --cap-add NET_RAW prom/blackbox-exporter

# Adresse de gestion de r-siege (sur le réseau Docker « clab »)
docker inspect -f '{{.NetworkSettings.Networks.clab.IPAddress}}' clab-td4-r-siege
```

Crée `td4/prometheus.yml` (remplace `RSIEGE_IP` par l’adresse obtenue) :

```yaml
global:
  scrape_interval: 5s
rule_files:
  - /etc/prometheus/rules.yml
scrape_configs:
  - job_name: node
    static_configs:
      - targets: ["RSIEGE_IP:9100"]
  - job_name: probes
    metrics_path: /probe
    params:
      module: [icmp]
    static_configs:
      - targets: ["192.0.2.2"]    # via ISP-A
        labels: {cible: isp-a}
      - targets: ["192.0.2.6"]    # via ISP-B
        labels: {cible: isp-b}
      - targets: ["10.20.10.10"]  # agence via VPN
        labels: {cible: agence-vpn}
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - target_label: __address__
        replacement: RSIEGE_IP:9115
```

Crée `td4/rules.yml` (les alertes) :

```yaml
groups:
  - name: reseau
    rules:
      - alert: LienOperateurDown
        expr: probe_success{cible=~"isp-."} == 0
        for: 10s
        annotations: {summary: "Lien {{ $labels.cible }} injoignable"}
      - alert: TunnelVPNDown
        expr: probe_success{cible="agence-vpn"} == 0
        for: 15s
        annotations: {summary: "Le VPN vers l'agence est tombé"}
      - alert: LatenceElevee
        expr: probe_duration_seconds{cible=~"isp-."} > 0.2
        for: 2m
        annotations: {summary: "Latence > 200 ms sur {{ $labels.cible }}"}
      - alert: PerteDePaquets
        expr: (1 - avg_over_time(probe_success[2m])) > 0.03
        for: 1m
        annotations: {summary: "Perte > 3 % sur {{ $labels.cible }}"}
```

Lance Prometheus et Grafana :

```bash
docker run -d --name prom --network clab -p 9090:9090 \
  -v $PWD/td4/prometheus.yml:/etc/prometheus/prometheus.yml \
  -v $PWD/td4/rules.yml:/etc/prometheus/rules.yml prom/prometheus
docker run -d --name grafana --network clab -p 3000:3000 grafana/grafana
```

Ouvre `http://localhost:9090/targets` (les cibles doivent être « UP »), puis `http://localhost:3000` (identifiants par défaut `admin` / `admin`). Ajoute Prometheus comme source de données (URL `http://prom:9090`) et construis un tableau de bord avec ces requêtes :

| Panneau | Requête PromQL |
| --- | --- |
| Débit entrant ISP-A (bits/s) | `rate(node_network_receive_bytes_total{device="eth3"}[1m]) * 8` |
| Latence par cible | `probe_duration_seconds` |
| Disponibilité des liens | `probe_success` (affichage « État ») |
| Pertes sur 5 min | `1 - avg_over_time(probe_success[5m])` |

Exporte le tableau de bord en JSON (*Dashboard settings → JSON Model*) et mets-le dans ton dépôt.

**Test des alertes** : coupe `isp-a` en amont (`ip link set eth2 down` sur `isp-a`) et observe dans l’onglet **Alerts** de Prometheus l’alerte `LienOperateurDown` passer de *Pending* à *Firing*. Bonus : ajoute Alertmanager avec un webhook vers un petit script Python qui affiche l’alerte.

### Mini-recherche : le contexte de La Réunion (45 min)

Rédige une note d’une demi-page qui répond aux questions suivantes en t’appuyant sur des sources vérifiables (par exemple la carte des câbles sous-marins de TeleGeography, les sites des opérateurs et de l’ARCEP) :

1. Par quels câbles sous-marins La Réunion est-elle reliée au reste du monde ? Où atterrissent-ils ?
2. Quels sont les ordres de grandeur de latence vers la métropole ? Et vers l’Afrique du Sud ?
3. Que se passe-t-il si un câble est endommagé ? (Cherche des exemples d’incidents passés dans l’océan Indien.)
4. En quoi cela justifie-t-il un double opérateur **avec des chemins physiques différents** ?

Le but n’est pas de tout savoir : c’est de montrer au recruteur que tu as pensé le réseau **dans son contexte local**.

### Questions

1. Pourquoi ne supervise-t-on pas seulement l’état de l’interface `eth3` mais aussi la joignabilité de bout en bout ?
2. Pourquoi l’alerte de latence a-t-elle un `for: 2m` ?
3. Quel est le risque d’avoir trop d’alertes ?

### Corrigé

1. L’interface peut rester `up` alors que le service de l’opérateur est coupé en amont (voir séance 10). Seule une sonde de bout en bout détecte ces pannes silencieuses.
2. Pour éviter de se réveiller à cause d’un pic isolé : on alerte sur un **état durable**, pas sur une mesure instantanée.
3. La **fatigue d’alerte** : si tout le monde reçoit 50 alertes par jour, plus personne ne les lit, et la vraie panne passe inaperçue. Une bonne alerte est actionnable : elle dit *quoi* et *où*, et il y a une action à mener.

### Bilan de la semaine 3

Livrables : `firewall.nft` commenté, matrice de flux, dashboard Grafana exporté, rapport de bascule, note sur La Réunion, et une courte **note « SLA »** : disponibilité visée (par exemple 99,9 % ≈ 8 h 45 d’indisponibilité par an), ce que ton architecture garantit (double opérateur, VPN) et ce qu’elle ne garantit pas (point unique de défaillance : `r-siege` lui-même, coupure électrique, erreur humaine).

---

# SEMAINE 4 : AUTOMATISATION, AZURE ET IA

C’est la semaine où ton profil de développeur fait la différence. Tout ce que tu as construit à la main, tu le rends **reproductible, testé et interrogeable**. Pour le recruteur, c’est le cœur du poste « hybride ».

**Structure du dépôt à viser :**

```
reseau-lab/
  Makefile
  README.md
  netlab/              # bibliothèque Python
    __init__.py
    transport.py
    backup.py
    audit.py
    gendoc.py
  tests/
    test_audit.py
  terraform/
    main.tf
  mcp_server/
    server.py
  td4/                 # le labo (topology.yml, firewall.nft, ...)
  .github/workflows/ci.yml
```

## Séance 12 : des scripts d’exploitation propres (2 h 30)

### L’idée

Un script jeté dans un coin n’a aucune valeur en entreprise. Un outil **testable, relançable, sans effet de bord** en a une. Le principe de conception clé ici : séparer **comment on parle à l’équipement** (le *transport*) de **ce qu’on en fait** (sauvegarde, audit, documentation).

Dans le labo, le transport utilise `docker exec`. En production, ce serait SSH avec **Netmiko** (voir l’encadré plus bas). Le reste du code ne change pas : c’est le but de l’abstraction.

### Manipulation, étape 1 : le transport

Crée `netlab/transport.py` :

```python
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
```

**Pour la production**, une implémentation SSH ressemblerait à ceci (à garder en tête, pas à tester dans le labo) :

```python
from netmiko import ConnectHandler

class SshTransport:
    def __init__(self, hosts: dict, username: str, key_file: str) -> None:
        self.hosts, self.username, self.key_file = hosts, username, key_file

    def run(self, device: str, command: str) -> str:
        with ConnectHandler(device_type="linux", host=self.hosts[device],
                            username=self.username, use_keys=True,
                            key_file=self.key_file) as conn:
            return conn.send_command(command)
```

### Étape 2 : sauvegarde des configurations avec historique Git

Crée `netlab/backup.py` :

```python
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
```

Le jour où quelqu’un modifie une règle de pare-feu, `git diff` montre **qui a changé quoi et quand**. C’est du suivi de configuration, une pratique standard.

### Étape 3 : l’audit de conformité

Crée `netlab/audit.py` :

```python
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
```

### Étape 4 : les tests (sans lab, sans Docker)

Crée `tests/test_audit.py`. Les fonctions de contrôle prennent du **texte** en entrée : on les teste avec de simples chaînes, c’est rapide et sans dépendance.

```python
from netlab.audit import check_addressing, check_any_any, check_default_policies, check_snmp

GOOD = """table inet filter {
\tchain input {
\t\ttype filter hook input priority filter; policy drop;
\t}
\tchain forward {
\t\ttype filter hook forward priority filter; policy drop;
\t\tct state established,related accept
\t}
}"""

BAD = GOOD.replace("policy drop; \n\t}\n\tchain forward", "policy accept;\n\t}\n\tchain forward") + "\n\t\taccept"


def test_good_ruleset_is_compliant():
    assert check_default_policies(GOOD) == []
    assert check_any_any(GOOD) == []


def test_accept_policy_is_detected():
    findings = check_default_policies(GOOD.replace("input priority filter; policy drop",
                                                   "input priority filter; policy accept"))
    assert [f.rule for f in findings] == ["default-policy"]


def test_any_any_is_detected():
    assert len(check_any_any(GOOD + "\n\t\taccept")) == 1


def test_address_outside_plan_is_detected():
    data = '[{"ifname": "eth3", "addr_info": [{"family": "inet", "local": "172.31.0.5"}]}]'
    assert check_addressing(data)[0].rule == "addressing"


def test_default_snmp_community_is_detected():
    assert check_snmp("snmp-server community public")[0].severity == "HIGH"
```

(Tu peux supprimer la variable `BAD` inutilisée : garder du code mort est précisément ce que ton propre `ruff` te signalera.)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pytest ruff
pytest -q
ruff check .
```

**Test réel :** sur le routeur, introduis volontairement une règle laxiste (`docker exec clab-td4-r-siege nft add rule inet filter forward accept`), relance `python -m netlab.audit` : l’audit doit signaler l’écart et sortir avec le code 1. Retire la règle en rechargeant `firewall.nft`.

### Étape 5 : la documentation générée depuis l’état réel

Crée `netlab/gendoc.py` :

````python
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
````

Une documentation générée ne **ment** jamais : elle reflète ce qui tourne réellement. Les schémas, eux, restent à la main.

### Questions

1. Pourquoi les contrôles d’audit prennent-ils du texte en entrée plutôt que d’appeler Docker directement ?
2. Pourquoi ne faut-il jamais sauvegarder la sortie de `wg showconf` dans Git ?
3. Quelle est la différence entre une **sauvegarde** de configuration et un **audit** ? Pourquoi veut-on les deux ?

### Corrigé

1. Pour pouvoir **tester** sans lab : une fonction pure (texte → liste d’écarts) est testable en millisecondes et n’a aucune dépendance. C’est la même idée que pour n’importe quel code : isoler les effets de bord (ici, l’accès aux équipements) du calcul.
2. Elle contient la **clé privée** du tunnel. Un dépôt Git garde tout l’historique : une clé commitée une fois est compromise pour toujours, même si on la supprime ensuite.
3. La sauvegarde dit **ce qui existe** et permet de revenir en arrière ; l’audit dit **si c’est conforme** à une règle. Une configuration peut être parfaitement sauvegardée et dangereuse. On veut les deux : l’une pour la récupération, l’autre pour la prévention.

### Checkpoint

`pytest` passe, `python -m netlab.backup` crée un historique Git, et l’audit détecte la règle laxiste que tu as injectée.

---

## Séance 13 : Terraform et Azure (2 h)

### L’idée

**Infrastructure as Code (IaC)** : au lieu de cliquer dans le portail Azure, tu **décris** l’infrastructure dans des fichiers. Terraform compare ce que tu as décrit à ce qui existe, te montre la différence (`plan`), puis l’applique (`apply`). Avantages : reproductible, relisible en revue de code, versionné dans Git.

On construit une mini-architecture **hub-and-spoke** :

- un **VNet hub** (`10.50.0.0/16`) : le point central, où arriverait le VPN vers le siège ;
- un **VNet spoke** (`10.60.0.0/16`) : héberge des applications ;
- un **peering** entre les deux ;
- un **NSG** (*Network Security Group*, l’équivalent d’un pare-feu de sous-réseau).

Les plages Azure `10.50.0.0/16` et `10.60.0.0/16` **ne chevauchent pas** `10.10.0.0/16` et `10.20.0.0/16` (nos sites) : sinon, le routage vers Azure serait ambigu. C’est pour cela qu’un plan d’adressage global se pense **avant** de construire.

**Coûts** : VNet, sous-réseaux, NSG et peering ne coûtent presque rien tant qu’il n’y a pas de trafic ou de machines. **Ne crée pas de VPN Gateway** (facturée à l’heure) ni de VM sans les détruire. À la fin de la séance : `terraform destroy`.

### Manipulation

Installation sur Ubuntu (vérifie les instructions à jour sur les sites de HashiCorp et Microsoft) :

```bash
curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash     # Azure CLI
# Terraform : suis la procédure officielle (depot apt HashiCorp) sur developer.hashicorp.com
az login
export TF_VAR_subscription_id=$(az account show --query id -o tsv)
```

Crée `terraform/main.tf` :

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

variable "subscription_id" { type = string }
variable "location" {
  type    = string
  default = "francecentral"
}
variable "onprem_networks" {
  type    = list(string)
  default = ["10.10.0.0/16", "10.20.0.0/16"]
}

resource "azurerm_resource_group" "lab" {
  name     = "rg-reseau-lab"
  location = var.location
}

resource "azurerm_virtual_network" "hub" {
  name                = "vnet-hub"
  address_space       = ["10.50.0.0/16"]
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name
}

resource "azurerm_virtual_network" "spoke" {
  name                = "vnet-spoke-app"
  address_space       = ["10.60.0.0/16"]
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.lab.name
  virtual_network_name = azurerm_virtual_network.spoke.name
  address_prefixes     = ["10.60.1.0/24"]
}

resource "azurerm_network_security_group" "app" {
  name                = "nsg-app"
  location            = azurerm_resource_group.lab.location
  resource_group_name = azurerm_resource_group.lab.name

  security_rule {
    name                       = "allow-https-from-onprem"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefixes    = var.onprem_networks
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "app" {
  subnet_id                 = azurerm_subnet.app.id
  network_security_group_id = azurerm_network_security_group.app.id
}

resource "azurerm_virtual_network_peering" "hub_to_spoke" {
  name                      = "hub-to-spoke"
  resource_group_name       = azurerm_resource_group.lab.name
  virtual_network_name      = azurerm_virtual_network.hub.name
  remote_virtual_network_id = azurerm_virtual_network.spoke.id
}

resource "azurerm_virtual_network_peering" "spoke_to_hub" {
  name                      = "spoke-to-hub"
  resource_group_name       = azurerm_resource_group.lab.name
  virtual_network_name      = azurerm_virtual_network.spoke.name
  remote_virtual_network_id = azurerm_virtual_network.hub.id
}
```

```bash
cd terraform
terraform init
terraform fmt -check
terraform validate
terraform plan -out=tfplan
terraform apply tfplan          # relis le plan avant d'appliquer !
# ... observe dans le portail Azure ...
terraform destroy
```

**Pour aller plus loin (à documenter, sans déployer)** : décris dans le README comment ton labo se raccorderait à Azure : une **VPN Gateway** dans le hub, une connexion IPsec site-à-site vers le routeur de bordure, des routes vers `10.50.0.0/16` et `10.60.0.0/16` via ce tunnel, et le *gateway transit* sur le peering pour que le spoke joigne aussi le siège. Précise ce que ça coûte et pourquoi tu ne l’as pas déployé : c’est de la maturité professionnelle.

### Questions

1. Pourquoi un peering est-il déclaré **dans les deux sens** ?
2. Que se passerait-il si le VNet Azure utilisait `10.10.0.0/16` ?
3. Quel est l’intérêt de lire `terraform plan` avant `apply` ?
4. L’état Terraform (`terraform.tfstate`) est ici local. Pourquoi est-ce un problème en équipe, et quelle est la solution ?

### Corrigé

1. Un peering Azure est une relation entre **deux** VNets, chacun en déclare sa moitié. Tant que les deux moitiés n’existent pas, l’état reste « Initiated » et rien ne passe.
2. Chevauchement : un routeur ne peut pas savoir si `10.10.10.5` est au siège ou dans Azure. Le trafic partirait vers l’un ou l’autre de façon incohérente. On ne peut d’ailleurs pas appairer des réseaux qui se chevauchent.
3. Le `plan` montre exactement ce qui sera créé, modifié ou **détruit**. Une ligne « destroy » inattendue repérée à ce stade évite un incident.
4. Deux personnes ne partagent pas le même état local, et l’état peut contenir des secrets. Solution : un **backend distant** (par exemple un compte de stockage Azure) avec verrouillage de l’état, jamais commité dans Git.

### Checkpoint

`terraform validate` passe, `plan` est propre, `apply` puis `destroy` ont fonctionné. Vérifie dans le portail qu’**il ne reste rien** (groupe de ressources supprimé).

---

## Séance 14 : un serveur MCP pour interroger ton réseau (2 h)

### L’idée

**MCP** (*Model Context Protocol*) est un standard qui permet à un assistant IA d’appeler des **outils** exposés par un programme. Tu écris un petit serveur qui expose quelques fonctions de ton réseau ; l’assistant peut alors répondre à : « Quels liens sont dégradés et pourquoi ? » en appelant tes outils au lieu de deviner.

Trois principes de conception qui comptent autant que le code :

- **Lecture seule** : aucun outil ne modifie le réseau. Un assistant qui peut tout changer est un risque.
- **Commandes fixes** : l’assistant ne fournit jamais une commande shell en paramètre (pas d’injection possible). Il choisit un outil, pas un texte à exécuter.
- **Traçabilité** : chaque appel est journalisé.

### Manipulation

```bash
pip install "mcp[cli]" requests
```

Crée `mcp_server/server.py` :

```python
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
```

Pour le tester sans assistant, l’outil de développement de MCP fournit un inspecteur : `mcp dev mcp_server/server.py` (voir la documentation du SDK Python MCP si la commande a évolué). Pour le brancher à un assistant (par exemple Claude Code), la commande est du type `claude mcp add reseau-lab -- python /chemin/vers/mcp_server/server.py` : vérifie la syntaxe exacte dans la documentation de ton client.

**Scénario de test :** coupe `isp-a` en amont, puis demande à l’assistant : « Quels liens réseau sont dégradés, et que dit l’audit de configuration ? ». Il doit appeler `get_link_status` et `get_active_alerts` et te répondre en citant les résultats.

### Questions

1. Pourquoi est-il dangereux d’ajouter un outil `run_command(cmd: str)` qui exécute n’importe quelle commande sur le routeur ?
2. Que contient le journal `mcp_audit.log` et à quoi sert-il ?
3. Cite deux autres outils utiles en lecture seule, et un outil que tu refuserais de créer.

### Corrigé

1. L’assistant (ou un texte malveillant qui l’influence, comme une page web ou un log piégé) pourrait exécuter n’importe quoi : couper un lien, effacer des règles. En n’exposant que des lectures aux commandes **fixes**, la pire erreur possible reste une lecture inutile.
2. La liste horodatée des outils appelés et de leurs arguments. Elle permet de **rendre des comptes** : qui a demandé quoi, quand, et de détecter un usage anormal.
3. Exemples utiles : `get_wireguard_status` (dernier handshake), `get_top_talkers` (débit par interface). Outil refusé : `reload_firewall` ou `shutdown_interface`, les actions **qui modifient** doivent rester sous contrôle humain (ou, au minimum, derrière une validation explicite).

### Checkpoint

L’assistant répond correctement à ta question de test en s’appuyant sur tes outils, et le journal montre les appels.

---

## Séance 15 : intégration continue, packaging et démonstration (1 h 30)

### L’idée

Un projet qui ne se relance pas d’un seul geste n’est pas fini. Cette séance transforme ton travail en **dépôt présentable** : `make up` pour tout démarrer, une CI qui vérifie chaque commit, un README qui explique tout.

### Manipulation

**`Makefile`** :

```make
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
```

(Le `firewall.nft` doit être copié dans le conteneur au démarrage ; le plus propre est de le monter via `binds:` dans `topology.yml` plutôt que de faire un `docker cp` à la main : modifie ta topologie en conséquence.)

**`.github/workflows/ci.yml`** :

```yaml
name: CI
on: [push, pull_request]
jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install pytest ruff requests "mcp[cli]"
      - run: ruff check .
      - run: pytest -q
  terraform:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - run: terraform -chdir=terraform fmt -check
      - run: terraform -chdir=terraform init -backend=false
      - run: terraform -chdir=terraform validate
```

(Vérifie les versions actuelles des actions sur GitHub avant de les figer.)

**`README.md`** : il doit répondre à ces questions dans cet ordre.

1. **Quoi ?** Une phrase : « Labo d’un réseau multi-sites avec double opérateur, VPN, pare-feu, supervision et outillage d’automatisation. »
2. **Schéma** de l’architecture et plan d’adressage.
3. **Prérequis et démarrage** : `make up`, puis les URL (Prometheus, Grafana).
4. **Ce que démontre le projet** : bascule mesurée, audit, alertes, MCP.
5. **Limites et retour d’expérience** : ce que tu ferais différemment en production (voir ci-dessous).

### La démonstration de 3 minutes

Scénario à enregistrer (par exemple avec `peek` ou OBS) :

1. (0:00) Présenter le schéma, lancer un ping continu entre deux sites.
2. (0:30) Couper l’opérateur A en amont.
3. (0:45) Montrer la bascule dans le terminal du watchdog et la durée de coupure.
4. (1:15) Montrer l’alerte dans Prometheus et le tableau de bord Grafana.
5. (1:45) Poser la question à l’assistant (« Quels liens sont dégradés ? ») qui interroge ton serveur MCP.
6. (2:30) Lancer l’audit, montrer qu’il détecte une règle laxiste injectée.

### La page « retour d’expérience »

À rédiger honnêtement. Quelques pistes :

- **Limites du labo** : pas de vrai matériel, pas de trafic réel, un seul point de défaillance au siège (`r-siege` est à la fois routeur, pare-feu, VPN et bordure).
- **En production** : paire de pare-feux en haute disponibilité (VRRP), BGP avec les opérateurs, chemins physiques distincts, supervision externe (la supervision ne doit pas dépendre du réseau qu’elle surveille), gestion des secrets (coffre-fort, pas de clés en clair), changements via revue de code et déploiement automatisé.
- **Ce qui n’a pas été testé** : ce que tu n’as pas mesuré, tu ne dois pas l’affirmer.

### Checkpoint final

Quelqu’un qui clone ton dépôt peut faire `make up` et voir le labo tourner. La CI est verte. La vidéo existe. Tu as un journal rempli et un historique Git quotidien.

---

# Et après : transformer ce travail en entretien

## Ce que tu peux dire dans ta candidature

> *Pour compléter mon profil infrastructure, j’ai construit un laboratoire réseau multi-sites (FRRouting, nftables, WireGuard, VLAN, double opérateur avec bascule mesurée), supervisé par Prometheus/Grafana, avec outillage d’automatisation en Python testé en CI, déploiement Azure par Terraform et un serveur MCP en lecture seule. Dépôt : \[lien\].*

## Cinq questions d’entretien à préparer (réponses courtes, avec un exemple de ton labo)

1. **« Que se passe-t-il quand je tape une URL ? »** (DNS, ARP/passerelle, routage, NAT, TCP, TLS, HTTP : tu as vu chaque étape en capture.)
2. **« Un utilisateur dit qu’Internet ne marche pas, que fais-tu ? »** (La méthode des 5 questions, de la couche basse vers la haute ; l’incident du masque en exemple.)
3. **« Comment surveillerais-tu les liens opérateurs ? »** (Sondes de bout en bout, pas seulement l’état de l’interface ; alertes sur états durables ; le cas de la panne silencieuse.)
4. **« Quel est le point faible de ton architecture ? »** (Le point unique de défaillance au siège ; la réponse honnête est un atout.)
5. **« Pourquoi te former au réseau en venant de l’IA et du développement ? »** (Tu automatises ce que d’autres font à la main, et tu apportes l’IA là où elle a de la valeur : diagnostic, analyse de logs, assistant d’exploitation. Appuie-toi sur le MCP.)

## Auto-évaluation finale

Tu es prêt si tu peux, sans notes :

- calculer un sous-réseau et expliquer la différence entre switch, routeur et pare-feu ;
- expliquer ce que fait chaque ligne de ta configuration `nftables` ;
- décrire pourquoi une panne d’opérateur peut être invisible côté interface, et comment ta sonde la détecte ;
- expliquer ce que fait ton `terraform plan` et pourquoi les plages d’adresses ne se chevauchent pas ;
- présenter les limites de ton projet sans te défendre.

**Une dernière chose** : ce TD est un cadre solide, mais ce sont **tes erreurs et tes corrections** qui constitueront ta vraie expérience. Si une commande ne marche pas telle qu’écrite (versions d’images, noms de paquets, comportements de Containerlab ou d’Ubuntu 26.04), c’est normal : diagnostiquer, c’est le métier. Note-le dans ton journal, c’est de la matière d’entretien.