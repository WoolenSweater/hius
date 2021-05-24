import os
from starlette.staticfiles import StaticFiles as BaseStaticFiles
from liteapi.types import AttrScope


class StaticFiles(BaseStaticFiles):
    def get_path(self, scope: AttrScope) -> str:
        return os.path.normpath(os.path.join(*scope.ctx['path'].split('/')))
