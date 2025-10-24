"""Test BSL runner with JSON reporter."""

import sys
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from mcp_bsl.config import get_config
from mcp_bsl.bsl_runner import BSLRunner

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

def test_json_reporter():
    """Test BSL analysis with JSON reporter."""
    print("=" * 80)
    print("Testing BSL Runner with JSON Reporter")
    print("=" * 80)
    
    # Initialize config and runner
    config = get_config()
    runner = BSLRunner(config)
    
    # Test directory
    test_dir = r"C:\dev\lk\front\OrdersIntegration\src\CommonModules\OrdersIntegration_API_Orders"
    
    print(f"\nAnalyzing directory: {test_dir}")
    print(f"Using config: {config.config_path}")
    print(f"Memory: {config.default_memory_mb}MB")
    print("-" * 80)
    
    # Run analysis
    result = runner.analyze(test_dir, config.config_path, config.default_memory_mb)
    
    print("\n" + "=" * 80)
    print("ANALYSIS RESULTS")
    print("=" * 80)
    print(f"Success: {result.success}")
    print(f"Files processed: {result.files_processed}")
    print(f"Total diagnostics: {len(result.diagnostics)}")
    
    # Group by severity
    errors = [d for d in result.diagnostics if d.severity == 'error']
    warnings = [d for d in result.diagnostics if d.severity == 'warning']
    infos = [d for d in result.diagnostics if d.severity == 'info']
    
    print(f"\nErrors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Info: {len(infos)}")
    
    # Show first few diagnostics
    if result.diagnostics:
        print("\n" + "-" * 80)
        print("FIRST 5 DIAGNOSTICS:")
        print("-" * 80)
        for i, diag in enumerate(result.diagnostics[:5], 1):
            print(f"\n{i}. [{diag.severity.upper()}] {diag.file}:{diag.line}:{diag.column}")
            print(f"   Code: {diag.code}")
            print(f"   Message: {diag.message}")
    
    # Show full JSON output
    if result.output:
        print("\n" + "-" * 80)
        print("FULL BSL JSON OUTPUT:")
        print("-" * 80)
        print(result.output[:1000] + "..." if len(result.output) > 1000 else result.output)
    
    if result.error:
        print("\n" + "-" * 80)
        print("BSL SERVER LOGS (STDERR):")
        print("-" * 80)
        print(result.error[:500])
    
    print("\n" + "=" * 80)
    print("TEST COMPLETED")
    print("=" * 80)

if __name__ == "__main__":
    test_json_reporter()

