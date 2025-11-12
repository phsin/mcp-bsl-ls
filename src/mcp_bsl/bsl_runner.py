"""BSL Language Server execution wrapper."""

import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .config import BSLConfig, validate_source_path, validate_config_path


@dataclass
class BSLDiagnostic:
    """Represents a BSL diagnostic message."""
    file: str
    line: int
    column: int
    severity: str  # error, warning, info
    message: str
    code: Optional[str] = None


@dataclass
class BSLResult:
    """Result of BSL operation."""
    success: bool
    diagnostics: List[BSLDiagnostic]
    output: str
    error: str
    files_processed: int = 0


class BSLRunner:
    """Executes BSL Language Server commands."""
    
    def __init__(self, config: BSLConfig):
        self.config = config
        self.logger = logging.getLogger("bsl-mcp-server")
        self._temp_config_file = None
    
    def analyze(self, 
                src_dir: str, 
                config_path: Optional[str] = None,
                memory_mb: Optional[int] = None) -> BSLResult:
        """
        Run BSL analysis on source directory or file.
        
        Args:
            src_dir: Path to directory or file with .bsl/.os files
            config_path: Optional path to .bsl-language-server.json
            memory_mb: Optional JVM memory limit
            
        Returns:
            BSLResult with diagnostics and status
        """
        self.logger.info(f"Starting BSL analysis for: {src_dir}")
        
        try:
            # Validate inputs
            self.logger.debug("Validating input parameters")
            source_path = validate_source_path(src_dir)
            config_file = validate_config_path(config_path)
            
            # Use default config from BSL directory if none provided
            if config_file is None:
                default_config = Path(self.config.jar_path).parent / ".bsl-language-server.json"
                if not default_config.exists():
                    self._create_default_config(default_config)
                    self.logger.debug(f"Created default config file: {default_config}")
                config_file = default_config
                self.logger.debug(f"Using default config: {config_file}")
            
            memory = memory_mb or self.config.default_memory_mb
            
            self.logger.debug(f"Analysis parameters - source: {source_path}, config: {config_file}, memory: {memory}MB")
            
            # Build command
            cmd = self._build_analyze_command(source_path, config_file, memory)
            self.logger.debug(f"Built analyze command: {' '.join(cmd)}")
            
            # Execute command with safe environment and working directory
            self.logger.info("Executing BSL analysis command")
            env = self._get_safe_environment()
            
            # Use source directory as working directory to avoid Windows junction issues
            work_dir = source_path.parent if source_path.is_file() else source_path
            self.logger.debug(f"Working directory: {work_dir}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=300,  # 5 minutes timeout
                env=env,
                cwd=str(work_dir)
            )
            
            self.logger.info(f"Analysis command completed with return code: {result.returncode}")
            self.logger.debug(f"STDOUT length: {len(result.stdout)}, STDERR length: {len(result.stderr)}")
            
            # Check for stderr - filter out progress bar messages
            if result.stderr:
                stderr_lines = result.stderr.split('\n')
                # Filter out empty lines and progress bar messages
                error_lines = [
                    line for line in stderr_lines 
                    if line.strip() and not line.strip().startswith('Analyzing files')
                ]
                
                # Only treat as error if there are real error messages (not just progress)
                if error_lines:
                    self.logger.error(f"BSL analysis errors detected: {error_lines[:5]}")
                    return BSLResult(
                        success=False,
                        diagnostics=[],
                        output=result.stdout,
                        error=f"BSL analysis errors: {chr(10).join(error_lines)}",
                        files_processed=0
                    )
                else:
                    # Only progress messages, not actual errors
                    self.logger.debug(f"BSL analysis progress: {stderr_lines[:2]}")
            
            # JSON reporter creates bsl-json.json file in working directory
            json_report_path = work_dir / "bsl-json.json"
            json_content = ""
            
            # Check if JSON report exists - if not, return error
            if not json_report_path.exists():
                self.logger.error(f"JSON report file not found at: {json_report_path}")
                return BSLResult(
                    success=False,
                    diagnostics=[],
                    output=result.stdout,
                    error=f"JSON report file not found at: {json_report_path}",
                    files_processed=0
                )
            
            # Read JSON report
            self.logger.info(f"Reading JSON report from: {json_report_path}")
            try:
                with open(json_report_path, 'r', encoding='utf-8') as f:
                    json_content = f.read()
                self.logger.debug(f"JSON report file size: {len(json_content)} bytes")
                
                # Clean up the report file after reading
                # Keep file in DEBUG mode for inspection
                is_debug_mode = os.environ.get("BSL_LOG_LEVEL", "WARNING").upper() == "DEBUG"
                if not is_debug_mode:
                    json_report_path.unlink()
                    self.logger.debug("Removed JSON report file")
                else:
                    self.logger.debug(f"DEBUG mode enabled, keeping JSON report file: {json_report_path}")
            except Exception as e:
                self.logger.error(f"Failed to read JSON report file: {e}")
                return BSLResult(
                    success=False,
                    diagnostics=[],
                    output=result.stdout,
                    error=f"Failed to read JSON report file: {e}",
                    files_processed=0
                )
            
            # Parse results from JSON file
            self.logger.debug("Parsing analysis output")
            diagnostics = self._parse_analyze_output(json_content, result.stderr)
            files_processed = self._count_processed_files(source_path)
            
            self.logger.info(f"Analysis completed - diagnostics: {len(diagnostics)}, files processed: {files_processed}")
            
            return BSLResult(
                success=result.returncode == 0,
                diagnostics=diagnostics,
                output=json_content,
                error=result.stderr,
                files_processed=files_processed
            )
            
        except subprocess.TimeoutExpired:
            self.logger.error("BSL analysis timed out after 5 minutes")
            return BSLResult(
                success=False,
                diagnostics=[],
                output="",
                error="BSL analysis timed out after 5 minutes"
            )
        except Exception as e:
            self.logger.error(f"!!!!!!!! Error running BSL analysis: {str(e)}", exc_info=True)
            return BSLResult(
                success=False,
                diagnostics=[],
                output="",
                error=f"!!!!!!!! Error running BSL analysis: {str(e)}"
            )
    
    def format(self, src_dir: str) -> BSLResult:
        """
        Format BSL files in source directory.

        Args:
            src_dir: Path to directory or file with .bsl/.os files

        Returns:
            BSLResult with formatting status
        """
        self.logger.info(f"Starting BSL formatting for: {src_dir}")
        try:
            # Validate input
            self.logger.debug("Validating input parameters")
            source_path = validate_source_path(src_dir)

            # Build command
            cmd = self._build_format_command(source_path)
            self.logger.debug(f"Built format command: {' '.join(cmd)}")

            # Execute command with safe environment
            self.logger.info("Executing BSL formatting command")
            env = self._get_safe_environment()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=120,  # 2 minutes timeout
                env=env
            )

            self.logger.info(f"Formatting command completed with return code: {result.returncode}")
            self.logger.debug(f"STDOUT length: {len(result.stdout)}, STDERR length: {len(result.stderr)}")

            # Filter out progress bar from stderr
            stderr_filtered = result.stderr
            if result.stderr:
                stderr_lines = result.stderr.split('\n')
                error_lines = [
                    line for line in stderr_lines
                    if line.strip() and not line.strip().startswith('Analyzing files')
                ]
                stderr_filtered = '\n'.join(error_lines) if error_lines else ""
                if not error_lines:
                    self.logger.debug(f"Format progress: {stderr_lines[:2]}")

            files_processed = self._count_processed_files(source_path)
            self.logger.info(f"Formatting completed - files processed: {files_processed}")

            return BSLResult(
                success=result.returncode == 0,
                diagnostics=[],
                output=result.stdout,
                error=stderr_filtered,
                files_processed=files_processed
            )

        except subprocess.TimeoutExpired:
            self.logger.error("BSL formatting timed out after 2 minutes")
            return BSLResult(
                success=False,
                diagnostics=[],
                output="",
                error="BSL formatting timed out after 2 minutes"
            )
        except Exception as e:
            self.logger.error(f"Error running BSL formatting: {str(e)}", exc_info=True)
            return BSLResult(
                success=False,
                diagnostics=[],
                output="",
                error=f"Error running BSL formatting: {str(e)}"
            )

    def check_syntax(self,
                     ib_connection: str,
                     db_user: Optional[str] = None,
                     db_pwd: Optional[str] = None,
                     groupbymetadata: bool = True,
                     junitpath: Optional[str] = None) -> BSLResult:
        """
        Run syntax check using vanessa-runner.

        Args:
            ib_connection: Connection string to 1C infobase (e.g., "/F/path/to/base" or "/Sserver/base")
            db_user: Database user (optional)
            db_pwd: Database password (optional)
            groupbymetadata: Group results by metadata (default: True)
            junitpath: Path to save JUnit report (optional)

        Returns:
            BSLResult with syntax check results
        """
        self.logger.info(f"Starting syntax check for infobase: {ib_connection}")

        try:
            # Build command
            cmd = self._build_syntax_check_command(
                ib_connection,
                db_user,
                db_pwd,
                groupbymetadata,
                junitpath
            )
            self.logger.debug(f"Built syntax check command: {' '.join(cmd)}")

            # Execute command with safe environment
            self.logger.info("Executing vanessa-runner syntax-check command")
            env = self._get_safe_environment()
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                timeout=600,  # 10 minutes timeout
                env=env
            )

            self.logger.info(f"Syntax check completed with return code: {result.returncode}")
            self.logger.debug(f"STDOUT length: {len(result.stdout)}, STDERR length: {len(result.stderr)}")

            # Parse diagnostics from output
            diagnostics = self._parse_syntax_check_output(result.stdout, result.stderr)

            self.logger.info(f"Syntax check completed - diagnostics: {len(diagnostics)}")

            return BSLResult(
                success=result.returncode == 0,
                diagnostics=diagnostics,
                output=result.stdout,
                error=result.stderr,
                files_processed=0  # vanessa-runner doesn't report file count
            )

        except subprocess.TimeoutExpired:
            self.logger.error("Syntax check timed out after 10 minutes")
            return BSLResult(
                success=False,
                diagnostics=[],
                output="",
                error="Syntax check timed out after 10 minutes"
            )
        except Exception as e:
            self.logger.error(f"Error running syntax check: {str(e)}", exc_info=True)
            return BSLResult(
                success=False,
                diagnostics=[],
                output="",
                error=f"Error running syntax check: {str(e)}"
            )
    
    def _build_analyze_command(self, 
                              source_path: Path, 
                              config_file: Path,
                              memory_mb: int) -> List[str]:
        """Build analyze command."""
        # Use temp directory as user home to avoid Windows junction issues
        temp_home = Path(tempfile.gettempdir()).as_posix()
        
        # Get absolute paths in POSIX format to avoid Windows path issues
        config_path = config_file.resolve().as_posix()
        source_str = str(source_path.resolve())
        
        # Create temp directory for reports
        #temp_report_dir = Path(tempfile.gettempdir()) / "bsl_reports"
        output_path = ( Path(self.config.jar_path).parent ).as_posix()
        #temp_report_dir.mkdir(exist_ok=True)
        #output_path = (temp_report_dir / "report").as_posix()
        
        cmd = [
            'java',
            f'-Xmx{memory_mb}m',
            '-Dfile.encoding=UTF-8',
#            f'-Duser.home={temp_home}',
#            f'-Djava.io.tmpdir={temp_home}',
            '-jar', self.config.jar_path,
            '--analyze',
            '--srcDir', source_str,
            '--reporter', 'json',
            '-c', config_path
        ]
        
        return cmd
    
    def _build_format_command(self, source_path: Path) -> List[str]:
        """Build format command."""
        return [
            'java',
            '-Dfile.encoding=UTF-8',
            '-jar', self.config.jar_path,
            '--format',
            '--src', str(source_path)
        ]

    def _build_syntax_check_command(self,
                                     ib_connection: str,
                                     db_user: Optional[str],
                                     db_pwd: Optional[str],
                                     groupbymetadata: bool,
                                     junitpath: Optional[str]) -> List[str]:
        """Build syntax check command for vanessa-runner."""
        cmd = [
            'vrunner',
            'syntax-check',
            '--ibconnection', ib_connection
        ]

        if db_user:
            cmd.extend(['--db-user', db_user])

        if db_pwd:
            cmd.extend(['--db-pwd', db_pwd])

        if groupbymetadata:
            cmd.append('--groupbymetadata')

        if junitpath:
            cmd.extend(['--junitpath', junitpath])

        return cmd
    
    def _parse_analyze_output(self, stdout: str, stderr: str) -> List[BSLDiagnostic]:
        """Parse BSL analyze output into diagnostics."""
        self.logger.debug("Parsing BSL analyze output")
        self.logger.debug(f"STDOUT length: {len(stdout)}")
        self.logger.debug(f"STDERR length: {len(stderr)}")
        
        diagnostics = []
        
        # Try to parse JSON output first
        if stdout and stdout.strip():
            self.logger.debug("Attempting to parse JSON output")
            self.logger.debug(f"First 500 chars of output: {stdout[:500]}")
            
            # Try to extract JSON from output (might be mixed with logs)
            json_str = stdout.strip()
            
            # Find JSON array start if not pure JSON
            if json_str and '[' in json_str and ']' in json_str:
                start_idx = json_str.find('[')
                end_idx = json_str.rfind(']') + 1
                json_str = json_str[start_idx:end_idx]
                self.logger.debug(f"Extracted JSON substring from position {start_idx} to {end_idx}")
            
            if not json_str:
                self.logger.warning("JSON string is empty after extraction")
                return []
            
            try:
                data = json.loads(json_str)
                self.logger.debug(f"Successfully parsed JSON. Type: {type(data)}")
                
                # BSL LS JSON reporter format: array of file info objects
                if isinstance(data, list):
                    self.logger.debug(f"JSON is a list with {len(data)} items")
                    for file_info in data:
                        if not isinstance(file_info, dict):
                            continue
                        
                        file_path = file_info.get('path', '')
                        file_diagnostics = file_info.get('diagnostics', [])
                        self.logger.debug(f"Processing file: {file_path} with {len(file_diagnostics)} diagnostics")
                        
                        for diag in file_diagnostics:
                            severity_map = {
                                'Error': 'error',
                                'Warning': 'warning',
                                'Information': 'info',
                                'Hint': 'info'
                            }
                            
                            severity_str = diag.get('severity', 'Information')
                            severity = severity_map.get(severity_str, 'info')
                            
                            range_data = diag.get('range', {})
                            start = range_data.get('start', {})
                            line = start.get('line', 0)
                            character = start.get('character', 0)
                            
                            message = diag.get('message', '')
                            code = diag.get('code', '')
                            
                            diagnostics.append(BSLDiagnostic(
                                file=file_path,
                                line=line + 1,  # BSL LS uses 0-based line numbers
                                column=character + 1,  # BSL LS uses 0-based columns
                                severity=severity,
                                message=message,
                                code=code
                            ))
                    
                    self.logger.info(f"Successfully parsed {len(diagnostics)} diagnostics from JSON")
                    return diagnostics
                
                # Fallback: try old format with 'issues' key
                elif isinstance(data, dict) and 'issues' in data:
                    self.logger.debug(f"Found {len(data['issues'])} issues in JSON output")
                    for issue in data['issues']:
                        diagnostics.append(BSLDiagnostic(
                            file=issue.get('file', ''),
                            line=issue.get('line', 0),
                            column=issue.get('column', 0),
                            severity=issue.get('severity', 'info'),
                            message=issue.get('message', ''),
                            code=issue.get('code')
                        ))
                    return diagnostics
                else:
                    self.logger.warning(f"Unexpected JSON structure. Keys: {data.keys() if isinstance(data, dict) else 'not a dict'}")
                    
            except json.JSONDecodeError as e:
                self.logger.debug(f"JSON parsing failed: {e}, falling back to text parsing")
                pass
        
        # Parse text output if JSON parsing failed
        self.logger.debug("Parsing text output")
        lines = (stdout + '\n' + stderr).split('\n')
        parsed_lines = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Try to parse common BSL error formats
            # Format: file:line:column: severity: message
            if ':' in line and any(severity in line.lower() for severity in ['error', 'warning', 'info']):
                parts = line.split(':', 4)
                if len(parts) >= 4:
                    try:
                        file_path = parts[0]
                        line_num = int(parts[1])
                        col_num = int(parts[2])
                        severity_msg = parts[3]
                        
                        # Extract severity and message
                        severity = 'info'
                        message = severity_msg
                        for sev in ['error', 'warning', 'info']:
                            if sev in severity_msg.lower():
                                severity = sev
                                message = severity_msg.replace(sev, '').strip(': ').strip()
                                break
                        
                        diagnostics.append(BSLDiagnostic(
                            file=file_path,
                            line=line_num,
                            column=col_num,
                            severity=severity,
                            message=message
                        ))
                        parsed_lines += 1
                    except (ValueError, IndexError):
                        # If parsing fails, add as general message
                        diagnostics.append(BSLDiagnostic(
                            file='',
                            line=0,
                            column=0,
                            severity='info',
                            message=line
                        ))
                        parsed_lines += 1
        
        self.logger.debug(f"Parsed {parsed_lines} diagnostic lines from text output")
        return diagnostics
    
    def _count_processed_files(self, source_path: Path) -> int:
        """Count BSL/OS files in source path."""
        if source_path.is_file():
            self.logger.debug(f"Counting single file: {source_path}")
            return 1

        bsl_files = list(source_path.glob('**/*.bsl'))
        os_files = list(source_path.glob('**/*.os'))
        total_files = len(bsl_files) + len(os_files)

        self.logger.debug(f"Found {len(bsl_files)} .bsl files and {len(os_files)} .os files, total: {total_files}")
        return total_files

    def _parse_syntax_check_output(self, stdout: str, stderr: str) -> List[BSLDiagnostic]:
        """Parse vanessa-runner syntax check output into diagnostics."""
        self.logger.debug("Parsing vanessa-runner syntax check output")
        diagnostics = []

        # Combine stdout and stderr
        output = stdout + '\n' + stderr

        # Parse output line by line
        for line in output.split('\n'):
            line = line.strip()
            if not line:
                continue

            # Try to detect error patterns
            # Common patterns in vanessa-runner output:
            # - "Ошибка: <message>" or "Error: <message>"
            # - Lines containing "Модуль:" or "Module:"
            # - Lines containing file paths with line numbers

            # Pattern 1: Direct error messages
            if 'ошибка' in line.lower() or 'error' in line.lower():
                diagnostics.append(BSLDiagnostic(
                    file='',
                    line=0,
                    column=0,
                    severity='error',
                    message=line
                ))

            # Pattern 2: Warning messages
            elif 'предупреждение' in line.lower() or 'warning' in line.lower():
                diagnostics.append(BSLDiagnostic(
                    file='',
                    line=0,
                    column=0,
                    severity='warning',
                    message=line
                ))

        self.logger.info(f"Parsed {len(diagnostics)} diagnostics from syntax check output")
        return diagnostics
    
    def _create_temp_config(self) -> Path:
        """Create minimal temporary configuration file to avoid directory traversal."""
        minimal_config = {
            "diagnosticLanguage": "RU",
            "language": "RU"
        }
        
        # Create temp file with .json extension
        temp_fd, temp_path = tempfile.mkstemp(suffix='.bsl-language-server.json', text=True)
        try:
            with open(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(minimal_config, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Created minimal temp config at: {temp_path}")
            return Path(temp_path)
        except Exception as e:
            # Close and cleanup on error
            try:
                Path(temp_path).unlink(missing_ok=True)
            except:
                pass
            raise RuntimeError(f"Failed to create temp config file: {e}") from e
    
    def _create_default_config(self, config_path: Path) -> None:
        """Create minimal configuration file in BSL directory."""
        minimal_config = {
            "diagnosticLanguage": "RU",
            "language": "RU"
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(minimal_config, f, ensure_ascii=False, indent=2)
            self.logger.debug(f"Created default config at: {config_path}")
        except Exception as e:
            raise RuntimeError(f"Failed to create default config file: {e}") from e
    
    def _get_safe_environment(self) -> Dict[str, str]:
        """
        Create a safe environment for subprocess execution.
        Redirects problematic Windows paths to safe temporary locations.
        """
        # Start with current environment
        env = os.environ.copy()
        
        # Get safe temp directory
        temp_dir = tempfile.gettempdir()
        
        # Override problematic Windows environment variables
        # This prevents BSL LS from accessing junction points and problematic directories
        env['LOCALAPPDATA'] = temp_dir
        env['APPDATA'] = temp_dir
        env['TEMP'] = temp_dir
        env['TMP'] = temp_dir
        
        # Set user home to temp as well
        env['USERPROFILE'] = temp_dir
        env['HOME'] = temp_dir
        
        self.logger.debug(f"Created safe environment with redirected paths to: {temp_dir}")
        return env
