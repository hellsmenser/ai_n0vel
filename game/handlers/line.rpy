init python:
    LINE_MIDDLEWARES = []

    def register_line_middleware(fn, phase="post"):
        """Регистрирует middleware.
        phase: "pre" или "post" — когда вызывать относительно renpy.say.
        Функция сигнатуры (step, who, text) -> text (для pre) или -> None/text (для post)."""
        fn._line_mw_phase = phase
        LINE_MIDDLEWARES.append(fn)
        return fn

    def _apply_line_middlewares(step, who, text, phase):
        for mw in LINE_MIDDLEWARES:
            if getattr(mw, "_line_mw_phase", "post") != phase:
                continue
            try:
                res = mw(step, who, text)
                if phase == "pre" and isinstance(res, str):
                    text = res
            except Exception as e:
                pass
        return text

    # Вспомогательная функция для добавления записи в историю стандартным способом
    def _append_history_entry(who_obj, what_text):
        try:
            from renpy.store import _history_list, HistoryEntry
            who_name = None
            if who_obj is not None:
                who_name = getattr(who_obj, 'name', None) or str(who_obj)
            _history_list.append(HistoryEntry(who=who_name, what=what_text))
        except Exception as e:
            pass

    # --- Middleware реализации ---

    @register_line_middleware
    def mw_history_override(step, who, text):
        """post: переопределяет последнюю запись истории если указан step['history_text']."""
        hist = step.get("history_text")
        if not hist:
            return
        try:
            from renpy.store import _history_list
            if _history_list:
                entry = _history_list[-1]
                # Пытаемся просто заменить поле what (у HistoryEntry оно существует)
                if hasattr(entry, 'what'):
                    entry.what = hist
                else:
                    # если по какой-то причине формат другой — добавляем новую запись
                    _append_history_entry(who, hist)
        except Exception as e:
            pass

    @register_line_middleware
    def mw_history_extra(step, who, text):
        extra = step.get("history_extra")
        if not extra:
            return
        for line in extra:
            _append_history_entry(who, line)

    @register_line_middleware
    def mw_history_inject(step, who, text):
        inject = step.get("history_inject")
        if not inject:
            return
        _append_history_entry(who, inject)


    def handle_line(step, chars):
        who = chars.get(step.get("speaker"))
        text = step.get("text")
        text = _apply_line_middlewares(step, who, text, phase="pre")
        renpy.say(who, text)
        _apply_line_middlewares(step, who, text, phase="post")
        return False

    register_act_handler("line", handle_line)
