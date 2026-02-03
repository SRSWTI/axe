from __future__ import annotations


class AxeCLIException(Exception):
    """Base exception class for Axe Code CLI."""

    pass


class ConfigError(AxeCLIException, ValueError):
    """Configuration error."""

    pass


class AgentSpecError(AxeCLIException, ValueError):
    """Agent specification error."""

    pass


class InvalidToolError(AxeCLIException, ValueError):
    """Invalid tool error."""

    pass


class MCPConfigError(AxeCLIException, ValueError):
    """MCP config error."""

    pass


class MCPRuntimeError(AxeCLIException, RuntimeError):
    """MCP runtime error."""

    pass
