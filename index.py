from cSMTP import cSMTP
import yaml
from yaml.loader import SafeLoader
import json

if __name__ == '__main__':
    try:
        with open('configs.yaml') as f:
            data = yaml.load(f, Loader=SafeLoader)

            smtp = cSMTP(proxies_file=data['proxies_file'],
                        emails_file=data['emails_file'],
                        emails_test_file=data['emails_test_file'],
                        smtp_file=data['smtp_file'],
                        imap_file=data['imap_file'],
                        subject=data['subject'],
                        message_file=data['message_file'],
                        num_threads=data['num_threads'],
                        max_emails_per_session=data['max_emails_per_session'],
                        max_emails_per_hour=data['max_emails_per_hour'],
                        seed_interval=data['seed_interval'],
                        macro_fields=data['macro_fields'],
                        skip_test=data['skip_test'],
                        no_real_send=data['no_real_send'],
                        html_email=data['html_email']
                        )
            smtp.start()
    except Exception as e:
        print(e)