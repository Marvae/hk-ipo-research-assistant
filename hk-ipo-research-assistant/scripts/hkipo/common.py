"""跨模块共享常量与 HTTP 客户端。

背景：各数据源模块此前各自定义了同一串 User-Agent，并为每次请求新建
httpx.Client。这里收敛为一份 UA 定义 + 一个统一的客户端工厂/fetch 助手。
（曾试过进程级共享单例 client，实测会被 AAStocks 的 cookie 坑死，
详见 http_client 的 docstring，已改回「每次新建、只收敛配置」。）

导入约定：本目录的模块同时以「扁平模块」（CLI 入口把本目录加入 sys.path，
`import aastocks`）和「包内模块」（`hkipo.aastocks`，相对导入）两种方式
被加载，因此调用方统一用双写导入：

    try:
        from common import USER_AGENT, http_client, fetch_text
    except ImportError:  # 包模式且本目录不在 sys.path 时
        from .common import USER_AGENT, http_client, fetch_text
"""

from __future__ import annotations

import httpx

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def http_client() -> httpx.Client:
    """返回一个新配置好的 httpx.Client（每次调用都新建，调用方用完即弃）。

    只收敛「配置」（timeout=30、follow_redirects=True），不共享状态——
    这是实测后的决定。曾实现为进程级共享单例，结果被 AAStocks 坑死：
    其首个响应会种下 aa_cookie，共享 client 在后续请求中带上该 cookie
    后，响应会被挂住直到 30s 读超时（交错对照实验 3/3 复现：带 cookie
    的请求必超时、清空 cookie 立即恢复、同期每次新建的 client 恒 ~2s
    正常）。共享连接的 keep-alive 复用在同一环境下也有同样的挂死表现。
    因此 cookie 与连接都保持「每次新建 Client」的原始语义；本工具是
    短生命周期 CLI，连接建立开销相对页面抓取可忽略，进程退出统一回收。
    调用方需要不同行为时用单次请求参数覆盖（如 timeout=10、
    follow_redirects=False）。
    """
    return httpx.Client(timeout=30, follow_redirects=True)


def fetch_text(url: str, headers: dict | None = None, timeout: float | None = None) -> str:
    """GET 一个页面并返回文本；非 2xx 抛 httpx.HTTPError（同 raise_for_status 语义）。"""
    kwargs: dict = {}
    if headers is not None:
        kwargs["headers"] = headers
    if timeout is not None:
        kwargs["timeout"] = timeout
    resp = http_client().get(url, **kwargs)
    resp.raise_for_status()
    return resp.text
