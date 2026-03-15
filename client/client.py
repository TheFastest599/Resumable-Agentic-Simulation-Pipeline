"""
Python client for the Resumable Agentic Simulation Pipeline API.

Programmatic usage:
    from client.client import SimulationClient
    c = SimulationClient("http://localhost:8000")
    job = c.submit_job("monte_carlo_pi", {"iterations": 1_000_000})
    result = c.wait_for_result(job["id"])

CLI (arg-based):
    python -m client.client submit monte_carlo_pi --iterations 1000000 --wait
    python -m client.client status <job_id>
    python -m client.client list [--status COMPLETED] [--limit 20]
    python -m client.client tasks
    python -m client.client chats [--limit 20]
    python -m client.client chat "Run 3 pi simulations" [--conversation-id <id>]

Interactive REPL (no args):
    python -m client.client
    rasp> /tasks
    rasp> /submit monte_carlo_pi iterations=500000
    rasp> /status <job_id>
    rasp> /list --status COMPLETED
    rasp> /chats
    rasp> /chat                  ← new conversation
    rasp> /chat <conv_id>        ← resume existing conversation
    rasp> /chat-rename <id> My best run
    rasp> /chat-delete <id>
    rasp> /help
    rasp> /quit
"""
import json
import sys
import time
from typing import Any, Optional

import httpx
from colorama import Fore, Style, init as _colorama_init

_colorama_init(autoreset=True)

# ── colour helpers ─────────────────────────────────────────────────────────────
def _c(text: str, color: str) -> str:
    return f"{color}{text}{Style.RESET_ALL}"

def _info(text: str)    -> str: return _c(text, Fore.CYAN)
def _ok(text: str)      -> str: return _c(text, Fore.GREEN)
def _warn(text: str)    -> str: return _c(text, Fore.YELLOW)
def _err(text: str)     -> str: return _c(text, Fore.RED)
def _dim(text: str)     -> str: return _c(text, Style.DIM)
def _bold(text: str)    -> str: return _c(text, Style.BRIGHT)
def _user_msg(text: str)  -> str: return _c(text, Fore.YELLOW)
def _agent_msg(text: str) -> str: return _c(text, Fore.GREEN)


class SimulationClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    # ── Jobs ──────────────────────────────────────────────────────────────────

    def submit_job(
        self,
        task_name: str,
        payload: dict[str, Any],
        priority: int = 5,
        max_retries: int = 3,
        depends_on: list[str] | None = None,
    ) -> dict:
        body = {
            "task_name": task_name,
            "payload": payload,
            "priority": priority,
            "max_retries": max_retries,
            "depends_on": depends_on or [],
        }
        r = httpx.post(self._url("/jobs"), json=body, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_job(self, job_id: str) -> dict:
        r = httpx.get(self._url(f"/jobs/{job_id}"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_jobs(self, status: Optional[str] = None, limit: int = 50) -> dict:
        params: dict[str, Any] = {"limit": limit}
        if status:
            params["status"] = status
        r = httpx.get(self._url("/jobs"), params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def cancel_job(self, job_id: str) -> dict:
        r = httpx.post(self._url(f"/jobs/{job_id}/cancel"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def resume_job(self, job_id: str) -> dict:
        r = httpx.post(self._url(f"/jobs/{job_id}/resume"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def wait_for_result(
        self,
        job_id: str,
        poll_interval: float = 2.0,
        timeout: float = 300.0,
    ) -> dict:
        """Poll until job reaches a terminal state. Returns final job dict."""
        start = time.time()
        terminal = {"COMPLETED", "FAILED", "CANCELLED"}
        while True:
            job = self.get_job(job_id)
            status = job.get("status")
            progress = job.get("progress", 0.0)
            print(f"  [{status}] progress={progress:.0%}", end="\r", flush=True)
            if status in terminal:
                print()
                return job
            if time.time() - start > timeout:
                raise TimeoutError(f"Job {job_id} did not complete within {timeout}s")
            time.sleep(poll_interval)

    # ── Tasks ─────────────────────────────────────────────────────────────────

    def list_tasks(self) -> dict:
        r = httpx.get(self._url("/tasks"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # ── Conversations ─────────────────────────────────────────────────────────

    def chat(self, message: str, conversation_id: Optional[str] = None) -> dict:
        body: dict[str, Any] = {"message": message}
        if conversation_id:
            body["conversation_id"] = conversation_id
        r = httpx.post(self._url("/agent/chat"), json=body, timeout=120.0)
        r.raise_for_status()
        return r.json()

    def list_conversations(self, limit: int = 20) -> list:
        r = httpx.get(self._url("/agent/conversations"), params={"limit": limit}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def get_conversation(self, conv_id: str) -> dict:
        r = httpx.get(self._url(f"/agent/conversations/{conv_id}"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def delete_conversation(self, conv_id: str) -> dict:
        r = httpx.delete(self._url(f"/agent/conversations/{conv_id}"), timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def rename_conversation(self, conv_id: str, name: str) -> dict:
        r = httpx.patch(
            self._url(f"/agent/conversations/{conv_id}"),
            json={"name": name},
            timeout=self.timeout,
        )
        r.raise_for_status()
        return r.json()


# ─── REPL helpers ────────────────────────────────────────────────────────────

def _parse_kv_payload(tokens: list[str]) -> dict[str, Any]:
    """Parse ['key=value', ...] into a dict, auto-casting to int/float where possible."""
    payload: dict[str, Any] = {}
    for tok in tokens:
        if "=" not in tok:
            print(f"  Skipping malformed token (expected key=value): {tok!r}")
            continue
        k, v = tok.split("=", 1)
        try:
            payload[k] = int(v)
        except ValueError:
            try:
                payload[k] = float(v)
            except ValueError:
                payload[k] = v
    return payload


_HELP = """
Commands:
  /tasks                            List all available simulation tasks
  /submit <task> [key=val ...]      Submit a job  (e.g. /submit monte_carlo_pi iterations=500000)
  /status <job_id>                  Get job status and result
  /list [--status S] [--limit N]    List jobs
  /cancel <job_id>                  Cancel a queued/running job
  /resume <job_id>                  Resume a failed/cancelled job

  /chats [--limit N]                List recent conversations (name + id)
  /chat                             Start a new conversation
  /chat <conv_id>                   Resume an existing conversation (loads history)
  /chat-rename <conv_id> <name>     Rename a conversation
  /chat-delete <conv_id>            Delete a conversation

  /help                             Show this help
  /quit  /exit                      Exit the REPL
"""


def _print_history(messages: list[dict]) -> None:
    if not messages:
        return
    print()
    for m in messages:
        if m["role"] == "user":
            print(f"  {_bold('You')}   : {_user_msg(m['text'])}")
        else:
            print(f"  {_bold('Agent')} : {_agent_msg(m['text'])}")
    print()


def _repl_chat_loop(
    client: SimulationClient,
    conversation_id: Optional[str] = None,
) -> None:
    """Nested REPL for multi-turn agent chat. /exit returns to main REPL."""
    local_history: list[dict] = []
    conv_name: Optional[str] = None

    if conversation_id:
        try:
            data = client.get_conversation(conversation_id)
            conv_name = data.get("name")
            for m in data.get("messages", []):
                local_history.append({"role": m["role"], "text": m["text"]})
            name_str = f" '{_bold(conv_name)}'" if conv_name else ""
            print(f"\n  {_info('Resuming conversation')}{name_str}  {_dim('[' + conversation_id + ']')}")
            _print_history(local_history)
        except Exception as e:
            print(f"  {_warn('Warning:')} could not load history — {e}\n")
    else:
        print(f"\n  {_info('New conversation')}  {_dim('(type /exit to return)')}\n")

    # Show chat name once at the top, then use plain "> " prompt
    if conv_name:
        print(f"  {_dim('Chat:')} {_bold(conv_name)}\n")

    while True:
        try:
            msg = input(f"  {_dim('>')} ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not msg:
            continue
        if msg in ("/exit", "/quit"):
            break
        if msg.startswith("/chat-rename") and conversation_id:
            new_name = msg[len("/chat-rename"):].strip()
            if new_name:
                try:
                    client.rename_conversation(conversation_id, new_name)
                    conv_name = new_name
                    print(f"  {_ok('Renamed to')} '{new_name}'")
                except Exception as e:
                    print(f"  {_err('Error:')} {e}")
            continue

        local_history.append({"role": "user", "text": msg})
        print(f"  {_bold('You')}   : {_user_msg(msg)}")

        try:
            resp = client.chat(msg, conversation_id=conversation_id)
            conversation_id = resp["conversation_id"]

            if conv_name is None:
                try:
                    data = client.get_conversation(conversation_id)
                    conv_name = data.get("name")
                    if conv_name:
                        print(f"\n  {_dim('Chat:')} {_bold(conv_name)}")
                except Exception:
                    pass

            reply = resp["reply"]
            local_history.append({"role": "assistant", "text": reply})
            print(f"  {_bold('Agent')} : {_agent_msg(reply)}\n")
        except httpx.HTTPStatusError as e:
            local_history.pop()
            print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
        except Exception as e:
            local_history.pop()
            print(f"  {_err('Error:')} {e}")


_STATUS_COLOR = {
    "COMPLETED": Fore.GREEN,
    "RUNNING":   Fore.CYAN,
    "QUEUED":    Fore.YELLOW,
    "FAILED":    Fore.RED,
    "CANCELLED": Fore.MAGENTA,
}

def _colored_status(status: str) -> str:
    return f"{_STATUS_COLOR.get(status, '')}{status}{Style.RESET_ALL}"


def _run_repl(client: SimulationClient) -> None:
    print(_bold("\n  Resumable Agentic Simulation Pipeline") + _dim("  —  interactive mode"))
    print(_dim("  Type /help for commands or /quit to exit.\n"))
    while True:
        try:
            line = input(_bold(Fore.CYAN + "rasp" + Style.RESET_ALL + "> ")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue

        parts = line.split()
        cmd = parts[0].lower()
        args = parts[1:]

        if cmd in ("/quit", "/exit"):
            break

        elif cmd == "/help":
            print(_dim(_HELP))

        elif cmd == "/tasks":
            try:
                data = client.list_tasks()
                hdr = "%-4s %-28s %s" % ("#", "Task Name", "Description")
                print(f"\n  {_bold(hdr)}")
                print(_dim("  " + "─" * 70))
                for i, t in enumerate(data["tasks"], 1):
                    print(f"  {_dim('%-4d' % i)}{_info('%-28s' % t['name'])} {t['description']}")
                print()
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/submit":
            if not args:
                print(f"  {_warn('Usage:')} /submit <task_name> [key=value ...]")
                continue
            task_name = args[0]
            payload = _parse_kv_payload(args[1:])
            try:
                job = client.submit_job(task_name, payload)
                print(f"  {_ok('Submitted:')} {_dim(job['id'])}  [{_colored_status(job['status'])}]")
            except httpx.HTTPStatusError as e:
                print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/status":
            if not args:
                print(f"  {_warn('Usage:')} /status <job_id>")
                continue
            try:
                job = client.get_job(args[0])
                print(f"  Status   : {_colored_status(job['status'])}")
                pct = "%.0f%%" % (job['progress'] * 100)
                print(f"  Progress : {_info(pct)}")
                if job.get("result"):
                    print(f"  Result   :\n{_ok(json.dumps(job['result'], indent=4))}")
                if job.get("error"):
                    print(f"  Error    : {_err(job['error'])}")
            except httpx.HTTPStatusError as e:
                print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/list":
            status_filter = None
            limit = 20
            i = 0
            while i < len(args):
                if args[i] == "--status" and i + 1 < len(args):
                    status_filter = args[i + 1]
                    i += 2
                elif args[i] == "--limit" and i + 1 < len(args):
                    limit = int(args[i + 1])
                    i += 2
                else:
                    i += 1
            try:
                data = client.list_jobs(status=status_filter, limit=limit)
                jobs = data["jobs"]
                if not jobs:
                    print(f"  {_dim('No jobs found.')}")
                else:
                    hdr = "%-38s %-24s %-12s %s" % ("Job ID", "Task", "Status", "Progress")
                    print(f"\n  {_bold(hdr)}")
                    print(_dim("  " + "─" * 84))
                    for j in jobs:
                        print(f"  {_dim(j['id'])}  {'%-24s' % j['task_name']} {_colored_status(j['status'])}  {_info('%.0f%%' % (j['progress']*100))}")
                    print()
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/cancel":
            if not args:
                print(f"  {_warn('Usage:')} /cancel <job_id>")
                continue
            try:
                job = client.cancel_job(args[0])
                print(f"  {_warn('Cancelled:')} {_dim(job['id'])}  [{_colored_status(job['status'])}]")
            except httpx.HTTPStatusError as e:
                print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/resume":
            if not args:
                print(f"  {_warn('Usage:')} /resume <job_id>")
                continue
            try:
                job = client.resume_job(args[0])
                print(f"  {_ok('Resumed:')} {_dim(job['id'])}  [{_colored_status(job['status'])}]")
            except httpx.HTTPStatusError as e:
                print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/chats":
            limit = 20
            if "--limit" in args:
                idx = args.index("--limit")
                if idx + 1 < len(args):
                    limit = int(args[idx + 1])
            try:
                convs = client.list_conversations(limit=limit)
                if not convs:
                    print(f"  {_dim('No conversations yet.')}")
                else:
                    hdr = "%-4s %-22s %-38s %s" % ("#", "Name", "ID", "Created")
                    print(f"\n  {_bold(hdr)}")
                    print(_dim("  " + "─" * 84))
                    for i, c in enumerate(convs, 1):
                        name = (c.get("name") or "(unnamed)")[:20]
                        created = c["created_at"][:16].replace("T", " ")
                        print(f"  {_dim('%-4d' % i)}{_info('%-22s' % name)} {_dim(c['id'])}  {created}")
                    print()
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/chat":
            conv_id = args[0] if args else None
            _repl_chat_loop(client, conversation_id=conv_id)

        elif cmd == "/chat-rename":
            if len(args) < 2:
                print(f"  {_warn('Usage:')} /chat-rename <conv_id> <new name>")
                continue
            conv_id = args[0]
            new_name = " ".join(args[1:])
            try:
                conv = client.rename_conversation(conv_id, new_name)
                print(f"  {_ok('Renamed to')} '{conv['name']}'")
            except httpx.HTTPStatusError as e:
                print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        elif cmd == "/chat-delete":
            if not args:
                print(f"  {_warn('Usage:')} /chat-delete <conv_id>")
                continue
            try:
                client.delete_conversation(args[0])
                print(f"  {_ok('Deleted conversation')} {_dim(args[0])}")
            except httpx.HTTPStatusError as e:
                print(f"  {_err('Error:')} {e.response.status_code} — {e.response.text}")
            except Exception as e:
                print(f"  {_err('Error:')} {e}")

        else:
            print(f"  {_err('Unknown command:')} {cmd!r}  {_dim('(type /help for commands)')}")


# ─── arg-based CLI ────────────────────────────────────────────────────────────

def main() -> None:
    import argparse

    # No args → interactive REPL
    if len(sys.argv) == 1:
        _run_repl(SimulationClient())
        return

    parser = argparse.ArgumentParser(description="Simulation Pipeline CLI")
    parser.add_argument("--url", default="http://localhost:8000")
    sub = parser.add_subparsers(dest="command")

    # submit
    p_sub = sub.add_parser("submit", help="Submit a simulation job")
    p_sub.add_argument("task", help="Task name (see: python -m client.client tasks)")
    p_sub.add_argument("--iterations", type=int, default=1_000_000)
    p_sub.add_argument("--steps", type=int, default=1_000)
    p_sub.add_argument("--size", type=int, default=512)
    p_sub.add_argument("--priority", type=int, default=5)
    p_sub.add_argument("--wait", action="store_true", help="Wait for result")

    # status
    p_status = sub.add_parser("status", help="Get job status")
    p_status.add_argument("job_id")

    # list
    p_list = sub.add_parser("list", help="List jobs")
    p_list.add_argument("--status", default=None)
    p_list.add_argument("--limit", type=int, default=20)

    # cancel
    p_cancel = sub.add_parser("cancel", help="Cancel a job")
    p_cancel.add_argument("job_id")

    # resume
    p_resume = sub.add_parser("resume", help="Resume a failed/cancelled job")
    p_resume.add_argument("job_id")

    # tasks
    sub.add_parser("tasks", help="List available simulation tasks")

    # chats
    p_chats = sub.add_parser("chats", help="List recent conversations")
    p_chats.add_argument("--limit", type=int, default=20)

    # chat (single-shot)
    p_chat = sub.add_parser("chat", help="Send a single message to the agent")
    p_chat.add_argument("message")
    p_chat.add_argument("--conversation-id", default=None)

    args = parser.parse_args()
    client = SimulationClient(args.url)

    if args.command == "submit":
        payload: dict[str, Any] = {}
        if args.iterations != 1_000_000:
            payload["iterations"] = args.iterations
        if args.steps != 1_000:
            payload["steps"] = args.steps
        if args.size != 512:
            payload["size"] = args.size
        job = client.submit_job(args.task, payload, priority=args.priority)
        print(f"Submitted: {job['id']}  [{job['status']}]")
        if args.wait:
            result = client.wait_for_result(job["id"])
            print("Result:", result.get("result"))

    elif args.command == "status":
        job = client.get_job(args.job_id)
        print(f"Status:   {job['status']}  Progress: {job['progress']:.0%}")
        if job.get("result"):
            print("Result:", json.dumps(job["result"], indent=2))
        if job.get("error"):
            print("Error:", job["error"])

    elif args.command == "list":
        data = client.list_jobs(status=args.status, limit=args.limit)
        for j in data["jobs"]:
            print(f"  {j['id']}  {j['task_name']:<28}  {j['status']:<12}  {j['progress']:.0%}")

    elif args.command == "cancel":
        job = client.cancel_job(args.job_id)
        print(f"Cancelled: {job['id']}  [{job['status']}]")

    elif args.command == "resume":
        job = client.resume_job(args.job_id)
        print(f"Resumed: {job['id']}  [{job['status']}]")

    elif args.command == "tasks":
        data = client.list_tasks()
        print(f"\n{'#':<4} {'Task Name':<28} Description")
        print("-" * 72)
        for i, t in enumerate(data["tasks"], 1):
            print(f"{i:<4} {t['name']:<28} {t['description']}")
        print()

    elif args.command == "chats":
        convs = client.list_conversations(limit=args.limit)
        if not convs:
            print("No conversations yet.")
        else:
            print(f"\n{'#':<4} {'Name':<22} {'ID':<38} Created")
            print("-" * 86)
            for i, c in enumerate(convs, 1):
                name = (c.get("name") or "(unnamed)")[:20]
                created = c["created_at"][:16].replace("T", " ")
                print(f"{i:<4} {name:<22} {c['id']:<38} {created}")
            print()

    elif args.command == "chat":
        resp = client.chat(args.message, conversation_id=args.conversation_id)
        print(f"[conv:{resp['conversation_id']}]")
        print(resp["reply"])

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
