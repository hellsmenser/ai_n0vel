init python:
    import copy

    class PlaybackError(object):
        """Save-safe structured diagnostic returned in an error PlaybackState."""

        def __init__(self, code, path, message):
            self.code = code
            self.path = path
            self.message = message


    class PlaybackActionResult(object):
        """Explicit control returned by one JSON action handler."""

        def __init__(self, kind, target=None, error=None):
            self.kind = kind
            self.target = target
            self.error = error

        @classmethod
        def continue_(cls):
            return cls("continue")

        @classmethod
        def scene_end(cls):
            return cls("scene_end")

        @classmethod
        def goto(cls, target):
            return cls("goto", target=target)

        @classmethod
        def failed(cls, error):
            return cls("error", error=error)


    class PlaybackResult(object):
        """Result returned by the Ren'Py playback labels."""

        def __init__(self, state, control):
            self.state = state
            self.control = control


    class PlaybackState(object):
        """Serializable prepared-scene state.

        The snapshot is defensively copied on input and output. Callers change
        progress by creating a new state with ``with_step_index`` instead of
        editing the prepared scene in place.
        """

        def __init__(self, scene_id=None, schema_version=None, content_hash=None,
                     snapshot=None, step_index=0, scene_variables=None,
                     branch_trace=None, phase="ready", last_error=None,
                     migrated_from_schema=None, state_version=2):
            self.state_version = state_version
            self.scene_id = scene_id
            self.schema_version = schema_version
            self.content_hash = content_hash
            self._snapshot = copy.deepcopy(snapshot) if snapshot is not None else None
            self.step_index = step_index
            self.scene_variables = copy.deepcopy(scene_variables or {})
            self.branch_trace = copy.deepcopy(branch_trace or [])
            self.phase = phase
            self.last_error = last_error
            self.migrated_from_schema = migrated_from_schema

        @property
        def snapshot(self):
            return copy.deepcopy(self._snapshot)

        def with_step_index(self, index):
            if isinstance(index, bool) or not isinstance(index, int) or index < 0:
                raise ValueError("step index must be a non-negative integer")
            return PlaybackState(
                scene_id=self.scene_id,
                schema_version=self.schema_version,
                content_hash=self.content_hash,
                snapshot=self._snapshot,
                step_index=index,
                scene_variables=self.scene_variables,
                branch_trace=self.branch_trace,
                phase=self.phase,
                last_error=self.last_error,
                migrated_from_schema=self.migrated_from_schema,
                state_version=self.state_version,
            )

        def _replace(self, step_index=None, branch_trace=None, phase=None,
                     last_error=None):
            return PlaybackState(
                scene_id=self.scene_id,
                schema_version=self.schema_version,
                content_hash=self.content_hash,
                snapshot=self._snapshot,
                step_index=self.step_index if step_index is None else step_index,
                scene_variables=self.scene_variables,
                branch_trace=self.branch_trace if branch_trace is None else branch_trace,
                phase=self.phase if phase is None else phase,
                last_error=last_error,
                migrated_from_schema=self.migrated_from_schema,
                state_version=self.state_version,
            )

        def started(self):
            if self.phase != "ready":
                raise ValueError("only a ready playback can start")
            return self._replace(phase="playing")

        def current_action(self):
            snapshot = self.snapshot
            if snapshot is None:
                return None
            dialogue = snapshot.get("dialogue", [])
            if self.step_index >= len(dialogue):
                return None
            return copy.deepcopy(dialogue[self.step_index])

        def after_success(self, result):
            if self.phase != "playing":
                raise ValueError("only a playing playback can advance")
            if not isinstance(result, PlaybackActionResult):
                raise ValueError("handler must return PlaybackActionResult")
            if result.kind not in ("continue", "scene_end", "goto"):
                raise ValueError("handler returned unsupported control")

            trace = self.branch_trace
            if result.kind == "goto":
                trace = trace + [{
                    "kind": "goto",
                    "step_index": self.step_index,
                    "target": result.target,
                }]
            next_index = self.step_index + 1
            dialogue_length = len(self._snapshot.get("dialogue", []))
            next_phase = "completed" if (
                result.kind in ("scene_end", "goto") or
                next_index >= dialogue_length
            ) else "playing"
            return self._replace(
                step_index=next_index,
                branch_trace=trace,
                phase=next_phase,
            )

        def failed(self, error):
            if not isinstance(error, PlaybackError):
                raise ValueError("playback failure requires PlaybackError")
            return self._replace(phase="error", last_error=error)

        def retry_current(self):
            """Retry only the action whose failure left the cursor in place."""
            if self.phase != "error" or not isinstance(self.last_error, PlaybackError):
                raise ValueError("only a failed playback can retry")
            return self._replace(phase="playing", last_error=None)

        def completed(self):
            return self._replace(phase="completed")


default playback_state = None
