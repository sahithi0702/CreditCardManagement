from flask import Flask, request, render_template, session, redirect, url_for, jsonify,flash
from bson.objectid import ObjectId
import csv
from dateutil import parser
from datetime import datetime
import datetime
from datetime import date
from flask_mail import Mail, Message
from email.mime.text import MIMEText
from flask import make_response, request, jsonify, render_template
import smtplib
import datetime
import logging
import matplotlib.pyplot as plt
import datetime
import os 
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.datastructures import Headers
from pymongo import MongoClient 
app = Flask(__name__)
app.secret_key="secretkey"
client=MongoClient("mongodb://localhost:27017")
logging.basicConfig(filename="loggers1.log")
logger=logging.getLogger(__name__)

db=client.creditcarddata
def gettime():
    current_datetime = datetime.datetime.now()
    return current_datetime


@app.route('/')
def main():
    return render_template('login.html')
@app.route('/api/login', methods=['POST'])
def logindata():
    try:
        # Fetching the details from the form and checking
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']
            user = db.users.find_one({'email': email})
            backpassword=check_password_hash(user['password'],password)
            if user:
                if user['email'] == email and backpassword:
                    session['email'] = email
                    # Redirect to the dashboard after successful login
                    app.logger.info(f"User {email} log in successful")
                    return redirect(url_for('home'))
                else:
                    # If the password does not match
                    app.logger.error("Invalid login credentials")
                    return "Invalid login credentials"
            
            else:
                # If the user is not registered
                app.logger.error("User not registered")
                flash('please register')
                return render_template('register.html')
                
    except Exception as e:
        # If any other exception occurs, redirect to the error page
        app.logger.error(f"An error occurred: {str(e)}")
        return redirect(url_for('error', error=str(e)))

@app.route('/api/register', methods=['POST', 'GET'])
def registerdata():
    try:
        if request.method == 'POST':
            fname = request.form['firstname']#get first name from the form
            lname = request.form['lastname']#get last name from the form
            email = request.form['email']#get email from the form
            password = request.form['password']#get password from the form
            hashed_password=generate_password_hash(password)
            confirmpassword = request.form['confirmpassword']#get confirm password from the form
            user = db.users.find_one({'email': email})
            if user:
                app.logger.error("Email already registered")
                return "Email already registered"
            else:
                if password == confirmpassword:
                    db.users.insert_one({'firstname': fname, 'lastname': lname, 'email': email, 'password': hashed_password})
                    app.logger.info(f"User {email} registered successfully")
                    return redirect(url_for('main'))
                else:
                    app.logger.error("Mismatch password and conform password. Please enter correct password.")
                    return "Mismatch password and conform password. Please enter correct password."

    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        return redirect(url_for('error', error=str(e)))
        
    
@app.route('/error')
def error():
    error = request.args.get('error')
    return render_template('error.html', error=error)

@app.route('/register')
def register():
    return render_template('register.html')

@app.route('/logout')
def logout():
    if 'email' in session :
        session.pop('email', None)
        return redirect(url_for('main'))

@app.route('/allcards')
def addcards():
    email=session['email']
    data=db.credit_details.find({'email':email})
    return render_template('allcards.html',data=data)

@app.post('/<id>/delete/')
def delete(id):
    db.credit_details.delete_one({"_id":ObjectId(id)})
    email=session['email']
    data=db.credit_details.find({'email':email})
    return redirect(url_for('addcards'))
    # return render_template('allcards.html',data=data)

@app.route('/api/credit_details', methods=['GET', 'POST'])
def savecreditdetails():
    try:
        if request.method == 'POST':
            name = request.form['name']
            cc_number = request.form['cc-number']
            bank = request.form['bank']
            CVV = request.form['CVV']
            expiry_date = request.form['expiry-date']
            credit_limit = request.form['credit-limit']
            remaining_limit = credit_limit
            email = session['email']
            db.credit_details.insert_one({'email': email, 'name': name, 'cc_number': cc_number, 'bank': bank,
                                          'CVV': CVV, 'expiry_date': expiry_date, 'credit_limit': credit_limit,
                                          'remaining_limit': remaining_limit})
            app.logger.info(f"Credit card details saved for user {email}")
            return redirect(url_for('addcards'))

    except Exception as e:
        app.logger.error(f"An error occurred: {str(e)}")
        # If any exception occurs, redirect to the error page with the error message
        return redirect(url_for('error', error=str(e)))

