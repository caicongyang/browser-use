import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ElementCache:
    """元素缓存类，管理URL到元素映射的存储和检索"""
    
    def __init__(self, cache_dir: str = "cache_data"):
        """
        初始化元素缓存
        
        Args:
            cache_dir: 缓存文件存储目录
        """
        self.cache_dir = cache_dir
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
        
        # 确保缓存目录存在
        os.makedirs(cache_dir, exist_ok=True)
        
        # 加载缓存元数据
        self._load_metadata()
    
    def _load_metadata(self) -> None:
        """加载缓存元数据"""
        metadata_file = os.path.join(self.cache_dir, "metadata.json")
        if os.path.exists(metadata_file):
            try:
                with open(metadata_file, 'r') as f:
                    self.metadata = json.load(f)
                logger.info(f"已加载缓存元数据，共 {len(self.metadata)} 个条目")
            except Exception as e:
                logger.error(f"加载缓存元数据失败: {str(e)}")
                self.metadata = {}
    
    def _save_metadata(self) -> None:
        """保存缓存元数据"""
        metadata_file = os.path.join(self.cache_dir, "metadata.json")
        try:
            with open(metadata_file, 'w') as f:
                json.dump(self.metadata, f)
        except Exception as e:
            logger.error(f"保存缓存元数据失败: {str(e)}")
    
    def _get_cache_file(self, cache_key: str) -> str:
        """获取缓存文件路径"""
        # 使用 URL 的哈希值作为文件名，避免文件名过长或包含特殊字符
        import hashlib
        filename = hashlib.md5(cache_key.encode()).hexdigest() + ".json"
        return os.path.join(self.cache_dir, filename)
    
    def _generate_cache_key(self, url: str, params: Optional[Dict[str, str]] = None) -> str:
        """生成缓存键"""
        if not params:
            return url
        
        # 对于带参数的URL，生成一个包含关键参数的缓存键
        param_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
        return f"{url}?{param_str}"
    
    def get_elements(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        获取URL对应的元素
        
        Args:
            url: 页面URL
            params: URL参数
            
        Returns:
            元素字典，如果缓存不存在则返回空字典
        """
        cache_key = self._generate_cache_key(url, params)
        
        # 检查内存缓存
        if cache_key in self.cache:
            logger.debug(f"从内存缓存获取元素: {cache_key}")
            return self.cache[cache_key]
        
        # 检查文件缓存
        cache_file = self._get_cache_file(cache_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    elements = json.load(f)
                    # 更新内存缓存
                    self.cache[cache_key] = elements
                    logger.info(f"从文件缓存加载元素: {cache_key}, 共 {len(elements)} 个元素")
                    return elements
            except Exception as e:
                logger.error(f"加载缓存文件失败: {str(e)}")
        
        return {}
    
    def store_elements(self, url: str, elements: Dict[str, Any], params: Optional[Dict[str, str]] = None) -> None:
        """
        存储URL对应的元素
        
        Args:
            url: 页面URL
            elements: 元素字典
            params: URL参数
        """
        cache_key = self._generate_cache_key(url, params)
        
        # 更新内存缓存
        self.cache[cache_key] = elements
        
        # 更新元数据
        import time
        self.metadata[cache_key] = {
            "url": url,
            "timestamp": time.time(),
            "element_count": len(elements),
            "version": self.metadata.get(cache_key, {}).get("version", 0) + 1
        }
        self._save_metadata()
        
        # 保存到文件
        cache_file = self._get_cache_file(cache_key)
        try:
            with open(cache_file, 'w') as f:
                json.dump(elements, f)
            logger.info(f"已缓存 {len(elements)} 个元素到 {cache_key}")
        except Exception as e:
            logger.error(f"保存缓存文件失败: {str(e)}")
    
    def get_all_urls(self) -> list:
        """获取所有缓存的URL"""
        return [meta.get("url") for meta in self.metadata.values() if "url" in meta]
    
    def get_cache_info(self, url: str, params: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """获取缓存信息"""
        cache_key = self._generate_cache_key(url, params)
        return self.metadata.get(cache_key, {})
    
    def clear_cache(self, url: Optional[str] = None, params: Optional[Dict[str, str]] = None) -> None:
        """
        清除缓存
        
        Args:
            url: 如果指定，只清除该URL的缓存；否则清除所有缓存
            params: URL参数
        """
        if url:
            cache_key = self._generate_cache_key(url, params)
            if cache_key in self.cache:
                del self.cache[cache_key]
            
            if cache_key in self.metadata:
                del self.metadata[cache_key]
                self._save_metadata()
            
            cache_file = self._get_cache_file(cache_key)
            if os.path.exists(cache_file):
                try:
                    os.remove(cache_file)
                    logger.info(f"已清除缓存: {cache_key}")
                except Exception as e:
                    logger.error(f"清除缓存文件失败: {str(e)}")
        else:
            # 清除所有缓存
            self.cache = {}
            self.metadata = {}
            self._save_metadata()
            
            # 删除缓存文件
            for filename in os.listdir(self.cache_dir):
                if filename.endswith(".json"):
                    try:
                        os.remove(os.path.join(self.cache_dir, filename))
                    except Exception as e:
                        logger.error(f"删除缓存文件失败: {filename}, {str(e)}")
            
            logger.info("已清除所有缓存") 