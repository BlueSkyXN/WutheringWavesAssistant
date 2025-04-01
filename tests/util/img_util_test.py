import logging

import cv2
import numpy as np

from src.util import img_util, file_util, screenshot_util, hwnd_util

logger = logging.getLogger(__name__)

hwnd_util.enable_dpi_awareness()


def test_img_save():
    import random
    import time

    import cv2
    import numpy as np
    from PIL import Image

    # 创建一个大的随机图像 (例如 1000x1000)
    img_rgb = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)

    # 循环 20 次，保存带有随机数的文件名
    for i in range(20):
        # 生成一个随机数用于文件名
        random_number = random.randint(1000, 9999)

        # 1. 使用 Pillow 保存 RGB 图像
        start_time = time.time()
        img_pil = Image.fromarray(img_rgb)  # 创建 Pillow 图像对象
        img_pil.save(
            f"saved_image_pillow_{random_number}.png"
        )  # 保存为 PNG 文件，文件名加上随机数
        end_time = time.time()
        print(
            f"Pillow save time for iteration {i + 1}: {end_time - start_time:.6f} seconds"
        )

        # 2. 使用 OpenCV 保存 RGB 图像（需要先转换为 BGR）
        start_time = time.time()
        img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)  # 转换为 BGR
        cv2.imwrite(
            f"saved_image_opencv_{random_number}.png", img_bgr
        )  # 保存为 PNG 文件，文件名加上随机数
        end_time = time.time()
        print(
            f"OpenCV save time for iteration {i + 1}: {end_time - start_time:.6f} seconds"
        )


def test_img_cvt():
    import time

    import cv2
    import numpy as np

    # 创建一个大的随机 BGR 图像 (例如 1000x1000)
    img_bgr = np.random.randint(0, 256, (1000, 1000, 3), dtype=np.uint8)

    # 计时：cv2 BGR 转 RGB
    start_time = time.time()
    for i in range(1000):
        img_rgb_cv2 = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)  # 使用 cv2 转换颜色空间
    end_time = time.time()
    cv2_bgr_to_rgb_total_time = end_time - start_time
    cv2_bgr_to_rgb_avg_time = cv2_bgr_to_rgb_total_time / 1000

    # 计时：直接交换通道
    start_time = time.time()
    for i in range(1000):
        # img_rgb_swap = img_bgr.copy()  # 复制图像避免原图改变
        img_rgb_swap = img_bgr
        img_rgb_swap[:, :, 0], img_rgb_swap[:, :, 2] = (
            img_rgb_swap[:, :, 2],
            img_rgb_swap[:, :, 0],
        )  # 交换 BGR 通道
    end_time = time.time()
    swap_channels_total_time = end_time - start_time
    swap_channels_avg_time = swap_channels_total_time / 1000

    # 输出结果
    print(f"cv2 BGR to RGB total time: {cv2_bgr_to_rgb_total_time:.6f} seconds")
    print(
        f"cv2 BGR to RGB average time per iteration: {cv2_bgr_to_rgb_avg_time:.6f} seconds"
    )

    print(f"Swap channels total time: {swap_channels_total_time:.6f} seconds")
    print(
        f"Swap channels average time per iteration: {swap_channels_avg_time:.6f} seconds"
    )


def test_match_template():
    guidebook = img_util.read_img(file_util.get_assets_template("Guidebook.png"))
    img = img_util.read_img(file_util.get_assets_screenshot("EchoSearch_001.png"))
    position = img_util.match_template(img, guidebook)
    img = img_util.draw_match_template_result(img, position)
    img_util.save_img_in_temp(img)
    img_util.show_img(img)


def test_match_template_list():
    template_list = [
        "Guidebook.png", "Backpack.png", "Quests.png", "UI_F2_Guidebook_EchoHunting.png",
        "UI_F2_Guidebook_RecurringChallenges.png",
    ]
    # img = img_util.read_img(file_util.get_assets_screenshot("EchoSearch_001.png"))
    img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()
    result_list = []
    for template_img_name in template_list:
        template_img = img_util.read_img(file_util.get_assets_template(template_img_name))
        position = img_util.match_template(img, template_img)
        result_list.append(position)
    for i in range(len(template_list)):
        img = img_util.draw_match_template_result(img, result_list[i])
    img_util.save_img_in_temp(img)
    img_util.show_img(img)


