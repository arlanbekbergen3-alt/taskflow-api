import os

# Список файлов для сборки (как ты указал)
files_to_collect = [
    "asf.py",
    "core/config.py",
    "core/security.py",
    "db/base.py",
    "db/database.py",
    "models/user.py",
    "models/task.py",
    "models/category.py",
    "schemas/user.py",
    "schemas/task.py",
    "schemas/category.py",
    "repositories/user.py",
    "repositories/task.py",
    "repositories/category.py",
    "services/user.py",
    "services/task.py",
    "services/category.py",
    "routers/auth.py",
    "routers/tasks.py",
    "routers/categories.py"
]

output_file = "project_code.txt"

with open(output_file, "w", encoding="utf-8") as out:
    out.write("### ДЕРЕВО ПРОЕКТА ###\n\n")
    # Генерируем дерево структуры
    for f in files_to_collect:
        out.write(f"- {f}\n")

    out.write("\n\n### СОДЕРЖИМОЕ ФАЙЛОВ ###\n\n")

    # Собираем код
    for file_path in files_to_collect:
        out.write(f"='='='='='='='='='='='='='='='='='='='='\n")
        out.write(f"ФАЙЛ: {file_path}\n")
        out.write(f"='='='='='='='='='='='='='='='='='='='='\n\n")

        if os.path.exists(file_path):
            with open(file_path, "r", encoding="utf-8") as f:
                out.write(f.read())
        else:
            out.write("# [Файл не найден или еще не создан]\n")
        out.write("\n\n")

print(f"Готово! Все файлы собраны в {output_file}")