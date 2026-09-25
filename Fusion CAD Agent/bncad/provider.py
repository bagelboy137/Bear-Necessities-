#!/usr/bin/env python3
"""Local model providers: LM Studio and Ollama, behind one interface.

Both speak the OpenAI chat-completions shape, so this is one code path with two
base URLs. Stdlib only - it has to run under the system 3.9 as happily as under
the CadQuery venv's 3.12.

Two things here are not incidental:

* **Reasoning models leak their scratchpad.** qwen3:8b through Ollama returns a
  separate `reasoning` field AND sometimes inlines `<think>` blocks in content.
  Left in, the code extractor picks up whatever fenced block the model wrote
  while thinking out loud, which is usually the wrong one.
* **The first call after an idle period is not slow, it is silent.** LM Studio
  JIT-loads on first request; a 14B takes ~60-90s to page in before a single
  token appears. A 60s timeout reads as "the model is broken" when nothing is
  wrong, so the default timeout is deliberately large.
"""

import json
import os
import re
import time
import urllib.error
import urllib.request

LM_STUDIO = "http://127.0.0.1:1234/v1"
OLLAMA = "http://127.0.0.1:11434/v1"

# <think>...</think> and friends. Non-greedy, DOTALL, and tolerant of an
# unclosed opener - a truncated response leaves <think> with no partner and the
# whole tail is scratchpad, not answer.
_THINK = re.compile(r"<(think|thinking|reasoning)>.*?</\1>", re.S | re.I)
_THINK_OPEN = re.compile(r"<(think|thinking|reasoning)>.*\Z", re.S | re.I)


def strip_reasoning(text):
    """Remove reasoning scratchpad from model output."""
    text = _THINK.sub("", text)
    text = _THINK_OPEN.sub("", text)
    return text.strip()


class ProviderError(RuntimeError):
    pass


