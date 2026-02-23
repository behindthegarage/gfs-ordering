# GFS Ordering Module Deployment Notes

## Critical: VPS vs OptiPlex Architecture

**ALWAYS deploy to VPS (162.212.153.134) — NOT the OptiPlex!**

The Kinawa Command Center runs on the Cloudfanatic VPS, not the local OptiPlex. The OptiPlex is for OpenClaw/Gateway only.

## Deployment Workflow

1. **Make changes** in `/home/openclaw/.openclaw/workspace/kinawa-command-center/`
2. **Commit & push** to GitHub: `behindthegarage/kinawa-command-center`
3. **Deploy to VPS**:
   ```bash
   ssh openclaw@162.212.153.134
   cd /home/openclaw/kinawa-command-center
   git pull origin master
   sudo systemctl restart kinawa
   ```

## Common Issues

### Changes not showing up
- **Cause:** Edited files on OptiPlex but didn't push to VPS
- **Fix:** Follow deployment workflow above
- **Prevention:** Always check `git log` on VPS to confirm latest commit

### JavaScript not working
- **Cause:** Browser caching old JS
- **Fix:** Hard refresh browser (Ctrl+F5 or Cmd+Shift+R)
- **Debug:** Check browser console (F12) for errors

## Verification Commands

```bash
# Check VPS has latest code
ssh openclaw@162.212.153.134 "cd /home/openclaw/kinawa-command-center && git log --oneline -3"

# Check specific file content on VPS
ssh openclaw@162.212.153.134 "grep 'search_term' /home/openclaw/kinawa-command-center/templates/file.html"

# Test page is serving correctly
ssh openclaw@162.212.153.134 "curl -s http://localhost:5000/gfs-ordering/ -u admin:kinawa2026 | head -20"
```

## File Locations

| Location | Purpose |
|----------|---------|
| OptiPlex: `~/.openclaw/workspace/kinawa-command-center/` | Git repo, make edits here |
| VPS: `/home/openclaw/kinawa-command-center/` | Production deployment |
| GitHub: `behindthegarage/kinawa-command-center` | Source of truth |

## Restart Service

```bash
ssh openclaw@162.212.153.134 "sudo systemctl restart kinawa"
```

Check status: `sudo systemctl status kinawa`
