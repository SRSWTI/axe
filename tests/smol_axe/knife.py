import glob as globlib
import json
import os
import re
import subprocess
import time
import sys
import tiktoken
from dotenv import load_dotenv
from openai import OpenAI
from openai.types.chat import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import (
    ChatCompletionMessageToolCall,
    Function,
)


load_dotenv()

API_KEY = os.getenv("OPENROUTER_API_KEY")
BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "anthropic/claude-opus-4.5"
MODELS = [
    "qwen/qwen3-coder-next",
    "anthropic/claude-sonnet-4.5",
]

client = OpenAI(base_url=BASE_URL, api_key=API_KEY)

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED, GRAY = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
    "\x1b[90m",
)

TOTAL_INPUT_TOKENS = 0
TOTAL_OUTPUT_TOKENS = 0



def read(args):
    try:
        lines = open(args["path"]).readlines()
        offset = args.get("offset", 0)
        limit = args.get("limit", len(lines))
        selected = lines[offset : offset + limit]
        return "".join(
            f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected)
        )
    except Exception as e:
        return f"error: {e}"


def write(args):
    try:
        with open(args["path"], "w") as f:
            f.write(args["content"])
        return "ok"
    except Exception as e:
        return f"error: {e}"


def edit(args):
    try:
        text = open(args["path"]).read()
        old, new = args["old"], args["new"]
        if old not in text:
            return "error: old_string not found"
        count = text.count(old)
        if not args.get("all") and count > 1:
            return f"error: old_string appears {count} times, must be unique (use all=true)"
        replacement = (
            text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
        )
        with open(args["path"], "w") as f:
            f.write(replacement)
        return "ok"
    except Exception as e:
        return f"error: {e}"


def glob(args):
    try:
        pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
        files = globlib.glob(pattern, recursive=True)
        files = sorted(
            files,
            key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
            reverse=True,
        )
        return "\n".join(files) or "none"
    except Exception as e:
        return f"error: {e}"


def grep(args):
    try:
        pattern = re.compile(args["pat"])
        hits = []
        for filepath in globlib.glob(args.get("path", ".") + "/**", recursive=True):
            try:
                for line_num, line in enumerate(open(filepath), 1):
                    if pattern.search(line):
                        hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
            except Exception:
                pass
        return "\n".join(hits[:50]) or "none"
    except Exception as e:
        return f"error: {e}"


def bash(args):
    try:
        result = subprocess.run(
            args["cmd"], shell=True, capture_output=True, text=True, timeout=30
        )
        return (result.stdout + result.stderr).strip() or "(empty)"
    except Exception as e:
        return f"error: {e}"





def run_streaming_command(cmd, timeout=None, return_summary=False):
    try:
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        output_buffer = []
        start_time = time.time()
        
        while True:
            if timeout and (time.time() - start_time > timeout):
                process.kill()
                return "\n".join(output_buffer) + "\n[Timeout reached]"

            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
                
            if line:
                stripped_line = line.rstrip()
                
                if any(x in stripped_line for x in ["Loading weights", "%|", "BertModel LOAD REPORT", "Key | Status"]):
                    continue

                output_buffer.append(stripped_line)
                
                display_line = stripped_line
                if len(display_line) > 60:
                    display_line = display_line[:30] + " ... " + display_line[-30:]
                
                print(f"{GRAY}  ⎿  {display_line}{RESET}", flush=True)
                
        if return_summary:
            summary = output_buffer[-20:] if len(output_buffer) > 20 else output_buffer
            return f"[Command finished. Summary of last 20 lines]:\n" + "\n".join(summary)
            
        return "\n".join(output_buffer) or "[Command finished with no output]"
    except Exception as e:
        return f"error: {e}"



def code_warm(args):
    """Index the codebase."""
    try:
        path = args.get("path", ".")
        return run_streaming_command(f"chop warm {path}", timeout=300, return_summary=True)
    except Exception as e:
        return f"error: {e}"

def code_index(args):
    """Build semantic index specifically."""
    try:
        path = args.get("path", ".")
        return run_streaming_command(f"chop semantic index {path}", timeout=600, return_summary=True)
    except Exception as e:
        return f"error: {e}"

