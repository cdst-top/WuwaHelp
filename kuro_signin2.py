import asyncio
from tarfile import data_filter
import httpx
import json
import os
import datetime

class KuroSignInTool:
    def __init__(self):
        self.base_url = "https://api.kurobbs.com"
        self.server_id = "10000000000000000000000000000000"
        self.game_id = "3"
        self.user_agent = "Mozilla/5.0 (Linux; Android 9;)"

        import sys
        if getattr(sys, 'frozen', False):
            self.base_url = os.path.dirname(sys.executable)
        else:
            self.base_url = os.path.dirname(os.path.abspath(__file__))

        self.config_file = os.path.join(self.base_url, "config.json")
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"Config file not found: {self.config_file},请先运行 kuro_signin2.py 初始化配置")
        
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
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
    
    async def init_sign_in(self, role_id: str, user_id: str, token: str, did: str = ""):
        """初始化签到"""
        url = f"{self.base_url}/encourage/signIn/initSignInV2"

        params = {
            "gameId": self.game_id,
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id,
        }

        headers = self._get_headers(token, did=did)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, data=params)
            return response.json()
        
    async def do_sign_in(self, role_id: str, user_id: str, token: str, did: str):
        """签到"""
        url = f"{self.base_url}/encourage/signIn/v2"
        now = datetime.datetime.now()
        params = {
            "gameId": self.game_id,
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id,
            "reqMonth": f"{now.month:02d}"
        }
        headers = self._get_headers(token, did=did)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, data=params)
            return response.json()
    
    async def get_sign_in_history(self, role_id: str, user_id: str, token: str, did: str):
        """获取签到历史"""
        url = f"{self.base_url}/encourage/signIn/queryRecordV2"
        params = {
            "gameId": self.game_id,
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id,
        }
        headers = self._get_headers(token, did=did)
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(url, headers=headers, data=params)
            return response.json()

async def main():
    try:
        tool = KuroSignInTool()
        accounts = tool.config.get("accounts", [])
        if not accounts:
            raise ValueError("No accounts found in config.json. Please add accounts to the config file.")
            return
        
        for acc_index, account in enumerate(accounts):
            token = account.get("token", "")
            did = account.get("did", "")
            roles = account.get("roles", [])
            
            if not roles:
                continue

            for role in roles:
                role_id = role["roleId"]
                user_id = role["userId"]
                role_name = role["roleName"]

                print(f"\n---账号 {acc_index + 1} :正在为角色[{role_name}]执行签到流程 ---")

                try:
                    init_data = await tool.init_sign_in(role_id, user_id, token, did)
                    if init_data.get("code") == 200:
                        data = init_data.get("data", {})
                        is_signed = data.get("isSignIn")
                        sign_num = data.get("signInNum")
                        print(f"本月签到次数: {sign_num}")

                        if is_signed:
                            print("角色已签到")
                        else:
                            print("角色未签到, 开始签到")
                            sign_res = await tool.do_sign_in(role_id, user_id, token, did)
                            if sign_res.get("code") == 200:
                                print(f"签到成功: {sign_res.get('msg')}")
                            else:
                                print(f"签到失败: {sign_res.get('msg')}")
                    else:
                        print(f"初始化签到失败: {init_data.get('msg')}")

                    history_data = await tool.get_sign_in_history(role_id, user_id, token, did)
                    if history_data.get("code") == 200:
                        records = history_data.get("data", [])
                        if records:
                            print("最近签到奖励记录:")
                            for record in records[:3]:
                                print(f"日期: {record.get('signInDate')}, 奖励: {record.get('goodsName')} x{record.get('goodsNum')}")
                except Exception as e:
                    print(f"获取签到历史失败: {e}")
    except Exception as e:
        print(f"主程序出错: {e}")

if __name__ == "__main__":
    asyncio.run(main())
                                


            
