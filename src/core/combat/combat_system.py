import logging
import threading
import time

from src.core.combat.combat_core import TeamMemberSelector
from src.core.combat.resonator.Changli import Changli
from src.core.combat.resonator.Jinhsi import Jinhsi
from src.core.combat.resonator.Shorekeeper import Shorekeeper
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

    def run(self, event: threading.Event):
        resonators = [
            self.shorekeeper, self.jinhsi, self.changli, self.jinhsi, self.shorekeeper, self.changli, self.jinhsi,
            self.changli
        ]
        member_number_map = {
            self.jinhsi.name: 3,
            self.changli.name: 2,
            self.shorekeeper.name: 1,
        }
        index = 0
        seq_length = len(resonators)
        while True:
            if not event.is_set():
                # logger.info("暂停中，event.is_set()")
                time.sleep(0.3)
                continue
            if self._delay_time - time.monotonic() < 0.0:
                # logger.info("暂停中，delay_time")
                time.sleep(0.3)
                continue
            # logger.info("index：%s", index)
            resonator = resonators[index]
            index = self._next_index(index, seq_length)
            self.control_service.fight_tap("F", 0.001)
            if index % 4 == 0:
                self.control_service.activate()
            if index % 2 == 0:
                self.control_service.camera_reset()
            is_toggled = self.team_member_selector.toggle(member_number_map.get(resonator.name), event=self.event)
            if not is_toggled:
                continue
            resonator.event = event
            try:
                resonator.combo()
            except StopError:  # 主动抛出异常快速跳出连招序列
                self.control_service.fight_tap("a", 0.001)  # 打一下普攻，打断守岸人变身蝴蝶
                continue

    def _next_index(self, index, seq_length) -> int:
        next_index = index + 1
        if next_index >= seq_length:
            next_index = 0
        return next_index

    def start(self, delay_seconds: float = 0.0):
        with self._lock:
            # logger.info("Combat system started.")
            self.event.set()
            if self.is_async:
                if delay_seconds > 0.0:
                    self._delay_seconds = delay_seconds
                    self._delay_time = time.monotonic() + delay_seconds
                if self._thread is None:
                    self._thread = threading.Thread(target=self.run, args=(self.event,))
                    self._thread.daemon = True
                    self._delay_seconds = delay_seconds
                    self._thread.start()
            else:
                self.run(self.event)

    # def stop(self):
    #     with self._lock:
    #         self.event.clear()
    #         if self.is_async:
    #             self._thread = None

    def pause(self):
        with self._lock:
            self.event.clear()

    def is_running(self):
        with self._lock:
            return self.event.is_set()
