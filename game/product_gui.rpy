screen ai_shell_button(label, button_action, width=430, selected=False, button_id=None):
    textbutton label:
        id button_id
        action button_action
        xsize width
        ysize 68
        text_xalign 0.5
        idle_background (theme_compact_button_hover("default", neutral_shell=True) if selected else theme_compact_button_idle("default", neutral_shell=True))
        hover_background theme_compact_button_hover("default", neutral_shell=True)
        selected_idle_background theme_compact_button_hover("default", neutral_shell=True)
        selected_hover_background theme_compact_button_hover("default", neutral_shell=True)
        text_font theme_font("body", theme_id="default", neutral_shell=True)
        text_color theme_color("text", theme_id="default", neutral_shell=True)
        text_hover_color ai_shell_hover_text_color()
        text_selected_color ai_shell_hover_text_color()
        text_size 28


screen ai_shell_back_button(target="main_menu"):
    textbutton "Назад":
        action ShowMenu(target)
        xsize 180
        ysize 56
        text_xalign 0.5
        idle_background theme_compact_button_idle("default", neutral_shell=True)
        hover_background theme_compact_button_hover("default", neutral_shell=True)
        text_font theme_font("body", theme_id="default", neutral_shell=True)
        text_color theme_color("text", theme_id="default", neutral_shell=True)
        text_hover_color ai_shell_hover_text_color()
        text_size 26


style product_gui_button is button
style product_gui_button_text is button_text

style product_gui_button_text:
    size 24


