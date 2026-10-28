# Lessons — provisioning a cloud GPU VM with bash

Every entry below is a defect that actually shipped, was found by a real test run, and
was then fixed. They are written as rules because each one cost a broken provision.

## bash / `set -Eeuo pipefail`

1. **`local a="$1" b="/tmp/$a"` does not work.** All expansions on a `local` line are
   evaluated before any of the assignments take effect, so `$a` is still unset — and
   under `set -u` the script dies with `a: unbound variable`. Use two statements.
   (shellcheck SC2318 flags exactly this.)
2. **`try` only sees the exit status of the last command in a chain.** `try "x" a || b`
   reports success when `a` fails, because `b` runs and succeeds. Wrap the thing you
   actually care about into a function, or hand `try` a single command.
3. **A quoted heredoc does not expand variables.** `<<'EOF'` writes `${SSH_PASSWORD_AUTH:-no}`
   literally into sshd config and breaks SSH. Use an unquoted `<<EOF` for config files
   that need values interpolated, and a quoted one for files that must stay verbatim
   (e.g. a generated script).
4. **`local` outside a function is a runtime error**, not a style issue.
5. Empty arrays are safe on bash ≥ 4.4 (`${#arr[@]}`, `${arr[*]}`), but guarding with an
   early `return 0` is free and documents intent.
6. `$( ... )` strips **trailing newlines but not carriage returns**. When the value
   becomes a URL path segment, `tr -d '\r\n'` it first.

## systemd

7. **`systemctl is-system-running` is not a liveness test.** It exits non-zero for the
   perfectly healthy `degraded` state, so every step gated on it silently takes the
   fallback branch. Use `[ -d /run/systemd/system ]`.
8. **`command -v systemctl` is true in containers with no systemd.** Same wrong branch,
   different cause. One predicate — `systemd_running()` — must be used everywhere.
9. **A per-user (`systemctl --user`) unit cannot be enabled from a root-only
   provision**: the target user has no session bus. Write a system unit with `User=`
   instead, and skip unit installation entirely when systemd is absent.

## Package installs

10. **Batch apt.** One `apt-get install` per package costs ~1–2 s of startup each; the
    base list has 22 entries. Install the missing set in one call, and fall back to
    one-at-a-time only if the batch fails, so a single unknown package cannot take the
    whole batch down.
11. `dpkg-query -W -f='${Status}' | grep 'install ok installed'` correctly returns false
    for half-installed (`iU`) packages, which is what you want — they get reinstalled.

## Downloads and installs

12. **Never curl straight onto `$PATH`.** A truncated transfer leaves a corrupt
    executable that shadows nothing and fails at runtime. Download to `/tmp`, then
    `install -m 0755` (atomic, sets the mode, no separate `chmod`).
13. Verify the upstream filename before blaming your script: Helm's installer really is
    `get-helm-3` with no `.sh` suffix, and HashiCorp zips use `linux_amd64`, not
    `linux-amd64`. A stub fixture with the wrong name produces a fake failure.
14. Gate `.bashrc` / `/etc/profile.d` PATH exports on the binary actually existing after
    the install, or you advertise directories that nothing created.

## Generated verifiers

15. **A generated `verify.sh` must set its own `PATH`.** Non-interactive runs (cron, CI,
    `ssh host ./verify.sh`) never source `.bashrc`, so every tool installed into
    `~/.cargo/bin`, `/usr/local/go/bin` or `~/.local/bin` reports MISSING and the
    verifier cries wolf.
16. Report required vs optional tools separately and exit non-zero only for required
    ones missing.

## Testing the script itself

17. **A failure-only harness is not a test.** Serve local fixtures from a stubbed `curl`
    so the download → extract → install branches actually execute; otherwise "all green"
    only proves the failure recorder works.
18. Model the stub on the real tool's behaviour (arg parsing, exit codes, output), or the
    harness tests the stub instead of the script.
19. Assert idempotency by rerunning on the same box and grepping for duplicates — one
    managed block in `.bashrc`, no repeated `export PATH`, no second unit file.
20. Test the systemd-present branch by creating `/run/systemd/system` and a permissive
    `systemctl` stub; the branch that never runs on a container image is the branch that
    breaks on the VM that has systemd.

## Review process

21. **A model stage can return `finish_reason: stop` with `output: null`** — budget spent
    entirely on reasoning tokens. Treat that as a failed review, never as "no findings".
22. Verify the reviewer's claims empirically before acting. "This breaks under `set -u`"
    is a hypothesis until a two-line test proves it; two of this round's model claims did
    not reproduce.
23. Reviewers are only as good as the contract you give them. Freeze the interface, list
    the landmines already fixed, and forbid rewrites.
