import csv
import urllib.request
from flask import redirect, render_template, request, session
from functools import wraps

def current_cash(db,user_id):
    return db.execute("SELECT cash FROM users WHERE id = :id",
                          id=user_id)[0]['cash']

def get_shares(db,user_id):
    return db.execute("select symbol,sum(shares),avg(price) from portfolio where user_id=:user_id group by symbol",
                user_id=user_id)

def get_history(db,user_id):
    return db.execute("select symbol,shares, price, transaction_date from portfolio where user_id=:user_id",
                user_id=user_id)

def trade_shares(user_id, symbol,quantity,price, db):
    #print("STARTING")
    #print("PRICE RECEIVED: ", price)

    current_cash = db.execute("SELECT cash FROM users WHERE id = :id",
                          id=user_id)[0]['cash']
    total_price = int(quantity) * price

    #print("CASH BEING ADDED/REMOVED: ", total_price )

    if current_cash >= total_price:
        cash_remained = current_cash - total_price
        db.execute("UPDATE users set cash = :final_cash where id=:user_id",
                final_cash=cash_remained, user_id=user_id)
        db.execute("INSERT INTO portfolio VALUES (:user_id, :price,:symbol,CURRENT_TIMESTAMP,:shares)",
                user_id=user_id,price=price,symbol=symbol,shares=quantity)
        return True
    return False


def apology(message, code=400):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


def login_required(f):
    """
    Decorate routes to require login.

    http://flask.pocoo.org/docs/0.12/patterns/viewdecorators/
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""

    # reject symbol if it starts with caret
    if symbol.startswith("^"):
        return None

    # Reject symbol if it contains comma
    if "," in symbol:
        return None

    # Query Yahoo for quote
    # http://stackoverflow.com/a/21351911
    try:

        # GET CSV
        url = f"http://download.finance.yahoo.com/d/quotes.csv?f=snl1&s={symbol}"
        webpage = urllib.request.urlopen(url)

        # Read CSV
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

        # Parse first row
        row = next(datareader)

        # Ensure stock exists
        try:
            price = float(row[2])
        except:
            return None

        # Return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
        return {
            "name": row[1],
            "price": price,
            "symbol": row[0].upper()
        }

    except:
        pass

    # Query Alpha Vantage for quote instead
    # https://www.alphavantage.co/documentation/
    try:

        # GET CSV
        url = f"https://www.alphavantage.co/query?apikey=NAJXWIA8D6VN6A3K&datatype=csv&function=TIME_SERIES_INTRADAY&interval=1min&symbol={symbol}"
        webpage = urllib.request.urlopen(url)

        # Parse CSV
        datareader = csv.reader(webpage.read().decode("utf-8").splitlines())

        # Ignore first row
        next(datareader)

        # Parse second row
        row = next(datareader)

        # Ensure stock exists
        try:
            price = float(row[4])
        except:
            return None

        # Return stock's name (as a str), price (as a float), and (uppercased) symbol (as a str)
        return {
            "name": symbol.upper(),  # for backward compatibility with Yahoo
            "price": price,
            "symbol": symbol.upper()
        }

    except:
        return None


def usd(value):
    """Formats value as USD."""
    return f"${value:,.2f}"
