from . import (
    utility,
    auth,
    profile,
    catalog,
    reviews,
    wishlist,
    cart,
    orders,
    manage_orders,
    inventory,
    manage_products,
    manage_coupons,
    reports,
    admin,
    jobs_routes,
)

ALL_BLUEPRINTS = [
    utility.bp,
    auth.bp,
    profile.bp,
    catalog.bp,
    reviews.bp,
    wishlist.bp,
    cart.bp,
    orders.bp,
    manage_orders.bp,
    inventory.bp,
    manage_products.bp,
    manage_coupons.bp,
    reports.bp,
    admin.bp,
    jobs_routes.bp,
]


def register_all(app):
    for bp in ALL_BLUEPRINTS:
        app.register_blueprint(bp)
