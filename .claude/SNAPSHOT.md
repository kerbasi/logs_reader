# Project Snapshot

## Текущее состояние

**Статус:** активная разработка
**Последнее обновление:** 2026-05-26T06:18:28Z (pre-compaction)

## Что сделано

- tkinter GUI (`gui.py`) — поиск логов с цветовой подсветкой, открытие в терминале
- `LogSearcher` — поиск по структуре `root/PN/YYYY[MM]/[DEBUG/]*SN*`, индекс через `.mlnx`
- `ProductResolver` — получение PN по SN через QMS3 HTTP API
- `ICTLogSearcher` — делегирует в `get_index().search(sn)` (singleton `ICTIndex`)
- `ICTIndex` (`src/ict_index.py`) — JSON-индекс `"TRIxxx/YYYYMM" → [filenames]`, параллельный билд через `ThreadPoolExecutor(20)`, горячие месяцы переиндексируются каждые 30с, полный rebuild раз в сутки, персистится в `/tmp/ict_log_index.json`
- `ICTIndex.search_by_pn(pn)` — контентный поиск по PN-колонке CSV; `_pn_index` строится при сканировании, персистируется в JSON, hot-rebuild без дублей
- `open_in_libreoffice()` — открытие CSV через `libreoffice --calc --infilter`
- GUI и CLI: ICT результаты объединяются со стандартными; CSV открываются через LibreOffice
- GUI dark theme читаемость: `text_dim` поднят до `#c8cad8`, UI шрифт 13pt, моно 12pt
- `main.py`: добавлен shebang `#!/usr/bin/env python3`
- `.gitattributes`: принудительные LF-окончания для `.py` и `.sh` (исправлен CRLF на Linux)
- Unit-тесты: 13 тестов в `tests/test_ict_index.py` (все зелёные)
- **GUI Pass/Fail фильтр** — два чекбокса в заголовке Results, оба включены по умолчанию; фильтрация мгновенная без повторного поиска; счётчик показывает "N of M" при активном фильтре
- **PN-only ICT поиск** — SN стал необязательным; если введён только PN, выполняется прямой поиск по именам ICT-файлов без QMS3; если введён только SN — прежнее поведение

## Что в процессе

_(нет)_

## Известные проблемы

- `pytest` не установлен в Windows-окружении — тесты не запускались локально (однако стандартный `unittest` модуль отлично работает и запускает все тесты)

## Следующие шаги

_(нет активных задач)_
