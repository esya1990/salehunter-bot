import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Название твоего JSON-файла с ключом
CREDENTIALS_FILE = 'honestalmatybot-b81f425fb588.json'  # <-- здесь укажи своё имя JSON!

# Подключение к Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
gc = gspread.authorize(credentials)

# ID твоей таблицы
spreadsheet_id = '1nPcx56Y0FQ0Y0754BPuUp2i_zSjb1KW1N586PhsCNVY'
sheet = gc.open_by_key(spreadsheet_id).sheet1

# Получение всех записей
records = sheet.get_all_records()

# Вывод всех товаров
for record in records:
    print(record)
