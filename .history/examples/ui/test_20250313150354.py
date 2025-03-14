from langchain_openai import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
import os
load_dotenv()

import asyncio

api_key = os.getenv('DEEPSEEK_API_KEY')
base_url = os.getenv('Base_URL')
model = os.getenv('MODEL')

llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)

async def main():
    agent = Agent(
        task='访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页',
        llm=llm,
        use_vision=False,
    )
    result = await agent.run()
    print(result)

asyncio.run(main())