import logging

logger = logging.getLogger('Providence')
logger.setLevel(logging.INFO)

handler = logging.FileHandler('bot.log') 
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

logger.addHandler(handler)
logger.propagate = False