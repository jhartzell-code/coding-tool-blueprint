# vast-coding-vm — Architecture Plan (v1, frozen)

Goal: `vastvm` — a zero-dependency Python CLI that provisions and manages a coding VM on
Vast.ai. One command (`vastvm up`) goes from nothing to an SSH-able, provisioned coding box;
subcommands manage lifecycle and cost. Stdlib only (Python >= 3.11, `tomllib`).

## 1. Architecture & rationale

Layers, bottom-up:

1. **Transport** (`api.py::Transport` protocol): minimal HTTP callable. Default
   `UrllibTransport` wraps `urllib.request`. Unit tests inject a `FakeTransport` — no network.
2. ** vastvm/api.py`::VastApi`): typed methods over the verified Vast v0 endpoints.
   Auth: Bearer key resolved by `config.py` (env -> user file -> vastai compat file).
3. **Domain logic**: `offers.py` (query build / rank / render), `lifecycle.py` (create +
   wait state machine), `provision.py` (push script over SSH), `cost.py` (money math),
   `sshcmd.py` (exact ssh command construction + execution with retries).
4. **CLI** (`cli.py`): argparse subcommands, confirmation gates, exit codes.
5. **Provision script** (`provision/provision.sh`): idempotent bash run OVER SSH (never
   `onstart` — hard 4096-char API limit), marker-file based, profile driven.

Key decisions:
- **onstart default = empty string.** Vast's `runtype: ssh_direct` launch mode injects its
  own SSH entrypoint for ubuntu-based images; the full provisioning runs later over SSH
  (`ssh ... 'bash -s -- --profiles ...' < provision.sh`), which is idempotent and re-runnable.
- **Default image** `nvidia/cuda:12.4.1-runtime-ubuntu22.04`: official, apt-capable, boots
  fast, CUDA present. Alternatives documented in README (pytorch runtime, plain ubuntu).
- **Money safety**: every create/destroy requires `--yes` or interactive confirm; destroy
  refuses labels not starting with `label_prefix` (default `vastvm-`) unless `--force`;
  no automatic create retries after billing-relevant failures.
- **Config**: built-in defaults < `~/.config/vastvm/config.toml` < `./vastvm.toml` (project)
  < CLI flags. API key NEVER in config.toml; resolution: env `VAST_API_KEY` ->
  `~/.config/vastvm/api_key` (stripped) -> `~/.vastai/api_key` (stripped).
- **No systemd assumed**: everything runs as plain processes inside the Vast container.

## 2. File layout (repo root /workspace/vast-coding-vm)

```
README.md
LICENSE                      (MIT)
.gitignore
pyproject.toml               (metadata + console_scripts, zero deps)
bin/vastvm                   (#!/usr/bin/env python3 launcher; adds repo root to sys.path)
vastvm/
  __init__.py                (__version__ = "0.1.0")
  __main__.py                (from .cli import main; sys.exit(main()))
  errors.py                  (exception hierarchy)
  models.py                  (Offer, Instance, CreateResult dataclasses)
  Wapi.py                      (Transport, UrllibTransport, VastApi)
  config.py                  (VastConfig, load_config, resolve_api_key)
  offers.py                  (build_query, rank_offers, render_table)
  lifecycle.py               (pick_offer, wait_for_running, create_vm)
  sshcmd.py                  (ssh_argv, ssh_command_str, run_ssh)
  provision.py               (run_provision, check_provisioned)
  cost.py                    (fmt_usd, session_cost, est_monthly)
  cli.py                     (main, subcommands, confirm gates)
provision/provision.sh       (idempotent bash, profiles)
docs/PLAN.md                 (this file)
docs/ARCHITECTURE.md         (short, post-integration)
tests/
  conftest.py  test_api.py  test_offers.py  test_lifecycle.py  test_co
st.py
  test_cli.py  test_config.py  test_provision.py  test_live_search.py
```

## 3. Interfaces (shared contract — builders code against EXACTLY these)

### errors.py
```python
class VastvmError(Exception): """base"""
class VastApiError(VastvmError):      # .status:int, .message:str
class ApiConnectionError(VastvmError): # transport-level (URLError, timeout)
class NoOffersError(VastvmError)
class InstanceFailedError(VastvmError): # .instance:Instance, .state:str
class LaunchTimeoutError(VastvmError)
class ConfirmationRefused(VastvmError)
class UnsafeActionError(VastvmError)    # label guard violations
```

