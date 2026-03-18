@description('Environment name, e.g. dev, prod')
param envName string = 'dev'

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Location for monitoring resources (Log Analytics + App Insights).')
param monitoringLocation string = location

@description('Location for Postgres Flexible Server (offer restrictions may apply per region).')
param postgresLocation string = 'northeurope'

@description('Optional suffix for Postgres server name (use to avoid conflicts when moving regions). Example: "ne".')
param postgresNameSuffix string = 'ne'

@description('Prefix for resource names')
param namePrefix string = 'opal'

@secure()
@description('Postgres admin password')
param postgresAdminPassword string

@description('Postgres admin username')
param postgresAdminUser string = 'opaladmin'

@description('Postgres SKU name')
param postgresSkuName string = 'Standard_B1ms'

@description('Postgres tier')
param postgresTier string = 'Burstable'

@description('Storage account SKU')
param storageSku string = 'Standard_LRS'

@description('Postgres backup retention in days (7-35)')
param postgresBackupRetentionDays int = 7

@description('Postgres geo-redundant backup (Enabled or Disabled)')
param postgresGeoRedundantBackup string = 'Disabled'

@description('Postgres high availability mode (Disabled or ZoneRedundant)')
param postgresHighAvailability string = 'Disabled'

@description('Availability zone for the HA standby replica (1, 2, or 3). Only used when postgresHighAvailability is ZoneRedundant.')
param postgresStandbyAvailabilityZone string = '2'

@description('Enable VNet integration with private endpoints for PG and Storage. Phase 1: deploy VNet+PEs alongside public access. Phase 2: set vnetContainerApps=true to migrate Container Apps into VNet.')
param vnetEnabled bool = false

@description('When true, Container Apps Environment is (re)created inside the VNet. Requires vnetEnabled=true. WARNING: recreates the CAE, changing all app FQDNs.')
param vnetContainerApps bool = false

@description('VNet address space')
param vnetAddressPrefix string = '10.0.0.0/16'

@description('Subnet for Container Apps (/23 = 512 IPs)')
param subnetContainerAppsPrefix string = '10.0.0.0/23'

@description('Subnet for private endpoints (/24 = 256 IPs)')
param subnetPrivateEndpointsPrefix string = '10.0.2.0/24'

var rgName = resourceGroup().name
var suffix = toLower('${uniqueString(subscription().id, rgName, envName)}')
var baseName = toLower('${namePrefix}-${envName}-${suffix}')

var acrName = take(replace('${namePrefix}${envName}${suffix}', '-', ''), 45)
var saName  = take(replace('${namePrefix}${envName}${suffix}sa', '-', ''), 24)
var sbName  = take('${baseName}-bus', 50)
var kvName  = take(replace('${namePrefix}${envName}${suffix}kv', '-', ''), 24)
var laName  = take('${baseName}-la', 63)
var aiName  = take('${baseName}-ai', 63)
var caEnvName = take('${baseName}-cae', 32)

// IMPORTANT: if you already created a Postgres server with the original name,
// you cannot recreate it in another region. Append a suffix.
var pgServerName = postgresNameSuffix == ''
  ? take('${baseName}-pg', 63)
  : take('${baseName}-pg-${postgresNameSuffix}', 63)

var pgDbName = 'opal'
var amlName = take('${baseName}-aml', 32)
var vnetName = '${baseName}-vnet'
// When vnetContainerApps is true, use a new CAE name to force recreation inside VNet
var caEnvNameVnet = take('${baseName}-cae-v', 32)

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: laName
  location: monitoringLocation
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: aiName
  location: monitoringLocation
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    accessPolicies: []
    enableRbacAuthorization: true
    enableSoftDelete: true
    enablePurgeProtection: true
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: saName
  location: location
  sku: { name: storageSku }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource rawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storage.name}/default/raw'
  properties: { publicAccess: 'None' }
}

resource outputsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storage.name}/default/outputs'
  properties: { publicAccess: 'None' }
}

resource exportsContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-01-01' = {
  name: '${storage.name}/default/exports'
  properties: { publicAccess: 'None' }
}

resource serviceBus 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: sbName
  location: location
  sku: { name: 'Standard', tier: 'Standard' }
  properties: {
    disableLocalAuth: true
  }
}