@app.route('/billgenerator',methods=('POST','GET'))
def billgen():
    if request.method == 'POST':
        email = request.form['email']
        date = gettime() 
        amount = request.form['amount']
        usedAt = request.form['placeOfUse']
        creditCardUsed = request.form['creditCardUsed']
        creditCardNumber = request.form['creditCardNumber']
        
        print(email, creditCardUsed, creditCardNumber)

        query = {
            "$and": [
                {"email": email},
                {"cc_number": creditCardNumber},
                {"bank": creditCardUsed}
            ]
        }        
        holderdata = db.credit_details.find_one(query)
        print(holderdata)
        if holderdata==None:
            user = db.users.find_one({'email': email})
            if user==None :
                return "user not found try with another mail which is already registered"
            else:
                return "bank details and card details does not match please enter valid details"
        else:
            availableAmount=holderdata['remaining_limit']
            expiry_date_string = holderdata['expiry_date']

            # Parse the string into a date object
            expiry_date = parser.parse(expiry_date_string).date()

            print(type(expiry_date))

            # Get the current date
            current_date = date.today()
            current_date = current_date.strftime("%Y-%m-%d")
            print(type(current_date))
            current_date=parser.parse(current_date).date()
            if current_date > expiry_date:
                return redirect(url_for('notfound'))
            print(availableAmount)
            amount=int(amount)
            availableAmount=int(availableAmount)
            print(amount,availableAmount)
            if amount<availableAmount:
                availableAmount=availableAmount-amount
                update_operation = {
                    "$set": {
                        "remaining_limit": availableAmount
                    }
                }
         
            else:
                smtp = smtplib.SMTP("smtp-mail.outlook.com", 587)

                smtp.starttls()

                smtp.login('mail-id', 'mail-password')

                msg = MIMEText("Logged in successfully")

                msg["From"] = 'Sahithi.Penthala@chubb.com'

                msg["To"] = email

                msg["Subject"] = "Test Email"

                msg.set_payload("This is the body of the email")

                smtp.sendmail('Sahithi.Penthala@chubb.com',email, msg.as_string())

                smtp.quit()
                # return "Amount insufficient"
            print(holderdata)
            db.transactions.insert_one({'email':email,'date':date,'amount':amount,'usedAt':usedAt,'creditCardUsed':creditCardUsed,'creditCardNumber':creditCardNumber})

            return redirect(url_for('main'))


@app.route('/update',methods=('GET','POST'))
def update():
    if request.method == 'POST':
        email=session['email']
        password=request.form['password']
        newpassword=request.form['newpassword']
        firstname=request.form['firstname']
        lastname=request.form['lastname']
        confirmpassword=request.form['confirmpassword']
        d=db.users.find_one({'email':email})
        backpassword=check_password_hash(d['password'],password)

        if(not backpassword):
            return "passwords does not match"
        
      

        else:
            if(newpassword==confirmpassword):
                hashed_password=generate_password_hash(newpassword)
                db.users.update_one( {"email": email },{ "$set": { 'password':hashed_password,'firstname':
                                                                  firstname,'lastname':lastname}})
            else:
                return "new password and confirm password are not same"

                
                

        return redirect(url_for('home'))

@app.route('/notfound')
def notfound():
    return render_template('notfound.html')
@app.route('/admin')
def admin():
    return redirect(url_for('adminpage'))
@app.route('/home')
def home():
    return render_template('home.html')
@app.route('/adminform')
def adminpage():
    return render_template('admin.html')

@app.route('/credit_details',methods=('GET','POST'))
def credit_details():
    return render_template('credit_details.html')

# @app.route('/history')
# def history():
#     email=session['email']
#     data=db.transactions.find({'email':email})
#     return render_template('history.html',data=data)
@app.route('/history')
def history():
    email = session['email']
    data = db.transactions.find({'email': email})
    search = request.args.get('search', '')
    if search:
        data = db.transactions.find({
            'email': email,
            '$or': [
                {'creditCardNumber': {'$regex': search, '$options': 'i'}},
                {'usedAt': {'$regex': search, '$options': 'i'}}
            ]
        })
    return render_template('history.html', data=data, search=search)

@app.route('/expense')
def expense():
    email = session['email']
    data = db.transactions.find({'email': email}, {'date': 1, 'amount': 1, '_id': 0})
    data_list = list(data)
    print(data_list)
    return render_template('expense.html', data=data_list)

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/dashboard')
def dash():
    email = session['email']
    d = db.credit_details.find({'email': email})
    recentTransactions = db.transactions.find({'email': email}).sort('date', -1).limit(3)
    search = request.args.get('search', '')
    if search:
        d = db.credit_details.find({'email': email, 'bank': {'$regex': search, '$options': 'i'}})
    return render_template('dashboard.html', data=d, search=search,data1=recentTransactions)                                                            


@app.route('/navbar')
def nav():
    return render_template('navbar.html')
@app.route('/download_history', methods=['POST'])
def download_history():
    # Set the response headers to trigger a download prompt
    response_headers = Headers({
        'Pragma': 'public',
        'Expires': '0',
        'Cache-Control': 'must-revalidate, post-check=0, pre-check=0',
        'Content-type': 'text/csv',
        'Content-Disposition': 'attachment; filename="TransactionHistory.csv"',
        'Content-Transfer-Encoding': 'binary'
    })

    # Get data from database or storage
    data = db.transactions.find()

    # Write data to a csv file
    with open('TransactionHistory.csv', mode='w', newline='') as history_file:
        history_writer = csv.writer(history_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        history_writer.writerow(['Serial Number','creditcardnumber','creditcardused','amount','usedAt','date'])
        counter = 1
        for transaction in data:
            history_writer.writerow([counter,transaction['creditCardUsed'],transaction['creditCardNumber'],transaction['amount'],transaction['usedAt'],transaction['date']])
            counter += 1

    # Return the csv file as a response with the appropriate headers
    with open('TransactionHistory.csv', mode='rb') as history_file:
        response = make_response(history_file.read())
    response.headers = response_headers
    
    return response
if __name__=='__main__':
    app.run(debug=True)
