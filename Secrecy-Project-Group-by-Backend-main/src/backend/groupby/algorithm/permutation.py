"""置换公共入口；保留已有导入方式。不是论文专用常数轮置换协议。"""
from .gen_perm import gen_perm
from .apply_perm import apply_perm
from .apply_inv import apply_inv

__all__ = ["gen_perm", "apply_perm", "apply_inv"]
