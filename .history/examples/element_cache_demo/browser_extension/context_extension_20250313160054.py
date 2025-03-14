import logging
import os
import sys
from typing import Dict, Any, Optional

# 添加当前目录的父目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from browser_use.browser.context import BrowserContext
from browser_use.dom.views import DOMElementNode
from cache.element_cache import ElementCache
from cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

def extend_browser_context(browser_context: BrowserContext, cache_dir: str = "cache_data") -> BrowserContext:
    """
    扩展BrowserContext，添加缓存功能
    
    Args:
        browser_context: 原始BrowserContext实例
        cache_dir: 缓存目录
        
    Returns:
        扩展后的BrowserContext实例
    """
    # 添加缓存相关属性
    browser_context.element_cache = ElementCache(cache_dir=cache_dir)
    browser_context.cache_manager = CacheManager(browser_context.element_cache, browser_context)
    
    # 保存原始方法
    original_get_dom_element_by_index = browser_context.get_dom_element_by_index
    
    # 添加缓存版本的方法
    async def get_dom_element_by_index_with_cache(index: int) -> Optional[DOMElementNode]:
        """
        使用缓存获取DOM元素
        
        Args:
            index: 元素索引
            
        Returns:
            DOM元素节点，如果找不到则返回None
        """
        current_url = await browser_context._get_current_url()
        
        # 尝试从缓存获取元素
        cached_elements = await browser_context.cache_manager.get_elements_with_cache(current_url)
        
        if str(index) in cached_elements:
            # 使用缓存的元素信息创建DOM元素节点
            element_data = cached_elements[str(index)]
            element_node = DOMElementNode(
                tag_name=element_data['tag_name'],
                xpath=element_data['xpath'],
                attributes=element_data['attributes'],
                children=[],  # 简化处理，不包含子元素
                is_visible=element_data.get('is_visible', True),
                is_interactive=element_data.get('is_interactive', True),
                is_in_viewport=element_data.get('is_in_viewport', True),
                highlight_index=element_data.get('highlight_index', index),
                parent=None
            )
            logger.info(f"从缓存获取元素: index={index}")
            return element_node
        
        # 缓存中没有找到，回退到标准方法
        logger.info(f"缓存中未找到元素 index={index}，使用标准方法")
        return await original_get_dom_element_by_index(index)
    
    # 替换方法
    browser_context.get_dom_element_by_index_with_cache = get_dom_element_by_index_with_cache
    
    # 添加辅助方法
    async def _get_current_url() -> str:
        """获取当前URL"""
        page = await browser_context.get_current_page()
        return await page.url()
    
    browser_context._get_current_url = _get_current_url
    
    # 添加缓存管理方法
    async def initialize_cache(urls: list) -> None:
        """
        初始化元素缓存
        
        Args:
            urls: 要缓存的URL列表
        """
        for url in urls:
            logger.info(f"初始化缓存: {url}")
            # 导航到URL
            page = await browser_context.get_current_page()
            await page.goto(url)
            # 等待页面加载
            await page.wait_for_load_state()
            # 获取并缓存元素
            await browser_context.cache_manager.get_elements_with_cache(url, force_refresh=True)
    
    browser_context.initialize_cache = initialize_cache
    
    return browser_context 