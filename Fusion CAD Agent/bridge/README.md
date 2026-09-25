# bridge/

The piece that closes the loop: gets a generated script **into** Fusion and gets the result **back out**.

Nothing is built here yet — this is the design.

## The problem
`Mac Mini Setup/tools/lm_studio_bridge.py` already handles *prompt → local model → file*. What's missing is *file → Fusion → result → back to the model*. Fusion's Python API only runs inside Fusion's own GUI process, so an outside process cannot simply invoke it.

## Option A — manual (zero build)
Drop the script into Fusion's Scripts folder, click Run, read the message box.

Good for prototyping. **Fails the actual goal** — an always-on mini that nobody is sitting in front of.

## Option B — watcher add-in (the real answer)
A Fusion **add-in** (not a script) that loads at Fusion startup and stays resident, polling a queue folder:

```
bridge/queue/    <- agent drops <job>.py here
bridge/running/  <- add-in moves it here while executing
bridge/done/     <- finished scripts
bridge/logs/     <- <job>.log: stdout, traceback, exported file paths
```

The agent writes a job, waits for the matching log, and reads success or traceback. That traceback is what makes iteration possible — a model that can see its own error fixes it far more often than one guessing blind.

### To resolve when building
- **Polling interval** — Fusion add-ins run on the UI thread; a tight poll will make the app sluggish. Use a timer/custom event rather than a blocking loop.
- **No `messageBox`, ever.** It blocks until clicked and would hang the queue permanently.
- **Crash recovery** — if Fusion dies mid-job, `running/` must be drained on next startup or that job is stuck forever.
- **Document state** — build into a fresh document per job, not whatever happens to be open.
- **Timeout** — a runaway script needs a ceiling.

## Recommendation
Prove the geometry works with Option A on the laptop first. Only build Option B once scripts are landing correctly — otherwise you're debugging two unproven systems at once.
