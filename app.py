import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime


from helpers import apology, login_required, lookup, usd

# def lookup(symbol):
#     symbol = symbol.upper()
#     if (symbol == "AAAA"):
#         return {"name": "Stock A", "price": 28.00, "symbol": "AAAA"}
#     elif (symbol == "BBBB"):
#         return {"name": "Stock B", "price": 14.00, "symbol": "BBBB"}
#     elif (symbol == "CCCC"):
#         return {"name": "Stock C", "price": 2000.00, "symbol": "CCCC"}
#     else:
#         return None

# Configure application
app = Flask(__name__)

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    portfolio = db.execute("SELECT symbol, SUM(num_shares) AS total_shares from purchases WHERE user_id = ? group by symbol;", session["user_id"])
    grand_total = cash

    for stock in portfolio:
        x = lookup(stock["symbol"])
        stock["curr_price"] = float(x["price"])
        stock["total_value"] = float(stock["curr_price"] * stock["total_shares"])
        grand_total += stock["total_value"]

        print(type(stock["curr_price"]), stock["total_value"], grand_total)
        print(f"{stock['curr_price']:.2f}")

    portfolio_print = portfolio
    for stock in portfolio_print:
        stock["curr_price"] = f"{stock['curr_price']:.2f}"
        stock["total_value"] = f"{stock['total_value']:.2f}"


    return render_template("index.html", portfolio=portfolio, cash=f"{cash:.2f}", grand_total=f"{grand_total:.2f}")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""

    if request.method == "POST":
        try:
            id = session["user_id"]
        except TypeError:
            print("AAAAHHHH")

        symbol = request.form.get("symbol").lower().strip()
        if not symbol:
            return apology("Field can not be empty", 400)

        quote = lookup(symbol)
        if not quote:
            return apology("Stock symbol not found", 400)

        num_shares = request.form.get("shares")
        try:
            num_shares = int(num_shares)
            if not num_shares > -1:
                raise ValueError
        except ValueError:
            return apology("number of shares needs to be a positive integer", 400)

        try:
            price = quote["price"]
            name = quote["name"]
        except TypeError:
            print("AAAAHHHH")

        cash = db.execute("SELECT cash FROM users WHERE id = ?", id)
        if not cash:
            print("AAAAHHHH")

        try:
            cash = cash[0]["cash"]
        except TypeError:
            print("AAAAHHHH")

        new_cash = cash - price * num_shares

        if (new_cash < 0):
            return apology("you cant afford this amount of shares at the current price", 400)

        # update cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?;", new_cash, id)

        now = datetime.now()
        time = now.strftime("%H:%M:%S")

            # Debug prints
        print("Before query execution:")
        print(f"Symbol: {symbol}")
        print(f"Quote: {quote}")
        print(f"Cash: {cash}")
        print(f"New Cash: {new_cash}")
        print(f"Time: {time}")

        # keep track of purchase
        db.execute("INSERT INTO purchases (user_id, symbol, price, num_shares,time) VALUES (?, ?, ?, ?, ?)", id, symbol, price, round(num_shares), time)

        return redirect("/")

    else:
        return render_template("/buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    history = db.execute("SELECT symbol, price, time, num_shares FROM purchases WHERE user_id = ?", session["user_id"])
    return render_template("history.html", history=history)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 400)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 400)

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

    if request.method == "GET":
        return render_template("quote.html")
    else:
        symbol = request.form.get("symbol")
        quote = lookup(symbol)
        if not quote:
            return apology("Stock symbol not found", 400)
        return render_template("quoted.html", name = quote["name"], price = usd(quote["price"]))


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        ex_usernames = [d["username"] for d in db.execute("SELECT username FROM users ")]
        if not username or not password or not confirmation:
            return apology("no field can be empty", 400)
        elif username in ex_usernames:
            return apology("username already exists", 400)
        elif password != confirmation:
            return apology("password and confirmation do not match", 400)

        password_hash = generate_password_hash(password)

        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, password_hash)
        return redirect("/")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]
    portfolio = db.execute("SELECT symbol, SUM(num_shares) AS total_shares FROM purchases WHERE user_id = ? GROUP BY symbol;", session["user_id"])
    for stock in portfolio:
        stock["curr_price"] = lookup(stock["symbol"])["price"]
        stock["total_value"] = stock["curr_price"] * stock["total_shares"]

    if request.method == "GET":
        return render_template("/sell.html", portfolio=portfolio)

    else:
        symbol_sell = request.form.get("symbol").lower().strip()
        if not symbol_sell:
            return apology("You have to select a stock", 400)

        if not symbol_sell in [d["symbol"] for d in portfolio]:
            return apology("You do not own this stock", 400)

        shares_sell = request.form.get("shares")
        try:
            shares_sell = int(shares_sell)
            if not shares_sell > -1:
                raise ValueError
        except ValueError:
            return apology("number of shares needs to be a positive integer", 400)

        owned_shares = 0
        for stock in portfolio:
            if stock["symbol"] == symbol_sell:
                owned_shares = stock["total_shares"]

        if owned_shares < shares_sell:
            return apology("You dont own that many shares of the stock", 400)


        quote = lookup(symbol_sell)
        price = quote["price"]
        new_cash = cash + price * shares_sell

        # update cash
        db.execute("UPDATE users SET cash = ? WHERE id = ?;", new_cash, session["user_id"])

        now = datetime.now()
        time = now.strftime("%H:%M:%S")

        # keep track of purchase
        db.execute("INSERT INTO purchases (user_id, symbol, price, num_shares,time) VALUES (?, ?, ?, ?, ?)", session["user_id"], symbol_sell, price, -shares_sell, time)

        return redirect("/")

