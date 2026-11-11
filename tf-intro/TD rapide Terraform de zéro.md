# TD rapide : Terraform de zéro

*Durée : environ 2 h. Aucun compte cloud n’est nécessaire avant la dernière séance, qui est facultative. Niveau : tu sais développer et utiliser Docker, mais tu n’as jamais touché à Terraform.*

## L’idée en 5 minutes

Terraform te laisse **décrire** une infrastructure dans des fichiers, puis il se charge de la créer, la modifier ou la détruire pour qu’elle corresponde à ta description. On dit que c’est **déclaratif** : tu écris l’état voulu (« je veux un réseau et deux sous-réseaux »), pas les étapes pour y arriver. Si tu connais Kubernetes, c’est la même logique que les manifestes YAML : tu déclares, l’outil réconcilie.

| Terme | Rôle |
| --- | --- |
| **Provider** | Le plugin qui sait parler à une plateforme (Azure, Docker, fichiers locaux…) |
| **Resource** | Un objet à créer (un réseau virtuel, un fichier, un conteneur) |
| **Variable** | Un paramètre d’entrée, pour ne pas écrire les valeurs en dur |
| **Output** | Une valeur affichée à la fin (une adresse, un identifiant) |
| **State** | Le fichier où Terraform note ce qu’il a déjà créé |
| **Plan** | L’aperçu de ce qui va changer, avant de le faire |

**Les commandes à connaître :**

| Commande | Effet |
| --- | --- |
| `terraform init` | Télécharge les providers (à faire une fois par projet) |
| `terraform fmt` | Met en forme les fichiers |
| `terraform validate` | Vérifie la syntaxe |
| `terraform plan` | Montre ce qui va être créé, modifié ou détruit |
| `terraform apply` | Applique le plan (demande confirmation) |
| `terraform destroy` | Supprime tout ce qui est dans le state |

Dans un plan, `+` veut dire créer, `~` modifier, `-` détruire, et `-/+` détruire puis recréer. Lis toujours le plan avant de confirmer.

---

## Séance 1 : installer Terraform (15 min)

Terraform n’est pas dans les dépôts Ubuntu standard : on utilise le dépôt de HashiCorp.

```bash
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
terraform version
```

Si `apt update` signale que le dépôt ne gère pas encore ta version d’Ubuntu, ne bloque pas : télécharge le binaire depuis la page officielle des versions (releases.hashicorp.com), décompresse l’archive et place `terraform` dans `/usr/local/bin`. Les instructions à jour sont sur developer.hashicorp.com.

**Checkpoint** : `terraform version` affiche un numéro de version.

---

## Séance 2 : ton premier projet, avec des fichiers (25 min)

Pour apprendre, on commence sans cloud : Terraform va créer un simple **fichier** sur ton disque. Tout se passe comme avec Azure, mais sans risque ni coût.

```bash
mkdir -p ~/reseau-lab/tf-intro && cd ~/reseau-lab/tf-intro
```

Crée `main.tf` :

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

resource "local_file" "bonjour" {
  filename = "${path.module}/bonjour.txt"
  content  = "Bonjour Terraform\n"
}
```

Lecture : un bloc `resource` a un **type** (`local_file`), un **nom** local (`bonjour`) et des arguments. `${path.module}` désigne le dossier du projet.

```bash
terraform init          # télécharge le provider « local »
terraform plan          # montre « 1 to add »
terraform apply         # tape yes
cat bonjour.txt
```

**Expériences à faire :**

1. Relance `terraform plan` sans rien changer. Que dit-il ?
2. Modifie le texte dans `content`, puis `terraform plan`. Quel symbole apparaît devant la ressource ?
3. Supprime à la main `bonjour.txt`, puis `terraform plan`. Que veut faire Terraform ?
4. Applique, puis `terraform destroy` pour tout supprimer.

### Questions

1. Pourquoi le deuxième `plan` ne propose-t-il rien ?
2. Quel rôle joue le dossier `.terraform/` créé par `init` ?

### Corrigé

1. Terraform compare ta description au state : tout correspond, il n’y a donc rien à faire. C’est ce qu’on appelle l’**idempotence** : relancer ne change rien tant que rien n’a changé.
2. Il contient les providers téléchargés. Il ne se versionne pas dans Git. Le fichier `.terraform.lock.hcl`, lui, se versionne : il fige les versions utilisées.

Pour l’expérience 3, Terraform voit que le fichier n’existe plus alors que le state dit qu’il devrait : le plan propose de le recréer (`1 to add`).

**Checkpoint** : tu sais lire un plan et tu as vu Terraform recréer un fichier supprimé.

---

## Séance 3 : variables, boucles et génération (35 min)

On applique maintenant Terraform à ton labo : générer les fichiers `frr.conf` de plusieurs sites à partir d’une seule description.

Crée `frr.conf.tftpl` (un modèle) :

```
hostname ${hostname}
!
router ospf
 ospf router-id ${router_id}
