import smtplib
import email.message


def trigger_mail(sent_from, to, host, password, subject, recipientname, mailbody):
    email_content = """
    <html><body style='background-color:powderblue;'>
    """ + mailbody + """<br/><br/>
    Regards,<br/>
    DevOps Enabler & Co.
    </body></html>
    """
    msg = email.message.Message()
    msg['Subject'] = subject
    msg['From'] = sent_from
    msg['To'] = to
    msg.add_header('Content-Type', 'text/html')
    msg.set_payload(email_content)
    try:
        server = smtplib.SMTP(host, 587)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(msg['From'], password)
        server.sendmail(msg['From'], [msg['To']], msg.as_string())
        server.close()
        return 'Email sent!'
    except Exception as e:
        return 'Something went wrong...' + str(e)
