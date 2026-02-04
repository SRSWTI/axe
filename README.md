# axe: The Agent Built for Real Engineers

**What it really means to be a 10x engineer—and the tool built for that reality.**

![axe in action](assets/gifs/bodega_axe.png)

---

## What do you mean by a "10x engineer"

The industry loves the lore of "10x engineer"—the lone genius who ships a new product in a weekend, the hacker who rewrites the entire stack in a caffeine-fueled sprint, the visionary who creates something from nothing.

**That's not what a 10x engineer actually does.**

The real 10x engineers aren't working on greenfield projects. They're not inventing new frameworks or building the next viral app. They're maintaining **behemoth codebases** where millions of users depend on their decisions every single day.

Their incentive structure is fundamentally different: **"If it's not broken, don't fix it."**

And with that constraint in mind, they ask a different question entirely:

> **"What truly matters for solving this particular problem, and how can I gain enough confidence to ship it reliably?"**

---

## Okay i get it, what is the engineering challenge?

**Idea creation is a human trait.** Ideas arise from impulsive feelings, obstacles we encounter, problems we want to solve. Creating something new is exciting, visceral, immediate.

**Maintaining something reliably over time requires a completely different pedigree**—and it's by far more important than creating the idea itself.

Consider the reality:
- A production codebase with **100,000+ lines** across hundreds of files
- **Millions of users** whose workflows depend on your system staying stable
- **Years of accumulated complexity**: edge cases, performance optimizations, backwards compatibility
- **Distributed teams** where no single person understands the entire system
- **The cost of breaking things** is measured in downtime, lost revenue, and user trust

In this environment, the questions that matter are:
- "If I change this function, what breaks?"
- "How does this data flow through the system?"
- "What are all the execution paths that touch this code?"
- "Where are the hidden dependencies I need to understand before refactoring?"

**This is where most coding tools fail.**

They're built for the weekend hackathon, the demo video, the "move fast and break things" mentality. They optimize for speed of creation, not confidence in maintenance.

---

## Why we built axe?

We built axe because we understood this problem intimately. Our team has been maintaining production systems at scale, and we needed a tool that matched the way **real engineering** actually works.

**axe is built for large codebases.** Not prototypes. Not "good enough for now" solutions.

It's built for the engineer who needs to:
- Understand a **call graph** before changing a function signature
- Trace **data flow** to debug a subtle state corruption
- Analyze **execution paths** to understand why a test fails in CI but not locally
- Perform **impact analysis** before refactoring to know exactly what depends on what

**The core insight:** To ship reliably in large codebases, you need **precise understanding**, not exhaustive reading.

---

## Explore axe

