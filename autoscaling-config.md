# Auto-scaling Configuration

## Container Apps Scaling Rules

### Web API (opal-web-api-dev)
- **Min Replicas**: 1
- **Max Replicas**: 5
- **Scale Rule**: HTTP concurrency
- **Threshold**: 50 concurrent requests per instance
- **Behavior**: Scales up when requests > 50/instance, scales down when idle

### Orchestrator (opal-orchestrator-dev)
- **Min Replicas**: 1
- **Max Replicas**: 3
- **Scale Rule**: Azure Service Bus queue
- **Queue**: jobs
- **Threshold**: 10 messages
- **Behavior**: Adds replica when queue > 10 messages, scales down when queue drains

### Export Worker (opal-export-worker-dev)
- **Min Replicas**: 0 (can scale to zero)
- **Max Replicas**: 3
- **Scale Rule**: Azure Service Bus queue
- **Queue**: exports
- **Threshold**: 5 messages
- **Behavior**: Starts from zero when messages arrive, scales to zero when idle

### Billing Service (opal-billing-service-dev)
- **Min Replicas**: 1
- **Max Replicas**: 1
- **Scale Rule**: None (fixed)
- **Behavior**: Always runs 1 replica for background tasks

## Cost Optimization

### Scale-to-Zero Benefits
- **Export Worker** scales to zero when no exports are queued
- Saves ~\-50/month when not processing exports
- Starts automatically within 1-2 seconds when work arrives

### HTTP Scaling Benefits
- **Web API** scales based on actual load
- Handles traffic spikes automatically
- Reduces to min replicas during low usage

### Queue-Based Scaling Benefits
- **Orchestrator** scales based on queue depth
- Prevents queue backlog during high load
- Efficient processing without over-provisioning

## Monitoring Scaling Events

### Azure Portal
1. Go to Container App
2. Navigate to "Metrics"
3. Select metric: "Replica Count"
4. View scaling history

### CLI Commands
\\\powershell
# Check current replica count
az containerapp replica list -g opal-dev-rg -n opal-web-api-dev --query "length(@)"

# View scaling configuration
az containerapp show -g opal-dev-rg -n opal-web-api-dev --query "properties.template.scale"
\\\

## Tuning Recommendations

### If experiencing delays:
- Increase max replicas
- Lower scaling thresholds
- Adjust min replicas to keep more instances warm

### If costs are high:
- Decrease max replicas
- Increase scaling thresholds
- Enable scale-to-zero where appropriate

### Current Configuration (Dev Environment)
- Conservative limits to control costs
- Sufficient for testing and light production use
- Adjust for production based on load testing

