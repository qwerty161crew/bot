import logging

import os
import time
import requests


from telegram import Bot


from dotenv import load_dotenv
from exceptions import TokenError, ResponseError
load_dotenv()
logging.basicConfig(format=f'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
telegram_token = os.getenv('TELEGRAM_TOKEN')
practicum_tocen = os.getenv('PRACTICUM_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {practicum_tocen}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    if telegram_token is None:
        raise TokenError('Отсутсвует токен телеграм API')
    if practicum_tocen is None:
        raise TokenError('Отсутсвует токен API Practicum')
    if chat_id is None:
        raise TokenError('Отсутсвует id чата')


def send_message(bot, message):
    bot.send_message(
        chat_id=chat_id,
        message=message
    )


def get_api_answer(timestamp):
    payload = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    return response.json()


def check_response(response):
    if response.get('homeworks') is None:
        raise ResponseError('В ответе от сервера отсутсвует поле: homeworks')
    if response.get('current_date') is None:
        raise ResponseError(
            'В ответе от сервера отсутсвует поле: current_date')


def parse_status(homework):
    return HOMEWORK_VERDICTS[homework['status']]


def main():
    """Основная логика работы бота."""
    try:
        check_tokens()
    except TokenError as exc:
        print(exc)
        return

    timestamp = int(time.time())
    response = get_api_answer(timestamp)
    try:
        check_response(response)
    except ResponseError as exc:
        print(exc)
        return

    for homework in response['homeworks']:
        message = parse_status(homework)

    bot = Bot(token=telegram_token)

    while True:
        try:
            time.sleep(10)
            send_message(bot, message)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'


if __name__ == '__main__':
    main()
