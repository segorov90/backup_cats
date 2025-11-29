import os
from dotenv import load_dotenv

load_dotenv()

# Конфигурация API
CATAAS_API_URL = "https://cataas.com/cat/says/{}?width=500&height=500&color=orange&type=square"
YANDEX_DISK_UPLOAD_URL = "https://cloud-api.yandex.net/v1/disk/resources/upload"
YANDEX_DISK_BASE_URL = "https://cloud-api.yandex.net/v1/disk/resources"
YANDEX_DISK_INFO_URL = "https://cloud-api.yandex.net/v1/disk"

# Название папки (замените на название вашей группы в Нетологии)
FOLDER_NAME = "Netology-Group-140"

# Получение токена из переменных окружения
YANDEX_TOKEN = os.getenv('YANDEX_TOKEN')