%{ for n in networks ~}
 network ${n} area 0
%{ endfor ~}
!
```

Remplace le contenu de `main.tf` :

```hcl
terraform {
  required_version = ">= 1.6"
  required_providers {
    local = {
      source  = "hashicorp/local"
      version = "~> 2.5"
    }
  }
}

variable "sites" {
  type = map(object({
    router_id = string
    networks  = list(string)
  }))
  default = {
    siege  = { router_id = "1.1.1.1", networks = ["10.10.10.0/24", "10.10.20.0/24"] }
    agence = { router_id = "2.2.2.2", networks = ["10.20.10.0/24"] }
  }
}

resource "local_file" "frr" {
  for_each = var.sites
  filename = "${path.module}/out/${each.key}/frr.conf"
  content = templatefile("${path.module}/frr.conf.tftpl", {
    hostname  = "r-${each.key}"
    router_id = each.value.router_id
    networks  = each.value.networks
  })
}

output "fichiers" {
  value = [for f in local_file.frr : f.filename]
}
```

Ce que tu découvres ici :

- `variable` déclare un paramètre, avec un type et une valeur par défaut.
- `for_each` crée **une ressource par élément** de la variable : ici deux fichiers, un par site.
- `each.key` et `each.value` désignent l’élément courant.
- `templatefile` remplit un modèle avec des valeurs.
- `output` affiche une valeur à la fin de l’`apply`.

```bash
terraform fmt
terraform validate
terraform plan          # « 2 to add »
terraform apply
cat out/siege/frr.conf
terraform output fichiers
```

**Exercices :**

1. Ajoute un troisième site `entrepot` dans la variable (par exemple `router_id = "3.3.3.3"`, réseau `10.30.10.0/24`). Que propose `plan` ? Que se passe-t-il pour les deux fichiers existants ?
2. Sans modifier `main.tf`, remplace les sites avec un fichier `terraform.tfvars` ou avec `terraform plan -var 'sites={...}'` (cherche la syntaxe avec `terraform plan -help`).
3. Supprime le site `agence` de la variable et fais un `plan`. Que veut faire Terraform ?

### Corrigé

1. `plan` propose `1 to add` : seul le nouveau fichier est créé, les deux autres sont inchangés. C’est tout l’intérêt de `for_each` : chaque élément a sa propre vie.
2. Un fichier `terraform.tfvars` est lu automatiquement : tu y écris `sites = { ... }` avec la même structure que le `default`. C’est la façon normale de séparer le code (le modèle) des valeurs (les données d’un environnement).
3. Il propose de **détruire** le fichier de l’agence (`1 to destroy`), car la description ne le contient plus. C’est le pouvoir (et le danger) de Terraform : supprimer un élément de la description supprime la ressource. D’où l’importance de lire le plan.

**Checkpoint** : tu as généré des fichiers pour plusieurs sites depuis une seule variable, et tu sais pourquoi on lit le plan avant d’appliquer.

---

## Séance 4 : le state, le cœur de Terraform (20 min)

Terraform ne devine pas ce qui existe : il consulte son **state**, un fichier (`terraform.tfstate`) qui dresse la liste de ce qu’il a créé.

```bash
terraform state list
terraform state show 'local_file.frr["siege"]'
head -30 terraform.tfstate
```

**Expérience :**

1. Renomme `terraform.tfstate` en `terraform.tfstate.bak2`, puis fais un `terraform plan`. Que propose-t-il alors que les fichiers existent toujours ? Remets le fichier à sa place.
2. Crée un fichier `.gitignore` contenant `.terraform/`, `*.tfstate` et `*.tfstate.*`.

### Questions

1. Pourquoi, sans state, Terraform veut-il tout recréer ?
2. Pourquoi ne faut-il jamais mettre `terraform.tfstate` dans Git ?
3. Dans une équipe, où doit se trouver le state ?

### Corrigé

1. Pour Terraform, une ressource qui n’est pas dans le state n’existe pas : il en conclut qu’il doit tout créer. Avec de vraies ressources cloud, cela créerait des doublons.
2. Il peut contenir des **secrets** (mots de passe, clés) en clair, et deux personnes qui en gardent chacune une copie divergente risquent de se contredire.
3. Dans un **backend distant** avec verrouillage (par exemple un compte de stockage Azure) : un état commun, protégé, et un seul `apply` à la fois.

**Checkpoint** : tu sais ce que contient le state et pourquoi il ne va pas dans Git.

---

## Séance 5 (facultative) : un petit réseau Azure (25 min)

Si tu as un compte Azure, tu peux appliquer les mêmes gestes à un vrai réseau. Seuls un réseau virtuel et un sous-réseau sont créés : ils ne coûtent presque rien tant qu’il n’y a pas de machines. **Ne crée ni VM ni passerelle VPN pendant ce TD**, et termine par `terraform destroy`.

```bash
az login
export TF_VAR_subscription_id=$(az account show --query id -o tsv)
mkdir -p ~/reseau-lab/tf-azure && cd ~/reseau-lab/tf-azure
```

Crée `main.tf` :

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

resource "azurerm_resource_group" "td" {
  name     = "rg-td-terraform"
  location = var.location
}

resource "azurerm_virtual_network" "hub" {
  name                = "vnet-td"
  address_space       = ["10.50.0.0/16"]
  location            = azurerm_resource_group.td.location
  resource_group_name = azurerm_resource_group.td.name
}

resource "azurerm_subnet" "app" {
  name                 = "snet-app"
  resource_group_name  = azurerm_resource_group.td.name
  virtual_network_name = azurerm_virtual_network.hub.name
  address_prefixes     = ["10.50.1.0/24"]
}
```

