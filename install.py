import subprocess
import sys

# Список библиотек для установки
libraries = ["disnake", "requests", "aiosqlite", "openai", "datetime", "asyncio"]

print("Установка библиотек...")

# Функция для установки библиотек через pip
def install_libraries():
    try:
        for library in libraries:
            print(f"Устанавливаю {library}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", library])
        print("Библиотеки были успешно установлены.")
    except subprocess.CalledProcessError:
        print("Произошла ошибка при установке библиотек.")
        sys.exit(1)

if __name__ == "__main__":
    install_libraries()
