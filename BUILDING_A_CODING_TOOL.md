# Building a Successful AI Coding Tool — Architecture, Process, and Lessons

This document describes how a successful coding tool should be built and how it should work, based on the verified construction and operation of a dual-GPU coding VM (local Quadro P4000 passthrough on Proxmox VM 110 + rented vast.ai RTX 3090 serving Huihui-Qwen3-Coder-30B), maintained by an agent-driven error-learning loop.

## 1. Target architecture

A successful coding tool has four planes:

1. **Execution plane** — where code runs: a sandboxed terminal (Docker in this build) with no GPU, no host SSH keys, and no direct Mac filesystem access. All privileged operations are brokered.
2. **GPU plane** — two tiers:
   - *Local deterministic tier:* Quadro P4000 passthrough into Proxmox VM 110 (coding-ubuntu, 10.0.0.186, 24GB RAM / 8 cores). Verified live via `qm guest exec 110 -- nvidia-smi` (driver 580.178.04, CUDA 13.0).
   - *Remote frontier tier:* rented vast.ai RTX 3090 (instance 57964336) serving Huihui-Qwen3-Coder-30B through an SSH tunnel (Mac 127.0.00.1:8081 → instance ollama :11434) as the delegation/build model.
3. **Model plane** — provider routes in the coding profile config: `vast-3090-shared` (delegation/build), `ollama-abliterated-local` / `7920-gpu` (P4000 local), LiteLLM router with `vast-3090` + `vast-5090`.
4. **Knowledge plane** — persistent memory for environment facts and error lessons; per-task skills for procedures; recovery artifacts for catastrophic loss.

## 2. Build sequence

1. Provision the execution sandbox; verify what it does NOT have (no GPU, no gh, no host keys) before planning any operation.
2. Pass the local GPU through and verify in-guest (`nvidia-smi` via `qm guest exec`) — do not trust host-level checks alone.
2. Rent the remote GPU; record instance ID, image, and initial SSH endpoint.
3. Establish the tunnel (launchd KeepAlive ssh -N with forwarding) and configure provider routes.
5. Run the error-learning loop continuously (below).
6. Keep two repos: the project repo and this methodology repo.

## 3. Verification gates

- P4000 live in guest: `qm guest exec 110 -- nvidia-smi` shows the card and VRAM in use.
- 3090 reachable: Mac 127.0.0.1:8081 responds; provider route answers a completion.
- Tunnel agent loaded and target matches the instance's CURRENT ssh_host:ssh_port.
- Repo state: `git log` present, working tree matches recovery artifacts, compile checks pass.

## 4. The error-learning loop

The tool must treat every failure as a learning event:

1. **Detect** — monitor tunnel logs, provider errors, and command exit codes.
2. **Diagnose** — form hypotheses from the changed variable (e.g., "instance stopped" vs "network down": a stopped container still pings but times out on SSH; check console `actual_status` FIRST).
3. **Fix** — apply the minimal change (re-point the tunnel to the instance's new `ssh_host:ssh_port`, restart the launchd job with bootout/bootstrap, not unload/load).
4. **Record** — save the lesson to persistent memory immediately so it is never repeated.
5. **Improve** — adjust the tool/build instructions (e.g., tunnel script should auto-discover the endpoint from the console API instead of hardcoding an address).

## 5. Hard lessons (verified 2026-10-27)

- A vast.ai instance's SSH endpoint (host AND port) changes on restart. Never hardcode; query the console API (`/api/v0/instances/<id>/`, cookie-auth in-browser fetch) for `ssh_host`/`ssh_port` on every reconnect.
- `launchctl unload/load` does NOT re-read a changed plist — use `bootout` + `bootstrap`.
- Session history claims can be wrong; direct inspection always wins.
- A backend migration can wipe a sandbox repo mid-rebuild; keep builder scripts that embed full file contents — they are gold for reconstruction.
- Scope greps on the Mac to small subdirectories or they time out.
- The vastai CLI can be installed but not logged in; the logged-in console browser session is the practical credential path.
- `resources_unavailable` on a vast.ai start call means queued, not failed — the start processes when the host frees capacity.

## 6. What good looks like

- Both GPUs verified live at any moment, by direct inspection, not assumption.
- Failures diagnosed from changed variables, fixed minimally, and recorded.
- Two maintained repos: working code + methodology.
- No credential values in notes, logs, or docs — locations only.
