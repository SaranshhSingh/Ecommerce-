from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from extensions import db
from models import Product, CartItem, Order, OrderItem, Category
from forms import UpdateCartForm, CheckoutForm

user_bp = Blueprint('user', __name__, url_prefix='/')


@user_bp.route('/')
def home():
    category_slug = request.args.get('category', '')
    search_q = request.args.get('q', '')

    query = Product.query.filter(Product.stock > 0)

    if category_slug:
        cat = Category.query.filter_by(slug=category_slug).first()
        if cat:
            query = query.filter(Product.category_id == cat.id)

    if search_q:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search_q}%'),
                Product.description.ilike(f'%{search_q}%')
            )
        )

    products = query.all()
    categories = Category.query.order_by(Category.name).all()
    featured = Product.query.filter(Product.is_featured == True, Product.stock > 0).limit(6).all()
    new_arrivals = Product.query.filter(Product.stock > 0).order_by(Product.created_at.desc()).limit(6).all()

    return render_template('user/home.html',
                           products=products,
                           categories=categories,
                           featured=featured,
                           new_arrivals=new_arrivals,
                           active_category=category_slug,
                           search_query=search_q)


@user_bp.route('/search')
def search():
    q = request.args.get('q', '').strip()
    if not q:
        return redirect(url_for('user.home'))
    products = Product.query.filter(
        Product.stock > 0,
        db.or_(
            Product.name.ilike(f'%{q}%'),
            Product.description.ilike(f'%{q}%')
        )
    ).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template('user/search_results.html',
                           products=products,
                           query=q,
                           categories=categories)


@user_bp.route('/category/<slug>')
def category(slug):
    cat = Category.query.filter_by(slug=slug).first_or_404()
    products = Product.query.filter(Product.category_id == cat.id, Product.stock > 0).all()
    categories = Category.query.order_by(Category.name).all()
    return render_template('user/home.html',
                           products=products,
                           categories=categories,
                           featured=[],
                           new_arrivals=[],
                           active_category=slug,
                           search_query='',
                           current_category=cat)


@user_bp.route('/product/<int:product_id>')
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    related = Product.query.filter(
        Product.category_id == product.category_id,
        Product.id != product.id,
        Product.stock > 0
    ).limit(4).all() if product.category_id else []
    return render_template('user/product_detail.html', product=product, related=related)


@user_bp.route('/cart')
@login_required
def cart():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()
    total = sum(item.product.price * item.quantity for item in cart_items)
    return render_template('user/cart.html', cart_items=cart_items, total=total)


@user_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    product = Product.query.get_or_404(product_id)

    if product.stock <= 0:
        flash('Product is out of stock.', 'danger')
        return redirect(url_for('user.home'))

    cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id).first()

    if cart_item:
        if cart_item.quantity < product.stock:
            cart_item.quantity += 1
            flash(f'Updated {product.name} quantity in cart.', 'success')
        else:
            flash('Cannot add more than available stock.', 'warning')
    else:
        cart_item = CartItem(user_id=current_user.id, product_id=product_id, quantity=1)
        db.session.add(cart_item)
        flash(f'{product.name} added to cart!', 'success')

    db.session.commit()
    return redirect(url_for('user.home'))


@user_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    if cart_item.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user.cart'))

    form = UpdateCartForm()
    if form.validate_on_submit():
        new_qty = form.quantity.data
        if new_qty > cart_item.product.stock:
            flash('Quantity exceeds available stock.', 'warning')
        else:
            cart_item.quantity = new_qty
            db.session.commit()
            flash('Cart updated.', 'success')

    return redirect(url_for('user.cart'))


@user_bp.route('/cart/remove/<int:item_id>', methods=['POST'])
@login_required
def remove_from_cart(item_id):
    cart_item = CartItem.query.get_or_404(item_id)

    if cart_item.user_id != current_user.id:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user.cart'))

    db.session.delete(cart_item)
    db.session.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('user.cart'))


@user_bp.route('/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    cart_items = CartItem.query.filter_by(user_id=current_user.id).all()

    if not cart_items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('user.cart'))

    subtotal = sum(item.product.price * item.quantity for item in cart_items)
    shipping = 0.00 if subtotal >= 50 else 9.99
    tax = round(subtotal * 0.08, 2)  # 8% tax
    total = round(subtotal + shipping + tax, 2)

    form = CheckoutForm()

    if form.validate_on_submit():
        # Build address string
        shipping_address = f"{form.full_name.data}\n{form.address.data}\n{form.city.data}, {form.state.data} {form.zip_code.data}\nPhone: {form.phone.data}"

        # Create order
        order = Order(
            user_id=current_user.id,
            total_price=total,
            status='confirmed',
            payment_method='card',
            payment_status='paid',
            shipping_address=shipping_address,
            billing_address=shipping_address
        )
        db.session.add(order)
        db.session.flush()

        for item in cart_items:
            if item.quantity > item.product.stock:
                flash(f'Not enough stock for {item.product.name}.', 'danger')
                db.session.rollback()
                return redirect(url_for('user.cart'))

            order_item = OrderItem(
                order_id=order.id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)
            item.product.stock -= item.quantity

        # Clear cart
        for item in cart_items:
            db.session.delete(item)

        db.session.commit()

        # Mask card number for display
        card_last4 = form.card_number.data.replace(' ', '')[-4:]
        flash(f'✅ Payment successful! Order #{order.id} confirmed. Card ending in •••• {card_last4}. Total: ${total:.2f}', 'success')
        return redirect(url_for('user.order_detail', order_id=order.id))

    return render_template('user/checkout.html',
                           form=form,
                           cart_items=cart_items,
                           subtotal=subtotal,
                           shipping=shipping,
                           tax=tax,
                           total=total)


@user_bp.route('/orders')
@login_required
def orders():
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('user/orders.html', orders=user_orders)


@user_bp.route('/order/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.user_id != current_user.id and not current_user.is_admin:
        flash('Unauthorized.', 'danger')
        return redirect(url_for('user.orders'))
    return render_template('user/order_detail.html', order=order)
