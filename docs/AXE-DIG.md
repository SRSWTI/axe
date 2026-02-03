# axe-dig: we dig deep to find how it works

**The brutal truth:** Your codebase is too big for context windows. We don't pretend otherwise.

Instead of dumping 100K lines and hoping for the best, axe-dig extracts exactly what matters. Structure, dependencies, data flow, execution paths—all at **95% fewer tokens** than reading raw files.

---

## The Problem: ctx window, slop coders end up spending a $500 to make a chat ui 

Your production codebase: 100,000 lines.
Claude's context window: ~200,000 tokens.
The math doesn't work.

| Approach | Tokens | What You Actually Get |
|----------|--------|----------------------|
| Read raw files | 23,314 | Full code, zero context left for responses |
| Grep results | ~5,000 | File paths. No understanding whatsoever. |
| **axe-dig** | **1,189** | Structure + call graphs + complexity metrics—everything needed for correct edits |

Measured on real production codebases with tiktoken. 95% reduction while keeping everything that matters.

---

## Installation

```bash
# axe-dig comes with axe-cli
pip install axe-cli

# path to your prject dir
axe

# Or standalone
pip install axe-dig

# First use in any project
cd /path/to/your/project
chop warm .  # Builds all 5 analysis layers
chop semantic index .
```

The daemon auto-starts. Indexes stay in memory. Queries return in ~100ms instead of 30 seconds.

---

## We dig 5 levels deep, and understand the width too.

Not every question needs full program analysis. Use the layer that matches your task:

```
┌──────────────────────────────────────────────────────────────┐
│ Layer 5: Program Dependence  → "What code affects line 89?"  │
│ Layer 4: Data Flow           → "Where does this value go?"   │
│ Layer 3: Control Flow        → "How complex is this?"        │
│ Layer 2: Call Graph          → "Who depends on this?"        │
│ Layer 1: AST                 → "What exists in this file?"   │
└──────────────────────────────────────────────────────────────┘
```

### Layer 1: AST (Structure)

**Question:** "What's in this file?"

**Token cost:** ~480 tokens for a 500-line file (vs 4,200 raw)

```bash
chop extract src/payment.py
```

**Output:**
```json
{
  "functions": [
    {
      "name": "process_payment",
      "signature": "async def process_payment(amount: Decimal, card: Card) -> Transaction",
      "params": ["amount: Decimal", "card: Card"],
      "return_type": "Transaction",
      "is_async": true,
      "line": 67
    }
  ],
  "classes": [
    {
      "name": "PaymentProcessor",
      "methods": ["process_payment", "refund", "validate_card"],
      "line": 23
    }
  ],
  "imports": ["from decimal import Decimal", "import stripe"]
}
```

**Use case:** Understand file structure without reading implementation details.

---

### Layer 2: Call Graph (Dependencies)

**Token cost:** +420 tokens (cumulative ~900)

#### Forward: What Does This Call?

```bash
chop calls /path/to/project
```

```json
{
  "function": "process_payment",
  "calls": [
    "validate_card",
    "stripe.charge",
    "db.save_transaction",
    "send_receipt_email"
  ]
}
```

#### Backward: Impact Analysis

```bash
# "If I change validate_card(), what breaks?"
chop impact validate_card /path/to/project
```

```json
{
  "function": "validate_card",
  "called_by": [
    {"file": "payment.py", "function": "process_payment", "line": 72},
    {"file": "payment.py", "function": "update_card", "line": 134},
    {"file": "subscription.py", "function": "renew_subscription", "line": 45},
    {"file": "tests/test_payment.py", "function": "test_invalid_card", "line": 28}
  ]
}
```

**Use case:** Safe refactoring. Know exactly what depends on what before you change anything.

---

### Layer 3: CFG (Control Flow)

**Token cost:** +105 tokens (cumulative ~1,005)

```bash
chop cfg src/payment.py process_payment
```

