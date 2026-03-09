from django.apps import AppConfig


class LotteryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.lottery"
    verbose_name = "抽奖管理"

    def ready(self):
        # 注册信号：维护客户参与/领奖统计
        from . import signals  # noqa: F401
