"""Test for check_syntax command."""

import sys
import os
import tempfile
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from mcp_bsl.bsl_runner import BSLRunner
from mcp_bsl.config import BSLConfig


def test_build_syntax_check_command():
    """Test building syntax check command."""
    # Create a temporary JAR file for testing
    with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as tmp:
        tmp_jar_path = tmp.name

    try:
        # Create a minimal config with vanessa-runner settings
        config = BSLConfig(
            jar_path=tmp_jar_path,
            default_memory_mb=4096,
            vrunner_ib_connection='/F/path/to/base',
            vrunner_db_user='config_user',
            vrunner_db_pwd='config_password',
            vrunner_groupbymetadata=True,
            vrunner_junitpath='/config/junit'
        )

        runner = BSLRunner(config)

        # Test command building with explicit parameters
        cmd = runner._build_syntax_check_command(
            ib_connection='/F/path/to/base',
            db_user='admin',
            db_pwd='password',
            groupbymetadata=True,
            junitpath='/path/to/junit'
        )

        print("Built command with explicit parameters:")
        print(' '.join(cmd))

        # Verify command structure
        assert 'vrunner' in cmd
        assert 'syntax-check' in cmd
        assert '--ibconnection' in cmd
        assert '/F/path/to/base' in cmd
        assert '--db-user' in cmd
        assert 'admin' in cmd
        assert '--db-pwd' in cmd
        assert 'password' in cmd
        assert '--groupbymetadata' in cmd
        assert '--junitpath' in cmd
        assert '/path/to/junit' in cmd

        print("✓ Command building with explicit parameters passed!")

        # Test using config values (call check_syntax without parameters)
        print("\nTesting config-based command building...")
        # This will use config values
        result = runner.check_syntax()  # No parameters = use config

        # Verify it didn't fail due to missing parameters
        assert result is not None
        print("✓ Config-based command building passed!")

    finally:
        # Cleanup temp file
        Path(tmp_jar_path).unlink(missing_ok=True)


def test_parse_syntax_check_output():
    """Test parsing syntax check output."""
    # Create a temporary JAR file for testing
    with tempfile.NamedTemporaryFile(suffix='.jar', delete=False) as tmp:
        tmp_jar_path = tmp.name

    try:
        # Create a minimal config (vrunner settings not needed for parsing test)
        config = BSLConfig(
            jar_path=tmp_jar_path,
            default_memory_mb=4096
        )

        runner = BSLRunner(config)

        # Test output parsing
        stdout = """
        Выполняется проверка синтаксиса...
        Ошибка: Неверный синтаксис в модуле
        Предупреждение: Использование устаревшей функции
        """

        stderr = """
        Error: Failed to parse module
        """

        diagnostics = runner._parse_syntax_check_output(stdout, stderr)

        print(f"\nParsed {len(diagnostics)} diagnostics:")
        for diag in diagnostics:
            print(f"  - [{diag.severity}] {diag.message}")

        # Verify we found diagnostics
        assert len(diagnostics) > 0

        # Check for error
        errors = [d for d in diagnostics if d.severity == 'error']
        assert len(errors) > 0

        # Check for warning
        warnings = [d for d in diagnostics if d.severity == 'warning']
        assert len(warnings) > 0

        print("✓ Output parsing test passed!")
    finally:
        # Cleanup temp file
        Path(tmp_jar_path).unlink(missing_ok=True)


if __name__ == '__main__':
    print("Testing check_syntax implementation...")
    print("=" * 50)

    try:
        test_build_syntax_check_command()
        test_parse_syntax_check_output()
        print("\n" + "=" * 50)
        print("All tests passed! ✓")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
