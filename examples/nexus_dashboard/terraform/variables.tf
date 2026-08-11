variable "aci_username" {
  description = "ACI APIC username"
  type        = string
  sensitive   = true
}

variable "aci_password" {
  description = "ACI APIC password"
  type        = string
  sensitive   = true
}

variable "aci_url" {
  description = "ACI APIC URL (https://...) — often the same host as Nexus Dashboard"
  type        = string
}