**Output:**
```json
{
  "function": "process_payment",
  "blocks": [
    {"id": 0, "statements": ["card_valid = validate_card(card)"]},
    {"id": 1, "statements": ["if not card_valid:", "    raise InvalidCard"]},
    {"id": 2, "statements": ["if amount <= 0:", "    raise InvalidAmount"]},
    {"id": 3, "statements": ["charge = stripe.charge(amount, card)", "return charge"]}
  ],
  "edges": [[0,1], [1,2], [2,3], [1,3], [2,3]],
  "complexity": 3
}
```

**What this tells you:**
- **Complexity: 3** → Function has 3 decision points (2 if statements = 3 execution paths)
- **Blocks:** 4 basic blocks (straight-line code between branches)
- **Edges:** Which blocks can follow which (for tracing execution)

**Use case:** Find overly complex functions (complexity > 10 = refactor candidate).

---

### Layer 4: DFG (Data Flow)

**Token cost:** +125 tokens (cumulative ~1,130)

```bash
chop dfg src/payment.py process_payment
```

**Output:**
```json
{
  "function": "process_payment",
  "variables": [
    {"name": "card_valid", "defined_at": [3], "used_at": [5]},
    {"name": "charge", "defined_at": [15], "used_at": [18, 22]},
    {"name": "transaction", "defined_at": [18], "used_at": [25]}
  ],
  "flows": [
    {"from": "card", "to": "card_valid", "via": "validate_card"},
    {"from": "amount", "to": "charge", "via": "stripe.charge"},
    {"from": "charge", "to": "transaction", "via": "db.save_transaction"}
  ]
}
```

**Use case:** Debugging. "Why is `charge` wrong? Let me trace back through the data flow."

---

### Layer 5: PDG (Program Slicing)

**Token cost:** +145 tokens (cumulative ~1,275)

**The killer feature:** Show only code that affects a specific line.

```bash
# "What code affects the return value on line 89?"
chop slice src/payment.py process_payment 89
```

**Output:**
```json
{
  "target_line": 89,
  "slice": [5, 8, 15, 67, 82, 89],
  "slice_code": [
    "card_valid = validate_card(card)",
    "if not card_valid: raise InvalidCard",
    "if amount <= 0: raise InvalidAmount",
    "charge = stripe.charge(amount, card)",
    "transaction = db.save_transaction(charge)",
    "return transaction"
  ]
}
```

**Before axe-dig:** Read 180-line function, manually trace every variable, miss the bug.
**With axe-dig:** See only the 6 lines that matter.

**Use case:** Answering "why did this variable have this value?" in complex functions.

---

## Real Example: Debugging a Tensor Shape Mismatch

**Scenario:** Training a transformer model crashes with "RuntimeError: mat1 and mat2 shapes cannot be multiplied (32x512, 768x1024)"

**Without axe-dig:**
1. Read the 180-line forward pass method
2. Trace every tensor transformation manually
3. Check all layer dimensions
4. Miss the dimension mismatch in initialization
5. Spend 45 minutes debugging

**With axe-dig:**

```bash
# 1. Find where the error occurs
chop search "mat1 and mat2 shapes" src/

# 2. Get program slice for that line
chop slice src/model.py TransformerBlock.forward 112

# Output shows only relevant code:
# 23:  x = self.embed(input_ids)  # [batch, seq, 768]
# 45:  attn_output = self.attention(x)  # [batch, seq, 768]
# 67:  x = x + attn_output
# 89:  x = self.layer_norm(x)  # [batch, seq, 768]
# 112: output = self.fc(x.mean(dim=1))  # ← ERROR HERE
# 134: return output

# 3. Check data flow for x
chop dfg src/model.py TransformerBlock.forward

# Shows: x maintains shape [batch, seq, 768] throughout
# x.mean(dim=1) produces [batch, 768]
# But self.fc expects input_dim=512 (wrong!)

# 4. Find where fc was initialized
chop impact fc src/
# Shows: self.fc = nn.Linear(512, num_classes) in __init__
# Should be: self.fc = nn.Linear(768, num_classes)
```

**Result:** Bug found in 8 minutes. 6 lines of code instead of 180. 175 tokens instead of 21,000.

The issue: `self.fc` was initialized with wrong input dimension (512 instead of 768) because someone copy-pasted from a different model architecture.

---

## Visual Demonstrations: axe-dig vs. Basic Tools

