"""Генератор історій для YouTube - Streamlit App (Stage 1)"""

import re
import json
import difflib
import streamlit as st
from core.config import STORY_CORE_PROMPT_PATH, STORY_PROMPT_PATH, ensure_cache_dir, COOKIES_FILE, STORY_CORE_PROMPT_FILENAME
from core.utils import safe_int, cookies_file_path
from services.prompts import (
    load_template_from_file,
    load_prompt_file,
    get_default_story_core_template,
    get_default_story_template,
    fill_story_core_prompt,
    fill_story_prompt,
    inject_subtitles_into_prompt,
    inject_story_core_into_prompt,
    inject_all_story_variables
)
from core.config import STORY_CORE_PROMPT_PATH
from services.generators import (
    fetch_and_clean_subtitles,
    generate_story_core
)
from services.llm_backends import generate_text


def initialize_session_state():
    """Initialize all session state variables on first run."""
    if 'youtube_url' not in st.session_state:
        st.session_state.youtube_url = ""
    if 'raw_subtitles' not in st.session_state:
        st.session_state.raw_subtitles = ""
    if 'clean_subtitles' not in st.session_state:
        st.session_state.clean_subtitles = ""
    if 'original_length_chars' not in st.session_state:
        st.session_state.original_length_chars = 0
    if 'story_core_prompt_template' not in st.session_state:
        # Load from file (must exist, no fallback)
        try:
            template = load_prompt_file(str(STORY_CORE_PROMPT_PATH))
            st.session_state.story_core_prompt_template = template
        except FileNotFoundError as e:
            st.error(
    f"Помилка: Файл промпту не знайдено: {STORY_CORE_PROMPT_FILENAME}. Розмістіть файл в корені проєкту.")
            st.session_state.story_core_prompt_template = ""
    if 'story_prompt_template' not in st.session_state:
        # Load from file (must exist, no fallback)
        try:
            template = load_prompt_file(str(STORY_PROMPT_PATH))
            st.session_state.story_prompt_template = template
        except FileNotFoundError as e:
            st.error(
    f"Помилка: Файл промпту не знайдено: prompt_story.txt. Розмістіть файл в корені проєкту.")
            st.session_state.story_prompt_template = ""
    if 'story_core_text' not in st.session_state:
        st.session_state.story_core_text = ""
    if 'story_core_text_pending' not in st.session_state:
        st.session_state.story_core_text_pending = None
    if 'story_core_prompt_filled' not in st.session_state:
        st.session_state.story_core_prompt_filled = ""
    if 'story_core_prompt_text' not in st.session_state:
        # Initialize with template from file
        try:
            template = load_prompt_file(str(STORY_CORE_PROMPT_PATH))
            st.session_state.story_core_prompt_text = template
            # Also keep the template for reference
            st.session_state.story_core_prompt_template = template
        except FileNotFoundError:
            st.session_state.story_core_prompt_text = ""
            st.session_state.story_core_prompt_template = ""
    if 'subtitles_text' not in st.session_state:
        st.session_state.subtitles_text = ""
    if 'story_prompt_filled' not in st.session_state:
        st.session_state.story_prompt_filled = ""
    if 'generated_story' not in st.session_state:
        st.session_state.generated_story = ""
    if 'story_core_result' not in st.session_state:
        st.session_state.story_core_result = ""
    if 'story_core_result_hash' not in st.session_state:
        st.session_state.story_core_result_hash = None
    if 'story_variables_hash' not in st.session_state:
        st.session_state.story_variables_hash = None
    if 'story_prompt_text' not in st.session_state:
        # Initialize with template from file
        try:
            template = load_prompt_file(str(STORY_PROMPT_PATH))
            st.session_state.story_prompt_text = template
            st.session_state.story_prompt_template = template
        except FileNotFoundError:
            st.session_state.story_prompt_text = ""
            st.session_state.story_prompt_template = ""
    if 'story_result' not in st.session_state:
        st.session_state.story_result = ""
    if 'story_result_pending' not in st.session_state:
        st.session_state.story_result_pending = None
    if 'sub_lang_mode' not in st.session_state:
        st.session_state.sub_lang_mode = "auto"
    if 'prefer_manual' not in st.session_state:
        st.session_state.prefer_manual = True
    # Initialize debug variables
    if 'debug_last_prompt' not in st.session_state:
        st.session_state.debug_last_prompt = ""
    if 'debug_last_response' not in st.session_state:
        st.session_state.debug_last_response = ""
    if 'debug_prompt_chars' not in st.session_state:
        st.session_state.debug_prompt_chars = 0
    if 'debug_story_core_chars' not in st.session_state:
        st.session_state.debug_story_core_chars = 0
    if 'debug_target_length_chars' not in st.session_state:
        st.session_state.debug_target_length_chars = 0
    if 'debug_response_chars' not in st.session_state:
        st.session_state.debug_response_chars = 0
    if 'debug_error' not in st.session_state:
        st.session_state.debug_error = None
    # Initialize analytics variables
    if 'analysis_story_input' not in st.session_state:
        st.session_state.analysis_story_input = ""
    if 'analysis_story_input_pending' not in st.session_state:
        st.session_state.analysis_story_input_pending = None
    if 'analysis_report' not in st.session_state:
        st.session_state.analysis_report = ""
    if 'comparison_table_md' not in st.session_state:
        st.session_state.comparison_table_md = ""
    if 'improvement_prompt' not in st.session_state:
        st.session_state.improvement_prompt = ""
    if 'improved_story' not in st.session_state:
        st.session_state.improved_story = ""
    # Initialize status tracking variables
    if 'last_status' not in st.session_state:
        st.session_state.last_status = "Готово до роботи"
    if 'last_status_level' not in st.session_state:
        st.session_state.last_status_level = "info"
    if 'last_action' not in st.session_state:
        st.session_state.last_action = ""
    if 'last_completed_step' not in st.session_state:
        st.session_state.last_completed_step = ""
    if 'last_run_at' not in st.session_state:
        st.session_state.last_run_at = ""
    # Initialize LLM backend and pipeline mode
    if 'llm_backend' not in st.session_state:
        from core.config import LLM_BACKEND_DEFAULT
        st.session_state.llm_backend = LLM_BACKEND_DEFAULT
    if 'pipeline_mode' not in st.session_state:
        st.session_state.pipeline_mode = "classic"
    # Initialize GenAI App configuration (UI-first, env fallback)
    if 'genai_app_url' not in st.session_state:
        from core.config import GENAI_APP_URL
        st.session_state.genai_app_url = GENAI_APP_URL
    if 'genai_app_token' not in st.session_state:
        from core.config import GENAI_APP_TOKEN
        st.session_state.genai_app_token = GENAI_APP_TOKEN


def update_original_length():
    """Recalculate original_length_chars from clean_subtitles."""
    st.session_state.original_length_chars = len(
        st.session_state.clean_subtitles)


def format_slide(text: str, prompt: str) -> str:
    """
    Format a single slide with enforced braces.

    Args:
        text: Slide narration text
        prompt: Voice delivery prompt

    Returns:
        Formatted slide string
    """
    # Trim
    text = text.strip()
    prompt = prompt.strip()

    # Ensure braces
    if not text.startswith("{"):
        text = "{" + text
    if not text.endswith("}"):
        text = text + "}"

    if not prompt.startswith("{"):
        prompt = "{" + prompt
    if not prompt.endswith("}"):
        prompt = prompt + "}"

    return f"Text:\n{text}\n\nPrompt:\n{prompt}"


def show_friendly_error(error: Exception):
    """Display user-friendly error message based on error type."""
    error_msg = str(error)

    # Check for GenAI App configuration issues
    if "не налаштовано" in error_msg or "not configured" in error_msg.lower(
    ) or "not set" in error_msg.lower():
        st.warning(
            "⚠️ Вкажи GenAI App URL у боковій панелі (Sidebar → GenAI App Settings).")
    else:
        # Show generic error
        st.error(f"❌ Помилка: {error_msg}")


def update_status(message: str, level: str = "info", action: str = "", step: str = ""):
    """Update status tracking variables."""
    from datetime import datetime
    st.session_state.last_status = message
    st.session_state.last_status_level = level
    st.session_state.last_action = action
    st.session_state.last_completed_step = step
    st.session_state.last_run_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def show_status_display():
    """Display current status area."""
    status_level = st.session_state.get("last_status_level", "info")
    status_message = st.session_state.get("last_status", "Готово до роботи")
    last_action = st.session_state.get("last_action", "")
    last_step = st.session_state.get("last_completed_step", "")
    last_run = st.session_state.get("last_run_at", "")

    status_text = status_message
    if last_step:
        status_text += f" | Останній крок: {last_step}"
    if last_run:
        status_text += f" | {last_run}"

    if status_level == "success":
        st.success(status_text)
    elif status_level == "warning":
        st.warning(status_text)
    elif status_level == "error":
        st.error(status_text)
    else:
        st.info(status_text)


def show_readiness_indicators():
    """Show compact readiness indicators."""
    subtitles_ready = bool(st.session_state.get("clean_subtitles"))
    core_ready = bool(st.session_state.get("story_core_text"))
    story_ready = bool(st.session_state.get("generated_story")
                       or st.session_state.get("story_result"))

    subtitles_indicator = "✅" if subtitles_ready else "—"
    core_indicator = "✅" if core_ready else "—"
    story_indicator = "✅" if story_ready else "—"

    st.caption(
    f"Статус: Субтитри {subtitles_indicator} | STORY_CORE {core_indicator} | Історія {story_indicator}")


