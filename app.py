from flask import Flask
from config import Config
from extensions import db, login_manager, migrate, csrf
from models import User, Product, CartItem, Order, OrderItem, Category


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.user import user_bp
    from routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    # Create tables and seed data
    with app.app_context():
        db.create_all()
        _seed_admin()
        _seed_categories()
        _seed_products()

    return app


def _seed_admin():
    """Create a default admin user if none exists."""
    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            name='Admin',
            email='admin@shop.com',
            role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)
        db.session.commit()
        print('✅ Default admin created: admin@shop.com / admin123')


def _seed_categories():
    """Create default product categories if none exist."""
    if Category.query.count() > 0:
        return

    categories = [
        Category(name='Electronics', slug='electronics',
                 description='Smartphones, laptops, headphones, and cutting-edge gadgets.',
                 icon='📱'),
        Category(name='Fashion', slug='fashion',
                 description='Trendy clothing, footwear, and accessories for all.',
                 icon='👗'),
        Category(name='Home & Kitchen', slug='home-kitchen',
                 description='Furniture, appliances, décor, and kitchen essentials.',
                 icon='🏠'),
        Category(name='Books', slug='books',
                 description='Bestsellers, fiction, non-fiction, and educational reads.',
                 icon='📚'),
        Category(name='Sports & Outdoors', slug='sports-outdoors',
                 description='Fitness gear, activewear, and outdoor adventure equipment.',
                 icon='⚽'),
        Category(name='Beauty & Personal Care', slug='beauty',
                 description='Skincare, makeup, haircare, and grooming products.',
                 icon='💄'),
        Category(name='Gaming & Toys', slug='gaming-toys',
                 description='Video games, consoles, board games, and toys for all ages.',
                 icon='🎮'),
        Category(name='Grocery & Gourmet', slug='grocery',
                 description='Premium food, beverages, organic produce, and kitchen staples.',
                 icon='🛒'),
    ]
    db.session.add_all(categories)
    db.session.commit()
    print('✅ 8 categories seeded.')