To demonstrate the precision advantage, we built minimal CLI agent implementations and compared them side-by-side.

### Example 1: Call Flow Tracker Analysis

When asked to explain how call flow tracking works:

<p align="center">
  <video src="https://api.srswti.com/storage/v1/object/public/aide_public/axe-github/axe_explain_dig.mp4" width="100%" autoplay loop muted playsinline>
    call flow explanation
  </video>
</p>

**Left:** Basic agent had to read the entire file after grepping for literal strings. **44,000 tokens**.  
**Right:** axe-dig used **17,000 tokens** while discovering:
- Call graphs for the decorator used on tracer functions
- Thread-safe depth tracking mechanisms
- How functions using this decorator actually work

axe-dig provided better understanding with fewer tokens.

### Example 2: Follow-up Questions Compound the Difference

When asked about caller information:

<p align="center">
  <video src="https://api.srswti.com/storage/v1/object/public/aide_public/axe-github/axe_call_flow_compounding.mp4" width="100%" autoplay loop muted playsinline>
    compounding effect
  </video>
</p>

**Left:** Started wrong, inferred wrong, continued wrong.  
**Right:** Had more context from the start, leading to precise answers.

### Example 3: Active Search vs. Generic Explanation

In the mlx-lm codebase, when asked how to compute DWQ targets:

<p align="center">
  <video src="https://api.srswti.com/storage/v1/object/public/aide_public/axe-github/axe_better_inference.mp4" width="100%" autoplay loop muted playsinline>
    better inference
  </video>
</p>

**Left:** Explained the concept generically.  
**Right:** axe actively searched the codebase and found the actual implementation.

**This is the difference:** axe-dig doesn't just save tokens—it finds the right answer in your code.

---

## Semantic Search: Find Code by Behavior

Traditional search finds text matches. axe-dig semantic search finds **what code does** based on call graphs and structural patterns.

```bash
# Traditional grep
grep "cache" src/  # Finds: variable names, comments, "cache_dir"

# axe-dig semantic search
chop semantic "memoize expensive computations with TTL expiration" src/
# Finds get_user_profile() because:
# - It calls redis.get() and redis.setex() (caching pattern)
# - Has TTL parameter in redis.setex call  
# - Called by functions that do expensive DB queries
# Even though it doesn't mention "memoize" or "TTL"
```

### How It Works

Every function gets embedded with:
- Function signature and docstring
- Forward call graph (what it calls)
- Backward call graph (who calls it)
- Complexity metrics (branches, loops, cyclomatic complexity)
- Data flow patterns (variables used and transformed)
- Dependencies (imports, external modules)
- First ~10 lines of implementation

This gets encoded into **1024-dimensional vectors** via sentence transformers, indexed with FAISS for fast similarity search.

### Example Queries

**1. Find retry logic with exponential backoff:**
```bash
chop semantic search "retry failed operations with exponential backoff"
```
**Result:**
```json
[
  {
    "name": "_is_retryable_error",
    "file": "src/axe_cli/soul/axesoul.py",
    "score": 0.713
  },
  {
    "name": "_retry_log",
    "file": "src/axe_cli/soul/axesoul.py",
    "score": 0.710
  }
]
```
**Why:** Neither function mentions "exponential backoff" in the name. But the embedding understands they're part of retry logic because they check exception types, are called by retry loops, and handle error recovery patterns.

**2. Find configuration loading:**
```bash
chop semantic search "load configuration from toml file"
```
**Result:**
```json
[
  {
    "name": "load_config_from_string",
    "file": "src/axe_cli/config.py",
    "score": 0.759
  },
  {
    "name": "_migrate_json_config_to_toml",
    "file": "src/axe_cli/config.py",
    "score": 0.747
  },
  {
    "name": "test_load_config_text_toml",
    "file": "tests/core/test_config.py",
    "score": 0.741
  }
]
```
**Why:** **0.759 is a very high score** - near-perfect match. Finds the exact TOML parsing functions, migration logic, and even the tests. The embedding captures the full context of configuration management.

