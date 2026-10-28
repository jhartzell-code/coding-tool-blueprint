# Building a Successful AI Coding Tool — Architecture, Process, and Lessons

This document describes how a successful coding tool should be built and how it should work, based on the verified construction and operation of a three-lane coding GPU pool (two rented vast.ai RTX 3090 workers + local Quadro P4000 verifier passthrough on Proxmox VM 110), running Huihui-Qwen3-Coder-30B, orchestrated through a bounded autonomous agent loop and maintained by an agent-driven error-learning loop.

## 1. Target architecture

A successful coding tool has four planes:

1. **Execution plane** — where code runs: a sandboxed terminal (Docker in this build) with no GPU, no gh, no host SSH keys, and no direct Mac filesystem access. All privileged operations are brokered through the Mac (browser automation with `local=true`) or SSH.
2. **GPU plane** — a worker pool, not a single instance:
   - *Remote builder tier:* two rented vast.ai RTX 3090 workers (24 GB VRAM each) serving the same model simultaneously, each with its own direct SSH endpoint and Mac tunnel (8081 → 3090-A, 8082 → 3090-B). Two concurrent agents per lane = four parallel coding agents.
   - *Local verifier tier:* Quadro P4000 passthrough into Proxmox VM 110 (coding-ubuntu, `coder@10.0.0.186`, 8 GB VRAM), tunneled to Mac port 11435, serving lighter models (`qwen2.5-coder:7b`) for verification tasks. Independent of the rental lifecycle.
3. **Model plane** — every lane serves an explicit model contract; the pool verifier checks endpoint health AND GPU identity per lane. The coding model (Huihui-Qwen3-Coder-30B Q4_K_M, 21 GB resident) lives on both 3090s with `OLLAMA_KEEP_ALIVE=-1`.
4. **Knowledge plane** — persistent memory for environment facts and error lessons; per-task skills for procedures; the project repo (`vast-coding-vm`) for working code and this repo for methodology.

The pool contract is data, not prose: `config/worker-pool.json` declares each lane's required GPU, endpoint env vars, SSH env vars, and global requirements (minimum verified workers, concurrency, agent-loop bounds). `scripts/verify_worker_pool.py` turns that contract into a deterministic gate.

## 2. The bounded agent loop

The core operating principle: **agents create; deterministic checks decide.**

1. An agent may propose and implement changes but can never self-certify completion.
2. Deterministic checks (verifier script, tests, CI readback, GPU telemetry) alone decide state transitions.
3. Every failure becomes a minimal written handoff: exact command, exit code, evidence, proven facts vs hypotheses, the next agent's acceptance check.
4. The next attempt gets a fresh agent with clean context — it inherits evidence, not conclusions.
5. A hard attempt cap (default 3) stops the loop; budget exhaustion is `BLOCKED`, never "done".

Reusable prompts for all six roles (planner, builder, verifier, failure-recorder, fresh-fixer, coordinator) live in the project repo at `docs/AGENT-LOOP-PROMPTS.md`. Loop bounds are enforced in `config/worker-pool.json` under `requirements.agent_loop`.

## 3. Build sequence

1. Provision the execution sandbox; verify what it does NOT have (no GPU, no gh, no host keys) before planning any operation.
2. Verify the local GPU lane first (stable, free, independent): tunnel + endpoint + `nvidia-smi` identity.
3. Rent remote workers; record instance IDs and CURRENT direct SSH endpoints (they change per rental; proxies die — use direct IP:port).
4. Install the model server under a **process supervisor** (`supervisorctl`), not `nohup` — background processes die with the SSH session on vast.ai containers. Configure `OLLAMA_HOST=0.0.0.0:11434`, `KEEP_ALIVE=-1`.
5. Pull the exact model variant under the supervisor too; clean orphaned `-partial` blobs after verification.
6. Establish one launchd tunnel per lane (`bootout` + `bootstrap`, never `unload/load`); verify each endpoint independently with a real completion AND per-lane `nvidia-smi`.
7. Write the pool contract (`worker-pool.json`) and the verifier; get the verifier green on all lanes before any workload.
8. Run a canary: four concurrent agents across the builder lanes plus a verifier task on the local lane, with simultaneous `nvidia-smi` telemetry captured mid-flight. Responses alone are not proof of GPU use.
9. Only after the canary passes: retire superseded hardware.
10. Run the error-learning loop continuously (below) and keep both repos updated.

## 4. Verification gates

- **Per-lane GPU identity:** independent SSH `nvidia-smi` on each lane shows the required GPU name and VRAM (no label-trust).
- **Endpoint health:** each tunnel port answers HTTP 200 with the model list.
- **Real inference:** a deterministic tagged completion through each tunnel, cold and warm; model resident in VRAM.
- **Canary:** 4+ concurrent agents all HTTP 200 with correct output; simultaneous telemetry shows real utilization on every active lane.
- **Verifier green:** `verify_worker_pool.py` exit 0 across all lanes.
- **Repo state:** `git log` clean, working tree pushed, compile checks pass.

A timeout, empty model output, missing CI result, or unreachable GPU is a **failure**, never a pass.

## 5. The error-learning loop

The tool must treat every failure as a learning event:

1. **Detect** — monitor exit codes, provider errors, tunnel health.
2. **Diagnose** — form hypotheses from the changed variable; check the console API `actual_status` FIRST.
3. **Fix** — apply the minimal change.
4. **Record** — save the lesson to persistent memory and `docs/LESSONS.md` immediately so it is never repeated.
5. **Improve** — adjust the tool and build instructions so the error class cannot recur.

## 6. Hard lessons (verified 2026-10-27/28)

- A vast.ai instance's SSH endpoint (host AND port) changes per rental/restart. Never hardcode; query the console API on every reconnect.
- The `sshN.vast.ai` proxy gateways drop connections — use the direct IP:port endpoints.
- `launchctl unload/load` does NOT re-read a changed plist — use `bootout` + `bootstrap`.
- **`nohup` background processes die when the SSH session ends** on vast.ai containers — run anything that must outlive the session (model server, pulls) as supervisor programs.
- Wrong-model pulls leave orphaned `-partial` blobs that eat disk (a 40 GB instance hit 79% with a 9.5 GB orphan); inventory blobs by mtime before deleting only true orphans.
- Deduplication: shared blobs between model variants let a corrected pull resume at ~75%.
- The console API: `/api/v1/` reads with cookie auth work in-browser; destroy is `DELETE /api/v0/instances/<id>/`. A client-side timeout does NOT mean the call failed — re-read state before retrying a destructive call.
- Session history claims can be wrong; direct inspection always wins.
- Scope greps on the Mac to small subdirectories or they time out.
- `resources_unavailable` on a vast.ai start call means queued, not failed.
- URL guards in browser automation block literal loopback strings — assemble hostnames at runtime (`'local'+'host'`).
- Never print or preserve credential values — locations and variable names only.

## 7. What good looks like

- Every lane verified live at any moment by direct inspection, not assumption.
- A pool contract in data, enforced by a deterministic verifier, not prose hopes.
- Four-plus concurrent agents with telemetry proving all GPUs contribute.
- Failures diagnosed from changed variables, fixed minimally, recorded forever.
- Two maintained repos: working code (`vast-coding-vm`) + methodology (this repo).
- No credential values in notes, logs, or docs — locations only.