def _seed_products():
    """Create sample products across categories if none exist."""
    if Product.query.count() > 0:
        return

    cats = {c.slug: c.id for c in Category.query.all()}

    products = [
        # ── Electronics ──
        Product(name='iPhone 16 Pro Max', price=1199.00, stock=25,
                category_id=cats.get('electronics'), is_featured=True,
                description='6.9-inch Super Retina XDR display, A18 Pro chip, 48MP camera system with 5× Optical Zoom. Available in Desert Titanium.'),
        Product(name='MacBook Air M3', price=1099.00, stock=18,
                category_id=cats.get('electronics'), is_featured=True,
                description='13.6-inch Liquid Retina display, Apple M3 chip, 18-hour battery life, 8GB unified memory, 256GB SSD.'),
        Product(name='Sony WH-1000XM5 Headphones', price=349.99, stock=40,
                category_id=cats.get('electronics'), is_featured=False,
                description='Industry-leading noise cancellation, 30-hour battery, Hi-Res Audio, multipoint connection, ultra-comfortable design.'),
        Product(name='Samsung Galaxy S25 Ultra', price=1299.99, stock=15,
                category_id=cats.get('electronics'), is_featured=True,
                description='6.8-inch QHD+ Dynamic AMOLED, Snapdragon 8 Elite, 200MP camera, S Pen included, titanium frame.'),
        Product(name='iPad Pro 13-inch M4', price=1299.00, stock=12,
                category_id=cats.get('electronics'),
                description='Ultra Retina XDR OLED display, M4 chip, Thunderbolt / USB 4, Face ID, Apple Pencil Pro support.'),

        # ── Fashion ──
        Product(name='Classic Leather Jacket', price=189.99, stock=30,
                category_id=cats.get('fashion'), is_featured=True,
                description='Genuine lambskin leather, satin lining, zippered pockets, slim-fit design. Timeless biker style.'),
        Product(name='Running Sneakers Air Max', price=129.99, stock=50,
                category_id=cats.get('fashion'),
                description='Lightweight mesh upper, visible Air cushioning, rubber outsole for traction. Available in 6 colours.'),
        Product(name='Cashmere Wool Scarf', price=79.99, stock=60,
                category_id=cats.get('fashion'),
                description='100% pure Mongolian cashmere, ultra-soft, 200cm × 70cm, hand-finished edges. Perfect for winter.'),
        Product(name='Slim-Fit Chino Pants', price=59.99, stock=100,
                category_id=cats.get('fashion'),
                description='Stretch cotton twill, tapered leg, flat front, machine washable. Sizes 28–40.'),

        # ── Home & Kitchen ──
        Product(name='Dyson V15 Detect Vacuum', price=749.99, stock=10,
                category_id=cats.get('home-kitchen'), is_featured=True,
                description='Laser reveals microscopic dust, 60-min runtime, HEPA filtration, LCD counts particles in real time.'),
        Product(name='KitchenAid Stand Mixer', price=449.99, stock=20,
                category_id=cats.get('home-kitchen'),
                description='5-quart stainless steel bowl, 10 speeds, tilt-head design, includes flat beater, dough hook, and wire whip.'),
        Product(name='Smart LED Desk Lamp', price=49.99, stock=80,
                category_id=cats.get('home-kitchen'),
                description='Touch-control dimming, USB charging port, 5 colour temperatures, memory function, foldable arm.'),
        Product(name='Ceramic Non-Stick Cookware Set', price=199.99, stock=25,
                category_id=cats.get('home-kitchen'),
                description='12-piece set, toxin-free ceramic coating, tempered glass lids, oven-safe up to 450°F.'),

        # ── Books ──
        Product(name='Atomic Habits by James Clear', price=16.99, stock=120,
                category_id=cats.get('books'), is_featured=True,
                description='An easy & proven way to build good habits & break bad ones. #1 New York Times bestseller.'),
        Product(name='The Midnight Library by Matt Haig', price=14.99, stock=90,
                category_id=cats.get('books'),
                description='Between life and death there is a library. A novel about all the choices that go into a life well lived.'),
        Product(name='Clean Code by Robert C. Martin', price=39.99, stock=45,
                category_id=cats.get('books'),
                description='A handbook of agile software craftsmanship. Essential reading for professional programmers.'),
        Product(name='Sapiens by Yuval Noah Harari', price=18.99, stock=75,
                category_id=cats.get('books'),
                description='A brief history of humankind, exploring how biology and history have defined us.'),

        # ── Sports & Outdoors ──
        Product(name='Yoga Mat Premium 6mm', price=34.99, stock=150,
                category_id=cats.get('sports-outdoors'),
                description='Non-slip surface, eco-friendly TPE material, alignment lines, carrying strap included.'),
        Product(name='Adjustable Dumbbell Set 25kg', price=249.99, stock=20,
                category_id=cats.get('sports-outdoors'), is_featured=False,
                description='Quick-adjust weight from 2.5–25kg, replaces 8 pairs of dumbbells, ergonomic grip.'),
        Product(name='Osprey Atmos AG 65L Backpack', price=299.99, stock=15,
                category_id=cats.get('sports-outdoors'),
                description='Anti-Gravity suspension, adjustable torso, integrated rain cover, 65-litre capacity.'),
        Product(name='Hydro Flask 32oz Water Bottle', price=44.99, stock=200,
                category_id=cats.get('sports-outdoors'),
                description='Double-wall vacuum insulation, keeps cold 24h/hot 12h, BPA-free, powder-coated grip.'),

        # ── Beauty & Personal Care ──
        Product(name='La Roche-Posay Sunscreen SPF 50', price=29.99, stock=100,
                category_id=cats.get('beauty'),
                description='Broad-spectrum UVA/UVB protection, oil-free, non-comedogenic, safe for sensitive skin.'),
        Product(name='Dyson Airwrap Multi-Styler', price=599.99, stock=8,
                category_id=cats.get('beauty'), is_featured=True,
                description='Coanda airflow technology, 6 attachments, curl, wave, smooth, and dry without extreme heat.'),
        Product(name='Vitamin C Brightening Serum', price=24.99, stock=150,
                category_id=cats.get('beauty'),
                description='20% L-Ascorbic Acid, hyaluronic acid, ferulic acid. Brightens, firms, and evens skin tone.'),
        Product(name='Electric Toothbrush Pro', price=89.99, stock=60,
                category_id=cats.get('beauty'),
                description='Sonic technology, 5 brushing modes, smart timer, USB-C charging, includes 3 brush heads.'),

        # ── Gaming & Toys ──
        Product(name='PlayStation 5 Slim', price=449.99, stock=12,
                category_id=cats.get('gaming-toys'), is_featured=True,
                description='4K gaming at up to 120fps, ultra-fast SSD, Tempest 3D AudioTech, DualSense wireless controller.'),
        Product(name='Nintendo Switch OLED', price=349.99, stock=30,
                category_id=cats.get('gaming-toys'),
                description='7-inch OLED screen, wide adjustable stand, wired LAN port, 64GB internal storage.'),
        Product(name='LEGO Creator Expert Set', price=129.99, stock=35,
                category_id=cats.get('gaming-toys'),
                description='2,500+ pieces, detailed architectural build, ages 16+, display-worthy collectible item.'),
        Product(name='Razer BlackWidow V4 Keyboard', price=169.99, stock=40,
                category_id=cats.get('gaming-toys'),
                description='Mechanical gaming keyboard, Razer Green switches, per-key RGB, magnetic wrist rest.'),

        # ── Grocery & Gourmet ──
        Product(name='Blue Mountain Coffee Beans 500g', price=34.99, stock=80,
                category_id=cats.get('grocery'),
                description='Single-origin Jamaican Blue Mountain, medium roast, whole bean, rich and smooth flavour.'),
        Product(name='Organic Manuka Honey UMF 15+', price=59.99, stock=40,
                category_id=cats.get('grocery'), is_featured=False,
                description='Raw, certified UMF 15+ from New Zealand, creamy texture, antibacterial properties.'),
        Product(name='Artisan Dark Chocolate Collection', price=29.99, stock=100,
                category_id=cats.get('grocery'),
                description='24-piece box, 70% cacao single-origin bars from Ecuador, Peru, and Madagascar.'),
        Product(name='Italian Extra Virgin Olive Oil 1L', price=22.99, stock=120,
                category_id=cats.get('grocery'),
                description='Cold-pressed from Sicilian Nocellara olives, DOP certified, fruity with peppery finish.'),
    ]

    db.session.add_all(products)
    db.session.commit()
    print(f'✅ {len(products)} products seeded across categories.')


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
