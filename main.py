"""
Resources used to write this code:
render_form() n.d., Grey Li, accessed 22 May 2026,
<https://bootstrap-flask.readthedocs.io/en/stable/macros/#render-form>

Day 69 L529 - Register new users (SQL Alchemy 3.1) 2024, TheMuellenator,
accessed 22 May 2026, <https://gist.github.com/TheMuellenator/93e0c714ee70390462271856b42f0c48>

Flask-Login n.d., accessed 22 May 2026,
<https://flask-login.readthedocs.io/en/latest/>

Simple Flashing n.d., Pallets, accessed 22 May 2026,
<https://flask.palletsprojects.com/en/stable/patterns/flashing/#simple-flashing>

If n.d., Pallets, accessed 22 May 2026,
<https://jinja.palletsprojects.com/en/stable/templates/#if>

Day 69 L529 05 - Updating the Nav bar n.d., TheMuellenator,
accessed 22 May 2026, <https://gist.github.com/TheMuellenator/b78e880809328e21a44e3947e963cf76>

Login Required Decorator n.d., Pallets, accessed 24 May 2026,
<https://flask.palletsprojects.com/en/stable/patterns/viewdecorators/#login-required-decorator>

flask.abort() n.d., Pallets, accessed 24 May 2026,
<https://flask.palletsprojects.com/en/stable/api/#flask.abort>

Day 69 L530 02 - Protect Routes with @admin_only decorator 2023, ricardolousada, accessed 24 May 2024,
<https://gist.github.com/TheMuellenator/933dcf773a50402c6219bb90b37b7875?permalink_comment_id=4693437#gistcomment-4693437>

Basic Relationship Patterns n.d., the SQLAlchemy authors and contributors,
accessed 24 May 2026, <https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html>

The Flask Mega-Tutorial, Part VI: Profile Page and Avatars n.d., Miguel Grinberg, accessed 24 May 2026,
<https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-vi-profile-page-and-avatars>

Basic Usage n.d., Grey Li, accessed 24 May 2026,
<https://flask-ckeditor.readthedocs.io/en/latest/basic.html>
"""

import os
from dotenv import load_dotenv
from datetime import date
from flask import Flask, abort, render_template, redirect, url_for, flash
from flask_bootstrap import Bootstrap5
from flask_ckeditor import CKEditor
from flask_ckeditor.utils import cleanify
from flask_login import UserMixin, login_user, LoginManager, current_user, logout_user, login_required
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Text, ForeignKey
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash
# from flask_gravatar import Gravatar  # Not compatible with latest Flask

# Alternative method to Flask-Gravatar
from hashlib import sha256  # Used to hash the mail address for Gravatar

# Import your forms from the forms.py
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm

'''
Make sure the required packages are installed: 
Open the Terminal in PyCharm (bottom left). 

On Windows type:
python -m pip install -r requirements.txt

On MacOS type:
pip3 install -r requirements.txt

This will install the packages from the requirements.txt for this project.
'''

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_KEY')
ckeditor = CKEditor(app)
Bootstrap5(app)

# TODO: Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)

# CREATE DATABASE
class Base(DeclarativeBase):
    pass


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_URI", "sqlite:///posts.db")
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# CONFIGURE TABLES
class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    subtitle: Mapped[str] = mapped_column(String(250), nullable=False)
    date: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="posts")
    comments: Mapped[list["Comment"]] = relationship(back_populates="parent_post")


# TODO: Create a User table for all your registered users. 
class User(UserMixin, db.Model):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String(1000), nullable=False)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    posts: Mapped[list["BlogPost"]] = relationship(back_populates="author")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")

    def get_id(self):
        return str(self.id)

    def avatar(self, size: int = 80):
        # digest = md5(self.email.lower().encode("utf-8")).hexdigest()
        hash = sha256(self.email.strip().lower().encode("utf-8")).hexdigest()
        return f'https://www.gravatar.com/avatar/{hash}?d=identicon&s={size}'


