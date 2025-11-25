"""
数据库元数据API路由
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Optional
from app.services.database_service import get_database_service
from app.models.schemas import DatabaseInfo, TableInfo, TableSearchResult

router = APIRouter()


@router.get("/databases", response_model=List[str])
async def get_databases():
    """
    获取所有数据库列表
    Returns:
        List[str]: 数据库名称列表
    """
    try:
        db_service = get_database_service()
        databases = db_service.get_databases()
        return databases
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取数据库列表失败: {str(e)}")


@router.get("/databases/{database}/tables", response_model=List[str])
async def get_tables(database: str):
    """
    获取指定数据库的所有表
    Args:
        database: 数据库名称
    Returns:
        List[str]: 表名称列表
    """
    try:
        db_service = get_database_service()
        tables = db_service.get_tables(database)
        return tables
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表列表失败: {str(e)}")


@router.get("/databases/{database}/tables/{table}/schema")
async def get_table_schema(database: str, table: str):
    """
    获取表的Schema信息
    Args:
        database: 数据库名称
        table: 表名称
    Returns:
        List[Dict]: 字段信息列表
    """
    try:
        db_service = get_database_service()
        schema = db_service.get_table_schema(database, table)
        return schema
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取表结构失败: {str(e)}")


@router.get("/metadata", response_model=Dict[str, List[str]])
async def get_all_metadata():
    """
    获取所有数据库及其表的元数据
    Returns:
        Dict[str, List[str]]: {数据库名: [表名列表]}
    """
    try:
        db_service = get_database_service()
        metadata = db_service.get_all_metadata()
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取元数据失败: {str(e)}")


@router.get("/search/tables")
async def search_tables(keyword: str = Query(..., description="搜索关键字")):
    """
    根据关键字搜索表
    Args:
        keyword: 搜索关键字
    Returns:
        List[Dict]: 匹配的表列表
    """
    try:
        db_service = get_database_service()
        results = db_service.search_tables(keyword)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"搜索表失败: {str(e)}")
