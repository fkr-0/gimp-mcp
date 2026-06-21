# Docstring Style

This project uses Google-style docstrings because they render cleanly with `mkdocstrings[python]` and remain readable inside MCP tool descriptions.

## Rules

```yaml
style: google
renderer: mkdocstrings-python
enforced_for:
  - nested MCP tool handlers extracted by scripts/docs.py
  - public Python API objects rendered by mkdocstrings
required_tool_sections:
  - one-sentence imperative summary
  - Args when a tool exposes parameters
  - Returns for every tool
allowed_operational_sections:
  - Notes
  - Warnings
  - Examples
forbidden_legacy_sections:
  - WHEN TO USE
  - BEST PRACTICE
  - PRIMARY USE
  - IMPORTANT
  - WARNING
  - COMBINES WITH
  - NOTE
```

## Tool docstring template

```python
async def example_tool(value: int, label: str | None = None) -> dict[str, Any]:
    """Apply the example operation to the active image.

    Notes:
        Use this tool when an assistant needs a small, deterministic editing
        step that should be visible in the generated tool reference.

    Args:
        value: Strength of the operation in project-specific units.
        label: Optional label used in result metadata.

    Returns:
        Operation result dictionary with status, message, and tool-specific
        data or error details.
    """
```

## Public API docstring template

```python
def load_contract(path: Path) -> dict[str, Any]:
    """Load a compatibility contract from YAML.

    Args:
        path: Path to the contract file.

    Returns:
        Parsed YAML mapping.

    Raises:
        ValueError: Raised when the file does not contain a top-level mapping.
    """
```

## Public API focus

Mkdocstrings pages should explain constructor parameters, return envelopes, and
raised project exceptions for bridge/configuration APIs. Short one-line
docstrings are acceptable for trivial aliases, but transport methods and public
protocol types should document:

```yaml
public_api_sections:
  constructors: [Args, Examples]
  command_methods: [Args, Returns, Raises]
  protocol_types: [Attributes]
  trivial_properties: [Returns]
```

This keeps generated API pages useful for maintainers who are wiring live GIMP
3.2.4 verification or adding new MCP tool modules.

## Why this policy exists

The MCP tool functions are nested inside `register_*_tools()` helpers, so normal mkdocstrings discovery cannot document them directly. `scripts/docs.py` extracts them with `ast`, checks their Google-style shape, and generates deterministic pages under `docs/tools/`.

For operational guidance, use `Notes:` and `Warnings:` instead of uppercase ad-hoc headings. Those sections are understood by mkdocstrings and keep the generated pages consistent.
