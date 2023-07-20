from cSMTP import cSMTP
import csv

if __name__ == '__main__':
    smtp = cSMTP('proxies_list.txt',
                 'emails_list.txt',
                 'emails_test_list.txt',
                 'smtp_list.txt',
                 'imap_list.txt',
                 'test cSMTP',
                 './template/test.html',
                 skip_test=True
                 )
    smtp.start()