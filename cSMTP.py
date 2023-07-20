import smtplib
import threading
import time
import requests
import socks
import csv
from email.message import EmailMessage
from email.mime.text import MIMEText
import imaplib
import email
from pathlib import Path
from datetime import datetime
import signal
import traceback
import socket
import numpy as np

class cSMTP():
    def __init__(self, proxies_file, emails_file, emails_test_file, smtp_file, imap_file, subject, layout_file, num_threads = 2, max_emails_per_session = 500, max_emails_per_hour = 100, seed_interval = 5, macro_fields = [], skip_test = False, no_real_send = False):
        '''Initializes custom SMTP class'''
        self.proxies = []
        self.smtps = []
        self.imaps = []
        # Set the number of threads to use
        self.num_threads = num_threads
        self.sent = {}
        self.sent['num_sent_without_proxy'] = 0
        self.sent["num_sent_with_proxy"] = 0
        # Define timeout SMTP server and Proxy when exceeded number of emails
        self.timeoutSMTPServers = []
        self.timeoutProxies = []

        # Set the number of seed emails to send after interval of emails sent
        self.seed_interval = seed_interval

        # Set the number of emails to send per session
        self.max_emails_per_session = max_emails_per_session

        # Set the max hourly rate per live SMTP
        self.max_emails_per_hour = max_emails_per_hour

        # Set the subject of the email
        self.subject = subject
        
        # Declare the number of emails sent through proxies
        self.num_sent_through_proxies = 0
        # Declare the number of emails sent through SMTP servers
        self.num_sent_through_smtp_server = 0

        #Declare skip test variable
        self.skip_test = skip_test

        #Declare skip real send variable
        self.no_real_send = no_real_send

        # Set the message of the email
        with open(layout_file, 'r') as file:
            self.message = file.read()

        # Define macro fields
        self.macro_fields = macro_fields

        # Load proxy list from a file
        proxy_list = cSMTP.load_file(proxies_file)
        for proxy in proxy_list:
            proxy_server = {}
            proxy_server['host'] = proxy.split(',')[0].split(':')[0]
            proxy_server['port'] = proxy.split(',')[0].split(':')[1]
            proxy_server['type'] = proxy.split(',')[1]
            if proxy.split(',')[2]:
                proxy_server['https'] = bool(proxy.split(',')[2])
            else :
                proxy_server['https'] = False
            self.proxies.append(proxy_server)

        # Load email list from a file
        self.email_list = cSMTP.load_file(emails_file)
        emails = []
        for email in self.email_list:
            _email = {}
            _email['to_address'] = email.split(',')[0]
            _email['to_name'] = email.split(',')[0]
            emails.append(_email)
        self.email_list = emails

        # Load email test list from a file
        self.email_test_list = cSMTP.load_file(emails_test_file)
        test_emails = []
        for test_email in self.email_test_list:
            _test_email = {}
            _test_email['to_address'] = test_email.split(',')[0]
            _test_email['to_name'] = test_email.split(',')[0]
            test_emails.append(_test_email)
        self.email_test_list = test_emails

        # Load SMTP list from a file
        smtp_list = cSMTP.load_file(smtp_file)
        for stmp in smtp_list:
            smtp_server = {}
            smtp_server['host'] = stmp.split(',')[0].split('@', 1)[0].split(':')[0]
            smtp_server['port'] = stmp.split(',')[0].split('@', 1)[0].split(':')[1]
            smtp_server['user'] = stmp.split(',')[0].split('@', 1)[1].split(':')[0]
            smtp_server['password'] = stmp.split(',')[0].split('@', 1)[1].split(':')[1]
            smtp_server['from_address'] = stmp.split(',')[1].split(':')[0]
            smtp_server['from_name'] = stmp.split(',')[1].split(':')[1]
            smtp_server['tls'] = True if stmp.split(',')[2].lower() == 'true' else False
            smtp_server['in_used'] = False
            self.smtps.append(smtp_server)

        # Load IMAP list from a file
        imap_list = cSMTP.load_file(imap_file)
        for imap in imap_list:
            imap_server = {}
            imap_server['host'] = imap.split(',')[0].split('@', 1)[0].split(':')[0]
            imap_server['port'] = imap.split(',')[0].split('@', 1)[0].split(':')[1]
            imap_server['user'] = imap.split(',')[0].split('@', 1)[1].split(':')[0]
            imap_server['password'] = imap.split(',')[0].split('@', 1)[1].split(':')[1]
            self.imaps.append(imap_server)

    @staticmethod
    def load_file(filename):
        '''Define a function to load file with TXT and CSV extension'''
        lines = []
        with open(filename, 'r') as f:
            if filename.endswith('.csv'):
                reader = csv.reader(f)
            elif filename.endswith('.txt'):
                reader = f.readlines()
            else:
                raise TypeError("Unknown file extension")
            
            for row in reader:
                lines.append(row.strip())
        return lines

    def __send(self, from_address, from_name, to_address, to_name, msg: EmailMessage, smtp_conn: smtplib.SMTP, proxy=False):
        '''Define a function to send an email message to a specified recipient with provided subject and message
        from a specified sender name and email address with macros fields.'''
        try:
            # Process Macros
            for macro_field in self.macro_fields:
                self.message = self.message.replace(f"{{{macro_field['key']}}}", macro_field['value'])
            
            # Send the email
            msg['From'] = "{} <{}>".format(from_name, from_address)
            msg['To'] = "{} <{}>".format(to_name, to_address)
            msg.add_alternative(MIMEText(self.message, 'html'), subtype='html')
            smtp_conn.send_message(msg, from_address, to_address)
            del msg['To']
            del msg['From']
            # Update the number of emails sent for this proxy
            if proxy:
                self.sent['num_sent_with_proxy'] += 1
                self.num_sent_through_proxies += 1
            else:
                self.sent['num_sent_without_proxy'] += 1
                self.num_sent_through_smtp_server += 1
            # Close the SMTP connection
            smtp_conn.quit()
            print(f"Email sent to {to_address} successfully")
        except Exception as e:
            smtp_conn.quit()
            print(traceback.print_exc(e))

    def __send_emails(self, email_list, smtp_list, proxies):
        '''Define a function to start send batch of emails'''
        msg = EmailMessage()
        i = 0
        
        # Loop through the email list
        for email in email_list:
            while True:
                # Choose an available proxy
                proxy = self.__choose_proxy(proxies)
                if proxy:
                    if proxy['type'] == 'socks4':
                        socks.set_default_proxy(socks.PROXY_TYPE_SOCKS4, proxy['host'], int(proxy['port']))
                        socks.wrap_module(smtplib)
                    elif proxy['type'] == 'socks5':
                        socks.set_default_proxy(socks.PROXY_TYPE_SOCKS5, proxy['host'], int(proxy['port']))
                        socks.wrap_module(smtplib)
                    elif proxy['type'] == 'http':
                        socks.set_default_proxy(socks.PROXY_TYPE_HTTP, proxy['host'], int(proxy['port']))
                        socks.wrap_module(smtplib)
                    else:
                        raise TypeError("Unknown proxy type")

                # Choose an available SMTP server
                smtp_server = self.__choose_smtp_server(smtp_list)
                if smtp_server is None:
                    # No available SMTP servers found, exit the loop
                    print("No available SMTP servers found.")
                    print("Will retry after 3 seconds.")
                    time.sleep(3)
                    continue
                smtp_conn = smtplib.SMTP(smtp_server['host'], smtp_server['port'], timeout=30)

                try:
                    print(f"Logging in to the SMTP server as {smtp_server['user']}:{smtp_server['password']}")
                    if smtp_server['tls']:
                        print("Changing SMTP server to TLS mode")
                        smtp_conn.starttls()
                        print("Changed SMTP server to TLS mode")
                    else:
                        print("TLS mode is not enabled. Using default mode.")
                    smtp_conn.login(smtp_server['user'], smtp_server['password'])
                    print(f"Logged in to SMTP server as {smtp_server['user']}:{smtp_server['password']}")
                    
                except smtplib.SMTPNotSupportedError as e:
                    if "STARTTLS" in str(e):
                        print("SMTP not supported TLS mode. Using default mode.")
                        smtp_conn.ehlo()
                        smtp_conn.login(smtp_server['user'], smtp_server['password'])
                        print(f"Logged in to SMTP server as {smtp_server['user']}:{smtp_server['password']}")
                except Exception as e:
                    print(f"Could not login to SMTP server as {smtp_server['user']}:{smtp_server['password']}")
                    print("Error:")
                    print(e)
                    break
                smtp_server['in_used'] = True               

                if self.skip_test == False:
                    print("Start send test mail")
                    if i % self.seed_interval == 0:
                        self.__test_seed(smtp_server['from_address'], smtp_server['from_name'], smtp_conn)

                if self.no_real_send == False:
                    print("Start send mail")
                    try:
                        if proxy:
                            # Check if the number of emails sent per session has been exceeded
                            if self.sent["num_sent_with_proxy"] < self.max_emails_per_session:
                                self.__send(smtp_server['from_address'], smtp_server['from_name'], email['to_address'], email['to_name'], msg, smtp_conn, True)
                            elif self.sent['num_sent_with_proxy'] == self.max_emails_per_session:
                                self.timeoutProxies[self.timeoutProxies.index(proxy)]['time_reset'] = time.time() + 3600
                                self.__send(smtp_server['from_address'], smtp_server['from_name'], email['to_address'], email['to_name'], msg, smtp_conn, True)
                        else:
                            # Check if the max hourly rate per live SMTP has been exceeded
                            if self.sent['num_sent_without_proxy'] < self.max_emails_per_hour:
                                self.__send(smtp_server['from_address'], smtp_server['from_name'], email['to_address'], email['to_name'], msg, smtp_conn, False)
                            elif self.sent['num_sent_without_proxy'] == self.max_emails_per_hour:
                                self.timeoutSMTPServers[self.timeoutSMTPServers.index(smtp_server)]['time_reset'] = time.time(
                                ) + 3600
                                self.__send(smtp_server['from_address'], smtp_server['from_name'], email['to_address'], email['to_name'], msg, smtp_conn, False)
                    except Exception as e:
                        # Log the error
                        print(f"Error sending email: {traceback.print_exc(e)}")
                        smtp_conn.close()
                break

    def __check_smtp_server(self, smtp_server):
        '''Define a function to check if SMTP server is active?'''
        try:
            host, port = smtp_server['host'], int(smtp_server['port'])
            # Try to connect to SMTP server and check its status
            smtp_conn = smtplib.SMTP(host, port, timeout=30)
            status = smtp_conn.noop()[0]
            print(f"SMTP server {smtp_server} status: {status}")
            smtp_conn.quit()
            return True
        except Exception as e:
            # SMTP server is down or unreachable
            print(f"SMTP server {smtp_server} is down or unreachable.")
            return False

    def __choose_smtp_server(self, smtp_list):
        '''Define a function to check over the list of SMTP servers'''
        # Iterate through the list of SMTP servers
        for smtp_server in smtp_list:
            # Check if the SMTP server is available
            if self.__check_smtp_server(smtp_server) and smtp_server['in_used'] == False:
                if smtp_server in self.timeoutSMTPServers:
                    if self.timeoutSMTPServers[self.timeoutSMTPServers.index(smtp_server)]['time_reset'] >= time.time():
                        del self.timeoutSMTPServers[self.timeoutSMTPServers.index(smtp_server)]
                        # Reset the number of emails sent without proxy
                        self.sent['num_sent_with_proxy'] = 0

                        # SMTP server is available, return its address
                        return smtp_server
                    else:
                        continue
                else:
                    # SMTP server is available, return its address
                    return smtp_server
        # No available SMTP server found
        return None

    def __check_proxy(self, proxy):
        '''Define a function to check if proxy is working or not?'''
        try:
            if proxy['https']:
                response = requests.get('https://www.google.com/', proxies={'https': f'{proxy["type"]}://{proxy["host"]}:{proxy["port"]}'})
                print(f"Proxy {proxy} status: {response.status_code}")
            else :
                response = requests.get('http://www.google.com/', proxies={'http': f'{proxy["type"]}://{proxy["host"]}:{proxy["port"]}'})
                print(f"Proxy {proxy} status: {response.status_code}")
            return True
        except requests.exceptions.RequestException as e:
            # Proxy is down or unreachable
            print(f"Proxy {proxy} is down or unreachable.")
            return False

    def __choose_proxy(self, proxies):
        '''Define a function to check over the list of proxies'''
        # Iterate through the list of proxies
        for proxy in proxies:
            # Check if the SMTP server is available
            if self.__check_proxy(proxy):
                if proxy in self.timeoutProxies:
                    if self.timeoutProxies[self.timeoutProxies.index(proxy)]['time_reset'] >= time.time():
                        del self.timeoutProxies[self.timeoutProxies.index(proxy)]
                        # Reset the number of emails sent without proxy
                        self.sent['num_sent_without_proxy'] = 0

                        # SMTP server is available, return its address
                        return proxy
                    else:
                        continue
                else:
                    # SMTP server is available, return its address
                    return proxy
        # No available SMTP server found
        return None

    def __even_split(self, list):
        '''Split a list of smtps or proxies to number of threads sublists'''
        k, m = divmod(len(list), self.num_threads)
        return [list[i * k + min(i, m):(i + 1) * k + min(i + 1, m)] for i in range(self.num_threads)]

    def __test_seed(self, from_address, from_name, smtp_conn: smtplib.SMTP):
        try:
            html = "This is a test email message."
            msg = EmailMessage()
            msg.add_alternative(MIMEText(html, "html"), subtype='html')
            msg['Subject'] = "This is a test email message."
            msg['From'] = "{} <{}>".format(from_name, from_address)
            for email_test in self.email_test_list:
                msg['To'] = "{} <{}>, ".format(email_test['to_name'], email_test['to_address'])
                smtp_conn.send_message(msg, from_address, email_test['to_address'])
                del msg['To']
            return True
        except Exception as e:
            print(f"Error sending test email: {traceback.print_exc(e)}")
            return False
        
    def __verify_email_list(self, imap_host, imap_username, imap_password, imap_port=993, verify=True):
        """
        Verifies a list of email addresses, checking for bounces and replies from the email server,
        and creating a list of dead email addresses. Set Verify to False to skip this step. If provided with
        a username and password, email authentication will occur in the verification step.
        """
        print("Finding dead email addresses...")

        dead_emails = []  # List of dead email addresses
        live_emails = [] # List of live email addresses

        for email in self.email_list:
            try:
                if verify:
                    # Check for any bounced messages
                    imap_server = imaplib.IMAP4_SSL(imap_host, imap_port)
                    imap_server.login(imap_username, imap_password)  # Only needed if email authentication is required
                    imap_server.select('INBOX')

                    # search_criteria = f'(OR SUBJECT "fail" (OR SUBJECT "undeliver" SUBJECT "returned")) (OR FROM "Delivery")'
                    search_criteria = f'HEADER "X-Failed-Recipients" "{email["to_address"]}"'
                    result, data = imap_server.search(None, search_criteria)
                    if result == 'OK' and data[0] != b'':
                        # Email bounced - add email address to list of dead emails
                        dead_emails.append(email["to_address"])
                    else:
                        live_emails.append(email["to_address"])

            except Exception as e:
                # Error occurred - consider email address dead and add to list of dead emails
                dead_emails.append(email["to_address"])
                print(f'Error verifying email {email["to_address"]}: {str(e)}')

        print("Checked all dead email addresses!")
        # Return list of dead email addresses
        return dead_emails, live_emails
    
    def create_thread(self):
        '''Define a function to create a thread'''
        # Divide big list into many sublists
        sublists_smtps = self.__even_split(self.smtps)
        sublists_proxies = self.__even_split(self.proxies)
        sublists_mails = self.__even_split(self.email_list)
        sublists_test_mails = self.__even_split(self.email_test_list)

        threads = []

        # Start sending emails on different threads
        for i in range(0, len(sublists_smtps)):
            sublist_smtps = sublists_smtps[i]
            sublist_proxies = sublists_proxies[i]
            sublist_mails = sublists_mails[i]
            sublist_test_mails = sublists_test_mails[i]

            # Create the thread
            thread = threading.Thread(
                target=self.__send_emails, args=(sublist_mails, sublist_smtps, sublist_proxies), daemon=True)
            # Start the thread
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

        time.sleep(15)

        dead_emails_list = []
        live_emails_list = []

        for imap_server in self.imaps:
            dead_emails, live_emails = self.__verify_email_list(imap_server['host'], imap_server['user'], imap_server['password'], imap_server['port'])
            dead_emails_list += dead_emails
            live_emails_list += live_emails
        
        dead_emails_list = np.unique(dead_emails_list)
        live_emails_list = np.unique(live_emails_list)

        return dead_emails_list.tolist(), live_emails_list.tolist()
    
    def start(self):
        '''Start sending emails'''
        print('Creating many threads to send emails...')
        dead_emails_list, live_emails_list = self.create_thread()

        live_emails_list = [x for x in live_emails_list if x not in dead_emails_list]

        # Print the reporting
        print("\n")
        print('All emails had been sent. There is the report: ')
        print(f'Number of dead emails: {len(dead_emails_list)}')
        print(f'Number of sent emails: {len(live_emails_list)}')
        print(f'Number of emails sent without proxy: {self.num_sent_through_smtp_server}')
        print(f'Number of emails sent with proxy: {self.num_sent_through_proxies}')

        # Save dead emails to disk
        print(f'Saving dead emails to disk...')
        dead_emails_filename = "/dead_emails_" + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        dead_emails_path = str(Path(__file__).parent.absolute()) + dead_emails_filename
        with open(dead_emails_path, 'w') as fp:
            for dead_email in dead_emails_list:
                # write each item on a new line
                fp.write("%s\n" % dead_email)
        print(f'Dead emails has been saved to disk at {dead_emails_path}.txt')

        # Save live emails to disk
        print(f'Saving live emails to disk...')
        live_emails_filename = "/live_emails_" + datetime.now().strftime("%Y-%m-%d %H-%M-%S")
        live_mails_path = str(Path(__file__).parent.absolute()) + live_emails_filename
        with open(live_mails_path, 'w') as fp:
            for live_email in live_emails_list:
                # write each item on a new line
                fp.write("%s\n" % live_email)
        print(f'Live emails has been saved to disk at {live_mails_path}.txt')
    
    @staticmethod
    def auto_unsubscribe(imap_server, username, password, unsubscribe_link):
        """
        Automatically unsubscribes email addresses when they reply with an unsubscribe request.
        imap_server: the IMAP server to use
        username: the username for the email account
        password: the password for the email account
        unsubscribe_link: the unsubscribe link to look for in email replies
        """
        # Connect to the IMAP server and select the INBOX folder
        imap_conn = imaplib.IMAP4_SSL(imap_server)
        imap_conn.login(username, password)
        imap_conn.select('INBOX')

        # Initialize a list to store unsubscribe email addresses
        unsubscribe_list = []

        # Search for email replies that contain the unsubscribe link
        result, data = imap_conn.search(None, 'FROM "" SUBJECT "Re: " BODY "{0}"'.format(unsubscribe_link))

        # Loop through the matching emails and get the email address to unsubscribe
        for num in data[0].split():
            result, data = imap_conn.fetch(num, "(RFC822)")
            email_body = data[0][1]
            mail = email.message_from_bytes(email_body)

            # Get the email address to unsubscribe from the email headers
            unsubscribe_address = mail['From']

            # Add the email address to the unsubscribe list
            unsubscribe_list.append(unsubscribe_address)

            # [TODO: Insert code to actually unsubscribe the email address]

        # Disconnect from the server
        imap_conn.close()
        imap_conn.logout()

        # Return the list of email addresses to unsubscribe
        return unsubscribe_list