def test_match_template_list_resize():
    # template_list = [
    #     "Guidebook.png", "Backpack.png", "Quests.png", "UI_F2_Guidebook_EchoHunting.png",
    #     "UI_F2_Guidebook_RecurringChallenges.png", "AutoPlay.png", "AutoPlayEnabled.png",
    # ]
    template_list = [
        "AutoPlay.png",
        # "AutoPlayEnabled.png",
    ]
    # img = img_util.read_img(file_util.get_assets_screenshot("EchoSearch_001.png"))
    img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()
    img = img_util.resize(img, (1280, 720))
    result_list = []
    for template_img_name in template_list:
        template_img = img_util.read_img(file_util.get_assets_template(template_img_name))
        position = img_util.match_template(img, template_img)
        result_list.append(position)
    for i in range(len(template_list)):
        img = img_util.draw_match_template_result(img, result_list[i])
    img_util.save_img_in_temp(img)
    img_util.show_img(img)


def test_mask():
    img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()
    # 创建全黑的 mask
    mask = np.zeros_like(img, dtype=np.uint8)
    # 获取原图尺寸
    h, w = img.shape[:2]
    # 需要的区域尺寸
    w_crop = int(w * 0.046875)  # 任务图标所在区域
    h_crop = int(h * 0.29)
    # 需要的区域设为白色（255）
    mask[:h_crop, :w_crop] = 255
    w_crop = int(w)  # 上方横排图标所在区域
    h_crop = int(h * 0.105)
    mask[:h_crop, :w_crop] = 255
    img_util.show_img(mask)
    img_util.save_img_in_temp(mask)
    img_util.save_img_in_temp(img)


def test_resize():
    img = img_util.read_img(file_util.get_temp_screenshot("screenshot_1742484594_82073020.png"))
    img = img_util.resize_by_ratio(img, 0.5)
    img_util.save_img_in_temp(img)


def test_match_template2():
    img = img_util.read_img(file_util.get_temp_screenshot("screenshot_1742484774_35132185.png"))
    template_img = img_util.read_img(file_util.get_assets_template("Dialogue.png"))
    result = img_util.match_template(img, template_img)
    logger.debug(result)
    logger.debug(result)
    logger.debug(result)


def test_read_BGRA():
    img = img_util.read_img(file_util.get_assets_screenshot("UI_F2_Guidebook_Activity_001.png"))
    template_img = img_util.read_img(file_util.get_assets_template("UI_F2_Guidebook_RecurringChallenges.png"))
    result = img_util.match_template(img, template_img)
    logger.debug(result)
    img = img_util.draw_match_template_result(img, result)
    img_util.save_img_in_temp(img)
    img_util.show_img(img)

def test_match_template_ORB():
    print(cv2.__version__)
    # 读取图标和截图
    icon = img_util.read_img(file_util.get_assets_template("UI_F2_Guidebook_RecurringChallenges.png"))
    screenshot = img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()

    # 创建 ORB 特征检测器
    orb = cv2.ORB_create()

    # 计算图标和截图的特征点
    kp1, des1 = orb.detectAndCompute(icon, None)
    kp2, des2 = orb.detectAndCompute(screenshot, None)

    # 使用 BFMatcher 进行匹配
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1, des2)

    # 排序匹配项
    matches = sorted(matches, key=lambda x: x.distance)

    # 绘制匹配结果
    img_matches = cv2.drawMatches(icon, kp1, screenshot, kp2, matches[:10], None,
                                  flags=cv2.DrawMatchesFlags_NOT_DRAW_SINGLE_POINTS)
    logger.debug(matches)
    cv2.imshow("Matches", img_matches)
    cv2.waitKey(0)


def test_match_template_ORB():
    print(cv2.__version__)
    # 读取图标和截图
    template_img = img_util.read_img(file_util.get_assets_template("UI_F2_Guidebook_RecurringChallenges.png"))
    img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()

    # 使用Canny边缘检测
    template_edges = cv2.Canny(template_img, 50, 200)
    img_edges = cv2.Canny(img, 50, 200)

    # 在边缘图上进行匹配
    edge_result = cv2.matchTemplate(img_edges, template_edges, cv2.TM_CCOEFF_NORMED)
    logger.debug(edge_result)


# import cv2
# import numpy as np
# from skimage.metrics import structural_similarity as compare_ssim


# -------------------- 核心匹配方法 --------------------
def base_match(img, template_img):
    """基础模板匹配"""
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)
    return cv2.matchTemplate(img_gray, template_gray, cv2.TM_CCOEFF_NORMED)


