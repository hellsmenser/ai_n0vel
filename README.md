# AI Novel (Diploma)

Проект — визуальная новелла на Ren'Py с динамической генерацией сцен. Генератор (внешний воркер) пишет JSON-файлы в `game/scenes/`, статус их готовности отслеживается через MongoDB задачи.

## Архитектура (основные файлы)
- `game/script.rpy` — точка входа: метки `start`, `play_next_scene` (игровой цикл). Никакой низкоуровневой логики.
- `game/tasks.rpy` — подключение к MongoDB, функции работы с задачами: `create_task`, `check_status`.
- `game/playback.rpy` — проигрывание одной JSON сцены: `play_json_scene(task_id)`.
- `game/scene_queue.rpy` — очередь префетча N сцен: переменные (`prefetch_depth`, `scene_tasks`, ...), функции `init_scene_queue`, `fill_scene_queue`, `poll_scene_tasks`, `get_next_ready_task_id`, `consume_task`, экраны `wait_task`, `scene_poll`.
- `game/handlers/` — act-хендлеры (обработка шагов диалога). Реестр в `registry.rpy`.
- `game/images.rpy` — объявления спрайтов.
- `game/scenes/scene_<task_id>.json` — файлы сцен (название по `_id` задачи Mongo).

### Поток исполнения
1. `start` вызывает `init_scene_queue(3)` (глубина префетча по умолчанию 3), запускает экран `scene_poll` (фоновый опрос) и прыгает в `play_next_scene`.
2. `scene_poll` каждую секунду вызывает `poll_scene_tasks`, которая обновляет статусы задач и поддерживает очередь длиной `prefetch_depth`.
3. `play_next_scene` ищет готовую задачу (`get_next_ready_task_id`):
   - Если есть — проигрывает её через `play_json_scene`, затем удаляет через `consume_task` и сразу пытается следующую.
   - Если нет — показывает `wait_task` (короткая пауза 0.5s) и повторяет попытку.
4. После проигрывания сцены предыдущая задача удаляется из Mongo (чистим ресурсы), очередь пополняется новой.

### Почему очередь
- Генератор может успеть сделать несколько сцен вперёд: они аккумулируются в `scene_tasks`.
- Фиксированный лимит `prefetch_depth` предотвращает бесконтрольный рост количества задач.
- Гонка статусов снижена: берём сцену только если `status == "done"` и файл существует (не пустой).

## Формат JSON сцены (упрощённо)
```jsonc
{
  "characters": { "lira": "Лира", "kael": "Каэль" },
  "scene": "bg room",
  "dialogue": [
    { "type": "show", "target": "lira neutral" },
    { "type": "line", "speaker": "lira", "text": "Привет!" },
    { "type": "pause", "duration": 0.5 },
    { "type": "transition", "effect": "fade" },
    { "type": "return" }
  ]
}
```

## Act-хендлеры
Каждый элемент `dialogue[]` имеет поле `type`, для которого существует обработчик `handle_<type>(step, chars) -> bool`.
- Возврат `True` = остановить дальнейшую обработку оставшихся шагов (например, `return`, `jump`).
- Реестр формируется через декоратор `@act_handler(name)` или `register_act_handler(name, func)`.
- Получение: `get_act_handlers()`.

### Добавление нового типа
1. Создать файл `game/handlers/<type>.rpy`.
2. Определить функцию и зарегистрировать.
3. Использовать новый `type` в JSON.

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
        return False
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
- `poll_scene_tasks()` — обновляет статусы всех, удаляет ошибочные, восполняет очередь.
- `get_next_ready_task_id()` — выбирает первый `done` с валидным файлом.
- `consume_task(tid)` — удаляет задачу из очереди и из Mongo, обновляет `last_consumed_task_id`.

Экраны:
- `scene_poll` — фоновый опрос (таймер 1.0 сек).
- `wait_task` — короткая пауза ожидания (возврат через 0.5 сек).

## Расширение персонажей
Добавьте спрайт в `images/<char>/` и объявите его в `images.rpy`:
```renpy
image lira happy = "images/lira/lira happy.webp"
```

## Отладка
- Отсутствующий хендлер: лог `[play_json_scene] Нет хендлера для act='...'`.
- Пустой реестр: `[play_json_scene] Реестр хендлеров пуст`.
- Очередь: префикс `[queue]` в логе.

## Требования окружения
- Ren'Py 8.x (Python 3).
- MongoDB (локально, `mongodb://localhost:27017/`).
- Пакеты Python (pymongo и зависимости лежат в `game/python-packages`).

## Минимальный запуск
1. Запустите MongoDB.
2. Откройте проект в Ren'Py Launcher.
3. Старт игры (`Start`): создаст очередь из `prefetch_depth` задач.
4. По мере готовности файлов сцены будут автоматически проигрываться без ручного вмешательства.

## Формат именования сцен
Имя файла сцены соответствует `_id` задачи: `scene_<task_id>.json`.



