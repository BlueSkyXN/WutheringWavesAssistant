<div align="center">
<img src="src/gui/resource/images/logo.ico" alt="LOGO" width="192" height="192" />

# Wuthering Waves Assistant

![license](https://img.shields.io/github/license/wakening/WutheringWavesAssistant)
![commit](https://img.shields.io/github/commit-activity/m/wakening/WutheringWavesAssistant?color=%23ff69b4)  
[![QQ](https://img.shields.io/badge/QQ-加群-blue?logo=tencentqq)](https://qm.qq.com/q/tDWAi0LCj8)
[![Discord](https://img.shields.io/badge/Discord-加入社区-5865F2?logo=discord&logoColor=white)](https://discord.gg/Ug8aXjvp)  

鸣潮自动化助手

**QQ群: 1039535103**

</div>


![Wuthering Waves Assistant](assets/static/HomePage.png)


## 📌 使用指南

- 点击转到 [下载页](https://github.com/wakening/WutheringWavesAssistant/releases/latest)，按描述选择合适的版本下载，看不懂就选300M左右那个，网速不行就去群里下  
- 下载后解压，剪切到一个路径没有中文的目录
- 双击一键更新并选择合适的更新渠道（无梯子建议选国内加速）升级到最新，双击WWA.exe启动脚本
- Windows系统设置：关闭HDR（默认关闭），关闭英伟达显卡滤镜（默认关闭），微星小飞机关闭或挪到左下角（不认识就不用管）
- 游戏内设置：
  - 简体中文，重置按键，重置滤镜，重置亮度  
  - 控制 镜头设置：  
    - 镜头重置：开  
    - 移动镜头修正：开  
    - 战斗镜头修正：开  
- MOD在刷boss时需要关闭，在游戏内按F6，F6在下面就Fn + F6

---

## 🔧 从源码安装（Conda）

<details>
<summary>点击这里展开/折叠</summary>

### 1️⃣ 安装 Conda

群文件里有，或点击 [Miniconda官方链接](https://repo.anaconda.com/miniconda/Miniconda3-py312_24.11.1-0-Windows-x86_64.exe) 下载
Miniconda  
安装时点击选项：  
Next -> I agree ->  Just Me (recommended) -> Next -> Next ->  
Add miniconda3 to my PATH environment variable -> Install  
安装完成后，任意打开一个**新的 powershell 窗口**，准备初始化conda
```powershell
conda -V
conda init powershell
```
执行后没有红色异常文字，这步就完成了，**关闭 powershell 窗口**

### 2️⃣ 安装 Git

前往 [Git 官网（右下角有个显示器，点击 Download for Windows）](https://git-scm.com/) 下载并安装 Git，全程保持默认设置。

### 3️⃣ 准备环境

- 选择一个**路径中不包含中文**的文件夹来存放本项目。
- **以管理员身份**打开一个**新的 PowerShell 窗口**。

### 4️⃣ 下载项目

```powershell
git clone https://github.com/wakening/WutheringWavesAssistant.git

或者使用免费的国内加速代理，任选其一：
git clone https://ghproxy.net/https://github.com/wakening/WutheringWavesAssistant.git
git clone https://ghfast.top/https://github.com/wakening/WutheringWavesAssistant.git
git clone https://gitclone.com/github.com/wakening/WutheringWavesAssistant.git
```

### 5️⃣ 安装依赖

管理员身份打开powershell，设置允许执行脚本，执行过一次即可
```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```
开始安装依赖
```powershell
cd WutheringWavesAssistant
./scripts/rebuild_conda_env.ps1
```

按照提示选择GPU或CPU环境安装，新N卡输入1，新老N卡都可以输入4，A卡输入3， 回车，等待脚本执行完成，若失败可以重跑，有红色文字即为失败，黄色等为正常  

### 6️⃣ 配置文件

- **老用户**（使用过 `mc_auto_boss` 的用户）：请复制 `config.yaml` 到本目录并覆盖  
- **新用户**：直接运行，并在页面上⭐️页面上修改参数，仅连招需修改config.yaml，其他参数修改config.yaml无效  

### 7️⃣ 启动脚本

**务必以管理员身份运行**，否则无法正常工作。

激活英伟达GPU环境wwa-cuda，cpu则是wwa-cpu
```powershell
conda activate wwa-cuda
```
激活后运行程序
```powershell
python main.py
```

若能正常运行，后续可双击启动器 WWA.exe 运行，AMD GPU用户到群里下载CPU版启动器  

### 8️⃣ 更新脚本

```powershell
git pull
```

若正常不报错，后续可双击更新器 WWA_updater.exe 更新并运行  
更新后若无法运行或窗口出现闪烁，可看下方常见问题  

### 9️⃣ 管理环境

查看conda里所有的环境:
```powershell
conda env list
```
卸载环境
```powershell
conda remove --name wwa-cuda --all -y
```

---

## ❓ 常见问题

### ⚠️ 脚本无法运行？

确保 **PowerShell 以管理员身份运行**，并且 Conda 和 Git 均已正确安装。

### ⚠️ 依赖安装失败？

重新运行 `./scripts/rebuild_conda_env.ps1` 以重建环境。

</details>

---

## ❓ 常见问题

### ⚠️ 运行时报错？

加入我们的 **QQ群 (1039535103)** 交流或提交 Issue 反馈问题。

---

## 免责声明

本项目为本人学习python所建，请下载后24小时内删除  
项目基于OCR文字识别、YOLO目标检测，纯图像识别，完全开源，永久免费，禁止售卖  
脚本是否有使用风险，一切解释权均由kuro所有，建议手刷不要使用脚本  


