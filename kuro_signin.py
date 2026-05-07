import asyncio  # 导入异步 I/O 库，用于处理并发网络请求
import httpx  # 导入 httpx 库，一个支持异步的 HTTP 客户端
import json  # 导入 json 库，用于处理 JSON 数据的序列化和反序列化
import os  # 导入 os 库，用于文件路径操作和系统交互
import datetime  # 导入 datetime 库，用于获取和格式化日期时间
from typing import List, Optional, Dict  # 导入类型提示，增强代码可读性

class KuroSignInTool:
    """库洛游戏自动签到工具类"""
    def __init__(self):
        # 初始化基础 URL，库洛社区 API 的根地址
        self.base_url = "https://api.kurobbs.com"
        # 预设的服务 ID，用于标识游戏服务器环境
        self.server_id = "76402e5b20be2c39f095a152090afddc"
        # 游戏 ID，'3' 通常代表《鸣潮》
        self.game_id = "3"
        # 模拟库街区 App 的 User-Agent，包含官方版本标识
        self.user_agent = "Mozilla/5.0 (Linux; Android 9; 23116PN5BC Build/PQ3A.190605.02201427; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Mobile Safari/537.36 Kuro/2.5.0 KuroGameBox/2.5.0"
        
        # 统一路径获取：存放在用户文档目录下
        import os
        self.base_dir = os.path.join(os.path.expanduser("~"), "Documents", "WuwaHelp")
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            
        # 拼接配置文件的完整存储路径，默认名为 config.json
        self.config_file = os.path.join(self.base_dir, "config.json")
        # 初始化时自动加载配置数据
        self.config = self._load_config()

    def _load_config(self):
        """内部方法：从本地文件加载用户配置"""
        # 检查配置文件是否存在
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"未找到配置文件: {self.config_file}，请先运行 kuro_login.py")
        # 读取并解析 JSON 配置文件
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 兼容性处理：统一将单账号或多账号格式转化为 accounts 列表格式
            if "accounts" in data:
                return data
            elif "token" in data:
                return {"accounts": [data]}
            else:
                return {"accounts": []}

    def _get_headers(self, token: str, did: str = ""):
        """内部方法：构造符合库洛 API 要求的请求头"""
        return {
            "User-Agent": self.user_agent,  # 模拟设备标识
            "Source": "android",            # 标识请求来源为安卓端
            "token": token,                 # 用户登录凭证
            "devcode": "127.127.127.127, " + self.user_agent, # 简化处理：固定 IP + UA
            "did": did or self.config.get("did", ""),         # 设备唯一标识
            "Accept": "application/json, text/plain, */*",    # 声明接受的数据格式
            "Content-Type": "application/x-www-form-urlencoded", # 声明提交的数据格式
            "origin": "https://web-static.kurobbs.com",       # 跨域请求来源
            "x-requested-with": "com.kurogame.kjq"            # 标识为 App 发起的请求
        }

    async def init_sign_in(self, role_id: str, user_id: str, token: str, did: str):
        """初始化签到数据：获取当前月份的奖品列表和用户的签到状态"""
        url = f"{self.base_url}/encourage/signIn/initSignInV2"
        # 构造请求参数，包含游戏、服务器、角色和用户 ID
        params = {
            "gameId": self.game_id,
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id
        }
        headers = self._get_headers(token, did=did)
        # 发送异步 POST 请求
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, params=params)
            return resp.json()  # 返回解析后的 JSON 响应

    async def do_sign_in(self, role_id: str, user_id: str, token: str, did: str):
        """执行实际的签到操作"""
        url = f"{self.base_url}/encourage/signIn/v2"
        now = datetime.datetime.now()
        # 签到接口通常需要传入当前月份 (reqMonth)
        params = {
            "gameId": self.game_id,
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id,
            "reqMonth": f"{now.month:02d}"  # 格式化为两位数，如 '05'
        }
        headers = self._get_headers(token, did=did)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, params=params)
            return resp.json()

    async def get_sign_in_history(self, role_id: str, user_id: str, token: str, did: str):
        """查询最近的签到历史记录"""
        url = f"{self.base_url}/encourage/signIn/queryRecordV2"
        params = {
            "gameId": self.game_id,
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id
        }
        headers = self._get_headers(token, did=did)
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, params=params)
            return resp.json()

async def main():
    """程序主入口：遍历账号执行签到任务"""
    try:
        # 实例化工具类
        tool = KuroSignInTool()
        # 从配置中获取账号列表
        accounts = tool.config.get("accounts", [])
        
        # 检查是否已有登录信息
        if not accounts:
            print("配置文件中没有账号信息，请先运行 kuro_login.py 登录。")
            return

        # 遍历每一个已保存的账号
        for acc_index, account in enumerate(accounts):
            token = account["token"]
            roles = account.get("roles", [])
            did = account.get("did", "")
            
            # 如果该账号下没有角色信息，则跳过
            if not roles:
                continue

            # 遍历账号下的每一个角色（例如同一个账号有不同区服的角色）
            for role in roles:
                role_id = role["roleId"]
                user_id = role["userId"]
                role_name = role["roleName"]

                print(f"\n--- 账号 {acc_index + 1}: 正在为角色 [{role_name}] 执行签到流程 ---")

                try:
                    # 1. 检查今日签到状态：先调用初始化接口
                    init_data = await tool.init_sign_in(role_id, user_id, token, did)
                    if init_data.get("code") == 200:
                        data = init_data.get("data", {})
                        is_signed = data.get("isSigIn")  # 是否已签到
                        sign_num = data.get("sigInNum")   # 累计签到次数
                        print(f"本月已签到次数: {sign_num}")
                        
                        if is_signed:
                            # 如果接口返回已签到，则无需后续操作
                            print("今日已签到，无需重复操作。")
                        else:
                            # 2. 如果未签到，执行正式签到接口
                            print("今日尚未签到，正在执行签到...")
                            sign_res = await tool.do_sign_in(role_id, user_id, token, did)
                            if sign_res.get("code") == 200:
                                print(f"签到成功！消息: {sign_res.get('msg')}")
                            else:
                                print(f"签到失败: {sign_res.get('msg')}")
                    else:
                        print(f"初始化签到失败: {init_data.get('msg')}")

                    # 3. 获取并显示最近的历史记录，用于确认奖励是否到账
                    history_data = await tool.get_sign_in_history(role_id, user_id, token, did)
                    if history_data.get("code") == 200:
                        records = history_data.get("data", [])
                        if records:
                            print("最近签到奖励记录:")
                            # 仅打印最近的 3 条记录
                            for record in records[:3]:
                                print(f"- {record.get('serialNum')}: {record.get('goodsName')} x{record.get('goodsNum')}")
                except Exception as e:
                    # 捕获单个角色操作中的异常，不影响其他角色
                    print(f"签到过程发生异常: {e}")
        
    except Exception as e:
        # 捕获全局初始化或配置读取中的严重错误
        print(f"发生错误: {e}")

if __name__ == "__main__":
    # 使用异步事件循环运行 main 协程
    asyncio.run(main())
