import pytest
from unittest.mock import patch, MagicMock

from src.classes.mutual_action.impart import Impart


def _make_avatar(base_world, name: str, level: int, gender):
    from src.classes.core.avatar import Avatar
    from src.classes.age import Age
    from src.systems.cultivation import Realm, CultivationProgress
    from src.systems.time import Year, Month, create_month_stamp
    from src.classes.root import Root
    from src.classes.alignment import Alignment
    from src.utils.id_generator import get_avatar_id

    avatar = Avatar(
        world=base_world,
        name=name,
        id=get_avatar_id(),
        birth_month_stamp=create_month_stamp(Year(1900), Month.JANUARY),
        age=Age(100, Realm.Nascent_Soul),
        gender=gender,
        pos_x=0,
        pos_y=0,
        root=Root.GOLD,
        personas=[],
        alignment=Alignment.RIGHTEOUS,
    )
    avatar.cultivation_progress = CultivationProgress(level=level, exp=0)
    avatar.weapon = MagicMock()
    avatar.weapon.get_detailed_info.return_value = "Test Weapon"
    base_world.avatar_manager.avatars[avatar.name] = avatar
    return avatar


class TestImpartLineageDownwardOnly:
    @pytest.fixture
    def avatars(self, base_world):
        from src.classes.core.avatar import Gender

        grandparent = _make_avatar(base_world, "Grandparent", 100, Gender.MALE)
        parent = _make_avatar(base_world, "Parent", 70, Gender.FEMALE)
        child = _make_avatar(base_world, "Child", 40, Gender.MALE)
        grandchild = _make_avatar(base_world, "Grandchild", 10, Gender.FEMALE)

        grandmaster = _make_avatar(base_world, "Grandmaster", 100, Gender.MALE)
        master = _make_avatar(base_world, "Master", 70, Gender.FEMALE)
        disciple = _make_avatar(base_world, "Disciple", 40, Gender.MALE)
        granddisciple = _make_avatar(base_world, "Granddisciple", 10, Gender.FEMALE)

        # Family links:
        grandparent.acknowledge_child(parent)
        parent.acknowledge_child(child)          # direct parent -> child
        parent.acknowledge_child(grandchild)     # enables grandparent -> grandchild at depth=2

        # Sect links:
        grandmaster.accept_disciple(master)
        master.accept_disciple(disciple)         # direct master -> disciple
        master.accept_disciple(granddisciple)    # enables grandmaster -> granddisciple at depth=2

        return {
            "grandparent": grandparent,
            "parent": parent,
            "child": child,
            "grandchild": grandchild,
            "grandmaster": grandmaster,
            "master": master,
            "disciple": disciple,
            "granddisciple": granddisciple,
        }

    def _can_start(self, giver, target):
        action = Impart(giver, giver.world)
        with patch("src.classes.observe.is_within_observation", return_value=True):
            return action.can_start(target_avatar=target)

    def test_parent_to_child_true(self, avatars):
        can_start, _ = self._can_start(avatars["parent"], avatars["child"])
        assert can_start is True

    def test_child_to_parent_false(self, avatars):
        can_start, _ = self._can_start(avatars["child"], avatars["parent"])
        assert can_start is False

    def test_grandparent_to_grandchild_true_depth_2(self, avatars):
        can_start, _ = self._can_start(avatars["grandparent"], avatars["grandchild"])
        assert can_start is True

    def test_master_to_disciple_true(self, avatars):
        can_start, _ = self._can_start(avatars["master"], avatars["disciple"])
        assert can_start is True

    def test_disciple_to_master_false(self, avatars):
        can_start, _ = self._can_start(avatars["disciple"], avatars["master"])
        assert can_start is False

    def test_grandmaster_to_granddisciple_true_depth_2(self, avatars):
        can_start, _ = self._can_start(avatars["grandmaster"], avatars["granddisciple"])
        assert can_start is True
