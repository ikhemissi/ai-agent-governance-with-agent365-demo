# azd passes every value of main.tfvars.json as a string. All come from the apim-gateway layer.

variable "subscription_id" {
  description = "Target subscription (AZURE_SUBSCRIPTION_ID)."
  type        = string
}

variable "resource_group_name" {
  description = "Resource group of the platform layer (AZURE_RESOURCE_GROUP)."
  type        = string
}

variable "apim_name" {
  description = "The API Management gateway (APIM_NAME)."
  type        = string

  validation {
    condition     = var.apim_name != ""
    error_message = "APIM_NAME is empty: provision the apim-gateway layer first."
  }
}

variable "apim_principal_id" {
  description = "API Management's managed identity (APIM_PRINCIPAL_ID): trusted by the gateway app instead of a secret."
  type        = string
}

variable "apim_gateway_client_id" {
  description = "The gateway's app registration (APIM_GATEWAY_CLIENT_ID): the audience of the users' tokens, and the app that exchanges them for Microsoft Graph."
  type        = string
}
