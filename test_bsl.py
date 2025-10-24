"""Test BSL runner with the fix."""

from mcp_bsl.config import get_config
from mcp_bsl.bsl_runner import BSLRunner

# Initialize
config = get_config()
runner = BSLRunner(config)

# Run analysis
file_path = r'C:\dev\lk\front\OrdersIntegration\src\CommonModules\OrdersIntegration_API_Orders\Module.bsl'
print(f"Analyzing: {file_path}")
print("-" * 80)

result = runner.analyze(file_path)

print(f"Success: {result.success}")
print(f"Files processed: {result.files_processed}")
print(f"Diagnostics found: {len(result.diagnostics)}")
print()

if result.diagnostics:
    print("Diagnostics:")
    for diag in result.diagnostics[:10]:
        print(f"  {diag.severity.upper()}: {diag.file}:{diag.line}:{diag.column} - {diag.message}")
    if len(result.diagnostics) > 10:
        print(f"  ... and {len(result.diagnostics) - 10} more")
else:
    print("No diagnostics found.")

if result.error:
    print()
    print("Error output (first 500 chars):")
    print(result.error[:500])

