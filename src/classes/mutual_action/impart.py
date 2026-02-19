from __future__ import annotations

from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from src.i18n import t
from .mutual_action import MutualAction
from src.classes.action.cooldown import cooldown_action
from src.classes.event import Event
from src.classes.relation.relation import Relation
from src.utils.config import CONFIG

if TYPE_CHECKING:
    from src.classes.core.avatar import Avatar


@cooldown_action
class Impart(MutualAction):
    """Impart cultivation knowledge to a downstream junior."""

    # i18n IDs
    ACTION_NAME_ID = "impart_action_name"
    DESC_ID = "impart_description"
    REQUIREMENTS_ID = "impart_requirements"

    EMOJI = "📉"
    PARAMS = {"target_avatar": "AvatarName"}
    FEEDBACK_ACTIONS = ["Accept", "Reject"]
    ACTION_CD_MONTHS: int = 6

    MAX_DEPTH_FAMILY: int = 2
    MAX_DEPTH_SECT: int = 2
    DOWNWARD_EDGE_RELATIONS = {Relation.IS_CHILD_OF, Relation.IS_DISCIPLE_OF}

    def _get_template_path(self) -> Path:
        return CONFIG.paths.templates / "mutual_action.txt"

    def _is_descendant_by_relation(
        self,
        target: "Avatar",
        edge_set: set[Relation],
        max_depth_family: int,
        max_depth_sect: int,
    ) -> bool:
        """Local BFS from giver over relation edges only."""
        if target is self.avatar:
            return False

        queue = deque([(self.avatar, 0, 0)])
        visited: set[tuple[str, int, int]] = {(str(self.avatar.id), 0, 0)}

        while queue:
            node, family_depth, sect_depth = queue.popleft()
            relations = getattr(node, "relations", {}) or {}
            for nxt, rel in relations.items():
                if rel not in edge_set:
                    continue

                next_family_depth = family_depth + (1 if rel == Relation.IS_CHILD_OF else 0)
                next_sect_depth = sect_depth + (1 if rel == Relation.IS_DISCIPLE_OF else 0)
                if next_family_depth > max_depth_family or next_sect_depth > max_depth_sect:
                    continue

                if nxt is target:
                    return True

                state = (str(nxt.id), next_family_depth, next_sect_depth)
                if state in visited:
                    continue
                visited.add(state)
                queue.append((nxt, next_family_depth, next_sect_depth))

        return False

    def _is_allowed_downward_target(self, target: "Avatar") -> bool:
        return self._is_descendant_by_relation(
            target=target,
            edge_set=self.DOWNWARD_EDGE_RELATIONS,
            max_depth_family=self.MAX_DEPTH_FAMILY,
            max_depth_sect=self.MAX_DEPTH_SECT,
        )

    def _can_start(self, target: "Avatar") -> tuple[bool, str]:
        """Check start conditions specific to impart."""
        from src.classes.observe import is_within_observation

        if not is_within_observation(self.avatar, target):
            return False, t("Target not within interaction range")

        if not self._is_allowed_downward_target(target):
            return False, t("Target is not your downstream junior")

        level_diff = self.avatar.cultivation_progress.level - target.cultivation_progress.level
        if level_diff < 20:
            return False, t(
                "Level difference insufficient, need 20 levels (current gap: {diff} levels)",
                diff=level_diff,
            )

        return True, ""

    def start(self, target_avatar: "Avatar|str") -> Event:
        target = self._get_target_avatar(target_avatar)
        target_name = target.name if target is not None else str(target_avatar)
        rel_ids = [self.avatar.id]
        if target is not None:
            rel_ids.append(target.id)
        content = t(
            "{giver} imparts cultivation knowledge to {receiver}",
            giver=self.avatar.name,
            receiver=target_name,
        )
        event = Event(
            self.world.month_stamp,
            content,
            related_avatars=rel_ids,
        )
        self._impart_success = False
        self._impart_exp_gain = 0
        return event

    def _settle_feedback(self, target_avatar: "Avatar", feedback_name: str) -> None:
        fb = str(feedback_name).strip()
        if fb == "Accept":
            self._apply_impart_gain(target_avatar)
            self._impart_success = True
        else:
            self._impart_success = False

    def _apply_impart_gain(self, target: "Avatar") -> None:
        exp_gain = 100 * 5 * 4
        target.cultivation_progress.add_exp(exp_gain)
        self._impart_exp_gain = exp_gain

    async def finish(self, target_avatar: "Avatar|str") -> list[Event]:
        target = self._get_target_avatar(target_avatar)
        events: list[Event] = []
        success = self._impart_success
        if target is None:
            return events

        if success:
            gain = int(self._impart_exp_gain)
            result_text = t(
                "{avatar} gained cultivation experience +{exp} points",
                avatar=target.name,
                exp=gain,
            )
            result_event = Event(
                self.world.month_stamp,
                result_text,
                related_avatars=[self.avatar.id, target.id],
            )
            events.append(result_event)

        return events
