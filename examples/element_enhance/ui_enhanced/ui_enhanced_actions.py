import logging
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union
from dataclasses import dataclass
from browser_use.agent.views import ActionResult

logger = logging.getLogger(__name__)

@dataclass
class ActionResponse:
    """操作响应类"""
    success: bool
    message: str
    page_state_changed: bool = False
    data: Optional[Any] = None

    @classmethod
    def from_result(cls, success: bool, message: str, data: Any = None, 
                   page_state_changed: bool = False) -> 'ActionResponse':
        """创建ActionResponse实例"""
        return cls(success=success, message=str(message), 
                  data=data, page_state_changed=page_state_changed)

class ElementHelper:
    """元素操作辅助类"""
    @staticmethod
    async def is_hidden(element) -> bool:
        """检查元素是否隐藏"""
        if hasattr(element, 'is_hidden') and element.is_hidden:
            return True
        if hasattr(element, 'attributes'):
            style = element.attributes.get('style', '').lower()
            if 'display: none' in style or 'visibility: hidden' in style:
                return True
            if element.attributes.get('hidden') is not None:
                return True
        return False

    @staticmethod
    async def get_element(context, index: int):
        """获取元素"""
        try:
            dom_state = await context.get_state()
            return dom_state.selector_map.get(index)
        except Exception as e:
            logger.error(f"获取元素失败: {e}")
            return None

class BaseAction:
    """基础Action类"""
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.parameters: Dict[str, str] = {}

    async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
        """执行操作"""
        raise NotImplementedError

    async def _get_page(self, context):
        """获取页面"""
        return await context.get_current_page()

class UIEnhancedActions:
    """UI增强操作类"""
    
    class InputTextAction(BaseAction):
        """文本输入操作"""
        def __init__(self):
            super().__init__("input_text", "输入文本到元素")
            self.parameters = {
                "index": "元素索引",
                "text": "要输入的文本"
            }

        async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
            try:
                index = int(params.get("index", 0))
                text = str(params.get("text", ""))
                if not text:
                    return ActionResponse.from_result(False, "未指定文本")

                page = await self._get_page(context)
                element = await ElementHelper.get_element(context, index)
                if not element:
                    return ActionResponse.from_result(False, "未找到元素")

                # 尝试不同的输入方法
                if await self._try_input_methods(page, element, text, context):
                    return ActionResponse.from_result(True, f"输入成功: {text}", 
                                                    page_state_changed=True)
                return ActionResponse.from_result(False, "所有输入方法都失败")
            except Exception as e:
                return ActionResponse.from_result(False, f"输入失败: {e}")

        async def _try_input_methods(self, page, element, text: str, context) -> bool:
            """尝试多种输入方法"""
            methods = [
                self._try_click_type,
                self._try_fill,
                self._try_js_input
            ]
            for method in methods:
                try:
                    if await method(page, element, text, context):
                        return True
                except Exception as e:
                    logger.warning(f"{method.__name__} 失败: {e}")
            return False

        async def _try_click_type(self, page, element, text: str, context) -> bool:
            """点击并输入"""
            await page.click(element.selector)
            await page.keyboard.type(text)
            return True

        async def _try_fill(self, page, element, text: str, _) -> bool:
            """使用fill方法"""
            await page.fill(element.selector, text)
            return True

        async def _try_js_input(self, page, element, text: str, _) -> bool:
            """使用JavaScript输入"""
            await page.evaluate(f"""
                selector => {{
                    const el = document.querySelector(selector);
                    if (el) {{
                        el.value = '{text}';
                        el.dispatchEvent(new Event('input', {{bubbles:true}}));
                        el.dispatchEvent(new Event('change', {{bubbles:true}}));
                    }}
                }}
            """, element.selector)
            return True

    class FindElementAction(BaseAction):
        """元素查找操作"""
        def __init__(self):
            super().__init__("find_element", "查找元素")
            self.parameters = {
                "text": "要查找的文本",
                "tag": "HTML标签",
                "exact": "是否精确匹配"
            }

        async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
            try:
                text = str(params.get("text", ""))
                tag = str(params.get("tag", "")).lower()
                exact = bool(params.get("exact", False))

                if not text:
                    return ActionResponse.from_result(False, "未指定查找文本")

                element = await self._find_element(context, text, tag, exact)
                if element:
                    return ActionResponse.from_result(True, "找到元素", data=element)
                return ActionResponse.from_result(False, "未找到元素")
            except Exception as e:
                return ActionResponse.from_result(False, f"查找失败: {e}")

        async def _find_element(self, context, text: str, tag: str, exact: bool):
            """查找元素的具体实现"""
            dom_state = await context.get_state()
            for index, element in dom_state.selector_map.items():
                if await ElementHelper.is_hidden(element):
                    continue
                if tag and element.tag_name.lower() != tag:
                    continue
                element_text = element.get_all_text_till_next_clickable_element()
                if (exact and element_text == text) or (not exact and text in element_text):
                    return element
            return None

    class PageAction(BaseAction):
        """页面操作"""
        def __init__(self):
            super().__init__("page_action", "页面相关操作")
            self.parameters = {"wait_time": "等待时间(秒)"}

        async def execute(self, params: Dict[str, Any], context) -> ActionResponse:
            try:
                wait_time = int(params.get("wait_time", 15))
                page = await self._get_page(context)
                
                await page.wait_for_load_state("networkidle")
                await asyncio.sleep(min(2, wait_time))
                await page.wait_for_load_state("domcontentloaded")
                
                return ActionResponse.from_result(True, "页面加载完成", 
                                                page_state_changed=True)
            except Exception as e:
                return ActionResponse.from_result(False, f"页面操作失败: {e}")

    @classmethod
    async def register_actions(cls, controller) -> None:
        """注册所有操作"""
        actions = {
            'input_text': cls.InputTextAction(),
            'find_element': cls.FindElementAction(),
            'page_action': cls.PageAction()
        }
        
        for name, action in actions.items():
            setattr(controller, name, 
                   await cls._create_action_method(action, controller))
        logger.info("UI操作注册完成")

    @staticmethod
    async def _create_action_method(action: BaseAction, controller):
        """创建操作方法"""
        async def method(*_, **kwargs):
            response = await action.execute(kwargs, controller.context)
            return {
                'success': response.success,
                'message': response.message,
                'data': response.data,
                'page_state_changed': response.page_state_changed
            }
        return method