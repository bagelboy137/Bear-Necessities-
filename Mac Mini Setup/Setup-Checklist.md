# Mac Mini — Always-On Claude Setup Checklist

Rebuilt 2026-08-03. Replaces the missing `mac-mini-claude-setup-checklist.md` referenced by the October reminder task.

**Purpose:** a Mac mini that stays awake 24/7 and runs Claude against the `Claude` folder without anyone sitting at it.

**Hardware is NOT bought** (corrected 2026-09-04). Conor is waiting on independent benchmarks after the machine
releases, then ordering. Intended config: M5 Pro, 18-core CPU / 20-core GPU, 64GB, 512GB, ~$2,899 retail /
~$2,679 education. Section 1 is prep you can do regardless; §2 onward starts the day it actually arrives.

⚠️ **Do the pre-move punch list first:** `Migration-Audit-2026-09-02.md`. Several items in it are laptop-side and
cannot be done once the folder has moved.

---

## 1. Before it arrives — accessories and prep

**Intended config (not ordered) · M5 Pro · 18-core CPU / 20-core GPU · 64GB · 512GB · ~$2,899 retail / ~$2,679 edu.**
Order pending post-release benchmarks.
The 64GB tier was the one irreversible choice (unified memory is not upgradeable); the 18-core was taken for
prefill latency on big tool schemas. Rationale in `Hermes-Local-Agent.md` Part 1 and `Memory.md`.

Order these so day one isn't blocked:

- [ ] **HDMI dummy plug / display emulator (~$10).** Load-bearing, not optional: `../Fusion CAD Agent/Hardware-Requirements.md`
      records that a fully headless mini may not drive the window server, and *the render sweep cannot run unattended at all*
      if it doesn't. You will have a real monitor attached on day one — the test is unplugging it (§9).
- [ ] **External drive for Time Machine.** Mandatory, not optional, under the single-authoritative-copy decision (§7).
- [ ] **Thunderbolt SSD for the model library.** 512GB internal fills at ~20GB/model; `import-external-model.sh` already
      implements the supported `lms import --symbolic-link` path. Cheaper than Apple's $270/TB internal.
- [ ] **Ethernet cable** — more reliable than Wi-Fi for an always-on box. Reserve its IP on the router (§2).
- [ ] Monitor + keyboard for first boot, or another Mac with Screen Sharing.

- [ ] **Confirm Drexel enrolment is active** if you have not taken delivery yet — education pricing runs through UNiDAYS
      and saved $220 on this build. Moot once the order ships.

