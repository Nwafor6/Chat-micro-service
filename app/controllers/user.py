from fastapi import Request

from app.core.exceptions import NotFoundException, UnauthorizedAccess
from app.models.user import User
from app.schemas import UpdateProfileBase


class UserController:
    """Controller for user-related operations."""

    @staticmethod
    async def update_user(request: Request, user_data: UpdateProfileBase) -> User:
        """Update a user's profile information.

        Args:
            request (Request): The FastAPI request object.
            user_data (UpdateProfileBase): The payload containing user information.

        Returns:
            User: The updated User object.
        """
        # The user should already exist from the middleware
        if not request.user:
            raise UnauthorizedAccess("User not authenticated")

        # Get the user in the current session context to avoid session conflicts
        user_id_str = str(request.user.user_id)
        current_user = await User.first(user_id=user_id_str)

        if not current_user:
            raise NotFoundException("User not found in current session")

        # Update the user with the new information
        await current_user.update(user_info=user_data.user_info)
        return current_user
