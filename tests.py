"""
Comprehensive test suite for FlaskShop e-commerce application.
Tests all core functionalities: auth, products, cart, orders, admin, roles,
categories, search, and payment gateway.
"""
import os
import sys
import unittest
import tempfile

# Ensure the app directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from extensions import db
from models import User, Product, CartItem, Order, OrderItem, Category
from config import Config


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # in-memory DB
    WTF_CSRF_ENABLED = False  # disable CSRF for testing
    SERVER_NAME = 'localhost'


class BaseTestCase(unittest.TestCase):
    """Base test case with app setup/teardown."""

    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()

    def register_user(self, name='Test User', email='test@test.com', password='password123'):
        return self.client.post('/auth/register', data={
            'name': name,
            'email': email,
            'password': password,
            'confirm_password': password
        }, follow_redirects=True)

    def login_user(self, email='test@test.com', password='password123'):
        return self.client.post('/auth/login', data={
            'email': email,
            'password': password
        }, follow_redirects=True)

    def login_admin(self):
        return self.client.post('/auth/login', data={
            'email': 'admin@shop.com',
            'password': 'admin123'
        }, follow_redirects=True)

    def create_product(self, name='Test Product', price=29.99, stock=10,
                       description='A test product', category_id=0):
        return self.client.post('/admin/products/add', data={
            'name': name,
            'price': price,
            'stock': stock,
            'description': description,
            'category_id': category_id,
            'is_featured': False
        }, follow_redirects=True)

    def create_category(self, name='Test Category', icon='📦', description='A test category'):
        return self.client.post('/admin/categories/add', data={
            'name': name,
            'icon': icon,
            'description': description
        }, follow_redirects=True)


