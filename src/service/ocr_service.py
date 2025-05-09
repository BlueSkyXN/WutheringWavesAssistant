import asyncio
import importlib.util
import logging
import os
import re
import time
from asyncio import Task
from concurrent.futures import ThreadPoolExecutor

import numpy as np

from src.core import environs
from src.core.contexts import Context
from src.core.interface import OCRService, ImgService, WindowService
from src.core.regions import Position, RapidocrPosition, TextPosition, DynamicPosition, PaddleocrPosition
from src.util import rapidocr_util
from src.util.wrap_util import timeit

logger = logging.getLogger(__name__)


def is_ocr_use_gpu() -> bool:
    ocr_use_gpu = None
    if environs.get_ocr_use_gpu() == "True":
        if importlib.util.find_spec("paddle") and importlib.util.find_spec("onnxruntime"):
            import paddle
            import onnxruntime
            if paddle.is_compiled_with_cuda() and "CUDAExecutionProvider" in onnxruntime.get_available_providers():
                ocr_use_gpu = True
                logger.info("OCR is running on GPU ✅")
        if ocr_use_gpu is None:
            ocr_use_gpu = False
            logger.warning("OCR expected GPU, falling back to CPU ⚠️")
    if ocr_use_gpu is None:
        ocr_use_gpu = False
        logger.info("OCR is running on CPU ✅")
    return ocr_use_gpu


class RapidOcrServiceImpl(OCRService):

    def __init__(self, context: Context, window_service: WindowService, img_service: ImgService):
        logger.debug("Initializing %s", self.__class__.__name__)
        super().__init__()
        self._context: Context = context
        self._window_service: WindowService = window_service
        self._img_service: ImgService = img_service

        self.ocr_use_gpu = is_ocr_use_gpu()

        self._engine = rapidocr_util.create_ocr(use_gpu=self.ocr_use_gpu)
        # self._collection: set[str] = set()
        self._last_time = time.time()
        # self._executor = ThreadPoolExecutor(max_workers=2)

    # def __del__(self):
    #     self._executor.shutdown(wait=False)

    def search_text(self, results: list[TextPosition], target: str) -> TextPosition | None:
        for result in results:
            if re.search(target, result.text, re.I):  # 使用正则匹配
                return result
        return None

    def search_texts(self, results: list[TextPosition], target: str) -> list[TextPosition]:
        filter_list = []
        for result in results:
            if re.search(target, result.text, re.I):  # 使用正则匹配
                filter_list.append(result)
        return filter_list

    def find_text(self, targets: str | list[str], img: np.ndarray | None = None,
                  position: Position | DynamicPosition | None = None) -> TextPosition | None:
        if isinstance(targets, str):
            targets = [targets]
        if img is None:
            img = self._img_service.screenshot()
        result = self.ocr(img, position)
        for target in targets:
            if text_info := self.search_text(result, target):
                return text_info
        return None

    # def async_find_text(self, targets: str | list[str], img: np.ndarray | None = None,
    #                     position: Position | DynamicPosition | None = None) -> Task:
    #     return asyncio.create_task(
    #         self._async_find_text(targets, img, position),
    #         name=f"find_text: {targets}"
    #     )
    #
    # async def _async_find_text(self, targets: str | list[str], img: np.ndarray | None = None,
    #                            position: Position | DynamicPosition | None = None):
    #     loop = asyncio.get_running_loop()
    #     try:
    #         return await loop.run_in_executor(  # 将同步方法提交到线程池
    #             self._executor,  # 线程池
    #             self.find_text,  # 要执行的同步方法
    #             targets, img, position  # 参数
    #         )
    #     except Exception as e:
    #         logger.error(f"Inference failed: {e}")
    #         return None

    def wait_text(self, targets: str | list[str], timeout: float = 3.0,
                  position: Position | DynamicPosition | None = None, wait_time: float = 0.1) -> TextPosition | None:
        if isinstance(targets, str):
            targets = [targets]
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.find_text(targets, img=None, position=position)
            if result is not None:
                return result
            time.sleep(wait_time)  # 每次截图和 OCR 处理之间增加一个短暂的暂停时间
        return None

    @timeit(ignore=3)
    def ocr(self, img: np.ndarray, position: Position | DynamicPosition | None = None,
            det=True, rec=True, cls=False) -> list[TextPosition]:
        self._ocr_wait()
        if position is not None:
            if isinstance(position, DynamicPosition):
                w, h = self._window_service.get_client_wh()
                position = position.to_position(h, w)
            img = img[position.y1:position.y2, position.x1:position.x2]
        if det is True and rec is True and cls is False:
            return self._ocr_det_rec(img)
        elif det is False and rec is True and cls is False:
            return self._ocr_det_rec(img)
        raise NotImplementedError("不支持的识别方式")

    def _ocr_det_rec(self, img: np.ndarray) -> list[TextPosition]:
        output = self._engine(img, use_det=True, use_rec=True, use_cls=False)
        positions = RapidocrPosition.format(output)
        return positions

    def _ocr_wait(self):
        """限制OCR调用频率，默认不限制OcrInterval=0"""
        config = self._context.config.app
        if config.OcrInterval > 0 and time.time() - self._last_time < config.OcrInterval:
            if wait_time := config.OcrInterval - (time.time() - self._last_time) > 0:
                time.sleep(wait_time)
        self._last_time = time.time()

    def print_ocr_result(self, ocr_results: list[TextPosition] | None):
        if ocr_results is None:
            logger.debug("ocr_results is None")
            return
        for result in ocr_results:
            logger.debug(result)


