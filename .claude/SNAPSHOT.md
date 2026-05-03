# Project Snapshot

## Текущее состояние

**Статус:** активная разработка
**Последнее обновление:** 2026-04-27T00:00:00Z

## Что сделано

- tkinter GUI (`gui.py`) — поиск логов с цветовой подсветкой, открытие в терминале
- `LogSearcher` — поиск по структуре `root/PN/YYYY[MM]/[DEBUG/]*SN*`, индекс через `.mlnx`
- `ProductResolver` — получение PN по SN через QMS3 HTTP API
- `ICTLogSearcher` — делегирует в `get_index().search(sn)` (singleton `ICTIndex`)
- `ICTIndex` (`src/ict_index.py`) — JSON-индекс `"TRIxxx/YYYYMM" → [filenames]`, параллельный билд через `ThreadPoolExecutor(20)`, горячие месяцы переиндексируются каждые 30с, полный rebuild раз в сутки, персистится в `/tmp/ict_log_index.json`
- `open_in_libreoffice()` — открытие CSV через `libreoffice --calc --infilter`
- GUI и CLI: ICT результаты объединяются со стандартными; CSV открываются через LibreOffice
- GUI dark theme читаемость: `text_dim` поднят до `#c8cad8`, UI шрифт 13pt, моно 12pt
- `main.py`: добавлен shebang `#!/usr/bin/env python3`
- `.gitattributes`: принудительные LF-окончания для `.py` и `.sh` (исправлен CRLF на Linux)

## Что в процессе

_(нет)_

## Известные проблемы

- `pytest` не установлен в Windows-окружении — тесты не запускались локально

## Следующие шаги

_(нет активных задач)_
