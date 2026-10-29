# AI Novel (Diploma)

Проект — визуальная новелла на Ren'Py с динамической генерацией сцен. Генератор (внешний воркер) пишет JSON-файлы в `game/scenes/`, статус их готовности отслеживается через MongoDB задачи.

## Архитектура (основные файлы)
- `game/script.rpy` — точка входа: метки `start`, `play_next_scene` (игровой цикл). Никакой низкоуровневой логики.
- `game/tasks.rpy` — подключение к MongoDB, функции работы с задачами: `create_task`, `check_status`.
- `game/playback_contract.rpy` и `game/schema/scene-v1.schema.json` — загрузка, миграция и строгая проверка сцены до выполнения.
- `game/playback_state.rpy` — сохраняемый snapshot, hash, cursor и структурированная ошибка.
- `game/playback.rpy` — подготовка snapshot и пошаговое проигрывание: labels `run_json_scene_file`, `run_json_scene_task` и внутренний цикл `_run_prepared_json_scene`.
- `game/playback_metadata.rpy` — поддерживаемые Ren'Py callbacks для History, save-slot metadata и проверки состояния после load.
- `game/scene_provider.rpy` — сохраняемая session state и несохраняемый runtime provider, структурированные ошибки, retry/ack и стабильная autosave-граница.
- `game/scene_queue.rpy` — bounded-очередь префетча N сцен и идемпотентный `done → consumed`; `wait_task` даёт interaction boundary между короткими poll.
- `game/theme_system.rpy` — реестр семи тем, Auto/override/fallback, palette tint, font packs и helpers для themed displayables.
- `game/gui/themes/` — одинаковый набор 9-slice PNG, manifests и четыре OFL font families с кириллицей.
- `game/screens.rpy` — gameplay/game-menu surfaces и pause layout: History 2/3 + меню 1/3 без отдельной кнопки History.
- `game/handlers/` — act-хендлеры (обработка шагов диалога). Реестр в `registry.rpy`.
- `game/images.rpy` — объявления спрайтов.
- `game/scenes/scene_<task_id>.json` — файлы сцен (название по `_id` задачи Mongo).

### Поток исполнения
1. `start` создаёт стабильную идентичность очереди без сетевого I/O и запускает provider-loop.
2. `SceneProvider.poll()` выполняет bounded-проверку очереди. При ожидании label показывает `wait_task` и повторяет poll; при ошибке открывает Retry/Main Menu.
3. Готовый snapshot проигрывается пошагово: каждое JSON-действие выполняется отдельной итерацией Ren'Py label-loop.
4. После успешного проигрывания provider идемпотентно меняет `done` на `consumed`, не удаляя внешнюю историю задачи. Retry ack не переигрывает сцену.
5. Только после completed playback и подтверждённого ack клиент фиксирует `boundary` и синхронно завершает autosave.

### Почему очередь
- Генератор может успеть сделать несколько сцен вперёд: они аккумулируются в `scene_tasks`.
- Фиксированный лимит `prefetch_depth` предотвращает бесконтрольный рост количества задач.
- Гонка статусов снижена: берём сцену только если `status == "done"` и файл существует (не пустой).

## Формат JSON сцены v1 (упрощённо)
```jsonc
{
  "schema_version": 1,
  "scene_id": "0123456789abcdef01234567",
  "characters": { "lira": "Лира", "kael": "Каэль" },
  "ui": { "theme_id": "literary", "palette_id": "sepia", "font_pack_id": "literary_serif" },
  "dialogue": [
    { "type": "scene", "target": "bg_tavern_interior" },
    { "type": "show", "target": "lira neutral", "transform": { "slot": "left" } },
    { "type": "show", "target": "kael serious", "transform": { "slot": "right", "flip": true } },
    { "type": "line", "speaker": "lira", "text": "Привет!" },
    { "type": "animate", "target": "lira neutral", "effect": { "type": "shake", "repeat": 3 } },
    { "type": "pause", "duration": 0.5 },
    { "type": "transition", "effect": "fade" },
    { "type": "return" }
  ]
}
```

Поле `ui` необязательно. При его отсутствии используется default-тема; в режиме `Auto` установленные рекомендации применяются, а неизвестные корректно записанные ID безопасно откатываются к default. Явный выбор пользователя в Preferences имеет приоритет. Main-menu shell всегда остаётся нейтральным.

