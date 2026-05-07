# 需要哪些库
import asyncio
import webbrowser
import uuid
import httpx
import json
import os
from typing import List, Dict, Optional


# 定义登录类，封装相关核心逻辑
class KuroLogin:
    def __init__(self):
        self.base_url = "https://api.kurobbs.com"
        self.server_id = "76402e5b20be2c39f095a152090afddc"
        self.game_id = "3"
        self.user_agent = "Mozilla/5.0 (Linux; Android 9; 23116PN5BC Build/PQ3A.190605.02201427; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Mobile Safari/537.36 Kuro/2.5.0 KuroGameBox/2.5.0"
        self.public_ip = "10.10.10.10"
        self.did = uuid.uuid4().hex

        # 兼容打包前后的路径获取
        import sys
        if getattr(sys, 'frozen', False):
            self.base_dir = os.path.dirname(sys.executable)
        else:
            self.base_dir = os.path.dirname(os.path.abspath(__file__))
            
        self.config_file = os.path.join(self.base_dir, "config.json")

    async def fetch_public_ip(self):
        """
        异步获取公网 IPy
        """
        services = [
            "https://event.kurobbs.com/event/ip",
            "https://api.ipify.org/?format=json",
            "https://httpbin.org/ip"   
        ]

        async with httpx.AsyncClient(timeout=5) as client:
            for service in services:
                try:
                    resp = await client.get(service)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict):
                            self.public_ip = data.get("ip") or data.get("origin", "") or self.public_ip
                        else:
                            self.public_ip = str(data)
                        break  # 成功获取后立即退出循环
                except Exception:
                    continue
        return self.public_ip
                        

    def get_dev_code(self):
        
        return f"{self.public_ip}, {self.user_agent}"
    
    async def login(self, phone: str, code: str) -> Optional[str]:
        """
        异步登录
        :param phone: 手机号
        :param code: 验证码
        :return: 登录凭证（成功时返回），否则返回 None
        """
        url = f"{self.base_url}/user/sdkLogin"
        params = {
            "code": code,
            "mobile": phone,
            "devCode": self.did
        }

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "source": "android",
            "devcode": self.get_dev_code(),
            "did": self.did,
            "User-Agent": self.user_agent,
            "Accept": "application/json, text/plain, */*"
        }

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.post(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data =resp.json()
                    if data.get("code") == 200:
                        return data.get("data", {}).get("token")
                    else:
                        print(f"登录失败: {data.get('msg', '未知错误')}")
                        
                else:
                    print(f"登录失败: {resp.status_code}")
            except Exception as e:
                print(f"登录请求异常: {e}")
        return None
        
    async def get_roles(self, token: str) -> List[Dict]:
        """
        异步获取角色列表
        :param token: 登录凭证
        :return: 角色列表
        """
        url = f"{self.base_url}/gamer/role/list"

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "token": token,
            "source": "android",
            "devcode": self.get_dev_code(),
            "did": self.did,
            "User-Agent": self.user_agent,
        }

        params = {"gameId": self.game_id}

        async with httpx.AsyncClient(timeout=10) as client:
            try:
                resp = await client.post(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data =resp.json()
                    if data.get("code") == 200:
                        return data.get("data", [])
                    else:
                        print(f"获取角色列表失败: {data.get('msg', '未知错误')}")
                        
                else:
                    print(f"网络请求失败: {resp.status_code}")
            except Exception as e:
                print(f"获取角色列表请求异常: {e}")
        return []

    def save_config(self, token: str, roles: List[Dict]):
        """
        将登录成功的凭证和角色信息持久化保存到本地 JSON 文件中
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

        if not exists:
            config["accounts"].append(new_account)

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
    
    phone = input("\n请输入手机号: ").strip()
    code = input("请输入验证码: ").strip()

    print("\n正在登录...")
    # 执行异步登录请求
    token = await login_tool.login(phone, code)

    if token:
        print("\n登录成功！")
        # 获取角色列表
        roles = await login_tool.get_roles(token)
        if roles:
            print("\n角色列表:", roles)
            for i, role in enumerate(roles):
                # print(f"角色 {i+1}: {role.get('roleName', '未知角色')}")
                print(f"[{i}] {role.get('roleName')} (ID: {role.get('roleId')})")
            login_tool.save_config(token, roles)
        else:
            print("\n获取角色列表失败")
    else:
        print("\n登录失败")

if __name__ == "__main__":
    # 使用 asyncio 运行顶层协程，开始程序
    asyncio.run(run_login_flow())