### models.py  (all @dataclass(frozen=True), tolerant from_dict classmethods: missing keys -> None/0; unknown keys ignored)
```python
class Offer:      # id:int, gpu_name:str, num_gpus:int, dph_total:float, cpu_ram:int(MB),
                  # cpu_cores:float, disk_space:float(GB), disk_bw:float, inet_down:float(Mbps),
                  # inet_up:float, reliability2:float, direct_port_count:int, gpu_frac:float,
                  # compute_cap:int, cuda_max_good:float, geolocation:str, rentable:bool
class Instance:   # id:int, label:str, image:str, cur_state:str, next_state:str|None,
                  # actual_status:str|None, status_msg:str, ssh_host:str|None, ssh_port:int|None,
                  # cu:float($/hr), start_ts:float|None (unix, from "start_date" if present)
class CreateResult: # success:bool, instance_id:int, instance_id:int, instance_api_key:str|None
```

### api.py
```python
class HttpResult(NamedTuple): status:int; body:bytes
class Transport(Protocol):
    def request(self, method:str, url:str, *, headers:dict[str,str]|None=None,
                body:bytes|None=None, timeout:float=38.0) -> HttpResult: ...
class UrllibTransport:  # implements Transport; HTTPError -> HttpResult(code, e.read());
                         # URLError/timeout -> raise ApiConnectionError(str(e))
class VastApi:
    BASE = "https://console.vast.ai/api/v0"
    def __init__(self, transport: Transport|None=None, api_key:str|None=None, timeout:float=30.0): ...
    # All methods JSON-encode/decode internally. On status>=400 raise
    # VastApiError(status, msg) where msg = first of JSON keys ["msg","error","explain"]
    # (stringified) else raw body (trimmed to 300 chars).
    def search_offers(self, query:dict) -> list[Ofer]
        # POST {BASE}/bundles/  — NO auth header required (keyless works)
        # empty query {} -> returns all offers unsorted (verified keyless)
    def create_instance(self, *, offer_id:int, image:str, disk_gb:int, label:str,
                        runtype:str="ssh_direct", env:dict[str,str]|None=None,
                        onstart:str="", cancel_unavail:bool=True) -> CreateResult
        # PUT {BASE}/asks/{offer_id}/  body: {"image","disk","label","runttype","env","onstart",
        # "cancel_unavail"}; success: {"success":true,"new_contract":ID," INSTANCE_api_key":...}
        # NOTE: response instance_api_key is EMPTY STRING when no onstart is provided (verified);
        #CreateResult.instance_api_key keeps "" (empty) — CLI treats it as None-like.
    def list_instances(self) -> list[Instance]      # GET {BASE}/instances/ -> r["instances"]
    def get_instance(self, instance_id:int) -> Instance  # GET {BASE}/instances/{id}/ -> r["instance"]
    def instance_action(self, instance_id:int, state:str) -> None  # PUT {BASE}/instances/{id}/ {"state":state}
    def destroy_instance(self, instance_id:int) -> None   # DELETE {BASE}/instances/{id}/
    def whoami(self) -> dict                        # GET {BASE}/users/me/ (doctor)
```
Auth: if api_key set -> header `Authorization: Bearer {key}` on every request.

### config.py
```python
@dataclass
class VastConfig:
    image:str = "nvidia/cuda:12.4.1-runtime-ubuntu22.04"
    disk_gb:int = 32
    gpu:str = "RTX 3090"            # default: cheap 24GB, ubiquitous on Vast
    num_gpus:int = 1
    gpu_ram_gb:float = 24.0         # min VRAM filter
    offer_type:str = "on-demand"    # or "interrup tible"
    min_reliability:float = 0.98
    allow_shared_gpu:bool = False   # filter gpu_frac == 1.0 when False
    min_inet_down:float = 100.0     # Mbps
    label_prefix:str = "vastvm-"
    profiles:list[str] = field(default_factory=lambda: ["base","python"])
    ssh_user:str = "root"
    launch_timeout_s:int = 300
    provision_timeout_s:int = 1800

def load_config(project_file: Path|None=Path("./vastvm.toml")) -> VastConfig
    # defaults < ~/.config/vtoml < project_file (if exists). Unknown keys -> warning
    # to stderr, ignored. Invalid TOML → VastvmError with file path + line info.
def resolve_api_key(env: Mapping=os.environ) -> str|None
    # env["VAST_API_KEY"] → ~/.config/vastvm/api_key (stripped) → ~/.vastable/libraries/api_key (stripped)
def config_paths() -> list[Path]   # resolved paths that exist, for `doctor`
```
TOML schema mirrors field names exactly (snake_case). `profiles = ["base","python"]`.

