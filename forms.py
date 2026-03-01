from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField, FloatField, IntegerField,
                     TextAreaField, SelectField, BooleanField)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange, ValidationError, Optional, Regexp
from models import User


class RegistrationForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different email.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')


class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired(), Length(max=200)])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField('Description')
    stock = IntegerField('Stock', validators=[DataRequired(), NumberRange(min=0)])
    category_id = SelectField('Category', coerce=int, validators=[Optional()])
    is_featured = BooleanField('Featured Product')
    submit = SubmitField('Save Product')


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(min=2, max=100)])
    description = TextAreaField('Description', validators=[Optional()])
    icon = StringField('Icon (emoji)', validators=[Optional(), Length(max=10)], default='📦')
    submit = SubmitField('Save Category')


class UpdateCartForm(FlaskForm):
    quantity = IntegerField('Quantity', validators=[DataRequired(), NumberRange(min=1)])
    submit = SubmitField('Update')


class OrderStatusForm(FlaskForm):
    status = SelectField('Status', choices=[
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered')
    ])
    submit = SubmitField('Update Status')


class CheckoutForm(FlaskForm):
    # Shipping Info
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    address = StringField('Street Address', validators=[DataRequired(), Length(min=5, max=200)])
    city = StringField('City', validators=[DataRequired(), Length(min=2, max=100)])
    state = StringField('State', validators=[DataRequired(), Length(min=2, max=100)])
    zip_code = StringField('ZIP Code', validators=[DataRequired(), Length(min=3, max=20)])
    phone = StringField('Phone Number', validators=[DataRequired(), Length(min=7, max=20)])

    # Payment Info
    cardholder_name = StringField('Cardholder Name', validators=[DataRequired(), Length(min=2, max=100)])
    card_number = StringField('Card Number', validators=[DataRequired(), Length(min=13, max=19)])
    card_expiry = StringField('Expiry (MM/YY)', validators=[
        DataRequired(),
        Regexp(r'^\d{2}/\d{2}$', message='Use MM/YY format')
    ])
    card_cvv = StringField('CVV', validators=[
        DataRequired(),
        Regexp(r'^\d{3,4}$', message='CVV must be 3 or 4 digits')
    ])

    submit = SubmitField('Place Order & Pay')
