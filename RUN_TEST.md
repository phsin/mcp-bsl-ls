# Как запустить тест JSON репортера

## Предварительные требования

1. Установите зависимости (если еще не установлены):
```bash
cd C:\1C\AI\mcp-bsl-python
pip install -e .
```

2. Убедитесь, что BSL Language Server доступен:
```bash
java -jar C:\1C\AI\bsl\bsl-language-server-0.24.2-exec.jar --version
```

## Запуск теста

### Через Python скрипт:

```bash
cd C:\1C\AI\mcp-bsl-python
python test_json_reporter.py
```

### Через MCP инструмент:

В Cursor или другом MCP клиенте вызовите:

```javascript
{
  "tool": "bsl_analyze",
  "arguments": {
    "srcDir": "C:\\dev\\lk\\front\\OrdersIntegration\\src\\CommonModules\\OrdersIntegration_API_Orders"
  }
}
```

### Прямое сравнение console vs json:

#### Console репортер (старый способ):
```bash
cd C:\1C\AI\bsl
java -jar .\bsl-language-server-0.24.2-exec.jar --analyze --srcDir "C:\dev\lk\front\OrdersIntegration\src\CommonModules\OrdersIntegration_API_Orders" --reporter console
```

#### JSON репортер (новый способ):
```bash
cd C:\1C\AI\bsl
java -jar .\bsl-language-server-0.24.2-exec.jar --analyze --srcDir "C:\dev\lk\front\OrdersIntegration\src\CommonModules\OrdersIntegration_API_Orders" --reporter json
```

## Ожидаемый результат

При успешном выполнении вы увидите:

```
================================================================================
Testing BSL Runner with JSON Reporter
================================================================================

Analyzing directory: C:\dev\lk\front\OrdersIntegration\src\CommonModules\OrdersIntegration_API_Orders
Using config: C:\path\to\config.json
Memory: 4096MB
--------------------------------------------------------------------------------
... (логи BSL анализа) ...

================================================================================
ANALYSIS RESULTS
================================================================================
Success: True
Files processed: 1
Total diagnostics: 15

Errors: 5
Warnings: 1
Info: 9

--------------------------------------------------------------------------------
FIRST 5 DIAGNOSTICS:
--------------------------------------------------------------------------------

1. [ERROR] C:\dev\lk\front\...\Module.bsl:112:4
   Code: ParseError
   Message: Ошибка разбора исходного кода...

2. [INFO] C:\dev\lk\front\...\Module.bsl:72:3
   Code: UsageWriteLogEvent
   Message: Не указан 5й параметр "Комментарий"

...
```

## Отладка

Если что-то не работает, проверьте логи:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Логи покажут:
- Команду, которая выполняется
- STDOUT и STDERR от BSL сервера
- Процесс парсинга JSON
- Количество найденных диагностик

