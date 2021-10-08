import os


MODE = os.environ.get('APP_MODE')
DEBUG = MODE not in ['PROD', 'STAGE']

if MODE in ['PROD', 'STAGE']:
    import config.secrets as secrets
else:
    import config.secrets_local as secrets


DATABASE_URI = 'mysql://ffuser:{}@mysql_ibt/ibt'.format(secrets.DATABASE_PASSWORD)

if MODE == 'PROD':
    DATABASE_URI = 'mysql://ffuser:{}@{}/ff'.format(secrets.DATABASE_PROD_PASSWORD, secrets.DATABASE_PROD_IP)

if MODE == 'STAGE':
    DATABASE_URI = 'mysql://ffuser:{}@{}/ff'.format(secrets.DATABASE_STAGE_PASSWORD, secrets.DATABASE_STAGE_IP)