| Resource | Description |
|----------|-------------|
| **[Installation](README.md#quick-start)** | Get up and running in seconds. |
| **[axe-dig](docs/AXE-DIG.md)** | A powerful inference needs a precise retrieval. Here you can dig with us more. |
| **[Use Cases](examples/README.md)** | Real-world workflows: features, bugs, refactoring, exploration. |
| **[Tools](src/axe_cli/tools/README.md)** | Complete reference for file ops, shell, and axe-dig tools. |
| **[Agents](src/axe_cli/agents/README.md)** | Creating custom agents and subagents for parallel work. |
| **[Configuration](src/axe_cli/README.md)** | Providers, models, sessions, and architecture deep dive. |

---

## We believe in precision.

Most coding tools take the brute-force approach: dump your entire codebase into the context window and hope the LLM figures it out.

**This is backwards.**

axe uses **axe-dig**, a 5-layer of retrieval that extracts **exactly what matters** for the task at hand:

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 5: Program Dependence  → "What affects line 42?"      │
│ Layer 4: Data Flow           → "Where does this value go?"  │
│ Layer 3: Control Flow        → "How complex is this?"       │
│ Layer 2: Call Graph          → "Who calls this function?"   │
│ Layer 1: AST                 → "What functions exist?"      │
└──────────────────────────────────────────────────────────────┘
```

When you need to understand a function, axe-dig gives you:
- The function signature and what it does
- **Forward call graph**: What does this function call?
- **Backward call graph**: Who calls this function?
- **Control flow complexity**: How many execution paths exist?
- **Data flow**: How do values transform through this code?
- **Impact analysis**: What breaks if I change this?

Sometimes this means fetching **more context**, not less. When you're debugging a race condition or tracing a subtle bug through multiple layers, axe-dig will pull in the full dependency chain—because **correctness matters more than brevity**.

---

## Let's see axe in action.

To demonstrate the precision advantage, we built a minimal cli agent implementation with basic tools (grep, edit, write, shell) and compared it against the same agent with axe-dig tools.

**Note:** These are intentionally minimal implementations to show how phenomenal the axe-dig difference is. (If you want to try it yourself, here you go-- we named it knife since its a small implementation of axe. [`tests/smol_axe/knife.py`](tests/smol_axe/knife.py)).

### Example 1: Basic Edit Operations

![comparison](assets/gifs/axe_comparison.gif)

**Left:** Basic cli agent with grep  
**Right:** basic cli with axe-dig

The difference is clear. The basic agent searches blindly, while axe-dig understands code structure and dependencies.

### Example 2: Understanding Call Flow Tracers

When asked to explain how call flow tracking works, both agents found the context—but the results were dramatically different.

![call flow part 1](assets/gifs/axe_explain_dig.gif)

**Left:** Had to read the entire file after grepping for literal strings. **44,000 tokens**.  
**Right:** axe-dig used **17,000 tokens** while also discovering:
- Call graphs for the decorator used on tracer functions
- Thread-safe depth tracking mechanisms
- How functions using this decorator actually work

axe-dig didn't just use fewer tokens—it provided **better understanding** of how the code flows.

### Example 3: The Compounding Effect

The difference compounds with follow-up questions. When we asked about caller information:

![call flow part 2](assets/gifs/axe_call_flow_compounding.gif)

**Left:** Started wrong, inferred wrong, continued wrong.  
**Right:** Had more context and better understanding from the start, leading to precise answers.

**This is why axe optimizes for what the code actually does and how it flows.**

### Example 4: Active Search vs. Passive Explanation

In the mlx-lm codebase, when asked how to compute DWQ targets:

![better inference](assets/gifs/axe_better_inference.gif)

**Left:** Explained the concept generically.  
**Right:** axe cli actively searched the codebase and found the actual implementation.

**Precision means finding the answer in your code, not explaining theory. **

---

## Intelligence per watt → Relevant tokens per context 

For Bodega, we optimized models for intelligence per watt: maximum throughput, minimum power consumption.

For axe, the equivalent metric is relevant tokens per context window.

| Scenario | Raw Tokens | axe-dig Tokens | Savings |
|----------|------------|----------------|---------|
| Function + callees | 21,271 | 175 | **99%** |
| Codebase overview (26 files) | 103,901 | 11,664 | 89% |
| Deep call chain (7 files) | 53,474 | 2,667 | 95% |

Precision retrieval naturally uses fewer tokens when extracting only what's needed for correct decisions. But when you need to trace a complex bug through seven layers, axe-dig fetches 150,000 tokens—whatever it takes.
Other tools burn tokens because they charge per token. axe optimizes for correctness.

---

## Built for Local Intelligence

axe was designed with **local compute and local LLMs** in mind.

Why does this matter?

Local LLMs have different constraints than cloud APIs:
- **Slower prefill and decoding** (can't waste time on irrelevant context)
- **Smaller context windows** (need precision, not bloat)
- **No per-token billing** (optimization is about speed and accuracy, not cost)

This forced us to build a **precise retrieval engine** from the ground up. We couldn't rely on "dump everything and let the cloud LLM figure it out."

The result: **axe works brilliantly with both local and cloud models**, because precision benefits everyone.

### Running Locally: Real-World Performance

Here's axe running with **srswti/blackbird-she-doesnt-refuse-21b**—a 21B parameter model from our Bodega collection, running entirely locally:

![local model demonstration](assets/gifs/axe_subagents.gif)

**Hardware:** M1 Max, 64GB RAM  
**Performance:** Spawning subagents, parallel task execution, full agentic capabilities

As you can see, the capability of axe-optimized Bodega models running locally is exceptional. The precision retrieval engine means even local models can handle complex workflows efficiently—because they're not wasting compute on irrelevant context.

---

## The axe-dig Advantage: Semantic Search

Traditional search finds syntax. **axe-dig semantic search finds behavior.**

```bash
# Traditional grep
grep "cache" src/  # Finds: variable names, comments, "cache_dir"

# axe-dig semantic search
chop semantic search "memoize expensive computations with TTL expiration"

# Finds: get_user_profile() because:
# - It calls redis.get() and redis.setex() (caching pattern)
# - Has TTL parameter in redis.setex call
# - Called by functions that do expensive DB queries
# Even though it doesn't mention "memoize" or "TTL"
```

Every function gets embedded with:
- Signature and docstring
- **Forward and backward call graphs**
- **Complexity metrics** (branches, loops, cyclomatic complexity)
- **Data flow patterns** (variables used and transformed)
- **Dependencies** (imports, external modules)
- First ~10 lines of implementation

This gets encoded into **1024-dimensional embeddings**, indexed with FAISS for fast similarity search.

**Find code by what it does, not what it's named.**

---

## Core Capabilities

### axe Operations

| Tool | What it does | Use case |
|------|-------------|----------|
| **CodeSearch** | Semantic search by behavior | "Find payment processing logic" |
| **CodeContext** | LLM-ready function summaries with call graphs | Understand unfamiliar code |
| **CodeStructure** | Navigate functions/classes in files/dirs | Explore new codebases |
| **CodeImpact** | Reverse call graph (who calls this?) | Safe refactoring |

### File Operations
- `ReadFile` / `WriteFile` / `StrReplaceFile` - Standard file I/O
- `Grep` - Exact file locations + line numbers (use after CodeSearch)
- `Glob` - Pattern matching
- `ReadMediaFile` - Images, PDFs, videos

### Multi-Agent Workflows
- `Task` - Spawn subagents for parallel work
- `CreateSubagent` - Custom agent specs
- `SetTodoList` - Track multi-step tasks

**Subagents in action:**

![subagents](assets/gifs/axe_subagents.gif)

Spawn specialized subagents to divide and conquer complex workflows. Each subagent operates independently with its own context and tools.

---

## Quick Start

### Install
```bash
# Install axe-cli (includes axe-dig)
uv pip install axe-cli

# Or from source
git clone https://github.com/SRSWTI/axe-cli
cd axe-cli
uv sync
axe
```

### Run
```bash
cd /path/to/your/project
axe
```

On first run, axe-dig automatically indexes your codebase (30-60 seconds for typical projects). After that, queries are instant.

### Start Using
```bash
# greet axe
hiii

# start coding
hey axe, can you tell me how does dwq targets are computed in mlx

# Toggle to shell mode
[Ctrl+X]
pytest tests/
[Ctrl+X]
```
Hit **Ctrl+X** to toggle between axe and your normal shell. No context switching. No juggling terminals.

![shell toggle](assets/gifs/axe_axe_sample_toggle_shell.gif)

---

## Powered by SRSWTI Inc.

**Building the world's fastest retrieval and inference engines.**

### Getting Started with Bodega

To access our inference engine and manage the lifecycle of your models, you need a simple setup:

1.  **Bodega Sensors**: Provides high-performance backend access and inference serving.
2.  **Bodega**: The visual interface for managing models, chats, and system status.

**Quick Install (macOS Tahoe and above, only for Apple-Silicon):**

```bash
curl -sL https://raw.githubusercontent.com/SRSWTI/axe/main/install_sensors.sh | bash
```

**Manual Setup:**
1.  Open **BodegaOS client** and log in with Google.
2.  Navigate to **Chat** → **Bodega Hub** → **Advanced**.
3.  click **Docs** to learn how to connect axe to your local Bodega Inference Engine.

### Bodega Inference Engine

Exclusive models trained/optimized for Bodega Inference Engine. axe includes **zero-day support** for all Bodega models, ensuring immediate access to our latest breakthroughs.

**Note:** Our models are also available on [🤗 Hugging Face](https://huggingface.co/srswti).

#### Raptor Series
Ultra-compact reasoning models designed for efficiency and edge deployment. **Super light**, amazing agentic coding capabilities, robust tool support, minimal memory footprint.

- [🤗 **bodega-raptor-0.9b**](https://huggingface.co/srswti/bodega-raptor-0.9b) - 900M params. Runs on base m4 air with 100+ tok/s.
- [🤗 **bodega-raptor-90m**](https://huggingface.co/srswti/bodega-raptor-90m) - Extreme edge variant. Sub-100M params for amazing tool calling.
- [🤗 **bodega-raptor-1b-reasoning-opus4.5-distill**](https://huggingface.co/srswti/bodega-raptor-1b-reasoning-opus4.5-distill) - Distilled from Claude Opus 4.5 reasoning patterns.
- [🤗 **bodega-raptor-8b-mxfp4**](https://huggingface.co/srswti/bodega-raptor-8b-mxfp4) - Balanced power/performance for laptops.
- [🤗 **bodega-raptor-15b-6bit**](https://huggingface.co/srswti/bodega-raptor-15b-6bit) - Enhanced raptor variant.

#### Flagship Models
Frontier intelligence, distilled and optimized.

- [🤗 **deepseek-v3.2-speciale-distilled-raptor-32b-4bit**](https://huggingface.co/srswti/deepseek-v3.2-speciale-distilled-raptor-32b-4bit) - DeepSeek V3.2 distilled to 32B with Raptor reasoning. Exceptional math/code generation in 5-7GB footprint. 120 tok/s on M1 Max.
- [🤗 **bodega-centenario-21b-mxfp4**](https://huggingface.co/srswti/bodega-centenario-21b-mxfp4) - Production workhorse. 21B params optimized for sustained inference workloads.
- [🤗 **bodega-solomon-9b**](https://huggingface.co/srswti/bodega-solomon-9b) - Multimodal and best for agentic coding.

#### Axe-Turbo Series
**Launched specifically for the Axe coding use case.** High-performance agentic coding models optimized for the Axe ecosystem.

- [🤗 **axe-turbo-1b**](https://huggingface.co/srswti/axe-turbo-1b) - 1B params, 150 tok/s, sub-50ms first token. Edge-first architecture.
- [🤗 **axe-turbo-31b**](https://huggingface.co/srswti/axe-turbo-31b) - High-capacity workloads. Exceptional agentic capabilities.

#### Specialized Models
Task-specific optimization.

- [🤗 **bodega-vertex-4b**](https://huggingface.co/srswti/bodega-vertex-4b) - 4B params. Optimized for structured data.
- [🤗 **blackbird-she-doesnt-refuse-21b**](https://huggingface.co/srswti/blackbird-she-doesnt-refuse-21b) - Uncensored 21B variant for unrestricted generation.

### Using Bodega Models

Configure Bodega in `~/.axe/config.toml`:

```toml
default_model = "bodega-raptor"

[providers.bodega]
type = "bodega"
base_url = "http://localhost:44468"  # Local Bodega server
api_key = ""

[models.bodega-raptor]
provider = "bodega"
model = "srswti/bodega-raptor-8b-mxfp4"
max_context_size = 32768
capabilities = ["thinking"]

[models.bodega-turbo]
provider = "bodega"
model = "srswti/axe-turbo-31b"
max_context_size = 32768
capabilities = ["thinking"]
```

See [sample_config.toml](sample_config.toml) for more examples including OpenRouter, Anthropic, and OpenAI configurations.

---

---



## What's Coming

Our internal team has been using features that will change the game:

### 1. Interactive Dashboard: Visualize Your Codebase

Understanding code isn't just about reading—it's about **seeing** the structure, connections, and flow.

The dashboard provides real-time visualization for:

![dashboard visualization](assets/gifs/axe_axe_future.gif)

**Code Health Analysis:**
- **Cyclic dependencies**: Visualize circular imports and dependency loops that make refactoring dangerous
- **Dead code detection**: See unreachable functions and unused modules with connection graphs
- **Safe refactoring zones**: Identify code that can be changed without cascading effects
- **Execution trace visualization**: Watch the actual flow of data through your system at runtime

**Debugging Workflows:**
- Trace execution paths visually from entry point to crash
- See which functions are called, in what order, with what values
- Identify bottlenecks and performance hotspots in the call graph
- Understand data transformations across multiple layers

The dashboard turns axe-dig's 5-layer analysis into interactive, explorable visualizations. No more drawing diagrams on whiteboards—axe generates them from your actual code.

### 2. Execution Tracing

See what actually happened at runtime. No more guessing why a test failed.

```bash
# Trace a failing test
/trace pytest tests/test_payment.py::test_refund

# Shows exact values that flowed through each function:
# process_refund(amount=Decimal("50.00"), transaction_id="tx_123")
#   → validate_refund(transaction=Transaction(status="completed"))
#     → check_refund_window(created_at=datetime(2024, 1, 15))
#       → datetime.now() - created_at = timedelta(days=45)
#       → raised RefundWindowExpired  # ← 30-day window exceeded
```

### 3. Monorepo Factoring (Enterprise Feature)

**Status:** Under active development. Our team has been using this internally for weeks.

Large monorepos become unmaintainable when everything is tangled together. axe analyzes your codebase and automatically factors it into logical modules based on:

- **Dependency analysis**: Which code actually depends on what
- **Call graph clustering**: Functions that work together, grouped together
- **Data flow boundaries**: Natural separation points in your architecture
- **Usage patterns**: How different parts of the codebase are actually used

**The result:** Clear module boundaries, reduced coupling, easier maintenance. This has been heavily requested by enterprise customers managing multi-million-line monorepos.

**Example workflow:**
```bash
# Analyze current structure
/monorepo analyze .

# Shows: 47 logical modules detected across 1,200 files
# Suggests: Split into 5 packages with clear boundaries
# Impact: Reduces cross-module dependencies by 73%

# Apply factoring
/monorepo factor --target packages/
```

### 4. Language Migration (X → Y)

Migrating codebases between languages is notoriously error-prone. axe uses its deep understanding of code structure to enable reliable migrations:

**How it works:**
1. **Analyze source code**: Extract call graphs, data flow, and business logic
2. **Preserve semantics**: Understand what the code does, not just what it says
3. **Generate target code**: Translate to the new language while maintaining behavior
4. **Verify correctness**: Compare execution traces and test coverage

**Supported migrations:**
- Python → TypeScript (preserve type safety)
- JavaScript → Go (maintain concurrency patterns)
- Ruby → Rust (keep performance characteristics)
- Java → Kotlin (modernize while preserving architecture)

Unlike simple transpilers, axe understands your code's **intent** and translates it idiomatically to the target language.

### 5. Performance Debugging

Flame graphs and memory profiling integrated directly in the chat interface.

```bash
# Generate flame graph
/flamegraph api_server.py

# Find memory leaks
/memory-profile background_worker.py
```

### 6. Smart Test Selection

```bash
# Only run tests affected by your changes
/test-impact src/payment/processor.py

# Shows: 12 tests need to run (not all 1,847)
```

---

## Supported Languages

Python, TypeScript, JavaScript, Go, Rust, Java, C, C++, Ruby, PHP, C#, Kotlin, Scala, Swift, Lua, Elixir

Language auto-detected. Specify with `--lang` if needed.

---

## Comparison

| Feature | Claude Code | OpenAI Codex | axe |
|---------|-------------|--------------|-----|
| **Built for** | Weekend projects | Demos | Production codebases |
| **Context strategy** | Dump everything | Dump everything | Extract signal (precision-first) |
| **Code search** | Text/regex | Text/regex | Semantic (behavior-based) |
| **Call graph analysis** | ❌ | ❌ | ✅ 5-layer analysis |
| **Precision optimization** | ❌ (incentivized to waste) | ❌ (incentivized to waste) | ✅ Fetch what's needed for correctness |
| **Execution tracing** | ❌ | ❌ | ✅ Coming soon |
| **Flame graphs** | ❌ | ❌ | ✅ Coming soon |
| **Memory profiling** | ❌ | ❌ | ✅ Coming soon |
| **Visual debugging** | ❌ | ❌ | ✅ Coming soon |
| **Shell integration** | ❌ | ❌ | ✅ Ctrl+X toggle |
| **Session management** | Limited | Limited | ✅ Full history + replay |
| **Skills system** | ✅  | ✅ | ✅ Modular, extensible |
| **Subagents** | ❌ | ❌ | ✅ Parallel task execution |

---

## Community

- **Issues**: [GitHub Issues](https://github.com/SRSWTI/axe/issues)
- **Discussions**: [GitHub Discussions](https://github.com/SRSWTI/axe/discussions)

## Acknowledgements

Special thanks to [kimi-cli](https://github.com/MoonshotAI/kimi-cli) for their amazing work, which inspired our tools and the Kosong provider.
