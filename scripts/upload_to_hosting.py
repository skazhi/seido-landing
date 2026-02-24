"""
Автоматическая загрузка файлов на хостинг reg.ru через FTP
"""
import ftplib
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Загружаем переменные окружения
env_path = Path(__file__).parent.parent / 'bot' / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Настройки FTP (замените на свои данные)
FTP_CONFIG = {
    'host': os.getenv('FTP_HOST', 'seidorun.ru'),
    'user': os.getenv('FTP_USER', 'u3426357'),
    'password': os.getenv('FTP_PASSWORD', ''),
    'port': int(os.getenv('FTP_PORT', 21)),
    'remote_dir': os.getenv('FTP_REMOTE_DIR', '/public_html'),
}

# Файлы для загрузки
FILES_TO_UPLOAD = [
    {
        'local': 'index.html',
        'remote': 'index.html',
        'description': 'Главная страница сайта'
    },
    {
        'local': 'api/api.php',
        'remote': 'api/api.php',
        'description': 'API для работы с базой данных'
    },
    {
        'local': 'seido_logo.png',
        'remote': 'seido_logo.png',
        'description': 'Логотип Seido'
    },
]


def create_remote_directory(ftp, remote_dir):
    """Создаёт директорию на FTP сервере, если её нет"""
    if not remote_dir or remote_dir == '.':
        return
    
    parts = [p for p in remote_dir.split('/') if p]
    current_path = ''
    
    for part in parts:
        current_path += '/' + part
        try:
            ftp.cwd(current_path)
        except:
            try:
                ftp.mkd(current_path)
                ftp.cwd(current_path)
            except Exception as e:
                print(f"  [!] Не удалось создать директорию {current_path}: {e}")


def upload_file(ftp, local_path, remote_path, base_dir):
    """Загружает один файл на FTP сервер"""
    try:
        # Переходим в базовую директорию
        ftp.cwd(base_dir)
        
        # Создаём директории, если нужно
        remote_dir = os.path.dirname(remote_path)
        if remote_dir:
            create_remote_directory(ftp, remote_dir)
            # Переходим в директорию файла
            if remote_dir:
                try:
                    ftp.cwd(remote_dir)
                except:
                    pass
        
        # Загружаем файл
        remote_filename = os.path.basename(remote_path)
        with open(local_path, 'rb') as file:
            ftp.storbinary(f'STOR {remote_filename}', file)
        
        print(f"  [OK] Загружен: {remote_path}")
        return True
    except Exception as e:
        print(f"  [ERROR] Ошибка при загрузке {remote_path}: {e}")
        return False


def main():
    """Основная функция загрузки"""
    print("=" * 60)
    print("Загрузка файлов на хостинг seidorun.ru")
    print("=" * 60)
    print()
    
    # Проверяем наличие файлов
    project_root = Path(__file__).parent.parent
    missing_files = []
    
    for file_info in FILES_TO_UPLOAD:
        local_path = project_root / file_info['local']
        if not local_path.exists():
            missing_files.append(file_info['local'])
            print(f"[!] Файл не найден: {file_info['local']}")
    
    if missing_files:
        print(f"\n❌ Не найдено файлов: {', '.join(missing_files)}")
        print("Проверьте, что все файлы на месте.")
        return
    
    # Проверяем настройки FTP
    if not FTP_CONFIG['password']:
        print("[!] Пароль FTP не указан!")
        print("\nСоздайте файл bot/.env и добавьте:")
        print("FTP_HOST=seidorun.ru")
        print("FTP_USER=u3426357")
        print("FTP_PASSWORD=ваш_пароль")
        print("FTP_REMOTE_DIR=/public_html")
        return
    
    # Подключаемся к FTP
    print(f"Подключение к FTP: {FTP_CONFIG['host']}...")
    print(f"   Пользователь: {FTP_CONFIG['user']}")
    print(f"   Порт: {FTP_CONFIG['port']}")
    print()
    
    try:
        ftp = ftplib.FTP()
        ftp.connect(FTP_CONFIG['host'], FTP_CONFIG['port'])
        print("[OK] Соединение установлено, авторизация...")
        ftp.login(FTP_CONFIG['user'], FTP_CONFIG['password'])
        ftp.encoding = 'utf-8'
        print("[OK] Авторизация успешна!")
        print()
    except ftplib.error_perm as e:
        print(f"[ERROR] Ошибка авторизации: {e}")
        print("\nПроверьте в панели reg.ru:")
        print("1. Раздел 'FTP-доступ' или 'Файловый менеджер'")
        print("2. Правильность логина (может быть полный: u3426357@seidorun.ru)")
        print("3. Правильность пароля FTP (может отличаться от пароля панели)")
        print("4. Попробуйте сбросить пароль FTP в панели")
        print("\nАльтернатива: используйте файловый менеджер reg.ru для загрузки")
        return
    except Exception as e:
        print(f"[ERROR] Ошибка подключения: {e}")
        print("\nПроверьте:")
        print("1. Правильность хоста (может быть IP: 31.31.196.247)")
        print("2. Доступность FTP сервера")
        print("3. Настройки файрвола")
        return
    
    try:
        # Переходим в рабочую директорию
        try:
            ftp.cwd(FTP_CONFIG['remote_dir'])
            print(f"Рабочая директория: {FTP_CONFIG['remote_dir']}")
        except:
            print(f"[!] Директория {FTP_CONFIG['remote_dir']} не найдена, используем корень")
        
        print()
        print("Начинаю загрузку файлов...")
        print()
        
        # Загружаем файлы
        uploaded = 0
        failed = 0
        
        for file_info in FILES_TO_UPLOAD:
            local_path = project_root / file_info['local']
            remote_path = file_info['remote']
            
            print(f"{file_info['description']}: {file_info['local']} -> {remote_path}")
            
            if upload_file(ftp, str(local_path), remote_path, FTP_CONFIG['remote_dir']):
                uploaded += 1
            else:
                failed += 1
            print()
        
        # Итоги
        print("=" * 60)
        print("[OK] Загрузка завершена!")
        print(f"   Успешно: {uploaded}")
        print(f"   Ошибок: {failed}")
        print("=" * 60)
        
        if uploaded > 0:
            print("\nПроверьте сайт:")
            print("   https://seidorun.ru")
            print("   https://seidorun.ru/api/api.php")
        
    except Exception as e:
        print(f"[ERROR] Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        ftp.quit()
        print("\nСоединение закрыто")


if __name__ == "__main__":
    main()
