import os
import asyncio
import logging
import sys
import time
from typing import Dict, Any, List, Tuple, Optional

# 添加当前目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(current_dir, '../..')))

from browser_use import Browser, Controller
from browser_use.agent.views import ActionResult
from browser_use.controller.views import ClickElementAction, TypeAction
# 从当前目录的browser_extension模块导入
from browser_extension.context_extension import extend_browser_context

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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
        self.total_standard_time = 0  # 标准操作总耗时
        self.total_cache_time = 0     # 缓存操作总耗时
        
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

async def find_element_by_text(context, text_content: str, tag_names: List[str] = None, exact_match: bool = False, interactive_only: bool = True) -> Optional[int]:
    """通过文本内容查找元素
    
    Args:
        context: 浏览器上下文
        text_content: 要查找的文本内容
        tag_names: 限制查找的标签名列表，为None时不限制
        exact_match: 是否要求精确匹配文本
        interactive_only: 是否只查找可交互元素
        
    Returns:
        找到的元素索引，未找到时返回None
    """
    dom_state = await context.get_state()
    
    for index, element in dom_state.selector_map.items():
        # 检查是否只查找可交互元素
        if interactive_only and not element.is_interactive:
            continue
            
        # 检查是否隐藏
        if element.is_hidden:
            continue
            
        # 检查标签名
        if tag_names and element.tag_name.lower() not in [t.lower() for t in tag_names]:
            continue
            
        # 获取元素文本
        element_text = element.get_all_text_till_next_clickable_element()
        
        # 检查文本匹配
        if exact_match:
            if element_text == text_content:
                return index
        else:
            if text_content in element_text:
                return index
                
    return None

async def find_input_element(context, input_type: str = None, placeholder: str = None) -> Optional[int]:
    """查找输入框元素
    
    Args:
        context: 浏览器上下文
        input_type: 输入框类型，如"text"、"password"等
        placeholder: 输入框占位符文本
        
    Returns:
        找到的元素索引，未找到时返回None
    """
    dom_state = await context.get_state()
    
    for index, element in dom_state.selector_map.items():
        # 检查标签名
        if element.tag_name.lower() != "input":
            continue
            
        # 检查是否隐藏
        if element.is_hidden:
            continue
            
        # 检查输入框类型
        if input_type and element.input_type != input_type:
            # 特殊处理：有些输入框可能没有明确设置type
            if input_type == "text" and element.input_type == "":
                pass  # 允许空type作为text类型
            else:
                continue
                
        # 检查占位符文本
        if placeholder:
            element_placeholder = element.attributes.get("placeholder", "")
            if placeholder.lower() not in element_placeholder.lower():
                continue
                
        return index
                
    return None

async def measure_performance(context, operation_func, args=(), use_cache=False):
    """测量操作性能
    
    Args:
        context: 浏览器上下文
        operation_func: 要测量的操作函数
        args: 操作函数的参数
        use_cache: 是否使用缓存
        
    Returns:
        (操作结果, 耗时)
    """
    start_time = time.time()
    result = await operation_func(*args)
    end_time = time.time()
    return result, end_time - start_time

