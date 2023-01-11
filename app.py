import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


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
    # return apology("TODO")
    users = db.execute("SELECT * FROM users WHERE username = ?;", session["user_id"])
    owned_cash = users[0]['cash']
    stockes = db.execute("SELECT * FROM transactions WHERE userID = ? AND type = 'b';", session["user_id"])
    for i in stockes:

        i["price"] = lookup(i["symbol"])["price"]
        print(i)
        i["total"] = i["price"] * i["shares"]

    sum_totals = owned_cash + sum([x['total'] for x in stockes])

    return render_template("index.html", owned_cash=owned_cash, stockes=stockes, sum_totals=sum_totals)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    # return apology("TODO")
    if request.method == "POST":

        if not request.form.get("symbol") or not (query := lookup(request.form.get("symbol"))):
            return apology("Please provide a Valid symbol");

        if (int(request.form.get("shares")) <= 0):
            return apology("Must provide an positive number for number of shares");

        rows = db.execute("SELECT * FROM users WHERE username = ?;", session["user_id"]);
        print(rows)
        print(session["user_id"])
        user_cash = rows[0]["cash"];
        total_prices = query["price"] * int(request.form.get("shares"))

        if user_cash < total_prices:
            return apology("CAN'T AFFORD");

        db.execute("INSERT INTO transactions(userID, company, symbol, shares, price, type) VALUES(?, ?, ?, ?, ?,?);",
                   session["user_id"], query["name"], request.form.get("symbol"), request.form.get("shares"), query["price"], "b");

          # Update user owned cash
        db.execute("UPDATE users SET cash = ? WHERE username = ?;",
                   (user_cash - total_prices), session["user_id"]);

        flash("Bought!")

        return redirect("/")
    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    transactions = db.execute("SELECT * FROM transactions WHERE userID = ?;", session["user_id"])
    return render_template("history.html", transactions=transactions)



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
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))
        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["username"]

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
    # return apology("TODO")
    if request.method == "POST":
        # Ensure Symbol is exists
        if not (query := lookup(request.form.get("symbol"))):
            return apology("INVALID SYMBOL")

        return render_template("quoted.html", query=query)
    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        if not (username := request.form.get("username")):
            return apology("MISSING USERNAME")

        if not (password := request.form.get("password")):
            return apology("MISSING PASSWORD")

        if not (confirmation := request.form.get("confirmation")):
            return apology("PASSWORD DON'T MATCH")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username is not registered already
        if len(rows) != 0:
            return apology("Already Registered", 403)

        hash_password = generate_password_hash(request.form.get("password"))
        # Insert user data inside the database
        db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", request.form.get("username"), hash_password)

        # Remember which user has logged in
        session["user_id"] = request.form.get("username");

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")

    # return apology("TODO")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    # return apology("TODO")
    if request.method == "POST":
        symbol = request.form.get("symbol");

        num_stocks = db.execute("SELECT shares FROM transactions WHERE userID = ? AND symbol = ?", session["user_id"], symbol)
        if num_stocks:

            num_stocks = int(num_stocks[0]["shares"])
            print(num_stocks)
            if num_stocks < int(request.form.get("shares")) or int(request.form.get("shares")) <= 0:
                return apology("Please entry number of stock properly")
            else:
                db.execute("UPDATE transactions set shares = ? where userID = ? AND symbol = ?", num_stocks - int(request.form.get("shares")), session["user_id"], symbol);
                return redirect("/")

        else:
            return apology("Please enter a valid share that you have already purchased")

    else:
        return render_template("sell.html")





