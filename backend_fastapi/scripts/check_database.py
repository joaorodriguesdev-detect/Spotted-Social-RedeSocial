#!/usr/bin/env python
"""Database diagnostic script – verifies connection, tables, and permissions."""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import from backend_fastapi
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import settings
from database import engine, Base, async_session_factory
from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError


async def check_database():
    """Run comprehensive database checks."""
    print("=" * 70)
    print("🔍  DATABASE DIAGNOSTIC CHECK")
    print("=" * 70)

    # 1. Check configuration
    print("\n1️⃣  CHECK: Configuration")
    print(f"   DATABASE_URL: {settings.DATABASE_URL}")

    # 2. Check connection
    print("\n2️⃣  CHECK: Database Connection")
    try:
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("   ✓ Connection successful!")
    except SQLAlchemyError as e:
        print(f"   ✗ Connection failed: {type(e).__name__}")
        print(f"   ✗ Error: {str(e)}")
        return False
    except Exception as e:
        print(f"   ✗ Unexpected error: {type(e).__name__}")
        print(f"   ✗ Error: {str(e)}")
        return False

    # 3. Check/Create tables
    print("\n3️⃣  CHECK: Tables Creation")
    try:
        async with engine.begin() as conn:
            print("   Creating tables (if they don't exist)...")
            await conn.run_sync(Base.metadata.create_all)
            print("   ✓ Tables created/verified!")
    except Exception as e:
        print(f"   ✗ Failed to create tables: {type(e).__name__}")
        print(f"   ✗ Error: {str(e)}")
        return False

    # 4. Inspect tables
    print("\n4️⃣  CHECK: Existing Tables")
    try:
        async with engine.begin() as conn:
            inspector = inspect(await conn.connection())
            tables = inspector.get_table_names()

            if not tables:
                print("   ⚠️  No tables found in database!")
            else:
                print(f"   ✓ Found {len(tables)} table(s):")
                for table_name in sorted(tables):
                    columns = inspector.get_columns(table_name)
                    print(f"      • {table_name} ({len(columns)} columns)")
    except Exception as e:
        print(f"   ✗ Failed to inspect tables: {type(e).__name__}")
        print(f"   ✗ Error: {str(e)}")

    # 5. Check User table specifically
    print("\n5️⃣  CHECK: User Table")
    try:
        async with async_session_factory() as session:
            from models.user import User
            result = await session.execute(text("SELECT COUNT(*) as count FROM user"))
            count = result.scalar()
            print(f"   ✓ User table exists with {count} users")
    except Exception as e:
        print(f"   ✗ User table check failed: {type(e).__name__}")
        print(f"   ✗ Error: {str(e)}")

    # 6. Test write permissions
    print("\n6️⃣  CHECK: Write Permissions")
    try:
        from datetime import datetime
        from models.user import User
        from utils import br_time
        # Don't use bcrypt due to version compatibility issues
        # Just test if we can create a user with a regular string
        
        test_username = f"test_user_{int(datetime.now().timestamp())}"
        test_user = User(
            name="Test User",
            username=test_username,
            password="hashed_password_here",  # Plain string for testing only
            created_at=br_time(),
        )

        async with async_session_factory() as session:
            session.add(test_user)
            await session.flush()
            user_id = test_user.id
            await session.commit()
            print(f"   ✓ Write test successful! Created user ID: {user_id}")

            # Clean up - delete the test user
            await session.execute(text(f"DELETE FROM user WHERE id = {user_id}"))
            await session.commit()
            print(f"   ✓ Cleanup successful!")

    except Exception as e:
        print(f"   ✗ Write test failed: {type(e).__name__}")
        print(f"   ✗ Error: {str(e)}")
        return False

    # 7. Check file permissions (for SQLite)
    if "sqlite" in settings.DATABASE_URL.lower():
        print("\n7️⃣  CHECK: SQLite File Permissions")
        db_file = "spotted.db"
        if os.path.exists(db_file):
            is_writable = os.access(db_file, os.W_OK)
            is_readable = os.access(db_file, os.R_OK)
            file_size = os.path.getsize(db_file)
            print(f"   ✓ File exists: {db_file}")
            print(f"   ✓ File size: {file_size} bytes")
            print(f"   ✓ Readable: {'Yes' if is_readable else 'No'}")
            print(f"   ✓ Writable: {'Yes' if is_writable else 'No'}")

            if not is_writable:
                print("   ⚠️  WARNING: Database file is not writable!")
                return False
        else:
            print(f"   ⚠️  File does not exist yet: {db_file}")

    print("\n" + "=" * 70)
    print("✅  ALL CHECKS PASSED!")
    print("=" * 70)
    return True


async def main():
    """Entry point."""
    try:
        success = await check_database()
        await engine.dispose()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        await engine.dispose()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {type(e).__name__}")
        print(f"   {str(e)}")
        import traceback
        traceback.print_exc()
        await engine.dispose()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

