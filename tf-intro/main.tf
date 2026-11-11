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
    entrepot = { router_id = "3.3.3.3", networks = ["10.30.10.0/24"] }
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