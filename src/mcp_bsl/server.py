"""MCP server for BSL Language Server integration."""

import asyncio
import json
import logging
import sys
from typing import Any, Dict, List, Optional
from pathlib import Path

from mcp.server import Server
from mcp.server.models import InitializationOptions, ServerCapabilities
from mcp.server.stdio import stdio_server
from mcp.types import (
    ListToolsResult,
    Tool,
    TextContent,
    ToolsCapability,
)

from .config import get_config
from .bsl_runner import BSLRunner, BSLResult


class BSLMCPServer:
    """MCP server for BSL Language Server integration."""
    
    def __init__(self):
        self.server = Server("bsl-lint")
        self.config = None
        self.runner = None
        self.logger = self._setup_logger()
        self._setup_handlers()
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for debugging."""
        import os
        
        logger = logging.getLogger("bsl-mcp-server")
        
        # Get log level from environment variable, default to WARNING
        # This prevents debug spam in Cursor UI
        log_level_name = os.environ.get("BSL_LOG_LEVEL", "WARNING").upper()
        log_level = getattr(logging, log_level_name, logging.WARNING)
        logger.setLevel(log_level)
        
        # Prevent propagation to parent loggers to avoid duplicate logs
        logger.propagate = False
        
        # Clear existing handlers to prevent duplicate logging
        # This is important because the logger is global and handlers accumulate
        if logger.handlers:
            logger.handlers.clear()
        
        # Only add handler if logger doesn't have any handlers
        # This prevents duplication when logger is reused
        if not logger.handlers:
            # Create console handler
            handler = logging.StreamHandler(sys.stderr)
            handler.setLevel(log_level)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            
            # Add handler to logger
            logger.addHandler(handler)
        
        return logger
    
    def _setup_handlers(self):
        """Setup MCP server handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> ListToolsResult:
            """List available tools."""
            self.logger.info("Listing available tools")
            return ListToolsResult(
                tools=[
                    Tool(
                        name="bsl_analyze",
                        description="Run BSL analysis on source directory or file",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "srcDir": {
                                    "type": "string",
                                    "description": "Path to directory or file with .bsl/.os files"
                                }
                            },
                            "required": ["srcDir"]
                        }
                    ),
                    Tool(
                        name="bsl_format",
                        description="Format BSL files in source directory",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "srcDir": {
                                    "type": "string",
                                    "description": "Path to directory or file with .bsl/.os files"
                                }
                            },
                            "required": ["srcDir"]
                        }
                    ),
                    Tool(
                        name="check_syntax",
                        description="Run syntax check using vanessa-runner",
                        inputSchema={
                            "type": "object",
                            "properties": {
                                "ibConnection": {
                                    "type": "string",
                                    "description": "Connection string to 1C infobase (e.g., '/F/path/to/base' or '/Sserver/base')"
                                },
                                "dbUser": {
                                    "type": "string",
                                    "description": "Database user (optional)"
                                },
                                "dbPwd": {
                                    "type": "string",
                                    "description": "Database password (optional)"
                                },
                                "groupbymetadata": {
                                    "type": "boolean",
                                    "description": "Group results by metadata (default: true)"
                                },
                                "junitpath": {
                                    "type": "string",
                                    "description": "Path to save JUnit report (optional)"
                                }
                            },
                            "required": ["ibConnection"]
                        }
                    )
                ]
            )
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]):
            """Handle tool calls."""
            self.logger.info(f"Handling tool call: {name} with arguments: {arguments}")
            try:
                # Initialize config and runner if not done yet
                if self.config is None:
                    self.logger.debug("Initializing config and runner")
                    self.config = get_config()
                    self.runner = BSLRunner(self.config)
                
                if name == "bsl_analyze":
                    self.logger.debug("Calling bsl_analyze handler")
                    return await self._handle_analyze(arguments)
                elif name == "bsl_format":
                    self.logger.debug("Calling bsl_format handler")
                    return await self._handle_format(arguments)
                elif name == "check_syntax":
                    self.logger.debug("Calling check_syntax handler")
                    return await self._handle_check_syntax(arguments)
                else:
                    self.logger.warning(f"Unknown tool requested: {name}")
                    return [TextContent(type="text", text=f"Unknown tool: {name}")]
                    
            except Exception as e:
                self.logger.error(f"Error handling tool call {name}: {str(e)}", exc_info=True)
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    async def _handle_analyze(self, arguments: Dict[str, Any]):
        """Handle bsl_analyze tool call."""
        src_dir = arguments.get("srcDir")
        
        # Get config_path from BSL_CONFIG environment variable via config
        config_path = self.config.config_path
        memory_mb = self.config.default_memory_mb
        
        self.logger.info(f"Starting BSL analysis for directory: {src_dir}")
        self.logger.debug(f"Analysis parameters - config: {config_path}, memory: {memory_mb}MB")
        
        if not src_dir:
            self.logger.error("srcDir parameter is required but not provided")
            return [TextContent(type="text", text="Error: srcDir parameter is required")]
        
        # If src_dir is a file, use its parent directory instead
        path = Path(src_dir)
        if path.exists() and path.is_file():
            self.logger.info(f"srcDir is a file: {src_dir}. Using parent directory instead.")
            src_dir = str(path.parent)
            self.logger.info(f"Analyzing parent directory: {src_dir}")
        
        # Run analysis in thread pool to avoid blocking
        self.logger.debug("Running analysis in thread pool")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, 
            self.runner.analyze, 
            src_dir,
            config_path, 
            memory_mb
        )
        
        self.logger.info(f"Analysis completed. Success: {result.success}, Files processed: {result.files_processed}")
        return self._format_analyze_result(result)
    
    async def _handle_format(self, arguments: Dict[str, Any]):
        """Handle bsl_format tool call."""
        src_dir = arguments.get("srcDir")

        self.logger.info(f"Starting BSL formatting for directory: {src_dir}")

        if not src_dir:
            self.logger.error("srcDir parameter is required but not provided")
            return [TextContent(type="text", text="Error: srcDir parameter is required")]

        # If src_dir is a file, use its parent directory instead
        path = Path(src_dir)
        if path.exists() and path.is_file():
            self.logger.info(f"srcDir is a file: {src_dir}. Using parent directory instead.")
            src_dir = str(path.parent)
            self.logger.info(f"Formatting parent directory: {src_dir}")

        # Run formatting in thread pool to avoid blocking
        self.logger.debug("Running formatting in thread pool")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self.runner.format, src_dir)

        self.logger.info(f"Formatting completed. Success: {result.success}, Files processed: {result.files_processed}")
        return self._format_format_result(result)

    async def _handle_check_syntax(self, arguments: Dict[str, Any]):
        """Handle check_syntax tool call."""
        ib_connection = arguments.get("ibConnection")
        db_user = arguments.get("dbUser")
        db_pwd = arguments.get("dbPwd")
        groupbymetadata = arguments.get("groupbymetadata", True)
        junitpath = arguments.get("junitpath")

        self.logger.info(f"Starting syntax check for infobase: {ib_connection}")

        if not ib_connection:
            self.logger.error("ibConnection parameter is required but not provided")
            return [TextContent(type="text", text="Error: ibConnection parameter is required")]

        # Run syntax check in thread pool to avoid blocking
        self.logger.debug("Running syntax check in thread pool")
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self.runner.check_syntax,
            ib_connection,
            db_user,
            db_pwd,
            groupbymetadata,
            junitpath
        )

        self.logger.info(f"Syntax check completed. Success: {result.success}, Diagnostics: {len(result.diagnostics)}")
        return self._format_check_syntax_result(result)
    
    def _format_analyze_result(self, result: BSLResult):
        """Format analysis result for MCP response."""
        if result.success:
            status = "✅ Analysis completed successfully"
        else:
            status = "❌ Analysis completed with errors"
        
        # Create summary
        summary_lines = [
            f"## BSL Analysis Results",
            f"**Status:** {status}",
            f"**Files processed:** {result.files_processed}",
            f"**Total diagnostics:** {len(result.diagnostics)}",
            ""
        ]
        
        # Group diagnostics by severity
        errors = [d for d in result.diagnostics if d.severity == 'error']
        warnings = [d for d in result.diagnostics if d.severity == 'warning']
        infos = [d for d in result.diagnostics if d.severity == 'info']
        
        if errors:
            summary_lines.extend([
                f"**Errors:** {len(errors)}",
                ""
            ])
            for diag in errors:  # Show ALL errors
                summary_lines.append(f"🔴 **{diag.file}:{diag.line}:{diag.column}** - [{diag.code}] {diag.message}")
            summary_lines.append("")
        
        if warnings:
            summary_lines.extend([
                f"**Warnings:** {len(warnings)}",
                ""
            ])
            for diag in warnings:  # Show ALL warnings
                summary_lines.append(f"🟡 **{diag.file}:{diag.line}:{diag.column}** - [{diag.code}] {diag.message}")
            summary_lines.append("")
        
        if infos:
            summary_lines.extend([
                f"**Info messages:** {len(infos)}",
                ""
            ])
            for diag in infos:  # Show ALL info messages
                summary_lines.append(f"ℹ️ **{diag.file}:{diag.line}:{diag.column}** - [{diag.code}] {diag.message}")
            summary_lines.append("")
        
        # Add full BSL JSON output
        if result.output and result.output.strip():
            summary_lines.extend([
                "",
                "## Full BSL JSON Output",
                "```json",
                result.output,
                "```"
            ])
        
        # Add error output if there are issues
        if result.error:
            summary_lines.extend([
                "",
                "## BSL Server Logs (STDERR)",
                "```",
                result.error[:2000] if len(result.error) > 2000 else result.error,  # Limit stderr length
                "```" + (f"\n... and {len(result.error) - 2000} more characters" if len(result.error) > 2000 else "")
            ])
        
        return [TextContent(type="text", text="\n".join(summary_lines))]
    
    def _format_format_result(self, result: BSLResult):
        """Format formatting result for MCP response."""
        if result.success:
            status = "✅ Formatting completed successfully"
            message = f"Successfully formatted {result.files_processed} files"
        else:
            status = "❌ Formatting failed"
            message = f"Failed to format files. Error: {result.error}"

        output_lines = [
            f"## BSL Formatting Results",
            f"**Status:** {status}",
            f"**Message:** {message}",
            f"**Files processed:** {result.files_processed}",
            ""
        ]

        if result.output:
            output_lines.extend([
                "## Output",
                "```",
                result.output,
                "```"
            ])

        if result.error:
            output_lines.extend([
                "## Error Output",
                "```",
                result.error,
                "```"
            ])

        return [TextContent(type="text", text="\n".join(output_lines))]

    def _format_check_syntax_result(self, result: BSLResult):
        """Format syntax check result for MCP response."""
        if result.success:
            status = "✅ Syntax check completed successfully"
        else:
            status = "❌ Syntax check completed with errors"

        # Create summary
        summary_lines = [
            f"## Syntax Check Results",
            f"**Status:** {status}",
            f"**Total diagnostics:** {len(result.diagnostics)}",
            ""
        ]

        # Group diagnostics by severity
        errors = [d for d in result.diagnostics if d.severity == 'error']
        warnings = [d for d in result.diagnostics if d.severity == 'warning']
        infos = [d for d in result.diagnostics if d.severity == 'info']

        if errors:
            summary_lines.extend([
                f"**Errors:** {len(errors)}",
                ""
            ])
            for diag in errors:
                if diag.file:
                    summary_lines.append(f"🔴 **{diag.file}:{diag.line}:{diag.column}** - {diag.message}")
                else:
                    summary_lines.append(f"🔴 {diag.message}")
            summary_lines.append("")

        if warnings:
            summary_lines.extend([
                f"**Warnings:** {len(warnings)}",
                ""
            ])
            for diag in warnings:
                if diag.file:
                    summary_lines.append(f"🟡 **{diag.file}:{diag.line}:{diag.column}** - {diag.message}")
                else:
                    summary_lines.append(f"🟡 {diag.message}")
            summary_lines.append("")

        if infos:
            summary_lines.extend([
                f"**Info messages:** {len(infos)}",
                ""
            ])
            for diag in infos:
                if diag.file:
                    summary_lines.append(f"ℹ️ **{diag.file}:{diag.line}:{diag.column}** - {diag.message}")
                else:
                    summary_lines.append(f"ℹ️ {diag.message}")
            summary_lines.append("")

        # Add full output
        if result.output and result.output.strip():
            summary_lines.extend([
                "",
                "## Full Output",
                "```",
                result.output[:5000] if len(result.output) > 5000 else result.output,
                "```" + (f"\n... and {len(result.output) - 5000} more characters" if len(result.output) > 5000 else "")
            ])

        # Add error output if there are issues
        if result.error and result.error.strip():
            summary_lines.extend([
                "",
                "## Error Output",
                "```",
                result.error[:2000] if len(result.error) > 2000 else result.error,
                "```" + (f"\n... and {len(result.error) - 2000} more characters" if len(result.error) > 2000 else "")
            ])

        return [TextContent(type="text", text="\n".join(summary_lines))]
    
    async def run(self):
        """Run the MCP server."""
        self.logger.info("Starting BSL MCP server")
        async with stdio_server() as (read_stream, write_stream):
            self.logger.debug("Server streams initialized, starting server")
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="bsl-lint",
                    server_version="0.1.0",
                    capabilities=ServerCapabilities(
                        tools=ToolsCapability()
                    )
                )
            )


def main():
    """Main entry point."""
    server = BSLMCPServer()
    try:
        server.logger.info("Starting MCP server main loop")
        asyncio.run(server.run())
    except KeyboardInterrupt:
        server.logger.info("Server interrupted by user")
        sys.exit(0)
    except Exception as e:
        import traceback
        server.logger.error(f"Server error: {e}", exc_info=True)
        print(f"Server error: {e}", file=sys.stderr)
        print(f"Traceback: {traceback.format_exc()}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()