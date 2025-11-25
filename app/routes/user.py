from fastapi import APIRouter, Depends, Request

from app.controllers import UserController
from app.core.auth import require_auth
from app.schemas import UpdateProfileBase
from app.utils.http import api_success

user_routes = APIRouter(
    prefix="/users",
    dependencies=[
        Depends(require_auth),
    ],
    tags=["Users"],
)


class UserRoutes:
    """Routes to handles user related operations."""

    @staticmethod
    @user_routes.post("/")
    async def update_user(request: Request, user_data: UpdateProfileBase):
        """
        Update user profile.
        Args:
            request (Request): The FastAPI request object.
            user_data (UpdateProfileBase): The data to update the user profile.

        Returns:
            dict: API success response with the updated user profile data.

        """
        user = await UserController.update_user(request, user_data)
        return api_success(data=user, message="User profile updated successfully")