def code_search(args):
    """Semantic or pattern search."""
    try:
        query = args["query"]
        path = args.get("path", ".")
        cmd = f"chop semantic search '{query}' --path {path}"
        raw_output = run_streaming_command(cmd, timeout=60, return_summary=False)
        
        try:
            start = raw_output.find('[')
            end = raw_output.rfind(']') + 1
            if start != -1 and end != -1:
                json_data = json.loads(raw_output[start:end])
                if isinstance(json_data, list):
                    return json.dumps(json_data[:5], indent=2)
        except Exception:
            pass
            
        return raw_output
    except Exception as e:
        return f"error: {e}"

def code_context(args):
    """Get LLM-ready context for a symbol."""
    try:
        symbol = args["symbol"]
        project = args.get("path", ".")
        cmd = f"chop context {symbol} --project {project}"
        return run_streaming_command(cmd, timeout=60, return_summary=False)
    except Exception as e:
        return f"error: {e}"

def code_structure(args):
    """Get file symbols/structure."""
    try:
        path = args["path"]
        cmd = f"chop structure {path}"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=30
        )
        return (result.stdout + result.stderr).strip()
    except Exception as e:
        return f"error: {e}"

def code_prewarm(args):
    """Run full pre-warming: index + generate knowledge base."""
    try:
        path = args.get("path", ".")
        cmd = f"uv run axe_knowledge_builder.py {path}"
        return run_streaming_command(cmd, timeout=600, return_summary=True)
    except Exception as e:
        return f"error: {e}"

def code_impact(args):
    """Find what depends on a symbol."""
    try:
        symbol = args["symbol"]
        path = args.get("path", ".")
        cmd = f"chop impact {symbol} {path}"
        return run_streaming_command(cmd, timeout=60, return_summary=False)
    except Exception as e:
        return f"error: {e}"



def _trigger_doc_update(file_path, summary="Agent edit"):
    """Trigger background update of knowledge base."""
    if "bodega.py" in file_path:
        return ""
        
    try:
        cmd = f'uv run axe_knowledge_builder.py --update "{file_path}" --summary "{summary}"'
        print(f"{GRAY}  ⎿  Updating Knowledge Base for {os.path.basename(file_path)}...{RESET}")
        
        run_streaming_command(cmd, timeout=60, return_summary=False)
        return "\n[Knowledge Base Updated]"
    except Exception as e:
        return f"\n[Doc Update Failed: {e}]"

def wrapped_write(args):
    result = write(args)
    if not result.startswith("error"):
        summary = f"Rewrote file content via write tool."
        doc_status = _trigger_doc_update(args["path"], summary)
        return result + doc_status
    return result

def wrapped_edit(args):
    result = edit(args)
    if not result.startswith("error"):
        summary = f"Edited file content via edit tool."
        doc_status = _trigger_doc_update(args["path"], summary)
        return result + doc_status
    return result



TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        wrapped_write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        wrapped_edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        bash,
    ),
    # "code_prewarm": (
    #     "PRE-WARM the codebase. Runs full analysis + generates Knowledge Base. Run this on any new/existing project first.",
    #     {"path": "string?"},
    #     code_prewarm,
    # ),
    # "code_warm": (
    #     "Index/re-index the codebase (full analysis). Run this first on new projects.",
    #     {"path": "string?"},
    #     code_warm,
    # ),
    # "code_index": (
    #     "Build/rebuild the semantic search index (embeddings) specifically.",
    #     {"path": "string?"},
    #     code_index,
    # ),
    "code_search": (
        "Semantic search: finds code by behavior/meaning (e.g. 'retry logic'). Use BEFORE grep.",
        {"query": "string", "path": "string?"},
        code_search,
    ),
    # "code_context": (
    #     "Get efficient LLM context (signatures, callees) ~95% token savings. Use INSTEAD of reading files.",
    #     {"symbol": "string", "path": "string?"},
    #     code_context,
    # ),
    # "code_structure": (
    #     "List functions/classes in a file/dir.",
    #     {"path": "string"},
    #     code_structure,
    # ),
    "code_impact": (
        "Find what calls/depends on a symbol (Reverse Call Graph).",
        {"symbol": "string", "path": "string?"},
        code_impact,
    ),
}


