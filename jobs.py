import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pymongo import MongoClient

from numbers_list import numbers_list


current_date = datetime.now().date()
str_current_date = current_date.strftime("%Y-%m-%d")
one_day_before = current_date - timedelta(days=1)
str_one_day_before = one_day_before.strftime("%Y-%m-%d")


email_subject = "Child questionare check"
smtp_server = 'smtp.gmail.com'
smtp_port = 587

to_emails = ["smolynets@gmail.com", "oksana.mavdryk25@gmail.com"]
from_email = "smolynets2@gmail.com"
email_app_password = os.getenv("EMAIL_APP_PASSWORD")


mongo_uri = os.getenv("MONGO_URI")
client = MongoClient(mongo_uri)
db = client.questionare_lists_db
collection = db.questionare_lists


def send_to_mongodb(q_list):
    data = {"date": str_current_date, "value": q_list}
    result = collection.insert_one(data)
    print(f"Document inserted with ID: {result.inserted_id}")


def get_from_mongodb():
    query = {"date": str_one_day_before}
    document = collection.find_one(query)
    if document:
        return document["value"]

def send_html_email(email_subject, to_emails, from_email, email_app_password, missing_elements):
    email_html_body = f"""
    <html>
    <body>
    <h1>{current_date.strftime("%d %B")} - Child questionare check</h1>
    <ul>
    """
    email_html_body += f"<li><strong>Нові анкети на сайті: {missing_elements}</strong></li>\n"
    email_html_body += "<br>"
    email_html_body += """
        </ul>
        </body>
        </html>
    """

    # Create the MIME message
    message = MIMEMultipart()
    message['From'] = from_email
    message['To'] = ", ".join(to_emails)
    message['Subject'] = email_subject

    # Attach the HTML body with UTF-8 encoding
    message.attach(MIMEText(email_html_body, 'html', 'utf-8'))

    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()  # Start TLS Encryption
        server.login(from_email, email_app_password)
        server.send_message(message)

def main():
    total_child_list = []
    for page_number in range(60):
        page_number += 1
        url = f"https://www.msp.gov.ua/children/search.php?form=%D0%9D%D0%B0%D1%86%D1%96%D0%BE%D0%BD%D0%B0%D0%BB%D1%8C%D0%BD%D0%B5+%D1%83%D1%81%D0%B8%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%BD%D1%8F&male=*&age_from=0&age_to=10&region=*&brothers=no&needs=no&number=&page={page_number}"
    
        email_messages = {}

        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        child_items = soup.find_all('div', class_='child__item')
        page_child_list = []
        for item in child_items:
            url = item.find('a')['href']
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            number = query_params.get('n', [None])[0]
            page_child_list.append(number)
        total_child_list.extend(page_child_list)
    last_day_result = get_from_mongodb()
    if last_day_result:
        missing_elements = [item for item in total_child_list if item not in last_day_result]
        if missing_elements:
            print(missing_elements)
            send_html_email(email_subject, to_emails, from_email, email_app_password, missing_elements)
    send_to_mongodb(total_child_list)


if __name__ == '__main__':
    main()