**3. Find shell command execution:**
```bash
chop semantic search "execute shell commands and capture output"
```
**Result:**
```json
[
  {
    "name": "run_sh",
    "file": "packages/kaos/tests/test_local_kaos_sh.py",
    "score": 0.729,
    "signature": "def run_sh(command: str) -> tuple[int, str, str]"
  },
  {
    "name": "exec",
    "file": "packages/kaos/src/kaos/local.py",
    "score": 0.703
  }
]
```
**Why:** Finds `run_sh()` which returns `(returncode, stdout, stderr)` - exactly "capture output". The signature reveals the behavior even though the query didn't mention tuples or return codes.

**4. Find file writing operations:**
```bash
chop semantic search "write content to file and handle errors"
```
**Result:**
```json
[
  {
    "name": "flush_content",
    "file": "src/axe_cli/ui/shell/visualize.py",
    "score": 0.685
  },
  {
    "name": "test_write_multiline_content",
    "file": "tests/tools/test_write_file.py",
    "score": 0.682
  },
  {
    "name": "test_write_unicode_content",
    "file": "tests/tools/test_write_file.py",
    "score": 0.676
  }
]
```
**Why:** Finds file writing functions AND their edge case tests (unicode, multiline, empty, large content). The "handle errors" part is captured by finding the test suite.

**5. Find session management:**
```bash
chop semantic search "save and restore session state to disk"
```
**Result:**
```json
[
  {
    "name": "sessions_dir",
    "file": "src/axe_cli/metadata.py",
    "score": 0.651
  },
  {
    "name": "session",
    "file": "src/axe_cli/app.py",
    "score": 0.649
  }
]
```
**Why:** Lower scores (0.64-0.65) because the query is more specific than what these functions do. But it still finds the right area of code for session management.

---

**Why it works:** The embedding includes what the function does (calls), who uses it (called_by), how complex it is (CFG), and what data it transforms (DFG). Searching for "retry with backoff" finds functions that check exceptions and are called by retry loops (score: 0.71). Searching for "load TOML config" finds TOML parsing functions (score: 0.76). Searching for "execute shell commands" finds functions that return `(returncode, stdout, stderr)` tuples (score: 0.73).

### Build the Index

```bash
# One-time build (happens automatically on first use)
chop warm /path/to/project

# Query (uses daemon, ~100ms)
chop semantic search "your query here" /path/to/project
```

Results include file path, function name, line number, and similarity score.

---

## Daemon Architecture: 300x Faster

**The old way:** Every query spawns a new process, parses the entire codebase, builds indexes, returns result, exits. ~30 seconds.

**axe-dig's daemon:** Long-running background process with indexes in RAM. ~100ms.

| Method | Query Time | What Happens |
|--------|------------|--------------|
| CLI spawn | ~30 seconds | Parse entire codebase, build all indexes, analyze, return, exit |
| Daemon query | ~100ms | Read from in-memory index, return |
| **Speedup** | **300x** | Measured on 50-file Python project |

### How It Works

```bash
# First query auto-starts daemon (transparent)
chop context process_payment --project .

# Daemon stays running, subsequent queries use in-memory indexes
chop impact process_payment .     # 100ms, not 30s
chop cfg src/payment.py process_payment   # <10ms if cached
```

### Per-Project Isolation

Each project gets its own daemon via deterministic socket names:

```bash
/tmp/axe-dig-{md5(project_path)[:8]}.sock
```

Work on 5 projects simultaneously without conflicts. No cross-contamination.

### Auto-Lifecycle Management

| Event | What Happens |
|-------|--------------|
| First query | Daemon auto-starts, indexes load into RAM |
| Subsequent queries | Daemon serves from memory (~100ms) |
| File edit | Daemon detects change, incrementally updates affected indexes |
| 5min idle | Daemon auto-shuts down to save resources |
| Next query | Daemon restarts, loads from cache (still faster than parsing) |

### Daemon Commands

```bash
# Manual control (usually automatic)
chop daemon start --project .    # Start daemon
chop daemon stop --project .     # Graceful shutdown
chop daemon status --project .   # Check health

# Example output
$ chop daemon status --project .
Daemon running (PID: 52847)
Socket: /tmp/axe-dig-b3c9f2e1.sock
Uptime: 243 seconds
Files indexed: 428
Cache hits: 91.7%
Semantic index: 1,892 functions
```