class Comment(db.Model):
    __tablename__ = "comments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    text: Mapped[str] = mapped_column(String(1000), nullable=False)
    author_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    author: Mapped["User"] = relationship(back_populates="comments")
    post_id: Mapped[int] = mapped_column(ForeignKey("blog_posts.id"))
    parent_post: Mapped["BlogPost"] = relationship(back_populates="comments")


@login_manager.user_loader
def load_user(user_id: str):
    if not user_id:
        return None

    query_result = db.session.execute(db.select(User).where(User.id == user_id))
    loaded_user = query_result.scalar()

    return loaded_user


with app.app_context():
    db.create_all()


def admin_only(function):
    @wraps(function)
    def check_if_user_is_admin(*args, **kwargs):
        if current_user.is_authenticated and current_user.id == 1:
            return function(*args, **kwargs)

        return abort(403)

    return check_if_user_is_admin


# TODO: Use Werkzeug to hash the user's password when creating a new user.
@app.route('/register', methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        query_result = db.session.execute(db.select(User).where(User.email == register_form.email.data))
        user_in_database = query_result.scalar()

        if user_in_database:
            flash("You've already signed up with that email, please log in instead!")

            return redirect(url_for("login"))

        hashed_password = generate_password_hash(register_form.password.data, method="pbkdf2:sha256", salt_length=8)

        user_to_register = User(
            email=register_form.email.data,
            password=hashed_password,
            name=register_form.name.data,
        )
        db.session.add(user_to_register)
        db.session.commit()

        login_user(user_to_register)

        return redirect(url_for("get_all_posts"))

    return render_template("register.html", form=register_form, current_user=current_user)


# TODO: Retrieve a user from the database based on their email.
@app.route('/login', methods=["GET", "POST"])
def login():
    login_form = LoginForm()

    if login_form.validate_on_submit():
        query_result = db.session.execute(db.select(User).where(User.email == login_form.email.data))
        user = query_result.scalar()

        if not user:
            flash("Unknown email, please try again or create an account!")
        elif not check_password_hash(user.password, login_form.password.data):
            flash("Incorrect password, please try again!")
        else:
            login_user(user)

            return redirect(url_for("get_all_posts"))

    return render_template("login.html", form=login_form, current_user=current_user)


@app.route('/logout')
@login_required
def logout():
    logout_user()

    return redirect(url_for('get_all_posts'))


@app.route('/')
def get_all_posts():
    result = db.session.execute(db.select(BlogPost))
    posts = result.scalars().all()

    return render_template("index.html", all_posts=posts, current_user=current_user)


# TODO: Allow logged-in users to comment on posts
@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = db.get_or_404(BlogPost, post_id)

    if comment_form.validate_on_submit():
        if not current_user.is_authenticated:
            flash("You need to login or register to comment.")

            return redirect(url_for("login"))
        else:
            text = cleanify(comment_form.body.data)

            comment = Comment(
                text=text,
                author_id=current_user.id,
                post_id=post_id
            )
            db.session.add(comment)
            db.session.commit()

    return render_template(
        "post.html",
        post=requested_post,
        current_user=current_user,
        form=comment_form
    )


# TODO: Use a decorator so only an admin user can create a new post
@app.route("/new-post", methods=["GET", "POST"])
@admin_only
def add_new_post():
    form = CreatePostForm()

    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()

        return redirect(url_for("get_all_posts"))

    return render_template("make-post.html", form=form, current_user=current_user)


# TODO: Use a decorator so only an admin user can edit a post
@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_only
def edit_post(post_id):
    post = db.get_or_404(BlogPost, post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        author=post.author,
        body=post.body
    )

    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author = current_user
        post.body = edit_form.body.data
        db.session.commit()

        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, is_edit=True, current_user=current_user)


# TODO: Use a decorator so only an admin user can delete a post
@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = db.get_or_404(BlogPost, post_id)
    db.session.delete(post_to_delete)
    db.session.commit()

    return redirect(url_for('get_all_posts'))


@app.route("/about")
def about():
    return render_template("about.html", current_user=current_user)


@app.route("/contact")
def contact():
    return render_template("contact.html", current_user=current_user)


if __name__ == "__main__":
    app.run(debug=True, port=5002)
