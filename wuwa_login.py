import asyncio  # 导入异步 I/O 库，用于处理并发网络请求
import httpx  # 导入 httpx 库，一个支持异步的 HTTP 客户端
import uuid  # 导入 uuid 库，用于生成设备唯一标识符
import json  # 导入 json 库，用于处理 JSON 数据的序列化和反序列化
import os  # 导入 os 库，用于文件路径操作和系统交互
import webbrowser  # 导入 webbrowser 库，用于在默认浏览器中打开网页
from typing import Optional, List, Dict  # 导入类型提示，增强代码可读性和类型检查

class KuroLogin:
    """库洛游戏登录类，封装了登录相关的核心逻辑"""
    def __init__(self):
        # 初始化基础 URL，库洛社区的 API 地址
        self.base_url = "https://api.kurobbs.com"
        # 预设的服务 ID，可能用于标识特定的服务端环境
        self.server_id = "76402e5b20be2c39f095a152090afddc"
        # 游戏 ID，'3' 通常代表《鸣潮》
        self.game_id = "3"
        # 设置模拟移动端浏览器的 User-Agent，防止被服务器识别为非法爬虫
        self.user_agent = "Mozilla/5.0 (Linux; Android 9; 23116PN5BC Build/PQ3A.190605.02201427; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Mobile Safari/537.36 Kuro/2.5.0 KuroGameBox/2.5.0"
        # 默认公网 IP，后续会通过 fetch_public_ip 进行动态更新
        self.public_ip = "127.127.127.127"
        # 生成一个随机的 32 位十六进制字符串作为设备唯一 ID (did)
        self.did = uuid.uuid4().hex
        
        # 统一路径获取：存放在用户文档目录下，解决打包后权限和路径漂移问题
        import os
        self.base_dir = os.path.join(os.path.expanduser("~"), "Documents", "WuwaHelp")
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            
        # 拼接配置文件的完整存储路径
        self.config_file = os.path.join(self.base_dir, "config.json")

    async def fetch_public_ip(self):
        """异步获取当前设备的公网 IP 地址"""
        # 定义多个 IP 获取服务，增加容错性
        services = [
            "https://event.kurobbs.com/event/ip",
            "https://api.ipify.org/?format=json",
            "https://httpbin.org/ip"
        ]
        # 使用 httpx 的异步客户端发送请求
        async with httpx.AsyncClient(timeout=5.0) as client:
            for service in services:
                try:
                    # 发送 GET 请求获取 IP
                    resp = await client.get(service)
                    if resp.status_code == 200:
                        data = resp.json()
                        # 解析不同服务返回的 JSON 格式
                        if isinstance(data, dict):
                            self.public_ip = data.get("ip") or data.get("origin") or self.public_ip
                        else:
                            self.public_ip = str(data)
                        break  # 获取成功则退出循环
                except Exception:
                    continue  # 某个服务失败则尝试下一个
        return self.public_ip  # 返回最终获取到的 IP

    def get_dev_code(self):
        """生成并返回用于请求头的 Devcode 字符串"""
        # 按照库洛 API 的要求拼接 IP 和 User-Agent
        return f"{self.public_ip}, {self.user_agent}"

    async def login(self, phone: str, code: str) -> Optional[str]:
        """
        执行登录 API 请求
        :param phone: 用户输入的手机号
        :param code: 用户获取到的短信验证码
        :return: 登录成功返回 token，否则返回 None
        """
        # 登录接口的具体路径
        url = f"{self.base_url}/user/sdkLogin"
        # 构造请求参数
        params = {
            "code": code,      # 验证码
            "mobile": phone,   # 手机号
            "devCode": self.did # 设备唯一标识
        }
        # 构造请求头，模拟真实移动端请求
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "source": "android",
            "devcode": self.get_dev_code(),
            "did": self.did,
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*"
        }
        
        # 开启异步 HTTP 客户端
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 发送 POST 请求执行登录
                resp = await client.post(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    # 判断业务状态码是否为成功 (200)
                    if data.get("code") == 200:
                        token = data.get("data", {}).get("token")
                        return token
                    else:
                        print(f"登录失败: {data.get('msg')}")
                else:
                    print(f"网络请求失败: {resp.status_code}")
            except Exception as e:
                print(f"请求发生异常: {e}")
        return None

    async def get_roles(self, token: str) -> List[Dict]:
        """
        根据登录获得的 token 获取关联的游戏角色列表
        :param token: 登录成功的凭证
        :return: 角色信息列表
        """
        # 获取角色列表的接口路径
        url = f"{self.base_url}/gamer/role/list"
        # 构造包含 token 的请求头
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "token": token,
            "source": "android",
            "devcode": self.get_dev_code(),
            "did": self.did,
            "User-Agent": self.user_agent
        }
        # 指定游戏 ID 参数
        params = {"gameId": self.game_id}
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # 发送 POST 请求获取角色数据
                resp = await client.post(url, headers=headers, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("code") == 200:
                        # 返回角色数据数组，默认为空列表
                        return data.get("data", [])
                    else:
                        print(f"获取角色失败: {data.get('msg')}")
                else:
                    print(f"网络请求失败: {resp.status_code}")
            except Exception as e:
                print(f"请求发生异常: {e}")
        return []

    def save_config(self, token: str, roles: List[Dict]):
        """
        将登录成功的凭证和角色信息持久化保存到本地 JSON 文件中
        :param token: 登录凭证
        :param roles: 角色列表
        """
        # 构造新的账号数据项
        new_account = {
            "token": token,
            "did": self.did,
            "roles": roles
        }
        
        config = {"accounts": []}
        # 如果配置文件已存在，则读取现有配置以便追加
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    old_config = json.load(f)
                    # 兼容不同版本的配置格式
                    if "accounts" in old_config:
                        config["accounts"] = old_config["accounts"]
                    elif "token" in old_config:
                        config["accounts"].append({
                            "token": old_config["token"],
                            "did": old_config.get("did", ""),
                            "roles": old_config.get("roles", [])
                        })
            except Exception:
                pass # 忽略读取错误，使用新配置覆盖

        # 检查当前登录的账号是否已经存在于配置中（去重逻辑）
        exists = False
        if roles:
            role_id = roles[0].get("roleId")
            for i, acc in enumerate(config["accounts"]):
                # 如果角色 ID 匹配，则更新现有账号信息
                if acc["roles"] and acc["roles"][0].get("roleId") == role_id:
                    config["accounts"][i] = new_account
                    exists = True
                    break
        
        # 如果是新账号，则添加到列表中
        if not exists:
            config["accounts"].append(new_account)

        # 将更新后的完整配置写回 JSON 文件
        with open(self.config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        print(f"配置已更新至: {self.config_file}")

async def run_login_flow():
    """控制整个登录交互流程的顶层函数"""
    # 实例化登录工具类
    login_tool = KuroLogin()
    # 先异步获取公网 IP，用于后续接口校验
    await login_tool.fetch_public_ip()
    
    print("=== 库街区 Python 登录助手 ===")
    print("1. 请前往库街区网页版获取验证码: https://www.kurobbs.com/mc/home/9")
    # 询问用户是否自动打开浏览器进行操作
    if input("是否现在打开浏览器? (y/n): ").lower() == 'y':
        webbrowser.open("https://www.kurobbs.com/mc/home/9")
    
    # 获取用户输入的必要信息
    phone = input("\n请输入手机号: ").strip()
    code = input("请输入验证码: ").strip()
    
    print("\n正在登录...")
    # 执行异步登录请求
    token = await login_tool.login(phone, code)
    
    if token:
        print("登录成功! 正在获取角色列表...")
        # 登录成功后紧接着获取角色列表
        roles = await login_tool.get_roles(token)
        if roles:
            print(f"成功获取到 {len(roles)} 个角色:")
            # 遍历并打印角色基本信息
            for i, role in enumerate(roles):
                print(f"[{i}] {role.get('roleName')} (ID: {role.get('roleId')})")
            
            # 保存到本地配置以便后续自动任务使用
            login_tool.save_config(token, roles)
        else:
            print("未找到关联的游戏角色。")
    else:
        print("登录流程终止。")

if __name__ == "__main__":
    # 使用 asyncio 运行顶层协程，开始程序
    asyncio.run(run_login_flow())