### Available Commands

| Command | Purpose | Latency |
|---------|---------|---------|
| `ping` | Health check | <1ms |
| `status` | Stats (uptime, cache hits, files) | <1ms |
| `search` | Pattern search in code | ~50ms |
| `extract` | Full file analysis (AST) | ~10ms |
| `impact` | Reverse call graph | ~20ms |
| `dead` | Dead code detection | ~100ms |
| `arch` | Architecture layers | ~150ms |
| `cfg` | Control flow graph | ~15ms |
| `dfg` | Data flow graph | ~20ms |
| `slice` | Program slicing | ~30ms |
| `calls` | Cross-file call graph | ~80ms |
| `semantic` | Embedding-based search | ~100ms |
| `tree` | File tree structure | ~20ms |
| `structure` | Code structure overview | ~30ms |
| `context` | LLM-ready context | ~50ms |
| `imports` | Parse file imports | ~10ms |
| `importers` | Reverse import lookup | ~100ms |

Compare to **30 seconds** per CLI spawn.

---

## Incremental Updates: Salsa-Style Recomputation

**The insight:** When you edit one function, you don't need to re-analyze the entire codebase.

axe-dig uses **content-hash-based caching** with automatic dependency tracking:

```python
# You edit payment.py
# axe-dig invalidates:
#   - payment.py's AST cache ✓
#   - Functions that CALL payment functions ✓
#   - Call graph edges involving payment.py ✓
# axe-dig keeps:
#   - All other files' analysis ✓
#   - Unchanged functions in payment.py ✓
```

### Before/After: The `chop warm` Command

```bash
# First run: Full index build
chop warm /path/to/project
# → Parses 428 files, builds call graph (6-12 seconds)

# You edit 3 files

# Second run: Incremental update
chop warm /path/to/project
# → Re-parses 3 files, patches call graph (<1 second)
```

**Measured speedup:** 10x for incremental updates vs full rebuild.

### How Dirty Detection Works

1. Compute SHA256 hash of each file's content
2. Store in `.dig/cache/file_hashes.json`
3. On next `warm`, compare hashes
4. Re-parse only files with changed hashes
5. Update call graph edges for changed functions
6. Update semantic embeddings for changed functions

---

## Multi-Language Support

Tree-sitter parsers under the hood mean **one interface, 16 languages:**

| Language | AST | Call Graph | CFG | DFG | PDG | Semantic* |
|----------|-----|------------|-----|-----|-----|-----------|
| Python | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Full |
| TypeScript | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Full |
| JavaScript | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ Full |
| Go | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Rust | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Java | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| C | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| C++ | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Ruby | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| PHP | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| C# | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Kotlin | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Scala | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Swift | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Lua | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |
| Elixir | ✅ | ✅ | ✅ | ✅ | ✅ | ⚠️ Basic |

**\*Semantic embeddings:**
- **Full**: Embeddings include all 5 layers (signature, call graph, CFG complexity, DFG variables, dependencies)
- **Basic**: Embeddings include signature, call graph, and dependencies, but not CFG/DFG summaries

> **Note:** CLI commands (`chop cfg`, `chop dfg`, `chop slice`) work for all languages. The "Basic" limitation only affects semantic search richness.

```bash
# Same commands, different languages
chop context main --project ./go-service --lang go
chop impact handleRequest ./rust-api --lang rust
```

---

## CLI Reference

### Core Commands

```bash
# Project setup
chop warm [path]                      # Build/update all indexes (incremental)

# Structure exploration
chop tree [path]                       # File tree
chop structure [path] --lang python    # Code structure overview
chop extract <file>                    # Detailed file analysis (L1)

# Search
chop search <pattern> [path]           # Text search in code
chop semantic search <query>           # Behavioral semantic search

# LLM context
chop context <entry> --project . --depth 2  # Get LLM-ready context
```

**Real example outputs from axe-cli codebase:**

