"""Configuration management for BSL MCP server."""

import os
import pathlib
from typing import Optional
from pydantic import BaseModel, Field, validator


class BSLConfig(BaseModel):
    """Configuration for BSL Language Server."""
    
    jar_path: str = Field(..., description="Path to BSL Language Server JAR file")
    default_memory_mb: int = Field(default=4096, description="Default JVM memory limit in MB")
    config_path: Optional[str] = Field(default=None, description="Path to .bsl-language-server.json configuration file")
    
    @validator('jar_path')
    def validate_jar_path(cls, v):
        """Validate that JAR file exists."""
        jar_path = pathlib.Path(v)
        if not jar_path.exists():
            raise ValueError(f"BSL JAR file not found: {v}")
        if not jar_path.suffix.lower() == '.jar':
            raise ValueError(f"File is not a JAR file: {v}")
        return str(jar_path.absolute())
    
    @validator('default_memory_mb')
    def validate_memory(cls, v):
        """Validate memory limit."""
        if v < 128:
            raise ValueError("Memory limit must be at least 128 MB")
        if v > 16384:
            raise ValueError("Memory limit should not exceed 16 GB")
        return v
    
    @validator('config_path')
    def validate_config_path_field(cls, v):
        """Validate configuration file path if provided."""
        if v is None:
            return None
        
        path = pathlib.Path(v)
        if not path.exists():
            raise ValueError(f"Configuration file not found: {v}")
        
        if path.suffix.lower() != '.json':
            raise ValueError(f"Configuration file must be JSON: {v}")
        
        return str(path.absolute())


def get_config() -> BSLConfig:
    """Get BSL configuration from environment variables."""
    jar_path = os.getenv('BSL_JAR')
    if not jar_path:
        jar_path = r'C:\1C\AI\bsl\bsl-language-server-0.24.2-exec.jar'
        #raise ValueError(
        #    "BSL_JAR environment variable is required. "
        #    "Set it to the path of bsl-language-server JAR file."
        #)
    
    memory_mb = int(os.getenv('BSL_MEMORY_MB', '4096'))
    config_path = os.getenv('BSL_CONFIG')
    
    return BSLConfig(
        jar_path=jar_path,
        default_memory_mb=memory_mb,
        config_path=config_path
    )


def validate_source_path(source_path: str) -> pathlib.Path:
    """Validate source path (file or directory)."""
    path = pathlib.Path(source_path)
    
    if not path.exists():
        raise ValueError(f"Source path does not exist: {source_path}")
    
    # Check if it's a BSL/OS file or directory containing them
    if path.is_file():
        if path.suffix.lower() not in ['.bsl', '.os']:
            raise ValueError(f"File is not a BSL/OS file: {source_path}")
    elif path.is_dir():
        # Check if directory contains BSL/OS files
        bsl_files = list(path.glob('**/*.bsl')) + list(path.glob('**/*.os'))
        if not bsl_files:
            raise ValueError(f"Directory contains no BSL/OS files: {source_path}")
    
    return path.absolute()


def validate_config_path(config_path: Optional[str]) -> Optional[pathlib.Path]:
    """Validate configuration file path."""
    if config_path is None:
        return None
    
    path = pathlib.Path(config_path)
    if not path.exists():
        raise ValueError(f"Configuration file not found: {config_path}")
    
    if path.suffix.lower() != '.json':
        raise ValueError(f"Configuration file must be JSON: {config_path}")
    
    return path.absolute()