# Analysis prompt template (Ukrainian output)
ANALYSIS_PROMPT_TEMPLATE = """Ти експерт з аналізу наративних текстів для YouTube.

Твоя задача: провести чесний аналіз згенерованої історії порівняно з оригіналом.

ВХІДНІ ДАНІ:

ОРИГІНАЛ (субтитри):
    {ORIGINAL}

ЗГЕНЕРОВАНА ІСТОРІЯ:
    {GENERATED}

ЗАВДАННЯ:

1. Оціни згенеровану історію за шкалою 0-10 для кожної метрики:
    - Hook (сила зачіпки в перших слайдах)
   - Retention chain (незавершені цикли / напруга)
   - Clarity (ясність викладу)
   - Pacing (ритм, темп)
   - Repetition (відсутність повторень)
   - Ending impact (вплив фіналу)

2. Перелічи 3 сильні сторони (bullet list)

3. Перелічи 3 слабкі сторони (bullet list)

4. Створи таблицю порівняння в markdown форматі:
    | Критерій | Оригінал | Згенерована | Коментар |
   |----------|----------|-------------|----------|
   | Hook | ... | ... | ... |
   | Stakes clarity | ... | ... | ... |
   | Loops | ... | ... | ... |
   | Escalation | ... | ... | ... |
   | Specificity | ... | ... | ... |
   | Ending | ... | ... | ... |

5. Створи "Промпт для покращення" - готовий промпт, який інструктує модель як переписати згенеровану історію:
    - Зберегти ключові факти
   - Виправити знайдені слабкості
   - Дотримуватися правил стилю: show-don't-tell, розмовний стиль, без моралізації
   - Уникнути повторень

   ВАЖЛИВО: Промпт для покращення має бути АНГЛІЙСЬКОЮ МОВОЮ ТІЛЬКИ. Не використовуй українську чи російську.

ФОРМАТ ВИВОДУ (строго дотримуйся):

## ОЦІНКИ (0-10)
- Hook: [число]/10
- Retention chain: [число]/10
- Clarity: [число]/10
- Pacing: [число]/10
- Repetition: [число]/10
- Ending impact: [число]/10

## СИЛЬНІ СТОРОНИ
- [перша]
- [друга]
- [третя]

## СЛАБКІ СТОРОНИ
- [перша]
- [друга]
- [третя]

## ТАБЛИЦЯ ПОРІВНЯННЯ
[markdown таблиця тут]

## ПРОМПТ ДЛЯ ПОКРАЩЕННЯ
[текст промпту для покращення]"""