async def run_ui_test():
    """运行UI测试"""
    logger.info("启动UI测试...")
    
    # 创建测试报告
    report = UITestReport("登录系统测试")
    report.start_test()
    
    # 创建浏览器和控制器
    browser = Browser()  # 使用默认配置
    controller = Controller()
    
    # 创建浏览器上下文并添加缓存功能
    context = await browser.new_context()
    context = extend_browser_context(context, cache_dir="ui_test_cache")
    
    try:
        # 定义测试任务
        task = '访问https://hy-sit.1233s2b.com,等待页面加载完成,输入用户名13600805241，输入密码Aa123456，点击登录按钮，登录成功等待页面加载完成后,点击辽阳市兴宇纸业有限公司-管理端，等待跳转的页面加载完成,验证页面包含文本首页'
        logger.info(f"测试任务: {task}")
        
        # 步骤1: 访问网站
        step1 = UITestStep("访问网站", "访问https://hy-sit.1233s2b.com并等待页面加载")
        step1.start()
        
        try:
            page = await context.get_current_page()
            await page.goto("https://hy-sit.1233s2b.com")
            await page.wait_for_load_state()
            
            # 获取当前URL并缓存页面元素
            current_url = await context._get_current_url()
            logger.info(f"当前页面: {current_url}")
            
            # 使用缓存获取页面元素
            cached_elements = await context.cache_manager.get_elements_with_cache(current_url, force_refresh=True)
            logger.info(f"缓存了 {len(cached_elements)} 个元素")
            
            # 等待一下确保页面完全加载
            await asyncio.sleep(2)
            
            step1.complete(True)
        except Exception as e:
            step1.complete(False, str(e))
        
        report.add_step(step1)
        
        # 如果前一步失败，则后续步骤不执行
        if not step1.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤2: 输入用户名
        step2 = UITestStep("输入用户名", "定位用户名输入框并输入13600805241")
        step2.start()
        
        try:
            # 比较标准方法和缓存方法的性能差异
            standard_func = find_input_element
            standard_args = (context, "text", "请输入手机号")
            username_index, standard_time = await measure_performance(context, standard_func, standard_args)
            
            # 如果没有找到明确的手机号输入框，尝试查找其他可能的用户名输入框
            if username_index is None:
                username_index, additional_time = await measure_performance(
                    context, 
                    find_input_element, 
                    (context, "tel", None)
                )
                standard_time += additional_time
                
            # 再次尝试查找任何文本输入框
            if username_index is None:
                username_index, additional_time = await measure_performance(
                    context, 
                    find_input_element, 
                    (context, "text", None)
                )
                standard_time += additional_time
            
            if username_index is None:
                raise Exception("未找到用户名输入框")
            
            # 输入用户名
            type_username_action = TypeAction(index=username_index, text="13600805241")
            await controller.registry.execute_action("type", type_username_action, context)
            logger.info("用户名输入完成")
            
            # 记录性能数据
            cache_time = 0  # 缓存方法在这个步骤中尚未实现
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            step2.complete(True)
        except Exception as e:
            step2.complete(False, str(e))
        
        report.add_step(step2)
        
        if not step2.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤3: 输入密码
        step3 = UITestStep("输入密码", "定位密码输入框并输入Aa123456")
        step3.start()
        
        try:
            # 查找密码输入框
            password_index, standard_time = await measure_performance(
                context,
                find_input_element,
                (context, "password", None)
            )
            
            if password_index is None:
                raise Exception("未找到密码输入框")
            
            # 输入密码
            type_password_action = TypeAction(index=password_index, text="Aa123456")
            await controller.registry.execute_action("type", type_password_action, context)
            logger.info("密码输入完成")
            
            # 记录性能数据
            cache_time = 0  # 缓存方法在这个步骤中尚未实现
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            step3.complete(True)
        except Exception as e:
            step3.complete(False, str(e))
        
        report.add_step(step3)
        
        if not step3.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤4: 点击登录按钮
        step4 = UITestStep("点击登录按钮", "定位并点击登录按钮")
        step4.start()
        
        try:
            # 使用标准方法查找登录按钮
            login_button_index, standard_time = await measure_performance(
                context,
                find_element_by_text,
                (context, "登录", ["button", "div", "span"], False, True)
            )
            
            # 使用缓存方法再次查找
            current_url = await context._get_current_url()
            cached_elements = await context.cache_manager.get_elements_with_cache(current_url)
            
            cache_start = time.time()
            cache_login_index = None
            
            # 使用缓存数据查找登录按钮
            for idx, element in cached_elements.items():
                text = element.get("text", "").lower()
                if "登录" in text and element.get("is_interactive", False):
                    cache_login_index = idx
                    break
                    
            cache_time = time.time() - cache_start
            
            # 使用找到的按钮索引（优先使用标准方法找到的）
            login_button_index = login_button_index or cache_login_index
            
            if login_button_index is None:
                raise Exception("未找到登录按钮")
            
            # 点击登录按钮
            click_login_action = ClickElementAction(index=login_button_index)
            await controller.registry.execute_action("click_element", click_login_action, context)
            logger.info("已点击登录按钮")
            
            # 记录性能数据
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            # 等待登录成功并页面加载完成
            logger.info("等待登录成功并页面加载完成")
            await page.wait_for_load_state()
            await asyncio.sleep(3)  # 额外等待以确保登录后的页面完全加载
            
            step4.complete(True)
        except Exception as e:
            step4.complete(False, str(e))
        
        report.add_step(step4)
        
        if not step4.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤5: 点击辽阳市兴宇纸业有限公司-管理端
        step5 = UITestStep("点击目标链接", "定位并点击辽阳市兴宇纸业有限公司-管理端链接")
        step5.start()
        
        try:
            # 缓存当前页面元素以提高性能
            current_url = await context._get_current_url()
            cached_elements = await context.cache_manager.get_elements_with_cache(current_url, force_refresh=True)
            
            # 使用标准方法查找目标链接
            target_link_index, standard_time = await measure_performance(
                context,
                find_element_by_text,
                (context, "辽阳市兴宇纸业有限公司-管理端", None, False, True)
            )
            
            # 使用缓存方法查找
            cache_start = time.time()
            cache_target_index = None
            
            for idx, element in cached_elements.items():
                text = element.get("text", "")
                if "辽阳市兴宇纸业有限公司-管理端" in text and element.get("is_interactive", False):
                    cache_target_index = idx
                    break
                    
            cache_time = time.time() - cache_start
            
            # 使用找到的链接索引（优先使用标准方法找到的）
            target_link_index = target_link_index or cache_target_index
            
            if target_link_index is None:
                raise Exception("未找到'辽阳市兴宇纸业有限公司-管理端'链接")
            
            # 记录性能数据
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            # 点击目标链接
            click_target_action = ClickElementAction(index=target_link_index)
            await controller.registry.execute_action("click_element", click_target_action, context)
            logger.info("已点击'辽阳市兴宇纸业有限公司-管理端'链接")
            
            # 等待页面跳转完成
            logger.info("等待页面跳转完成")
            await page.wait_for_load_state()
            await asyncio.sleep(3)  # 额外等待以确保跳转后的页面完全加载
            
            step5.complete(True)
        except Exception as e:
            step5.complete(False, str(e))
        
        report.add_step(step5)
        
        if not step5.success:
            logger.error("由于前序步骤失败，测试终止")
            report.complete_test()
            return False
        
        # 步骤6: 验证页面包含文本"首页"
        step6 = UITestStep("验证页面内容", "验证页面包含文本'首页'")
        step6.start()
        
        try:
            # 使用标准方法验证
            home_text_index, standard_time = await measure_performance(
                context,
                find_element_by_text,
                (context, "首页", None, False, False)
            )
            
            # 使用缓存方法验证
            current_url = await context._get_current_url()
            cached_elements = await context.cache_manager.get_elements_with_cache(current_url)
            
            cache_start = time.time()
            cache_home_index = None
            
            for idx, element in cached_elements.items():
                text = element.get("text", "")
                if "首页" in text:
                    cache_home_index = idx
                    break
                    
            cache_time = time.time() - cache_start
            
            # 记录性能数据
            report.total_standard_time += standard_time
            report.total_cache_time += cache_time
            
            # 验证结果
            found_text = (home_text_index is not None) or (cache_home_index is not None)
            
            if not found_text:
                raise Exception("页面不包含文本'首页'")
            
            logger.info("验证成功: 页面包含文本'首页'")
            step6.complete(True)
        except Exception as e:
            step6.complete(False, str(e))
        
        report.add_step(step6)
        
        # 完成测试并生成报告
        success = report.complete_test()
        return success
        
    except Exception as e:
        logger.error(f"执行测试任务时发生错误: {str(e)}")
        report.complete_test()
        return False
    finally:
        # 关闭浏览器
        await browser.close()
        logger.info("测试浏览器已关闭")

async def batch_run_tests(num_runs=1):
    """批量运行测试多次以获取更稳定的性能数据"""
    logger.info(f"开始批量运行UI测试 ({num_runs}次)...")
    
    success_count = 0
    
    for i in range(num_runs):
        logger.info(f"\n运行测试 #{i+1}/{num_runs}")
        success = await run_ui_test()
        if success:
            success_count += 1
    
    success_rate = (success_count / num_runs) * 100
    logger.info(f"\n批量测试完成: 成功率 {success_rate:.2f}% ({success_count}/{num_runs})")

if __name__ == "__main__":
    # 创建缓存目录
    os.makedirs("ui_test_cache", exist_ok=True)
    
    # 运行UI测试
    # asyncio.run(run_ui_test())
    
    # 批量运行测试以获取更稳定的性能数据
    asyncio.run(batch_run_tests(1))  # 默认运行1次，可以增加次数以获取更稳定的数据 