<#
.SYNOPSIS
    Creates the DLP policy the gateway's Purview check enforces (infra/apim-purview, docs/PURVIEW.md).

.DESCRIPTION
    One DLP policy for an Entra application, the gateway's app registration (APIM_GATEWAY_CLIENT_ID), with one rule:
    credit card numbers are blocked in text sent to the model (UploadText) and in its answers (DownloadText), with a
    High alert and an incident report.
    Adapted from the Azure-Samples AI-Gateway lab "apim-purview-dlp" (setup/Create-LabDlpPolicy.ps1). A DLP policy for
    an application is created with PowerShell (location "Applications", enforcement plane "Application").

    Needs PowerShell 7+, the ExchangeOnlineManagement module, and the Compliance Administrator role. It can take up to
    an hour before Purview enforces a new policy.

.EXAMPLE
    pwsh ./src/create-dlp-policy.ps1 -AppId "$(azd env get-value APIM_GATEWAY_CLIENT_ID)" -AlertRecipients admin@contoso.com
#>
param(
    [Parameter(Mandatory)] [string] $AppId,
    [Parameter(Mandatory)] [string[]] $AlertRecipients,
    [string] $AppName = 'AI gateway',
    [string] $PolicyName = 'AI gateway demo - block sensitive data to the model',
    [string] $RuleName = 'Block credit card numbers in prompts and tool results',
    # An access token for Security & Compliance PowerShell, when no browser is available for the interactive sign-in.
    [string] $AccessToken = '',
    [string] $Organization = ''
)
$ErrorActionPreference = 'Stop'

Import-Module ExchangeOnlineManagement
if ($AccessToken) {
    Connect-IPPSSession -AccessToken $AccessToken -Organization $Organization -ShowBanner:$false
} else {
    Connect-IPPSSession -ShowBanner:$false
}

$Locations = ConvertTo-Json -Compress -Depth 6 -InputObject @(@{
    Workload            = 'Applications'
    Location            = $AppId
    LocationDisplayName = $AppName
    LocationSource      = 'Entra'
    LocationType        = 'Individual'
    Inclusions          = @(@{ Type = 'Tenant'; Identity = 'All' })
})

if (-not (Get-DlpCompliancePolicy -Identity $PolicyName -ErrorAction SilentlyContinue)) {
    New-DlpCompliancePolicy -Name $PolicyName -Locations $Locations -EnforcementPlanes @('Application') -Mode Enable `
        -Comment 'The AI gateway checks prompts and tool results with Purview before the model.' | Out-Null
    Write-Host 'DLP policy created.'
} else {
    Set-DlpCompliancePolicy -Identity $PolicyName -Locations $Locations -EnforcementPlanes @('Application') -Mode Enable -Confirm:$false | Out-Null
    Write-Host 'DLP policy updated.'
}

$Rule = @{
    ContentContainsSensitiveInformation = @(@{ Name = 'Credit Card Number'; minCount = '1' })
    RestrictAccess                      = @(@{ Setting = 'UploadText'; Value = 'Block' }, @{ Setting = 'DownloadText'; Value = 'Block' })
    GenerateAlert                       = $AlertRecipients
    GenerateIncidentReport              = $AlertRecipients
    IncidentReportContent               = @('Default', 'Detections', 'DetectionDetails', 'MatchedItem', 'RulesMatched', 'Service', 'Severity', 'Title')
    ReportSeverityLevel                 = 'High'
    Comment                             = 'Credit card numbers never reach the model through the gateway.'
}
if (-not (Get-DlpComplianceRule -Identity $RuleName -ErrorAction SilentlyContinue)) {
    New-DlpComplianceRule -Name $RuleName -Policy $PolicyName @Rule | Out-Null
    Write-Host 'DLP rule created.'
} else {
    Set-DlpComplianceRule -Identity $RuleName @Rule -Confirm:$false | Out-Null
    Write-Host 'DLP rule updated.'
}

Get-DlpCompliancePolicy -Identity $PolicyName | Format-List Name, Mode, EnforcementPlanes, DistributionStatus
Get-DlpComplianceRule -Identity $RuleName | Format-List Name, Policy, ReportSeverityLevel