```bash
# Get token-efficient context for a function
$ chop context reset_step_count --project src/axe_cli/

## Code Context: reset_step_count (depth=2)

📍 TokenCounter.reset_step_count (token_counter.py:88)
   def reset_step_count(self) -> None
   # Reset the step counter (call at the start of each step).
   ⚡ complexity: 1 (1 blocks) 
   → calls: TokenCount

  📍 TokenCount (token_counter.py:25)
     def TokenCount() -> TokenCount
     # Token count statistics.

---
📊 2 functions | ~89 tokens
```

**Compare:** Reading the raw file would be ~4,200 tokens. axe-dig gives you the same understanding at **~89 tokens** (98% savings).

### Analysis Commands

```bash
# Call graph
chop calls [path]                      # Build cross-file call graph
chop impact <function> [path]          # Who calls this function?

# Control flow
chop cfg <file> <function>             # Control flow graph + complexity

# Data flow
chop dfg <file> <function>             # Variable definitions and uses

# Program slicing
chop slice <file> <func> <line>        # What affects this line?
```

**Real example: Impact analysis before refactoring**

```bash
# Before changing TokenCounter, see who uses it
$ chop impact TokenCounter src/axe_cli/

{
  "targets": {
    "token_counter.py:TokenCounter": {
      "function": "TokenCounter",
      "file": "token_counter.py",
      "caller_count": 1,
      "callers": [
        {
          "function": "get_global_counter",
          "file": "token_counter.py",
          "caller_count": 0,
          "callers": []
        }
      ]
    }
  }
}
```

**Result:** Safe to refactor `TokenCounter` - only used by `get_global_counter()` in the same file. No external dependencies to break.

### Codebase Analysis

```bash
chop dead [path] --entry main api      # Find unreachable code
chop arch [path]                       # Detect architecture layers
chop imports <file>                    # Parse imports from a file
chop importers <module> [path]         # Find all files that import a module
chop diagnostics <file|path>           # Type check + lint
chop change-impact [files...]          # Find tests affected by changes
chop doctor                            # Check/install diagnostic tools
```

### Daemon Management

```bash
chop daemon start --project .          # Start daemon manually
chop daemon stop --project .           # Stop daemon
chop daemon status --project .         # Check daemon health
```

---

## Performance Numbers (Measured)

### Daemon Speedup: 155x Faster

**What we measured:** Time to complete identical queries via (a) spawning `chop` CLI vs (b) querying the daemon via Unix socket.

| Command | Daemon | CLI | Speedup |
|---------|--------|-----|---------|
| `search` | 0.2ms | 72ms | **302x** |
| `extract` | 9ms | 97ms | **11x** |
| `impact` | 0.2ms | 1,129ms | **7,374x** |
| `tree` | 0.3ms | 76ms | **217x** |
| `structure` | 0.6ms | 181ms | **285x** |
| **Total** | **10ms** | **1,555ms** | **155x** |

**Why `impact` shows 7,374x speedup:** The CLI must rebuild the entire call graph from scratch on every invocation (~1.1 seconds). The daemon keeps the call graph in memory, so queries return in <1ms.

**Hardware:** MacBook Pro M1 Max, 64GB RAM
**Project:** 26 Python files, ~5,000 lines
**Protocol:** 10 iterations per query, mean ± stdev

---

### Token Savings: 89% Reduction

**What we measured:** Tokens required to understand code at different granularities, comparing raw file reads vs axe-dig structured output.

| Scenario | Raw Tokens | axe-dig Tokens | Savings |
|----------|------------|----------------|---------|
| Single file analysis | 9,114 | 7,074 | 22% |
| Function + callees | 21,271 | 175 | **99%** |
| Codebase overview (26 files) | 103,901 | 11,664 | 89% |
| Deep call chain (7 files) | 53,474 | 2,667 | 95% |
| **Total** | **187,760** | **21,580** | **89%** |

**What Each Scenario Measures:**

1. **Single file analysis (22% savings)**
   - Raw: `cat payment.py` → 9,114 tokens
   - axe-dig: `chop extract payment.py` → 7,074 tokens

2. **Function + callees (99% savings)** ← The killer feature
   - Raw: Read 3 files containing the function and everything it calls → 21,271 tokens
   - axe-dig: `chop context process_payment --depth 2` → 175 tokens
   - **Why so dramatic:** Call graph navigation goes directly to relevant code

