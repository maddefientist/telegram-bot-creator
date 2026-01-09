"""Create admin user script."""
import argparse
import asyncio
import sys

from sqlalchemy import select

sys.path.insert(0, ".")

from database import get_db_context
from models.user import User, UserRole
from core.auth import get_password_hash


async def create_admin(email: str, password: str) -> None:
    """Create an admin user."""
    async with get_db_context() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()

        if existing:
            if existing.role == UserRole.ADMIN:
                print(f"User {email} is already an admin")
                return
            else:
                # Upgrade to admin
                existing.role = UserRole.ADMIN
                await db.commit()
                print(f"Upgraded {email} to admin")
                return

        # Create new admin user
        user = User(
            email=email,
            hashed_password=get_password_hash(password),
            role=UserRole.ADMIN,
        )
        db.add(user)
        await db.commit()

        print(f"Created admin user: {email}")


def main():
    parser = argparse.ArgumentParser(description="Create admin user")
    parser.add_argument("--email", required=True, help="Admin email")
    parser.add_argument("--password", required=True, help="Admin password")

    args = parser.parse_args()

    if len(args.password) < 8:
        print("Password must be at least 8 characters")
        sys.exit(1)

    asyncio.run(create_admin(args.email, args.password))


if __name__ == "__main__":
    main()