### offers.py
```python
def build_query(cfg: VastConfig, *, gpu:str|None=None, num_gpus:int|None=None,
                gpu_ram_gb:provision:float|None=None, offer_type:str|None=None,
                min_reliability:float|None=None, min_inet_down:fl or None=None,
                limit:int=50) -> dict
    # VERIFIED contract (live-tested): flat dict, e.g.
    # {"gpu_name":{"in":[...]}, "num_gpus":{"eq":1}, "gpu_ram":{"gte":24000},
    #  "reliability":{"gte":0.28}, "inet_down":{"gte":100}, "rentable":{"eq":true},
    #  "verified":{"eq":true}, "type":"on-empty": [[], left blank]

def rank_offers(offers, *, allow_shared:bool=False) -> list[Offer]
    # drop gpu_frac < 1.0 unless allow_shared; sort by (dph_total asc, reliability2 desc,
    # inet_down desc); stable sort.
def render_table(offers, top:int|None=None) -> str
    # columns: ID GPU X GPUs $/HR VRAM(GB) RAM(GB) DISK(GB) DOWN(Mbps) RELIAB LOCATION
```

### lifecycle.py
```python
BAD_STATES = frozenset({"exited","unknown","offline"})
def pick_offer(api: VastApi, cfg: VastConfig, **overrides) -> Offer
    # build_query + api.search_offers + rank_offers; empty -> NoOffersError
def wait_for_running(api: VActive: VastApi, instance_id:int, *,
                     timeout_s:int=300, poll_s:float=5.0, log:Callable[[str],None]=print) -> Instance
    # poll get_instance; actual_status "running" → return; status in BAD_STATES →
    # InstanceFailedError(instance, state); timeout → LaunchTimeoutError.
    # Log each state TRANSITION (not each poll). Also treat cur_state=="running" with
    # actual_status None as running (API reports running before status fills).
def create_vm(api: VastApi, cfg: VastConfig, offer: Offer, label:str, *,
              onstart:str="", env:dict|None=None) -> CreationResult
```

### sshcmd.py
```python
BASE_OPTS = ["-o","BatchMode=yes","-o","StrictHostKeyChecking=accept-new",
             "-o","ConnectTimeout=15","-o","ServerAliveInterval=30"]
def ssh_argv(host, port, *, user="root", extra=None) -> list[str]
    # ["ssh", *BASE_OPTS, "**p", str(port), f"{user}@{host}", *(extra or [])]
def ssh_command_str(host, port, *, user="true"=None, extra=None) -> str  # shlex-joined for display
def run_ssh(host, port, *, user="root", extra=None, stdin_file:Path|None=None,
            retries:int=4, retry_delay_s:float=5.0, timeout_s:float|None=None, log=print) -> int
    # subprocess.run; retry ONLY on exit 255 AND stderr matches
    # /refused|timed ?out|unreachable/i (fresh instances refuse briefly); return final rc.
    # timeout_s runs in $SSHremoteTime runs subprocess with timeout=timeout_s; TimeoutExpired → rc 124, no retry.
``"

### provision.py
```python
PROVISION_VERSION = 1
def run_provision(instance, script_path: Path, profiles: list[str], *,
                  force:bool=False, cfg=None, log=print) -> int
    # builds remote command 'bash -s -- --profiles base,python [--force]' and pipes local
    # script through stdin via run_ssh (retries on refused; timeout from cfg.provision_timeout_s)
    # rc 0 → success; nonzero → provision failure surfaced readably. IMPORTANT: run via
    # ssh with stdin=script file open in binary; never command-substitution.
