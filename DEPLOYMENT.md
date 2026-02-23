# GFS Ordering — Deployment

## Deployment (CRITICAL — Read Before Editing)

| Field | Value |
|-------|-------|
| **Canonical Host** | ✅ **VPS** |
| **Host IP/Name** | `162.212.153.134` |
| **Code Path** | `/home/openclaw/gfs-ordering/` |
| **Repo** | `behindthegarage/gfs-ordering` |
| **Deploy Method** | Git push → GitHub Actions → auto-deploy |
| **Domain/URL** | Via Club Kinawa CC integration |
| **Auth** | CC login required |

**⚠️ Rule:** Always edit on VPS. Never develop locally.

## Auto-Deploy Workflow

1. **Edit files on VPS**: `ssh openclaw@162.212.153.134`
2. **Commit & push** from VPS to GitHub
3. **GitHub Actions automatically deploys** back to VPS

Or edit locally, push, and auto-deploy triggers:
```bash
git add .
git commit -m "changes"
git push origin master
```

## Manual Verification

```bash
# Check VPS has latest code
ssh openclaw@162.212.153.134 "cd /home/openclaw/gfs-ordering && git log --oneline -3"

# Check service status
ssh openclaw@162.212.153.134 "sudo systemctl status gfs-ordering"
```

## File Locations

| Location | Purpose |
|----------|---------|
| **VPS:** `/home/openclaw/gfs-ordering/` | ✅ Canonical — edit here |
| **GitHub:** `behindthegarage/gfs-ordering` | Source of truth |
| ~~OptiPlex~~ | ❌ Stale — deleted |
