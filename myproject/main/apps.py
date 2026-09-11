from django.apps import AppConfig


class MainConfig(AppConfig):
    name = 'main'

    def ready(self):
        # 註冊登入時自動補 Profile 的 signal
        from . import signals  # noqa: F401
