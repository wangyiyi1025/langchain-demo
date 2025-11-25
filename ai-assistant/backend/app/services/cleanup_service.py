"""
定时清理服务
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from app.services.conversation_db_service import conversation_db_service


class CleanupService:
    """清理服务"""

    def __init__(self):
        """初始化调度器"""
        self.scheduler = BackgroundScheduler()

    def cleanup_old_messages(self):
        """清理7天前的历史消息"""
        try:
            deleted_count = conversation_db_service.delete_old_messages(days=7)
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 清理任务执行完成，删除了 {deleted_count} 条历史消息")
        except Exception as e:
            current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{current_time}] 清理任务执行失败: {str(e)}")

    def start(self):
        """启动定时任务"""
        # 每天凌晨2点执行清理任务
        self.scheduler.add_job(
            self.cleanup_old_messages,
            trigger=CronTrigger(hour=2, minute=0),
            id='cleanup_old_messages',
            name='清理7天前的历史消息',
            replace_existing=True
        )

        self.scheduler.start()
        print("✓ 定时清理任务已启动（每天凌晨2点执行）")

    def stop(self):
        """停止定时任务"""
        if self.scheduler.running:
            self.scheduler.shutdown()
            print("✓ 定时清理任务已停止")

    def run_now(self):
        """立即执行清理任务（用于测试）"""
        self.cleanup_old_messages()


# 创建全局清理服务实例
cleanup_service = CleanupService()
