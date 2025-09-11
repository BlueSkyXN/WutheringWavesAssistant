import logging
from pathlib import Path

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
        input_shape, img.shape, outputs, model.confidence_thres, model.iou_thres, ratio, pad
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
    model = yolo_util.MODEL_BOSS_V20
    # model = yolo_util.MODEL_REWARD
    # model = yolo_util.MODEL_BOSS_FLEURDELYS
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
        input_shape, img.shape, outputs, model.confidence_thres, model.iou_thres, ratio, pad
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



def test_search_echo_from_local_dir():
    logger.debug("\n")

    # model = yolo_util.MODEL_BOSS_V10
    model = yolo_util.MODEL_BOSS_V20
    ort_provider = yolo_util.get_ort_providers()
    ort_session_options = yolo_util.create_ort_session_options()
    session = yolo_util.create_ort_session(
        model_path=model.path, providers=ort_provider, sess_options=ort_session_options
    )
    input_shape = session.get_inputs()[0].shape
    logger.debug("Model input shape: %s", input_shape)  # [1, 3, 640, 640] NCHW

    folder_path = Path(r"D:\Game\WutheringWavesAssistant-dev\temp\screenshot\260")
    import cv2
    import shutil

    for png_file in folder_path.iterdir():
        if not png_file.is_file() or png_file.suffix.lower() != '.png':
            continue
        logger.debug(png_file.absolute())
        img_name = png_file.absolute()
        img = img_util.read_img(img_name)

        img_process, ratio, pad = yolo_util.preprocess(img)
        outputs = yolo_util.run_ort_session(session, img_process)
        boxes, scores, class_ids = yolo_util.postprocess(
            input_shape, img.shape, outputs, 0.6, model.iou_thres, ratio, pad
        )
        img = img.copy()
        yolo_util.draw_detections(img, boxes, scores, class_ids, model.classes)
        img = img_util.hide_uid(img)
        # img_util.save_img_in_temp(img)
        # img_util.show_img(img)

        cv2.imshow('Image Viewer', img)
        key = cv2.waitKey(0)

        if key == 27:  # ESC键退出
            logger.debug("用户中断显示")
            break
        elif 49 <= key <= 57:  # 数字键1-9 (ASCII码 49-57)
            folder_num = chr(key)  # 获取按下的数字
            target_folder_name = folder_num.zfill(2)  # 转换为两位数字，如 '1' -> '01'
            target_folder = folder_path / target_folder_name

            # 创建目标文件夹（如果不存在）
            target_folder.mkdir(exist_ok=True)

            # 复制文件
            target_path = target_folder / png_file.name
            shutil.copy2(png_file, target_path)
            logger.debug(f"已复制到: {target_path}")

        elif key == 48:  # 数字键0 (ASCII码 48)
            logger.debug("跳过当前图片")
            continue

    cv2.destroyAllWindows()


def test_search_echo_from_local_dir_sort():
    logger.debug("\n")

    # model = yolo_util.MODEL_BOSS_V10
    model = yolo_util.MODEL_BOSS_V20
    ort_provider = yolo_util.get_ort_providers()
    ort_session_options = yolo_util.create_ort_session_options()
    session = yolo_util.create_ort_session(
        model_path=model.path, providers=ort_provider, sess_options=ort_session_options
    )
    input_shape = session.get_inputs()[0].shape
    logger.debug("Model input shape: %s", input_shape)  # [1, 3, 640, 640] NCHW

    folder_path = Path(r"D:\Game\WutheringWavesAssistant-dev\temp\screenshot\260")
    import shutil

    for png_file in folder_path.iterdir():
        if not png_file.is_file() or png_file.suffix.lower() != '.png':
            continue
        logger.debug(png_file.absolute())
        img_name = png_file.absolute()
        img = img_util.read_img(img_name)
        img_src = img
        # img_process, ratio, pad = yolo_util.preprocess(img)
        # outputs = yolo_util.run_ort_session(session, img_process)
        # boxes, scores, class_ids = yolo_util.postprocess(
        #     input_shape, img.shape, outputs, 0.6, model.iou_thres
        # )
        img = img.copy()
        # yolo_util.draw_detections(img, boxes, scores, class_ids, model.classes)
        # img = img_util.hide_uid(img)
        # img_util.save_img_in_temp(img)
        # img_util.show_img(img)

        results = yolo_util.search_echo(session, img, 0.5, model.iou_thres)
        if results is None:
            logger.debug("跳过当前图片")
            continue
        box, score, class_id = results
        logger.debug("box: %s, scores: %s, class_id: %s", box, score, class_id)
        # x1, y1, w, h = box
        # return box

        # cv2.imshow('Image Viewer', img)
        # key = cv2.waitKey(0)

        if score >= 0.88:
            target_folder = folder_path / "high"
            target_folder_draw = folder_path / "high-draw"
        else:
            target_folder = folder_path / "low"
            target_folder_draw = folder_path / "low-draw"

        # 创建目标文件夹（如果不存在）
        target_folder.mkdir(exist_ok=True)
        target_folder_draw.mkdir(exist_ok=True)

        # 复制文件
        target_path = target_folder / png_file.name
        shutil.copy2(png_file, target_path)
        logger.debug(f"已复制到: {target_path}")

        img = img_src.copy()
        img_process, ratio, pad = yolo_util.preprocess(img)
        outputs = yolo_util.run_ort_session(session, img_process)
        boxes, scores, class_ids = yolo_util.postprocess(
            input_shape, img.shape, outputs, 0.5, model.iou_thres, ratio, pad
        )
        yolo_util.draw_detections(img, boxes, scores, class_ids, model.classes)

        img_util.save_img(img, str((target_folder_draw / png_file.name).absolute()))



