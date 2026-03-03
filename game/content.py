"""Read-only content database interface for loading JSON story assets."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ContentDB:
    """
    Read-only access layer for authored JSON content files.

    The intended implementation loads files from 'content/' and exposes
    convenient lookup/listing methods for game systems while keeping content
    mutation out of runtime logic.

    JSON expectations (high level):
    -encounters.json: list[dict] of encounter definitions. Entries are
      expected to include IDs plus metadata such as tags, allowed beat types,
      difficulty bands, prerequisites, and optional thread affinities.
    -locations.json: list[dict] of location definitions keyed by id.
    -npcs.json: list[dict] of NPC definitions keyed by id.
    -items.json: list[dict]' of item definitions keyed by id.
    -templates.json: dict[str, str | dict] of text templates and template
      groups used by game.scene.render_scene(...).
    -threads.json': 'list[dict]' of authored plot-thread templates or seeds.

    Interaction with DMPolicy:
    DMPolicy should treat ContentDB as a read-only source of candidate
    encounters/templates. The policy performs filtering/scoring (beat match,
    trait fit, difficulty fit, novelty penalty, prerequisites) without
    modifying content definitions.
    """

    def __init__(self, content_dir: str = "content") -> None:
        """
        Prepare the content database interface.

        Args:
            content_dir: Path to the directory containing JSON content files.

        Returns:
            None.

        Interaction:
            Future implementation should load and validate JSON schemas here (or
            lazily), then build read-only indexes used by DMPolicy,
            game.scene, and optional NPC logic.
        """
        self.content_dir = Path(content_dir)
        self._locations: dict[str, dict[str, Any]] = {}
        self._encounters: list[dict[str, Any]] = []
        self._templates: dict[str, Any] = {}
        self._threads: list[dict[str, Any]] = []
        # TODO: Load JSON files and validate schema contracts for each file.

    def get_location(self, location_id: str) -> dict[str, Any]:
        """
        Return a location definition by ID.

        Args:
            location_id: Stable location identifier referenced by GameState.

        Returns:
            A location definition dictionary from locations.json.

        Interaction:
            Scene generation and rendering may use location metadata (tags,
            descriptions, exits, ambient variables) to contextualize scenes.
        """
        pass

    def list_encounters(self) -> list[dict[str, Any]]:
        """
        Return all encounter definitions as read-only candidate inputs.

        Returns:
            List of encounter dictionaries authored in encounters.json.

        Interaction:
            DMPolicy is expected to filter these candidates by beat type,
            prerequisites, location, plot-thread relevance, and difficulty
            targets before utility scoring and scene selection.
        """
        pass

    def list_templates(self) -> dict[str, Any]:
        """
        Return template definitions used for scene text rendering.

        Returns:
            Template mapping loaded from templates.json.

        Interaction:
            game.scene.render_scene(...) uses this mapping with scene_spec
            text_vars to perform template selection and variable substitution.
        """
        pass

    def list_threads(self) -> list[dict[str, Any]]:
        """
        Return authored plot-thread seeds/templates.

        Returns:
            List of plot-thread dictionaries loaded from threads.json.

        Interaction:
            The game may instantiate runtime PlotThread objects from these
            definitions during setup or when new story arcs are introduced.
        """
        pass