def run_tool(name, args):
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def make_openai_tools():
    tools = []
    for name, (description, params, _fn) in TOOLS.items():
        properties = {}
        required = []
        for param_name, param_type in params.items():
            is_optional = param_type.endswith("?")
            base_type = param_type.rstrip("?")
            json_type = "integer" if base_type == "number" else base_type
            properties[param_name] = {"type": json_type}
            if not is_optional:
                required.append(param_name)

        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )
    return tools



def count_tokens(text: str, model: str = "gpt-4") -> int:
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def call_api(messages, model):

    try:
        input_text = ""
        for msg in messages:
            if isinstance(msg, dict):
                input_text += str(msg.get("content", ""))
            elif hasattr(msg, "content"):
                input_text += str(msg.content or "")
        
        in_cnt = count_tokens(input_text, model)
 
        global TOTAL_INPUT_TOKENS, TOTAL_OUTPUT_TOKENS
        TOTAL_INPUT_TOKENS += in_cnt
        
        print(f"{DIM}Input tokens: {in_cnt} (Total: {TOTAL_INPUT_TOKENS}){RESET}")

        stream = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=make_openai_tools(),
            stream=True,
            extra_headers={
                "HTTP-Referer": "https://github.com/SRSWTI/axe",
                "X-Title": "axe",
                "include_reasoning": "true",
            },
            extra_body={
                "include_reasoning": True
            }
        )

        print(f"\n{CYAN}⏺{RESET} ", end="", flush=True)

        collected_content = []
        collected_tool_calls = {}
        
        in_reasoning = False
        reasoning_buffer = []

        def smooth_print(text, delay=0.002):
            for char in text:
                print(char, end="", flush=True)
                time.sleep(delay)

        for chunk in stream:
            delta = chunk.choices[0].delta
            

            delta_dict = delta.model_dump()
            
            reasoning_chunk = delta_dict.get("reasoning") or delta_dict.get("reasoning_content")
            
            if reasoning_chunk:
                if not in_reasoning:
                    in_reasoning = True
                    print(f"\n{GRAY}Reasoning:{RESET}\n{GRAY}", end="", flush=True)
                
                smooth_print(reasoning_chunk)
                reasoning_buffer.append(reasoning_chunk)
                continue 
            
            if in_reasoning and delta.content:
                in_reasoning = False
                print(f"{RESET}\n\n{CYAN}Response:{RESET}\n", end="", flush=True)

            if delta.content:
                content_chunk = delta.content
                smooth_print(content_chunk)
                collected_content.append(content_chunk)

            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in collected_tool_calls:
                        collected_tool_calls[idx] = {
                            "id": tc.id,
                            "type": "function",
                            "name": "",
                            "arguments": "",
                        }

                    if tc.id:
                        collected_tool_calls[idx]["id"] = tc.id

                    if tc.function:
                        if tc.function.name:
                            collected_tool_calls[idx]["name"] += tc.function.name
                        if tc.function.arguments:
                            collected_tool_calls[idx]["arguments"] += (
                                tc.function.arguments
                            )

        print()

        full_content = "".join(collected_content) if collected_content else None

        if full_content:
            out_cnt = count_tokens(full_content, model)
            TOTAL_OUTPUT_TOKENS += out_cnt
            
            print(f"{DIM}Output tokens: {out_cnt} (Total: {TOTAL_OUTPUT_TOKENS}){RESET}")
            print(f"{DIM}Total Session Tokens: {TOTAL_INPUT_TOKENS + TOTAL_OUTPUT_TOKENS}{RESET}")

        tool_calls_obj = []
        if collected_tool_calls:
            for idx in sorted(collected_tool_calls.keys()):
                data = collected_tool_calls[idx]
                tool_calls_obj.append(
                    ChatCompletionMessageToolCall(
                        id=data["id"],
                        type="function",
                        function=Function(
                            name=data["name"], arguments=data["arguments"]
                        ),
                    )
                )

        return ChatCompletionMessage(
            role="assistant",
            content=full_content,
            tool_calls=tool_calls_obj if tool_calls_obj else None,
        )

    except Exception as e:
        print(f"{RED}API Error: {e}{RESET}")
        return None