def parse_analysis_response(response_text: str) -> tuple[str, str, str]:
    """
    Parse LLM analysis response into components.

    Returns:
        Tuple of (analysis_report, comparison_table_md, improvement_prompt)
    """
    analysis_report = ""
    comparison_table_md = ""
    improvement_prompt = ""

    # Find section markers
    table_start = response_text.find("## ТАБЛИЦЯ ПОРІВНЯННЯ")
    prompt_start = response_text.find("## ПРОМПТ ДЛЯ ПОКРАЩЕННЯ")

    # Extract comparison table (between ## ТАБЛИЦЯ ПОРІВНЯННЯ and ## ПРОМПТ
    # ДЛЯ ПОКРАЩЕННЯ or end)
    if table_start != -1:
        table_end = prompt_start if prompt_start != -1 else len(response_text)
        comparison_table_md = response_text[table_start:table_end].strip()
        # Remove the header
        if comparison_table_md.startswith("## ТАБЛИЦЯ ПОРІВНЯННЯ"):
            comparison_table_md = comparison_table_md[len(
                "## ТАБЛИЦЯ ПОРІВНЯННЯ"):].strip()

    # Extract improvement prompt (after ## ПРОМПТ ДЛЯ ПОКРАЩЕННЯ)
    if prompt_start != -1:
        improvement_prompt = response_text[prompt_start +
     len("## ПРОМПТ ДЛЯ ПОКРАЩЕННЯ"):].strip()

    # Analysis report is everything before the table section (or before prompt
    # if no table)
    if table_start != -1:
        analysis_report = response_text[:table_start].strip()
    elif prompt_start != -1:
        analysis_report = response_text[:prompt_start].strip()
    else:
        # If no sections found, return full text as analysis report
        analysis_report = response_text.strip()

    return analysis_report, comparison_table_md, improvement_prompt


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Генератор історій для YouTube",
        page_icon="📺",
        layout="wide"
    )

    st.title("Генератор історій для YouTube")

    # Ensure cache directory exists
    ensure_cache_dir()

    # Initialize session state
    initialize_session_state()

    # Sidebar for input
    with st.sidebar:
        st.header("Вхідні дані")
        st.session_state.youtube_url = st.text_input(
            "Посилання на YouTube",
            value=st.session_state.youtube_url,
            help="Вставте посилання на YouTube відео"
        )

        use_cache = st.checkbox(
            "Використовувати кеш, якщо доступний",
            value=True,
            help="Якщо увімкнено, використовує кешовані субтитри замість повторного завантаження"
        )

        st.session_state.sub_lang_mode = st.selectbox(
            "Пріоритет мови субтитрів",
            options=["auto", "en", "uk", "ru"],
            format_func=lambda x: {
                "auto": "Авто (en → uk → ru)",
                "en": "Тільки англійська (en)",
                "uk": "Тільки українська (uk)",
                "ru": "Тільки російська (ru)"
            }[x],
            index=[
    "auto", "en", "uk", "ru"].index(
        st.session_state.sub_lang_mode) if st.session_state.sub_lang_mode in [
            "auto", "en", "uk", "ru"] else 0,
            help="Виберіть пріоритет мови для субтитрів"
        )

        st.session_state.prefer_manual = st.checkbox(
            "Пробувати ручні субтитри першими",
            value=st.session_state.prefer_manual,
            help="Якщо увімкнено, спочатку шукає ручні субтитри, потім автоматичні"
        )

        # Show cookies file status
        cookies_path = cookies_file_path()
        if cookies_path:
            st.caption(
    f"Cookies файл знайдено: {COOKIES_FILE} (використовується для авторизації)")
        else:
            st.caption(f"Cookies файл не знайдено ({COOKIES_FILE}).")

        st.divider()

        # LLM Backend and Pipeline Mode switches
        st.subheader("Налаштування LLM")

        backend_options = ["ChatGPT (OpenAI)", "GenAI App"]
        backend_index = 0 if st.session_state.llm_backend == "openai" else 1
        backend_choice = st.radio(
            "LLM Backend",
            backend_options,
            index=backend_index,
            help="Виберіть провайдера для генерації текстів"
        )
        st.session_state.llm_backend = "openai" if backend_choice == "ChatGPT (OpenAI)" else "genai_app"

        # GenAI App configuration inputs (show only when genai_app is selected)
        if st.session_state.llm_backend == "genai_app":
            st.subheader("GenAI App Settings")

            genai_url = st.text_input(
                "GenAI App URL",
                value=st.session_state.get("genai_app_url", ""),
                placeholder="https://your-endpoint.com/run",
                help="Вкажи повний URL ендпоінту GenAI App Builder"
            )
            st.session_state.genai_app_url = genai_url.strip()

            genai_token = st.text_input(
                "GenAI App Token (optional)",
                value=st.session_state.get("genai_app_token", ""),
                type="password",
                help="Вкажи токен авторизації (якщо потрібен)"
            )
            st.session_state.genai_app_token = genai_token.strip()

            st.caption(
                "💡 Tip: Вклей свій GenAI App Builder endpoint у поле вище.")

            # Test connection button
            if st.button("Test GenAI App connection"):
                if not st.session_state.genai_app_url:
                    st.sidebar.warning("⚠️ Спочатку вкажи GenAI App URL вище.")
                else:
                    try:
                        import time
                        start = time.time()
                        test_response = generate_text(
    "Reply ONLY with: OK", backend="genai_app")
                        latency = time.time() - start
                        st.sidebar.success(
                            f"✅ З'єднано! Відповідь: {test_response[:50]} | Затримка: {latency:.2f}s")
                    except Exception as e:
                        error_msg = str(e)
                        if "not configured" in error_msg.lower() or "not set" in error_msg.lower():
                            st.sidebar.error(
                                "❌ URL не налаштовано. Перевір поле вище.")
                        else:
                            st.sidebar.error(f"❌ Помилка: {error_msg[:200]}")

            st.divider()

        pipeline_options = ["Classic", "Multi-PASS (AI Controlled)"]
        pipeline_index = 0 if st.session_state.pipeline_mode == "classic" else 1
        pipeline_choice = st.radio(
            "Pipeline Mode",
            pipeline_options,
            index=pipeline_index,
            help="Classic: існуючі промпти. Multi-PASS: AI контролює всі етапи."
        )
        st.session_state.pipeline_mode = "classic" if pipeline_choice == "Classic" else "multipass"

        # Test backend button
        if st.button("Тест вибраного backend"):
            try:
                from services.llm_backends import generate_text as backend_generate
                import time
                start = time.time()
                test_response = backend_generate(
    "Reply with: OK", backend=st.session_state.llm_backend)
                latency = time.time() - start
                st.success(
                    f"✅ Backend працює! Відповідь: {test_response[:100]} | Затримка: {latency:.2f}s")
            except Exception as e:
                st.error(f"❌ Backend помилка: {str(e)}")

        st.divider()

        if st.button("Отримати субтитри", type="primary"):
            if not st.session_state.youtube_url or not st.session_state.youtube_url.strip():
                update_status(
    "Помилка: не вказано посилання на YouTube",
    "error",
    "Отримати субтитри (sidebar)",
     "")
                st.error("Будь ласка, введіть посилання на YouTube.")
            else:
                try:
                    try:
                        with st.status("Отримую субтитри...", expanded=True) as status:
                            status.write("Крок 1/1: Завантаження субтитрів...")
                        raw_vtt, clean_text, meta = fetch_and_clean_subtitles(
                            st.session_state.youtube_url,
                            lang_mode=st.session_state.sub_lang_mode,
                            prefer_manual=st.session_state.prefer_manual,
                            use_cache=use_cache
                        )
                        st.session_state.raw_subtitles = raw_vtt
                        st.session_state.clean_subtitles = clean_text
                        st.session_state.subtitles_text = clean_text
                        st.session_state.original_length_chars = len(
                            clean_text)

                        # Inject subtitles into the top prompt textarea
                        if st.session_state.story_core_prompt_text:
                            st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                st.session_state.story_core_prompt_text,
                                clean_text
                            )
                        else:
                            # If prompt text is empty, load template and inject
                            try:
                                template = load_prompt_file(
                                    str(STORY_CORE_PROMPT_PATH))
                                st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                    template,
                                    clean_text
                                )
                            except FileNotFoundError:
                                pass

                        source_map = {
                            "cache": "кеш",
                            "manual": "ручні",
                            "auto": "авто"
                        }
                        source_text = source_map.get(
                            meta["source"], meta["source"])
                        status.update(
    label="Субтитри отримано ✅", state="complete")
                        update_status(
    f"Субтитри отримано! Джерело: {source_text}",
    "success",
    "Отримати субтитри (sidebar)",
     "Субтитри завантажено")
                        try:
                            st.toast("Готово: Субтитри отримано!", icon="✅")
                        except:
                            pass
                        st.rerun()
                    except:
                        with st.spinner("Отримання субтитрів..."):
                            raw_vtt, clean_text, meta = fetch_and_clean_subtitles(
                                st.session_state.youtube_url,
                                lang_mode=st.session_state.sub_lang_mode,
                                prefer_manual=st.session_state.prefer_manual,
                                use_cache=use_cache
                            )
                            st.session_state.raw_subtitles = raw_vtt
                            st.session_state.clean_subtitles = clean_text
                            st.session_state.subtitles_text = clean_text
                            st.session_state.original_length_chars = len(
                                clean_text)

                            if st.session_state.story_core_prompt_text:
                                st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                    st.session_state.story_core_prompt_text,
                                    clean_text
                                )
                            else:
                                try:
                                    template = load_prompt_file(
                                        str(STORY_CORE_PROMPT_PATH))
                                    st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                        template,
                                        clean_text
                                    )
                                except FileNotFoundError:
                                    pass

                            source_map = {
                                "cache": "кеш",
                                "manual": "ручні",
                                "auto": "авто"
                            }
                            source_text = source_map.get(
                                meta["source"], meta["source"])
                            update_status(
    f"Субтитри отримано! Джерело: {source_text}",
    "success",
    "Отримати субтитри (sidebar)",
     "Субтитри завантажено")
                            try:
                                st.toast(
    "Готово: Субтитри отримано!", icon="✅")
                            except:
                                pass
                        st.rerun()
                except ValueError as e:
                    update_status(
    f"Помилка: {
        str(e)}",
        "error",
        "Отримати субтитри (sidebar)",
         "")
                    st.error(str(e))
                except Exception as e:
                    update_status(
    f"Помилка: {
        str(e)}",
        "error",
        "Отримати субтитри (sidebar)",
         "")
                    st.error(str(e))

        st.divider()

    # Create top-level tabs
    tab_generate, tab_analytics = st.tabs([
        "Генерація",
        "Аналітика та покращення"
    ])

    # ========================
    # TAB 1: GENERATION
    # ========================
    with tab_generate:
        # ========================
        # ACTION BAR (PRO TOOL)
        # ========================
        st.subheader("Панель керування")

        # Readiness indicators
        show_readiness_indicators()

        # Action buttons in columns
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            run_all_button = st.button(
    "Згенерувати все",
    type="primary",
     use_container_width=True)

        with col2:
            fetch_subtitles_button = st.button(
    "Отримати субтитри", use_container_width=True)

        with col3:
            generate_core_button = st.button(
    "Згенерувати STORY_CORE", use_container_width=True)

        with col4:
            generate_story_button = st.button(
    "Згенерувати історію", use_container_width=True)

        with col5:
            clear_status_button = st.button(
    "Очистити статус", use_container_width=True)

        # Status display area
        st.divider()
        show_status_display()
        st.divider()

        # Handle clear status button
        if clear_status_button:
            update_status("Статус очищено", "info", "Очищення статусу", "")
            st.rerun()

        # Handle run all pipeline
        if run_all_button:
            # Check prerequisites
            if not st.session_state.youtube_url or not st.session_state.youtube_url.strip():
                update_status(
    "Помилка: не вказано посилання на YouTube",
    "error",
    "Згенерувати все",
     "")
                st.error(
                    "Будь ласка, введіть посилання на YouTube в бічній панелі.")
            else:
                # Try to use st.status, fallback to st.spinner
                try:
                    with st.status("Запуск повного пайплайну...", expanded=True) as status:
                        status.write("Крок 1/3: Отримання субтитрів...")
                        try:
                            use_cache = True  # Use cache by default
                            raw_vtt, clean_text, meta = fetch_and_clean_subtitles(
                                st.session_state.youtube_url,
                                lang_mode=st.session_state.sub_lang_mode,
                                prefer_manual=st.session_state.prefer_manual,
                                use_cache=use_cache
                            )
                            st.session_state.raw_subtitles = raw_vtt
                            st.session_state.clean_subtitles = clean_text
                            st.session_state.subtitles_text = clean_text
                            st.session_state.original_length_chars = len(
                                clean_text)

                            # Inject subtitles into prompt
                            if st.session_state.story_core_prompt_text:
                                st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                    st.session_state.story_core_prompt_text,
                                    clean_text
                                )
                            else:
                                try:
                                    template = load_prompt_file(
                                        str(STORY_CORE_PROMPT_PATH))
                                    st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                        template,
                                        clean_text
                                    )
                                except FileNotFoundError:
                                    pass

                            status.update(
    label="Крок 1/3: Субтитри отримано ✅", state="complete")
                            status.write("Крок 2/3: Генерація STORY_CORE...")

                            # Step 2: Generate STORY_CORE
                            if not st.session_state.story_core_prompt_text or not st.session_state.story_core_prompt_text.strip():
                                raise ValueError("Промпт STORY_CORE порожній")

                            prompt_to_send = st.session_state.story_core_prompt_text
                            story_core_output = generate_text(
    prompt_to_send, backend=st.session_state.llm_backend)

                            st.session_state.story_core_text_pending = story_core_output
                            st.session_state.story_core_result = story_core_output
                            import hashlib
                            st.session_state.story_core_result_hash = hashlib.md5(
                                story_core_output.encode()).hexdigest()
                            st.session_state.story_core_prompt_filled = prompt_to_send

                            # Apply pending immediately
                            st.session_state.story_core_text = story_core_output
                            st.session_state.story_core_text_pending = None

                            status.update(
    label="Крок 2/3: STORY_CORE згенеровано ✅",
     state="complete")
                            status.write("Крок 3/3: Генерація історії...")

                            # Step 3: Generate STORY
                            # Auto-inject variables if needed
                            story_core_str = st.session_state.story_core_result if st.session_state.story_core_result else ""
                            target_length_str = str(
    st.session_state.original_length_chars)
                            combined_vars = f"{story_core_str}|{target_length_str}"
                            current_hash = hashlib.md5(
                                combined_vars.encode()).hexdigest()

                            if (st.session_state.story_variables_hash is None or
                                st.session_state.story_variables_hash != current_hash or
                                not st.session_state.story_prompt_text or
                                st.session_state.story_prompt_text == st.session_state.story_prompt_template):

                                if not st.session_state.story_prompt_text or st.session_state.story_prompt_text == st.session_state.story_prompt_template:
                                    try:
                                        template = load_prompt_file(
                                            str(STORY_PROMPT_PATH))
                                        st.session_state.story_prompt_text = template
                                        st.session_state.story_prompt_template = template
                                    except FileNotFoundError:
                                        pass

                                if st.session_state.story_prompt_text:
                                    st.session_state.story_prompt_text = inject_all_story_variables(
                                        st.session_state.story_prompt_text,
                                        st.session_state.story_core_result if st.session_state.story_core_result else "",
                                        st.session_state.original_length_chars
                                    )
                                    st.session_state.story_variables_hash = current_hash

                            prompt_template = st.session_state.story_prompt_text
                            try:
                                prompt_to_send = fill_story_prompt(
                                    prompt_template,
                                    st.session_state.story_core_result,
                                    st.session_state.original_length_chars,
                                    None
                                )
                            except Exception:
                                prompt_to_send = prompt_template
                                if "{TARGET_LENGTH_CHARS}" in prompt_to_send:
                                    prompt_to_send = prompt_to_send.replace(
                                        "{TARGET_LENGTH_CHARS}", str(st.session_state.original_length_chars))
                                prompt_to_send = re.sub(
                                    r'TARGET_LENGTH_CHARS:\s*\{[^}]*\}',
                                    f'TARGET_LENGTH_CHARS: {
    st.session_state.original_length_chars}',
                                    prompt_to_send
                                )
                                prompt_to_send = re.sub(
    r'SLIDE_COUNT:\s*\{[^}]*\}', '', prompt_to_send)
                                prompt_to_send = prompt_to_send.replace(
                                    "{SLIDE_COUNT}", "")

                            story_output = generate_text(prompt_to_send)
                            st.session_state.story_result_pending = story_output
                            st.session_state.generated_story = story_output
                            st.session_state.story_result = story_output
                            st.session_state.story_result_pending = None
                            st.session_state.story_prompt_filled = prompt_to_send

                            status.update(
    label="Крок 3/3: Історія згенерована ✅", state="complete")

                            update_status(
    "Пайплайн завершено успішно!",
    "success",
    "Згенерувати все",
     "Історія згенерована")

                            try:
                                st.toast(
    "Готово: Історія згенерована!", icon="✅")
                            except:
                                pass

                            st.rerun()
                        except Exception as e:
                            status.update(
    label=f"Помилка: {
        str(e)}", state="error")
                            update_status(
    f"Помилка під час виконання пайплайну: {
        str(e)}", "error", "Згенерувати все", "")
                            st.error(f"Помилка: {str(e)}")
                except:
                    # Fallback to spinner if st.status not available
                    with st.spinner("Запуск повного пайплайну..."):
                        try:
                            # Same logic as above but with spinner
                            use_cache = True
                            raw_vtt, clean_text, meta = fetch_and_clean_subtitles(
                                st.session_state.youtube_url,
                                lang_mode=st.session_state.sub_lang_mode,
                                prefer_manual=st.session_state.prefer_manual,
                                use_cache=use_cache
                            )
                            st.session_state.raw_subtitles = raw_vtt
                            st.session_state.clean_subtitles = clean_text
                            st.session_state.subtitles_text = clean_text
                            st.session_state.original_length_chars = len(
                                clean_text)

                            if st.session_state.story_core_prompt_text:
                                st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                    st.session_state.story_core_prompt_text,
                                    clean_text
                                )
                            else:
                                try:
                                    template = load_prompt_file(
                                        str(STORY_CORE_PROMPT_PATH))
                                    st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                        template,
                                        clean_text
                                    )
                                except FileNotFoundError:
                                    pass

                            if not st.session_state.story_core_prompt_text or not st.session_state.story_core_prompt_text.strip():
                                raise ValueError("Промпт STORY_CORE порожній")

                            prompt_to_send = st.session_state.story_core_prompt_text
                            story_core_output = generate_text(
    prompt_to_send, backend=st.session_state.llm_backend)

                            st.session_state.story_core_text = story_core_output
                            st.session_state.story_core_result = story_core_output
                            import hashlib
                            st.session_state.story_core_result_hash = hashlib.md5(
                                story_core_output.encode()).hexdigest()
                            st.session_state.story_core_prompt_filled = prompt_to_send

                            story_core_str = st.session_state.story_core_result if st.session_state.story_core_result else ""
                            target_length_str = str(
    st.session_state.original_length_chars)
                            combined_vars = f"{story_core_str}|{target_length_str}"
                            current_hash = hashlib.md5(
                                combined_vars.encode()).hexdigest()

                            if (st.session_state.story_variables_hash is None or
                                st.session_state.story_variables_hash != current_hash or
                                not st.session_state.story_prompt_text or
                                st.session_state.story_prompt_text == st.session_state.story_prompt_template):

                                if not st.session_state.story_prompt_text or st.session_state.story_prompt_text == st.session_state.story_prompt_template:
                                    try:
                                        template = load_prompt_file(
                                            str(STORY_PROMPT_PATH))
                                        st.session_state.story_prompt_text = template
                                        st.session_state.story_prompt_template = template
                                    except FileNotFoundError:
                                        pass

                                if st.session_state.story_prompt_text:
                                    st.session_state.story_prompt_text = inject_all_story_variables(
                                        st.session_state.story_prompt_text,
                                        st.session_state.story_core_result if st.session_state.story_core_result else "",
                                        st.session_state.original_length_chars
                                    )
                                    st.session_state.story_variables_hash = current_hash

                            prompt_template = st.session_state.story_prompt_text
                            try:
                                prompt_to_send = fill_story_prompt(
                                    prompt_template,
                                    st.session_state.story_core_result,
                                    st.session_state.original_length_chars,
                                    None
                                )
                            except Exception:
                                prompt_to_send = prompt_template
                                if "{TARGET_LENGTH_CHARS}" in prompt_to_send:
                                    prompt_to_send = prompt_to_send.replace(
                                        "{TARGET_LENGTH_CHARS}", str(st.session_state.original_length_chars))
                                prompt_to_send = re.sub(
                                    r'TARGET_LENGTH_CHARS:\s*\{[^}]*\}',
                                    f'TARGET_LENGTH_CHARS: {
    st.session_state.original_length_chars}',
                                    prompt_to_send
                                )
                                prompt_to_send = re.sub(
    r'SLIDE_COUNT:\s*\{[^}]*\}', '', prompt_to_send)
                                prompt_to_send = prompt_to_send.replace(
                                    "{SLIDE_COUNT}", "")

                            story_output = generate_text(prompt_to_send)
                            st.session_state.story_result = story_output
                            st.session_state.generated_story = story_output
                            st.session_state.story_prompt_filled = prompt_to_send

                            update_status(
    "Пайплайн завершено успішно!",
    "success",
    "Згенерувати все",
     "Історія згенерована")

                            try:
                                st.toast(
    "Готово: Історія згенерована!", icon="✅")
                            except:
                                pass

                            st.rerun()
                        except Exception as e:
                            update_status(
    f"Помилка під час виконання пайплайну: {
        str(e)}", "error", "Згенерувати все", "")
                            st.error(f"Помилка: {str(e)}")

        # Handle STORY_CORE generation from action bar
        if generate_core_button:
            if not st.session_state.story_core_prompt_text or not st.session_state.story_core_prompt_text.strip():
                update_status(
    "Помилка: промпт STORY_CORE порожній",
    "error",
    "Згенерувати STORY_CORE",
     "")
                st.error(
                    "Промпт порожній. Будь ласка, завантажте шаблон або введіть промпт.")
            else:
                try:
                    try:
                        with st.status("Генерую STORY_CORE...", expanded=True) as status:
                            status.write("Крок 1/1: Генерація STORY_CORE...")
                            prompt_to_send = st.session_state.story_core_prompt_text
                            from services.llm_client import generate_text
                            story_core_output = generate_text(prompt_to_send)
                            st.session_state.story_core_text_pending = story_core_output
                            st.session_state.story_core_result = story_core_output
                            import hashlib
                            st.session_state.story_core_result_hash = hashlib.md5(
                                story_core_output.encode()).hexdigest()
                            st.session_state.story_core_prompt_filled = prompt_to_send
                            st.session_state.story_core_text = story_core_output
                            st.session_state.story_core_text_pending = None
                            status.update(
    label="STORY_CORE згенеровано ✅", state="complete")
                            update_status(
    "STORY_CORE згенеровано успішно!",
    "success",
    "Згенерувати STORY_CORE",
     "STORY_CORE згенеровано")
                            try:
                                st.toast(
    "Готово: STORY_CORE згенеровано!", icon="✅")
                            except:
                                pass
                            st.rerun()
                    except:
                        with st.spinner("Генерація STORY_CORE..."):
                            prompt_to_send = st.session_state.story_core_prompt_text
                            from services.llm_client import generate_text
                            story_core_output = generate_text(prompt_to_send)
                            st.session_state.story_core_text_pending = story_core_output
                            st.session_state.story_core_result = story_core_output
                            import hashlib
                            st.session_state.story_core_result_hash = hashlib.md5(
                                story_core_output.encode()).hexdigest()
                            st.session_state.story_core_prompt_filled = prompt_to_send
                            st.session_state.story_core_text = story_core_output
                            st.session_state.story_core_text_pending = None
                            update_status(
    "STORY_CORE згенеровано успішно!",
    "success",
    "Згенерувати STORY_CORE",
     "STORY_CORE згенеровано")
                            try:
                                st.toast(
    "Готово: STORY_CORE згенеровано!", icon="✅")
                            except:
                                pass
                            st.rerun()
                except Exception as e:
                    update_status(
    f"Помилка генерації STORY_CORE: {
        str(e)}", "error", "Згенерувати STORY_CORE", "")
                    show_friendly_error(e)

        # Handle story generation from action bar
        if generate_story_button:
            # Check pipeline mode
            if st.session_state.pipeline_mode == "multipass":
                # Multi-PASS AI-controlled pipeline
                if not st.session_state.clean_subtitles or not st.session_state.clean_subtitles.strip():
                    update_status(
    "Помилка: немає субтитрів для Multi-PASS",
    "error",
    "Згенерувати історію (Multi-PASS)",
     "")
                    st.error("Будь ласка, спочатку отримайте субтитри.")
                else:
                    try:
                        try:
                            with st.status("Запуск Multi-PASS pipeline...", expanded=True) as status:
                                from services.multipass_pipeline import run_multipass

                                status.write("PASS 0: Аналіз структури...")
                                multipass_result = run_multipass(
                                    st.session_state.clean_subtitles,
                                    target_chars=st.session_state.original_length_chars,
                                    slides_hint=None,
                                    backend=st.session_state.llm_backend
                                )

                                status.update(
    label="Multi-PASS завершено ✅", state="complete")

                                # Format slides for display
                                slides = multipass_result.get(
                                    "story_slides", [])
                                slide_parts = []
                                for i, slide in enumerate(slides, 1):
                                    text = slide.get("Text", "")
                                    prompt = slide.get("Prompt", "")
                                    slide_parts.append(
                                        format_slide(text, prompt))
                                formatted_story = "\n".join(slide_parts)

                                # Store results
                                st.session_state.generated_story = formatted_story.strip()
                                st.session_state.story_result = formatted_story.strip()

                                # Store multipass debug info
                                st.session_state.debug_last_response = json.dumps(
                                    multipass_result, indent=2, ensure_ascii=False)

                                update_status(
    "Multi-PASS завершено успішно!",
    "success",
    "Згенерувати історію (Multi-PASS)",
     "Multi-PASS complete")
                                try:
                                    st.toast(
    "Готово: Multi-PASS історія!", icon="✅")
                                except:
                                    pass
                                st.rerun()
                        except:
                            with st.spinner("Запуск Multi-PASS pipeline..."):
                                from services.multipass_pipeline import run_multipass

                                multipass_result = run_multipass(
                                    st.session_state.clean_subtitles,
                                    target_chars=st.session_state.original_length_chars,
                                    slides_hint=None,
                                    backend=st.session_state.llm_backend
                                )

                                # Format slides for display
                                slides = multipass_result.get(
                                    "story_slides", [])
                                slide_parts = []
                                for i, slide in enumerate(slides, 1):
                                    text = slide.get("Text", "")
                                    prompt = slide.get("Prompt", "")
                                    slide_parts.append(
                                        format_slide(text, prompt))
                                formatted_story = "\n".join(slide_parts)

                                st.session_state.generated_story = formatted_story.strip()
                                st.session_state.story_result = formatted_story.strip()
                                st.session_state.debug_last_response = json.dumps(
                                    multipass_result, indent=2, ensure_ascii=False)

                                update_status(
    "Multi-PASS завершено успішно!",
    "success",
    "Згенерувати історію (Multi-PASS)",
     "Multi-PASS complete")
                                try:
                                    st.toast(
    "Готово: Multi-PASS історія!", icon="✅")
                                except:
                                    pass
                                st.rerun()
                    except Exception as e:
                        update_status(
                            f"Помилка Multi-PASS: {str(e)}", "error", "Згенерувати історію (Multi-PASS)", "")
                        show_friendly_error(e)
            elif not st.session_state.story_prompt_text or not st.session_state.story_prompt_text.strip():
                update_status("Помилка: промпт історії порожній",
                              "error", "Згенерувати історію", "")
                st.error(
                    "Промпт порожній. Будь ласка, завантажте шаблон або введіть промпт.")
            elif not st.session_state.story_core_result or not st.session_state.story_core_result.strip():
                update_status(
    "Помилка: STORY_CORE не згенеровано",
    "error",
    "Згенерувати історію",
     "")
                st.error(
                    "STORY_CORE не згенеровано. Будь ласка, спочатку згенеруйте STORY_CORE.")
            else:
                try:
                    try:
                        with st.status("Генерую історію...", expanded=True) as status:
                            status.write("Крок 1/1: Генерація історії...")
                            prompt_template = st.session_state.story_prompt_text
                            try:
                                prompt_to_send = fill_story_prompt(
                                    prompt_template,
                                    st.session_state.story_core_result,
                                    st.session_state.original_length_chars,
                                    None
                                )
                            except Exception:
                                prompt_to_send = prompt_template
                                if "{TARGET_LENGTH_CHARS}" in prompt_to_send:
                                    prompt_to_send = prompt_to_send.replace(
                                        "{TARGET_LENGTH_CHARS}", str(st.session_state.original_length_chars))
                                prompt_to_send = re.sub(
                                    r'TARGET_LENGTH_CHARS:\s*\{[^}]*\}',
                                    f'TARGET_LENGTH_CHARS: {
    st.session_state.original_length_chars}',
                                    prompt_to_send
                                )
                                prompt_to_send = re.sub(
    r'SLIDE_COUNT:\s*\{[^}]*\}', '', prompt_to_send)
                                prompt_to_send = prompt_to_send.replace(
                                    "{SLIDE_COUNT}", "")

                            story_output = generate_text(
    prompt_to_send, backend=st.session_state.llm_backend)
                            st.session_state.story_result_pending = story_output
                            st.session_state.generated_story = story_output
                            st.session_state.story_result = story_output
                            st.session_state.story_result_pending = None
                            st.session_state.story_prompt_filled = prompt_to_send
                            status.update(
    label="Історія згенерована ✅", state="complete")
                            update_status(
    "Історію згенеровано успішно!",
    "success",
    "Згенерувати історію",
     "Історія згенерована")
                            try:
                                st.toast(
    "Готово: Історія згенерована!", icon="✅")
                            except:
                                pass
                            st.rerun()
                    except:
                        with st.spinner("Генерація історії..."):
                            prompt_template = st.session_state.story_prompt_text
                            try:
                                prompt_to_send = fill_story_prompt(
                                    prompt_template,
                                    st.session_state.story_core_result,
                                    st.session_state.original_length_chars,
                                    None
                                )
                            except Exception:
                                prompt_to_send = prompt_template
                                if "{TARGET_LENGTH_CHARS}" in prompt_to_send:
                                    prompt_to_send = prompt_to_send.replace(
                                        "{TARGET_LENGTH_CHARS}", str(st.session_state.original_length_chars))
                                prompt_to_send = re.sub(
                                    r'TARGET_LENGTH_CHARS:\s*\{[^}]*\}',
                                    f'TARGET_LENGTH_CHARS: {
    st.session_state.original_length_chars}',
                                    prompt_to_send
                                )
                                prompt_to_send = re.sub(
    r'SLIDE_COUNT:\s*\{[^}]*\}', '', prompt_to_send)
                                prompt_to_send = prompt_to_send.replace(
                                    "{SLIDE_COUNT}", "")

                            story_output = generate_text(
    prompt_to_send, backend=st.session_state.llm_backend)
                            st.session_state.story_result_pending = story_output
                            st.session_state.generated_story = story_output
                            st.session_state.story_result = story_output
                            st.session_state.story_result_pending = None
                            st.session_state.story_prompt_filled = prompt_to_send
                            update_status(
    "Історію згенеровано успішно!",
    "success",
    "Згенерувати історію",
     "Історія згенерована")
                            try:
                                st.toast(
    "Готово: Історія згенерована!", icon="✅")
                            except:
                                pass
                            st.rerun()
                except Exception as e:
                    update_status(
    f"Помилка генерації історії: {
        str(e)}", "error", "Згенерувати історію", "")
                    show_friendly_error(e)

        # Handle individual action buttons from action bar
        if fetch_subtitles_button:
            if not st.session_state.youtube_url or not st.session_state.youtube_url.strip():
                update_status(
    "Помилка: не вказано посилання на YouTube",
    "error",
    "Отримати субтитри",
     "")
                st.error("Будь ласка, введіть посилання на YouTube.")
            else:
                try:
                    try:
                        with st.status("Отримую субтитри...", expanded=True) as status:
                            status.write("Крок 1/1: Завантаження субтитрів...")
                            use_cache = True
                            raw_vtt, clean_text, meta = fetch_and_clean_subtitles(
                                st.session_state.youtube_url,
                                lang_mode=st.session_state.sub_lang_mode,
                                prefer_manual=st.session_state.prefer_manual,
                                use_cache=use_cache
                            )
                            st.session_state.raw_subtitles = raw_vtt
                            st.session_state.clean_subtitles = clean_text
                            st.session_state.subtitles_text = clean_text
                            st.session_state.original_length_chars = len(
                                clean_text)

                            if st.session_state.story_core_prompt_text:
                                st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                    st.session_state.story_core_prompt_text,
                                    clean_text
                                )
                            else:
                                try:
                                    template = load_prompt_file(
                                        str(STORY_CORE_PROMPT_PATH))
                                    st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                        template,
                                        clean_text
                                    )
                                except FileNotFoundError:
                                    pass

                            source_map = {
                                "cache": "кеш",
                                "manual": "ручні",
                                "auto": "авто"
                            }
                            source_text = source_map.get(
                                meta["source"], meta["source"])
                            status.update(
    label="Субтитри отримано ✅", state="complete")
                            update_status(
    f"Субтитри отримано! Джерело: {source_text}",
    "success",
    "Отримати субтитри",
     "Субтитри завантажено")
                            try:
                                st.toast(
    "Готово: Субтитри отримано!", icon="✅")
                            except:
                                pass
                            st.rerun()
                    except:
                        with st.spinner("Отримання субтитрів..."):
                            use_cache = True
                            raw_vtt, clean_text, meta = fetch_and_clean_subtitles(
                                st.session_state.youtube_url,
                                lang_mode=st.session_state.sub_lang_mode,
                                prefer_manual=st.session_state.prefer_manual,
                                use_cache=use_cache
                            )
                            st.session_state.raw_subtitles = raw_vtt
                            st.session_state.clean_subtitles = clean_text
                            st.session_state.subtitles_text = clean_text
                            st.session_state.original_length_chars = len(
                                clean_text)

                            if st.session_state.story_core_prompt_text:
                                st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                    st.session_state.story_core_prompt_text,
                                    clean_text
                                )
                            else:
                                try:
                                    template = load_prompt_file(
                                        str(STORY_CORE_PROMPT_PATH))
                                    st.session_state.story_core_prompt_text = inject_subtitles_into_prompt(
                                        template,
                                        clean_text
                                    )
                                except FileNotFoundError:
                                    pass

                            source_map = {
                                "cache": "кеш",
                                "manual": "ручні",
                                "auto": "авто"
                            }
                            source_text = source_map.get(
                                meta["source"], meta["source"])
                            update_status(
    f"Субтитри отримано! Джерело: {source_text}",
    "success",
    "Отримати субтитри",
     "Субтитри завантажено")
                            try:
                                st.toast(
    "Готово: Субтитри отримано!", icon="✅")
                            except:
                                pass
                            st.rerun()
                except Exception as e:
                    update_status(
    f"Помилка під час отримання субтитрів: {
        str(e)}", "error", "Отримати субтитри", "")
                    st.error(f"Помилка: {str(e)}")

        # Main content area with expanders (one-page layout)

        # Check for pending story_core updates before creating widgets
        if st.session_state.story_core_text_pending is not None:
            st.session_state.story_core_text = st.session_state.story_core_text_pending
            st.session_state.story_core_result = st.session_state.story_core_text_pending
            # Update hash to trigger re-injection in story prompt
            import hashlib
            st.session_state.story_core_result_hash = hashlib.md5(
    st.session_state.story_core_text_pending.encode()).hexdigest()
            st.session_state.story_core_text_pending = None

        # Check for pending story result updates before creating widgets
        if st.session_state.story_result_pending is not None:
            st.session_state.story_result = st.session_state.story_result_pending
            st.session_state.generated_story = st.session_state.story_result_pending
            st.session_state.story_result_pending = None

        # Auto-inject all story variables (STORY_CORE, TARGET_LENGTH_CHARS)
        # if they exist and haven't been injected yet (or if they changed)
        import hashlib

        # Create combined hash for all variables
        story_core_str = st.session_state.story_core_result if st.session_state.story_core_result else ""
        target_length_str = str(st.session_state.original_length_chars)
        combined_vars = f"{story_core_str}|{target_length_str}"
        current_hash = hashlib.md5(combined_vars.encode()).hexdigest()

        # Check if we need to inject (hash changed or prompt text is empty/template)
        # If hash is None, it means variables were just set and haven't been
        # injected yet
        if (st.session_state.story_variables_hash is None or
            st.session_state.story_variables_hash != current_hash or
            not st.session_state.story_prompt_text or
            st.session_state.story_prompt_text == st.session_state.story_prompt_template):

            # If prompt text is empty or same as template, load template first
            if not st.session_state.story_prompt_text or st.session_state.story_prompt_text == st.session_state.story_prompt_template:
                try:
                    template = load_prompt_file(str(STORY_PROMPT_PATH))
                    st.session_state.story_prompt_text = template
                    st.session_state.story_prompt_template = template
                except FileNotFoundError:
                    pass

            # Inject all variables (STORY_CORE, TARGET_LENGTH_CHARS)
            if st.session_state.story_prompt_text:
                st.session_state.story_prompt_text = inject_all_story_variables(
                    st.session_state.story_prompt_text,
                    st.session_state.story_core_result if st.session_state.story_core_result else "",
                    st.session_state.original_length_chars
                )
                # Update hash to prevent re-injection on next rerun
                st.session_state.story_variables_hash = current_hash

        # Expander 1: Clean Subtitles
        with st.expander("Субтитри (очищені)", expanded=False):
            st.subheader("Очищені субтитри")

            st.text_area(
                "Субтитри (очищені)",
                height=300,
                help="Очищений текст субтитрів (ORIGINAL_STORY)",
                key="clean_subtitles"
            )

            # Recalculate length when text changes (text_area with key
            # automatically updates session_state)
            if 'clean_subtitles' in st.session_state:
                st.session_state.original_length_chars = len(
                    st.session_state.clean_subtitles)

            st.metric(
                "К-сть символів (оригінал)",
                st.session_state.original_length_chars
            )

        # Expander 2: STORY_CORE Prompt (editable)
        with st.expander("Промпт STORY_CORE (можна редагувати)", expanded=False):
            st.subheader("Промпт STORY_CORE")

            st.text_area(
            "Шаблон промпту (можна редагувати)",
            height=300,
            help="Промпт для генерації STORY_CORE (субтитри вже підставлені)",
            key="story_core_prompt_text"
        )

        # Expander 3: STORY_CORE Result
        with st.expander("STORY_CORE результат", expanded=False):
            st.subheader("Результат STORY_CORE")
            st.text_area(
            "Згенерований STORY_CORE",
            height=300,
            help="Результат генерації STORY_CORE (можна редагувати)",
            key="story_core_text"
        )

            col1, col2 = st.columns(2)
        with col1:
            if st.button("Згенерувати STORY_CORE", type="primary"):
                if not st.session_state.story_core_prompt_text or not st.session_state.story_core_prompt_text.strip():
                    update_status(
    "Помилка: промпт STORY_CORE порожній",
    "error",
    "Згенерувати STORY_CORE (expander)",
     "")
                    st.error(
                        "Промпт порожній. Будь ласка, завантажте шаблон або введіть промпт.")
                else:
                    try:
                        try:
                            with st.status("Генерую STORY_CORE...", expanded=True) as status:
                                status.write(
                                    "Крок 1/1: Генерація STORY_CORE...")
                                prompt_to_send = st.session_state.story_core_prompt_text
                                from services.llm_client import generate_text
                                story_core_output = generate_text(
                                    prompt_to_send)
                                st.session_state.story_core_text_pending = story_core_output
                                st.session_state.story_core_result = story_core_output
                                import hashlib
                                st.session_state.story_core_result_hash = hashlib.md5(
                                    story_core_output.encode()).hexdigest()
                                st.session_state.story_core_prompt_filled = prompt_to_send
                                status.update(
    label="STORY_CORE згенеровано ✅", state="complete")
                                update_status(
    "STORY_CORE згенеровано успішно!",
    "success",
    "Згенерувати STORY_CORE (expander)",
     "STORY_CORE згенеровано")
                                try:
                                    st.toast(
    "Готово: STORY_CORE згенеровано!", icon="✅")
                                except:
                                    pass
                                st.rerun()
                        except:
                            with st.spinner("Генерація STORY_CORE..."):
                                prompt_to_send = st.session_state.story_core_prompt_text
                                story_core_output = generate_text(
    prompt_to_send, backend=st.session_state.llm_backend)
                                st.session_state.story_core_text_pending = story_core_output
                                st.session_state.story_core_result = story_core_output
                                import hashlib
                                st.session_state.story_core_result_hash = hashlib.md5(
                                    story_core_output.encode()).hexdigest()
                                st.session_state.story_core_prompt_filled = prompt_to_send
                                update_status(
    "STORY_CORE згенеровано успішно!",
    "success",
    "Згенерувати STORY_CORE (expander)",
     "STORY_CORE згенеровано")
                                try:
                                    st.toast(
    "Готово: STORY_CORE згенеровано!", icon="✅")
                                except:
                                    pass
                                st.rerun()
                    except ValueError as e:
                        update_status(
    f"Помилка: {
        str(e)}",
        "error",
        "Згенерувати STORY_CORE (expander)",
         "")
                        st.error(f"Помилка: {str(e)}")
                    except Exception as e:
                        update_status(
    f"Помилка генерації: {
        str(e)}",
        "error",
        "Згенерувати STORY_CORE (expander)",
         "")
                        st.error(f"Помилка генерації: {str(e)}")

        with col2:
            if st.button("Перегенерувати STORY_CORE (з поточним промптом)"):
                if not st.session_state.story_core_prompt_text or not st.session_state.story_core_prompt_text.strip():
                    st.error(
                        "Промпт порожній. Будь ласка, завантажте шаблон або введіть промпт.")
                else:
                    try:
                        with st.spinner("Перегенерація STORY_CORE..."):
                            # Use EXACTLY the content of the top textarea
                            prompt_to_send = st.session_state.story_core_prompt_text

                            # Call LLM with the prompt
                            from services.llm_client import generate_text
                            story_core_output = generate_text(prompt_to_send)

                            # Store in pending (will be applied on next rerun
                            # before widget creation)
                            st.session_state.story_core_text_pending = story_core_output
                            st.session_state.story_core_result = story_core_output
                            # Update hash to trigger re-injection in story
                            # prompt
                            import hashlib
                            st.session_state.story_core_result_hash = hashlib.md5(
                                story_core_output.encode()).hexdigest()
                            st.session_state.story_core_prompt_filled = prompt_to_send
                            st.success("STORY_CORE перегенеровано успішно!")
                            st.rerun()
                    except ValueError as e:
                        st.error(f"Помилка: {str(e)}")
                    except Exception as e:
                        st.error(f"Помилка генерації: {str(e)}")

        # Expander 4: Story Prompt (editable)
        with st.expander("Промпт історії (можна редагувати)", expanded=False):
            st.subheader("Промпт історії")
            st.text_area(
                "Шаблон промпту (можна редагувати)",
                height=300,
                help="Промпт для генерації історії (STORY_CORE вже підставлений)",
                key="story_prompt_text",
            )

        # Debug panel
        with st.expander("Debug / Raw AI response", expanded=False):
            from core.config import LLM_MODEL

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Model", LLM_MODEL)
                st.metric("TARGET_LENGTH_CHARS", st.session_state.debug_target_length_chars)
            with col2:
                st.metric("Prompt chars", st.session_state.debug_prompt_chars)
                st.metric("Story core chars", st.session_state.debug_story_core_chars)
            with col3:
                st.metric("Response chars", st.session_state.debug_response_chars)
                if st.session_state.debug_error:
                    st.error(f"Error: {st.session_state.debug_error}")

            st.divider()

            st.subheader("Prompt Preview (first 800 chars)")
            debug_last_prompt = st.session_state.get("debug_last_prompt", "")
            st.text_area(
                "Last prompt",
                value=debug_last_prompt[:800] if debug_last_prompt else "",
                height=150,
                disabled=True,
                key="debug_prompt_preview",
            )

            st.subheader("Response Preview (first 2000 chars)")
            debug_last_response = st.session_state.get("debug_last_response", "")
            st.text_area(
                "Last response",
                value=debug_last_response[:2000] if debug_last_response else "",
                height=200,
                disabled=True,
                key="debug_response_preview",
            )

            with st.expander("Full Prompt", expanded=False):
                st.text_area(
                    "Full prompt text",
                    value=debug_last_prompt,
                    height=300,
                    disabled=True,
                    key="debug_prompt_full",
                )

            with st.expander("Full Response", expanded=False):
                st.text_area(
                    "Full response text",
                    value=debug_last_response,
                    height=300,
                    disabled=True,
                    key="debug_response_full",
                )

        col1, col2 = st.columns(2)

        def _fill_story_prompt_for_send(prompt_template: str) -> str:
            """Fill story prompt placeholders; fallback to manual replacement."""
            try:
                return fill_story_prompt(
                    prompt_template,
                    st.session_state.story_core_result,
                    st.session_state.original_length_chars,
                    None,  # No slide_count
                )
            except Exception:
                prompt_to_send = prompt_template
                if "{TARGET_LENGTH_CHARS}" in prompt_to_send:
                    prompt_to_send = prompt_to_send.replace(
                        "{TARGET_LENGTH_CHARS}", str(st.session_state.original_length_chars)
                    )
                prompt_to_send = re.sub(
                    r"TARGET_LENGTH_CHARS:\s*\{[^}]*\}",
                    f"TARGET_LENGTH_CHARS: {st.session_state.original_length_chars}",
                    prompt_to_send,
                )
                prompt_to_send = re.sub(r"SLIDE_COUNT:\s*\{[^}]*\}", "", prompt_to_send)
                prompt_to_send = prompt_to_send.replace("{SLIDE_COUNT}", "")
                return prompt_to_send

        def _warn_on_placeholders(prompt_to_send: str) -> None:
            remaining_placeholders: list[str] = []
            if "{TARGET_LENGTH_CHARS}" in prompt_to_send or re.search(
                r"TARGET_LENGTH_CHARS:\s*\{", prompt_to_send
            ):
                remaining_placeholders.append("TARGET_LENGTH_CHARS")
            if "{{STORY_CORE}}" in prompt_to_send or "{STORY_CORE}" in prompt_to_send:
                remaining_placeholders.append("STORY_CORE")
            if remaining_placeholders:
                st.warning(
                    "Увага: Плейсхолдери не замінені: "
                    f"{', '.join(remaining_placeholders)}. Продовжую генерацію..."
                )

        def _is_llm_refusal(text: str | None) -> bool:
            if not text:
                return False
            low = text.lower()
            return ("i'm sorry" in text) or ("i can't assist" in low) or (
                "cannot" in low and "assist" in low
            )

        with col1:
            if st.button("Згенерувати історію", type="primary"):
                if not st.session_state.story_prompt_text or not st.session_state.story_prompt_text.strip():
                    update_status(
                        "Помилка: промпт історії порожній",
                        "error",
                        "Згенерувати історію (expander)",
                        "",
                    )
                    st.error("Промпт порожній. Будь ласка, завантажте шаблон або введіть промпт.")
                elif not st.session_state.story_core_result or not st.session_state.story_core_result.strip():
                    update_status(
                        "Помилка: STORY_CORE не згенеровано",
                        "error",
                        "Згенерувати історію (expander)",
                        "",
                    )
                    st.error("STORY_CORE не згенеровано. Будь ласка, спочатку згенеруйте STORY_CORE.")
                else:
                    prompt_template = st.session_state.story_prompt_text
                    try:
                        with st.status("Генерую історію...", expanded=True) as status:
                            status.write("Крок 1/1: Генерація історії...")

                            prompt_to_send = _fill_story_prompt_for_send(prompt_template)
                            _warn_on_placeholders(prompt_to_send)

                            # Store debug info before calling LLM
                            st.session_state.debug_last_prompt = prompt_to_send
                            st.session_state.debug_prompt_chars = len(prompt_to_send)
                            st.session_state.debug_story_core_chars = (
                                len(st.session_state.story_core_result)
                                if st.session_state.story_core_result
                                else 0
                            )
                            st.session_state.debug_target_length_chars = (
                                st.session_state.original_length_chars
                            )

                            from services.llm_client import generate_text
                            try:
                                story_output = generate_text(prompt_to_send)
                                st.session_state.debug_error = None
                            except Exception as e:
                                st.session_state.debug_error = str(e)
                                raise

                            # Store debug info after LLM call
                            st.session_state.debug_last_response = story_output
                            st.session_state.debug_response_chars = (
                                len(story_output) if story_output else 0
                            )

                            if _is_llm_refusal(story_output):
                                status.update(label="Помилка: LLM відмовився", state="error")
                                update_status(
                                    "LLM відмовився генерувати контент",
                                    "error",
                                    "Згенерувати історію (expander)",
                                    "",
                                )
                                st.error(
                                    "LLM відмовився генерувати контент. Можливі причини:\n"
                                    "- Промпт містить незамінені плейсхолдери\n"
                                    "- Контент порушує політику OpenAI\n"
                                    "- Промпт занадто складний або незрозумілий\n\n"
                                    f"Відповідь LLM: {story_output[:200]}..."
                                )
                                st.session_state.story_result_pending = story_output
                                st.session_state.story_prompt_filled = prompt_to_send
                                st.rerun()
                            else:
                                st.session_state.story_result_pending = story_output
                                st.session_state.generated_story = story_output
                                st.session_state.story_result = story_output
                                st.session_state.story_result_pending = None
                                st.session_state.story_prompt_filled = prompt_to_send
                                status.update(label="Історія згенерована ✅", state="complete")
                                update_status(
                                    "Історію згенеровано успішно!",
                                    "success",
                                    "Згенерувати історію (expander)",
                                    "Історія згенерована",
                                )
                                try:
                                    st.toast("Готово: Історія згенерована!", icon="✅")
                                except Exception:
                                    pass
                                st.rerun()
                    except Exception as e:
                        # Fallback path if st.status isn't available or if it fails
                        with st.spinner("Генерація історії..."):
                            try:
                                prompt_to_send = _fill_story_prompt_for_send(prompt_template)
                                _warn_on_placeholders(prompt_to_send)

                                from services.llm_client import generate_text
                                story_output = generate_text(prompt_to_send)

                                st.session_state.story_result_pending = story_output
                                st.session_state.generated_story = story_output
                                st.session_state.story_result = story_output
                                st.session_state.story_result_pending = None
                                st.session_state.story_prompt_filled = prompt_to_send
                                update_status(
                                    "Історію згенеровано успішно!",
                                    "success",
                                    "Згенерувати історію (expander)",
                                    "Історія згенерована",
                                )
                                try:
                                    st.toast("Готово: Історія згенерована!", icon="✅")
                                except Exception:
                                    pass
                                st.rerun()
                            except ValueError as ve:
                                update_status(
                                    f"Помилка: {str(ve)}",
                                    "error",
                                    "Згенерувати історію (expander)",
                                    "",
                                )
                                st.error(f"Помилка: {str(ve)}")
                            except Exception as ge:
                                update_status(
                                    f"Помилка генерації: {str(ge)}",
                                    "error",
                                    "Згенерувати історію (expander)",
                                    "",
                                )
                                st.error(f"Помилка генерації: {str(ge)}")
                                import traceback

                                st.code(traceback.format_exc())

        with col2:
            if st.button("Перегенерувати історію (з поточним промптом)"):
                if not st.session_state.story_prompt_text or not st.session_state.story_prompt_text.strip():
                    st.error("Промпт порожній. Будь ласка, завантажте шаблон або введіть промпт.")
                else:
                    try:
                        with st.spinner("Перегенерація історії..."):
                            prompt_template = st.session_state.story_prompt_text
                            prompt_to_send = _fill_story_prompt_for_send(prompt_template)
                            _warn_on_placeholders(prompt_to_send)

                            st.session_state.debug_last_prompt = prompt_to_send
                            st.session_state.debug_prompt_chars = len(prompt_to_send)
                            st.session_state.debug_story_core_chars = (
                                len(st.session_state.story_core_result)
                                if st.session_state.story_core_result
                                else 0
                            )
                            st.session_state.debug_target_length_chars = (
                                st.session_state.original_length_chars
                            )

                            from services.llm_client import generate_text
                            try:
                                story_output = generate_text(prompt_to_send)
                                st.session_state.debug_error = None
                            except Exception as e:
                                st.session_state.debug_error = str(e)
                                raise

                            st.session_state.debug_last_response = story_output
                            st.session_state.debug_response_chars = (
                                len(story_output) if story_output else 0
                            )

                            if _is_llm_refusal(story_output):
                                st.error(
                                    "LLM відмовився генерувати контент. Можливі причини:\n"
                                    "- Промпт містить незамінені плейсхолдери\n"
                                    "- Контент порушує політику OpenAI\n"
                                    "- Промпт занадто складний або незрозумілий\n\n"
                                    f"Відповідь LLM: {story_output[:200]}..."
                                )
                                st.session_state.story_result_pending = story_output
                                st.session_state.story_prompt_filled = prompt_to_send
                                st.rerun()
                            else:
                                st.session_state.story_result_pending = story_output
                                st.session_state.story_prompt_filled = prompt_to_send
                                st.success("Історію перегенеровано успішно!")
                                st.rerun()
                    except ValueError as ve:
                        st.error(f"Помилка: {str(ve)}")
                    except Exception as ge:
                        st.error(f"Помилка генерації: {str(ge)}")
                        import traceback

                        st.code(traceback.format_exc())

        # Expander 5: Story Result (auto-expands when story exists)
        has_story = bool(
            st.session_state.get("generated_story") or st.session_state.get("story_result")
        )
        with st.expander("Результат історії", expanded=has_story):
            st.subheader("Результат історії")
            st.text_area(
                "Згенерована історія",
                height=300,
                help="Результат генерації історії (можна редагувати)",
                key="generated_story",
            )

            # Add code block for easy copying
            st.code(st.session_state.generated_story or "", language=None)
    
    # ========================
    # TAB 2: ANALYTICS
    # ========================
    with tab_analytics:
        # Analytics and Improvement
        st.subheader("Аналітика та покращення")
        
        # Apply pending updates BEFORE creating widgets
        if st.session_state.analysis_story_input_pending is not None:
            st.session_state.analysis_story_input = st.session_state.analysis_story_input_pending
            st.session_state.analysis_story_input_pending = None
        
        # Single source of truth: story input field
        st.text_area(
            "Історія для аналітики (встав сюди)",
            key="analysis_story_input",
            height=350,
            help="Встав історію в це поле для аналізу та покращення"
        )
        
        # Convenience buttons
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Вставити згенеровану історію сюди"):
                if st.session_state.get("generated_story") and st.session_state.generated_story.strip():
                    st.session_state.analysis_story_input_pending = st.session_state.generated_story
                    st.success("Історію вставлено!")
                    st.rerun()
                else:
                    st.warning("Немає згенерованої історії для вставки.")
        
        with col_b:
            if st.button("Застосувати покращену як вхід"):
                if st.session_state.get("improved_story") and st.session_state.improved_story.strip():
                    st.session_state.analysis_story_input_pending = st.session_state.improved_story
                    st.success("Покращену історію застосовано як вхід!")
                    st.rerun()
                else:
                    st.warning("Немає покращеної історії для застосування.")
        
        st.divider()
        
        # Validate if we have input
        has_story_input = bool(st.session_state.get("analysis_story_input") and st.session_state.analysis_story_input.strip())
        has_improvement_prompt = bool(st.session_state.get("improvement_prompt"))
        
        col1, col2 = st.columns(2)
        with col1:
            analyze_button = st.button(
                "Згенерувати промпт для покращення (EN)",
                type="primary",
                disabled=not has_story_input
            )
        with col2:
            improve_button = st.button(
                "Покращити історію (EN)",
                type="primary",
                disabled=not has_story_input or not has_improvement_prompt
            )
        
        if not has_story_input:
            st.info("Встав історію у поле вище, щоб використати аналітику.")
        elif not has_improvement_prompt and improve_button:
            st.warning("Спочатку проаналізуйте історію, щоб створити промпт для покращення.")
        
        # Handle analyze button
        if analyze_button:
            # Validate input
            story = st.session_state.analysis_story_input.strip()
            if not story:
                st.error("Встав історію для аналізу у поле вище.")
            else:
                try:
                    with st.spinner("Аналіз історії..."):
                        # Prepare original subtitles (truncate if too long, but keep key parts)
                        original_text = st.session_state.get("clean_subtitles", "")
                        if len(original_text) > 5000:
                            # Keep first 2000 and last 2000 chars to preserve key parts
                            original_text = original_text[:2000] + "\n\n[...текст скорочено...]\n\n" + original_text[-2000:]
                        
                        # Use the dedicated input field as single source of truth
                        generated_text = story
                        
                        # Build analysis prompt with English-only instruction at the top
                        analysis_prompt = f"""OUTPUT LANGUAGE: For the "ПРОМПТ ДЛЯ ПОКРАЩЕННЯ" section, output ENGLISH ONLY. Do not output any Ukrainian/Russian in that section.

{ANALYSIS_PROMPT_TEMPLATE.format(
                            ORIGINAL=original_text,
                            GENERATED=generated_text
                        )}"""
                        
                        # Call LLM
                        analysis_response = generate_text(analysis_prompt, backend=st.session_state.llm_backend)
                        
                        # Parse response
                        analysis_report, comparison_table_md, improvement_prompt = parse_analysis_response(analysis_response)
                        
                        # Check if improvement_prompt contains Cyrillic characters
                        cyrillic_pattern = re.compile(r'[А-Яа-яІіЇїЄєҐґ]')
                        if improvement_prompt and cyrillic_pattern.search(improvement_prompt):
                            # Retry once with stronger English-only instruction
                            st.warning("Промпт для покращення містить неанглійські символи. Повторна спроба...")
                            retry_prompt = f"""OUTPUT LANGUAGE: ENGLISH ONLY. Do not output any Ukrainian/Russian.

{ANALYSIS_PROMPT_TEMPLATE.format(
                                ORIGINAL=original_text,
                                GENERATED=generated_text
                            )}

CRITICAL: The "ПРОМПТ ДЛЯ ПОКРАЩЕННЯ" section must be in ENGLISH ONLY. No other language."""
                            retry_response = generate_text(retry_prompt, backend=st.session_state.llm_backend)
                            analysis_report, comparison_table_md, improvement_prompt = parse_analysis_response(retry_response)
                            
                            # Check again
                            if improvement_prompt and cyrillic_pattern.search(improvement_prompt):
                                st.error("Модель повернула промпт не англійською після повторної спроби. Спробуйте ще раз.")
                                # Still store what we got, but show error
                        
                        # Store in session state
                        st.session_state.analysis_report = analysis_report
                        st.session_state.comparison_table_md = comparison_table_md
                        st.session_state.improvement_prompt = improvement_prompt
                        
                        st.success("Аналіз завершено успішно!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Помилка під час аналізу: {str(e)}")
        
        # Handle improve button
        if improve_button:
            # Validate input
            story = st.session_state.analysis_story_input.strip()
            if not story:
                st.error("Встав історію для аналізу у поле вище.")
            elif not has_improvement_prompt:
                st.error("Спочатку згенеруй промпт для покращення.")
            else:
                try:
                    with st.spinner("Покращення історії..."):
                        # Use the dedicated input field as single source of truth
                        generated_text = story
                        improvement_prompt_text = st.session_state.get("improvement_prompt", "")
                        
                        # Build improve prompt with English-only instruction and format requirements
                        improve_prompt = f"""OUTPUT LANGUAGE: ENGLISH ONLY. Do not output any Ukrainian/Russian.

{improvement_prompt_text}

ORIGINAL GENERATED STORY (to rewrite):
    {generated_text}

Rewrite the story according to the instructions above, preserving key facts and improving identified weaknesses.

STRICT FORMAT REQUIREMENTS:
    - Each slide must be exactly:
        text:{{...}}
  prompt:{{...}}
- No headings, no numbering, no markdown.
- Preserve the exact slide structure.
- Output in ENGLISH ONLY.

ANTI-COPY RULES (CRITICAL):
    - You MUST rewrite every text:{{...}} block.
- DO NOT reuse original sentences.
- Change wording in EVERY slide while keeping meaning.
- If output is too similar to input, rewrite more aggressively.
- Paraphrase, rephrase, restructure - but keep the core facts and narrative flow.
- This is a REWRITE task, not a copy-paste task."""
                        
                        # Call LLM
                        improved_story = generate_text(improve_prompt, backend=st.session_state.llm_backend)
                        
                        # Validate: Check for Cyrillic characters
                        cyrillic_pattern = re.compile(r'[А-Яа-яІіЇїЄєҐґ]')
                        if cyrillic_pattern.search(improved_story):
                            st.error("Модель повернула не англійською. Натисни 'Покращити історію (EN)' ще раз.")
                            # Do NOT store improved_story when invalid
                        else:
                            # Similarity guard: check if output is too similar to input
                            def normalize_text(text):
                                """Normalize text for similarity comparison."""
                                return ' '.join(text.lower().split())
                            
                            normalized_input = normalize_text(generated_text)
                            normalized_improved = normalize_text(improved_story)
                            
                            # Calculate similarity ratio
                            similarity_ratio = difflib.SequenceMatcher(None, normalized_input, normalized_improved).ratio()
                            
                            if similarity_ratio > 0.97:
                                st.warning(f"Покращення вийшло ідентичним (схожість: {similarity_ratio:.2%}). Натисни ще раз або підкрути промпт.")
                                # Do NOT update improved_story when too similar
                            else:
                                # Store in session state only if valid and different
                                st.session_state.improved_story = improved_story
                                st.success(f"Історію покращено успішно! Схожість з оригіналом: {similarity_ratio:.2%}")
                                st.rerun()
                except Exception as e:
                    st.error(f"Помилка під час покращення: {str(e)}")
        
        # Display analysis report
        if st.session_state.get("analysis_report"):
            st.divider()
            st.subheader("Звіт аналізу")
            # Use markdown for better formatting, or text_area readonly
            st.markdown(st.session_state.analysis_report)
        
        # Display comparison table
        if st.session_state.get("comparison_table_md"):
            st.divider()
            st.subheader("Таблиця порівняння")
            st.markdown(st.session_state.comparison_table_md)
        
        # Display improvement prompt (editable)
        if st.session_state.get("improvement_prompt"):
            st.divider()
            st.subheader("Промпт для покращення")
        st.text_area(
                "Промпт для покращення (можна редагувати)",
                height=200,
                help="Промпт для покращення історії (можна редагувати перед покращенням)",
                key="improvement_prompt"
            )
            st.code(st.session_state.improvement_prompt or "", language=None)
        
        # Display improved story (editable) - separate output field
        if st.session_state.get("improved_story"):
            st.divider()
            st.subheader("Покращена історія (результат)")
            st.text_area(
                "Покращена історія (результат)",
            height=300,
                help="Покращена версія історії (можна редагувати)",
                key="improved_story"
        )
            st.code(st.session_state.improved_story or "", language=None)


if __name__ == "__main__":
    main()

