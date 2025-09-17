"""
User handlers package for the vape shop Telegram bot.

This package contains all user-related handlers split into logical modules:
- catalog: Product catalog and product management handlers
- cart: Shopping cart management handlers
- orders: Order creation and management handlers  
- profile: User profile and language settings handlers
- menu: Main menu and navigation handlers
"""

from aiogram import Router

from . import catalog, cart, orders, profile, menu

def setup_user_routers():
    """Set up and return the main user router with all sub-routers included."""
    main_router = Router()
    
    # Include all sub-routers
    main_router.include_router(catalog.router)
    main_router.include_router(cart.router) 
    main_router.include_router(orders.router)
    main_router.include_router(profile.router)
    main_router.include_router(menu.router)
    
    return main_router

# Export the main router setup function
__all__ = ['setup_user_routers']