resource queueJobs 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  name: '${serviceBus.name}/jobs'
  properties: {
    enablePartitioning: true
    lockDuration: 'PT5M'
    maxDeliveryCount: 5
    deadLetteringOnMessageExpiration: true
  }
}

resource queueExports 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  name: '${serviceBus.name}/exports'
  properties: {
    enablePartitioning: true
    lockDuration: 'PT1M'
    maxDeliveryCount: 10
    deadLetteringOnMessageExpiration: true
  }
}

resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
  }
}

// ── VNet + Private Endpoints (deployed when vnetEnabled=true) ──

resource vnet 'Microsoft.Network/virtualNetworks@2023-11-01' = if (vnetEnabled) {
  name: vnetName
  location: location
  properties: {
    addressSpace: { addressPrefixes: [vnetAddressPrefix] }
    subnets: [
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: subnetContainerAppsPrefix
          delegations: [
            {
              name: 'Microsoft.App.environments'
              properties: { serviceName: 'Microsoft.App/environments' }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: subnetPrivateEndpointsPrefix
        }
      }
    ]
  }
}

// ── Private DNS Zones ──

resource dnsZonePg 'Microsoft.Network/privateDnsZones@2020-06-01' = if (vnetEnabled) {
  name: 'privatelink.postgres.database.azure.com'
  location: 'global'
}

resource dnsZonePgLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (vnetEnabled) {
  parent: dnsZonePg
  name: 'pg-vnet-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

resource dnsZoneBlob 'Microsoft.Network/privateDnsZones@2020-06-01' = if (vnetEnabled) {
  name: 'privatelink.blob.core.windows.net'
  location: 'global'
}

resource dnsZoneBlobLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2020-06-01' = if (vnetEnabled) {
  parent: dnsZoneBlob
  name: 'blob-vnet-link'
  location: 'global'
  properties: {
    virtualNetwork: { id: vnet.id }
    registrationEnabled: false
  }
}

// ── Private Endpoints ──

resource pePg 'Microsoft.Network/privateEndpoints@2023-11-01' = if (vnetEnabled) {
  name: '${baseName}-pe-pg'
  location: location
  properties: {
    subnet: { id: vnet.properties.subnets[1].id }
    privateLinkServiceConnections: [
      {
        name: 'pg-connection'
        properties: {
          privateLinkServiceId: postgres.id
          groupIds: ['postgresqlServer']
        }
      }
    ]
  }
}

resource pePgDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = if (vnetEnabled) {
  parent: pePg
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'pg-dns-config'
        properties: { privateDnsZoneId: dnsZonePg.id }
      }
    ]
  }
}

resource peStorage 'Microsoft.Network/privateEndpoints@2023-11-01' = if (vnetEnabled) {
  name: '${baseName}-pe-sa'
  location: location
  properties: {
    subnet: { id: vnet.properties.subnets[1].id }
    privateLinkServiceConnections: [
      {
        name: 'storage-connection'
        properties: {
          privateLinkServiceId: storage.id
          groupIds: ['blob']
        }
      }
    ]
  }
}

resource peStorageDns 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2023-11-01' = if (vnetEnabled) {
  parent: peStorage
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'blob-dns-config'
        properties: { privateDnsZoneId: dnsZoneBlob.id }
      }
    ]
  }
}

// ── Container Apps Environment ──
// When vnetContainerApps=true, a NEW environment is created inside the VNet.
// The old environment (caEnvName) must be deleted manually after apps are migrated.

resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: vnetContainerApps ? caEnvNameVnet : caEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: listKeys(logAnalytics.id, logAnalytics.apiVersion).primarySharedKey
      }
    }
    workloadProfiles: [
      { name: 'consumption', workloadProfileType: 'Consumption' }
      { name: 'dedicated', workloadProfileType: 'D4', minimumCount: 0, maximumCount: 1 }
    ]
    vnetConfiguration: vnetContainerApps ? {
      infrastructureSubnetId: vnet.properties.subnets[0].id
      internal: false
    } : null
  }
}