# ─────────────────────────────────────────────
# 1. AUTHENTICATION TESTS
# ─────────────────────────────────────────────
class TestAuth(BaseTestCase):

    def test_register_page_loads(self):
        """GET /auth/register returns 200."""
        resp = self.client.get('/auth/register')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Create Account', resp.data)

    def test_login_page_loads(self):
        """GET /auth/login returns 200."""
        resp = self.client.get('/auth/login')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Welcome Back', resp.data)

    def test_register_new_user(self):
        """User registration creates a new user."""
        resp = self.register_user()
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Registration successful', resp.data)
        user = User.query.filter_by(email='test@test.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.name, 'Test User')
        self.assertEqual(user.role, 'user')

    def test_register_duplicate_email(self):
        """Registration with existing email fails."""
        self.register_user()
        resp = self.register_user()
        self.assertIn(b'Email already registered', resp.data)

    def test_login_valid_credentials(self):
        """Login with correct credentials succeeds."""
        self.register_user()
        resp = self.login_user()
        self.assertIn(b'Login successful', resp.data)

    def test_login_invalid_credentials(self):
        """Login with wrong password fails."""
        self.register_user()
        resp = self.login_user(password='wrongpass')
        self.assertIn(b'Invalid email or password', resp.data)

    def test_login_nonexistent_user(self):
        """Login with non-existent email fails."""
        resp = self.login_user(email='nobody@test.com')
        self.assertIn(b'Invalid email or password', resp.data)

    def test_logout(self):
        """Logout redirects and shows message."""
        self.register_user()
        self.login_user()
        resp = self.client.get('/auth/logout', follow_redirects=True)
        self.assertIn(b'logged out', resp.data)

    def test_admin_seeded(self):
        """Default admin user is seeded automatically."""
        admin = User.query.filter_by(email='admin@shop.com').first()
        self.assertIsNotNone(admin)
        self.assertTrue(admin.is_admin)


# ─────────────────────────────────────────────
# 2. USER MODEL TESTS
# ─────────────────────────────────────────────
class TestUserModel(BaseTestCase):

    def test_password_hashing(self):
        """Passwords are hashed, not stored in plaintext."""
        user = User(name='Test', email='t@t.com', role='user')
        user.set_password('mypassword')
        self.assertNotEqual(user.password_hash, 'mypassword')
        self.assertTrue(user.check_password('mypassword'))
        self.assertFalse(user.check_password('wrongpassword'))

    def test_is_admin_property(self):
        """is_admin property works correctly."""
        admin = User(name='A', email='a@a.com', role='admin')
        user = User(name='U', email='u@u.com', role='user')
        self.assertTrue(admin.is_admin)
        self.assertFalse(user.is_admin)


# ─────────────────────────────────────────────
# 3. PRODUCT CRUD TESTS (Admin)
# ─────────────────────────────────────────────
class TestProductCRUD(BaseTestCase):

    def test_create_product(self):
        """Admin can create a product."""
        self.login_admin()
        resp = self.create_product()
        self.assertIn(b'created', resp.data)
        product = Product.query.filter_by(name='Test Product').first()
        self.assertIsNotNone(product)
        self.assertEqual(product.price, 29.99)
        self.assertEqual(product.stock, 10)

    def test_view_products_admin(self):
        """Admin can view product list."""
        self.login_admin()
        self.create_product()
        resp = self.client.get('/admin/products')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Test Product', resp.data)

    def test_edit_product(self):
        """Admin can edit a product."""
        self.login_admin()
        self.create_product()
        product = Product.query.filter_by(name='Test Product').first()
        resp = self.client.post(f'/admin/products/edit/{product.id}', data={
            'name': 'Updated Product',
            'price': 49.99,
            'stock': 20,
            'description': 'Updated description',
            'category_id': 0,
            'is_featured': False
        }, follow_redirects=True)
        self.assertIn(b'updated', resp.data)
        updated = Product.query.get(product.id)
        self.assertEqual(updated.name, 'Updated Product')
        self.assertEqual(updated.price, 49.99)

    def test_delete_product(self):
        """Admin can delete a product."""
        self.login_admin()
        self.create_product()
        product = Product.query.filter_by(name='Test Product').first()
        resp = self.client.post(f'/admin/products/delete/{product.id}', follow_redirects=True)
        self.assertIn(b'deleted', resp.data)
        self.assertIsNone(Product.query.get(product.id))

    def test_non_admin_cannot_create_product(self):
        """Regular user cannot access admin product creation."""
        self.register_user()
        self.login_user()
        resp = self.client.get('/admin/products/add')
        self.assertEqual(resp.status_code, 403)


# ─────────────────────────────────────────────
# 4. CART SYSTEM TESTS
# ─────────────────────────────────────────────
class TestCartSystem(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Create a product for cart tests
        self.login_admin()
        self.create_product(name='Cart Test Item', price=15.00, stock=5)
        self.client.get('/auth/logout')
        # Register and login as regular user
        self.register_user()
        self.login_user()

    def test_add_to_cart(self):
        """User can add a product to cart."""
        product = Product.query.filter_by(name='Cart Test Item').first()
        resp = self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        self.assertIn(b'added to cart', resp.data)
        cart_item = CartItem.query.first()
        self.assertIsNotNone(cart_item)
        self.assertEqual(cart_item.quantity, 1)

    def test_add_to_cart_increments_quantity(self):
        """Adding same product again increases quantity."""
        product = Product.query.filter_by(name='Cart Test Item').first()
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        cart_item = CartItem.query.first()
        self.assertEqual(cart_item.quantity, 2)

    def test_view_cart(self):
        """User can view their cart."""
        product = Product.query.filter_by(name='Cart Test Item').first()
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        resp = self.client.get('/cart')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Cart Test Item', resp.data)

    def test_update_cart_quantity(self):
        """User can update item quantity in cart."""
        product = Product.query.filter_by(name='Cart Test Item').first()
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        cart_item = CartItem.query.first()
        resp = self.client.post(f'/cart/update/{cart_item.id}', data={
            'quantity': 3
        }, follow_redirects=True)
        self.assertIn(b'Cart updated', resp.data)
        cart_item = CartItem.query.get(cart_item.id)
        self.assertEqual(cart_item.quantity, 3)

    def test_remove_from_cart(self):
        """User can remove item from cart."""
        product = Product.query.filter_by(name='Cart Test Item').first()
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        cart_item = CartItem.query.first()
        resp = self.client.post(f'/cart/remove/{cart_item.id}', follow_redirects=True)
        self.assertIn(b'removed from cart', resp.data)
        self.assertEqual(CartItem.query.count(), 0)

    def test_add_out_of_stock_product(self):
        """Cannot add out-of-stock product to cart."""
        product = Product.query.filter_by(name='Cart Test Item').first()
        product.stock = 0
        db.session.commit()
        resp = self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        self.assertIn(b'out of stock', resp.data)

    def test_cart_requires_login(self):
        """Cart page requires login."""
        self.client.get('/auth/logout')
        resp = self.client.get('/cart', follow_redirects=True)
        self.assertIn(b'Welcome Back', resp.data)  # redirected to login


# ─────────────────────────────────────────────
# 5. ORDER SYSTEM & PAYMENT GATEWAY TESTS
# ─────────────────────────────────────────────
class TestOrderSystem(BaseTestCase):

    def setUp(self):
        super().setUp()
        # Create product via admin
        self.login_admin()
        self.create_product(name='Order Test Item', price=25.00, stock=10)
        self.client.get('/auth/logout')
        # Register, login, and add to cart
        self.register_user()
        self.login_user()
        product = Product.query.filter_by(name='Order Test Item').first()
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)

    def _checkout_data(self):
        """Return valid checkout payment form data."""
        return {
            'full_name': 'Test User',
            'address': '123 Test Street',
            'city': 'San Francisco',
            'state': 'CA',
            'zip_code': '94102',
            'phone': '+15551234567',
            'cardholder_name': 'Test User',
            'card_number': '4111111111111111',
            'card_expiry': '12/28',
            'card_cvv': '123'
        }

    def test_checkout_page_loads(self):
        """GET /checkout shows the checkout form."""
        resp = self.client.get('/checkout')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Secure Checkout', resp.data)
        self.assertIn(b'Shipping', resp.data)
        self.assertIn(b'Payment', resp.data)

    def test_checkout_creates_order(self):
        """Placing an order via payment creates an order and clears cart."""
        resp = self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        self.assertIn(b'Payment successful', resp.data)
        self.assertEqual(Order.query.count(), 1)
        self.assertEqual(CartItem.query.count(), 0)

    def test_checkout_reduces_stock(self):
        """Checkout reduces product stock."""
        product = Product.query.filter_by(name='Order Test Item').first()
        initial_stock = product.stock
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        product = Product.query.filter_by(name='Order Test Item').first()
        self.assertEqual(product.stock, initial_stock - 1)

    def test_order_total_includes_tax(self):
        """Order total includes tax calculation."""
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        order = Order.query.first()
        # 25.00 subtotal + 0 shipping (>$50 threshold not met so $9.99) + 8% tax
        # subtotal=25, shipping=9.99, tax=25*0.08=2.00, total=36.99
        self.assertAlmostEqual(order.total_price, 36.99, places=2)

    def test_order_has_payment_status(self):
        """Order created via checkout has payment_status='paid'."""
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        order = Order.query.first()
        self.assertEqual(order.payment_status, 'paid')
        self.assertEqual(order.payment_method, 'card')
        self.assertEqual(order.status, 'confirmed')

    def test_order_has_shipping_address(self):
        """Order stores shipping address."""
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        order = Order.query.first()
        self.assertIn('123 Test Street', order.shipping_address)
        self.assertIn('San Francisco', order.shipping_address)

    def test_checkout_card_last4_shown(self):
        """Flash message shows last 4 digits of card."""
        resp = self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        self.assertIn(b'1111', resp.data)

    def test_checkout_invalid_expiry_format(self):
        """Checkout rejects invalid expiry format."""
        data = self._checkout_data()
        data['card_expiry'] = '1228'  # missing /
        resp = self.client.post('/checkout', data=data, follow_redirects=True)
        self.assertIn(b'MM/YY', resp.data)

    def test_checkout_invalid_cvv(self):
        """Checkout rejects invalid CVV."""
        data = self._checkout_data()
        data['card_cvv'] = '12'  # too short
        resp = self.client.post('/checkout', data=data, follow_redirects=True)
        self.assertIn(b'3 or 4 digits', resp.data)

    def test_view_orders(self):
        """User can view their order list."""
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        resp = self.client.get('/orders')
        self.assertEqual(resp.status_code, 200)

    def test_view_order_detail(self):
        """User can view order detail."""
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        order = Order.query.first()
        resp = self.client.get(f'/order/{order.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Order Test Item', resp.data)

    def test_checkout_empty_cart(self):
        """Checkout with empty cart redirects."""
        # Clear cart first
        cart_item = CartItem.query.first()
        self.client.post(f'/cart/remove/{cart_item.id}', follow_redirects=True)
        resp = self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        self.assertIn(b'cart is empty', resp.data)

    def test_order_status_default_confirmed(self):
        """Orders via payment gateway default to 'confirmed'."""
        self.client.post('/checkout', data=self._checkout_data(), follow_redirects=True)
        order = Order.query.first()
        self.assertEqual(order.status, 'confirmed')


# ─────────────────────────────────────────────
# 6. ADMIN DASHBOARD & USER MANAGEMENT TESTS
# ─────────────────────────────────────────────
class TestAdminPanel(BaseTestCase):

    def test_admin_dashboard_loads(self):
        """Admin dashboard loads with stats."""
        self.login_admin()
        resp = self.client.get('/admin/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Admin Dashboard', resp.data)

    def test_admin_can_view_users(self):
        """Admin can view user list."""
        self.login_admin()
        self.register_user()  # logout happens implicitly during register
        self.login_admin()
        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_delete_user(self):
        """Admin can delete a user."""
        self.register_user()
        self.login_admin()
        user = User.query.filter_by(email='test@test.com').first()
        resp = self.client.post(f'/admin/users/delete/{user.id}', follow_redirects=True)
        self.assertIn(b'deleted', resp.data)
        self.assertIsNone(User.query.get(user.id))

    def test_admin_cannot_delete_self(self):
        """Admin cannot delete their own account."""
        self.login_admin()
        admin = User.query.filter_by(email='admin@shop.com').first()
        resp = self.client.post(f'/admin/users/delete/{admin.id}', follow_redirects=True)
        self.assertIn(b'cannot delete yourself', resp.data)

    def test_admin_can_view_all_orders(self):
        """Admin can view all orders."""
        self.login_admin()
        resp = self.client.get('/admin/orders')
        self.assertEqual(resp.status_code, 200)

    def test_admin_can_update_order_status(self):
        """Admin can update an order's status."""
        # Create an order first
        self.login_admin()
        self.create_product(name='Status Test', price=10.0, stock=5)
        self.client.get('/auth/logout')
        self.register_user()
        self.login_user()
        product = Product.query.filter_by(name='Status Test').first()
        self.client.post(f'/cart/add/{product.id}', follow_redirects=True)
        self.client.post('/checkout', data={
            'full_name': 'Test User',
            'address': '123 Test St',
            'city': 'SF',
            'state': 'CA',
            'zip_code': '94102',
            'phone': '5551234567',
            'cardholder_name': 'Test User',
            'card_number': '4111111111111111',
            'card_expiry': '12/28',
            'card_cvv': '123'
        }, follow_redirects=True)
        self.client.get('/auth/logout')

        # Admin updates order status
        self.login_admin()
        order = Order.query.first()
        resp = self.client.post(f'/admin/orders/{order.id}', data={
            'status': 'shipped'
        }, follow_redirects=True)
        self.assertIn(b'updated', resp.data)
        order = Order.query.first()
        self.assertEqual(order.status, 'shipped')


# ─────────────────────────────────────────────
# 7. ROLE-BASED ACCESS CONTROL TESTS
# ─────────────────────────────────────────────
class TestRoleAccess(BaseTestCase):

    def test_user_cannot_access_admin_dashboard(self):
        """Regular user gets 403 on admin routes."""
        self.register_user()
        self.login_user()
        resp = self.client.get('/admin/')
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_manage_products(self):
        """Regular user gets 403 on admin product management."""
        self.register_user()
        self.login_user()
        resp = self.client.get('/admin/products')
        self.assertEqual(resp.status_code, 403)

    def test_user_cannot_manage_users(self):
        """Regular user gets 403 on admin user management."""
        self.register_user()
        self.login_user()
        resp = self.client.get('/admin/users')
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_cannot_access_admin(self):
        """Anonymous user is redirected from admin routes."""
        resp = self.client.get('/admin/', follow_redirects=True)
        self.assertIn(b'Welcome Back', resp.data)  # redirected to login

    def test_anonymous_can_browse_products(self):
        """Anonymous users can view the home page and products."""
        resp = self.client.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'All Products', resp.data)


