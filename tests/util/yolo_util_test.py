import logging

from src.util import file_util, img_util, yolo_util, screenshot_util, hwnd_util

logger = logging.getLogger(__name__)

hwnd_util.enable_dpi_awareness()

def test_yolo_util():
    logger.debug("\n")
    img_name = "EchoSearch_001.png"
    # img_name = "EchoSearch_002.png"
    img = img_util.read_img(file_util.get_assets_screenshot(img_name))
    logger.debug("img shape: %s", img.shape)  # (720, 1280, 3) HWC
    # model = yolo_util.MODEL_BOSS_V10
    model = yolo_util.MODEL_BOSS_V20
    ort_provider = yolo_util.get_ort_providers()
    ort_session_options = yolo_util.create_ort_session_options()
    session = yolo_util.create_ort_session(
        model_path=model.path, providers=ort_provider, sess_options=ort_session_options
    )
    input_shape = session.get_inputs()[0].shape
    logger.debug("Model input shape: %s", input_shape)  # [1, 3, 640, 640] NCHW
    img_process, ratio, pad = yolo_util.preprocess(img)
    outputs = yolo_util.run_ort_session(session, img_process)
    boxes, scores, class_ids = yolo_util.postprocess(
        input_shape, img.shape, outputs, model.confidence_thres, model.iou_thres
    )
    img = img.copy()
    yolo_util.draw_detections(img, boxes, scores, class_ids, model.classes)
    img = img_util.hide_uid(img)
    img_util.save_img_in_temp(img)
    img_util.show_img(img)


def test_yolo_util_from_screen():
    logger.debug("\n")
    hwnd = hwnd_util.get_hwnd()
    img = screenshot_util.screenshot(hwnd)
    logger.debug("img shape: %s", img.shape)  # (720, 1280, 3) HWC
    # model = yolo_util.MODEL_BOSS_V20
    # model = yolo_util.MODEL_REWARD
    model = yolo_util.MODEL_BOSS_FLEURDELYS
    ort_provider = yolo_util.get_ort_providers()
    ort_session_options = yolo_util.create_ort_session_options()
    session = yolo_util.create_ort_session(
        model_path=model.path, providers=ort_provider, sess_options=ort_session_options
    )
    input_shape = session.get_inputs()[0].shape
    logger.debug("Model input shape: %s", input_shape)  # [1, 3, 640, 640] NCHW
    img_process, ratio, pad = yolo_util.preprocess(img)
    outputs = yolo_util.run_ort_session(session, img_process)
    boxes, scores, class_ids = yolo_util.postprocess(
        input_shape, img.shape, outputs, model.confidence_thres, model.iou_thres
    )

    img_src = img.copy()
    img_src = img_util.hide_uid(img_src)
    img_util.save_img_in_temp(img_src)

    img = img.copy()
    yolo_util.draw_detections(img, boxes, scores, class_ids, model.classes)
    img = img_util.hide_uid(img)
    img_util.save_img_in_temp(img)
    img_util.show_img(img)


def test_search_echo_from_local():
    logger.debug("\n")
    img_name = "echo_search_1740488077_91938666.png"
    # img_name = "echo_search_1740479618_68431652.png"
    img = img_util.read_img(file_util.get_assets_screenshot(img_name))
    logger.debug("img shape: %s", img.shape)  # (720, 1280, 3) HWC
    # model = yolo_util.MODEL_BOSS_V10
    model = yolo_util.MODEL_BOSS_V20
    ort_provider = yolo_util.get_ort_providers()
    ort_session_options = yolo_util.create_ort_session_options()
    session = yolo_util.create_ort_session(
        model_path=model.path, providers=ort_provider, sess_options=ort_session_options
    )
    # img = img.copy()
    img = img_util.hide_uid(img)
    outputs = yolo_util.search_echo(session, img)
    logger.debug("outputs: %s", outputs)



