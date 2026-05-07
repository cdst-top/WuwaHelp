import asyncio
import httpx
import json
import os
import uuid
from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class GameDataTool:
    def __init__(self):
        self.base_url = "https://api.kurobbs.com"
        self.server_id = "76402e5b20be2c39f095a152090afddc"
        self.game_id = "3"
        self.user_agent = "Mozilla/5.0 (Linux; Android 9; 23116PN5BC Build/PQ3A.190605.02201427; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Mobile Safari/537.36 Kuro/2.5.0 KuroGameBox/2.5.0"
        
        # 统一路径获取：存放在用户文档目录下
        import os
        self.base_dir = os.path.join(os.path.expanduser("~"), "Documents", "WuwaHelp")
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir, exist_ok=True)
            
        self.config_file = os.path.join(self.base_dir, "config.json")
        self.config = self._load_config()

    def _load_config(self):
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(f"未找到配置文件: {self.config_file}，请先运行 kuro_login.py")
        with open(self.config_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            # 兼容旧格式并统一为 accounts 列表
            if "accounts" in data:
                return data
            elif "token" in data:
                return {"accounts": [data]}
            else:
                return {"accounts": []}

    def _get_headers(self, token: str, b_at: str = "", did: str = ""):
        return {
            "User-Agent": self.user_agent,
            "Source": "android",
            "token": token,
            "B-At": b_at,
            "Did": did, # 直接使用传入的 did
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/x-www-form-urlencoded"
        }

    async def get_b_at_token(self, role_id: str, user_id: str, token: str, did: str) -> str:
        """获取 B-At 令牌"""
        url = f"{self.base_url}/aki/roleBox/requestToken"
        params = {
            "serverId": self.server_id,
            "roleId": role_id,
            "userId": user_id
        }
        headers = self._get_headers(token, did=did)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, params=params)
            data = resp.json()
            if data.get("code") == 200:
                # Java 源码中返回的是嵌套 JSON 字符串
                inner_data = json.loads(data["data"])
                return inner_data["accessToken"]
            else:
                raise Exception(f"获取 B-At 失败: {data.get('msg')}")

    async def get_daily_data(self, role_id: str, token: str, b_at: str, did: str):
        """获取每日体力、活跃度等数据"""
        # 注意：Java 源码中参数是在 URL 上的，Body 为空
        url = f"{self.base_url}/gamer/widget/game3/getData"
        params = {
            "type": "2",
            "roleId": role_id,
            "gameId": self.game_id,
            "serverId": self.server_id,
            "sizeType": "1"
        }
        headers = self._get_headers(token, b_at, did=did)
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            # 使用 post 但 body 为空，params 拼接到 URL
            resp = await client.post(url, headers=headers, params=params)
            return resp.json()

    async def get_base_data(self, role_id: str, token: str, b_at: str, did: str):
        """获取基础探索数据 (宝箱、探索度)"""
        url = f"{self.base_url}/aki/roleBox/akiBox/baseData"
        # Java 源码中使用的是 multipart/form-data
        files = {
            "serverId": (None, self.server_id),
            "roleId": (None, role_id),
            "gameId": (None, self.game_id)
        }
        headers = self._get_headers(token, b_at, did=did)
        # 移除 Content-Type，让 httpx 自动生成带 boundary 的 multipart/form-data
        if "Content-Type" in headers:
            del headers["Content-Type"]
            
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, headers=headers, files=files)
            return resp.json()

def print_section(title):
    print(f"\n{'='*10} {title} {'='*10}")

async def main():
    try:
        tool = GameDataTool()
        accounts = tool.config.get("accounts", [])
        
        if not accounts:
            print("配置文件中没有账号信息，请先运行 kuro_login.py 登录。")
            return

        for acc_index, account in enumerate(accounts):
            token = account["token"]
            roles = account.get("roles", [])
            did = account.get("did", "")
            
            if not roles:
                continue

            for role in roles:
                role_id = role["roleId"]
                user_id = role["userId"]
                role_name = role["roleName"]

                print_section(f"账号 {acc_index + 1}: {role_name} (ID: {role_id})")
                
                try:
                    # 1. 获取 B-At
                    b_at = await tool.get_b_at_token(role_id, user_id, token, did)
                    
                    # 2. 获取数据
                    daily_task = tool.get_daily_data(role_id, token, b_at, did)
                    base_task = tool.get_base_data(role_id, token, b_at, did)
                    
                    daily_resp, base_resp = await asyncio.gather(daily_task, base_task)

                    # 3. 解析并显示每日数据
                    if daily_resp.get("code") == 200:
                        daily_data = daily_resp.get("data", {})
                        print_section("每日实时数据 (原始数据解析)")
                        
                        # 遍历所有 DailyDetail 数据
                        for key in ["energyData", "livenessData", "storeEnergyData", "towerData", "weeklyData"]:
                            detail = daily_data.get(key)
                            if detail:
                                print(f"[{detail.get('name')}]: {detail.get('cur', detail.get('value'))} / {detail.get('total')}")
                        
                        # 特殊处理 battlePassData (列表)
                        bp_list = daily_data.get("battlePassData", [])
                        for bp in bp_list:
                            print(f"[{bp.get('name')}]: {bp.get('value')}")
                    else:
                        print(f"获取每日数据失败: {daily_resp.get('msg')}")

                    # 4. 解析并显示基础数据
                    if base_resp.get("code") == 200:
                        print_section("基础探索数据 (原始数据解析)")
                        data_raw = base_resp.get("data")
                        base_data = {}
                        if isinstance(data_raw, str):
                            try:
                                base_data = json.loads(data_raw)
                            except:
                                print(f"警告: 无法解析 data 字符串: {data_raw[:100]}...")
                        elif isinstance(data_raw, dict):
                            base_data = data_raw
                        
                        if base_data:
                            for k, v in base_data.items():
                                if not isinstance(v, (list, dict)):
                                    print(f"{k}: {v}")
                            
                            if "boxList" in base_data:
                                print("\n[宝箱统计]:")
                                for box in base_data["boxList"]:
                                    print(f"  - {box.get('boxName') or box.get('name')}: {box.get('num')}")
                            
                            if "explorationList" in base_data:
                                print("\n[区域探索]:")
                                for area in base_data["explorationList"]:
                                    print(f"  - {area.get('countryName')}: {area.get('explorationPercentage', 0)/10}%")
                        else:
                            print(f"基础数据内容为空，原始响应: {base_resp}")
                    else:
                        print(f"获取基础数据失败: {base_resp.get('msg')}")

                except Exception as e:
                    print(f"获取角色 {role_name} 数据时发生错误: {e}")

    except Exception as e:
        print(f"程序运行发生错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())
