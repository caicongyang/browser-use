# 元素缓存演示

这个示例展示了如何实现和使用基于 URL 的元素缓存策略，通过缓存元素信息可以显著提高元素定位的效率，特别是对于结构相对稳定的后台管理系统。

## 功能特点

1. **URL 到元素的映射**：为每个 URL 创建元素缓存
2. **缓存验证机制**：验证缓存是否仍然有效
3. **差异化更新**：只更新变化的元素
4. **性能比较**：标准方法与缓存方法的性能对比

## 目录结构

```
element_cache_demo/
├── cache/
│   ├── __init__.py
│   ├── element_cache.py     # 元素缓存类
│   └── cache_manager.py     # 缓存管理器
├── browser_extension/
│   ├── __init__.py
│   └── context_extension.py # BrowserContext 扩展
├── demo.py                  # 演示脚本
└── README.md                # 说明文档
```

## 使用方法

1. 扩展 BrowserContext：

```python
from browser_use import Browser
from element_cache_demo import extend_browser_context

# 创建浏览器
browser = Browser()
context = await browser.new_context()

# 扩展浏览器上下文，添加缓存功能
context = extend_browser_context(context, cache_dir="cache_data")
```

2. 使用缓存获取元素：

```python
# 使用缓存获取元素
element = await context.get_dom_element_by_index_with_cache(index)
```

3. 初始化缓存：

```python
# 初始化多个页面的缓存
urls = ["https://example.com", "https://example.com/page1"]
await context.initialize_cache(urls)
```

## 演示内容

演示脚本 `demo.py` 包含四个测试场景：

1. **初始缓存构建**：构建并存储元素缓存
2. **使用缓存定位元素**：比较标准方法和缓存方法的性能差异
3. **缓存验证和更新**：验证缓存有效性并差异化更新
4. **性能比较**：在多个页面上测试性能提升

## 运行演示

```bash
cd examples
python -m element_cache_demo.demo
```

## 注意事项

1. 缓存策略应根据实际系统特点进行调整
2. 对于高度动态的页面，可能需要减少缓存依赖
3. 缓存文件可能会随时间增长，应实现定期清理机制 