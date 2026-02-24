"""
Экспорт данных из SQLite в SQL файл для импорта в MySQL через phpMyAdmin
"""
import sqlite3
import json
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "seido.db")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "seido_export.sql")

if not os.path.exists(DB_PATH):
    print(f"❌ Файл базы данных не найден: {DB_PATH}")
    exit(1)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("🔄 Экспорт данных из SQLite...")

with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
    f.write("-- Экспорт данных Seido из SQLite\n")
    f.write(f"-- Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write("SET FOREIGN_KEY_CHECKS=0;\n\n")
    
    # Экспорт бегунов
    print("  📊 Экспорт бегунов...")
    cursor.execute("SELECT * FROM runners")
    runners = cursor.fetchall()
    
    if runners:
        f.write("-- Бегуны\n")
        f.write("DELETE FROM runners;\n")
        for row in runners:
            values = []
            for key in row.keys():
                val = row[key]
                if val is None:
                    values.append("NULL")
                elif isinstance(val, str):
                    # Экранируем кавычки
                    val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                    values.append(f"'{val_escaped}'")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    values.append(f"'{str(val)}'")
            
            columns = ', '.join(row.keys())
            values_str = ', '.join(values)
            f.write(f"INSERT INTO runners ({columns}) VALUES ({values_str});\n")
        print(f"    ✅ Экспортировано {len(runners)} бегунов")
    
    # Экспорт забегов
    print("  🏃 Экспорт забегов...")
    cursor.execute("SELECT * FROM races")
    races = cursor.fetchall()
    
    # Колонки, которые есть в MySQL (исключаем organizer_id и другие несуществующие)
    mysql_race_columns = ['id', 'name', 'date', 'location', 'organizer', 'race_type', 
                          'distances', 'website_url', 'protocol_url', 'is_active', 
                          'created_at', 'updated_at']
    
    if races:
        f.write("\n-- Забеги\n")
        f.write("DELETE FROM races;\n")
        for row in races:
            values = []
            columns = []
            
            # Фильтруем только существующие колонки
            for key in mysql_race_columns:
                if key in row.keys():
                    columns.append(key)
                    val = row[key]
                    if val is None:
                        values.append("NULL")
                    elif isinstance(val, str):
                        val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                        values.append(f"'{val_escaped}'")
                    elif isinstance(val, (int, float)):
                        values.append(str(val))
                    elif isinstance(val, dict) or (isinstance(val, str) and val.startswith('{')):
                        # JSON данные
                        if isinstance(val, str):
                            val_escaped = val.replace("'", "''")
                        else:
                            val_escaped = json.dumps(val, ensure_ascii=False).replace("'", "''")
                        values.append(f"'{val_escaped}'")
                    else:
                        values.append(f"'{str(val)}'")
            
            columns_str = ', '.join(columns)
            values_str = ', '.join(values)
            f.write(f"INSERT INTO races ({columns_str}) VALUES ({values_str});\n")
        print(f"    ✅ Экспортировано {len(races)} забегов")
    
    # Экспорт результатов
    print("  🏆 Экспорт результатов...")
    cursor.execute("SELECT * FROM results")
    results = cursor.fetchall()
    
    if results:
        f.write("\n-- Результаты\n")
        f.write("DELETE FROM results;\n")
        for row in results:
            values = []
            for key in row.keys():
                val = row[key]
                if val is None:
                    values.append("NULL")
                elif isinstance(val, str):
                    val_escaped = val.replace("'", "''").replace("\\", "\\\\")
                    values.append(f"'{val_escaped}'")
                elif isinstance(val, (int, float)):
                    values.append(str(val))
                else:
                    values.append(f"'{str(val)}'")
            
            columns = ', '.join(row.keys())
            values_str = ', '.join(values)
            f.write(f"INSERT INTO results ({columns}) VALUES ({values_str});\n")
        print(f"    ✅ Экспортировано {len(results)} результатов")
    
    f.write("\nSET FOREIGN_KEY_CHECKS=1;\n")

conn.close()

print(f"\n✅ Экспорт завершён: {OUTPUT_FILE}")
print(f"\n📤 Теперь импортируйте этот файл в phpMyAdmin:")
print(f"   1. Откройте phpMyAdmin")
print(f"   2. Выберите базу u3426357_seido")
print(f"   3. Вкладка 'Импорт' → выберите файл → 'Вперёд'")
