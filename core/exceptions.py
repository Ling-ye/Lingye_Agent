"""异常体系"""

class LingyeAgentsException(Exception):
    """LingyeAgents基础异常类"""
    pass

class LLMException(LingyeAgentsException):
    """LLM相关异常"""
    pass

class AgentException(LingyeAgentsException):
    """Agent相关异常"""
    pass

class ConfigException(LingyeAgentsException):
    """配置相关异常"""
    pass

class ToolException(LingyeAgentsException):
    """工具相关异常"""
    pass