resource postgres 'Microsoft.DBforPostgreSQL/flexibleServers@2023-03-01-preview' = {
  name: pgServerName
  location: postgresLocation
  sku: {
    name: postgresSkuName
    tier: postgresTier
  }
  properties: {
    administratorLogin: postgresAdminUser
    administratorLoginPassword: postgresAdminPassword
    version: '15'
    storage: { storageSizeGB: 64 }
    backup: { backupRetentionDays: postgresBackupRetentionDays, geoRedundantBackup: postgresGeoRedundantBackup }
    highAvailability: {
      mode: postgresHighAvailability
      standbyAvailabilityZone: postgresHighAvailability == 'ZoneRedundant' ? postgresStandbyAvailabilityZone : ''
    }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  name: '${postgres.name}/${pgDbName}'
  properties: {}
}

resource aml 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: amlName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: amlName
    storageAccount: storage.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id
    publicNetworkAccess: 'Enabled'
  }
}

// ── Cost Management: Budget + Alert ──

@description('Monthly budget amount in USD')
param budgetAmount int = 100

@description('Email address(es) for budget alerts (comma-separated)')
param budgetAlertEmails array = []

resource budgetActionGroup 'Microsoft.Insights/actionGroups@2023-01-01' = if (!empty(budgetAlertEmails)) {
  name: '${baseName}-budget-ag'
  location: 'global'
  properties: {
    groupShortName: 'OpalBudget'
    enabled: true
    emailReceivers: [for (email, i) in budgetAlertEmails: {
      name: 'budget-alert-${i}'
      emailAddress: email
      useCommonAlertSchema: true
    }]
  }
}

resource budget 'Microsoft.CostManagement/budgets@2023-11-01' = if (!empty(budgetAlertEmails)) {
  name: '${namePrefix}-${envName}-monthly'
  scope: resourceGroup()
  properties: {
    category: 'Cost'
    amount: budgetAmount
    timeGrain: 'Monthly'
    timePeriod: {
      startDate: '2025-01-01'
    }
    filter: {
      dimensions: {
        name: 'ResourceGroupName'
        operator: 'In'
        values: [rgName]
      }
    }
    notifications: {
      actual50pct: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 50
        contactEmails: budgetAlertEmails
        thresholdType: 'Actual'
      }
      actual75pct: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 75
        contactEmails: budgetAlertEmails
        thresholdType: 'Actual'
      }
      actual100pct: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 100
        contactEmails: budgetAlertEmails
        thresholdType: 'Actual'
      }
      forecast120pct: {
        enabled: true
        operator: 'GreaterThanOrEqualTo'
        threshold: 120
        contactEmails: budgetAlertEmails
        thresholdType: 'Forecasted'
      }
    }
  }
}

// ── Redis Cache ──

var redisName = take('${baseName}-redis', 63)

resource redis 'Microsoft.Cache/redis@2024-03-01' = {
  name: redisName
  location: location
  properties: {
    sku: {
      name: 'Basic'
      family: 'C'
      capacity: 0
    }
    enableNonSslPort: false
    minimumTlsVersion: '1.2'
    redisConfiguration: {
      'maxmemory-policy': 'allkeys-lru'
    }
  }
}

// ── Diagnostic Settings ──

resource pgDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'pg-diagnostics'
  scope: postgres
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { categoryGroup: 'allLogs', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-01-01' existing = {
  parent: storage
  name: 'default'
}

resource storageBlobDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'storage-blob-diagnostics'
  scope: blobService
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { category: 'StorageRead', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
      { category: 'StorageWrite', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
      { category: 'StorageDelete', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
    metrics: [
      { category: 'Transaction', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
  }
}

resource sbDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'sb-diagnostics'
  scope: serviceBus
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { categoryGroup: 'allLogs', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
  }
}

resource kvDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'kv-diagnostics'
  scope: keyVault
  properties: {
    workspaceId: logAnalytics.id
    logs: [
      { categoryGroup: 'allLogs', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
  }
}

resource redisDiagnostics 'Microsoft.Insights/diagnosticSettings@2021-05-01-preview' = {
  name: 'redis-diagnostics'
  scope: redis
  properties: {
    workspaceId: logAnalytics.id
    metrics: [
      { category: 'AllMetrics', enabled: true, retentionPolicy: { enabled: false, days: 0 } }
    ]
  }
}

output redisHostName string = redis.properties.hostName
output redisName string = redis.name
output keyVaultName string = keyVault.name
output containerAppsEnvironmentName string = containerAppsEnv.name
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output storageAccountName string = storage.name
output serviceBusNamespace string = serviceBus.name
output postgresServerName string = postgres.name
output amlWorkspaceName string = aml.name
output postgresLocationUsed string = postgresLocation
output postgresNameSuffixUsed string = postgresNameSuffix
