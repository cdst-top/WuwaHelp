import sys  # 导入系统模块
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QComboBox, QScrollArea, QGridLayout, QFrame
)  # 导入 PySide6 核心组件
import json
import os
import sys
import asyncio

def get_base_dir():
    """获取程序运行时的基础目录。为了稳定性和可见性，统一存放在用户文档目录下"""
    # 获取当前用户的“文档”文件夹路径
    doc_path = os.path.join(os.path.expanduser("~"), "Documents", "WuwaHelp")
    # 如果文件夹不存在，则自动创建
    if not os.path.exists(doc_path):
        try:
            os.makedirs(doc_path, exist_ok=True)
        except:
            # 如果创建失败（极罕见），回退到源码所在目录
            return os.path.dirname(os.path.abspath(__file__))
    return doc_path

from wuwa_login import KuroLogin  # 导入已有的登录逻辑类
from kuro_signin import KuroSignInTool  # 导入签到逻辑类
from get_game_data import GameDataTool  # 导入游戏数据获取类
from PySide6.QtCore import Qt, QThread, Signal, QTimer  # 增加 QTimer 支持

# 增加一个登录线程类，防止 GUI 界面在请求网络时卡死
class LoginThread(QThread):
    finished = Signal(dict)  # 登录完成信号，传递结果字典

    def __init__(self, phone, code):
        super().__init__()
        self.phone = phone
        self.code = code
        self.login_tool = KuroLogin()

    def run(self):
        # 在子线程中运行异步登录逻辑
        async def do_work():
            await self.login_tool.fetch_public_ip()
            token = await self.login_tool.login(self.phone, self.code)
            if token:
                roles = await self.login_tool.get_roles(token)
                return {"success": True, "token": token, "roles": roles, "did": self.login_tool.did}
            return {"success": False, "msg": "登录失败，请检查验证码"}
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do_work())
        self.finished.emit(result)

