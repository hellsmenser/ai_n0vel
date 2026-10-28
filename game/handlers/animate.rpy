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
        tag = target.split()[0]
        previous_transforms = list(
            renpy.game.context().scene_lists.at_list.get("master", {}).get(tag, [])
        )
        previous_transforms.append(
            json_shake(offset=offset, duration=duration, repetitions=repetitions)
        )
        renpy.show(target, at_list=previous_transforms)
        return PlaybackActionResult.continue_()

    register_act_handler("animate", handle_animate)