Для размещения персонажей `show.transform.slot` принимает `far_left`, `left`, `center`, `right` или `far_right`; `flip: true` зеркалит спрайт. `slot` нельзя передавать одновременно с legacy-полем `xalign`, при этом старые сцены с `xalign`, `yalign`, `alpha` и `flip` остаются совместимыми.

Доступные theme IDs: `default`, `modern_muted`, `literary`, `romantic`, `lovecraft_biopunk`, `high_fantasy`, `science_fiction`. У default есть варианты `default`, `graphite_sage`, `warm_parchment`, `muted_blue`, `subdued_plum`. Графические элементы не содержат текста; default palette variants используют runtime tint и не дублируют PNG.

Тонкие рамки и орнаменты генерируются детерминированно с 2x supersampling и premultiplied-alpha downsampling; у больших pause-панелей сглаживаются только углы и полоса декора, чтобы не расходовать память на плоский центр. Namebox имеет компактный базовый размер и расширяется только для длинного имени. Цвет имени назначается по `character_id` и порядку `story_metadata.cast`, оставаясь различимым на фактическом фоне namebox. Карточка сохранения показывает безопасно экранированное название истории из `ai_novel.story_title`, затем legacy `_save_name`, а для старого безымянного слота — нейтральный fallback.

## Act-хендлеры
Каждый элемент `dialogue[]` имеет поле `type`, для которого существует обработчик `handle_<type>(step, chars) -> PlaybackActionResult`.
- Результат явно имеет вид `continue`, `scene_end`, `goto` или `error`. Handler не должен сам вызывать `renpy.jump()` и скрыто менять control flow.
- Реестр формируется через декоратор `@act_handler(name)` или `register_act_handler(name, func)`.
- Получение: `get_act_handlers()`.

### Добавление нового типа
1. Обновить JSON Schema и `_ACTION_FIELDS` в `playback_contract.rpy`.
2. Создать `game/handlers/<type>.rpy`, определить функцию и зарегистрировать её.
3. Добавить ресурсы и проверки их существования, если action на них ссылается.
4. Обновить Python-валидатор генератора и native invariant/regression tests.
5. Только после этого использовать новый `type` в JSON.

Пример:
```renpy
init python:
    @act_handler("flash")
    def handle_flash(step, chars):
        color = step.get("color", "#ffffff")
        dur = float(step.get("duration", 0.2))
        renpy.scene()
        renpy.show("flash_color", what=Solid(color))
        renpy.pause(dur)
        renpy.scene()
        return PlaybackActionResult.continue_()
```
JSON:
```json
{ "type": "flash", "color": "#ff0000", "duration": 0.15 }
```

## Очередь сцен — детали
Переменные (в `scene_queue.rpy`):
- `prefetch_depth` — целевое число задач вперёд.
- `scene_tasks` — список task_id в порядке создания.
- `task_status` — словарь статусов.
- `task_result` — словарь результатов (если воркер что-то кладёт).
- `last_consumed_task_id` — последний проигранный (используется при генерации следующей).

Функции:
- `init_scene_queue(depth)` — очистка и первичное наполнение очереди.
- `fill_scene_queue()` — добавляет задачи пока длина < `prefetch_depth`.
- `poll_scene_tasks()` — обновляет ограниченное число статусов и bounded-шагами восполняет очередь; error/missing остаются видимыми provider-у.
- `get_next_ready_task_id()` — выбирает первый `done` с валидным файлом.
- `consume_task(tid)` — удаляет задачу из локальной очереди, идемпотентно подтверждает в Mongo статус `consumed` и обновляет `last_consumed_task_id`.

Экраны:
- `wait_task` — короткая пауза ожидания (возврат через 0.5 сек).
- `scene_provider_error` — безопасное структурированное сообщение и действия Retry/Main Menu.

## Расширение персонажей
Добавьте спрайт в `images/<char>/` и объявите его в `images.rpy`:
```renpy
image lira happy = "images/lira/lira happy.webp"
```

Экспериментальная Акари проверяет следующий уровень каталога: один персонаж
имеет независимые локальные настройки позы и одежды. Библиотека показывает
21 цельный прозрачный спрайт с родной головой (`3 костюма × 7 поз`), поэтому
геометрия шеи, воротника, рук и волос не собирается из несовместимых генераций.
Для каждого спрайта manifest хранит вычисленный по реальной линии опоры
`root_anchor` и `sprite_offset`; смещённая поза не обязана использовать общий
центр. Отдельная смена выражения отложена до появления согласованного
полноспрайтового набора.
Настройки сохраняются в существующем persistent-формате с безопасными
значениями по умолчанию; старые плоские `variants` остаются совместимыми.

