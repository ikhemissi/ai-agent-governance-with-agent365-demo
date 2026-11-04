# Outputs become azd environment values. No secrets.

output "APIM_PURVIEW_SWITCH" { value = azurerm_api_management_named_value.purview_check.name }
