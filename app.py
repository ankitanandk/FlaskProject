from flask import Flask, render_template, request, redirect
import pymysql
import boto3
import json
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
import os

ACCESS_KEY = "AKIAURHHXOMYTEF62MPB"
SECRET_KEY = "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"
AWS_REGION = "us-east-1"
AWS_STORAGE_BUCKET_NAME = 'ccprjbucket'

ENDPOINT = "database-1.c7wyctrjz30j.us-east-1.rds.amazonaws.com"
PORT = "3306"
USR = "admin"
PASSWORD = "Ankit1234"
DBNAME = "cloudproject"

app = Flask(__name__)


@app.route('/')
def main():
    return render_template("login.html")


@app.route('/notfound')
def notfound():
    return render_template("usernotfound.html")


@app.route('/login')
def login():
    render_template("login")


@app.route('/register')
def register():
    return render_template("register.html")


@app.route('/add', methods=["POST"])
def add():
    email = request.form.get("email")
    password = request.form.get("password")
    desc = request.form.get("description")
    email1 = request.form.get("email1")
    email2 = request.form.get("email2")
    email3 = request.form.get("email3")
    email4 = request.form.get("email4")
    email5 = request.form.get("email5")

    f = request.files['file']
    filename = f.filename.split("\\")[-1]
    f.save(secure_filename(filename))

    client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)
    client.upload_file(filename, "ccprjbucket", filename,
                       ExtraArgs={'GrantRead': 'uri="http://acs.amazonaws.com/groups/global/AllUsers"'})

    newFile = client.generate_presigned_url('get_object',
                                           Params={
                                               'Bucket': AWS_STORAGE_BUCKET_NAME,
                                               'Key': filename,
                                           },
                                           ExpiresIn=5000)

    conn = pymysql.connect(host=ENDPOINT, user=USR, password=PASSWORD, database=DBNAME)
    cur = conn.cursor()

    statement = f"INSERT INTO userdetails(email,password,description,email1,email2,email3,email4,email5,imagelocation) VALUES('" + email + "','" + password + "','" + desc + "','" + email1 + "','" + email2 + "','" + email3 + "','" + email4 + "','" + email5 + "' ,'" + filename + "');"
    cur.execute(statement)
    conn.commit()
    os.remove(filename)

    sns_client = boto3.client(
        'sns',
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
        region_name=AWS_REGION
    )

    emails = [email1,email2,email3,email4,email5]


    topic = sns_client.create_topic(Name="newSNStest2")
    topic_arn = topic["TopicArn"]
    protocol = 'email'
    endpoint = email
    subscription = sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol=protocol,
            Endpoint=endpoint,
            ReturnSubscriptionArn=True)['SubscriptionArn']

    lambda_client = boto3.client('lambda',
                                 aws_access_key_id=ACCESS_KEY,
                                 aws_secret_access_key=SECRET_KEY,
                                 region_name=AWS_REGION)

    lambda_payload = {"email": newFile}
    lambda_client.invoke(FunctionName='test',
                         InvocationType='Event',
                         Payload=json.dumps(lambda_payload))

    return redirect("/")


@app.route('/mainpage', methods=["GET"])
def mainpage():
    email = request.args.get('email')
    password = request.args.get('password')
    email1 = request.args.get('email1')
    email2 = request.args.get('email2')
    email3 = request.args.get('email3')
    email4 = request.args.get('email4')
    email5 = request.args.get('email5')

    try:
        conn = pymysql.connect(host=ENDPOINT, user=USR, password=PASSWORD, database=DBNAME)
        cur = conn.cursor()

        cur.execute(
            "SELECT * FROM userdetails Where email ='" + str(email) + "' AND password = '" + str(password) + "';")
        query_results = cur.fetchall()

        if len(query_results) == 1:
            return render_template("mainpage.html")
        else:
            return redirect("/notfound")

    except Exception as e:
        print("Database connection failed due to {}".format(e))
        return redirect("/")


@app.route('/search', methods=["POST"])
def search():
    email = request.form.get("email")
    return redirect("viewdetails/" + str(email))


@app.route('/viewdetails/<email>')
def viewdetails(email):
    try:
        conn = pymysql.connect(host=ENDPOINT, user=USR, password=PASSWORD, database=DBNAME)
        cur = conn.cursor()
        cur.execute("SELECT * FROM userdetails Where email ='" + email + "';")
        conn.commit()
        query_results = cur.fetchall()

        client = boto3.client('s3', aws_access_key_id=ACCESS_KEY, aws_secret_access_key=SECRET_KEY)

        url = client.generate_presigned_url('get_object',
                                            Params={
                                                'Bucket': 'ccprjbucket',
                                                'Key': 'images/' + str(query_results[0][8]),
                                            },
                                            ExpiresIn=3600)
        url = str(url).split('?')[0]

        item = {'email': query_results[0][0], 'password': query_results[0][1], 'desc': query_results[0][2], 'email1':query_results[0][3], 'email2':query_results[0][4], 'email3':query_results[0][5], 'email4':query_results[0][6], 'email5':query_results[0][7], 'link': url}
        print(item)

        return render_template("viewdetails.html", item=item)

    except Exception as e:
        print("Database connection failed due to {}".format(e))
        return redirect("/")


@app.before_first_request
def initialize():
    try:
        print("INITIALIZING DATABASE")
        conn = pymysql.connect(host=ENDPOINT, user=USR, password=PASSWORD, database=DBNAME)
        cur = conn.cursor()

        try:
            cur.execute(
                "CREATE TABLE userdetails(email VARCHAR(20), password VARCHAR(20), description VARCHAR(50), email1 VARCHAR(20), email2 VARCHAR(20), email3 VARCHAR(20), email4 VARCHAR(20), email5 VARCHAR(20), imagelocation VARCHAR(50));")
            print("table created")
        except:
            cur.execute(
                "INSERT INTO userdetails(email,password,description,email1,email2,email3,email4,email5,imagelocation) VALUES('test1@gmail.com','password','this is a desc','None','None','None','None','None', 'Default.png');")
            print("Insert Success")

            conn.commit()

        cur.execute("SELECT * FROM userdetails;")
        query_results = cur.fetchall()
        print(query_results)
        return redirect("/")

    except Exception as e:
        print("Database connection failed due to {}".format(e))
        return redirect("/")


if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8000)