## Отладка
- Отсутствующий хендлер: лог `[play_json_scene] Нет хендлера для act='...'`.
- Пустой реестр: `[play_json_scene] Реестр хендлеров пуст`.
- Очередь: префикс `[queue]` в логе.

## Автоматическая проверка Stage 0–5

Из каталога `Novel` полный baseline запускается так:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\run_stage0_baseline.ps1
```

Runner использует `F:\renpy\renpy-8.3.4-sdk` по умолчанию, синтаксически разбирает fixtures, запускает lint и native testcases в отдельных процессах и отдельных savedir. Saves и diagnostics пишутся только в игнорируемый каталог `test-artifacts`; итог находится в `test-artifacts/stage0/stage0-results.json`. Не запускайте два native runner одновременно: Ren'Py persistent остаётся общим файлом и на Windows может дать `WinError 32`.

Обычный case получает `PASS` только при exit code 0 и отсутствии свежих `traceback.txt`/`errors.txt`; это важно, потому что Ren'Py 8.3.4 может вернуть 0 после игрового исключения. Матрица покрывает контракт, handlers, пошаговый cursor, save/load, rollback 1/3/10, History, save metadata, hard checkpoint паузы, очередь, provider errors/retry и настоящую autosave-load boundary.

Последний полный одиночный прогон 2026-10-24: JSON fixtures `37/37`, lint `PASS`, native testcases `101/101`, `overall_passed=true`, свежих error diagnostics нет. В матрицу входят regression-сценарии всех мутаций story builder/asset library, валидного и невалидного запуска истории, сохранения focus через screen rebuild, mouse caret и переходов Up/Down по перенесённым и пустым строкам. Отдельный `tools/run_gui_visual_matrix.ps1` подтверждает small/touch варианты главного меню, story builder и asset library.

Проверка текущего GUI/demo-среза 2026-10-29: Ren'Py lint `PASS`, small/touch visual matrix `PASS`, новые theme, product-GUI, demo и character-slot cases проходят в изолированных savedir; Python-suite orchestrator — `30/30`. Один cumulative запуск завис на `demo_story_history_visual`, после чего тот же case прошёл изолированно без свежих diagnostics. Полный baseline текущего worktree не заявляется зелёным: 38 отслеживаемых `game/test_fixtures/*` удалены локально и не входят в этот коммит; без решения об их восстановлении runner не может воспроизвести исторический `101/101`.

UI-polish 2026-10-30: generator regressions `4/4`, Ren'Py lint `PASS`, focused cases для namebox, hover, 65 уникальных speaker colors, save-title escaping/fallback и visual component — `5/5`. Сквозной `demo_story_save_load_resume` повторно завис без свежего traceback и не заявляется зелёным; реальные `FileJson`/`FileTime`, JSON metadata сохранения и общий title-component проверены отдельно.

`PlaybackState.state_version == 2` — текущая совместимая версия save-state. Старые или повреждённые состояния не мигрируются неявно: после load они fail-closed переводятся в структурированную ошибку до вызова handler.

## Документация проекта

- [План завершения Ren'Py-клиента](docs/renpy-client-completion-plan.md) — этапы, критерии готовности и оставшаяся ручная приёмка GUI.
- [Журнал решений](docs/decision-log.md) — архитектурные решения, альтернативы, компромиссы и подтверждающие тесты для пояснительной записки.

## Требования окружения
- Ren'Py 8.x (Python 3).
- MongoDB (локально, `mongodb://localhost:27017/`).
- Пакеты Python (pymongo и зависимости лежат в `game/python-packages`).

## Минимальный запуск
1. Запустите MongoDB. Без неё клиент покажет управляемую ошибку `provider_offline`, а не будет ждать стандартный длинный timeout драйвера.
2. Откройте проект в Ren'Py Launcher.
3. Старт игры (`Start`): создаст очередь из `prefetch_depth` задач.
4. По мере готовности файлов сцены будут автоматически проигрываться без ручного вмешательства.

## Формат именования сцен
Имя файла сцены соответствует `_id` задачи: `scene_<task_id>.json`.



