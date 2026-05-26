# Project Snapshot

## Текущее состояние

**Статус:** активная разработка
**Последнее обновление:** 2026-05-26

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
- **PN-only ICT поиск** — SN стал необязательным; прямой поиск по именам ICT-файлов без QMS3
- **Dual results view** — SN: tk.Text (filename + Path + Info lines); PN/ICT: Treeview (File/Date/Station/Operator + path info row); SUMMARY companions grouped with `└` prefix
- **Operator fix** — `_parse_oper_id` пробует OperID → OperatorID → Operator; `search()` ленивая дозаписи для None-записей; горячий ребилд сразу при старте
- **Palette overhaul** — `#18181B` bg, `#2563EB` primary button, `#06B6D4` result numbers, `#10B981` pass; три стиля кнопок: primary/secondary/danger
- **UX** — поиск автоматически переводит в верхний регистр; приложение открывается развёрнутым; xterm: Monospace 13pt, тёмная тема, геометрия 220×55

## Что в процессе

_(нет)_

## Известные проблемы

- `pytest` не установлен в Windows-окружении — используется `unittest`
- xterm: `-maximized` убран (не поддерживается старыми версиями), вместо него `-geometry 220x55`

## Следующие шаги

_(нет активных задач)_
