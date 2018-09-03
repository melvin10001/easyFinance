from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required, lookup, usd, trade_shares, current_cash, get_shares
from helpers import get_history

# Configure application
app = Flask(__name__)

# Ensure responses aren't cached


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    sum_of_money = 0
    columns = ['Symbol', 'Name', 'Shares', 'Price', 'TOTAL']
    user_id = session["user_id"]
    cash_owned = current_cash(db, user_id)
    sum_of_money += cash_owned
    shares = get_shares(db, user_id)
    # Update ugly looking price and add TOTAL price
    for share in shares:
        total = share['sum(shares)'] * share['avg(price)']
        sum_of_money += total
        share["total"] = usd(total)
        share['avg(price)'] = usd(share['avg(price)'])

    return render_template("index.html", columns=columns, shares=shares,
                           cash=usd(cash_owned), total=usd(sum_of_money))


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":

        symbol = request.form.get("symbol")
        quantity = request.form.get("shares")
        user_id = session["user_id"]
        stock_info = lookup(symbol)
        if not quantity or not quantity.isnumeric():
            return apology("Bad quantity", 400)
        if stock_info is None:
            return apology("Bad symbol", 400)

        price = stock_info["price"]

        if trade_shares(user_id, symbol, quantity, price, db):
            return redirect("/")

        return apology("Can't afford", 400)

    return render_template("buy.html")


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    columns = ['Symbol', 'Shares', 'Price', 'Transacted']
    user_id = session["user_id"]
    shares = get_history(db, user_id)
    for entry in shares:
        entry['price'] = usd(entry['price'])

    return render_template("history.html", columns=columns, shares=shares)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""

    if request.method == "POST":

        symbol = request.form.get("symbol")

        stock_info = lookup(symbol)
        try:
            price = usd(stock_info["price"])
            return render_template("quoted.html", name=stock_info["name"], symbol=stock_info["symbol"],
                                   price=price)
        except TypeError:
            return apology("Bad Symbol", 400)
    return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":

        # Ensure username was submitted
        username = request.form.get("username")
        password = request.form.get("password")
        password_validated = request.form.get("confirmation")
        if not username:
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not password:
            return apology("must provide password", 400)
        # Ensure that repeated password is correct
        elif password != password_validated:
            return apology("password does not match", 400)
        else:
            hashed_password = generate_password_hash(
                password, method='pbkdf2:sha256', salt_length=8)
            insert_new_user = db.execute(
                "INSERT INTO users (username,hash) VALUES(:username, :hash)",
                username=username, hash=hashed_password)
            if not insert_new_user:
                return apology("following user exists", 400)
            # Login user and redirect

            session["user_id"] = insert_new_user
            return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    user_id = session["user_id"]

    if request.method == "POST":

        password = request.form.get("password")
        password_validated = request.form.get("confirmation")

        if not password:
            return apology("must provide password", 400)
        # Ensure that repeated password is correct
        elif password != password_validated:
            return apology("password does not match", 400)
        else:
            hashed_password = generate_password_hash(
                password, method='pbkdf2:sha256', salt_length=8)
            print(hashed_password)
            insert_new_user = db.execute(
                "UPDATE users SET hash=:hash WHERE id=:user_id", user_id=user_id,
                hash=hashed_password)
        return redirect("/")

    return render_template("change_password.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    user_id = session["user_id"]
    shares = get_shares(db, user_id)

    if request.method == "POST":

        symbol = request.form.get("symbol")
        quantity = request.form.get("shares")
        if not quantity or not quantity.isnumeric():
            return apology("Bad quantity", 400)
        quantity = int(quantity)
        for share in shares:
            if share["symbol"] == symbol and share["sum(shares)"] >= quantity:
                price = lookup(symbol)["price"]
                trade_shares(user_id, symbol, -quantity, price, db)

                return redirect("/")
            else:
                return apology("Wrong number of shares", 400)

    return render_template("sell.html", shares=shares)


def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
