# DeepAgents API Reference

> Auto-generated from `deepagents>=0.3.5` source code

The deepagents library provides a framework for building AI agents with file system access, skills, memory, and subagent capabilities built on LangChain/LangGraph.

## Table of Contents

- [Quick Start](#quick-start)
- [Core Function: `create_deep_agent`](#core-function-create_deep_agent)
- [Backends](#backends)
  - [BackendProtocol](#backendprotocol)
  - [FilesystemBackend](#filesystembackend)
  - [StateBackend](#statebackend)
  - [StoreBackend](#storebackend)
  - [CompositeBackend](#compositebackend)
- [Middleware](#middleware)
  - [FilesystemMiddleware](#filesystemmiddleware)
  - [SkillsMiddleware](#skillsmiddleware)
  - [MemoryMiddleware](#memorymiddleware)
  - [SubAgentMiddleware](#subagentmiddleware)
- [Data Types](#data-types)

---

## Quick Start

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

# Basic agent with filesystem access
agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    system_prompt="You are a helpful assistant.",
)

# Agent with custom tools and filesystem backend
backend = FilesystemBackend(root_dir="/path/to/project")
agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[my_tool_1, my_tool_2],
    backend=backend,
    skills=["/path/to/skills/"],
)

# Run the agent
result = agent.invoke({"messages": [("human", "Hello!")]})
```

---

## Core Function: `create_deep_agent`

```python
def create_deep_agent(
    model: str | BaseChatModel | None = None,
    tools: Sequence[BaseTool | Callable | dict[str, Any]] | None = None,
    *,
    system_prompt: str | None = None,
    middleware: Sequence[AgentMiddleware] = (),
    subagents: list[SubAgent | CompiledSubAgent] | None = None,
    skills: list[str] | None = None,
    memory: list[str] | None = None,
    response_format: ResponseFormat | None = None,
    context_schema: type[Any] | None = None,
    checkpointer: Checkpointer | None = None,
    store: BaseStore | None = None,
    backend: BackendProtocol | BackendFactory | None = None,
    interrupt_on: dict[str, bool | InterruptOnConfig] | None = None,
    debug: bool = False,
    name: str | None = None,
    cache: BaseCache | None = None,
) -> CompiledStateGraph
```

Creates a deep agent with built-in support for:
- **Todo list management** via `write_todos` tool
- **File operations**: `ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`
- **Shell execution**: `execute` (if backend implements `SandboxBackendProtocol`)
- **Subagent delegation** via `task` tool

### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `model` | `str \| BaseChatModel \| None` | Model to use. Defaults to `claude-sonnet-4-5-20250929`. Can be a model name string or instance. |
| `tools` | `Sequence[BaseTool \| Callable \| dict]` | Custom tools for the agent to use. |
| `system_prompt` | `str \| None` | Additional instructions for the agent. Added to system prompt. |
| `middleware` | `Sequence[AgentMiddleware]` | Additional middleware to apply after standard middleware. |
| `subagents` | `list[SubAgent \| CompiledSubAgent]` | Custom subagents available via the `task` tool. |
| `skills` | `list[str]` | Paths to skill directories (e.g., `["/skills/user/", "/skills/project/"]`). |
| `memory` | `list[str]` | Paths to AGENTS.md memory files to load at startup. |
| `backend` | `BackendProtocol \| BackendFactory` | Backend for file storage. Defaults to `StateBackend`. |
| `interrupt_on` | `dict[str, bool \| InterruptOnConfig]` | Tool names to interrupt on for human-in-the-loop. |
| `checkpointer` | `Checkpointer` | For persisting agent state between runs. |
| `store` | `BaseStore` | For persistent storage (required for `StoreBackend`). |

### Returns

`CompiledStateGraph` - A configured LangGraph agent ready for `.invoke()` or `.ainvoke()`.

### Example

```python
from deepagents import create_deep_agent
from deepagents.backends import FilesystemBackend

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[search_tool, calculator_tool],
    system_prompt="You are a research assistant.",
    backend=FilesystemBackend(root_dir="/workspace"),
    skills=[".deepagents/skills/"],
    memory=["~/.deepagents/AGENTS.md"],
)

# Invoke synchronously
result = agent.invoke({"messages": [("human", "Research quantum computing")]})

# Invoke asynchronously
result = await agent.ainvoke({"messages": [("human", "Research quantum computing")]})
```

---

## Backends

Backends provide pluggable file storage for agents. All backends implement `BackendProtocol`.

### BackendProtocol

Abstract base class defining the file operations interface.

```python
class BackendProtocol(ABC):
    """Protocol for pluggable memory backends."""

    def ls_info(self, path: str) -> list[FileInfo]: ...
    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> str: ...
    def write(self, file_path: str, content: str) -> WriteResult: ...
    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult: ...
    def grep_raw(self, pattern: str, path: str | None = None, glob: str | None = None) -> list[GrepMatch] | str: ...
    def glob_info(self, pattern: str, path: str = "/") -> list[FileInfo]: ...
    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]: ...
    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]: ...

    # Async versions also available (als_info, aread, awrite, etc.)
```

### SandboxBackendProtocol

Extended protocol for backends that support command execution:

```python
class SandboxBackendProtocol(BackendProtocol):
    """Protocol for sandboxed backends with isolated runtime."""

    def execute(self, command: str) -> ExecuteResponse: ...
    async def aexecute(self, command: str) -> ExecuteResponse: ...

    @property
    def id(self) -> str: ...
```

---

### FilesystemBackend

Reads and writes files directly from the local filesystem.

```python
from deepagents.backends import FilesystemBackend

backend = FilesystemBackend(
    root_dir="/path/to/project",  # Base directory (default: cwd)
    virtual_mode=False,           # If True, treats paths as virtual under root_dir
    max_file_size_mb=10,          # Max file size for grep operations
)
```

**Key Features:**
- Direct filesystem access with actual paths
- Security: O_NOFOLLOW to prevent symlink attacks
- Ripgrep-powered grep with Python fallback
- Path containment in virtual_mode

**When to Use:**
- Local development environments
- When agent needs access to real filesystem
- Projects with existing file structures

### StateBackend

Stores files in LangGraph agent state (ephemeral, in-memory).

```python
from deepagents.backends import StateBackend

# Usually created via factory for runtime access
backend_factory = lambda rt: StateBackend(rt)

agent = create_deep_agent(
    backend=backend_factory,  # Pass factory, not instance
)
```

**Key Features:**
- Files persist within a conversation thread
- Automatically checkpointed after each agent step
- No filesystem access required

**When to Use:**
- Sandbox/isolated environments
- Testing and development
- When files should not persist across sessions

### StoreBackend

Stores files in LangGraph's BaseStore (persistent, cross-thread).

```python
from deepagents.backends import StoreBackend
from langgraph.store.memory import MemoryStore

store = MemoryStore()  # Or PostgresStore, etc.

# Created via factory
backend_factory = lambda rt: StoreBackend(rt)

agent = create_deep_agent(
    backend=backend_factory,
    store=store,
)
```

**Key Features:**
- Persistent storage across conversations
- Namespace-based organization
- Optional assistant_id isolation for multi-agent setups

**When to Use:**
- Long-term memory storage
- Cross-session file persistence
- Multi-agent deployments

### CompositeBackend

Routes file operations to different backends by path prefix.

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

runtime = make_runtime()  # Your runtime setup

composite = CompositeBackend(
    default=StateBackend(runtime),  # Fallback for unmatched paths
    routes={
        "/memories/": StoreBackend(runtime),  # Persistent storage
        "/cache/": StateBackend(runtime),     # Ephemeral cache
    },
)

# Routes automatically by path
composite.write("/temp.txt", "ephemeral")          # -> StateBackend
composite.write("/memories/notes.md", "persistent") # -> StoreBackend
```

**Key Features:**
- Longest-prefix matching for routes
- Aggregates results from multiple backends for ls/grep/glob
- Execution delegated to default backend

**When to Use:**
- Hybrid storage strategies
- Different persistence for different file types
- Memory systems with ephemeral scratch space

---

## Middleware

Middleware extends agent capabilities by modifying requests, responses, and providing additional tools.

### FilesystemMiddleware

Provides filesystem tools (`ls`, `read_file`, `write_file`, `edit_file`, `glob`, `grep`, `execute`).

```python
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import FilesystemBackend

middleware = FilesystemMiddleware(
    backend=FilesystemBackend(root_dir="/workspace"),
    system_prompt=None,  # Custom system prompt (optional)
    custom_tool_descriptions=None,  # Override tool descriptions
    tool_token_limit_before_evict=20000,  # Auto-evict large results
)
```

**Tools Provided:**

| Tool | Description |
|------|-------------|
| `ls` | List files in a directory |
| `read_file` | Read file with pagination (offset/limit) |
| `write_file` | Create new file |
| `edit_file` | String replacement in existing files |
| `glob` | Find files by pattern (`**/*.py`) |
| `grep` | Search file contents |
| `execute` | Run shell commands (if backend supports) |

**Note:** `create_deep_agent` automatically includes `FilesystemMiddleware`.

### SkillsMiddleware

Loads and exposes agent skills using progressive disclosure.

```python
from deepagents.middleware import SkillsMiddleware
from deepagents.backends import FilesystemBackend

middleware = SkillsMiddleware(
    backend=FilesystemBackend(root_dir="/project"),
    sources=[
        "/skills/base/",     # Base skills (lowest priority)
        "/skills/user/",     # User skills
        "/skills/project/",  # Project skills (highest priority)
    ],
)
```

**Skill Structure:**

```
/skills/project/
├── web-research/
│   ├── SKILL.md          # Required: YAML frontmatter + instructions
│   └── helper.py         # Optional: supporting files
└── data-analysis/
    └── SKILL.md
```

**SKILL.md Format:**

```markdown
---
name: web-research
description: Structured approach to conducting thorough web research
license: MIT
---

# Web Research Skill

## When to Use
- User asks to research a topic
- Information gathering required

## Steps
1. Search for relevant sources
2. ...
```

**Skill Metadata (from YAML frontmatter):**

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Identifier (max 64 chars, lowercase alphanumeric + hyphens) |
| `description` | Yes | What the skill does (max 1024 chars) |
| `license` | No | License name |
| `compatibility` | No | Environment requirements |
| `metadata` | No | Arbitrary key-value pairs |
| `allowed-tools` | No | Space-delimited pre-approved tools |

### MemoryMiddleware

Loads agent memory/context from AGENTS.md files.

```python
from deepagents.middleware import MemoryMiddleware
from deepagents.backends import FilesystemBackend

middleware = MemoryMiddleware(
    backend=FilesystemBackend(root_dir="/"),
    sources=[
        "~/.deepagents/AGENTS.md",      # User-level memory
        "./.deepagents/AGENTS.md",      # Project-level memory
    ],
)
```

**Features:**
- Loads AGENTS.md files at agent startup
- Injects into system prompt
- Agent can update memory via `edit_file` tool
- Supports learning from user feedback

**When to Update Memory:**
- User explicitly asks to remember something
- User provides identity/role information
- User gives feedback on agent's work
- Patterns or preferences discovered

**AGENTS.md Format:**

Standard Markdown with no required structure. Common sections:
- Project overview
- Build/test commands
- Code style guidelines
- Architecture notes

### SubAgentMiddleware

Provides the `task` tool for delegating to specialized subagents.

```python
from deepagents.middleware import SubAgentMiddleware
from deepagents import SubAgent

# Define custom subagents
code_reviewer = SubAgent(
    name="code-reviewer",
    description="Reviews code for quality and best practices",
    system_prompt="You are an expert code reviewer...",
    tools=[review_tool],
)

middleware = SubAgentMiddleware(
    default_model="claude-sonnet-4-5-20250929",
    default_tools=[],
    subagents=[code_reviewer],
    general_purpose_agent=True,  # Include default general-purpose agent
)
```

**SubAgent TypedDict:**

```python
class SubAgent(TypedDict):
    name: str                    # Agent identifier
    description: str             # Used to decide when to call
    system_prompt: str           # Agent's system prompt
    tools: Sequence[BaseTool]    # Agent's tools
    model: NotRequired[str | BaseChatModel]  # Optional model override
    middleware: NotRequired[list[AgentMiddleware]]  # Additional middleware
```

**CompiledSubAgent TypedDict:**

For pre-compiled agents:

```python
class CompiledSubAgent(TypedDict):
    name: str           # Agent identifier
    description: str    # Description for routing
    runnable: Runnable  # Pre-compiled agent runnable
```

---

## Data Types

### FileInfo

```python
class FileInfo(TypedDict):
    path: str                      # Absolute file path
    is_dir: NotRequired[bool]      # True if directory
    size: NotRequired[int]         # Size in bytes
    modified_at: NotRequired[str]  # ISO timestamp
```

### GrepMatch

```python
class GrepMatch(TypedDict):
    path: str   # Absolute file path
    line: int   # Line number (1-indexed)
    text: str   # Matching line content
```

### WriteResult

```python
@dataclass
class WriteResult:
    error: str | None = None                    # Error message on failure
    path: str | None = None                     # Path of written file
    files_update: dict[str, Any] | None = None  # State update for checkpoint backends
```

### EditResult

```python
@dataclass
class EditResult:
    error: str | None = None                    # Error message on failure
    path: str | None = None                     # Path of edited file
    files_update: dict[str, Any] | None = None  # State update for checkpoint backends
    occurrences: int | None = None              # Number of replacements made
```

### ExecuteResponse

```python
@dataclass
class ExecuteResponse:
    output: str                    # Combined stdout/stderr
    exit_code: int | None = None   # Process exit code (0 = success)
    truncated: bool = False        # Whether output was truncated
```

### FileUploadResponse / FileDownloadResponse

```python
@dataclass
class FileUploadResponse:
    path: str
    error: FileOperationError | None = None

@dataclass
class FileDownloadResponse:
    path: str
    content: bytes | None = None
    error: FileOperationError | None = None

FileOperationError = Literal[
    "file_not_found",
    "permission_denied",
    "is_directory",
    "invalid_path",
]
```

### SkillMetadata

```python
class SkillMetadata(TypedDict):
    name: str                     # Skill identifier
    description: str              # What the skill does
    path: str                     # Path to SKILL.md
    license: str | None           # License name
    compatibility: str | None     # Environment requirements
    metadata: dict[str, str]      # Arbitrary key-value pairs
    allowed_tools: list[str]      # Pre-approved tools
```

---

## Public Exports

From `deepagents`:
- `create_deep_agent`
- `FilesystemMiddleware`
- `MemoryMiddleware`
- `SubAgent`
- `SubAgentMiddleware`
- `CompiledSubAgent`

From `deepagents.backends`:
- `BackendProtocol`
- `FilesystemBackend`
- `StateBackend`
- `StoreBackend`
- `CompositeBackend`

From `deepagents.middleware`:
- `FilesystemMiddleware`
- `MemoryMiddleware`
- `SkillsMiddleware`
- `SubAgentMiddleware`
- `SubAgent`
- `CompiledSubAgent`
