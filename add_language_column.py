#!/usr/bin/env python3
"""
Database migration script to add language_code column to users table
"""

import asyncio
import asyncpg
from config import DATABASE_URL

async def migrate_db():
    """Add language_code column to users table"""
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # Check if column exists
        result = await conn.fetchval("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='users' AND column_name='language_code'
        """)
        
        if not result:
            print("Adding language_code column to users table...")
            await conn.execute("ALTER TABLE users ADD COLUMN language_code TEXT DEFAULT 'ru'")
            print("✅ Language column added successfully!")
        else:
            print("✅ Language column already exists.")
            
        # Update existing users without language_code to 'ru'
        await conn.execute("""
            UPDATE users 
            SET language_code = 'ru' 
            WHERE language_code IS NULL
        """)
        
        # Check how many users now have language_code set
        total_users = await conn.fetchval("SELECT COUNT(*) FROM users WHERE language_code = 'ru'")
        print(f"✅ {total_users} users now have Russian as default language.")
            
    except Exception as e:
        print(f"❌ Error during migration: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_db())