def multi_scale_match(img, template_img, scales=np.linspace(0.8, 1.2, 5)):
    """多尺度匹配"""
    best_val = -1
    best_scale = 1.0
    best_loc = (0, 0)
    h, w = template_img.shape[:2]

    for scale in scales:
        scaled_img = cv2.resize(img, None, fx=scale, fy=scale)
        if scaled_img.shape[0] < h or scaled_img.shape[1] < w:
            continue

        result = base_match(scaled_img, template_img)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        if max_val > best_val:
            best_val = max_val
            best_scale = scale
            best_loc = (int(max_loc[0] / scale), int(max_loc[1] / scale))

    return best_val, best_loc, best_scale


def edge_match(img, template_img):
    """边缘特征匹配"""

    def auto_canny(image):
        sigma = 0.33
        v = np.median(image)
        lower = int(max(0, (1.0 - sigma) * v))
        upper = int(min(255, (1.0 + sigma) * v))
        return cv2.Canny(image, lower, upper)

    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    template_gray = cv2.cvtColor(template_img, cv2.COLOR_BGR2GRAY)

    img_edges = auto_canny(img_gray)
    template_edges = auto_canny(template_gray)

    # 边缘增强
    kernel = np.ones((2, 2), np.uint8)
    img_edges = cv2.dilate(img_edges, kernel)
    return cv2.matchTemplate(img_edges, template_edges, cv2.TM_CCOEFF_NORMED)


# -------------------- 辅助函数 --------------------
def draw_match(img, location, template_size, confidence, color=(0, 255, 0)):
    """可视化匹配结果"""
    x, y = location
    w, h = template_size
    cv2.rectangle(img, (x, y), (x + w, y + h), color, 2)
    cv2.putText(img, f"{confidence:.2f}", (x, y - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
    return img


# -------------------- 主程序 --------------------
def main(img, template_img):
    # # 初始化参数
    # # TEMPLATE_PATH = "template.jpg"
    # TEMPLATE_PATH = file_util.get_assets_template("UI_F2_Guidebook_RecurringChallenges.png")
    # # SCREENSHOT_PATH = "screenshot.jpg"
    # SCREENSHOT_PATH = file_util.get_temp_screenshot("screenshot_1742729351_57647083.png")
    THRESHOLD = 0.6  # 匹配阈值
    #
    # # 加载图像
    # template_img = cv2.imread(TEMPLATE_PATH)
    # img = cv2.imread(SCREENSHOT_PATH)
    #
    # # 校验图像加载
    # if template_img is None or img is None:
    #     print("错误：图片加载失败，请检查路径")
    #     return

    # 执行多尺度匹配
    # ms_score, ms_loc, ms_scale = multi_scale_match(img, template_img)

    # 执行边缘匹配
    edge_result = edge_match(img, template_img)
    _, edge_max, _, edge_loc = cv2.minMaxLoc(edge_result)

    # 执行基础匹配
    base_result = base_match(img, template_img)
    _, base_max, _, base_loc = cv2.minMaxLoc(base_result)

    # 结果分析
    results = [
        # ("多尺度", ms_score, ms_loc),
        ("边缘匹配", edge_max, edge_loc),
        ("基础匹配", base_max, base_loc)
    ]

    # 可视化最佳结果
    display_img = img.copy()
    template_size = template_img.shape[1], template_img.shape[0]  # (width, height)

    for method, score, loc in results:
        print(f"{method} 置信度: {score:.2f} @ {loc}")
        if score > THRESHOLD:
            # color = (0, 255, 0) if "多尺度" in method else (0, 0, 255)
            color = (0, 255, 0)
            display_img = draw_match(display_img, loc, template_size, score, color)
            print(f"{method} 置信度: {score:.2f} @ {loc}")

    # 显示结果
    cv2.imshow("Match result", display_img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def test_match_other():
    # img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()
    # template_img = img_util.read_img(file_util.get_assets_template("UI_F2_Guidebook_RecurringChallenges.png"))
    # main(img, template_img)

    template_list = [
        "Guidebook.png", "Backpack.png", "Quests.png",
        "UI_F2_Guidebook_EchoHunting.png",
        "UI_F2_Guidebook_RecurringChallenges.png",
    ]
    # img = screenshot_util.screenshot(hwnd_util.get_hwnd()).copy()
    # img = img_util.read_img(file_util.get_temp_screenshot("screenshot_1742728685_41907802.png"))
    img = img_util.read_img(file_util.get_temp_screenshot("screenshot_1742731326_29348156.png"))
    img = img_util.resize(img, (1280, 720))
    # result_list = []
    for template_img_name in template_list:
        template_img = img_util.read_img(file_util.get_assets_template(template_img_name))
        main(img, template_img)

