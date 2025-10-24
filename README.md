# BSL MCP Server (Python)

MCP server for integrating BSL Language Server with Model Context Protocol, providing analysis and formatting capabilities for 1C files (*.bsl, *.os).

## Features

- **BSL Analysis**: Run comprehensive analysis on BSL/OS files with detailed diagnostics
- **Code Formatting**: Format BSL files according to BSL Language Server rules
- **Flexible Input**: Support for single files or entire directories
- **Multiple Output Formats**: Both human-readable summaries and structured JSON
- **Configurable**: Customizable JVM memory limits and configuration files

## Installation

### Prerequisites

- Python 3.10 or higher
- Java Runtime Environment (JRE) 8 or higher
- BSL Language Server JAR file

### Install from Source

1. Clone the repository:
```bash
git clone <repository-url>
cd mcp-bsl-python
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Install the package:
```bash
pip install -e .
```

## Configuration

### Environment Variables

Set the following environment variable:

```bash
export BSL_JAR="/path/to/bsl-language-server-0.24.2-exec.jar"
```

Optional environment variables:
```bash
export BSL_MEMORY_MB="4096"    # JVM memory limit in MB (default: 4096)
export BSL_LOG_LEVEL="ERROR"   # Logging level: ERROR, WARNING, INFO, DEBUG (default: WARNING)
```

### MCP Configuration

Add to your `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "bsl-mcp": {
      "command": "python",
      "args": ["-m", "mcp_bsl.server"],
      "env": {
        "BSL_JAR": "C:\\1C\\AI\\bsl\\bsl-language-server-0.24.2-exec.jar",
        "BSL_MEMORY_MB": "4096",
        "BSL_CONFIG": "C:\\1C\\AI\\bsl\\.bsl-language-server.json",
        "BSL_LOG_LEVEL": "ERROR"
      },
      "debug": false
    }
  }
}
```

> **Note:** `BSL_LOG_LEVEL` is set to `ERROR` to minimize log output in Cursor IDE. Use `DEBUG` for troubleshooting.

## Usage

### Available Tools

#### `bsl_analyze`

Run BSL analysis on source directory or file.

**Parameters:**
- `srcDir` (required): Path to directory or file with .bsl/.os files
- `configPath` (optional): Path to .bsl-language-server.json configuration file
- `memoryMb` (optional): JVM memory limit in MB (default: 4096)

**Example:**
```json
{
  "name": "bsl_analyze",
  "arguments": {
    "srcDir": "C:\\1C\\MyProject\\src"
  }
}
```

#### `bsl_format`

Format BSL files in source directory.

**Parameters:**
- `srcDir` (required): Path to directory or file with .bsl/.os files

**Example:**
```json
{
  "name": "bsl_format",
  "arguments": {
    "srcDir": "C:\\1C\\MyProject\\src"
  }
}
```

### Output Formats

#### Analysis Results

The `bsl_analyze` tool provides:

1. **Human-readable summary** with:
   - Status (success/error)
   - Number of files processed
   - Diagnostic counts by severity
   - Top issues with file locations

2. **Structured JSON output** with:
   - Complete diagnostic information
   - File paths, line/column numbers
   - Severity levels and messages
   - Summary statistics

#### Formatting Results

The `bsl_format` tool provides:
- Success/failure status
- Number of files processed
- Raw output from BSL Language Server

## BSL Language Server Configuration

Create a `.bsl-language-server.json` file in your project root:

```json
{
  "language": "bsl",
  "diagnostics": {
    "computeTrigger": "onSave",
    "skipSupport": "never"
  },
  "codeLens": {
    "showCognitiveComplexity": true,
    "showCyclomaticComplexity": true
  },
  "traceLog": {
    "enabled": false
  }
}
```

## Error Handling

The server handles various error conditions:

- **File not found**: Validates source paths before execution
- **Invalid JAR**: Checks BSL Language Server JAR file existence
- **Timeout**: 5-minute timeout for analysis, 2-minute for formatting
- **Memory limits**: Configurable JVM memory allocation
- **Parse errors**: Graceful handling of malformed BSL output

## Development

### Project Structure

```
mcp-bsl-python/
├── pyproject.toml          # Project metadata and dependencies
├── requirements.txt        # Dependencies
├── README.md              # This file
├── src/
│   └── mcp_bsl/
│       ├── __init__.py
│       ├── server.py      # Main MCP server implementation
│       ├── bsl_runner.py  # BSL jar execution wrapper
│       └── config.py      # Configuration management
└── .bsl-language-server.json  # Example BSL config
```

### Running Tests

```bash
python -m pytest tests/
```

### Building

```bash
python -m build
```

## Troubleshooting

### Common Issues

1. **"BSL_JAR environment variable is required"**
   - Set the `BSL_JAR` environment variable to the correct path
   - Ensure the JAR file exists and is readable

2. **"Source path does not exist"**
   - **Always use absolute paths** (e.g., `C:\dev\project\src\Module.bsl`)
   - Relative paths may not work correctly with MCP server
   - See [PATH_USAGE_GUIDE.md](PATH_USAGE_GUIDE.md) for detailed path usage instructions
   - Verify the `srcDir` parameter points to an existing file or directory
   - Check file permissions

3. **"Directory contains no BSL/OS files"**
   - Ensure the directory contains `.bsl` or `.os` files
   - Check file extensions are correct

4. **Java execution errors**
   - Verify Java is installed and accessible in PATH
   - Check JVM memory limits are reasonable
   - Ensure BSL Language Server JAR is compatible with your Java version

5. **Seeing "ERROR: BSL analysis stderr detected"**
   - This was fixed - progress bar output is now filtered out
   - Only real errors are shown
   - Update to the latest version if you see this issue

6. **Log messages appearing twice**
   - This was fixed - duplicate handler accumulation resolved
   - Each log message now appears exactly once
   - See [FIX_DUPLICATE_LOGS.md](FIX_DUPLICATE_LOGS.md) for details

### Debug Mode and Logging

The server supports different logging levels controlled via the `BSL_LOG_LEVEL` environment variable:

- **ERROR** (recommended for production) - Only critical errors
- **WARNING** (default) - Warnings and errors
- **INFO** - Informational messages
- **DEBUG** - Detailed debug information

To enable debug logging in MCP configuration:
```json
{
  "mcpServers": {
    "bsl-mcp": {
      "env": {
        "BSL_LOG_LEVEL": "DEBUG"
      }
    }
  }
}
```

For more details, see [LOGGING_CONFIGURATION.md](LOGGING_CONFIGURATION.md).

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

For issues and questions:
- Create an issue in the repository
- Check existing documentation
- Review BSL Language Server documentation
