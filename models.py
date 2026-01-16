# coding: utf-8
"""
SQLAlchemy ORM 模型定义
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base
class Account(Base):
    """公众号表"""
    __tablename__ = 'accounts'
    
    id = Column(Integer, primary_key=True)
    biz = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # 关系
    parameters = relationship("Parameter", back_populates="account", cascade="all, delete-orphan")
    articles = relationship("Article", back_populates="account", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Account(biz='{self.biz}', name='{self.name}')>"
class Parameter(Base):
    """参数表"""
    __tablename__ = 'parameters'
    
    id = Column(Integer, primary_key=True)
    biz = Column(String(100), ForeignKey('accounts.biz'), nullable=False, index=True)
    cookie = Column(Text, nullable=False)
    key = Column(Text, nullable=False)
    pass_ticket = Column(Text, nullable=False)
    uin = Column(Text, nullable=False)
    appmsg_token = Column(Text)
    captured_at = Column(DateTime, nullable=False)
    expires_at = Column(DateTime)
    is_valid = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # 关系
    account = relationship("Account", back_populates="parameters")
    
    def __repr__(self):
        return f"<Parameter(biz='{self.biz}', is_valid={self.is_valid})>"
class Article(Base):
    """文章表"""
    __tablename__ = 'articles'
    
    id = Column(Integer, primary_key=True)
    biz = Column(String(100), ForeignKey('accounts.biz'), nullable=False, index=True)
    url = Column(Text, unique=True, nullable=False)  # 完整URL
    short_url = Column(Text, index=True)  # 短链接（用于快速查找）
    title = Column(Text)
    html_content = Column(Text)  # HTML内容
    publish_date = Column(Date, index=True)
    read_count = Column(Integer, index=True)  # 阅读量
    old_like_count = Column(Integer)  # 点赞数（大拇指👍）
    like_count = Column(Integer)  # 喜欢数/收藏数（爱心❤️）
    share_count = Column(Integer)  # 分享数
    comment_count = Column(Integer)  # 评论数
    local_html_path = Column(Text)  # 本地HTML文件路径
    fetched_at = Column(DateTime, default=datetime.now, index=True)
    
    # 关系
    account = relationship("Account", back_populates="articles")
    
    def __repr__(self):
        return f"<Article(title='{self.title}', read_count={self.read_count})>"
    
    def to_dict(self):
        """转换为字典"""
        # 处理 publish_date 可能是字符串或 datetime
        if self.publish_date:
            if isinstance(self.publish_date, str):
                publish_date_str = self.publish_date
            else:
                publish_date_str = self.publish_date.isoformat()
        else:
            publish_date_str = None
        
        # 处理 fetched_at
        if self.fetched_at:
            if isinstance(self.fetched_at, str):
                fetched_at_str = self.fetched_at
            else:
                fetched_at_str = self.fetched_at.isoformat()
        else:
            fetched_at_str = None
            
        return {
            'id': self.id,
            'biz': self.biz,
            'url': self.url,
            'short_url': self.short_url,
            'title': self.title,
            'html_content': self.html_content,
            'publish_date': publish_date_str,
            'read_count': self.read_count,
            'old_like_count': self.old_like_count,
            'like_count': self.like_count,
            'share_count': self.share_count,
            'comment_count': self.comment_count,
            'local_html_path': self.local_html_path,
            'fetched_at': fetched_at_str
        }
