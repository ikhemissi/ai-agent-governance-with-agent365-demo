# The demo's Purview check at the gateway (branch "purview"). Off by default: when the API Management named value
# purview-check is "on", every call to the model API is checked by Microsoft Purview as the signed-in user, before
# the model sees it (the text the user typed and the tools' results), and refused if a DLP policy blocks it; with
# purview-check-responses "on" too, the model's answer is checked before it leaves the gateway.
#
# How the user's identity reaches Purview: the gateway app (apim-gateway.tf) exchanges the user's token for a
# Microsoft Graph token (On-Behalf-Of) and calls Graph's processContent with it. The exchange needs no secret: the
# gateway app trusts API Management's managed identity as a federated credential. The DLP policy itself is created in
# Purview, scoped to the gateway app (docs/PURVIEW.md).

locals {
  purview_graph_scopes = ["Content.Process.User", "ProtectionScopes.Compute.User", "ContentActivity.Write"]
}

data "azuread_service_principal" "graph" {
  client_id = "00000003-0000-0000-c000-000000000000" # Microsoft Graph
}

# The apim-gateway block ignores changes to required_resource_access, so that this access can be added here.
resource "azuread_application_api_access" "purview_graph" {
  application_id = azuread_application.apim_gateway.id
  api_client_id  = data.azuread_service_principal.graph.client_id
  scope_ids      = [for scope in local.purview_graph_scopes : data.azuread_service_principal.graph.oauth2_permission_scope_ids[scope]]
}

# Admin consent for those permissions, for every user of the tenant (no user prompt in the On-Behalf-Of exchange).
resource "azuread_service_principal_delegated_permission_grant" "purview_graph" {
  service_principal_object_id          = azuread_service_principal.apim_gateway.object_id
  resource_service_principal_object_id = data.azuread_service_principal.graph.object_id
  claim_values                         = local.purview_graph_scopes
}

# API Management's managed identity signs the On-Behalf-Of exchange for the gateway app, instead of a client secret.
resource "azuread_application_federated_identity_credential" "purview_apim" {
  application_id = azuread_application.apim_gateway.id
  display_name   = "api-management-managed-identity"
  description    = "API Management's managed identity, for the On-Behalf-Of exchange to Microsoft Graph (Purview)."
  audiences      = ["api://AzureADTokenExchange"]
  issuer         = "https://login.microsoftonline.com/${data.azurerm_client_config.current.tenant_id}/v2.0"
  subject        = module.apim_ai_gateway.principal_id
}

# The switch: "on" or "off". Re-provisioning keeps its current value.
resource "azurerm_api_management_named_value" "purview_check" {
  name                = "purview-check"
  api_management_name = module.apim_ai_gateway.name
  resource_group_name = azurerm_resource_group.main.name
  display_name        = "purview-check"
  value               = "off"

  lifecycle {
    ignore_changes = [value]
  }
}

# The answer check's switch: "on" (with purview-check "on") holds each answer until Purview has checked it.
resource "azurerm_api_management_named_value" "purview_check_responses" {
  name                = "purview-check-responses"
  api_management_name = module.apim_ai_gateway.name
  resource_group_name = azurerm_resource_group.main.name
  display_name        = "purview-check-responses"
  value               = "off"

  lifecycle {
    ignore_changes = [value]
  }
}

# One Purview check (processContent), shared by the prompt check and the answer check.
resource "azurerm_api_management_policy_fragment" "purview" {
  api_management_id = module.apim_ai_gateway.id
  name              = "purview-process-content"
  format            = "rawxml"
  value = templatefile("${path.module}/policies/purview-fragment.xml.tftpl", {
    client_id = azuread_application.apim_gateway.client_id
  })
}

# A policy for all APIs, so that the model API's own policy (a shared module) stays as it is; it acts only on the
# model API, and only when the switch is on.
resource "azurerm_api_management_policy" "purview" {
  api_management_id = module.apim_ai_gateway.id
  xml_content = templatefile("${path.module}/policies/purview-policy.xml.tftpl", {
    tenant_id = data.azurerm_client_config.current.tenant_id
    client_id = azuread_application.apim_gateway.client_id
  })

  depends_on = [
    azurerm_api_management_named_value.purview_check,
    azurerm_api_management_named_value.purview_check_responses,
    azurerm_api_management_policy_fragment.purview,
    azuread_application_federated_identity_credential.purview_apim,
    azuread_service_principal_delegated_permission_grant.purview_graph,
  ]
}

output "APIM_PURVIEW_SWITCH" { value = azurerm_api_management_named_value.purview_check.name }
