init -35 python:
    DEMO_STORY_METADATA_PATH = "demo_story/story_metadata.json"
    DEMO_STORY_FIXTURES = (
        ("demo_story/scene_01_corridor.json", "demo_after_bell_01"),
        ("demo_story/scene_02_rooftop.json", "demo_after_bell_02"),
        ("demo_story/scene_03_promise.json", "demo_after_bell_03"),
    )


    class DemoStorySceneProvider(object):
        """Deterministic metadata-first provider used by the playable demo."""

        def poll(self, session):
            if session.provider_cursor == 0:
                try:
                    metadata = load_story_metadata_file(DEMO_STORY_METADATA_PATH)
                except StoryMetadataError as error:
                    return SceneProviderResult(
                        "error",
                        session=session,
                        error=SceneProviderError(
                            "story_metadata_invalid",
                            "poll",
                            error.message,
                            retryable=False,
                            path=error.path,
                            source="story_metadata",
                        ),
                    )
                return SceneProviderResult(
                    "metadata",
                    session=session.replaced(provider_cursor=1),
                    story_metadata=metadata,
                )

            fixture_index = session.provider_cursor - 1
            if fixture_index >= len(DEMO_STORY_FIXTURES):
                return SceneProviderResult("waiting", session=session)

            relative_path, scene_id = DEMO_STORY_FIXTURES[fixture_index]
            prepared = prepare_json_scene_file(relative_path, expected_scene_id=scene_id)
            if prepared.phase == "error":
                return SceneProviderResult(
                    "error",
                    session=session,
                    scene_ref=scene_id,
                    error=_provider_error_from_playback(
                        prepared.last_error,
                        operation="prepare",
                        task_id=scene_id,
                        retryable=False,
                    ),
                    playback_state=prepared,
                )
            return SceneProviderResult(
                "ready",
                session=session,
                scene_ref=scene_id,
                playback_state=prepared,
            )

        def acknowledge(self, session, scene_ref):
            return SceneProviderResult(
                "acknowledged",
                session=session.replaced(provider_cursor=session.provider_cursor + 1),
                scene_ref=scene_ref,
            )

        def report_failure(self, session, scene_ref, playback_error):
            return None


    SCENE_PROVIDER_FACTORIES["demo_story"] = DemoStorySceneProvider


label demo_story:
    $ renpy.scene()
    $ playback_state = None
    $ scene_session = SceneSessionState(provider_kind="demo_story")
    $ scene_client_start()
    jump play_next_scene
