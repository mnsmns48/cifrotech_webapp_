from fastapi_users import FastAPIUsers

from api_users.backend import authentication_backend
from api_users.dependencies.user_manager import get_user_manager
from models import User
from var_types import var_types

fastapi_users = FastAPIUsers[User, var_types.UserIdType](get_user_manager, [authentication_backend])

current_super_user = fastapi_users.current_user(active=True, verified=True, superuser=True)
current_user = fastapi_users.current_user()
