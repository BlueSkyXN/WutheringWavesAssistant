import logging
import threading
import time

from src.core.combat.combat_core import TeamMemberSelector, BaseCombo, BaseResonator, CharClassEnum
from src.core.combat.resonator.camellya import Camellya
from src.core.combat.resonator.cartethyia import Cartethyia
from src.core.combat.resonator.changli import Changli
from src.core.combat.resonator.ciaccona import Ciaccona
from src.core.combat.resonator.encore import Encore
from src.core.combat.resonator.jinhsi import Jinhsi
from src.core.combat.resonator.phoebe import Phoebe
from src.core.combat.resonator.sanhua import Sanhua
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
        self.camellya = Camellya(self.control_service, self.img_service)
        self.sanhua = Sanhua(self.control_service, self.img_service)
        self.cartethyia = Cartethyia(self.control_service, self.img_service)
        self.ciaccona = Ciaccona(self.control_service, self.img_service)
        self.phoebe = Phoebe(self.control_service, self.img_service)

        self.resonator_map = {
            self.jinhsi.name_en: self.jinhsi,
            self.changli.name_en: self.changli,
            self.shorekeeper.name_en: self.shorekeeper,
            self.encore.name_en: self.encore,
            self.verina.name_en: self.verina,
            self.camellya.name_en: self.camellya,
            self.sanhua.name_en: self.sanhua,
            self.cartethyia.name_en: self.cartethyia,
            self.ciaccona.name_en: self.ciaccona,
            self.phoebe.name_en: self.phoebe,
        }
        self.resonators = None
        self._sorted_resonators = None

        self.is_nightmare: bool = False

    def get_resonators(self) -> list[BaseResonator]:
        resonators = []
        member_names = self.team_member_selector.get_team_members()
        member_names_log = []
        for member_name in member_names:
            resonator = self.resonator_map.get(member_name)
            resonators.append(resonator)
            member_names_log.append(resonator.name)
        logger.info(f"编队: {member_names_log}")
        return resonators

    def _sort_resonators(self, resonators: list):
        dps = []
        support = []
        healer = []
        for index, resonator in enumerate(resonators):
            char_class = resonator.char_class()
            if CharClassEnum.MainDPS in char_class or CharClassEnum.SubDPS in char_class:
                dps.append((resonator, index))
            elif CharClassEnum.Support in char_class:
                support.append((resonator, index))
            elif CharClassEnum.Healer in char_class:
                healer.append((resonator, index))
            else:
                raise NotImplementedError()
        # 辅助先于输出
        sorted_resonators = support + dps + healer
        logger.debug(f"sorted_resonators: {sorted_resonators}")
        return sorted_resonators

    def run(self, event: threading.Event):
        if self.resonators is None:
            self.resonators = self.get_resonators()
        if self.resonators and self._sorted_resonators is None:
            self._sorted_resonators = self._sort_resonators(self.resonators)
        index = 0
        seq_length = len(self.resonators)
        last_index = index
        last_index_toggle = True
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
            resonator, src_index = self._sorted_resonators[index]
            if resonator is None:
                time.sleep(0.3)
                continue
            is_toggled = self.team_member_selector.toggle(src_index, event=event, resonators=self.resonators)
            if not is_toggled:
                index = self._next_index(index, seq_length)
                continue
            # 大招期间无法切人，若又切到同一个角色，尝试切下一个人
            # 避免单角色连续站场两次
            if last_index == index and last_index_toggle:
                logger.debug(f"又轮到同一个角色，跳过, member: {index + 1}")
                index = self._next_index(index, seq_length)
                last_index_toggle = False
                continue
            last_index_toggle = True
            last_index = index
            index = self._next_index(index, seq_length)
            resonator.event = event
            if isinstance(resonator, BaseCombo):
                resonator.is_nightmare = self.is_nightmare
            try:
                resonator.combo()
            except StopError:  # 主动抛出异常快速跳出连招序列
                if self.is_nightmare:
                    self.control_service.pick_up()
            finally:
                self.control_service.mouse_left_up()

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

    # def _auto_pause_after(self):
    #     self.control_service.mouse_left_up()
    #     self.control_service.mouse_right_up()
    #     self.control_service.jump()  # 退出蝴蝶/红椿

    # def is_running(self):
    #     with self._lock:
    #         return self.event.is_set()

    def set_resonators(self, resonator_names_zh: list[str]):
        resonators: list[BaseResonator] = []
        resonators_names_en = []
        for name_zh in resonator_names_zh:
            if not name_zh:
                resonators.append(None)
                continue
            for names_en, resonator in self.resonator_map.items():
                if resonator.name == name_zh:
                    resonators.append(resonator)
                    resonators_names_en.append(resonator.name_en)
                    break
        logger.info(resonators_names_en)
        logger.info(f"编队: {resonator_names_zh}")
        self.resonators = resonators

    def is_boss_health_bar_exist(self):
        return BaseResonator.is_boss_health_bar_exist(self.img_service.screenshot())

    def move_prepare(self, camellya_reset: bool = False):
        if self.resonators is None:
            self.resonators = self.get_resonators()
        try:
            cur_member_number = self.team_member_selector.get_cur_member_number()
            if cur_member_number is None:
                return
            resonator = self.resonators[cur_member_number - 1]
            if isinstance(resonator, Camellya):
                resonator.quit_blossom()
                # 椿落地会前移，后闪复位
                if camellya_reset:
                    self.control_service.dash_dodge()
                    time.sleep(0.3)
            # elif isinstance(resonator, Shorekeeper):
            #     self.control_service.jump()
        except IndexError as e:
            logger.exception(e)
