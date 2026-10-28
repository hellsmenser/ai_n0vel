init -20 python:
    # Ren'Py 8.3's Input accepts newlines, but it does not place the caret
    # from a mouse click and does not implement visual-line Up/Down movement.
    # Keep the change local to the two authoring fields instead of changing
    # the engine-wide Input behaviour.
    import builtins

    _project_multiline_input_state = builtins.dict()

    class ProjectMultilineInput(renpy.display.behavior.Input):
        def __init__(self, editor_id, *args, **kwargs):
            self.editor_id = editor_id
            self._preferred_x = None
            self._last_render_size = (0, 0)
            self._cache_ready = False
            cached = _project_multiline_input_state.get(editor_id)

            # The caret mapper intentionally works one source codepoint per
            # rendered glyph. HarfBuzz ligatures (for example "fi") break
            # that invariant, so authoring fields use Ren'Py's freetype
            # shaper locally instead of changing the engine-wide default.
            kwargs.setdefault("shaper", "freetype")

            super(ProjectMultilineInput, self).__init__(*args, **kwargs)

            self._cache_ready = True
            self._restore_cached_caret(cached)

        def _restore_cached_caret(self, cached):
            if cached is not None and cached[0] == self.content:
                self.caret_pos = min(max(int(cached[1]), 0), len(self.content))
                self._preferred_x = cached[2]
                self.update_text(self.content, self.editable)
            else:
                self._remember_caret()

        def _remember_caret(self):
            if self._cache_ready:
                _project_multiline_input_state[self.editor_id] = (
                    self.content,
                    self.caret_pos,
                    self._preferred_x,
                )

        def update_text(self, new_content, editable, check_size=False):
            super(ProjectMultilineInput, self).update_text(new_content, editable, check_size)
            self._remember_caret()

        def per_interact(self):
            cached = _project_multiline_input_state.get(self.editor_id)
            self._cache_ready = False
            super(ProjectMultilineInput, self).per_interact()
            self._cache_ready = True
            self._restore_cached_caret(cached)

        def render(self, width, height, st, at):
            rv = super(ProjectMultilineInput, self).render(width, height, st, at)
            self._last_render_size = rv.get_size()
            return rv

        def _layout_geometry(self):
            layout = self.get_layout()
            if layout is None:
                return None, [], None

            logical_index = 0
            line_boundaries = []
            caret_geometry = None

            for line_number, line in enumerate(layout.lines):
                boundaries = []

                for glyph in line.glyphs:
                    # The caret is inserted into the Text as an embedded
                    # displayable. It has no corresponding source character.
                    if glyph.character == 0xfffc:
                        caret_geometry = (line_number, float(glyph.x))
                        continue

                    # Ren'Py represents an empty paragraph with a synthetic
                    # zero-width-space glyph. It has no character in the
                    # Input content, but still needs a clickable caret stop.
                    if glyph.character == 0x200b and (
                            logical_index >= len(self.content)
                            or self.content[logical_index] != "\u200b"):
                        if not boundaries:
                            boundaries.append((float(glyph.x), logical_index))
                        continue

                    if logical_index >= len(self.content):
                        continue

                    if not boundaries:
                        boundaries.append((float(glyph.x), logical_index))

                    boundaries.append((float(glyph.x + glyph.advance), logical_index + 1))
                    logical_index += 1

                if not boundaries and caret_geometry is not None and caret_geometry[0] == line_number:
                    boundaries.append((caret_geometry[1], self.caret_pos))

                line_boundaries.append((line, boundaries))

                # A hard newline belongs to the paragraph boundary, not to a
                # rendered glyph. Consume exactly one newline per paragraph;
                # consuming all of them would collapse empty lines.
                if line.eop and logical_index < len(self.content) and self.content[logical_index] == "\n":
                    logical_index += 1

            return layout, line_boundaries, caret_geometry

        @staticmethod
        def _nearest_line(line_boundaries, y):
            if not line_boundaries:
                return None

            for line_number, (line, _boundaries) in enumerate(line_boundaries):
                if line.y <= y <= line.y + line.height:
                    return line_number

            return min(
                range(len(line_boundaries)),
                key=lambda i: abs(y - (line_boundaries[i][0].y + line_boundaries[i][0].height / 2.0)),
            )

        @staticmethod
        def _nearest_boundary(boundaries, x):
            if not boundaries:
                return None
            return min(boundaries, key=lambda item: abs(item[0] - x))[1]

        def _set_caret(self, position, preserve_column=False):
            if position is None:
                return False

            self.caret_pos = min(max(int(position), 0), len(self.content))
            if not preserve_column:
                self._preferred_x = None
            self.update_text(self.content, self.editable)
            renpy.display.render.redraw(self, 0)
            return True

        def _caret_from_point(self, x, y):
            layout, line_boundaries, _caret_geometry = self._layout_geometry()
            if layout is None:
                return None

            layout_x = x * layout.oversample - layout.add_left
            layout_y = y * layout.oversample - layout.add_top
            line_number = self._nearest_line(line_boundaries, layout_y)
            if line_number is None:
                return None

            return self._nearest_boundary(line_boundaries[line_number][1], layout_x)

        def _move_vertical(self, direction):
            _layout, line_boundaries, caret_geometry = self._layout_geometry()
            if caret_geometry is None:
                return False

            line_number, caret_x = caret_geometry
            target_line = line_number + direction
            if target_line < 0 or target_line >= len(line_boundaries):
                return False

            if self._preferred_x is None:
                self._preferred_x = caret_x

            target = self._nearest_boundary(line_boundaries[target_line][1], self._preferred_x)
            return self._set_caret(target, preserve_column=True)

        def event(self, ev, x, y, st):
            pygame = renpy.display.behavior.pygame
            map_event = renpy.display.behavior.map_event

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                width, height = self._last_render_size
                if 0 <= x <= width and 0 <= y <= height:
                    if self.value is not None:
                        renpy.set_editable_input_value(self.value, True)
                    self.editable = True
                    if self._set_caret(self._caret_from_point(x, y)):
                        # Refresh every Input displayable so only the clicked
                        # value remains editable. The caret cache restores the
                        # position after screen reconstruction.
                        renpy.restart_interaction()
                        raise renpy.display.core.IgnoreEvent()

            if self.multiline and map_event(ev, "input_up"):
                if self._move_vertical(-1):
                    raise renpy.display.core.IgnoreEvent()

            if self.multiline and map_event(ev, "input_down"):
                if self._move_vertical(1):
                    raise renpy.display.core.IgnoreEvent()

            if (
                map_event(ev, "input_left")
                or map_event(ev, "input_right")
                or map_event(ev, "input_jump_word_left")
                or map_event(ev, "input_jump_word_right")
                or map_event(ev, "input_home")
                or map_event(ev, "input_end")
                or ev.type in (pygame.KEYDOWN, pygame.TEXTINPUT, pygame.TEXTEDITING)
            ):
                self._preferred_x = None

            return super(ProjectMultilineInput, self).event(ev, x, y, st)