```bash
terraform init
terraform plan -out=tfplan
terraform apply tfplan
# observe le réseau dans le portail Azure
terraform destroy
```

Repère dans ce fichier ce que tu as déjà vu : les **références** entre ressources (`azurerm_resource_group.td.name` crée une dépendance : Terraform sait qu’il doit créer le groupe de ressources avant le réseau), les variables, et le plan. La plage `10.50.0.0/16` ne chevauche volontairement pas le plan d’adressage du labo (`10.10.x.x`, `10.20.x.x`).

**Checkpoint** : `apply` puis `destroy` fonctionnent, et le portail Azure ne montre plus de groupe `rg-td-terraform` à la fin.

---

## Pièges fréquents des débutants

- **Oublier `terraform destroy`** après un essai cloud : une ressource oubliée peut coûter de l’argent. Vérifie dans le portail.
- **Lire le plan en diagonale** : une ligne `-/+` (détruire puis recréer) sur une ressource importante doit t’alerter.
- **Modifier à la main** dans le portail ce que Terraform gère : au prochain `plan`, il voudra annuler ton changement.
- **Committer le state ou des secrets** dans Git.
- **Ne pas figer les versions** de providers : `version = "~> 4.0"` évite qu’une mise à jour casse ton projet sans prévenir.

## Auto-évaluation

Tu as retenu l’essentiel si tu peux, sans notes :

- expliquer la différence entre un style déclaratif et un script ;
- lire un plan et dire ce qui sera créé, modifié ou détruit ;
- expliquer ce que fait `for_each` et ce qu’il se passe quand on retire un élément ;
- expliquer ce qu’est le state, et pourquoi il ne va pas dans Git ;
- dire ce que tu vérifierais avant de lancer `apply` sur une vraie infrastructure.

Pour la suite, la séance 13 du TD réseau applique ces notions à l’architecture Azure du labo (deux réseaux, un peering, un NSG).
