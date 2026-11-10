# The demo's MCP server in API Management: the notes MCP server (notes-mcp.tf) registered as an MCP API at
# <gateway>/notes, shown in Agent 365 as "Team notes (APIM)". MCP APIs are created with azapi. What works (checked on
# Standard v2): a backend with the server's full URL, and an API of type "mcp" pointing at it with backendId and the
# streamable transport, without endpoints. Agent 365 blocks it by setting the API's accessState; re-applying keeps that
# state (the bodies below never set it). Block a replaced API again from the admin center. The policy uses azurerm,
# which compares the XML without its formatting: API Management returns it reformatted.

locals {
  apim_mcp_notes_path = "notes"
}

resource "azapi_resource" "notes_backend" {
  type      = "Microsoft.ApiManagement/service/backends@2024-06-01-preview"
  name      = "notes-mcp"
  parent_id = module.apim_ai_gateway.id
  body = {
    properties = {
      protocol = "http"
      url      = "${module.notes_mcp.url}/mcp"
      tls      = { validateCertificateChain = true, validateCertificateName = true }
      type     = "Single"
    }
  }
}

resource "azapi_resource" "notes_api" {
  type      = "Microsoft.ApiManagement/service/apis@2025-09-01-preview"
  name      = "notes"
  parent_id = module.apim_ai_gateway.id
  # azapi's schema for this preview API version lacks backendId.
  schema_validation_enabled = false
  body = {
    properties = {
      type                 = "mcp"
      displayName          = "Team notes (APIM)"
      description          = "Read and add short team notes."
      path                 = local.apim_mcp_notes_path
      protocols            = ["https"]
      backendId            = azapi_resource.notes_backend.name
      subscriptionRequired = false
      mcpProperties        = { transportType = "streamable" }
    }
  }
}

# Users of the tenant with the gateway's scope only, as for the model; then the notes server with the gateway's own
# identity (the only caller it accepts). Never read the response body here: it would break MCP streaming.
resource "azurerm_api_management_api_policy" "notes_policy" {
  api_name            = azapi_resource.notes_api.name
  api_management_name = module.apim_ai_gateway.name
  resource_group_name = azurerm_resource_group.main.name
  xml_content = templatefile("${path.module}/policies/mcp-policy.xml.tftpl", {
    tenant_id        = data.azurerm_client_config.current.tenant_id
    client_id        = azuread_application.apim_gateway.client_id
    scope            = local.apim_gateway_scope
    backend_audience = join("", azuread_application_identifier_uri.notes_mcp[*].identifier_uri)
  })
}

output "APIM_MCP_NOTES_URL" { value = "${module.apim_ai_gateway.gateway_url}/${local.apim_mcp_notes_path}" }
