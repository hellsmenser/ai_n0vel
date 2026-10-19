init python:
    LINE_MIDDLEWARES = []

    def register_line_middleware(fn, phase="post"):
        """Register a line hook that runs before or after ``renpy.say``."""
        if phase not in ("pre", "post"):
            raise ValueError("line middleware phase must be pre or post")
        fn._line_mw_phase = phase
        LINE_MIDDLEWARES.append(fn)
        return fn

    def _apply_line_middlewares(step, who, text, phase):
        for middleware in LINE_MIDDLEWARES:
            if getattr(middleware, "_line_mw_phase", "post") != phase:
                continue
            result = middleware(step, who, text)
            if phase == "pre" and isinstance(result, str):
                text = result
        return text

    def handle_line(step, chars):
        who = chars.get(step.get("speaker"))
        text = _apply_line_middlewares(
            step,
            who,
            escape_dynamic_text(step.get("text")),
            phase="pre",
        )
        renpy.say(who, text)
        _apply_line_middlewares(step, who, text, phase="post")
        return PlaybackActionResult.continue_()

    register_act_handler("line", handle_line)