*Superseded, kept for history: the July 2026 buying guidance (base M4 16GB, refurb M1/M2 as the value option, "do not
expect sub-$500") and the October purchase target. The M5 Pro launch on 2026-08-25 obsoleted all of it — no M4 mini
reaches 64GB. See `CLAUDE.md` → "Hardware plan — SUPERSEDED".*

---

## 2. First boot

- [ ] Run through macOS setup, sign in with your Apple ID
- [ ] Name the machine something identifiable (e.g. `claude-mini`) — System Settings → General → About → Name
- [ ] Install all pending macOS updates before configuring anything else
- [ ] ⚠️ **Leave the disk as the default APFS (case-insensitive).** Do not choose case-sensitive at install
- [ ] Connect via **ethernet** if possible
- [ ] Set a static IP or DHCP reservation on your router so you can always find it

---

## 3. Keep it awake — the core of "always on"

System Settings → **Energy** (or Battery → Options):

- [ ] **Prevent automatic sleeping when the display is off** → ON
- [ ] **Wake for network access** → ON
- [ ] **Start up automatically after a power failure** → ON ← critical for unattended recovery
- [ ] Display can sleep; the *machine* must not

Verify from Terminal:

```sh
pmset -g            # check sleep values
sudo pmset -a sleep 0 disksleep 0   # belt and braces
```

- [ ] Confirm `sleep` shows `0`

---

## 4. Survive a reboot unattended

A power blip at 3am shouldn't take the machine offline until you notice.

- [ ] **Turn off FileVault**, *or* accept that a reboot requires you to unlock the disk before login. FileVault + auto-login are mutually exclusive
  - Trade-off: FileVault off means the disk is readable if the machine is physically stolen. For a home machine holding this folder — which includes portfolio and severance detail — decide deliberately
- [ ] Enable **automatic login** — System Settings → Users & Groups → Automatically log in as
- [ ] Set apps you need to launch on login — System Settings → General → Login Items
- [ ] Test: pull the power, plug it back in, confirm it returns to a logged-in desktop with no keyboard input

---

## 5. Remote access — including from the iPad

Four jobs, four tools. Trying to do all of it with one app is where this goes wrong.

| Job | Tool | Why this one |
|---|---|---|
| **Drive Claude** — the daily case | **Claude app on the iPad**, paired to the mini (same QR flow as §6) | Universal app; no iPad-specific setup. You type, the work runs on the mini. Pro/Max required |
| **Full screen control** — Fusion, the LM Studio GUI, System Settings | **Jump Desktop** (iPadOS, one-time ~$25 — check current price) | **Apple ships no Screen Sharing client for iPadOS.** A third-party VNC/RDP app is mandatory, not optional. Jump's Fluid protocol holds up over the internet where raw VNC does not, and it maps the Magic Keyboard trackpad properly |
| **Shell** | **Blink Shell** + `mosh` (`brew install mosh` on the mini) | mosh survives the iPad sleeping and switching between Wi-Fi and cellular; plain SSH drops every time |
| **Reach it outside the house** | **Tailscale** | Free personal tier, apps on macOS and iPadOS, WireGuard, no port forwarding, no static WAN address |

**The rule that outranks the rest: never port-forward 5900 or 22.** This box runs
FileVault **off** with **auto-login** (§4), so anything that reaches it arrives at an
already-unlocked desktop holding portfolio and employment records. Apple's built-in VNC
also caps its password at 8 characters. Tailscale is the security boundary — put every
remote path inside it.

Also worth knowing:

- The **HDMI dummy plug** in §1 is what makes headless screen sharing usable at a real
  resolution rather than whatever the window server invents with no display attached.
- **Universal Control is not a path here.** It extends a Mac's keyboard and trackpad
  *to* a nearby iPad on the same Apple ID — the opposite direction, and local only.

- [ ] Enable **Screen Sharing** — System Settings → General → Sharing → Screen Sharing
- [ ] Enable **Remote Login (SSH)** if you want shell access
- [ ] Install **Tailscale** on the mini, the iPad, and the laptop; confirm the mini's
      `100.x` address answers from the iPad **on cellular, Wi-Fi off** — that is the real test
- [ ] Install **Jump Desktop** on the iPad, connect over Tailscale, confirm you can
      actually drive Fusion with it (small hit targets are the thing that fails)
- [ ] `brew install mosh`, then confirm Blink reconnects after the iPad has slept
- [ ] Confirm you can reach it from your laptop before removing the monitor

---

## 6. Claude setup

- [ ] Install the Claude desktop app
- [ ] Sign in — **Claude Dispatch requires a Pro or Max subscription**
- [ ] Pair your phone to the Mac via QR code in Dispatch
- [ ] Confirm you can trigger work from the phone and see it run on the mini
- [ ] Grant the app access to the `Claude` folder
- [ ] Verify it reads the root `CLAUDE.md` — ask it to name your projects; it should list all **15** without being told

---

## 7. Move the Claude folder over

**Decided:** the mini is the **single authoritative copy**. This is a *move*, not a copy — no two-way sync with the laptop.

### How to move it — do NOT drag the folder in Finder

**2.1GB of the folder's 2.6GB is rebuildable junk that must not travel**, and a
`git clone` is not a substitute either, because four directories are gitignored on
purpose and exist only in the working copy. Use the exclusion list:

```sh
# from the laptop, once the mini has SSH/Screen Sharing (step 5)
rsync -avh --progress \
  --exclude='.venv*' --exclude='node_modules' --exclude='__pycache__' \
  --exclude='dist/' --exclude='.wrangler/' --exclude='.vinext/' \
  --exclude='_to_delete/' \
  ~/Claude/ <mini>:~/Claude/
```

| Excluded | Size | Why |
|---|---|---|
| `Fusion CAD Agent/.venv-cq` | 1.29GB | uv Python 3.12 symlinked into `~/.local/share/uv/` — rebuild it below |
| `Bear Necessities/website/node_modules` | 709MB | `npm ci` rebuilds it |
| `website/dist`, `.wrangler`, `.vinext` | ~8MB | build output |
| `_to_delete/` | 145MB | dead 3.9 venvs staged for removal |

**Gitignored but essential — these are why `git clone` is not enough:**
`Bear Necessities/website/` (its own repo, no remote), `product/reference/competitors/`
(96 photos), `product/cad/native-modules/` (delivery copy), `Fusion CAD Agent/exports/bncad/`
(run history and benchmark evidence).

Then rebuild the two environments on the mini:

```sh
uv venv --python 3.12 "$HOME/Claude/Fusion CAD Agent/.venv-cq"
uv pip install --python "$HOME/Claude/Fusion CAD Agent/.venv-cq/bin/python" cadquery
( cd "$HOME/Claude/Bear Necessities/website" && npm ci )     # needs Node >= 22.13
```

- [ ] Folder rsynced with the exclusions above
- [ ] `.venv-cq` rebuilt with `uv` (§7d has the same command and the reasoning)
- [ ] `npm ci` run in `website/`
- [ ] `git -C ~/Claude status` on the mini matches the laptop (clean) — a better
      integrity check than counting files
- [ ] ⚠️ **Set up Time Machine to an external drive before retiring the laptop copy.** One authoritative copy is one point of failure until backups exist
- [ ] Confirm everything works on the mini for a week
- [ ] Then archive or delete the laptop copy so it can't drift and later be mistaken for current
- [ ] Reach the folder from the laptop via Dispatch or Screen Sharing — do not re-create a local copy
- [ ] Confirm all **17 `CLAUDE.md`**, **17 `Memory.md`** and **4 `AGENTS.md`** files arrived intact
      (17 = root + 15 top-level projects + `Home Projects/Home Network`; `AGENTS.md` = root, Bear Necessities,
      Career, Mac Mini Setup). Count them: `for n in CLAUDE.md Memory.md AGENTS.md; do printf '%s: ' "$n";
      find ~/Claude -name "$n" -not -path '*/node_modules/*' -not -path '*/.venv*' -not -path '*/.git/*' | wc -l; done`
- [ ] Confirm the git repo came with it: `git log` should show history
- [ ] **Bring the model library across rather than re-downloading it.** ~28GB was on
      the laptop as of the last `storage-check.sh`, and the 64GB roster adds
      `qwen3-coder-30b` (~16GB of weights). Copy `~/.lmstudio/models` to the
      Thunderbolt SSD and re-import with the supported symlink path
      (`tools/local-ai/import-external-model.sh`, which wraps `lms import
      --symbolic-link`) instead of pulling everything again over the wire
- [ ] ⚠️ **Re-register all scheduled tasks.** The definitions in `Scheduled/` travel with the folder, but the *schedules themselves* live in app config and do **not**. Recreate each one:
  - [ ] `chestnut-hill-monthly-updates` (monthly)
  - [ ] `septa-funding-watch` (weekly)
  - [ ] `bellwether-district-watch` (monthly)
  - [ ] `weekly-lexus-rx-hybrid-watch` (weekly)
  - [ ] `mac-mini-claude-project-reminder` (one-time — retire this once the mini is running)
- [ ] Decide which machine is authoritative, so the laptop and mini don't diverge

---

## 7b. Local AI stack (LM Studio/llmster) — SCRIPTED

The toolkit supports the official headless `llmster` daemon and the tested desktop-service fallback. Preview is safe and makes no changes.

```bash
cd "<Claude folder>/Mac Mini Setup/tools/local-ai"
./bootstrap-mac-mini.sh            # preview hardware profile and actions

# Preferred headless runtime (official LM Studio installer):
curl -fsSL https://lmstudio.ai/install.sh | bash

./bootstrap-mac-mini.sh --apply --download-models
./prepare-mlx-runtime.sh          # verify latest stable MLX is selected
python3 local-ai-manager.py doctor
python3 local-ai-manager.py benchmark
./verify-local-ai.sh --expect-autostart
./acceptance-test.sh --post-reboot  # run within 30 minutes after a real reboot
```

Full reasoning in `tools/local-ai/README.md`. Three things to know:

- **Autostart depends on auto-login** (step 4). Both headless and desktop recovery are per-user LaunchAgents.
- **Use the RAM profile, then benchmark.** `local-ai-manager.py plan` selects a conservative roster; test once with Fusion closed and again with Fusion open.
- **MLX is mandatory for primary chat/coding models.** Downloads force `--mlx`; doctor and acceptance inspect LM Studio metadata and fail on an accidental GGUF variant.
- **Do not use `--lan` casually.** On LM Studio 0.4+, enable Require Authentication, create a scoped token, and use `LM_API_TOKEN`. Never forward port 1234 through the router.
- Read `tools/local-ai/OPERATING-GUIDE.md` before adding optional models or raising context length.

## 7b-bis. Obsidian vault — DOES NOT TRAVEL, AND IS NO LONGER JUST A MIRROR

The vault lives in iCloud
(`~/Library/Mobile Documents/com~apple~CloudDocs/Obsidian Vault/Obsidian Vault/`),
outside the folder and its git repo. Same portability gap as the scheduled tasks
and the plugins below.

> ⚠️ **Changed 2026-09-02 — this section's old assumption is dead.** The vault used
> to be *purely derived*: losing it cost nothing, because `obsidian-port.py`
> regenerated it. It now also holds **`Context/`, `Inbox/`, `Outbox/`, `Templates/`** —
> vault-native folders created by the shared-workspace change, containing
> `Profile.md`, `Goals.md`, `Preferences.md`, `Current Focus.md` and
> `Working Agreement.md`. **That content exists nowhere else.** It is not in
> `~/Claude`, not in this git repo, and not regenerable by any script.
>
> The port script cannot harm it — verified 2026-09-02, it is **write-only**: no
> `unlink`, no `rmtree`, no pruning of any kind. (Corollary: it never removes
> orphans either, so a renamed source note leaves a stale copy in the vault forever.)
>
> The risk is not the script, it is that **iCloud is the only copy** — on a machine
> where "Optimize Mac Storage" is on, eviction is silent, and FileVault is off.
> Until the mini's Time Machine is running, `Context/` is a single point of failure
> for Conor's profile, goals and working agreement.

- [ ] **Back up `Context/` somewhere that is not iCloud** before trusting the mini
      with it — a copy into `~/Claude` (where git and Time Machine both cover it), or
      onto the Time Machine drive directly. Decide which is authoritative and say so,
      or this becomes the two-copies-drift problem the 2026-08-03 audit warned about.

- [ ] Install Obsidian and sign in; iCloud will have synced the vault contents already
- [ ] Open the vault and confirm `Home.md` and `Claude Vault.base` render
- [ ] Re-run the port from the folder: `python3 obsidian-port.py`
  - Idempotent and folder-relative — safe to re-run any time to refresh
  - Override the destination with `OBSIDIAN_VAULT=/path/to/vault` if iCloud is not used on the mini
- [ ] Remember the direction — now with one exception: **`~/Claude` is authoritative
  for projects, and the vault is output.** Edits to *ported* notes inside Obsidian are
  overwritten on the next run. **But `Context/`, `Inbox/`, `Outbox/` and `Templates/`
  are vault-native and authoritative there** — nothing ports them, and nothing
  regenerates them

- [ ] **Re-add the Obsidian MCP server** — user-scope MCP config lives in
  `~/.claude.json` and does **not** travel with the folder:
  ```sh
  claude mcp add obsidian --scope user -- npx -y obsidian-mcp@2 serve \
    --vault "notes=$HOME/Library/Mobile Documents/com~apple~CloudDocs/Obsidian Vault/Obsidian Vault" \
    --recovery-days 7 --recovery-max-bytes 268435456
  ```
  - Needs Node >= 22 (step 7c already installs Node). No Obsidian plugin, no API
    key, and Obsidian does not need to be running — that is why this server was
    chosen over the REST-API ones, which would go dark whenever the app is closed
  - [ ] Verify: `claude mcp list` shows `obsidian - ✔ Connected`, and
    `npx -y obsidian-mcp@2 doctor --vault "notes=<path>"` returns `"ok": true`
  - [ ] ⚠️ **Learn the unbrick before you need it.** Upstream issue #71 is unfixed
    in 2.0.1: an ownerless write-lock permanently blocks startup and never
    self-heals, and Claude Code reports only a connect timeout with empty stderr.
    Fix: `rm -rf "<vault>/.obsidian-mcp/locks/write"`. Use `doctor` to see the
    real error — the MCP log will not tell you
  - [ ] Remember the port script now guards vault-side edits (`port_hash`), so a
    re-port **skips and names** edited notes instead of reverting them

## 7c. Claude Code plugins, skills & MCP servers — DO NOT TRAVEL WITH THE FOLDER

Same portability gap as the scheduled tasks in step 7. The agent environment lives in
`~/.claude/settings.json` (`enabledPlugins` + `extraKnownMarketplaces`),
`~/.claude/plugins/`, `~/.claude/skills/`, and `~/.claude.json` (MCP servers) — none of
it inside the `Claude` folder. Re-install on the mini or it is all silently absent.

- [ ] **Snapshot the live laptop state right before migrating** — the lists below are a
      dated point-in-time and *will* drift. Capture the truth to bring with you:
  ```sh
  claude plugin list > /tmp/claude-env.txt
  cat ~/.claude/plugins/known_marketplaces.json >> /tmp/claude-env.txt
  python3 -c "import json;print('\n'.join(json.load(open('$HOME/.claude/settings.json'))['enabledPlugins']))" >> /tmp/claude-env.txt
  claude mcp list >> /tmp/claude-env.txt
  ls ~/.claude/skills >> /tmp/claude-env.txt
  ```

- [ ] **Install Node first — the local-AI toolkit does not.** `tools/local-ai/` is deliberately stdlib-only Python, so nothing in step 7b puts `node` on the box. `ponytail`, `claude-mem`, `playwright`, and `chrome-devtools-mcp` all shell out to `node`.
  ```sh
  brew install node   # laptop landed 26.7.0 / npm 11.19.0 on 2026-08-26
  ```
- [ ] Confirm `node` resolves in a **non-interactive** shell, not just your terminal — hooks run non-interactively: `zsh -c 'command -v node'`

- [ ] **Add the 3 marketplaces** (`claude-plugins-official` is built in; add the other two):
  ```sh
  claude plugin marketplace add DietrichGebert/ponytail
  claude plugin marketplace add thedotmack/claude-mem
  ```
- [ ] **Install all 20 plugins** (user scope, headless — `/plugin` slash commands need an interactive panel). As of **2026-09-01**:
  ```sh
  for p in chrome-devtools-mcp claude-code-setup claude-md-management code-review \
           code-simplifier context7 feature-dev figma frontend-design github \
           mattpocock-skills playwright ralph-loop security-guidance skill-creator \
           superpowers typescript-lsp vercel; do
    claude plugin install "$p@claude-plugins-official" --scope user --yes
  done
  claude plugin install ponytail@ponytail --scope user --yes
  claude plugin install claude-mem@thedotmack --scope user --yes
  ```
- [ ] Verify: `claude plugin list` shows all 20 `✔ enabled`, and `~/.claude/settings.json` `enabledPlugins` has 20 keys.
- [ ] **ponytail default level:** installs at **`full`**, user scope — applies to *every* project here, not just coding ones. `/ponytail lite` or `/ponytail off` per session for the writing-heavy projects.

- [ ] **Copy the 7 loose skills** — hand-installed, in no repo:
  ```sh
  rsync -a ~/.claude/skills/ "<new mac>":~/.claude/skills/
  # banana defuddle json-canvas obsidian-bases obsidian-cli obsidian-markdown world-building
  ```
- [ ] **Authenticate the MCP servers that need it.** Run `claude mcp list`. As of 2026-09-01:
  - **`github`** — the plugin's `.mcp.json` sends `Authorization: Bearer
    ${GITHUB_PERSONAL_ACCESS_TOKEN}`. That env var is unset, so the header ships
    unexpanded and the server rejects it ("Authorization header is badly formatted").
    **Fix — set the token** (a fine-grained PAT scoped to just the startups' repos is
    better hygiene than reusing the broad `gh` token; `workflow` scope needed only for
    Actions):
    ```jsonc
    // ~/.claude/settings.json
    "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "github_pat_..." }
    ```
    A config token (not interactive OAuth) is required here because **scheduled/autonomous
    agents can't do a device-code flow.** `claude mcp list` should then show `github ✔`.
    Needed for real startup code work — repos, PRs, issues, CI.
  - `vercel`, `figma` — HTTP servers, `/mcp` → sign in interactively. Only if a startup uses them.
- [ ] Re-check for plugins/skills/MCP added after 2026-09-01 — re-run the snapshot above.

---

## 7d. CAD stack (bncad) — the part that builds actual geometry

*Added 2026-08-28. `Fusion CAD Agent/bncad/` turns a JSON part spec into a
validated, supplier-ready STEP using a local model. It was verified on a
relocated checkout with a from-scratch venv and under a cron-like environment,
so this section is the sequence that was actually tested.*

- [ ] **Install the prerequisites first.** None of the commands below exist on a
      fresh Mac. This is the step that stops people:
  ```sh
  xcode-select --install                                   # git, make, clang
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  brew install uv                                          # or: curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- [ ] **Build the CadQuery environment with `uv`.** A fresh Mac has no system
      `python3.12`, so the plain `venv` command fails with "command not found".
      `uv` fetches the interpreter as well:
  ```sh
  uv venv --python 3.12 "$HOME/Claude/Fusion CAD Agent/.venv-cq"
  uv pip install --python "$HOME/Claude/Fusion CAD Agent/.venv-cq/bin/python" cadquery
  ```
- [ ] **Delete any `.venv-cq` that travelled with the folder.** It is gitignored,
      but a filesystem *move* brings it anyway, and it points at the laptop's
      interpreter. Rebuild it here rather than trusting it.
      *(§7's `rsync` already excludes `.venv*` — this checkbox is the safety net for
      a Finder drag or Migration Assistant. Verified 2026-09-02: `.venv-cq/bin/python`
      is a symlink to `/Users/cmken/.local/share/uv/...`, so a copied venv is broken
      on arrival, not merely stale. The two 3.9 venvs that had the same defect were
      retired to `_to_delete/` the same day.)*
- [ ] **Check readiness:** `cd "$HOME/Claude/Bear Necessities/cad" && python3 preflight.py --for parts`
      — it names the exact fix for anything missing. Exit 0 means ready.
- [ ] **Run the self-tests:** `"$HOME/Claude/Fusion CAD Agent/bncad.sh" selftest`
      — no model, no Fusion, no network needed.
- [ ] **Build one real part** to prove the whole chain:
      `"$HOME/Claude/Fusion CAD Agent/bncad.sh" build C-01-anchor-plate`

### Fusion, if this mini is also to finish parts

Fusion is **optional** — every build above is headless through CadQuery. Fusion
adds the cross-kernel check and the parametric feature tree.

- [ ] Install Autodesk Fusion and **sign in once interactively**. It is not an
      offline application and it cannot be installed headless.
- [ ] Preferences → General → API → tick **Fusion MCP Server**.
- [ ] Verify: `"$HOME/Claude/Fusion CAD Agent/bncad.sh" doctor` shows a Fusion MCP
      line. **Do not pin the port** — it moves (27182 documented, 27180 observed
      twice); discovery handles it.
- [ ] Know the standing limits: Fusion demands re-authentication periodically, so
      a months-long unattended run will eventually stall on a modal dialog. Only
      the `native` and `visuals` stages depend on it; `parts` and `validate` do
      not.

### Scheduling it

Nothing schedules bncad yet — decide whether you want it to. If so, a launchd
job is the macOS-correct way (cron works but does not survive as cleanly):

```sh
# ~/Library/LaunchAgents/com.conor.bncad.plist -> ProgramArguments:
#   /bin/sh -lc '"$HOME/Claude/Fusion CAD Agent/bncad.sh" bench --model qwen/qwen2.5-coder-14b >> /tmp/bncad.log 2>&1'
launchctl load ~/Library/LaunchAgents/com.conor.bncad.plist
```

- [ ] **Always pass `--model` (or set `BN_MODEL`).** With neither, `bench` sweeps
      every model on every provider, which is an all-day job.
- [ ] Branch on the exit code: `0` success · `1` a part did not meet its spec ·
      `2` configuration · `3` busy, another build is running. `3` is not a
      failure.

### Choosing the model here — do not assume the laptop's answer

On the 16GB laptop the 14B looked 33× slower than the 7B. That was **memory
starvation, not the model**: with RAM free it runs at ~30s and builds parts the
7B cannot. On a 32GB+ mini the 14B is expected to be the right default.

- [ ] Settle it with numbers: `"$HOME/Claude/Fusion CAD Agent/bncad.sh" bench --model qwen/qwen2.5-coder-14b --repeat 2`
      and read the per-part **pass rate**. A single run cannot tell a robust
      result from a lucky one.

---

## 7e. Hermes Agent local host — SEE `Hermes-Local-Agent.md`

*Added 2026-09-01. The Hermes Agent desktop app pointed at the local LM Studio
server, so autonomous Hermes tasks run on a local model instead of paid API
usage. Verified on the 16 GB laptop; the runbook is written for the 64 GB mini.*

`Hermes-Local-Agent.md` is the authoritative doc — hardware rationale, the
ordered runbook, and the failure table. Summary of the steps:

- [ ] LM Studio ≥ 0.3.6, server on `:1234` (§7b already does this). Install
      Hermes **only** from `hermes-agent.nousresearch.com` (lookalike domains
      exist). Bionic is a client, not a server — ignore it.
- [ ] Model for the 64 GB tier: `qwen/qwen3-coder-30b` MLX 4-bit (already the
      `coding` role in `model-profiles.json`). Only use tool-use-badged models.
- [ ] Load at **64000** context, `--parallel 1`. Hermes refuses below 64k and a
      context change needs a model **reload**. Set the per-model default context
      to 64000 in LM Studio so it survives restarts.
- [ ] If MLX crashes under a real prompt, fall back to the **GGUF Q4_K_M** build
      of the same model — the sanctioned benchmark-backed exception. Record it.
- [ ] Wire it + prove it in one command: **`tools/local-ai/setup-hermes.sh --load`**.
      Resolves `qwen/qwen3-coder-30b` from the 64 GB profile, backs up the config,
      writes `provider`/`base_url`/`model.default`/`context_length: 64000` via the
      CLI (the desktop provider UI has mapping bugs — issues #38975 / #47961), then
      runs `verify-hermes.sh` — which asserts a model is loaded at ≥ 64k, that it
      emits a well-formed `tool_call`, and that `hermes -z` executes a real
      terminal tool and uses the result. A `/v1/models` 200 is not proof.
- [ ] Restart the Hermes desktop app fully so its backend picks up the config.

---

## 7f. Codex CLI + the website's publishing path — DOES NOT TRAVEL

*Added 2026-09-02 by the migration audit. This folder has a root `AGENTS.md` and the
Bear Necessities site publishes through ChatGPT/OpenAI Sites, so Codex is a real
dependency with no setup step until now.*

- [ ] **Install the Codex CLI and sign in.** Credentials live in `~/.codex`, outside
      this folder — same portability gap as the scheduled tasks and `~/.claude*`.
- [ ] **Prove the site can still be published from the mini.** The live site is
      `https://bear-necessities-overland.cmkennedy218.chatgpt.site`; its project id is
      committed at `Bear Necessities/website/.openai/hosting.json`. Run a build and a
      no-op redeploy — finding out the credential is missing during a real content
      change is the bad version of this.
  ```sh
  cd "$HOME/Claude/Bear Necessities/website"
  npm ci && npm run build      # needs Node >= 22.13 (package.json engines)
  ```
- [ ] ⚠️ **The website is its own git repo with NO REMOTE.** Until it is pushed
      somewhere, the laptop is the only copy in the world. Push it to a private repo
      before retiring the laptop copy (the `github` MCP in §7c is being fixed anyway),
      or at minimum keep the bundle at `Bear Necessities/website-repo-2026-09-02.bundle`
      on the Time Machine drive. Restore from a bundle with:
      `git clone website-repo-2026-09-02.bundle website`
- [ ] Note that only **3 of 15** projects have an `AGENTS.md` (root, Bear Necessities,
      Career, Mac Mini Setup). Codex reads `CLAUDE.md` for the rest — the root
      `AGENTS.md` now says so explicitly rather than claiming a file that isn't there.

---

## 7g. Ollama — OPTIONAL, decide before installing

*The toolkit carries `tools/ollama/` (a LaunchAgent + `ollama-doctor.sh`) because bncad
supports Ollama as a second provider and there is benchmark evidence under
`Fusion CAD Agent/exports/bncad/bench-ollama/`. It had no install step and the plist
hardcoded `/Users/cmken` paths; both fixed 2026-09-02.*

**LM Studio is the primary runtime (§7b) and Ollama is not required.** The one
measured data point is against it: `qwen3:8b` through Ollama passed 1/5 bncad parts at
~1200s, versus 9/12 at 28s for the 7B coder on LM Studio — model class, not the runner,
but nothing here needs Ollama today.

If you do want it:

```sh
brew install ollama
"$HOME/Claude/Mac Mini Setup/tools/ollama/install-ollama-autostart.sh" --dry-run   # preview
"$HOME/Claude/Mac Mini Setup/tools/ollama/install-ollama-autostart.sh"
"$HOME/Claude/Mac Mini Setup/tools/ollama/ollama-doctor.sh"
```

- [ ] Decided whether Ollama is on this machine at all
- [ ] If yes: installed, autostart verified, `ollama-doctor.sh` green, bound to loopback
- [ ] If no: nothing to do — LM Studio covers every documented workflow

---

## 7h. Home cloud storage — SEE `Home-Cloud-Storage.md`

Make Conor's project files reachable from the laptop, iPad and iPhone. Full
decision doc, options analysis and the step-by-step runbook are in
`Home-Cloud-Storage.md`; the short version:

**Order matters — backup layer first, cloud second.** Sync propagates deletions;
it is not a backup.

- [ ] **Time Machine running and verified** (test-restore one file) — the §1
      drive connected, first full backup complete. Do not enable any file
      sharing until this is done.
- [ ] Off-site copy decided: `~/Claude` → the GitHub repo (already exists);
      non-repo files → **iCloud Drive** *or* **Backblaze Personal** (~$99/yr).
- [ ] 2 TB external SSD formatted (APFS), hosting `/Volumes/Vault/Projects`,
      `/Volumes/Vault/Models` (the LM Studio library — same drive, see §7b),
      etc. Project files moved over via the §7 rsync path, not Finder drag.
- [ ] **SMB File Sharing** on (System Settings → Sharing → File Sharing → SMB),
      strong account password. Mounts in the iOS/iPadOS **Files app** via
      `smb://<mini-tailscale-ip>`.
- [ ] Verified from the **iPhone on cellular, wifi off** — open a file, edit,
      save, confirm the change on the laptop.
- [ ] **Taildrive** tried (`tailscale drive share …`) — appears as "Tailscale"
      in Files with no address typed. Prefer it over SMB *only if* large-file
      transfers are fast and reliable (it's alpha).
- [ ] **Syncthing** installed (mini + laptop via `brew`, iOS via Möbius Sync) on
      **only** the 1–3 folders that must be offline on the iPad. File Versioning
      → Staggered on each. Not the whole Vault.
- [ ] Reboot the mini; confirm shares + Syncthing return and the iPad
      reconnects.
- [ ] **Restore a deleted test file from Time Machine** — prove the backup
      layer, not just the sync layer.
- [ ] Record in the Decisions log which access method won (SMB vs Taildrive) and
      which folders are on Syncthing.

**Do NOT:** port-forward anything; run Nextcloud unless he wants the hobby; RAID
a documents archive; buy a NAS.

---

## 8. Safety rails for unattended operation

- [ ] Confirm `git status` is clean before leaving it alone, so any autonomous change is visible as a diff
- [ ] Consider a daily auto-commit so overnight edits are recoverable:
  ```sh
  cd ~/Claude && git add -A && git commit -m "auto: $(date +%F)" || true
  ```
- [ ] Set up Time Machine to an external drive — git protects the files, Time Machine protects the machine
- [ ] Decide which tasks may act autonomously vs. which must ask first. Anything touching money, sending email, or posting publicly should ask
- [ ] Note: this folder contains portfolio holdings, severance terms, and your home address. Treat physical and network access to the mini accordingly

---

## 9. Verify before walking away

- [ ] ⚠️ **Disconnect the monitor and confirm Fusion still drives the window server.**
      This is the one untested load-bearing assumption in the whole project: per
      `../Fusion CAD Agent/Hardware-Requirements.md`, a fully headless mini may not
      drive the window server, and *the render and native-CAD stages cannot run
      unattended at all* if it doesn't. Fit the HDMI dummy plug (§1), pull the real
      monitor, then over Screen Sharing run
      `"$HOME/Claude/Fusion CAD Agent/bncad.sh" doctor` and a `./build.sh native`
      or `visuals` stage. If it fails, the headless CadQuery path (`parts`,
      `validate`) still works — only the Fusion-dependent stages are lost
- [ ] Close the lid / disconnect the monitor and confirm it stays reachable
- [ ] Trigger a task from your phone and confirm it completes
- [ ] Reboot it remotely and confirm it comes back logged in on its own
- [ ] Let a real scheduled task fire on its own schedule and confirm the output
- [ ] Check `pmset -g log | grep -i sleep` after a day to confirm nothing put it to sleep

---

## Decisions log

- *Resolved 2026-08-03 — **Authority:** the mini is the single authoritative copy; no two-way sync.*
- *Resolved 2026-08-07 — **FileVault: OFF.*** Uptime/auto-login after a power blip wins over disk encryption. Section 4's checkbox reflects this: turn FileVault off, enable automatic login.
- *Resolved 2026-08-07 — **Autonomy boundary:** the default stands as final.* Money, email, and public posting always ask first; everything else may proceed autonomously. No additional categories added.
- *Confirmed 2026-08-07 — **Scheduled-task re-registration is a real, not theoretical, step.*** Checked live registrations on 2026-08-07: none of the 5 tasks listed in step 7 were actually registered in app config, only defined in-folder. Re-registered `mac-mini-claude-project-reminder` for Oct 1, 2026. The other four still need the same fix (outside this project's scope — flagged, not actioned).
