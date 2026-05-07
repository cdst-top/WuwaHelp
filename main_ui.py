import sys  # 导入系统模块，用于处理命令行参数和退出程序
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QHBoxLayout, QVBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QTextEdit,
    QLabel, QFrame
)  # 从 PySide6 库中导入所有需要的界面组件（小部件）

# 主窗口类，继承自 QMainWindow（这是 PySide6 提供的一个标准主窗口模板）
class SimpleUI(QMainWindow):
    def __init__(self):
        super().__init__()  # 调用父类的初始化方法，确保窗口正确创建
        self.setWindowTitle("PySide6 极简左右布局UI")  # 设置窗口顶部的标题
        self.resize(1024, 768)  # 设置窗口的初始大小（宽1024，高768）

        # ========== 1. 全局根布局：左右水平布局 =======ß===
        # 在 PySide6 中，每个窗口都必须有一个“中心部件”来承载布局
        root_widget = QWidget()  # 创建一个空白的基础部件
        self.setCentralWidget(root_widget)  # 将它设置为窗口的正中心部件
        root_layout = QHBoxLayout(root_widget)  # 创建一个“水平布局管理器”，并绑定到根部件上

        # ---------- 左侧菜单栏 ----------
        self.menu_list = QListWidget()  # 创建一个列表选择框，作为左侧菜单
        # 往菜单里添加 3 个具体的功能选项
        QListWidgetItem("数据全景", self.menu_list)
        QListWidgetItem("账号详情", self.menu_list)
        QListWidgetItem("账号管理", self.menu_list)
        
        # 绑定点击事件：当用户点击菜单项时，执行 self.on_menu_click 函数
        self.menu_list.itemClicked.connect(self.on_menu_click)
        
        # 固定左侧菜单的宽度为 200 像素，防止它被右侧内容挤压
        self.menu_list.setFixedWidth(100)

        # ---------- 右侧整体区域 ----------
        # 右侧部分通常比较复杂，我们先创建一个空白部件来当容器
        right_widget = QWidget()
        # 为右侧容器设置“垂直布局管理器”，让里面的内容从上往下排
        right_layout = QVBoxLayout(right_widget)

        # 右侧顶部：存放按钮的水平区域
        btn_layout = QHBoxLayout()  # 创建一个小型的水平布局
        self.btn_add = QPushButton("添加")  # 创建“添加”按钮
        self.btn_del = QPushButton("删除")  # 创建“删除”按钮
        self.btn_refresh = QPushButton("刷新")  # 创建“刷新”按钮
        
        # 将按钮加入到这个小型水平布局中
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_del)
        btn_layout.addStretch()  # 添加一个“弹簧”，将按钮全部挤到左边，右边留白

        # 右侧下方：业务内容显示区（使用标签展示文字）
        self.content_label = QLabel("请点击左侧功能模块")  # 初始化显示的文字
        self.content_label.setFrameStyle(QFrame.Box | QFrame.Sunken)  # 给标签加一个边框，看起来更有立体感
        # 使用简单的 CSS 样式来美化标签：字体大小14像素，内边距20像素
        self.content_label.setStyleSheet("font-size: 14px; padding: 20px;")

        # 右侧最下方：业务日志文本框（用于显示程序运行过程中的详细信息）
        self.log_text = QTextEdit()  # 创建一个多行文本输入框
        self.log_text.setPlaceholderText("业务执行日志将显示在这里...")  # 设置没内容时的提示文字

        # 按照从上到下的顺序，将“按钮栏”、“内容标签”、“日志框”加入右侧的主布局
        right_layout.addLayout(btn_layout)  # 加入刚才创建的水平按钮栏
        right_layout.addWidget(self.content_label)  # 加入内容标签
        right_layout.addWidget(self.log_text)  # 加入日志框

        # ========== 左右大布局拼装 ==========
        # 最后一步，将“左侧菜单”和“整个右侧区域”加入最开始创建的水平根布局中
        root_layout.addWidget(self.menu_list)   # 左边菜单挂载
        root_layout.addWidget(right_widget)     # 右边大区域挂载

        # 绑定按钮的点击信号到对应的处理函数（槽函数）
        self.btn_add.clicked.connect(self.add_click)
        self.btn_del.clicked.connect(self.del_click)

    # 【事件处理函数】左侧菜单被点击时触发
    def on_menu_click(self, item: QListWidgetItem):
        menu_name = item.text()  # 获取被点击的菜单项文字
        self.content_label.setText(f"当前选中：{menu_name}")  # 更新右侧标签的文字
        self.log_text.append(f"👉 切换到 {menu_name}")  # 在日志框追加一条记录

    # 【事件处理函数】点击添加按钮时触发
    def add_click(self):
        # append 会在文本框末尾新起一行添加文字
        self.log_text.append("✅ 点击了【添加】按钮，可在这里调用你的Python业务函数")

    # 【事件处理函数】点击删除按钮时触发
    def del_click(self):
        self.log_text.append("❌ 点击了【删除】按钮，可在这里调用你的Python业务函数")

# 程序启动的固定模版
if __name__ == "__main__":
    # 1. 创建应用程序对象，负责管理整个程序的生命周期
    app = QApplication(sys.argv)
    
    # 2. 创建并显示我们刚才定义的窗口
    win = SimpleUI()
    win.show()  # 这一步非常重要，不写 show 窗口就不会弹出来
    
    # 3. 进入程序的“主循环”，等待用户点击、拖动等操作，直到关闭窗口
    sys.exit(app.exec())