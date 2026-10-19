transform json_shake(offset=10, duration=0.05, repetitions=1):
    xoffset 0
    block:
        linear duration xoffset offset
        linear duration xoffset -offset
        linear duration xoffset 0
        repeat repetitions


init python:
    def handle_animate(step, chars):
        target = step.get("target")
        effect = step.get("effect")
        if not isinstance(effect, dict) or effect.get("type") != "shake":
            return PlaybackActionResult.continue_()

        # Contract validation bounds these values. Defaults keep migrated v0
        # ``effect: \"shake\"`` scenes deterministic.
        offset = effect.get("xoffset", 10)
        duration = effect.get("duration", 0.05)
        repetitions = effect.get("repeat", 1)
        renpy.show(
            target,
            at_list=[json_shake(offset=offset, duration=duration, repetitions=repetitions)],
        )
        return PlaybackActionResult.continue_()

    register_act_handler("animate", handle_animate)
