#### 程序介绍
一款完全离线、无需依赖 Outlook 环境的 MSG 转 EML 批量转换工具。基于 PyQt6 构建现代化 UI，专为高保密企业内网环境设计，支持拖拽操作与极速大文件处理。

#### 软件架构
本项目采用 MVC (Model-View-Controller) 分层架构，确保界面与核心转换逻辑解耦，保证在高负载下软件的稳定性：
*   **表现层 (View)**：基于 `PyQt6` 构建的现代化交互界面，支持原生的系统级文件拖拽识别，并通过 `QProgressBar` 和 `QTextEdit` 提供实时可视化的任务反馈。
*   **调度层 (Controller)**：使用 `QThread` 和 `pyqtSignal` 实现多线程异步任务调度。所有的邮件解析与转换均在独立后台线程进行，彻底杜绝主界面假死卡顿现象。
*   **解析引擎层 (Model)**：
    *   读取端：集成 `extract-msg` 开源库，完全脱离 Windows/Outlook COM 接口，直接对 `.msg` (OLE 复合文档格式) 进行底层二进制解包。
    *   写入端：利用 Python 官方内置的 `email` 与 `email.policy` 库，重新组装 MIME 多段结构，并针对巨型附件的 Base64 换行算法进行了 `policy.default` 提速优化。

#### 下载使用
1. **获取入口**：点击右侧发行版Release。
2. **下载程序**：下载"Msg_To_Eml_Exchange"标题下"msg_eml_exchange.exe"(仅限Win系统)
3. **双击运行**：运行后根据界面提示进行操作即可。

![程序首页](https://gitee.com/caoyongzhuo/MSG_TO_EML/raw/master/assets/%E7%A8%8B%E5%BA%8F%E7%95%8C%E9%9D%A2.png)

#### 安装教程

1.  **获取源码**：将本仓库克隆或下载到本地解压。
2.  **创建虚拟环境（推荐）**：在项目根目录下打开终端，执行 `python -m venv .venv` 创建虚拟环境。Windows 环境下执行 `.\.venv\Scripts\activate` 激活环境。
3.  **安装依赖**：在已激活的虚拟环境中，执行命令安装必须的第三方库：
    ```bash
    pip install PyQt6 extract-msg
    ```

#### 使用说明

1.  **启动程序**：在终端运行 `python msg_eml_exchange.py` 即可打开图形界面。
2.  **执行转换**：
    *   将准备好的 `.msg` 文件直接拖入软件窗口，或点击“添加 MSG 文件”进行批量选择。
    *   在“路径设置”栏中，选择转换后 `.eml` 文件的输出保存目录。
    *   勾选列表中需要转换的文件，点击下方蓝色的“🚀 开始转换”按钮。
3.  **独立打包 (可选)**：如果您需要将其发给未安装 Python 的同事，可以在虚拟环境中使用 PyInstaller 打包为独立的绿色单文件：
    ```bash
    pip install pyinstaller
    pyinstaller -F -w msg_eml_exchange.py
    ```
4. 打包完成后，在生成的 `dist` 目录下提取 `msg_eml_exchange.exe` 即可跨平台离线使用。

## Star History

<a href="https://www.star-history.com/?repos=TonaSmith%2FMSG_TO_EML&type=timeline&logscale=&legend=top-left">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/chart?repos=TonaSmith/MSG_TO_EML&type=timeline&theme=dark&logscale&legend=top-left" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/chart?repos=TonaSmith/MSG_TO_EML&type=timeline&logscale&legend=top-left" />
   <img alt="Star History Chart" src="https://api.star-history.com/chart?repos=TonaSmith/MSG_TO_EML&type=timeline&logscale&legend=top-left" />
 </picture>
</a>
![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-Stable-brightgreen.svg)
