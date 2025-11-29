import requests
import json
import time
import logging
from tqdm import tqdm
from config import *


def validate_text(text):

    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        text = text.replace(char, '_')
    return text.strip()


class CatBackup:
    def __init__(self, yandex_token, folder_name=FOLDER_NAME):
        self.yandex_token = yandex_token
        self.folder_name = folder_name
        self.headers = {
            'Authorization': f'OAuth {self.yandex_token}',
            'Content-Type': 'application/json'
        }
        self.backup_info = []

        # Настройка логирования
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('backup.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def check_yandex_token(self):

        url = YANDEX_DISK_INFO_URL

        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                user_data = response.json()
                user_name = user_data.get('user', {}).get('display_name', 'Неизвестно')
                self.logger.info(f"Токен валиден. Пользователь: {user_name}")
                return True
            else:
                self.logger.error(f"Неверный токен. Код ошибки: {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка соединения с Яндекс.Диском: {e}")
            return False

    def create_folder_on_yandex(self):

        url = YANDEX_DISK_BASE_URL
        params = {
            'path': f'/{self.folder_name}'
        }

        try:
            response = requests.put(url, headers=self.headers, params=params)

            if response.status_code == 201:
                self.logger.info(f"Папка '{self.folder_name}' успешно создана на Яндекс.Диске")
                return True
            elif response.status_code == 409:
                self.logger.info(f"Папка '{self.folder_name}' уже существует на Яндекс.Диске")
                return True
            elif response.status_code == 401:
                self.logger.error("Ошибка авторизации. Проверьте токен Яндекс.Диска")
                return False
            else:
                self.logger.error(f"Ошибка при создании папки: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка соединения: {e}")
            return False

    def get_cat_image(self, text):

        url = CATAAS_API_URL.format(text)

        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                self.logger.info(f"Картинка с текстом '{text}' успешно получена")
                return response.content
            else:
                self.logger.error(f"Ошибка при получении картинки: {response.status_code}")
                return None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при загрузке картинки: {e}")
            return None

    def upload_to_yandex_disk(self, image_data, filename):


        upload_url = YANDEX_DISK_UPLOAD_URL
        params = {
            'path': f'/{self.folder_name}/{filename}.jpg',
            'overwrite': 'true'
        }

        try:

            response = requests.get(upload_url, headers=self.headers, params=params)

            if response.status_code != 200:
                self.logger.error(f"Ошибка получения ссылки для загрузки: {response.status_code}")
                return None

            upload_data = response.json()
            href = upload_data['href']


            upload_response = requests.put(href, data=image_data, headers={'Content-Type': 'image/jpeg'})

            if upload_response.status_code == 201:
                self.logger.info(f"Файл '{filename}.jpg' успешно загружен")


                file_info = self.get_file_info(filename)
                return file_info
            else:
                self.logger.error(f"Ошибка загрузки файла: {upload_response.status_code}")
                return None

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при загрузке на Яндекс.Диск: {e}")
            return None

    def get_file_info(self, filename):

        url = YANDEX_DISK_BASE_URL
        params = {
            'path': f'/{self.folder_name}/{filename}.jpg'
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code == 200:
                file_data = response.json()
                return {
                    'filename': f"{filename}.jpg",
                    'size': file_data.get('size', 0),
                    'created': file_data.get('created', ''),
                    'modified': file_data.get('modified', ''),
                    'path': file_data.get('path', ''),
                    'text': filename
                }
            else:
                return {
                    'filename': f"{filename}.jpg",
                    'size': 0,
                    'created': '',
                    'modified': '',
                    'path': f'/{self.folder_name}/{filename}.jpg',
                    'text': filename
                }
        except Exception as e:
            self.logger.error(f"Ошибка при получении информации о файле: {e}")
            return {
                'filename': f"{filename}.jpg",
                'size': 0,
                'created': '',
                'modified': '',
                'path': f'/{self.folder_name}/{filename}.jpg',
                'text': filename
            }

    def save_backup_info(self):

        if not self.backup_info:
            self.logger.warning("Нет информации для сохранения")
            return None

        timestamp = int(time.time())
        filename = f'cat_backup_info_{timestamp}.json'

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.backup_info, f, ensure_ascii=False, indent=2)
            self.logger.info(f"Информация о {len(self.backup_info)} файлах сохранена в: {filename}")
            return filename
        except Exception as e:
            self.logger.error(f"Ошибка при сохранении JSON файла: {e}")
            return None

    def backup_cat_images(self, texts):

        self.logger.info("Начинаем резервное копирование картинок с котиками...")


        if not self.check_yandex_token():
            return False


        if not self.create_folder_on_yandex():
            return False

        successful_uploads = 0


        with tqdm(total=len(texts), desc="Загрузка картинок", unit="file") as pbar:
            for text in texts:

                validated_text = validate_text(text)


                image_data = self.get_cat_image(text)

                if image_data:

                    file_info = self.upload_to_yandex_disk(image_data, validated_text)

                    if file_info:
                        self.backup_info.append(file_info)
                        successful_uploads += 1
                        pbar.set_postfix({"status": " успешно", "file": f"{validated_text}.jpg"})
                    else:
                        pbar.set_postfix({"status": " ошибка", "file": f"{validated_text}.jpg"})
                else:
                    pbar.set_postfix({"status": " ошибка", "file": f"{validated_text}.jpg"})

                pbar.update(1)
                time.sleep(1)


        json_filename = self.save_backup_info()


        print(f"\n{'=' * 50}")
        print(" РЕЗЕРВНОЕ КОПИРОВАНИЕ ЗАВЕРШЕНО!")
        print(f"{'=' * 50}")
        print(f" Успешно загружено: {successful_uploads} из {len(texts)} картинок")
        print(f" Папка на Яндекс.Диске: {self.folder_name}")
        if json_filename:
            print(f" Файл с информацией: {json_filename}")
        print(f" Лог операции: backup.log")

        return successful_uploads > 0


def main():
    print(" РЕЗЕРВНОЕ КОПИРОВАНИЕ КАРТИНОК С КОТИКАМИ НА ЯНДЕКС.ДИСК")
    print("=" * 60)


    if not YANDEX_TOKEN:
        yandex_token = input(" Введите ваш токен Яндекс.Диска: ").strip()
        if not yandex_token:
            print(" Токен не может быть пустым!")
            return
    else:
        yandex_token = YANDEX_TOKEN
        print(" Токен загружен из переменных окружения")

    print("\n ВВЕДИТЕ ТЕКСТЫ ДЛЯ КАРТИНОК С КОТИКАМИ")
    print("(для завершения введите 'stop' или оставьте пустую строку)")
    print("-" * 60)

    texts = []
    counter = 1

    while True:
        text = input(f"Текст для картинки {counter}: ").strip()

        if text.lower() == 'stop' or not text:
            break

        texts.append(text)
        counter += 1

    if not texts:
        print(" Не введено ни одного текста для картинок!")
        return

    print(f"\n БУДЕТ СОЗДАНО {len(texts)} КАРТИНОК С ТЕКСТАМИ:")
    for i, text in enumerate(texts, 1):
        print(f"  {i}. '{text}'")

    confirm = input("\n Начать резервное копирование? (y/n): ").strip().lower()
    if confirm not in ['y', 'yes', 'д', 'да']:
        print(" Операция отменена")
        return

    print()


    backup_manager = CatBackup(yandex_token)
    backup_manager.backup_cat_images(texts)


if __name__ == "__main__":
    main()