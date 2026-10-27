# coding-tool-blueprint

How a successful AI coding tool should be built — and how it should work.

This is the companion repository to the **vast-coding-vm** project (dual-GPU coding VM: local Quadro P4000 passthrough + rented vast.ai RTX 3090). It captures the verified architecture, the build process, and the hard-won operational lessons (with an error-learning loop) from building and running that system.

## Contents
- [BUILDING_A_CODING_TOOL.md](BUILDING_A_CODING_TOOL.md) — the full methodology: architecture, build sequence, verification gates, and the error-learning loop.

## Source project
The main project repo: `jhartzell-code/vast-coding-vm` — a vast.ai GPU lifecycle CLI (`vastvm`) plus coding-VM deployment tooling, reconstructed after a backend migration wiped the original repo mid-rebuild.

## Principles
1. **Verify, then trust.** Direct inspection beats session history and stale configs — every time.
2. **GPU capacity is a lifecycle, not a fixture.** Rented instances stop, restart, and change SSH endpoints; the tool must detect and re-point automatically.
3. **Record every error.** A persistent error-learning loop (each lesson saved to durable memory) means mistakes are never repeated.
4. **Recoverability is a feature.** Builder scripts and recovery artifacts that embed full file contents turn a catastrophic wipe into a rebuild.