# 增加一个全账号自动签到线程类
class SignAllThread(QThread):
    progress = Signal(str)  # 用于向界面发送进度和奖励信息
    finished = Signal()     # 签到全部完成信号

    def run(self):
        async def do_sign():
            try:
                tool = KuroSignInTool()
                accounts = tool.config.get("accounts", [])
                
                if not accounts:
                    self.progress.emit("❌ 错误：未找到已登录账号，请先前往【账号登录】页签。")
                    return

                for acc_index, account in enumerate(accounts):
                    token = account["token"]
                    roles = account.get("roles", [])
                    did = account.get("did", "")
                    phone = account.get("mobile", "未知号码")
                    
                    self.progress.emit(f"--- 账号 {acc_index + 1} ({phone}): 正在启动 ---")

                    for role in roles:
                        role_id = role["roleId"]
                        user_id = role["userId"]
                        role_name = role["roleName"]

                        # 1. 初始化并检查状态
                        init_data = await tool.init_sign_in(role_id, user_id, token, did)
                        if init_data.get("code") == 200:
                            is_signed = init_data.get("data", {}).get("isSigIn")
                            if is_signed:
                                self.progress.emit(f"✅ 角色 [{role_name}]: 今日已签到")
                            else:
                                # 2. 执行签到
                                sign_res = await tool.do_sign_in(role_id, user_id, token, did)
                                if sign_res.get("code") == 200:
                                    self.progress.emit(f"🎉 角色 [{role_name}]: 签到成功！")
                                else:
                                    self.progress.emit(f"❌ 角色 [{role_name}]: 签到失败 ({sign_res.get('msg')})")
                        
                        # 3. 获取历史记录以显示奖励
                        history = await tool.get_sign_in_history(role_id, user_id, token, did)
                        if history.get("code") == 200:
                            records = history.get("data", [])
                            if records:
                                latest = records[0]
                                self.progress.emit(f"🎁 最近奖励: {latest.get('goodsName')} x{latest.get('goodsNum')}")
            except Exception as e:
                self.progress.emit(f"⚠️ 运行异常: {str(e)}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(do_sign())
        self.finished.emit()

# 增加一个游戏数据获取线程类
class FetchGameDataThread(QThread):
    progress = Signal(str)  # 发送单行日志
    finished = Signal(list)  # 完成后传递所有账号的游戏数据汇总

    def run(self):
        async def do_fetch():
            try:
                tool = GameDataTool()
                accounts = tool.config.get("accounts", [])
                all_data = []  # 汇总所有账号的游戏数据

                if not accounts:
                    self.progress.emit("❌ 错误：未找到已登录账号，请先前往【账号登录】页签。")
                    return

                for acc_index, account in enumerate(accounts):
                    token = account["token"]
                    roles = account.get("roles", [])
                    did = account.get("did", "")
                    phone = account.get("mobile", "未知号码")

                    self.progress.emit(f"--- 正在刷新账号 {acc_index + 1} ({phone}) ---")

                    for role in roles:
                        role_id = role["roleId"]
                        user_id = role["userId"]
                        role_name = role.get("roleName", "未知角色")

                        try:
                            # 1. 获取 B-At 令牌
                            b_at = await tool.get_b_at_token(role_id, user_id, token, did)

                            # 2. 获取每日实时数据（包含结晶波片、活跃度等）
                            daily = await tool.get_daily_data(role_id, token, b_at, did)
                            daily_details = []
                            if isinstance(daily, dict) and daily.get("code") == 200:
                                daily_data = daily.get("data", {})
                                # 按顺序提取关键数据项
                                for key in ["energyData", "livenessData", "storeEnergyData", "towerData", "weeklyData"]:
                                    detail = daily_data.get(key)
                                    if detail and isinstance(detail, dict):
                                        daily_details.append({
                                            "name": detail.get("name", key),
                                            "cur": detail.get("cur", detail.get("value", "?")),
                                            "total": detail.get("total", "?")
                                        })
                            
                            self.progress.emit(f"✅ 成功获取角色: {role_name}")
                            all_data.append({
                                "phone": phone,
                                "roleName": role_name,
                                "details": daily_details
                            })
                        except Exception as e:
                            self.progress.emit(f"⚠️ 角色 [{role_name}] 获取失败: {str(e)}")

                return all_data
            except Exception as e:
                self.progress.emit(f"⚠️ 运行异常: {str(e)}")

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(do_fetch())
        self.finished.emit(result if result else [])

class TabbedUI(QMainWindow):
    """
    使用 QTabWidget 实现页签导航的进阶 UI 演示
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("鸣潮签到助手")
        self.resize(1024, 768)

        # 1. 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 2. 创建主布局（垂直布局）
        main_layout = QVBoxLayout(central_widget)

        # 3. 创建 QTabWidget（页签窗口部件）
        # 它是实现“左侧/顶部切换页签”的核心组件
        self.tabs = QTabWidget()
        
        # 将页签组件加入主布局
        main_layout.addWidget(self.tabs)

        # 4. 创建并添加各个功能页面
        self.setup_tab1()
        self.setup_tab2()
        self.setup_tab3()
        
        # 设置默认显示的页签为"角色数据"（索引1）
        self.tabs.setCurrentIndex(1)
        
        # 优化启动体验：不在初始化时直接运行耗时任务
        # 使用 QTimer.singleShot 在窗体显示 100ms 后再自动执行数据刷新和签到
        QTimer.singleShot(100, self.auto_start_tasks)

    def auto_start_tasks(self):
        """窗体显示后自动执行的任务"""
        self.handle_refresh_game_data()
        self.handle_sign_all()

    def setup_tab1(self):
        """功能页面1：登录管理"""
        tab = QWidget()  # 每个页签本质上都是一个独立的 QWidget
        layout = QVBoxLayout(tab)  # 为这个页面设置布局

        # 创建一个支持超链接的标签
        link_label = QLabel('请前往库街区网页版获取验证码: <a href="https://www.kurobbs.com/mc/home/9" style="color: #0078d4; text-decoration: underline;">点击打开网页</a>')
        link_label.setOpenExternalLinks(True)  # 关键设置：允许点击链接时自动打开系统默认浏览器
        layout.addWidget(link_label)
        layout.addWidget(QLabel("手机号："))
        
        # 使用 QComboBox 替代 QLineEdit
        # QComboBox 是下拉框，setEditable(True) 后可以让它像输入框一样输入新内容
        self.phone_combo = QComboBox()
        self.phone_combo.setEditable(True) 
        self.phone_combo.setPlaceholderText("请输入或选择手机号")
        layout.addWidget(self.phone_combo)
        
        # 尝试从本地 config.json 加载历史号码
        self.load_history_phones()

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("请输入验证码")
        layout.addWidget(self.code_input)
        
        self.btn_login = QPushButton("开始登录")
        self.btn_login.clicked.connect(self.handle_login) # 绑定专门的登录处理函数
        layout.addWidget(self.btn_login)
        
        layout.addStretch()  # 添加弹簧，让内容靠上排版
        self.tabs.addTab(tab, "账号登录")  # 将页面加入页签栏，并设置标签文字

    def load_history_phones(self):
        """从 config.json 加载历史登录过的手机号"""
        config_path = os.path.join(get_base_dir(), "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # 假设 config.json 中有 accounts 列表，每个 account 有 mobile 字段
                    accounts = data.get("accounts", [])
                    phones = []
                    for acc in accounts:
                        # 尝试从不同可能的字段名中获取手机号
                        phone = acc.get("mobile") or acc.get("phone")
                        if phone and phone not in phones:
                            phones.append(str(phone))
                    
                    # 将获取到的号码添加到下拉框中
                    self.phone_combo.addItems(phones)
            except Exception as e:
                print(f"加载历史号码失败: {e}")

    def handle_login(self):
        """处理登录按钮点击事件"""
        current_phone = self.phone_combo.currentText().strip()
        current_code = self.code_input.text().strip()
        
        if not current_phone or not current_code:
            self.statusBar().showMessage("错误：手机号或验证码不能为空", 3000)
            return

        self.btn_login.setEnabled(False)
        self.btn_login.setText("正在登录...")
        
        # 启动登录子线程
        self.login_thread = LoginThread(current_phone, current_code)
        self.login_thread.finished.connect(self.on_login_finished)
        self.login_thread.start()

    def on_login_finished(self, result):
        """登录完成的回调"""
        self.btn_login.setEnabled(True)
        self.btn_login.setText("开始登录")
        
        if result["success"]:
            phone = self.phone_combo.currentText().strip()
            # 1. 更新界面记忆
            if self.phone_combo.findText(phone) == -1:
                self.phone_combo.addItem(phone)
            
            # 2. 调用 wuwa_login 的保存逻辑，并额外记录手机号
            login_tool = KuroLogin()
            # 构造带手机号的 roles 数据（或者在保存配置时额外处理）
            # 这里我们手动更新一下 config.json 确保手机号被存入
            self.update_config_with_phone(phone, result["token"], result["roles"], result["did"])
            
            self.statusBar().showMessage(f"登录成功！欢迎，{phone}", 5000)
            self.code_input.clear()
        else:
            self.statusBar().showMessage(result["msg"], 5000)

    def update_config_with_phone(self, phone, token, roles, did):
        """增强版的配置保存，确保手机号被记录以便记忆功能使用"""
        config_path = os.path.join(get_base_dir(), "config.json")
        config = {"accounts": []}
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
            except: pass

        new_acc = {
            "mobile": phone, # 明确保存手机号
            "token": token,
            "did": did,
            "roles": roles
        }

        # 去重更新逻辑
        exists = False
        for i, acc in enumerate(config.get("accounts", [])):
            if acc.get("mobile") == phone:
                config["accounts"][i] = new_acc
                exists = True
                break
        
        if not exists:
            if "accounts" not in config: config["accounts"] = []
            config["accounts"].append(new_acc)

        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)

    def setup_tab2(self):
        """功能页面2：角色信息 - 9宫格展示"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("<h3>功能模块 2：账号状态概览</h3>"))

        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        
        # 内部网格容器
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll.setWidget(self.grid_container)
        layout.addWidget(scroll)

        # 刷新按钮
        self.btn_refresh_game = QPushButton("🔄 刷新账号状态")
        self.btn_refresh_game.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:disabled { background-color: #c8c8c8; }
        """)
        self.btn_refresh_game.clicked.connect(self.handle_refresh_game_data)
        layout.addWidget(self.btn_refresh_game)

        # 增加一个打开配置文件夹的辅助按钮
        self.btn_open_folder = QPushButton("📂 打开配置文件所在目录")
        self.btn_open_folder.setStyleSheet("color: #666; font-size: 11px; border: none; background: transparent; text-decoration: underline;")
        self.btn_open_folder.clicked.connect(self.open_config_folder)
        layout.addWidget(self.btn_open_folder)

        self.tabs.addTab(tab, "角色数据")

    def open_config_folder(self):
        """打开配置文件所在的文件夹"""
        import webbrowser
        folder = get_base_dir()
        webbrowser.open(f"file://{folder}")

    def create_account_card(self, data):
        """创建一个简洁美观的账号卡片"""
        card = QFrame()
        card.setFixedWidth(240)
        card.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QFrame:hover {
                border: 1px solid #0078d4;
            }
        """)
        
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 15, 15, 15)
        card_layout.setSpacing(8)

        # 标题：手机号和角色名
        header = QLabel(f"📱 {data['phone']}\n👤 {data['roleName']}")
        header.setStyleSheet("font-weight: bold; color: #333; font-size: 13px;")
        card_layout.addWidget(header)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet("background-color: #f0f0f0;")
        card_layout.addWidget(line)

        # 详细信息：使用水平布局实现标题靠左、数据靠右
        for detail in data['details']:
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(0, 2, 0, 2)
            row_layout.setSpacing(10)

            # 标题：靠左
            name_label = QLabel(detail['name'])
            name_label.setStyleSheet("color: #666; font-size: 12px;")

            # 数据：根据不同项目设置不同的红色阈值，活跃度始终不变色
            cur = detail.get('cur', 0)
            name = detail['name']
            is_high_value = (
                (name == '结晶波片' and isinstance(cur, (int, float)) and cur > 180) or
                (name == '结晶单质' and isinstance(cur, (int, float)) and cur > 240)
            )
            if is_high_value:
                value_label = QLabel(f"<span style='color: #e74c3c; font-weight: bold;'>{cur}</span><span style='color: #999;'>/{detail['total']}</span>")
            else:
                value_label = QLabel(f"<span style='color: #0078d4; font-weight: bold;'>{cur}</span><span style='color: #999;'>/{detail['total']}</span>")

            row_layout.addWidget(name_label)
            row_layout.addStretch()
            row_layout.addWidget(value_label)

            card_layout.addWidget(row_widget)

        card_layout.addStretch()
        return card

    def handle_refresh_game_data(self):
        """点击刷新角色列表按钮"""
        # 清空现有网格内容
        while self.grid_layout.count():
            child = self.grid_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        self.btn_refresh_game.setEnabled(False)
        self.btn_refresh_game.setText("正在刷新数据...")
        self.statusBar().showMessage("正在获取各账号游戏数据...")

        # 启动游戏数据获取线程
        self.fetch_thread = FetchGameDataThread()
        self.fetch_thread.finished.connect(self.on_refresh_game_data_finished)
        self.fetch_thread.start()

    def on_refresh_game_data_finished(self, all_data):
        """刷新完成后的回调"""
        self.btn_refresh_game.setEnabled(True)
        self.btn_refresh_game.setText("🔄 刷新账号状态")

        if all_data:
            # 填充网格布局（3列，即9宫格模式）
            for i, data in enumerate(all_data):
                row = i // 3
                col = i % 3
                card = self.create_account_card(data)
                self.grid_layout.addWidget(card, row, col)
            
            self.statusBar().showMessage(f"刷新成功，共加载 {len(all_data)} 个角色数据", 3000)
        else:
            self.statusBar().showMessage("⚠️ 未获取到任何数据，请确认已登录", 5000)
            no_data = QLabel("暂无数据，请先登录账号并刷新")
            no_data.setStyleSheet("color: #999; margin: 20px;")
            self.grid_layout.addWidget(no_data, 0, 0)

    def setup_tab3(self):
        """功能页面3：自动签到"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        layout.addWidget(QLabel("<h3>功能模块 3：全账号自动签到</h3>"))
        
        # 结果显示区
        self.sign_log = QTextEdit()
        self.sign_log.setReadOnly(True)
        self.sign_log.setPlaceholderText("点击下方按钮开始全自动签到...")
        layout.addWidget(self.sign_log)
        
        self.btn_sign_all = QPushButton("立即执行全账号签到")
        self.btn_sign_all.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 12px;")
        self.btn_sign_all.clicked.connect(self.handle_sign_all)
        layout.addWidget(self.btn_sign_all)
        
        self.tabs.addTab(tab, "自动签到")

    def handle_sign_all(self):
        """点击全账号签到按钮"""
        self.sign_log.clear()
        self.btn_sign_all.setEnabled(False)
        self.btn_sign_all.setText("正在全自动签到中...")
        
        # 启动签到子线程
        self.sign_thread = SignAllThread()
        self.sign_thread.progress.connect(lambda msg: self.sign_log.append(msg))
        self.sign_thread.finished.connect(self.on_sign_all_finished)
        self.sign_thread.start()

    def on_sign_all_finished(self):
        """全账号签到完成"""
        self.btn_sign_all.setEnabled(True)
        self.btn_sign_all.setText("立即执行全账号签到")
        self.sign_log.append("\n✨ 所有账号签到任务执行完毕！")
        self.statusBar().showMessage("签到任务已完成", 5000)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TabbedUI()
    window.show()
    sys.exit(app.exec())
