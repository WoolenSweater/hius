import os
from starlette.types import Scope
from starlette.staticfiles import StaticFiles as BaseStaticFiles


class StaticFiles(BaseStaticFiles):
    def get_path(self, scope: Scope) -> str:
        return os.path.normpath(os.path.join(*scope['ctx_path'].split('/')))