# ─────────────────────────────────────────────
# 8. PRODUCT BROWSING TESTS (User)
# ─────────────────────────────────────────────
class TestProductBrowsing(BaseTestCase):

    def test_home_page_shows_products(self):
        """Home page shows in-stock products."""
        self.login_admin()
        self.create_product(name='Visible Product', stock=5)
        self.create_product(name='Hidden Product', stock=0)
        self.client.get('/auth/logout')

        resp = self.client.get('/')
        self.assertIn(b'Visible Product', resp.data)
        self.assertNotIn(b'Hidden Product', resp.data)

    def test_product_detail_page(self):
        """Product detail page shows product info."""
        self.login_admin()
        self.create_product(name='Detail Product', description='Great product')
        self.client.get('/auth/logout')

        product = Product.query.filter_by(name='Detail Product').first()
        resp = self.client.get(f'/product/{product.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Detail Product', resp.data)
        self.assertIn(b'Great product', resp.data)

    def test_product_404(self):
        """Non-existent product returns 404."""
        resp = self.client.get('/product/9999')
        self.assertEqual(resp.status_code, 404)


# ─────────────────────────────────────────────
# 9. CATEGORY SYSTEM TESTS
# ─────────────────────────────────────────────
class TestCategorySystem(BaseTestCase):

    def test_admin_can_create_category(self):
        """Admin can create a category."""
        self.login_admin()
        resp = self.create_category(name='Vintage Collectibles', icon='🏺')
        self.assertIn(b'created', resp.data)
        cat = Category.query.filter_by(name='Vintage Collectibles').first()
        self.assertIsNotNone(cat)
        self.assertEqual(cat.slug, 'vintage-collectibles')

    def test_admin_can_view_categories(self):
        """Admin can view category list."""
        self.login_admin()
        resp = self.client.get('/admin/categories')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Electronics', resp.data)  # seeded category

    def test_admin_can_edit_category(self):
        """Admin can edit a category."""
        self.login_admin()
        self.create_category(name='Editable Cat')
        cat = Category.query.filter_by(name='Editable Cat').first()
        resp = self.client.post(f'/admin/categories/edit/{cat.id}', data={
            'name': 'Edited Category',
            'icon': '💻',
            'description': 'Updated'
        }, follow_redirects=True)
        self.assertIn(b'updated', resp.data)

    def test_admin_can_delete_category(self):
        """Admin can delete a category."""
        self.login_admin()
        self.create_category(name='Temp Category')
        cat = Category.query.filter_by(name='Temp Category').first()
        resp = self.client.post(f'/admin/categories/delete/{cat.id}', follow_redirects=True)
        self.assertIn(b'deleted', resp.data)

    def test_category_filter_on_home(self):
        """Home page filters products by category."""
        self.login_admin()
        self.create_category(name='TestBooks', icon='📚')
        cat = Category.query.filter_by(name='TestBooks').first()
        self.create_product(name='Python Book', stock=5, category_id=cat.id)
        self.create_product(name='Unrelated Item', stock=5, category_id=0)
        self.client.get('/auth/logout')

        resp = self.client.get(f'/?category={cat.slug}')
        self.assertIn(b'Python Book', resp.data)
        self.assertNotIn(b'Unrelated Item', resp.data)

    def test_category_page_loads(self):
        """Category page via slug works."""
        self.login_admin()
        self.create_category(name='TestFashion', icon='👗')
        cat = Category.query.filter_by(name='TestFashion').first()
        self.create_product(name='Jacket', stock=10, category_id=cat.id)
        self.client.get('/auth/logout')

        resp = self.client.get(f'/category/{cat.slug}')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Jacket', resp.data)

    def test_product_with_category_badge(self):
        """Product shows category badge on home page."""
        self.login_admin()
        self.create_category(name='TestGaming', icon='🎮')
        cat = Category.query.filter_by(name='TestGaming').first()
        self.create_product(name='PS5', stock=5, category_id=cat.id)
        self.client.get('/auth/logout')

        resp = self.client.get('/')
        self.assertIn(b'TestGaming', resp.data)

    def test_seeded_categories_exist(self):
        """Categories are seeded on startup."""
        # The app seeds categories in create_app
        count = Category.query.count()
        self.assertGreaterEqual(count, 8)

    def test_seeded_products_exist(self):
        """Products are seeded on startup."""
        count = Product.query.count()
        self.assertGreaterEqual(count, 30)