screen story_builder():
    tag menu
    style_prefix "product_gui"

    $ _draft = story_draft_get()
    $ _is_advanced = _draft["mode"] == "advanced"
    $ _can_start = not story_draft_validate(_draft)

    add gui.main_menu_background fit "cover"
    add Solid("#071019E6")

    frame:
        id "story_builder_root"
        xfill True
        yfill True
        margin (54, 42)
        padding (58, 42)
        background theme_frame("pause_history_frame.png", theme_id="default", neutral_shell=True, legacy="gui/frame.png")

        vbox:
            xfill True
            yfill True
            spacing 24

            hbox:
                xfill True
                use ai_shell_back_button("main_menu")

                vbox:
                    xfill True
                    xalign 0.5
                    text "Создание новой истории":
                        xalign 0.5
                        size 46
                        font theme_font("title", theme_id="default", neutral_shell=True)
                        color theme_color("text", theme_id="default", neutral_shell=True)
                    text "Задайте важное, а недостающие детали ИИ придумает сам.":
                        xalign 0.5
                        size 23
                        font theme_font("body", theme_id="default", neutral_shell=True)
                        color theme_color("muted", theme_id="default", neutral_shell=True)

                null width 180

            hbox:
                xalign 0.5
                spacing 18
                use ai_shell_button("Базовый", Function(product_gui_update, story_draft_set_mode, "basic"), width=360, selected=not _is_advanced, button_id="story_mode_basic")
                use ai_shell_button("Продвинутый", Function(product_gui_update, story_draft_set_mode, "advanced"), width=360, selected=_is_advanced, button_id="story_mode_advanced")

            side "c r":
                ymaximum 570
                xfill True
                yfill True
                spacing 20

                viewport:
                    id "story_builder_viewport"
                    yinitial 0.0
                    mousewheel True
                    draggable True
                    pagekeys True

                    vbox:
                        xfill True
                        spacing 28

                        text "Жанры":
                            size 30
                            font theme_font("title", theme_id="default", neutral_shell=True)
                            color theme_color("accent", theme_id="default", neutral_shell=True)

                        grid 4 2:
                            xfill True
                            spacing 14
                            for genre_id, genre_label in STORY_GENRES:
                                textbutton genre_label:
                                    id ("story_genre_" + genre_id)
                                    action Function(product_gui_update, story_draft_toggle_genre, genre_id)
                                    selected genre_id in _draft["genres"]
                                    xfill True
                                    ysize 58
                                    text_xalign 0.5
                                    idle_background theme_compact_button_idle("default", neutral_shell=True)
                                    hover_background theme_compact_button_hover("default", neutral_shell=True)
                                    selected_idle_background theme_compact_button_hover("default", neutral_shell=True)
                                    selected_hover_background theme_compact_button_hover("default", neutral_shell=True)
                                    text_font theme_font("body", theme_id="default", neutral_shell=True)
                                    text_color theme_color("text", theme_id="default", neutral_shell=True)
                                    text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)

                        text "Мои пожелания":
                            size 30
                            font theme_font("title", theme_id="default", neutral_shell=True)
                            color theme_color("accent", theme_id="default", neutral_shell=True)

                        frame:
                            xfill True
                            ysize (210 if not _is_advanced else 150)
                            padding (24, 18)
                            background Solid("#101820E8")
                            add ProjectMultilineInput(
                                "story_wishes",
                                value=StoryDraftInputValue("wishes"),
                                length=STORY_WISHES_MAX,
                                multiline=True,
                                copypaste=True,
                                font=theme_font("body", theme_id="default", neutral_shell=True),
                                color=theme_color("text", theme_id="default", neutral_shell=True),
                            ):
                                id "story_wishes_input"

                        if not _is_advanced:
                            text "ИИ предложит название, тон, место действия, состав персонажей и стиль интерфейса.":
                                size 22
                                font theme_font("body", theme_id="default", neutral_shell=True)
                                color theme_color("muted", theme_id="default", neutral_shell=True)
                                xmaximum 1450

                        if _is_advanced:
                            hbox:
                                xfill True
                                spacing 24

                                vbox:
                                    xfill True
                                    spacing 16
                                    text "Рабочее название" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                                    frame:
                                        xfill True
                                        ysize 58
                                        padding (18, 10)
                                        background Solid("#101820E8")
                                        add ProjectMultilineInput("story_title", value=StoryDraftInputValue("title_seed"), length=STORY_SHORT_TEXT_MAX, font=theme_font("body", theme_id="default", neutral_shell=True), color=theme_color("text", theme_id="default", neutral_shell=True)):
                                            id "story_title_input"
                                vbox:
                                    xfill True
                                    spacing 16
                                    text "Место действия" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                                    frame:
                                        xfill True
                                        ysize 58
                                        padding (18, 10)
                                        background Solid("#101820E8")
                                        add ProjectMultilineInput("story_setting", value=StoryDraftInputValue("setting"), length=STORY_WISHES_MAX, font=theme_font("body", theme_id="default", neutral_shell=True), color=theme_color("text", theme_id="default", neutral_shell=True)):
                                            id "story_setting_input"

                            text "Тон" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                            hbox:
                                spacing 12
                                for tone_id, tone_label in STORY_TONES:
                                    textbutton tone_label action Function(product_gui_update, story_draft_set, "tone", tone_id) selected _draft["tone"] == tone_id xsize 250 ysize 54 text_xalign 0.5 idle_background theme_compact_button_idle("default", neutral_shell=True) hover_background theme_compact_button_hover("default", neutral_shell=True) selected_idle_background theme_compact_button_hover("default", neutral_shell=True) text_font theme_font("body", theme_id="default", neutral_shell=True) text_color theme_color("text", theme_id="default", neutral_shell=True) text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)

                            hbox:
                                xfill True
                                spacing 32
                                vbox:
                                    spacing 12
                                    text "Объём" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                                    hbox:
                                        spacing 10
                                        for value_id, value_label in STORY_LENGTHS:
                                            textbutton value_label action Function(product_gui_update, story_draft_set, "length", value_id) selected _draft["length"] == value_id xsize 190 ysize 54 text_xalign 0.5 idle_background theme_compact_button_idle("default", neutral_shell=True) hover_background theme_compact_button_hover("default", neutral_shell=True) selected_idle_background theme_compact_button_hover("default", neutral_shell=True) text_font theme_font("body", theme_id="default", neutral_shell=True) text_color theme_color("text", theme_id="default", neutral_shell=True) text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)
                                vbox:
                                    spacing 12
                                    text "Темп" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                                    hbox:
                                        spacing 10
                                        for value_id, value_label in STORY_PACING:
                                            textbutton value_label action Function(product_gui_update, story_draft_set, "pacing", value_id) selected _draft["pacing"] == value_id xsize 210 ysize 54 text_xalign 0.5 idle_background theme_compact_button_idle("default", neutral_shell=True) hover_background theme_compact_button_hover("default", neutral_shell=True) selected_idle_background theme_compact_button_hover("default", neutral_shell=True) text_font theme_font("body", theme_id="default", neutral_shell=True) text_color theme_color("text", theme_id="default", neutral_shell=True) text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)

                            text "Персонажи из включённых ассетов" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                            hbox:
                                spacing 18
                                for asset in asset_catalog_entries("characters", enabled_only=True, include_hidden=False):
                                    textbutton asset["title"] action Function(product_gui_update, story_draft_toggle_cast, asset["id"]) selected asset["id"] in _draft["cast_asset_ids"] xsize 300 ysize 60 text_xalign 0.5 idle_background theme_compact_button_idle("default", neutral_shell=True) hover_background theme_compact_button_hover("default", neutral_shell=True) selected_idle_background theme_compact_button_hover("default", neutral_shell=True) text_font theme_font("body", theme_id="default", neutral_shell=True) text_color theme_color("text", theme_id="default", neutral_shell=True) text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)

                            text "Предпочтительный стиль интерфейса" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True) size 26
                            grid 4 2:
                                spacing 10
                                textbutton "Выбор ИИ" action Function(product_gui_update, story_draft_set_ui, "", "", "") selected not _draft["ui"]["theme_id"] xsize 320 ysize 54 text_xalign 0.5 idle_background theme_compact_button_idle("default", neutral_shell=True) hover_background theme_compact_button_hover("default", neutral_shell=True) selected_idle_background theme_compact_button_hover("default", neutral_shell=True) text_font theme_font("body", theme_id="default", neutral_shell=True) text_color theme_color("text", theme_id="default", neutral_shell=True) text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)
                                for theme_id in THEME_IDS:
                                    textbutton theme_id.replace("_", " ").title() action Function(product_gui_update, story_draft_set_ui, theme_id, "", "") selected _draft["ui"]["theme_id"] == theme_id xsize 320 ysize 54 text_xalign 0.5 idle_background theme_compact_button_idle("default", neutral_shell=True) hover_background theme_compact_button_hover("default", neutral_shell=True) selected_idle_background theme_compact_button_hover("default", neutral_shell=True) text_font theme_font("body", theme_id="default", neutral_shell=True) text_color theme_color("text", theme_id="default", neutral_shell=True) text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)

                vbar:
                    value YScrollValue("story_builder_viewport")
                    xsize 18
                    base_bar theme_frame("scrollbar_track.png", theme_id="default", neutral_shell=True)
                    thumb theme_frame("scrollbar_thumb.png", theme_id="default", neutral_shell=True)

            hbox:
                xfill True
                text ("Выберите хотя бы один жанр или опишите свою идею." if not _can_start else "Черновик готов. Его можно будет изменить позже."):
                    xfill True
                    yalign 0.5
                    font theme_font("body", theme_id="default", neutral_shell=True)
                    color (theme_color("muted", theme_id="default", neutral_shell=True) if _can_start else "#e99a87")
                textbutton "Создать историю":
                    action ProductGuiStartStory()
                    sensitive _can_start
                    xsize 330
                    ysize 64
                    text_xalign 0.5
                    idle_background theme_compact_button_hover("default", neutral_shell=True)
                    hover_background Solid("#53CFE8AA")
                    insensitive_background Solid("#26323DDD")
                    text_font theme_font("body", theme_id="default", neutral_shell=True)
                    text_color theme_color("text", theme_id="default", neutral_shell=True)
                    text_insensitive_color theme_color("muted", theme_id="default", neutral_shell=True)

    key "game_menu" action ShowMenu("main_menu")


