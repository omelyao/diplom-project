import os
import json
import requests
import streamlit as st
from datetime import datetime
from dotenv import load_dotenv
from PIL import Image
import base64
import io

# === Загрузка .env ===
load_dotenv()
API_URL = os.getenv("API_URL")
API_KEY = os.getenv("API_KEY")
MODEL = "deepseek/deepseek-r1:free"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
RESULTS_FILE = "ege_results.json"
LEVELS_FILE = "ege_levels.json"
USERS_FILE = "users.json"

# === Темы по типам заданий ===
TASK_THEMES = {
    1: "Простейшие текстовые задачи (проценты, округление)",
    2: "Единицы измерения (время, длина, масса, объём, площадь)",
    3: "Графики и диаграммы",
    4: "Преобразования выражений и формулы",
    5: "Теория вероятностей",
    6: "Оптимальный выбор (комплекты, варианты)",
    7: "Анализ графиков функций",
    8: "Анализ утверждений",
    9: "Задачи на квадратной решетке (карта, фигуры)",
    10: "Прикладная геометрия (фигуры на плоскости)",
    11: "Стереометрия: многогранники, составные тела",
    12: "Планиметрия: треугольники, четырёхугольники, окружность",
    13: "Пространственные фигуры: параллелепипед, призма, цилиндр",
    14: "Вычисления с дробями и десятичными числами",
    15: "Округление и проценты в текстовых задачах",
    16: "Преобразования выражений: степени, логарифмы, тригонометрия",
    17: "Уравнения: линейные, квадратные, показательные",
    18: "Неравенства и числовые промежутки",
    19: "Числа и их свойства (цифровая запись)",
    20: "Сложные текстовые задачи: движение, смеси, работа",
    21: "Задачи на смекалку"
}
# === Загрузка пользователей ===  # === Ваши новые строки ===
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            st.error("Файл пользователей поврежден. Создайте новый.")
            return {}
    return {}

# === Сохранение пользователей ===  # === Ваши новые строки ===
def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# === Регистрация нового пользователя ===  # === Ваши новые строки ===
def register_user(username, password):
    users = load_users()
    if username in users:
        return False  # Пользователь уже существует
    users[username] = {
        "password": password,
        "levels": {"full": 1, "tasks": {}},  # Уровни по задачам
        "results": []  # История результатов
    }
    save_users(users)
    return True

# === Авторизация пользователя ===  # === Ваши новые строки ===
def authenticate_user(username, password):
    users = load_users()
    if username in users and users[username]["password"] == password:
        return users[username]  # Возвращаем данные пользователя
    return None

# === Загрузка и сохранение уровней ===
def load_levels():
    if os.path.exists(LEVELS_FILE):
        with open(LEVELS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"full": 1, "tasks": {}}

def save_levels(levels):
    with open(LEVELS_FILE, "w", encoding="utf-8") as f:
        json.dump(levels, f, ensure_ascii=False, indent=2)

levels = load_levels()

# === Генерация промпта ===
def build_prompt(mode, task_number=None, count=21, theme=None, level=1):
    level_clause = {1: "легкого", 2: "среднего", 3: "сложного"}.get(level, "легкого")
    theme_clause = f' Все задачи должны содержать тематику "{theme}".' if theme else ""
    if mode == "full":
        return f"""
Ты — преподаватель математики. Сгенерируй {count} разных задач {level_clause} уровня сложности для подготовки к ЕГЭ (базовый уровень), каждая из своей темы.
{theme_clause}
Ответ в формате JSON:
[
  {{"question": "...", "answer": "...", "explanation": "Краткое объяснение"}}
]
Никаких пояснений вне JSON!
""".strip()
    elif mode == "single":
        description = TASK_THEMES.get(task_number, "")
        return f"""
Ты — преподаватель математики. Сгенерируй {count} задач типа №{task_number} ({description}) {level_clause} уровня сложности для базового ЕГЭ.
{theme_clause}
Ответ в формате JSON:
[
  {{"question": "...", "answer": "...", "explanation": "Краткое объяснение"}}
]
Никаких пояснений вне JSON!
""".strip()

