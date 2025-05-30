import logging
import threading
import time

from src.core.combat.combat_core import TeamMemberSelector
from src.core.combat.resonator.changli import Changli
from src.core.combat.resonator.encore import Encore
from src.core.combat.resonator.jinhsi import Jinhsi
from src.core.combat.resonator.shorekeeper import Shorekeeper
from src.core.combat.resonator.verina import Verina
from src.core.exceptions import StopError
from src.core.interface import ControlService, ImgService

logger = logging.getLogger(__name__)


class CombatSystem:

    def __init__(self, control_service: ControlService, img_service: ImgService):
        self.control_service: ControlService = control_service
        self.img_service: ImgService = img_service

        self.team_member_selector = TeamMemberSelector(self.control_service, self.img_service)

        self.is_async = False
        self.event = threading.Event()
        # self._thread = threading.Thread(target=self.run)
        # self._thread.daemon = True
        self._thread = None
        self._delay_seconds = None
        self._delay_time = None
        self._lock = threading.Lock()

        self.jinhsi = Jinhsi(self.control_service, self.img_service)
        self.changli = Changli(self.control_service, self.img_service)
        self.shorekeeper = Shorekeeper(self.control_service, self.img_service)
        self.encore = Encore(self.control_service, self.img_service)
        self.verina = Verina(self.control_service, self.img_service)

        self.resonator_map = {
            self.jinhsi.name_en: self.jinhsi,
            self.changli.name_en: self.changli,
            self.shorekeeper.name_en: self.shorekeeper,
            self.encore.name_en: self.encore,
            self.verina.name_en: self.verina,
        }

        self.is_nightmare: bool = False

    def run(self, event: threading.Event):
        resonators = []
        member_names = self.team_member_selector.get_team_members()
        for member_name in member_names:
            resonators.append(self.resonator_map.get(member_name))
        index = 0
        seq_length = len(resonators)
        while True:
            # logger.debug("member: %s", index + 1)
            if not event.is_set():
                # logger.info("暂停中，event.is_set()")
                time.sleep(0.3)
                continue
            if self.is_async and self._delay_time - time.monotonic() < 0.0:
                # logger.info("暂停中，delay_time")
                time.sleep(0.3)
                continue
            # logger.info("index：%s", index)
            if self.is_nightmare:
                self.control_service.fight_tap("F", 0.001)
            if index % 3 == 0:
                self.control_service.activate()
            if index % 2 == 0:
                self.control_service.camera_reset()
            resonator = resonators[index]
            if resonator is None:
                time.sleep(0.3)
                continue
            is_toggled = self.team_member_selector.toggle(index, event=event, resonators=resonators)
            index = self._next_index(index, seq_length)
            # if is_toggled is None:
            #     time.sleep(0.3)
            #     continue
            if not is_toggled:
                continue
            resonator.event = event
            try:
                resonator.combo()
            except StopError:  # 主动抛出异常快速跳出连招序列
                pass

    def _next_index(self, index, seq_length) -> int:
        next_index = index + 1
        if next_index >= seq_length:
            next_index = 0
        return next_index

    def start(self, delay_seconds: float = 0.0):
        if self.is_async:
            with self._lock:
                # logger.info("Combat system started.")
                self.event.set()
                if delay_seconds > 0.0:
                    self._delay_seconds = delay_seconds
                    self._delay_time = time.monotonic() + delay_seconds
                if self._thread is None:
                    self._thread = threading.Thread(target=self.run, args=(self.event,))
                    self._thread.daemon = True
                    self._delay_seconds = delay_seconds
                    self._thread.start()
        else:
            self.event.set()
            self.run(self.event)

    # def stop(self):
    #     with self._lock:
    #         self.event.clear()
    #         if self.is_async:
    #             self._thread = None

    def pause(self):
        with self._lock:
            self.event.clear()

    # def is_running(self):
    #     with self._lock:
    #         return self.event.is_set()