3. **Codebase overview (89% savings)**
   - Raw: Read all 26 Python files → 103,901 tokens
   - axe-dig: `chop structure . --lang python` → 11,664 tokens

4. **Deep call chain (95% savings)**
   - Raw: Read 7 files in the call chain → 53,474 tokens
   - axe-dig: `chop context get_relevant_context --depth 3` → 2,667 tokens

**Token counter:** tiktoken with cl100k_base encoding (Claude's tokenizer)

---

### Summary

| Metric | Before axe-dig | After axe-dig | Improvement |
|--------|----------------|---------------|-------------|
| Query latency | 1.5s | 10ms | **155x faster** |
| Tokens for function context | 21K | 175 | **99% savings** |
| Tokens for codebase overview | 104K | 12K | **89% savings** |

**Cost impact:** At Claude Sonnet rates (~$3/M input tokens), saving 166K tokens per session = ~$0.50/session. Over 1,000 sessions, that's **$500 saved**.

---

## Cache Structure

axe-dig stores all indexes in `.dig/cache/`:

```
.dig/
├── daemon.pid               # Running daemon PID
├── status                   # "ready" | "indexing" | "stale"
└── cache/
    ├── call_graph.json      # Forward call edges
    ├── file_hashes.json     # Content hashes (dirty detection)
    ├── parse_cache/         # Cached AST results per file
    │   ├── src_payment.py.json
    │   └── src_db.py.json
    └── semantic/            # Embedding-based search
        ├── index.faiss      # FAISS vector index
        └── metadata.json    # Function metadata for results
```

### What's Actually Stored

**`call_graph.json`** - Cross-file function call relationships:
```json
{
  "edges": [
    {
      "from_file": "src/axe_cli/soul/axesoul.py",
      "from_func": "_make_skill_runner",
      "to_file": "packages/kosong/src/kosong/message.py",
      "to_func": "Message"
    },
    {
      "from_file": "src/axe_cli/tools/shell/__init__.py",
      "from_func": "__call__",
      "to_file": "src/axe_cli/tools/utils.py",
      "to_func": "ToolResultBuilder"
    }
  ]
}
```

This is what powers `chop impact` - instant reverse call graph lookups without re-parsing.

**`semantic/metadata.json`** - Rich function embeddings:
```json
{
  "units": [
    {
      "name": "reset_step_count",
      "qualified_name": "token_counter.py.TokenCounter.reset_step_count",
      "file": "token_counter.py",
      "line": 88,
      "unit_type": "function",
      "signature": "def reset_step_count(self) -> None",
      "docstring": "Reset the step counter (call at the start of each step).",
      "calls": ["TokenCount"],
      "called_by": [],
      "cfg_summary": "complexity:1, blocks:1",
      "dfg_summary": "vars:1, def-use chains:0",
      "dependencies": "dataclasses",
      "code_preview": "def reset_step_count(self) -> None:\n    self._step_count = TokenCount()"
    }
  ]
}
```

This metadata gets embedded into 1024-dimensional vectors for semantic search. Notice it includes:
- Call graph (what it calls, who calls it)
- Complexity metrics (CFG summary)
- Data flow (DFG summary)
- Dependencies (imports)
- Code preview (first ~10 lines)

**Why this matters:** You're not reading these files directly. The daemon loads them into RAM once, then serves queries in ~100ms. The call graph alone can be 10MB+ for large codebases, but it's instant because it's in memory.

---

## Real-World Workflows

### Debugging a Backend DB Bug

**Scenario:** Users sometimes get stale data even after updates.

```bash
# 1. Find where the error occurs
chop search "get_user" src/

# 2. Get the program slice (what code affects the return value?)
chop slice src/db.py get_user 45

# Output shows:
# 12:  cached = redis.get(f"user:{user_id}")
# 15:  if cached:
# 18:      return json.loads(cached)
# 23:  user = db.query("SELECT * FROM users WHERE id = ?", user_id)
# 34:  redis.setex(f"user:{user_id}", 3600, json.dumps(user))
# 45:  return user

# 3. Find who calls this (to see if cache is invalidated on update)
chop impact get_user src/

# 4. Search for update functions
chop semantic search "update user data in database" src/
# Finds update_user() but it doesn't call redis.delete()!

# 5. Check data flow in update_user
chop dfg src/db.py update_user
# Shows: updates DB but never invalidates cache
```

**Result:** Found the bug—cache invalidation missing in update_user(). 4 commands, 3 minutes.

---

### Before Refactoring

```bash
# 1. Understand current implementation
chop extract src/payment.py
chop cfg src/payment.py process_payment

# 2. Find all usages (impact analysis)
chop impact process_payment src/

# 3. Check architectural role
chop arch src/

# 4. Look for dead code to remove
chop dead src/ --entry main api
```

**Result:** Confidence to refactor without breaking callers.

---

### Understanding a New Codebase

```bash
# 1. Get overview
chop tree src/
chop structure src/ --lang python

# 2. Find entry points
chop arch src/  # Shows entry/middle/leaf layers

# 3. Trace from entry to implementation
chop context main --project src/ --depth 3

# 4. Find relevant code semantically
chop semantic search "payment processing and refunds" src/
```

**Before axe-dig:** Read README, grep around, read random files, build mental model over few shots.
**With axe-dig:** Structured exploration in minutes.

---

### Adding a Feature

```bash
# 1. Find similar existing code
chop semantic search "subscription billing and recurring payments" .

# 2. Understand how it works
chop context process_subscription --project . --depth 2

# 3. Check what depends on it
chop impact process_subscription .

# 4. Find where to add new code
chop arch src/  # See layer structure
```

**Result:** Implement features in the right place, following existing patterns.

---

## Why These Design Choices?

### Why Tree-sitter?

- **10-100x faster** than language-native parsers
- **Incremental parsing**: Re-parse only edited portions
- **Multi-language**: Same API for 16 languages
- **Error-tolerant**: Parses incomplete/broken code

### Why JSON Output?

- **LLM-friendly**: Can be pasted directly into prompts
- **Language-agnostic**: Works with any tooling
- **Human-readable**: Easy to debug and inspect
- **Transformable**: Pipe through `jq` for filtering

### Why Layered Architecture?

Different questions need different analysis depths:

| Question | Layer | Why |
|----------|-------|-----|
| "What functions exist?" | L1 (AST) | Fast, lightweight |
| "Who calls this?" | L2 (Call Graph) | Need cross-file analysis |
| "Is this function complex?" | L3 (CFG) | Need branching logic |
| "Where does this variable come from?" | L4 (DFG) | Need data dependencies |
| "What affects this line?" | L5 (PDG) | Need full dependency graph |

**Pay for what you need.** Don't compute PDGs when you just need function names.

### Why a Daemon?

- **Speed**: Eliminate 30s cli spawn overhead → 100ms daemon query
- **Memory efficiency**: Load indexes once, reuse for all queries
- **Caching**: Memoization persists across queries
- **Zero config**: Auto-starts, auto-stops, transparent to users

### Why Semantic Search?

Because **text search finds syntax, not behavior.**

```bash
# Text search
chop semantic search "stripe"  # Finds: comments, variable names, imports

# Semantic search
chop semantic search "charge credit cards and handle failures"
# Finds: functions that actually do payment processing
```

Embeddings encode what the function does, what it calls, who calls it, data flow patterns, and complexity. Find code by behavior, not keywords.

---

## What's Next

- **VSCode extension**: Inline axe-dig analysis while editing
- **Git integration**: Track complexity over time, highlight risky changes
- **Custom embeddings**: Fine-tune on your codebase's domain
- **Streaming daemon**: Live updates as you type
- **Multi-language call graphs**: Trace Python → TypeScript API calls


## Why "axe-dig"?

Because you need to **dig** through massive codebases with surgical precision. Not read everything. Not guess. Extract exactly what matters and move on.
## Credits & References

Special thanks to [parcadei](https://github.com/parcadei) for his work.

Built on the shoulders of giants:
- [Tree-sitter](https://tree-sitter.github.io/tree-sitter/)
- [qlty](https://github.com/qltysh/qlty) - Code quality CLI for universal linting, auto-formatting, security scanning, and maintainability
- [ast-grep](https://github.com/ast-grep/ast-grep)