# === Генерация заданий через API ===
def generate_questions(prompt):
    import re
    payload = {"model": MODEL, "messages": [{"role": "user", "content": prompt}]}
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        result = response.json()
        content = result["choices"][0]["message"]["content"].strip()
        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?", "", content)
            content = re.sub(r"```$", "", content).strip()
        start = content.find("[")
        end = content.rfind("]") + 1
        return json.loads(content[start:end])
    except Exception as e:
        st.error("❌ Не удалось распарсить JSON или произошла ошибка запроса.")
        return []

# === Генерация полного варианта в 3 запроса по 7 заданий ===
def generate_full_exam(theme,  levels):
    prompts = [
        build_prompt("full", count=7, theme=theme),
        build_prompt("full", count=7, theme=theme),
        build_prompt("full", count=7, theme=theme),
    ]
    results = []
    for prompt in prompts:
        part = generate_questions(prompt)
        if isinstance(part, list):
            results.extend(part)
        else:
            st.error("❌ Одна из частей генерации не удалась.")
            return []
    return results

users = load_users()
# === Сохранение результата ===
def save_result(username, mode, task_number, total, correct):
    users = load_users()  # Загружение пользователей
    user_data = users.get(username, {})
    
    entry = {
        "datetime": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "mode": mode,
        "task_number": task_number,
        "total": total,
        "correct": correct,
        "percent": round(correct / total * 100, 1) if total else 0,
        "level": user_data["levels"]["full"] if mode == "full" else user_data["levels"]["tasks"].get(str(task_number), 1)
    }
    
    # Сохраняем историю результатов пользователя в отдельный файл
    user_results_file = f"results_{username}.json"
    if os.path.exists(user_results_file):
        with open(user_results_file, "r", encoding="utf-8") as f:
            all_results = json.load(f)
    else:
        all_results = []

    all_results.append(entry)

    # Сохраняем результаты обратно в файл
    with open(user_results_file, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    # Логика повышения уровня
    if mode == "full":
        if correct / total >= 0.8 and user_data['levels']['full'] < 3:
            user_data['levels']['full'] += 1
            st.success("🎉 Ваш уровень сложности повышен до " + str(user_data['levels']['full']))
    elif mode == "single":
        tn = str(task_number)
        if correct / total >= 0.8:
            current_task_level = user_data['levels']['tasks'].get(tn, 1)
            if current_task_level < 3:
                user_data['levels']['tasks'][tn] = current_task_level + 1
                st.success(f"🎉 Уровень сложности для задания №{task_number} повышен до {user_data['levels']['tasks'][tn]}")

    # Сохраняем обновленного пользователя
    save_users(users)

# === Интерфейс Streamlit ===
st.set_page_config("Подготовка к ЕГЭ", page_icon="📘")

right_img = Image.open("right.png")
buffered = io.BytesIO()
right_img.save(buffered, format="PNG")
img_base64 = base64.b64encode(buffered.getvalue()).decode()

# Показываем только картинку по центру
st.markdown(
    f"""
    <div style='text-align: center;'>
        <img src="data:image/png;base64,{img_base64}" style="max-width: 500px;" />
    </div>
    """,
    unsafe_allow_html=True
)

# === Пользовательская аутентификация ===
st.sidebar.header("Аутентификация")
auth_option = st.sidebar.selectbox("Выберите действие", ["Войти", "Регистрация"])
username = st.sidebar.text_input("Имя пользователя")
password = st.sidebar.text_input("Пароль", type="password")

if auth_option == "Регистрация":
    if st.sidebar.button("Зарегистрироваться"):
        if register_user(username, password):
            st.sidebar.success("Регистрация прошла успешно. Теперь вы можете войти.")
        else:
            st.sidebar.error("Пользователь с таким именем уже существует.")
else:
    if st.sidebar.button("Войти"):
        if authenticate_user(username, password):
            st.session_state['username'] = username  # Сохранение имени пользователя
            st.sidebar.success("Успешный вход!")
        else:
            st.sidebar.error("Ошибка авторизации. Попробуйте снова.")


# Проверка на авторизацию и загрузка данных пользователя
user_data = None
if 'username' not in st.session_state:
    st.warning("Пожалуйста, войдите, чтобы начать тренировку.")
else:
    username = st.session_state['username']
    user_data = load_users().get(username)  # Загружаем данные пользователя
    st.success("Вы успешно вошли как " + username)
    # Пробел для дальнейшего функционала, если пользователь авторизован
    mode = st.radio("Выбери режим:", ["Пройти весь вариант (21 задание)", "Решить одно задание с вариациями"])
    
    theme = st.text_input("Тема, которая тебе интересна (например, космос)")
    questions = []
    score = 0
    
    if mode == "Пройти весь вариант (21 задание)":
        st.markdown(f"**Текущий уровень сложности:** {user_data['levels']['full']}")
        if st.button("Сгенерировать вариант"):
            questions = generate_full_exam(theme, user_data['levels']['full'])
            st.session_state.questions = questions
            st.session_state.mode = "full"
            st.session_state.task_number = None
    else:
        task_number = st.selectbox("Выбери номер задания (1–21):", list(range(1, 22)))
        current_task_level = user_data['levels']['tasks'].get(str(task_number), 1)
        st.markdown(f"**Ваш уровень сложности для задания №{task_number}:** {current_task_level}")
        count = st.slider("Сколько вариантов сгенерировать?", 1, 10, 5)
        if st.button("Сгенерировать задания"):
            prompt = build_prompt("single", task_number=task_number, count=count, theme=theme, level=current_task_level)
            questions = generate_questions(prompt)
            st.session_state.questions = questions
            st.session_state.mode = "single"
            st.session_state.task_number = task_number

    if "questions" in st.session_state:
        st.markdown("### Задания:")
        submitted = st.button("Проверить ответы")
        correct = 0
        total = len(st.session_state.questions)

        for i, q in enumerate(st.session_state.questions):
            st.markdown(f"**Вопрос {i+1}:** {q['question']}")
            user_key = f"user_answer_{i}"
            user_input = st.text_input("Ваш ответ:", key=user_key)

            if submitted:
                is_correct = str(user_input).strip() == str(q["answer"]).strip()
                if is_correct:
                    st.success(f"✅ Верно! Ваш ответ: {user_input}")
                    correct += 1
                else:
                    st.error(f"❌ Неверно. Ваш ответ: {user_input} | Правильный ответ: {q['answer']}")
                if q.get("explanation"):
                    st.info(f"🧠 Пояснение: {q['explanation']}")

        if submitted:
            percent = correct / total * 100
            st.markdown("---")
            st.info(f"🎯 Правильных ответов: **{correct} из {total}** ({percent:.1f}%)")

            if st.session_state.mode == "full":
                if percent >= 80 and user_data['levels']['full'] < 3:
                    user_data['levels']['full'] += 1
            elif st.session_state.mode == "single":
                tn = str(st.session_state.task_number)
                if percent >= 80:
                    user_data['levels']['tasks'][tn] = min(3, user_data['levels']['tasks'].get(tn, 1) + 1)

            # Сохраняем обновленные уровни
            save_users(users)  # Переменная users должна быть определена до этого
            save_result(username, st.session_state.mode, st.session_state.task_number, total, correct)
            st.balloons()

    # === История прохождений для текущего пользователя ===
    user_results_file = f"results_{username}.json"
    if os.path.exists(user_results_file):
        current_mode = st.session_state.get("mode")
        current_task = st.session_state.get("task_number")
        filtered_results = []

        with open(user_results_file, "r", encoding="utf-8") as f:
            all_results = json.load(f)
            if current_mode == "full":
                filtered_results = [r for r in all_results if r["mode"] == "full"]
            elif current_mode == "single" and current_task is not None:
                filtered_results = [r for r in all_results if r["mode"] == "single" and r["task_number"] == current_task]

        if filtered_results:
            with st.expander("📜 История тренировок"):
                for entry in reversed(filtered_results[-10:]):
                    task_info = f" №{entry['task_number']}" if entry['task_number'] else ""
                    st.markdown(
                        f"- {entry['datetime']} | {entry['mode']}{task_info} | "
                        f"{entry['correct']}/{entry['total']} ({entry['percent']}%) | Уровень {entry['level']}")