# ─────────────────────────────────────────────
# 10. SEARCH TESTS
# ─────────────────────────────────────────────
class TestSearch(BaseTestCase):

    def test_search_finds_product_by_name(self):
        """Search returns products matching name."""
        self.login_admin()
        self.create_product(name='Wireless Mouse', stock=10)
        self.client.get('/auth/logout')

        resp = self.client.get('/search?q=Wireless')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'Wireless Mouse', resp.data)

    def test_search_finds_product_by_description(self):
        """Search returns products matching description."""
        self.login_admin()
        self.create_product(name='Gadget X', stock=10, description='ergonomic bluetooth device')
        self.client.get('/auth/logout')

        resp = self.client.get('/search?q=bluetooth')
        self.assertIn(b'Gadget X', resp.data)

    def test_search_empty_query_redirects(self):
        """Empty search redirects to home."""
        resp = self.client.get('/search?q=', follow_redirects=False)
        self.assertEqual(resp.status_code, 302)

    def test_search_no_results(self):
        """Search with no matches shows no products."""
        resp = self.client.get('/search?q=xyznonexistent12345')
        self.assertIn(b'No products found', resp.data)

    def test_home_search_filter(self):
        """Home page search filter works via query param."""
        self.login_admin()
        self.create_product(name='Blue Headphones', stock=5)
        self.create_product(name='Red Shoes', stock=5)
        self.client.get('/auth/logout')

        resp = self.client.get('/?q=Headphones')
        self.assertIn(b'Blue Headphones', resp.data)
        self.assertNotIn(b'Red Shoes', resp.data)


# ─────────────────────────────────────────────
# RUN TESTS
# ─────────────────────────────────────────────
if __name__ == '__main__':
    # Run with verbose output
    unittest.main(verbosity=2)