class PaddleOcrServiceImpl(OCRService):

    def __init__(self, context: Context, window_service: WindowService, img_service: ImgService):
        logger.debug("Initializing %s", self.__class__.__name__)
        super().__init__()
        self._context: Context = context
        self._window_service: WindowService = window_service
        self._img_service: ImgService = img_service

        self.ocr_use_gpu = is_ocr_use_gpu()

        from src.util import paddleocr_util
        self._engine = paddleocr_util.create_paddleocr(use_gpu=self.ocr_use_gpu)
        self._last_time = time.time()

    def search_text(self, results: list[TextPosition], target: str) -> TextPosition | None:
        for result in results:
            if re.search(target, result.text, re.I):  # 使用正则匹配
                return result
        return None

    def search_texts(self, results: list[TextPosition], target: str) -> list[TextPosition]:
        filter_list = []
        for result in results:
            if re.search(target, result.text, re.I):  # 使用正则匹配
                filter_list.append(result)
        return filter_list

    def find_text(self, targets: str | list[str], img: np.ndarray | None = None,
                  position: Position | DynamicPosition | None = None) -> TextPosition | None:
        if isinstance(targets, str):
            targets = [targets]
        if img is None:
            img = self._img_service.screenshot()
        result = self.ocr(img, position)
        for target in targets:
            if text_info := self.search_text(result, target):
                return text_info
        return None

    def wait_text(self, targets: str | list[str], timeout: float = 3.0,
                  position: Position | DynamicPosition | None = None, wait_time: float = 0.1) -> TextPosition | None:
        if isinstance(targets, str):
            targets = [targets]
        start_time = time.monotonic()
        while time.monotonic() - start_time < timeout:
            result = self.find_text(targets, img=None, position=position)
            if result is not None:
                return result
            time.sleep(wait_time)  # 每次截图和 OCR 处理之间增加一个短暂的暂停时间
        return None

    # @timeit(ignore=3)
    def ocr(self, img: np.ndarray, position: Position | DynamicPosition | None = None,
            det=True, rec=True, cls=False) -> list[TextPosition]:
        self._ocr_wait()
        if position is not None:
            if isinstance(position, DynamicPosition):
                w, h = self._window_service.get_client_wh()
                position = position.to_position(h, w)
            img = img[position.y1:position.y2, position.x1:position.x2]
        if det is True and rec is True and cls is False:
            return self._ocr_det_rec(img)
        elif det is False and rec is True and cls is False:
            return self._ocr_det_rec(img)
        raise NotImplementedError("不支持的识别方式")

    def _ocr_det_rec(self, img: np.ndarray) -> list[TextPosition]:
        output = self._engine.ocr(img, det=True, rec=True, cls=False)
        positions = PaddleocrPosition.format(output)
        return positions

    def _ocr_wait(self):
        """限制OCR调用频率，默认不限制OcrInterval=0"""
        config = self._context.config.app
        if config.OcrInterval > 0 and time.time() - self._last_time < config.OcrInterval:
            if wait_time := config.OcrInterval - (time.time() - self._last_time) > 0:
                time.sleep(wait_time)
        self._last_time = time.time()

    def print_ocr_result(self, ocr_results: list[TextPosition] | None):
        if ocr_results is None:
            logger.debug("ocr_results is None")
            return
        for result in ocr_results:
            logger.debug(result)

# SVTR
# class SVTROcrServiceImpl(OCRService):
#     pass
