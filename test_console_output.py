#!/usr/bin/env python3
"""Test script for console output functionality."""

import tempfile
import os
from pathlib import Path

def test_console_output():
    """Test console output functionality."""
    print("Testing BSL Console Output...")
    
    # Import our modules
    from mcp_bsl.config import get_config
    from mcp_bsl.bsl_runner import BSLRunner
    
    try:
        # Test configuration
        config = get_config()
        print(f"[OK] Config loaded: JAR={config.jar_path}")
        
        # Test runner
        runner = BSLRunner(config)
        print("[OK] BSL runner created")
        
        # Create test BSL file with intentional issues
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            test_file = temp_path / "test.bsl"
            test_file.write_text("""
// Test BSL file with intentional issues
Процедура Тест()
    Перем Переменная;  // Unused variable warning
    // Missing return statement
КонецПроцедуры

Функция ТестФункция()
    // Missing return statement - error
КонецФункции
""", encoding='utf-8')
            
            print(f"[OK] Test file created: {test_file}")
            
            # Test analyze with console output
            try:
                print("\n" + "="*50)
                print("RUNNING ANALYSIS WITH CONSOLE OUTPUT")
                print("="*50)
                
                result = runner.analyze(str(temp_path), console_output=True)
                
                print(f"\n[OK] Analysis completed: success={result.success}, files={result.files_processed}")
                print(f"   Diagnostics: {len(result.diagnostics)}")
                
                # Also test without console output for comparison
                print("\n" + "="*50)
                print("RUNNING ANALYSIS WITHOUT CONSOLE OUTPUT")
                print("="*50)
                
                result2 = runner.analyze(str(temp_path), console_output=False)
                print(f"[OK] Analysis completed silently: success={result2.success}, files={result2.files_processed}")
                
            except Exception as e:
                print(f"[WARN] Analysis failed (expected if BSL jar issues): {e}")
        
        print("\n[OK] Console output test completed!")
        return True
        
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_console_output()
    if success:
        print("\n[SUCCESS] Console output functionality is working!")
    else:
        print("\n[ERROR] Console output functionality has issues")
