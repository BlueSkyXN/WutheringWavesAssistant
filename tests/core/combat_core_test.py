import logging
import time

import pytest

from src.core.combat.combat_core import TeamMemberSelector
from src.core.combat.combat_system import CombatSystem
from src.core.combat.resonator.encore import Encore
from src.core.contexts import Context
from src.core.injector import Container
from src.core.interface import ControlService, WindowService, ImgService
from src.util import img_util, file_util

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def context():
    logger.debug("\n")
    context = Context()
    return context


@pytest.fixture(scope="module")
def container(context):
    container = Container.build(context)
    return container


@pytest.fixture(scope="module")
def control_service(container):
    control_service: ControlService = container.control_service()
    control_service.activate()
    time.sleep(0.2)
    return control_service


@pytest.fixture(scope="module")
def img_service(container):
    img_service: ImgService = container.img_service()
    return img_service


def test_get_team_members(control_service, img_service):
    team_member_selector = TeamMemberSelector(control_service, img_service)
    # img = img_util.read_img(file_util.get_temp_screenshot("screenshot_1746901046_31874794.png"))
    # img = img_util.read_img(file_util.get_temp_screenshot("screenshot_1748341981_13141297.png"))
    team_members = team_member_selector.get_team_members()
