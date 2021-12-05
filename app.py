import flask
import os
import requests
from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

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

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "redis"
app.secret_key =  'AOZr96j/3yX R~XHH!jmN]KWX/,?gT' #os.urandom(24)
app.config['SECRET_KEY'] = 'AOZr96j/3yX R~XHH!jmN]KWX/,?gT' #os.urandom(32)
#app.secret_key = 'AOZr96j/3yX R~XHH!jmN]KWX/,?gT'
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///test.db")




@app.route("/")
@login_required
def index():
    """Show portfolio"""
    name = "BITCOIN"
    
    user = session["user_id"]
    role = session["role"]
    
    if role == "client":
        client = 'c'+str(user)
        portfolio = db.execute("SELECT bitcoins FROM CLIENT WHERE client_id = (?)", client)
        current_cash = db.execute("SELECT fiat_money FROM CLIENT WHERE client_id = (?)", client)
        
        current_cash = current_cash[0]['fiat_money']
    
    
        total = 0.00

        price = requests.get('https://cloud.iexapis.com/stable/crypto/btcusd/quote?token=pk_95e64a4d35634188936141168c726d64').json()["latestPrice"]

        
        
        share_num = db.execute("SELECT bitcoins FROM CLIENT WHERE client_id = (?)", client)


        counter = 0
        for i in share_num:
            total = total + (float(i["bitcoins"]) * float(price))
            counter += 1

        return render_template("client_index.html", portfolio=portfolio, price=float(price), current_cash=float(current_cash), total=float(total))
        
    elif role == "trader":
        return redirect("/reqs")
    elif role == "manager":
        return redirect("/history")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy bitcoins"""

    if request.method == "GET" and session["role"] == "client":
        return render_template("buy.html")

    else:
        role = session["role"]
        user = session["user_id"]
        if role == "client":   
            client = 'c'+str(user) 
            symbol = "BTCUSD"
            status = 1
            coins = request.form.get("coins")
            commission_type = request.form["commission"]
            quote = requests.get('https://cloud.iexapis.com/stable/crypto/btcusd/quote?token=pk_95e64a4d35634188936141168c726d64')
     
            # if invalid ticker
            name = "BITCOIN"
            user = session["user_id"]
            role = session["role"]
            client = 'c'+ str(user)
            trader = "self"
            current_cash = db.execute("SELECT fiat_money FROM CLIENT WHERE client_id = (?)", client)
            current_cash = current_cash[0]['fiat_money']
        
            # Gold or Silver customer
            chk1 = db.execute("SELECT strftime('%m',time) AS month, SUM(coin*price) FROM TRANSACTIONX WHERE client_id=(?)and coin>0 and status>0 GROUP BY month", client)
            chk2 = db.execute("SELECT strftime('%m',time) AS month, SUM(coin*price) FROM TRANSACTIONX WHERE client_id=(?) and coin<0 and status>0 GROUP BY month", client)
            curt = db.execute("SELECT strftime('%m',datetime('now','localtime')) as now")
            curt = curt[0]["now"]
            ttt = 0
            for item in chk1+chk2:
                if int(item['month'])+1 == int(curt):
                    ttt = ttt+abs(chk2[0]['SUM(coin*price)'])
            
            
            if ttt >= float(100000):
                db.execute("UPDATE CLIENT SET level = (?) WHERE client_id = (?)", "Gold", client)
            else:
                db.execute("UPDATE CLIENT SET level = (?) WHERE client_id = (?)", "Silver", client)

                                 
            level = db.execute("SELECT level FROM CLIENT WHERE client_id = (?)", client)
            level = level[0]['level']
            
            if level == "Gold":
                com = 0.025
            else:
                com = 0.05
        
            if commission_type == "fiat":
                commission_tax = float(quote.json()["latestPrice"]) * float(coins)*com
                new_balance = current_cash - (float(quote.json()["latestPrice"]) * float(coins)) - commission_tax
            else:
                commission_tax = float(coins)*(com)
                new_balance = current_cash - (float(quote.json()["latestPrice"]) * float(coins))
                coins = float(coins) - commission_tax
	            
            
            new_balance = current_cash - (float(quote.json()["latestPrice"]) * float(coins))

            portfolio = db.execute("SELECT COUNT(client_id) FROM CLIENT WHERE client_id = (?)", client)

            if quote.status_code == 500 or quote.status_code == 404:
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, coins, quote.json()["latestPrice"], commission_tax, commission_type, -1)
                flash("Unfortunately API is down!!!", "danger")
                return render_template("buy.html")


            #if user has enough funds (including commissions)
            if quote.status_code == 200 and ( new_balance >= 0 ):
                status = 1
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, coins, quote.json()["latestPrice"], commission_tax, commission_type, status)
                db.execute("UPDATE CLIENT SET fiat_money = (?) WHERE client_id = (?)", new_balance, client)
            
                if portfolio[0]["COUNT(client_id)"] == 0:
                    db.execute("UPDATE CLIENT SET bitcoins = bitcoins + (?) WHERE client_id = (?)", coins, client)
                    flash("Bought!", "primary")
                    return redirect("/")
                # if stock already in portfolio, add to it
                else:
                    db.execute("UPDATE CLIENT SET bitcoins = bitcoins + (?) WHERE client_id = (?)", coins, client)
                    flash("Bought!", "primary")
                    return redirect("/")
            # if not enough funds in account
            elif new_balance < 0:
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, coins, quote.json()["latestPrice"], commission_tax, commission_type, -1)
                flash("You do not have enough funds in account.", "danger")
                return render_template("buy.html")




@app.route("/load", methods=["GET", "POST"])
@login_required
def load():
    """Load fiat money for bitcoin purchase"""
    if request.method == "GET" and session["role"] == "client":
        return render_template("load.html")
    else:
        user = session["user_id"]
        role = session["role"]
        if role == "client":
            client = 'c'+str(user)
            amount = request.form.get("amount")
            current_cash = db.execute("SELECT fiat_money FROM CLIENT WHERE client_id = (?)", client)
            current_cash = current_cash[0]['fiat_money']
            new_balance = current_cash + int(amount)
        
            if new_balance > current_cash:
                db.execute("UPDATE CLIENT SET fiat_money = (?) WHERE client_id = (?)", new_balance, client)
                return redirect("/")
            else:
                return render_template("load.html")
        
@app.route("/history")
@login_required
def history():
    """Show history of approved transactions"""
    user = session["user_id"]
    role = session["role"]
    
    if role == "client":
        client = 'c'+str(user)    
        history = db.execute("SELECT client_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX WHERE client_id = (?) and status =1", client)
        return render_template("client_history.html", history=history)
    elif role == "trader":
        trader = 't' + str(user)
        history = db.execute("SELECT client_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX WHERE trader_id = (?) and status =1", trader)
    else:
        Buy = db.execute("SELECT client_id, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY client_id")
        Sell = db.execute("SELECT client_id, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin<0 and status>0 GROUP BY client_id") 
        
        
        #history = db.execute("SELECT client_id, trader_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX")
        return render_template("admin_history.html", Buy=Buy,Sell=Sell)
        
@app.route("/insights")
@login_required
def insight():
    user = session["user_id"]
    role = session["role"]
    
    if role == "manager":
        dailyBuy = db.execute("SELECT strftime('%d',time) AS day, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY day")
        dailySell = db.execute("SELECT strftime('%d',time) AS day, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY day")


        weeklyBuy = db.execute("SELECT strftime('%W',time) AS week, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY week")
        weeklySell = db.execute("SELECT strftime('%W',time) AS week, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY week")

        monthlyBuy = db.execute("SELECT strftime('%m',time) AS month, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY month")
        monthlySell = db.execute("SELECT strftime('%m',time) AS month, SUM(coin), SUM(commission) FROM TRANSACTIONX WHERE coin>0 and status>0 GROUP BY month")
        
        return render_template("insights.html",dailyBuy=dailyBuy,dailySell=dailySell,  weeklyBuy=weeklyBuy,weeklySell=weeklySell,monthlyBuy=monthlyBuy,monthlySell=monthlySell)
        
@app.route("/failed")
@login_required
def failed():
    """Show history of failed/cancelled transactions"""
    user = session["user_id"]
    role = session["role"]
    if role == "client":
        client = 'c'+str(user)    
        failed = db.execute("SELECT client_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX WHERE client_id = (?) and status =-1", client)
        return render_template("client_failed.html", failed=failed)


@app.route("/sendmoney" , methods=["GET", "POST"])
@login_required
def sendmoney():
    if request.method == "GET" and session["role"] == "client":
        traderList = db.execute("SELECT trader_id FROM TRADER")
        return render_template("sendmoney.html", traderList=traderList)

    else:
        if session["role"] == "client":
            user = session["user_id"]
            role = session["role"]
            client = 'c'+str(user)
            amount = request.form.get("amount")
            trader = request.form.get("traders")
            current_cash = db.execute("SELECT fiat_money FROM CLIENT WHERE client_id = (?)", client)
            current_cash = current_cash[0]['fiat_money']
            
            if float(amount) > float(current_cash):
                flash("Don't have Enough Money to Send!!!", "danger")
                return redirect("/sendmoney")
            else:
                db.execute("INSERT INTO TRANSFER_CASH_TO_TRADER (client_id, trader_id, amount) VALUES (? ,?, ?)", client, trader, amount)
                traderList = db.execute("SELECT trader_id FROM TRADER")
                return redirect("/sendmoney")


@app.route("/asktrade", methods=["GET", "POST"])
@login_required
def asktrade():
    """Update address"""
    if request.method == "GET" and session["role"] == "client":
        traderList = db.execute("SELECT trader_id FROM TRADER")
        return render_template("asktrade.html", traderList=traderList)

    else:
        if session["role"] == "client":
            user = session["user_id"]
            role = session["role"]
            client = 'c'+str(user)
            coins = request.form.get("crypto")
            trader = request.form.get("traders")
            db.execute("INSERT INTO ASK_FOR_TRADE (client_id, trader_id, coin) VALUES (? ,?, ?)", client, trader, coins)

            return redirect("/asktrade")


@app.route("/reqs", methods=["GET", "POST"])
@login_required
def reqs():
    """Update address"""
    if request.method == "GET" and session["role"] == "trader":
        trader = 't'+str(session["user_id"])
        reqList = db.execute("SELECT client_id, coin FROM ASK_FOR_TRADE WHERE trader_id = (?) and status=(?)", trader, -1)
        
        return render_template("requests.html", reqList=reqList)

    elif request.method == "POST" and session["role"] == "trader":
        if session["role"] == "trader":
            user = session["user_id"]
            role = session["role"]
            trader = 't'+str(user)
            
            reqList = db.execute("SELECT client_id, coin FROM ASK_FOR_TRADE WHERE trader_id = (?)", trader)
            
            outputList = []
            quote = requests.get('https://cloud.iexapis.com/stable/crypto/btcusd/quote?token=pk_95e64a4d35634188936141168c726d64')
            for i in range(len(reqList)):
                temp = request.form.get("stat_"+str(i))
                outputList.append(temp)
            newList = []
            for i in range(len(reqList)):
                commission_tax = (0.025 * float(abs(reqList[i]['coin'])) * float(quote.json()["latestPrice"]))
                total = (1.025 * float(abs(reqList[i]['coin'])) * float(quote.json()["latestPrice"]))
                commission_type = "fiat_money"

                
                if reqList[i]['coin'] > 0:
                    available_cash = db.execute("SELECT net_amount FROM NET_AMOUNT WHERE client_id = (?) and trader_id = (?)", reqList[i]['client_id'], trader)
                    if len(available_cash) > 0:
                        available_cash = available_cash[0]["net_amount"] 
                    else:
                        available_cash = 0
                    
                    flag = 0
                                        
                    if (outputList[i] == 'accept' or outputList[i] == 'decline') and available_cash < total:
                        db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, reqList[i]['client_id'], trader, reqList[i]['coin'], quote.json()["latestPrice"], commission_tax, commission_type, -1)
                        db.execute("DELETE FROM ASK_FOR_TRADE WHERE client_id = (?) and trader_id = (?) and coin = (?)", reqList[i]['client_id'], trader, reqList[i]['coin'])
                        flag = 1
                
                    
                    elif outputList[i] == 'accept' and flag==0:
                        db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, reqList[i]['client_id'], trader, reqList[i]['coin'], quote.json()["latestPrice"], commission_tax, commission_type, 1)
                        db.execute("DELETE FROM ASK_FOR_TRADE WHERE client_id = (?) and trader_id = (?) and coin = (?)", reqList[i]['client_id'], trader, reqList[i]['coin'])
                        db.execute("UPDATE NET_AMOUNT SET net_amount = net_amount-(?) WHERE client_id = (?) and trader_id = (?)", available_cash - float(reqList[i]['coin'])*float(quote.json()["latestPrice"]), reqList[i]['client_id'], trader)
                        db.execute("UPDATE CLIENT SET bitcoins = bitcoins + (?) WHERE client_id = (?)", reqList[i]['coin'], reqList[i]['client_id'])
                    
                    elif outputList[i] == 'decline' and flag==0:
                        db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, reqList[i]['client_id'], trader, reqList[i]['coin'], quote.json()["latestPrice"], commission_tax, commission_type, -1)
                        db.execute("DELETE FROM ASK_FOR_TRADE WHERE client_id = (?) and trader_id = (?) and coin = (?)", reqList[i]['client_id'], trader, reqList[i]['coin'])
                        
                    else:
                        newList.append(reqList[i]) 

                        
                
                elif reqList[i]['coin'] < 0:
                
                    available_coin = db.execute("SELECT bitcoins FROM CLIENT WHERE client_id = (?)", reqList[i]['client_id'])
                    if len(available_coin) > 0:
                        available_coin = available_coin[0]["bitcoins"] 
                    else:
                        available_coin = 0
                    flag = 0
                                        
                    if (outputList[i] == 'accept' or outputList[i] == 'decline') and available_coin < abs(reqList[i]['coin']):
                        db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, reqList[i]['client_id'], trader, reqList[i]['coin'], quote.json()["latestPrice"], commission_tax, commission_type, -1)
                        db.execute("DELETE FROM ASK_FOR_TRADE WHERE client_id = (?) and trader_id = (?) and coin = (?)", reqList[i]['client_id'], trader, reqList[i]['coin'])
                        flag = 1 
                       
                        
                    elif outputList[i] == 'accept' and flag==0:
                        db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, reqList[i]['client_id'], trader, reqList[i]['coin'], quote.json()["latestPrice"], commission_tax, commission_type, 1)
                        db.execute("DELETE FROM ASK_FOR_TRADE WHERE client_id = (?) and trader_id = (?) and coin = (?)", reqList[i]['client_id'], trader, reqList[i]['coin'])
                        db.execute("UPDATE CLIENT SET fiat_money = fiat_money+(?) WHERE client_id = (?)",  abs(float(reqList[i]['coin']))*float(quote.json()["latestPrice"]), reqList[i]['client_id'])
                        db.execute("UPDATE CLIENT SET bitcoins = bitcoins + (?) WHERE client_id = (?)", reqList[i]['coin'], reqList[i]['client_id'])
                    
                    elif outputList[i] == 'decline' and flag ==0:
                        db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, reqList[i]['client_id'], trader, reqList[i]['coin'], quote.json()["latestPrice"], commission_tax, commission_type, -1)
                        db.execute("DELETE FROM ASK_FOR_TRADE WHERE client_id = (?) and trader_id = (?) and coin = (?)", reqList[i]['client_id'], trader, reqList[i]['coin']) 
                        
                    
                    else:
                        newList.append(reqList[i]) 

            
        return render_template("requests.html", reqList=newList)




@app.route("/moneyreq", methods=["GET", "POST"])
@login_required
def moneyreq():
    """Update address"""
    if request.method == "GET" and session["role"] == "trader":
        trader = 't'+str(session["user_id"])
        reqList = db.execute("SELECT client_id, amount FROM TRANSFER_CASH_TO_TRADER WHERE trader_id = (?) and status=(?)", trader,-1)
    
        return render_template("itrademoney.html", reqList=reqList)

    elif request.method == "POST" and session["role"] == "trader":
        if session["role"] == "trader":
            user = session["user_id"]
            role = session["role"]
            trader = 't'+str(user)
            
            reqList = db.execute("SELECT client_id, amount FROM TRANSFER_CASH_TO_TRADER WHERE trader_id = (?) and status =(?)", trader, -1)
            
            outputList = []
            quote = requests.get('https://cloud.iexapis.com/stable/crypto/btcusd/quote?token=pk_95e64a4d35634188936141168c726d64')
            for i in range(len(reqList)):
                temp = request.form.get("stat_"+str(i))
                outputList.append(temp)
            newList = []
             
            for i in range(len(reqList)):
                already = db.execute("SELECT net_amount FROM NET_AMOUNT WHERE trader_id = (?) and client_id = (?)", trader, reqList[i]['client_id'])
                if outputList[i] == 'accept' and len(already)==0:
                    db.execute("INSERT INTO NET_AMOUNT (client_id, trader_id, net_amount) VALUES (?, ?, ?)", reqList[i]['client_id'], trader, reqList[i]['amount'])
                    db.execute("UPDATE CLIENT SET fiat_money = fiat_money-(?) WHERE client_id = (?)", reqList[i]['amount'], reqList[i]['client_id'])
                    db.execute("DELETE FROM TRANSFER_CASH_TO_TRADER WHERE client_id = (?) and trader_id = (?) and amount = (?)", reqList[i]['client_id'], trader, reqList[i]['amount'])
                elif outputList[i] == 'accept' and len(already)!=0:
                    db.execute("UPDATE NET_AMOUNT SET net_amount = net_amount+(?) WHERE client_id = (?) and trader_id = (?)", reqList[i]['amount'], reqList[i]['client_id'], trader)
                    db.execute("UPDATE CLIENT SET fiat_money = fiat_money-(?) WHERE client_id = (?)", reqList[i]['amount'], reqList[i]['client_id'])
                    db.execute("DELETE FROM TRANSFER_CASH_TO_TRADER WHERE client_id = (?) and trader_id = (?) and amount = (?)", reqList[i]['client_id'], trader, reqList[i]['amount'])
                elif outputList[i] == 'decline':
                    db.execute("UPDATE TRANSFER_CASH_TO_TRADER SET status=0 WHERE client_id = (?) and trader_id = (?) and amount = (?)", reqList[i]['client_id'], trader, reqList[i]['amount'])
                    #db.execute("DELETE FROM TRANSFER_CASH_TO_TRADER WHERE client_id = (?) and trader_id = (?) and amount = (?)", reqList[i]['client_id'], trader, reqList[i]['amount']) 
                    
                else:
                    newList.append(reqList[i])
            return render_template("itrademoney.html", reqList=newList)


@app.route("/logs")
@login_required
def logs():
    """Show history of failed/cancelled transactions"""
    user = session["user_id"]
    role = session["role"]
    if role == "trader":
        trader = 't'+str(user)    
        logs = db.execute("SELECT client_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX WHERE trader_id = (?) and status =-1", trader)
        return render_template("logs.html", logs=logs)

@app.route("/moneylogs")
@login_required
def moneylogs():
    """Show history of failed/cancelled transactions"""
    user = session["user_id"]
    role = session["role"]
    if role == "trader":
        trader = 't'+str(user)    
        logs = db.execute("SELECT client_id, amount, time FROM TRANSFER_CASH_TO_TRADER WHERE trader_id = (?) and status =(?)", trader,0)
        return render_template("moneylogs.html", logs=logs)



@app.route("/trader_history")
@login_required
def trader_history():
    """Show history of approved transactions"""
    user = session["user_id"]
    role = session["role"]
    if role == "trader":
        trader = 't' + str(user)
        history = db.execute("SELECT client_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX WHERE trader_id = (?) and status=1", trader)
        return render_template("trader_history.html", history=history)


@app.route("/search" , methods=["GET", "POST"])
@login_required
def search():
    if request.method == "GET" and session["role"] == "trader":
        clientList = db.execute("SELECT client_id FROM CLIENT")
        return render_template("search.html", clientList=clientList)

    else:
        if session["role"] == "trader":
            user = session["user_id"]
            role = session["role"]
            trader = 't'+str(user)
            client = request.form.get("clients")
            user = int(client[-1:])
            cname = db.execute("SELECT user_id, fiat_money, level FROM CLIENT WHERE client_id=(?)", client)
            uname = db.execute("SELECT username, first_name, last_name FROM USER WHERE user_id=(?)", user)
            addr = db.execute("SELECT zipcode, street_name, city, state FROM LIVES WHERE user_id=(?)", user)
            trnx = db.execute("SELECT client_id, trader_id, price, coin, status, time FROM TRANSACTIONX WHERE client_id=(?)", client)
            return render_template("client_details.html", cname=cname, uname=uname, addr=addr, trnx=trnx)
            
            


@app.route("/admin_history")
@login_required
def admin_history():
    """Show history of approved transactions"""
    user = session["user_id"]
    role = session["role"]
    if role == "admin":

        history = db.execute("SELECT client_id, price, coin, commission, commission_type, status, time FROM TRANSACTIONX WHERE status=1")
        return render_template("admin_history.html", history=history)


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
        rows = db.execute("SELECT * FROM USER WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash("Username or password incorrect.", "danger")
            return render_template("login.html")

        # Remember which user has logged in
        session["user_id"] = rows[0]["user_id"]
        session["role"] = rows[0]["role"]

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


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    rows = db.execute("SELECT * FROM USER WHERE username = :username", username=request.form.get("username"))
    if request.method == "GET":
        return render_template("register.html")
    else:
        # if no username exists and passwords match
        if (request.form.get("password")) == (request.form.get("confirmation")) and len(rows) == 0:
            hashed = generate_password_hash(request.form.get("password"))
            username = request.form.get("username")
            first_name = request.form.get("fname")
            last_name = request.form.get("lname")
            phone_no = request.form.get("pnumber")
            cell_no = request.form.get("cnumber")
            email = request.form.get("email")
            role = request.form["role"]
            db.execute("INSERT INTO USER (username, first_name, last_name, email, phone_no, cell_no, role, hash) VALUES (:username, :first_name, :last_name, :email, :phone_no, :cell_no, :role, :password)", username=username, first_name=first_name, last_name=last_name, email=email, phone_no=phone_no, cell_no=cell_no, role=role, password=hashed)
            
            last = db.execute("SELECT last_insert_rowid() FROM USER");
            user = int(last[0]['last_insert_rowid()'])

            if role == "client":
                client = 'c'+str(user)
                db.execute("INSERT INTO CLIENT (user_id, client_id, fiat_money, bitcoins, level) VALUES (?, ?, ?, ?, ?)", user, client, 1000000.00, 0.00, "Silver")
            elif role == "trader":
                trader = 't'+str(user)
                db.execute("INSERT INTO TRADER (user_id, trader_id, fiat_money) VALUES (?, ?, ?)", user, trader, 90000000.00)
            elif role == "manager":
                manager = 'm' + str(user)
                db.execute("INSERT INTO MANAGER (user_id, manager_id) VALUES (?,?)", user, manager)            
            flash("Account created!", "primary")
            return render_template("login.html")
        # if passwords do not match
        elif (request.form.get("password")) != (request.form.get("confirmation")) and len(rows) == 0:
            flash("Your passwords do not match.", "danger")
            return render_template("register.html")
        # if username exists
        else:
            flash("Username already exists.", "danger")
            return render_template("register.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "GET":
        return render_template("cquote.html")
    else:
        #ticker = request.form.get("symbol")
        quote = requests.get('https://cloud.iexapis.com/stable/crypto/btcusd/quote?token=pk_95e64a4d35634188936141168c726d64')
        if quote.status_code == 200:
            return render_template("cquoted.html", quote=quote.json()["latestPrice"], name="BITCOIN")
        else:
            flash("API down", "danger")
            return render_template("cquote.html")


@app.route("/address", methods=["GET", "POST"])
@login_required
def address():
    """Update address"""
    if request.method == "GET":
        return render_template("address.html")
    else:
        user = session["user_id"]  
        client = 'c'+str(user)
        stadd = request.form.get("stadd")
        city = request.form.get("city")
        state = request.form.get("state")
        zipcode = request.form.get("zipcode")
        
        already = db.execute("SELECT user_id FROM LIVES WHERE user_id = (?)", user) 
        
        if len(already)==0:   
            db.execute("INSERT INTO LIVES (user_id, street_name, city, state, zipcode) VALUES (?, ?, ?, ?, ?)", user, stadd, city, state, zipcode)
            flash("Address added for the first time!!!", "primary")
            
        else:
            db.execute("UPDATE LIVES SET street_name = (?), city = (?), state = (?), zipcode = (?) WHERE user_id = (?)", stadd, city, state, zipcode, user)
            flash("Address Updated!!!", "primary")

        return redirect("/")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell bitcoins"""
    if request.method == "GET" and session["role"] == "client":
        return render_template("sell.html")
    else:
        role = session["role"]
        user = session["user_id"]
    
        if session["role"] == "client":
            coins = request.form.get("coins")
            commission_type = request.form["commission"]        
            user = session["user_id"]
            role = session["role"]
            client = 'c'+str(session["user_id"])
            trader = "self"
        
            symbol = "BTCUSD"
            price = requests.get('https://cloud.iexapis.com/stable/crypto/btcusd/quote?token=pk_95e64a4d35634188936141168c726d64')

            # if invalid stock ticker

            current_cash = db.execute("SELECT fiat_money FROM CLIENT WHERE client_id = (?)", client)
            current_cash = current_cash[0]['fiat_money']


            chk1 = db.execute("SELECT strftime('%m',time) AS month, SUM(coin*price) FROM TRANSACTIONX WHERE client_id=(?)and coin>0 and status>0 GROUP BY month", client)
            chk2 = db.execute("SELECT strftime('%m',time) AS month, SUM(coin*price) FROM TRANSACTIONX WHERE client_id=(?) and coin<0 and status>0 GROUP BY month", client)
            curt = db.execute("SELECT strftime('%m',datetime('now','localtime')) as now")
            curt = curt[0]["now"]
            ttt = 0
            for item in chk1+chk2:
                if int(item['month'])+1 == int(curt):
                    ttt = ttt+abs(chk2[0]['SUM(coin*price)'])
            
            if ttt >= float(100000):
                db.execute("UPDATE CLIENT SET level = (?) WHERE client_id = (?)", "Gold", client)
            else:
                db.execute("UPDATE CLIENT SET level = (?) WHERE client_id = (?)", "Silver", client)
 


            level = db.execute("SELECT level FROM CLIENT WHERE client_id = (?)", client)
            level = level[0]['level']
          
            if level == "Gold":
                com = 0.025
            else:
                com = 0.05

        
            if commission_type == "fiat":
                commission_tax = float(price.json()["latestPrice"]) * float(coins) * com
                new_balance = current_cash + (float(price.json()["latestPrice"]) * float(coins)) - commission_tax
            else:
            
                new_balance = current_cash + (float(price.json()["latestPrice"]) * float(coins))
                commission_tax = float(coins)*(com)
                coins = float(coins) - commission_tax 
                #coins = str(coins)

            if price.status_code != 200:
                status = -1
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, "-" + str(coins), price.json()["latestPrice"], commission_tax, commission_type, status)        
                flash("Unfortunately API is down!!!.", "danger")
                return render_template("sell.html")


            
            coins_owned = db.execute("SELECT bitcoins FROM CLIENT WHERE client_id = (?)", client)

            # user does not own stock
            if coins_owned == []:
                status = -1
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, "-" + str(coins), price.json()["latestPrice"], commission_tax, commission_type, status)        
                flash("You do not own bitcoins.", "danger")
                return render_template("sell.html")

            # user tried to sell more shares than they own
            if float(coins_owned[0]["bitcoins"]) < float(coins):
                status = -1
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, "-" + str(coins), price.json()["latestPrice"], commission_tax, commission_type, status)        
                flash("You do not own that many bitcoins.", "danger")
                return render_template("sell.html")

            # if they sell all their stock
            if float(coins_owned[0]["bitcoins"]) == float(coins):
                # update cash balance
                db.execute("UPDATE CLIENT SET fiat_money = (?) WHERE client_id = (?)", new_balance, client)
                # update portfolio
                #db.execute("DELETE FROM USER WHERE user_id = (?)", user)
                # update history
                status = 1
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, "-" + str(coins), price.json()["latestPrice"], commission_tax, commission_type, status)
                flash("Sold!", "primary")
                return redirect("/")


            if float(coins_owned[0]["bitcoins"]) > float(coins):
                # update cash balance
                db.execute("UPDATE CLIENT SET fiat_money = (?) WHERE client_id = (?)", new_balance, client)
                # update portfolio
                db.execute("UPDATE CLIENT SET bitcoins = bitcoins - (?) WHERE client_id = (?)", coins, client)
                #update history
                status = 1
                db.execute("INSERT INTO TRANSACTIONX (user_id, client_id, trader_id, coin, price, commission, commission_type, status) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", user, client, trader, "-" + str(coins), price.json()["latestPrice"], commission_tax, commission_type, status)
                flash("Sold!", "primary")
                return redirect("/")

            return "error 500"




def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
    
    
