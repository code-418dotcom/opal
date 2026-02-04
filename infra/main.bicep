@description('Environment name, e.g. dev, prod')
param envName string = 'dev'

@description('Primary location for resources')
param location string = resourceGroup().location

@description('Location for monitoring resources (Log Analytics + App Insights).')
param monitoringLocation string = location

@description('Location for Postgres Flexible Server (offer restrictions may apply per region).')
param postgresLocation string = 'northeurope'

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

var rgName = resourceGroup().name
var suffix = toLower('${uniqueString(subscription().id, rgName, envName)}')
var baseName = toLower('${namePrefix}-${envName}-${suffix}')

var acrName = take(replace('${namePrefix}${envName}${suffix}', '-', ''), 45)
var saName  = take(replace('${namePrefix}${envName}${suffix}sa', '-', ''), 24)

// IMPORTANT: Service Bus namespace cannot end with '-sb' (reserved). Use '-bus' instead.
var sbName  = take('${baseName}-bus', 50)

var kvName  = take('${baseName}-kv', 24)
var laName  = take('${baseName}-la', 63)
var aiName  = take('${baseName}-ai', 63)
var caEnvName = take('${baseName}-cae', 32)

var pgServerName = take('${baseName}-pg', 63)
var pgDbName = 'opal'

var amlName = take('${baseName}-aml', 32)

//
// Monitoring
//
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

//
// Key Vault (RBAC enabled)
//
resource keyVault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: kvName
  location: location
  properties: {
    tenantId: subscription().tenantId
    sku: { family: 'A', name: 'standard' }
    accessPolicies: []
    enabledForDeployment: false
    enabledForDiskEncryption: false
    enabledForTemplateDeployment: false
    enableRbacAuthorization: true
  }
}

//
// Storage
//
resource storage 'Microsoft.Storage/storageAccounts@2023-01-01' = {
  name: saName
  location: location
  sku: { name: storageSku }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
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

//
// Service Bus (namespace name uses -bus, not -sb)
//
resource serviceBus 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: sbName
  location: location
  sku: { name: 'Standard', tier: 'Standard' }
  properties: {}
}

resource queueJobs 'Microsoft.ServiceBus/namespaces/queues@2024-01-01' = {
  name: '${serviceBus.name}/jobs'
  properties: {
    enablePartitioning: true
    lockDuration: 'PT1M'
    maxDeliveryCount: 10
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

//
// ACR
//
resource acr 'Microsoft.ContainerRegistry/registries@2023-07-01' = {
  name: acrName
  location: location
  sku: { name: 'Standard' }
  properties: {
    adminUserEnabled: false
  }
}

//
// Container Apps Environment
//
resource containerAppsEnv 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: caEnvName
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
      {
        name: 'consumption'
        workloadProfileType: 'Consumption'
      }
      {
        name: 'dedicated'
        workloadProfileType: 'D4'
        minimumCount: 0
        maximumCount: 1
      }
    ]
  }
}

//
// Postgres Flexible Server (deploy to postgresLocation)
//
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
    backup: {
      backupRetentionDays: 7
      geoRedundantBackup: 'Disabled'
    }
    highAvailability: { mode: 'Disabled' }
  }
}

resource postgresDb 'Microsoft.DBforPostgreSQL/flexibleServers/databases@2023-03-01-preview' = {
  name: '${postgres.name}/${pgDbName}'
  properties: {}
}

//
// Azure ML Workspace (explicit dependent resources to avoid "Missing dependent resources in workspace json")
// NOTE: API versions vary; this pattern is robust across many subscriptions.
//
resource aml 'Microsoft.MachineLearningServices/workspaces@2024-04-01' = {
  name: amlName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    friendlyName: amlName

    // Explicit dependencies
    storageAccount: storage.id
    keyVault: keyVault.id
    applicationInsights: appInsights.id
    containerRegistry: acr.id

    publicNetworkAccess: 'Enabled'
  }
}

output containerAppsEnvironmentName string = containerAppsEnv.name
output acrLoginServer string = acr.properties.loginServer
output acrName string = acr.name
output storageAccountName string = storage.name
output serviceBusNamespace string = serviceBus.name
output postgresServerName string = postgres.name
output keyVaultName string = keyVault.name
output appInsightsName string = appInsights.name
output amlWorkspaceName string = aml.name
output monitoringLocationUsed string = monitoringLocation
output postgresLocationUsed string = postgresLocation
output postgresSkuUsed string = postgresSkuName
output postgresTierUsed string = postgresTier