screen asset_library():
    tag menu
    style_prefix "product_gui"
    default asset_category = ASSET_CATEGORIES[0][0] if ASSET_CATEGORIES else None
    default selected_asset_id = None
    default description_buffer = ""

    $ _selected_asset = asset_catalog_get(selected_asset_id)
    if _selected_asset is None or _selected_asset["category"] != asset_category:
        $ _category_items = asset_catalog_entries(asset_category, include_hidden=False)
        $ _selected_asset = _category_items[0] if _category_items else None
        $ selected_asset_id = _selected_asset["id"] if _selected_asset else None
        $ description_buffer = asset_catalog_description(selected_asset_id) if selected_asset_id else ""
    $ _constructor = asset_catalog_constructor(selected_asset_id) if _selected_asset else None

    add gui.main_menu_background fit "cover"
    add Solid("#071019E8")

    frame:
        id "asset_library_root"
        xfill True
        yfill True
        margin (46, 38)
        padding (52, 42)
        background theme_frame("pause_history_frame.png", theme_id="default", neutral_shell=True, legacy="gui/frame.png")

        vbox:
            xfill True
            yfill True
            spacing 22

            hbox:
                xfill True
                use ai_shell_back_button("main_menu")
                text "Библиотека ассетов" xfill True xalign 0.5 textalign 0.5 size 46 font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True)
                null width 180

            hbox:
                spacing 14
                for category_id, category_label in ASSET_CATEGORIES:
                    button:
                        id ("asset_category_" + category_id)
                        action Function(product_gui_select_asset_category, category_id)
                        selected asset_category == category_id
                        xsize 300
                        ysize 58
                        idle_background theme_compact_button_idle("default", neutral_shell=True)
                        hover_background theme_compact_button_hover("default", neutral_shell=True)
                        selected_idle_background theme_compact_button_hover("default", neutral_shell=True)
                        text category_label xalign 0.5 yalign 0.5 size 24 font theme_font("body", theme_id="default", neutral_shell=True) color (theme_color("accent", theme_id="default", neutral_shell=True) if asset_category == category_id else theme_color("text", theme_id="default", neutral_shell=True))

            hbox:
                xfill True
                yfill True
                spacing 26

                frame:
                    xsize 760
                    yfill True
                    padding (24, 24)
                    background Solid("#0B141DDD")

                    side "c r":
                        spacing 14
                        viewport:
                            id "asset_cards_viewport"
                            mousewheel True
                            draggable True
                            pagekeys True
                            vpgrid:
                                cols 2
                                spacing 18
                                for asset in asset_catalog_entries(asset_category, include_hidden=False):
                                    button:
                                        id ("asset_card_" + asset["id"])
                                        action Function(product_gui_select_asset, asset["id"])
                                        xsize 330
                                        ysize 330
                                        padding (12, 12)
                                        idle_background theme_compact_button_idle("default", neutral_shell=True)
                                        hover_background theme_compact_button_hover("default", neutral_shell=True)
                                        vbox:
                                            xfill True
                                            spacing 8
                                            fixed:
                                                xfill True
                                                ysize 4
                                                if asset["id"] == selected_asset_id:
                                                    add Solid(theme_color("accent", theme_id="default", neutral_shell=True))
                                            add asset_catalog_card_preview(asset["id"]) xalign 0.5 xysize (290, 205) fit "contain"
                                            text asset["title"] xalign 0.5 font theme_font("title", theme_id="default", neutral_shell=True) color (theme_color("accent", theme_id="default", neutral_shell=True) if asset["id"] == selected_asset_id else theme_color("text", theme_id="default", neutral_shell=True)) size 24
                                            text asset_catalog_description(asset["id"]) xalign 0.5 textalign 0.5 font theme_font("body", theme_id="default", neutral_shell=True) color theme_color("muted", theme_id="default", neutral_shell=True) size 17 xmaximum 300
                        vbar value YScrollValue("asset_cards_viewport") xsize 16 base_bar theme_frame("scrollbar_track.png", theme_id="default", neutral_shell=True) thumb theme_frame("scrollbar_thumb.png", theme_id="default", neutral_shell=True)

                frame:
                    xfill True
                    yfill True
                    padding (32, 28)
                    background Solid("#0B141DEE")

                    if _selected_asset:
                        side "c r":
                            spacing 12
                            viewport:
                                id "asset_detail_viewport"
                                mousewheel True
                                draggable True
                                pagekeys True

                                vbox:
                                    xfill True
                                    spacing 18
                                    hbox:
                                        xfill True
                                        text _selected_asset["title"] xfill True size 36 font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("accent", theme_id="default", neutral_shell=True)
                                        button:
                                            id "asset_toggle"
                                            action Function(product_gui_update, asset_catalog_toggle, _selected_asset["id"])
                                            xsize 190
                                            ysize 54
                                            idle_background theme_compact_button_idle("default", neutral_shell=True)
                                            hover_background theme_compact_button_hover("default", neutral_shell=True)
                                            text ("Включён" if asset_catalog_is_enabled(selected_asset_id) else "Выключен") xalign 0.5 yalign 0.5 size 22 font theme_font("body", theme_id="default", neutral_shell=True) color (theme_color("accent", theme_id="default", neutral_shell=True) if asset_catalog_is_enabled(selected_asset_id) else theme_color("muted", theme_id="default", neutral_shell=True))

                                    if _constructor:
                                        $ _components = asset_catalog_selected_components(selected_asset_id)
                                        hbox:
                                            spacing 22
                                            frame:
                                                xsize 340
                                                ysize 500
                                                padding (12, 12)
                                                background Solid("#101820E8")
                                                fixed:
                                                    add asset_catalog_constructor_preview(selected_asset_id) id "asset_constructor_composite" xalign 0.5 yalign 0.5 xysize (310, 465) fit "contain"

                                            vbox:
                                                xfill True
                                                spacing 12
                                                text "Одежда" id "asset_outfit_section_title" size 23 font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True)
                                                hbox:
                                                    spacing 8
                                                    for option in _constructor["outfits"]:
                                                        textbutton option["title"]:
                                                            id ("asset_component_outfit_" + option["id"])
                                                            action Function(product_gui_update, asset_catalog_select_component, _selected_asset["id"], "outfit", option["id"])
                                                            selected _components["outfit"] == option["id"]
                                                            xsize 155
                                                            ysize 48
                                                            text_xalign 0.5
                                                            idle_background theme_compact_button_idle("default", neutral_shell=True)
                                                            hover_background theme_compact_button_hover("default", neutral_shell=True)
                                                            selected_idle_background theme_compact_button_hover("default", neutral_shell=True)
                                                            text_font theme_font("body", theme_id="default", neutral_shell=True)
                                                            text_color theme_color("text", theme_id="default", neutral_shell=True)
                                                            text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)
                                                            text_size 17

                                                text "Поза" size 23 font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True)
                                                $ _pose_rows = (len(_constructor["poses"]) + 1) // 2
                                                grid 2 _pose_rows:
                                                    spacing 8
                                                    for option in _constructor["poses"]:
                                                        textbutton option["title"]:
                                                            id ("asset_component_pose_" + option["id"])
                                                            action Function(product_gui_update, asset_catalog_select_component, _selected_asset["id"], "pose", option["id"])
                                                            selected _components["pose"] == option["id"]
                                                            xsize 238
                                                            ysize 44
                                                            text_xalign 0.5
                                                            idle_background theme_compact_button_idle("default", neutral_shell=True)
                                                            hover_background theme_compact_button_hover("default", neutral_shell=True)
                                                            selected_idle_background theme_compact_button_hover("default", neutral_shell=True)
                                                            text_font theme_font("body", theme_id="default", neutral_shell=True)
                                                            text_color theme_color("text", theme_id="default", neutral_shell=True)
                                                            text_selected_color theme_color("accent", theme_id="default", neutral_shell=True)
                                                            text_size 17
                                                    if len(_constructor["poses"]) % 2:
                                                        null

                                        text "Для каждой позы используется цельный прозрачный спрайт: голова и одежда не смещаются относительно тела." size 17 font theme_font("body", theme_id="default", neutral_shell=True) color theme_color("muted", theme_id="default", neutral_shell=True) xmaximum 820
                                    else:
                                        text "Доступные варианты" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True) size 24
                                        hbox:
                                            spacing 16
                                            for variant in asset_catalog_variants(selected_asset_id):
                                                button:
                                                    id ("asset_variant_" + variant["id"])
                                                    action Function(product_gui_update, asset_catalog_select_variant, _selected_asset["id"], variant["id"])
                                                    xsize 215
                                                    ysize 255
                                                    padding (10, 10)
                                                    idle_background (theme_compact_button_hover("default", neutral_shell=True) if asset_catalog_selected_variant(selected_asset_id)["id"] == variant["id"] else theme_compact_button_idle("default", neutral_shell=True))
                                                    hover_background theme_compact_button_hover("default", neutral_shell=True)
                                                    vbox:
                                                        xfill True
                                                        add variant["preview"] xalign 0.5 xysize (190, 190) fit "contain"
                                                        text variant["title"] xalign 0.5 font theme_font("body", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True) size 18

                                    text "Описание для ИИ" font theme_font("title", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True) size 24
                                    frame:
                                        xfill True
                                        ysize 150
                                        padding (18, 14)
                                        background Solid("#101820E8")
                                        add ProjectMultilineInput("asset_description", value=ScreenVariableInputValue("description_buffer"), length=ASSET_DESCRIPTION_MAX, multiline=True, copypaste=True, font=theme_font("body", theme_id="default", neutral_shell=True), color=theme_color("text", theme_id="default", neutral_shell=True))
                                    hbox:
                                        xfill True
                                        spacing 14
                                        button:
                                            id "asset_description_reset"
                                            action [SetScreenVariable("description_buffer", _selected_asset["description"]), Function(product_gui_update, asset_catalog_set_description, _selected_asset["id"], "")]
                                            xsize 280
                                            ysize 54
                                            idle_background theme_compact_button_idle("default", neutral_shell=True)
                                            hover_background theme_compact_button_hover("default", neutral_shell=True)
                                            text "Сбросить" xalign 0.5 yalign 0.5 size 22 font theme_font("body", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True)
                                        button:
                                            id "asset_description_save"
                                            action Function(product_gui_update, asset_catalog_set_description, _selected_asset["id"], description_buffer)
                                            xsize 280
                                            ysize 54
                                            idle_background theme_compact_button_hover("default", neutral_shell=True)
                                            hover_background Solid("#53CFE8AA")
                                            text "Сохранить" xalign 0.5 yalign 0.5 size 22 font theme_font("body", theme_id="default", neutral_shell=True) color theme_color("text", theme_id="default", neutral_shell=True)
                            vbar value YScrollValue("asset_detail_viewport") xsize 16 base_bar theme_frame("scrollbar_track.png", theme_id="default", neutral_shell=True) thumb theme_frame("scrollbar_thumb.png", theme_id="default", neutral_shell=True)

    key "game_menu" action ShowMenu("main_menu")
