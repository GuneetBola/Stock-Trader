import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import *

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd
app.jinja_env.globals.update(usd=usd, lookup=lookup, int=int)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
# if not os.environ.get("API_KEY"):
    # raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows=db.execute("SELECT symbol,SUM(numofshares) as total_shares FROM boughtshares WHERE id=:id GROUP BY symbol HAVING numofshares>0",id=session["user_id"])
    user=db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])

    values={}
    cash=user[0]['cash']
    complete_total=cash
    for stock in rows:
        price = lookup(stock['symbol'])['price']
        total = stock['total_shares'] * price
        stock.update({'valueofstock': price})
        complete_total += total

    return render_template("index.html",rows=rows,cash=cash,total=complete_total)

@app.route("/portfolio")
@login_required
def portfolio():
    """Show portfolio of stocks"""
    rows=db.execute("SELECT symbol,SUM(numofshares) as total_shares FROM boughtshares WHERE id=:id GROUP BY symbol HAVING numofshares>0",id=session["user_id"])
    user=db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])

    values={}
    cash=user[0]['cash']
    complete_total=cash
    for stock in rows:
        price = lookup(stock['symbol'])['price']
        total = stock['total_shares'] * price
        stock.update({'valueofstock': price})
        complete_total += total

    return render_template("index.html",rows=rows,cash=cash,total=complete_total)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():

    shares=request.form.get("numofshares")
    symbol=request.form.get("symbol")
    """Buy shares of stock"""
    if request.method=="POST":
        if not shares or not symbol:
            return apology("do not leave fields (number of shares or symbol) blank", 403)

        elif not int(request.form.get("numofshares")) > 0:
            return apology("must provide positive/integer number of shares", 403)

        elif lookup(request.form.get("symbol"))==None:
            return apology("must provide valid stock symbol", 403)

        else:
            rows=db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])
            cash=rows[0]['cash']
            quote = lookup(request.form.get("symbol"))
            moneyshares=quote['price']*int(request.form.get("numofshares"))
            actual_cash=cash-moneyshares

            if actual_cash<0:
                return apology("You do not have enough money to buy these many stocks of this stock.", 403)
            else:
                db.execute("UPDATE users SET cash=:updated WHERE id=:id",updated=actual_cash, id=session["user_id"])

                db.execute("INSERT INTO transactions (id,symbol,numofshares,valueofshares,date) VALUES (:id,:symbol,:numofshares,:valueofshares, :date)",
                    id=session["user_id"],
                    symbol=request.form.get("symbol"),
                    numofshares=int(shares),
                    valueofshares= quote['price'],
                    date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))


                db.execute("INSERT INTO boughtshares (id,symbol,numofshares,valueofstock) VALUES(:id,:symbol,:numofshares,:valueofstock)",
                id=session["user_id"],symbol=quote['symbol'],numofshares=shares,valueofstock=quote['price'])

        return redirect("/")
    else:
        return render_template("buy.html")



@app.route("/history")
@login_required
def history():

    """Show history of transactions"""
    user_transactions = db.execute(
        "SELECT symbol, numofshares, valueofshares, date FROM transactions WHERE id = :id ORDER BY date DESC",
            id=session["user_id"])

    return render_template("history.html",transactions=user_transactions)


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
    if request.method =="POST":
        symbol1=request.form.get("symbol")
        quote=lookup(symbol1)
        if quote == None:
            return apology("must enter a valid stock symbol")
        else:
            return render_template("quoted.html", value=quote['price'],symbol=quote['symbol'],name=quote['name'])
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method=="POST":

        if not request.form.get("username"):
            return apology("must provide username", 403)

        elif not request.form.get("password"):
            return apology("must provide password", 403)


        try:
            insert=db.execute("INSERT INTO users (username,hash) VALUES (:username,:hash)", username=request.form.get("username"),hash=generate_password_hash(request.form.get("password")))
        except:
            return apology("Username already exists", 403)


        session["user_id"]=insert
        return redirect("/login")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method=="POST":
        if not request.form.get("shares") or not request.form.get("symbol"):
            return apology("do not leave fields (number of shares or symbol) blank", 403)
        elif int(request.form.get("shares"))<0 or not request.form.get("shares").isdigit():
            return apology("must provide positive/integer number of shares", 403)
        elif lookup(request.form.get("symbol"))==None:
            return apology("must provide valid stock symbol", 403)
        else:
            rows = db.execute("SELECT cash FROM users WHERE id=:id",id=session["user_id"])
            cash = rows[0]['cash']
            stock = lookup(request.form.get("symbol"))
            shares = int(request.form.get("shares"))
            moneyshares = stock['price'] * int(request.form.get("shares"))
            cash_after=cash+moneyshares
            find = db.execute("SELECT SUM(numofshares) as total_shares FROM boughtshares WHERE id = :id AND symbol = :symbol GROUP BY symbol",
                id=session["user_id"], symbol=request.form.get("symbol"))

            if len(find) != 1 or find[0]["total_shares"] <= 0 or find[0]["total_shares"] < shares:
                return apology("you can't sell less than 0 or more than you own", 400)
            db.execute("UPDATE users SET cash=:updated WHERE id=:id",updated=cash_after, id=session["user_id"])


            db.execute("INSERT INTO boughtshares (id,symbol,numofshares,valueofstock) VALUES(:id,:symbol,:numofshares,:valueofstock)",
                id=session["user_id"],
                symbol=request.form.get("symbol"),
                numofshares=-shares,
                valueofstock=stock['price'])

            db.execute("INSERT INTO transactions (id,symbol,numofshares,valueofshares,date) VALUES (:id,:symbol,:numofshares,:valueofshares, :date)",
                id=session["user_id"], symbol=request.form.get("symbol"), numofshares=-shares, valueofshares=stock['price'], date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

        return redirect("/")
    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