class Provider:
    """One local OpenAI-compatible server."""

    def __init__(self, name, base_url, timeout=1800):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def __repr__(self):
        return "Provider(%s, %s)" % (self.name, self.base_url)

    def _get(self, path, timeout=10):
        with urllib.request.urlopen(self.base_url + path, timeout=timeout) as r:
            return json.load(r)

    def alive(self, timeout=5):
        try:
            self._get("/models", timeout=timeout)
            return True
        except Exception:
            return False

    def models(self):
        try:
            return sorted(m["id"] for m in self._get("/models").get("data", []))
        except Exception:
            return []

    def chat(self, system, user, model, temperature=0.15, max_tokens=8000,
             timeout=None, retries=2):
        """One completion. Returns (text, elapsed_seconds, usage_dict).

        `text` has reasoning stripped. Raises ProviderError after `retries`
        failed attempts so the caller sees a real error rather than an empty
        string that looks like a bad answer.
        """
        body = json.dumps({
            "model": model,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }).encode()
        last = None
        for attempt in range(retries + 1):
            t0 = time.time()
            try:
                req = urllib.request.Request(
                    self.base_url + "/chat/completions", data=body,
                    headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(
                        req, timeout=timeout or self.timeout) as r:
                    payload = json.load(r)
            except urllib.error.HTTPError as e:
                detail = e.read().decode("utf-8", "replace")[:500]
                last = "HTTP %s from %s: %s" % (e.code, self.name, detail)
            except Exception as e:
                last = "%s: %s" % (type(e).__name__, e)
            else:
                first = payload["choices"][0]
                choice = first["message"]
                text = strip_reasoning(choice.get("content") or "")
                # A completion cut off at the token limit looks exactly like a
                # model that wrote broken code: the fence never closes and the
                # loop reports a syntax error against a reply that was fine as
                # far as it got. Name the real cause instead.
                if first.get("finish_reason") == "length":
                    raise ProviderError(
                        "%s/%s hit the token limit mid-answer (finish_reason="
                        "'length', %s completion tokens). The reply is truncated, "
                        "not wrong. Raise max_tokens, or raise the server's "
                        "context window - Ollama defaults to 4096, which this "
                        "system prompt alone nearly fills."
                        % (self.name, model,
                           payload.get("usage", {}).get("completion_tokens", "?")))
                # Ollama puts the scratchpad in its own field. If content came
                # back empty but reasoning did not, the model answered inside
                # its thinking and the reply is genuinely empty - say so rather
                # than silently returning "".
                if not text and choice.get("reasoning"):
                    raise ProviderError(
                        "%s/%s answered entirely inside its reasoning block and "
                        "returned no content. Use a non-reasoning model for code "
                        "generation, or raise max_tokens." % (self.name, model))
                return text, time.time() - t0, payload.get("usage", {})
            if attempt < retries:
                time.sleep(2 + 3 * attempt)
        raise ProviderError("%s/%s failed after %d attempts: %s"
                            % (self.name, model, retries + 1, last))


def _env_url(var, default):
    """Resolve a service URL from the environment.

    BN_LM_STUDIO_URL is accepted as well as BN_LMSTUDIO_URL: runtime.json and
    Bear Necessities' preflight.py have always spelled it with the extra
    underscore, so a user who exported the documented name and got a silently
    different endpoint here would have had a genuinely baffling afternoon.
    """
    aliases = {"BN_LMSTUDIO_URL": ("BN_LMSTUDIO_URL", "BN_LM_STUDIO_URL")}
    for name in aliases.get(var, (var,)):
        if os.environ.get(name):
            return os.environ[name]
    return default


def discover(timeout=3):
    """Every local provider currently answering. Order is preference order."""
    found = []
    for name, url, var in (("lmstudio", LM_STUDIO, "BN_LMSTUDIO_URL"),
                           ("ollama", OLLAMA, "BN_OLLAMA_URL")):
        p = Provider(name, _env_url(var, url))
        if p.alive(timeout=timeout):
            found.append(p)
    return found


def resolve(spec_str=None, timeout=3):
    """Turn "provider/model", "model", or None into (Provider, model_id).

    The bare-model form is what a human types. It is resolved by asking each
    live provider what it actually has, which means a typo fails immediately
    with the real roster instead of 90 seconds later with a 404.
    """
    providers = discover(timeout=timeout)
    if not providers:
        raise ProviderError(
            "No local model server is answering. Start LM Studio (port 1234) or "
            "Ollama (port 11434), or set BN_LMSTUDIO_URL / BN_OLLAMA_URL.")

    if spec_str is None:
        spec_str = os.environ.get("BN_MODEL", "")

    if "/" in spec_str:
        head, _, tail = spec_str.partition("/")
        for p in providers:
            if p.name == head:
                # Verify it against the roster too. Returning `tail` unchecked
                # meant "ollama/qwen3-8b" (hyphen for colon) sailed through and
                # failed much later as a 404 - the one form the docs use as the
                # example of a typo failing immediately.
                if tail in p.models():
                    return p, tail
                raise ProviderError(
                    "%s has no model %r. It has: %s"
                    % (p.name, tail, ", ".join(p.models()) or "nothing loaded"))
        # Not a provider prefix - "qwen/qwen2.5-coder-14b" is itself a model id.

    if spec_str:
        for p in providers:
            if spec_str in p.models():
                return p, spec_str
        roster = "; ".join("%s: %s" % (p.name, ", ".join(p.models()) or "none")
                           for p in providers)
        raise ProviderError("No live provider has model %r. Available - %s"
                            % (spec_str, roster))

    for p in providers:
        got = p.models()
        if got:
            return p, got[0]
    raise ProviderError("Providers are up but none has a model loaded.")


def demo():
    assert strip_reasoning("<think>a</think>B") == "B"
    assert strip_reasoning("A<think>x</think>B") == "AB"
    assert strip_reasoning("keep<think>drop") == "keep", "unclosed opener"
    assert strip_reasoning("<THINKING>x</THINKING>ok") == "ok", "case insensitive"
    assert strip_reasoning("plain") == "plain"
    # A code fence written inside the scratchpad must not survive.
    assert "wrong" not in strip_reasoning(
        "<think>```python\nwrong\n```</think>```python\nright\n```")
    p = Provider("nope", "http://127.0.0.1:9/v1")
    assert not p.alive(timeout=1)
    assert p.models() == []
    print("provider demo ok")


if __name__ == "__main__":
    demo()