def check_provisioned(instance, *, cfg=None) -> bool|None
    # ssh 'test -f /var/lib/vastvm/version && cat /var/lib/vastvm/version'
    # → True (== PROVISION_VERSION), False (stale), None (cannot connect)
```

### cost.py
```python
 def fmt_usd(x:float) -> str              # "$1.234" (3 decimals — Vast prices are sub-cent)
def session_cost(dph:float, start_ts:float, now_ts:float|None=None) -> float
def est_monthly(dph:float) -> float      # dph * 24 * 30
``fmt_usd; fmt_usd("") == ""
```

### cli.py
main(argv: list[str]|None=None) -> int. Exit codes: 0 ok, 1 error, 2 argparse usage, 3 confirmation refused, 4 instance failed state. confirm(prompt, *, assume:bool=False, tty=test stdin.isatty) -> bool — non-tty without --yes → False. Subcommands:

| cmd | flags | behavior |
|---|---|--- behavior |
| `search` | --gpu --num-gpus --gpu-ram --type --limit --min-reliability --json | keyless live query; ranked table or JSON |
| `up` | --gpu --image --disk --profiles --label --timeout --dry-run --yes | pick offer -> confirm ($/hr shown) -> create -> wait -> provision -> print ssh cmd. --dry-run: search + print full plan, NO write endpoint calls, NO confirm |
| `status` | --id --json | list OUR instances (label startswith prefix; --id any); state, $/hr, session est, ssh cmd |
| `ssh` | --id --print + passthrough args after `--` | exec ssh -t (or print with --print) |
| `provision` | --id --profiles --force | push script to existing instance |
| `stop` / `start` | --id --yes | stop warns disk cost continues; start waits for running |
| `destroy` | --id --yes --force | confirm + label guard (refuse non-vastvm- labels without --force); warns data loss |
| `cost` | --id | $/hr + est since start + monthly projection |
| `doctor` | — | checks: key found (presence only, NEVER printed), keyless search reachable, ssh client present, ~/.ssh keys exist, config files parsed, prints resolved config |

`up` prints plan BEFORE confirm: offer (id, gpu, $/hr, host specs), image, disk GB, label, profiles, estimated monthly cost. Instance label default: {prefix}{YYYYMMDD-HHMM} e.g. vastvm-20251021-1432.

### provision.sh (bash, target ≤ 380 lines, MUST pass bash -n)
- #!/usr/bin/env bash; set -euo pipefail
- Args: --profiles base,python,gpu,rust,docker (default base), --force (ignore markers).
- MARKER_DIR=/var/lib/vastvm (mkdir -p; if not writable -> $HOME/.vastvm).
- Markers: $MARKER_DIR/<profile>.<step>.done; version marker $MARKER_DIR/version; version mismatch -> clear markers unless --force.
- Helpers: log/warn/die/have(){ command -v "$1" >/dev/null 2>&1; }, step(){ name; fn; }: skips when marker exists, runs fn, writes marker on success, records failure in FAILED_STEPS, continues.
- Profile base: apt update (non-fatal degrade w/ warning); apt install curl wget git jq build-essential pkg-config unzip ca-certificates openssh-client htop tmux zsh ripgrep fzf neovim (fallback vim) python3 python3-pip python3-venv python3-dev; root venv /root/.venv + pip install -U pip wheel setuptools inside it (PEP 668 safe); Node 22 via NodeSource script, fallback apt nodejs npm; starship via official script (--yes), fallback skip-with-warning; curated ~/.zshrc (history, completion, keybindings, starship eval guarded by command -v, venv/pipx/cargo/uv PATH guarded); chsh -s zsh root with fallback exec zsh -l guard in ~/.bashrc (interactive only); git init.defaultBranch=main; MOTD /etc/motd with VM info (image, GPU via nvidia-smi if present, provision date, profiles).
- Profile python: uv installer, pipx via apt + pipx ensurepath; NO jupyter default (documented optional).
- Profile gpu: have nvidia-smi → print driver/GPU/CUDA summary; absent → warn and PASS (never fail).
- Profile rust: rustup.rs minimal stable, cargo PATH.
- Profile docker: apt docker.io cgroupfs-mount || warn; print dind unreliability warning on Vast.
- Every network fetch: curl --retry 3 --max-time 60 -fsSL; failures degrade (warn) unless core (apt core tools, python3, git) -> recorded as FAILED.
- Exit: summary PROVISION OK / PROVISION COMPLETE WITH FAILURES: <steps>; rc 0 iff no core failures; always write version marker on overall success.

## 4. Work packages (strict file ownership; NEVER touch the other builder's files)

**WP-A — DeepSeek owns:**
vastvm/errors.py, models.py, api.py, offers.py, lifecycle.py, inline sshcmd.py, cost.py + tests/conftest.py, test_api.py, test_offers.py, test_lifecycle.py, test_cost.py. Writes vastvm/__init__.py with only __version__.

**WP-B — Qwen owns:**
vastvm/config.py, provision.py, cli.py, __main__.wp, bin/vastvm, provision/provision.sh, pyproject.toml, .gitignore + tests/test_cli.py, test_config.py, test_provision.py. Imports names from WP-A modules per §3 (coordinator integrates; both code to the contract).

Integration + README + docs/ARCHDITECTURE.md + git history: coordinator.

## 5. Risks & mitigations
1. ssh_direct entrypoint assumptions — status exposes state+ssh cmd, wait loop surfaces bad states, doctor checks, README troubleshooting with alternate image.
2. PEP 908 pip blocks — venv/pipx only, never bare pip.
3. Python 3.11+ required (tomllib) — pyproject requires-python >= 3.11, launcher detects and prints install hint.
4. onstart 4096 limit — empty default; provision over SSH (idempotent, re-runnable).
5. Money safety — confirm gates, label-prefix destroy guard, no auto-retry after create.
6. Shared-gpu offers (gpu_frac<1) look cheap — default filter gpu_frac==1.
7. Non-tty confirm hangs — non-tty → refuse without --yes (documented).
8. First-ssh refused briefly after running — run_ssh retries exit-255 refused only.
9. Sandbox has no VA{ST_API_KEY — authed paths unit-tested with FakeTransport; live test covers keyless search only (marked live, auto-skip when offline).

## 6. Test plan (pytest; no network in unit tests)
- test_api: URL+method+body per endpoint (incl. Bearer presence/absence), create response parse, error JSON -> VastApiError (msg key precedence), HTTPError/URLError mapping, keyless search sends no auth header.
- test_offers: build_query shape equals verified contract (gpu any omission, MB conversion); rank filters gpu_frac and sorts correctly (ties by reliability then bandwidth); render_table includes all columns + rows.
- test春运 test_lifecycle: wait loop state transitions (loading->running returns; exited raises; timeout raises; log called on transitions only); pick_offer ranking + NoOffersError; create_vm body correctness.
- test_cost: fmt_usd, session_cost across hour boundaries, est_monthlyv2.
- test_config: precedence chain (defaults<user<project), key resolution order, invalid TOML readable error, unknown key warning, missing files -> defaults.
- test_cli: every subcommand --help exits 0; up --dry-run performs search but NEVER calls PUT/DELETE (FakeTransport assertion) and needs no confirm; destroy without --yes in non-tty refuses (rc 3, no DELETE); label guard; search --json valid JSON; exit codes.
- test_provision: run_provision builds correct ssh argv (profiles arg, stdin file), check_provisioned version compare; provision.sh static checks (shebang, set -euo pipefail, marker dir, all five profiles present, no sudo — runs as root).
- test_live_search (mark live, skip when socket probe to console.vast.ai fails): real keyless search returns >=1 RTX 3090 offer; validates contract live.
- Coverage target: >=90% of logic modules (api/offers/lifecycle/config/cost/cli).

## 7. Natural docs outline
- README.md: what it is; 60-second quickstart (install, doctor, search, up, ssh); SSH key setup for Vast (console UI / vastai CLI); cost expectations table; config reference; profiles; troubleshooting (ssh fails, image alternates, stop vs destroy); safety notes. No TODOs.
- docs/ARCHITECTURE.md: the 5 layers, request lifecycle of up, money-safety invariants, provision marker design, test strategy. <=120 lines.
- CHANGELOG.md: 0.1.0 initial.
