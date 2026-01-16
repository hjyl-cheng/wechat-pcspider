# coding: utf-8
"""
数据库辅助函数
提供一些高级的数据库查询功能
"""
from typing import Optional, Tuple, Dict
from database import get_db_session
from models import Account, Parameter
from db_operations import get_valid_parameters
import logging

logger = logging.getLogger(__name__)


def get_biz_by_account_name(account_name: str) -> Tuple[Optional[str], Optional[Dict]]:
    """
    根据公众号名称获取BIZ和参数
    
    Parameters
    ----------
    account_name : str
        公众号名称
    
    Returns
    -------
    tuple
        (biz, params) - BIZ字符串和参数字典，如果不存在返回 (None, None)
    """
    with get_db_session() as session:
        account = session.query(Account).filter(Account.name == account_name).first()
        
        if account:
            biz = account.biz
            logger.info(f"✅ 找到公众号: {account_name} -> BIZ: {biz}")
            
            # 获取该BIZ的有效参数
            params = get_valid_parameters(biz)
            
            return biz, params
        else:
            logger.warning(f"⚠️  未找到公众号: {account_name}")
            return None, None
