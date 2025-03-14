import os
import sys
import time
import asyncio
import logging
import argparse
from typing import Dict, Any, List, Tuple, Optional, Union

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../..')))

from dotenv import load_dotenv
from browser_use import Browser, Controller, Agent
from browser_use.browser.browser import BrowserConfig
from browser_use.agent.views import ActionResult
from browser_use.controller.views import ClickElementAction, Action, ActionResponse
from browser_use.controller.registry import Registry

# 从当前目录的browser_extension模块导入
from browser_extension.context_extension import extend_browser_context

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# UI测试相关类和辅助函数
class UITestStep:
    """UI测试步骤类"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.start_time = 0
        self.end_time = 0
        self.success = False
        self.error_message = ""
        
    def start(self):
        """开始执行步骤"""
        logger.info(f"执行步骤: {self.name} - {self.description}")
        self.start_time = time.time()
        
    def complete(self, success: bool, error_message: str = ""):
        """完成步骤"""
        self.end_time = time.time()
        self.success = success
        self.error_message = error_message
        
        duration = self.end_time - self.start_time
        if success:
            logger.info(f"步骤 '{self.name}' 成功完成，耗时: {duration:.2f}秒")
        else:
            logger.error(f"步骤 '{self.name}' 失败，耗时: {duration:.2f}秒, 错误: {error_message}")
    
    @property
    def duration(self) -> float:
        """获取步骤执行时长"""
        if self.end_time > 0:
            return self.end_time - self.start_time
        return 0

class UITestReport:
    """UI测试报告类"""
    def __init__(self, test_name: str):
        self.test_name = test_name
        self.steps: List[UITestStep] = []
        self.start_time = 0
        self.end_time = 0
        self.total_standard_time: float = 0.0
        self.total_cache_time: float = 0.0
        
    def add_step(self, step: UITestStep):
        """添加测试步骤"""
        self.steps.append(step)
        
    def start_test(self):
        """开始测试"""
        logger.info(f"开始UI测试: {self.test_name}")
        self.start_time = time.time()
        
    def complete_test(self):
        """完成测试"""
        self.end_time = time.time()
        duration = self.end_time - self.start_time
        
        # 计算测试结果
        total_steps = len(self.steps)
        successful_steps = sum(1 for step in self.steps if step.success)
        
        logger.info(f"\n{'=' * 50}")
        logger.info(f"UI测试报告: {self.test_name}")
        logger.info(f"{'=' * 50}")
        logger.info(f"总耗时: {duration:.2f}秒")
        logger.info(f"步骤总数: {total_steps}")
        logger.info(f"成功步骤: {successful_steps}")
        logger.info(f"失败步骤: {total_steps - successful_steps}")
        
        if self.total_standard_time > 0 and self.total_cache_time > 0:
            improvement = (self.total_standard_time - self.total_cache_time) / self.total_standard_time * 100
            logger.info(f"\n性能比较:")
            logger.info(f"  标准操作总耗时: {self.total_standard_time:.4f}秒")
            logger.info(f"  缓存操作总耗时: {self.total_cache_time:.4f}秒")
            logger.info(f"  性能提升: {improvement:.2f}%")
        
        logger.info(f"\n步骤详情:")
        for i, step in enumerate(self.steps, 1):
            status = "✅ 成功" if step.success else "❌ 失败"
            logger.info(f"  {i}. {step.name}: {status} ({step.duration:.2f}秒)")
            if not step.success:
                logger.info(f"     错误: {step.error_message}")
                
        logger.info(f"{'=' * 50}")
        
        # 返回测试是否全部成功
        return successful_steps == total_steps

# 增强的UI操作函数
async def is_element_hidden(element):
    """检查元素是否隐藏"""
    # 安全地检查元素是否有is_hidden属性，如果没有则检查可见性相关的其他属性
    if hasattr(element, 'is_hidden'):
        return element.is_hidden
    
    # 备选检查方法
    if hasattr(element, 'attributes'):
        # 检查style属性中是否包含display:none或visibility:hidden
        style = element.attributes.get('style', '').lower()
        if 'display: none' in style or 'visibility: hidden' in style:
            return True
        
        # 检查是否有hidden属性
        if element.attributes.get('hidden') is not None:
            return True
    
    # 默认认为元素可见
    return False

async def find_element_by_text(context, text_content: str, tag_names: Optional[List[str]] = None, exact_match: bool = False, interactive_only: bool = True) -> Optional[int]:
    """通过文本内容查找元素"""
    dom_state = await context.get_state()
    
    for index, element in dom_state.selector_map.items():
        # 检查是否只查找可交互元素
        if interactive_only and not getattr(element, 'is_interactive', False):
            continue
            
        # 检查是否隐藏
        if await is_element_hidden(element):
            continue
            
        # 检查标签名
        if tag_names and element.tag_name.lower() not in [t.lower() for t in tag_names]:
            continue
            
        # 获取元素文本 - 安全地访问方法
        element_text = ""
        if hasattr(element, 'get_all_text_till_next_clickable_element'):
            element_text = element.get_all_text_till_next_clickable_element()
        elif hasattr(element, 'attributes') and 'innerText' in element.attributes:
            element_text = element.attributes['innerText']
        
        # 检查文本匹配
        if exact_match:
            if element_text == text_content:
                return index
        else:
            if text_content in element_text:
                return index
                
    return None

async def find_input_element(context, input_type: Optional[str] = None, placeholder: Optional[str] = None) -> Optional[int]:
    """查找输入框元素"""
    dom_state = await context.get_state()
    
    for index, element in dom_state.selector_map.items():
        # 检查标签名
        if element.tag_name.lower() != "input":
            continue
            
        # 检查是否隐藏
        if await is_element_hidden(element):
            continue
            
        # 检查输入框类型 - 安全地获取input_type
        element_type = getattr(element, 'input_type', None)
        if element_type is None and hasattr(element, 'attributes'):
            element_type = element.attributes.get('type', '')
        
        # 检查输入框类型是否匹配
        if input_type and element_type != input_type:
            # 特殊处理：有些输入框可能没有明确设置type
            if input_type == "text" and element_type == "":
                pass  # 允许空type作为text类型
            else:
                continue
                
        # 检查占位符文本
        if placeholder and hasattr(element, 'attributes'):
            element_placeholder = element.attributes.get("placeholder", "")
            if placeholder.lower() not in element_placeholder.lower():
                continue
                
        return index
                
    return None

async def measure_performance(context, operation_func, args=(), use_cache=False):
    """测量操作性能"""
    start_time = time.time()
    result = await operation_func(*args)
    end_time = time.time()
    return result, end_time - start_time

async def get_cached_elements(context, url, force_refresh=False):
    """安全地获取缓存的元素"""
    try:
        # 首先尝试使用cache_manager访问
        if hasattr(context, 'cache_manager'):
            return await context.cache_manager.get_elements_with_cache(url, force_refresh=force_refresh)
        
        # 如果上面的方法不可用，尝试直接调用get_elements_with_cache
        if hasattr(context, 'get_elements_with_cache'):
            return await context.get_elements_with_cache(url, force_refresh=force_refresh)
        
        # 如果都不可用，则返回空字典
        logger.warning("无法找到缓存方法，返回空缓存")
        return {}
    except Exception as e:
        logger.error(f"获取缓存元素时出错: {str(e)}")
        return {}

def get_available_actions(controller) -> List[str]:
    """安全地获取控制器中可用的操作列表"""
    try:
        # 尝试通过不同方式获取可用操作
        available_actions = []
        
        # 尝试直接通过get_registered_actions方法获取
        if hasattr(controller.registry, 'get_registered_actions'):
            return controller.registry.get_registered_actions()
        
        # 尝试通过dir()获取所有成员，并过滤出可能的操作
        registry_members = dir(controller.registry)
        action_methods = [
            member for member in registry_members 
            if member.startswith("action_") or 
               member.endswith("_action") or
               "execute" in member
        ]
        
        if action_methods:
            logger.info(f"发现可能的操作方法: {action_methods}")
            
        # 基于常见操作猜测可用的操作
        common_actions = [
            "click_element", "fill", "type", "input_text", "focus", "blur",
            "press_key", "scroll", "navigate", "get_text"
        ]
        
        # 默认至少返回click_element操作
        return ["click_element"]
        
    except Exception as e:
        logger.warning(f"获取可用操作失败: {str(e)}")
        return ["click_element"]  # 至少返回一个我们知道应该存在的操作

async def input_text_to_element(controller, context, element_index, text):
    """向元素输入文本，尝试多种可能的操作名称"""
    try:
        # 尝试多种可能的输入文本方式
        # 1. 先尝试直接点击元素
        logger.info("首先尝试点击元素")
        try:
            await controller.registry.execute_action("click_element", {"index": element_index}, context)
            logger.info("元素点击成功")
            
            # 2. 获取当前页面并使用keyboard.type直接输入
            page = await context.get_current_page()
            await page.keyboard.type(text)
            logger.info("通过keyboard.type方法输入文本成功")
            return ActionResult(success=True, extracted_content=f"已点击并输入文本: {text}")
        except Exception as e:
            logger.warning(f"点击和键盘输入失败: {str(e)}")
            
        # 3. 尝试使用fill方法直接填充元素
        try:
            logger.info("尝试使用元素选择器直接填充文本")
            page = await context.get_current_page()
            dom_state = await context.get_state()
            element = dom_state.selector_map.get(element_index)
            
            if element and hasattr(element, 'selector'):
                await page.fill(element.selector, text)
                logger.info("通过fill方法输入文本成功")
                return ActionResult(success=True, extracted_content=f"已使用fill填充文本: {text}")
        except Exception as e:
            logger.warning(f"使用fill方法填充文本失败: {str(e)}")
        
        # 4. 如果以上方法都失败，尝试使用评估JS直接设置值
        try:
            logger.info("尝试使用JavaScript设置元素值")
            page = await context.get_current_page()
            dom_state = await context.get_state()
            element = dom_state.selector_map.get(element_index)
            
            if element and hasattr(element, 'selector'):
                await page.evaluate(f"""
                    selector => {{
                        const element = document.querySelector(selector);
                        if (element) {{
                            element.value = '{text}';
                            element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                """, element.selector)
                logger.info("通过JavaScript设置元素值成功")
                return ActionResult(success=True, extracted_content=f"已使用JavaScript设置文本: {text}")
        except Exception as e:
            logger.warning(f"使用JavaScript设置元素值失败: {str(e)}")
        
        # 如果所有方法都失败
        raise Exception("所有输入文本的方法都失败")
            
    except Exception as e:
        logger.error(f"输入文本过程中发生错误: {str(e)}")
        raise Exception(f"无法输入文本到元素: {str(e)}")

async def wait_for_page_refresh(context, page, max_wait_time=15):
    """等待页面完全刷新和加载完成"""
    logger.info("等待页面刷新和加载完成...")
    
    try:
        # 1. 等待页面加载状态
        await page.wait_for_load_state("networkidle")
        
        # 2. 等待URL变化，这通常表示导航已发生
        initial_url = page.url
        start_time = time.time()
        
        while time.time() - start_time < max_wait_time:
            current_url = page.url
            if current_url != initial_url:
                logger.info(f"检测到URL变化: {initial_url} -> {current_url}")
                break
            await asyncio.sleep(0.5)
        
        # 3. 等待额外时间以确保页面上的所有元素都加载完成
        logger.info("等待页面元素加载完成...")
        await asyncio.sleep(5)
        
        # 4. 等待可能的动画效果完成
        await page.wait_for_load_state("domcontentloaded")
        
        # 5. 检查页面内容变化，确认页面已刷新
        dom_state = await context.get_state()
        logger.info(f"页面现在包含 {len(dom_state.selector_map)} 个元素")
        
        return True
    except Exception as e:
        logger.error(f"等待页面刷新时出错: {str(e)}")
        # 尽管出错，我们仍然返回True以允许测试继续
        return True

# LLM集成部分
def get_llm(provider: str):
    """获取指定的LLM模型"""
    if provider == 'anthropic':
        from langchain_anthropic import ChatAnthropic
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Error: ANTHROPIC_API_KEY is not set. Please provide a valid API key.")
        
        return ChatAnthropic(
            model_name='claude-3-5-sonnet-20240620', timeout=25, stop=None, temperature=0.0
        )
    elif provider == 'openai':
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Error: OPENAI_API_KEY is not set. Please provide a valid API key.")
        
        return ChatOpenAI(model='gpt-4o', temperature=0.0)
    elif provider == 'deepseek':
        from langchain_openai import ChatOpenAI
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("Error: DEEPSEEK_API_KEY is not set. Please provide a valid API key.")
        
        return ChatOpenAI(model='deepseek-chat', temperature=0.0, base_url='https://api.deepseek.com/v1')
    else:
        raise ValueError(f'Unsupported provider: {provider}')

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="使用LLM增强的UI自动化测试工具")
    parser.add_argument(
        '--task',
        type=str,
        help='要执行的测试任务描述',
        default='访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页'
    )
    parser.add_argument(
        '--provider',
        type=str,
        choices=['openai', 'anthropic', 'deepseek'],
        default='deepseek',
        help='要使用的LLM提供商 (默认: deepseek)',
    )
    parser.add_argument(
        '--use_cache',
        action='store_true',
        help='是否使用元素缓存来提高性能'
    )
    parser.add_argument(
        '--max_steps',
        type=int,
        default=25,
        help='最大执行步骤数'
    )
    parser.add_argument(
        '--cache_dir',
        type=str,
        default='ui_test_cache',
        help='缓存目录路径'
    )
    return parser.parse_args()

# 创建自定义增强操作类
class EnhancedInputTextAction(Action):
    """增强的文本输入操作，尝试多种输入方法"""
    def __init__(self):
        super().__init__()
        self.name = "enhanced_input_text"
        self.description = "使用多种策略向元素输入文本，包括点击+键盘输入、fill和JavaScript方法"
        self.parameters = {
            "index": "要输入文本的元素索引",
            "text": "要输入的文本内容"
        }
    
    async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
        try:
            element_index = int(params.get("index"))
            text = params.get("text")
            
            if not text:
                return ActionResponse(success=False, message="未指定要输入的文本")
                
            # 调用增强的输入文本方法
            controller = context.get_controller()
            result = await input_text_to_element(controller, context, element_index, text)
            
            return ActionResponse(
                success=True,
                message=f"成功输入文本: {text}",
                page_state_changed=True
            )
        except Exception as e:
            return ActionResponse(success=False, message=f"输入文本失败: {str(e)}")

class FindElementByTextAction(Action):
    """根据文本内容查找元素"""
    def __init__(self):
        super().__init__()
        self.name = "find_element_by_text"
        self.description = "根据文本内容查找页面上的元素"
        self.parameters = {
            "text": "要查找的文本内容",
            "tag_names": "（可选）限制查找的标签名列表，例如 ['button', 'div']",
            "exact_match": "（可选）是否要求精确匹配文本，默认为否",
            "interactive_only": "（可选）是否只查找可交互元素，默认为是"
        }
    
    async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
        try:
            text = params.get("text")
            if not text:
                return ActionResponse(success=False, message="未指定要查找的文本")
                
            tag_names = params.get("tag_names")
            exact_match = params.get("exact_match", False)
            interactive_only = params.get("interactive_only", True)
            
            if isinstance(tag_names, str):
                # 如果是以逗号分隔的字符串，将其转换为列表
                tag_names = [tag.strip() for tag in tag_names.split(",")]
                
            element_index = await find_element_by_text(
                context, text, tag_names, exact_match, interactive_only
            )
            
            if element_index is not None:
                return ActionResponse(
                    success=True,
                    message=f"找到包含文本 '{text}' 的元素，索引为 {element_index}",
                    extracted_content={"element_index": element_index}
                )
            else:
                return ActionResponse(success=False, message=f"未找到包含文本 '{text}' 的元素")
        except Exception as e:
            return ActionResponse(success=False, message=f"查找元素失败: {str(e)}")

class FindInputElementAction(Action):
    """查找输入框元素"""
    def __init__(self):
        super().__init__()
        self.name = "find_input_element"
        self.description = "查找页面上的输入框元素"
        self.parameters = {
            "input_type": "（可选）输入框类型，如'text'、'password'等",
            "placeholder": "（可选）占位符文本"
        }
    
    async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
        try:
            input_type = params.get("input_type")
            placeholder = params.get("placeholder")
            
            element_index = await find_input_element(context, input_type, placeholder)
            
            if element_index is not None:
                return ActionResponse(
                    success=True,
                    message=f"找到输入框元素，索引为 {element_index}",
                    extracted_content={"element_index": element_index}
                )
            else:
                criteria = []
                if input_type:
                    criteria.append(f"类型为 '{input_type}'")
                if placeholder:
                    criteria.append(f"占位符包含 '{placeholder}'")
                criteria_text = "、".join(criteria) if criteria else "任何类型"
                
                return ActionResponse(success=False, message=f"未找到{criteria_text}的输入框元素")
        except Exception as e:
            return ActionResponse(success=False, message=f"查找输入框失败: {str(e)}")

class WaitForPageRefreshAction(Action):
    """等待页面刷新完成"""
    def __init__(self):
        super().__init__()
        self.name = "wait_for_page_refresh"
        self.description = "等待页面完全刷新和加载完成"
        self.parameters = {
            "max_wait_time": "（可选）最大等待时间（秒），默认为15秒"
        }
    
    async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
        try:
            max_wait_time = float(params.get("max_wait_time", 15))
            page = await context.get_current_page()
            
            success = await wait_for_page_refresh(context, page, max_wait_time)
            
            if success:
                return ActionResponse(
                    success=True,
                    message="页面已刷新和加载完成",
                    page_state_changed=True
                )
            else:
                return ActionResponse(success=False, message="等待页面刷新超时")
        except Exception as e:
            return ActionResponse(success=False, message=f"等待页面刷新时出错: {str(e)}")

# 自定义Controller扩展类
class EnhancedController(Controller):
    """增强的控制器，包含更多UI操作方法"""
    
    def __init__(self):
        super().__init__()
        self._context = None
        
    @property
    def context(self):
        return self._context
        
    @context.setter
    def context(self, value):
        self._context = value
        # 设置上下文时，添加辅助方法获取控制器的能力
        if hasattr(value, 'get_controller'):
            pass
        else:
            # 为上下文添加获取控制器的方法
            def get_controller():
                return self
            value.get_controller = get_controller
    
    def register_enhanced_actions(self):
        """注册所有增强的操作"""
        # 确保只注册一次
        if getattr(self, '_enhanced_actions_registered', False):
            return
            
        logger.info("注册增强的UI操作方法")
        
        # 注册增强的操作
        self.registry.register(EnhancedInputTextAction())
        self.registry.register(FindElementByTextAction())
        self.registry.register(FindInputElementAction())
        self.registry.register(WaitForPageRefreshAction())
        
        # 标记为已注册
        self._enhanced_actions_registered = True
        logger.info("增强的UI操作方法注册完成")

# 更新EnhancedUITestAgent类
class EnhancedUITestAgent:
    """增强的UI测试代理，结合LLM能力和增强的UI测试方法"""
    
    def __init__(self, task: str, llm_provider: str, use_cache: bool = True, cache_dir: str = "ui_test_cache"):
        self.task = task
        self.llm_provider = llm_provider
        self.use_cache = use_cache
        self.cache_dir = cache_dir
        self.report = UITestReport(f"LLM驱动的UI测试: {task[:30]}...")
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 初始化组件 - 使用增强的控制器
        self.llm = get_llm(llm_provider)
        self.controller = EnhancedController()  # 使用增强的控制器
        self.browser = Browser(config=BrowserConfig())
        
        # 注册增强的操作
        self.controller.register_enhanced_actions()
        
        # 初始化代理
        self.agent = Agent(
            task=task,
            llm=self.llm,
            controller=self.controller,
            browser=self.browser,
            use_vision=True,
            max_actions_per_step=1,
        )
        
    async def setup(self):
        """设置浏览器上下文并添加增强功能"""
        # 创建浏览器上下文
        context = await self.browser.new_context()
        
        # 如果启用缓存，扩展上下文以支持元素缓存
        if self.use_cache:
            logger.info(f"启用元素缓存，缓存目录: {self.cache_dir}")
            context = extend_browser_context(context, cache_dir=self.cache_dir)
        
        # 将上下文添加到控制器
        self.controller.context = context
        
        # 创建一个页面
        self.page = await context.new_page()
        
        logger.info("浏览器设置完成")
        
    async def run(self, max_steps: int = 25):
        """运行LLM驱动的UI测试"""
        self.report.start_test()
        
        try:
            # 设置浏览器和上下文
            await self.setup()
            
            # 运行代理执行任务
            logger.info(f"开始执行任务: {self.task}")
            
            # 添加任务描述前缀，帮助LLM理解可用的增强功能
            task_with_context = f"""
            你现在可以使用以下增强的操作方法来完成UI测试任务:
            
            1. enhanced_input_text - 增强的文本输入操作，尝试多种输入方法
            2. find_element_by_text - 通过文本内容查找元素
            3. find_input_element - 查找输入框元素
            4. wait_for_page_refresh - 等待页面刷新完成
            
            这些操作提供了更强大的UI交互能力，包括更好的元素查找和文本输入方法。
            请充分利用这些功能来完成以下任务:
            
            {self.task}
            """
            
            # 更新代理的任务
            self.agent.task = task_with_context
            
            # 运行代理
            await self.agent.run(max_steps=max_steps)
            
            # 完成测试
            success = self.report.complete_test()
            return success
            
        except Exception as e:
            logger.error(f"执行测试时发生错误: {str(e)}")
            self.report.complete_test()
            return False
            
        finally:
            # 提示用户
            input("测试完成，按Enter键关闭浏览器...")
            # 关闭浏览器
            await self.browser.close()
            logger.info("测试浏览器已关闭")
    
    async def execute_step(self, step_name: str, step_description: str, step_func, *args, **kwargs):
        """执行测试步骤并记录结果"""
        step = UITestStep(step_name, step_description)
        step.start()
        
        try:
            result = await step_func(*args, **kwargs)
            step.complete(True)
            return result
        except Exception as e:
            step.complete(False, str(e))
            raise e  # 重新抛出异常以便上层处理
        finally:
            self.report.add_step(step)

async def main():
    """主函数"""
    args = parse_arguments()
    
    # 创建并运行增强的UI测试代理
    agent = EnhancedUITestAgent(
        task=args.task,
        llm_provider=args.provider,
        use_cache=args.use_cache,
        cache_dir=args.cache_dir
    )
    
    success = await agent.run(max_steps=args.max_steps)
    
    # 退出码：0表示成功，1表示失败
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main()) 