def separator():
    return f"{DIM}{'─' * min(os.get_terminal_size().columns, 80)}{RESET}"


def render_markdown(text):
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


def select_model():
    print(f"\n{BOLD}Select Model:{RESET}")
    for i, m in enumerate(MODELS):
        print(f" {i+1}) {m}")
    print(f" {len(MODELS)+1}) Custom...")

    choice = input(f"\n{BOLD}Choice (default 1):{RESET} ").strip()
    if not choice:
        return MODELS[0]

    try:
        idx = int(choice) - 1
        if 0 <= idx < len(MODELS):
            return MODELS[idx]
        elif idx == len(MODELS):
            return input(f"{BOLD}Enter model ID:{RESET} ").strip()
    except ValueError:
        pass

    return MODELS[0]


def main():
    if len(sys.argv) > 1:
        target_dir = sys.argv[1]
        try:
            os.chdir(target_dir)
            print(f"{GREEN}Changed working directory to: {os.getcwd()}{RESET}")
        except FileNotFoundError:
            print(f"{RED}Directory not found: {target_dir}{RESET}")
            return

    if not API_KEY:
        print(f"{RED}Error: OPENROUTER_API_KEY not found in .env{RESET}")
        return

    current_model = DEFAULT_MODEL

    # current_model = select_model()

    print(f"{BOLD}axe-code{RESET} | {DIM}{current_model} | {os.getcwd()}{RESET}\n")
    print(f"{DIM}Type /model to switch models{RESET}")

    messages = []
    tool_list = ", ".join(TOOLS.keys())
    system_prompt = f"""You are 'axe', a world-class agentic coding assistant.

# INTELLIGENT WORKFLOW: GREP + CODESEARCH
1. **Grep (PREFERRED)**: Use FIRST for exact text matches.
2. **CodeSearch (SEMANTIC)**: Combine with Grep. Use HEAVILY for behavioral queries ("retry logic") even without knowing exact names.
3. **CodeImpact**: Check callers/dependencies before refactoring.
4. **Edit**: Use `edit` for precise string replacement.

# RULE OF THUMB
- Know the text? -> `grep`
- Know the behavior? -> `code_search`

Capabilities:
1. Local File System: Use read, write, edit, glob, grep, and bash.
2. Engine Tools: You have access to complex tools via the server.
   Available Tools: {tool_list}
"""
    messages.append({"role": "system", "content": system_prompt})

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}❯{RESET} ").strip()
            print(separator())
            if not user_input:
                continue

            if user_input.lower() in ("/q", "exit", "quit"):
                break

            if user_input.lower() == "/c":
                messages = [{"role": "system", "content": system_prompt}]
                print(f"{GREEN}⏺ Cleared conversation{RESET}")
                continue

            if user_input.lower() == "/model":
                current_model = select_model()
                print(f"{GREEN}⏺ Switched to {current_model}{RESET}")
                continue

            messages.append({"role": "user", "content": user_input})

            while True:
                message_response = call_api(messages, current_model)
                if not message_response:
                    break

                messages.append(message_response)

                tool_calls = message_response.tool_calls

                if tool_calls:
                    for tool_call in tool_calls:
                        tool_name = tool_call.function.name
                        tool_args = json.loads(tool_call.function.arguments)
                        arg_preview = str(tool_args)[:50]

                        print(
                            f"\n{GREEN}⏺ {tool_name.capitalize()}{RESET}({DIM}{arg_preview}{RESET})"
                        )

                        result = run_tool(tool_name, tool_args)

                        result_lines = result.split("\n")
                        preview = result_lines[0][:60]
                        if len(result_lines) > 1:
                            preview += f" ... +{len(result_lines) - 1} lines"
                        elif len(result_lines[0]) > 60:
                            preview += "..."
                        print(f"  {DIM}⎿  {preview}{RESET}")

                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "content": result,
                            }
                        )
                else:
                    break

            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}⏺ Error: {err}{RESET}")


if __name__ == "__main__":
    main()