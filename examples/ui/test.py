from langchain_openai import ChatOpenAI
from browser_use import Agent
from dotenv import load_dotenv
import os
load_dotenv()

import asyncio

from browser_use import Agent, Controller
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContext

api_key = os.getenv('QIANWEN_API_KEY')
base_url = os.getenv('QIANWEN_BASE_URL')
model = os.getenv('QIANWEN_MODEL')

llm = ChatOpenAI(model=model, api_key=api_key, base_url=base_url)


# browser = Browser(
# 	config=BrowserConfig(
# 		# NOTE: you need to close your chrome browser - so that this can open your browser in debug mode
# 		chrome_instance_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
# 	)
# )

async def main():
    agent = Agent(
        task='访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页',
        llm=llm,
         use_vision=False,
        # browser=browser,
    )
    result = await agent.run()
    print(result)

asyncio.run(main())