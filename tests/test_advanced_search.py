# test_advanced_search.py
from dotenv import load_dotenv
from lingye_agent.tools import create_advanced_search_registry, AdvancedSearchTool

# 加载环境变量
load_dotenv()

def test_advanced_search():
    """测试高级搜索工具"""

    # 创建包含高级搜索工具的注册表
    registry = create_advanced_search_registry()

    print("测试高级搜索工具\n")

    # 测试查询
    test_queries = [
        "钉宫理惠简介",
        "vedal和anny近况"
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"测试 {i}: {query}")
        result = registry.execute_tool("advanced_search", query)
        print(f"结果: {result}\n")
        print("-" * 60 + "\n")

def test_api_configuration():
    """测试API配置检查"""
    print("测试API配置检查:")

    # 直接创建搜索工具实例
    search_tool = AdvancedSearchTool()

    # 如果没有配置API，会显示配置提示
    result = search_tool.search("羊宫妃那最出名的角色top10")
    print(f"搜索结果: {result}")

def test_with_agent():
    """测试与Agent的集成"""
    print("\n与Agent集成测试:")
    print("高级搜索工具已准备就绪，可以与Agent集成使用")

    # 显示工具描述
    registry = create_advanced_search_registry()
    tools_desc = registry.get_tools_description()
    print(f"工具描述:\n{tools_desc}")

if __name__ == "__main__":
    test_advanced_search()
    test_api_configuration()
    test_with_agent()
