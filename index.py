from cSMTP import cSMTP

if __name__ == '__main__':
    smtp = cSMTP('proxies_list.txt', 
                 'emails_list.txt',
                 'smtp_list.txt')
