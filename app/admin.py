from sqladmin import Admin, ModelView

from app.models.chat import Message, Room
from app.models.user import User


class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.user_id, User.is_ai, User.created_at]
    column_searchable_list = [User.user_id]
    column_sortable_list = [User.id, User.created_at]
    form_columns = [User.user_id, User.is_ai, User.user_info]


class RoomAdmin(ModelView, model=Room):
    column_list = "__all__"
    column_searchable_list = ["name"]


class MessageAdmin(ModelView, model=Message):
    column_list = "__all__"


def setup_admin(app, engine):
    """Register all admin views."""
    admin = Admin(app, engine, base_url="/val-admin")
    
    admin.add_view(UserAdmin)
    admin.add_view(RoomAdmin)
    admin.add_view(MessageAdmin)
    
    return admin