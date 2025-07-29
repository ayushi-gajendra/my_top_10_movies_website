from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, Float
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests
from dotenv import load_dotenv
import os



# ---------------------- Load Environment ---------------------- #
load_dotenv()
API_KEY = os.getenv("API_KEY")

# ---------------------- Flask App Setup ---------------------- #
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///my_movies.db"

Bootstrap5(app)

# ---------------------- DATABASE ---------------------- #

class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Movie(db.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    year: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    rating: Mapped[float] = mapped_column(Float, nullable=True)
    ranking: Mapped[int] = mapped_column(Integer, nullable=True)
    review: Mapped[str] = mapped_column(String(250), nullable=True)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


with app.app_context():
    db.create_all()


# ---------------------- FORMS ---------------------- #

class MovieForm(FlaskForm):
    new_rating = StringField("Your Rating Out of 10", validators=[DataRequired()])
    new_review = StringField("Your Review", validators=[DataRequired()])
    submit = SubmitField('Done')


class DeleteForm(FlaskForm):
    sure = SubmitField('Yes')
    not_sure = SubmitField('No')


class AddForm(FlaskForm):
    title = StringField("Movie Title")
    submit = SubmitField("Search Movie")


# ---------------------- ROUTES ---------------------- #

@app.route("/")
def home():
    result = db.session.execute(db.select(Movie).order_by(Movie.rating))
    my_movies = result.scalars().all()

    rank = 1
    for movie in reversed(my_movies):
        movie.ranking = rank
        rank += 1

    db.session.commit()
    return render_template("index.html", movies=my_movies)


@app.route("/delete", methods=["GET", "POST"])
def delete_movie():
    form = DeleteForm()
    movie_id = request.args.get("movie_id")
    movie_to_delete = db.get_or_404(Movie, movie_id)

    if form.validate_on_submit():
        if form.sure.data:
            db.session.delete(movie_to_delete)
            db.session.commit()
        return redirect(url_for("home"))

    return render_template("delete.html", form=form, title=movie_to_delete.title)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = AddForm()
    if form.validate_on_submit():
        movie = form.title.data
        url_for_movie_search = "https://api.themoviedb.org/3/search/movie"
        params = {
            "api_key": API_KEY,
            "query": movie,
        }
        response = requests.get(url_for_movie_search, params=params)
        data = response.json()
        api_data = data["results"]
        return render_template("select.html", data=api_data)

    return render_template("add.html", form=form)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    form = MovieForm()
    movie_id = request.args.get("movie_id")
    movie_to_update = db.get_or_404(Movie, movie_id)

    if form.validate_on_submit():
        movie_to_update.rating = form.new_rating.data
        movie_to_update.review = form.new_review.data
        db.session.commit()
        return redirect(url_for("home"))

    return render_template("edit.html", form=form, title=movie_to_update.title)


@app.route("/find")
def find():
    movie_id = request.args.get("movie_id")
    url_for_movie_select = "https://api.themoviedb.org/3/movie"
    params = {
        "api_key": API_KEY,
    }

    response = requests.get(f"{url_for_movie_select}/{movie_id}", params=params)
    data = response.json()

    poster_path = data.get("poster_path")
    img_url = f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "https://via.placeholder.com/500x750?text=No+Image"

    movie_to_add = Movie(
        title=data["title"],
        year=data["release_date"].split("-")[0],
        description=data["overview"],
        img_url=img_url
    )

    db.session.add(movie_to_add)
    db.session.commit()
    return redirect(url_for("edit", movie_id=movie_to_add.id))


# ---------------------- RUN ---------------------- #

if __name__ == '__main__':
    app.run(debug=True)