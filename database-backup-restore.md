# PostgreSQL Backup & Restore Guide

## Automated Backups
- **Retention**: 7 days
- **Geo-Redundant**: Disabled (dev environment)
- **Frequency**: Automatic snapshots every 5 minutes
- **Server**: opal-dev-dbeia4dlnxsy4-pg-ne

## Restore Commands

### Point-in-Time Restore (PITR)
```powershell
# Restore to specific time
az postgres flexible-server restore \
  --resource-group opal-dev-rg \
  --name opal-dev-dbeia4dlnxsy4-pg-ne-restored \
  --source-server opal-dev-dbeia4dlnxsy4-pg-ne \
  --restore-time "2026-02-08T12:00:00Z"
```

### Restore to Latest
```powershell
# Restore to most recent backup
az postgres flexible-server restore \
  --resource-group opal-dev-rg \
  --name opal-dev-dbeia4dlnxsy4-pg-ne-restored \
  --source-server opal-dev-dbeia4dlnxsy4-pg-ne
```

## Disaster Recovery
1. Restore database to new server
2. Update container app connection strings
3. Verify data integrity
4. Switch DNS/traffic if needed

## Monitoring
- Check backup status: Azure Portal → PostgreSQL → Backup and restore
- Set alerts for backup failures
- Test restore monthly
