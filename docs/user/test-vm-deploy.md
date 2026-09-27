# Test VM deployment (T3 only)

Target host: **`192.168.102.20`** (HAOS test server). Production is out of scope.

```bash
# Optional once: ssh-keyscan -H 192.168.102.20 >> scripts/known_hosts.test
export HA_TEST_SSH_USER=root
export HA_TEST_SSH_KEY=~/.ssh/id_ed25519   # or use ssh-agent
./scripts/deploy_test_vm.sh dry-run
./scripts/deploy_test_vm.sh deploy
# On failure:
./scripts/deploy_test_vm.sh rollback
```

HA UI credentials for Playwright come from OpenBao (`kv/ha-test`, namespace `homelab`) — see [openbao.md](openbao.md). Not from SSH keys. OpenBao must be running and unsealed.
