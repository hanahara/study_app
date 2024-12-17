import streamlit as st
from datetime import datetime , timedelta
import pytz
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import os
import sqlite3

proxie = { "https//:socks5://socks.hide.me:1080" }

proxies = proxie



def save_to_db(question_data):
    conn = sqlite3.connect('questions.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS questions
                 (question TEXT, response TEXT, evaluation INTEGER, time TIMESTAMP)''')
    c.execute('''INSERT INTO questions (question, response, evaluation, time) VALUES (?, ?, ?, ?)''',
              (question_data['question'], question_data['response'], question_data['evaluation'], question_data['time']))
    conn.commit()
    conn.close()

# 呼び出し時に保存
    save_to_db(question_data)       

# --- AppState Class to Manage Global States ---
class AppState:
    def __init__(self):
        if "question_data" not in st.session_state:
            st.session_state.question_data = []  # 質問、回答、評価をまとめて保存
        if "reminder_time" not in st.session_state:
            st.session_state.reminder_time = None
        if "current_question_index" not in st.session_state:
            st.session_state.current_question_index = 0
        if "messages" not in st.session_state:
            st.session_state.messages = [SystemMessage(content="You are a helpful assistant.")]

    def add_question(self, question):
        reminder_time = self.get_reminder_time()
        st.session_state.question_data.append({
            "question": question,
            "time": datetime.now(),
            "reminder_time": reminder_time,
            "response": None,
            "visible": False,
            "evaluated": False,
            "evaluation": None
        })

    def set_reminder_time(self, reminder_time):
        st.session_state.reminder_time = reminder_time

    def get_reminder_time(self):
        return st.session_state.reminder_time

    def save_to_history(self, question_data):
        if "history" not in st.session_state:
            st.session_state.history = []  # historyもここで初期化
        st.session_state.history.append(question_data)

# --- ChatManager Class for Handling Q&A ---
class ChatManager:
    def __init__(self, app_state, llm):
        self.app_state = app_state
        self.llm = llm

    def generate_fun_fact(self, question):
        """質問内容に基づいて豆知識を生成する"""
        # 例: 簡易的に質問内容に関連したテキストを生成する
        st.session_state.messages.append(HumanMessage(content=f"質問: {question} に関する興味深い豆知識を教えてください。"))
        response = self.llm(st.session_state.messages)
        st.session_state.messages.append(AIMessage(content=response.content))
        return response.content    

    def count_pending_questions(self):
        return sum(1 for q in st.session_state.question_data if not q['response'] and not q['visible'])

    def show_current_question(self):
        question_data = st.session_state.question_data
        if question_data and len(question_data) > st.session_state.current_question_index:
            current_question = question_data[st.session_state.current_question_index]
            self.display_question_answer(current_question)

    def display_question_answer(self, question_data):
    # 動的に表示するための空のプレースホルダーを作成
        message_placeholder = st.empty()
    
        # 1週間後の指定時刻を計算
        reminder_time = self.app_state.get_reminder_time()
        if reminder_time:
            reminder_datetime = question_data['time'].replace(
                hour=reminder_time.hour,
                minute=reminder_time.minute,
                second=0, microsecond=0
            ) + timedelta(days=0)
    
            # 現在の時間がリマインダー時刻を過ぎているかチェック
            if datetime.now() >= reminder_datetime:
                question_data['visible'] = True
    
        # 質問と回答をカード形式で表示
        if question_data['visible']:
            with message_placeholder.container():
                col1, col2 = st.columns([1, 4])
                with col1:
                    st.markdown("### 質問")
                    st.write(f"**{question_data['question']}**")
                with col2:
                    st.markdown("### 回答")
                    if not question_data['response']:
                        self.generate_response(question_data)
                    if question_data['response']:
                        st.write(f"**{question_data['response']}**")
                    
                    # 豆知識を表示
                    fun_fact = self.generate_fun_fact(question_data['question'])
                    st.info(f"豆知識: {fun_fact}")
        else:
            # 残り時間を表示
            time_remaining = reminder_datetime - datetime.now()
            days, remainder = divmod(time_remaining.total_seconds(), 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes = remainder // 60
    
            message_placeholder.write(
                f"この質問と回答はあと {int(days)}日 {int(hours)}時間 {int(minutes)}分で表示されます。"
            )

        

    def generate_response(self, question_data):
        with st.spinner("回答を待っています..."):
            # 質問をLLMに渡して回答を生成
            st.session_state.messages.append(HumanMessage(content=question_data['question']))
            response = self.llm(st.session_state.messages)
            question_data['response'] = response.content  # 回答をデータに保存
            st.session_state.messages.append(AIMessage(content=response.content))
            st.success("回答が届きました！")

    def get_evaluation(self, question_data):
        evaluation = st.slider("この回答を評価してください (1〜10):", 1, 10)
        if st.button("評価を送信"):
            question_data['evaluated'] = True
            question_data['evaluation'] = evaluation
            self.app_state.save_to_history(question_data)
            st.success("評価が送信されました！")
    
            
    def next_question(self):
        if st.session_state.current_question_index < len(st.session_state.question_data) - 1:
            st.session_state.current_question_index += 1

        

# --- ReminderManager Class for Reminder Time ---
class ReminderManager:
    def __init__(self, app_state):
        self.app_state = app_state

    def set_reminder(self):
        st.write("回答を返す時刻を設定してください")
        
        # 選択肢を定義（6通りの時刻）
        time_options = [
            datetime.strptime("07:00", "%H:%M").time(),
            datetime.strptime("10:00", "%H:%M").time(),
            datetime.strptime("12:00", "%H:%M").time(),
            datetime.strptime("15:00", "%H:%M").time(),
            datetime.strptime("19:00", "%H:%M").time(),
            datetime.strptime("22:00", "%H:%M").time()
        ]
        
        # セレクトボックスで選択
        selected_time = st.selectbox("回答を返す時間を選んでください", time_options, format_func=lambda t: t.strftime("%H:%M"))
        
        if st.button("時刻を設定"):
            self.app_state.set_reminder_time(selected_time)
            st.success(f"回答を返す時刻を {selected_time.strftime('%H:%M')} に設定しました")

    def get_reminder(self):
        return self.app_state.get_reminder_time()


class HistoryManager:
    def show_history(self):
        st.write("過去の質問と評価履歴")
    
        # 履歴データを取得
        history = st.session_state.get("history", [])
        if not history:
            st.write("履歴がまだありません")
            return
    
        # 並べ替えとフィルタリング用の選択肢
        sort_option = st.radio("並べ替え:", ("評価の大きい順", "評価の小さい順"))
        filter_option = st.slider("特定の評価でフィルタリング (0: 全て表示)", 0, 10, 0)
    
        # 履歴の並べ替え
        if sort_option == "評価の大きい順":
            history = sorted(history, key=lambda x: (-x['evaluation'] if x['evaluation'] is not None else -1, x['time']))
        elif sort_option == "評価の小さい順":
            history = sorted(history, key=lambda x: (x['evaluation'] if x['evaluation'] is not None else 11, x['time']))
    
        # 履歴のフィルタリング
        if filter_option > 0:
            history = [item for item in history if item['evaluation'] == filter_option]
    
        # 履歴の表示
        if history:
            for item in history:
                with st.container():
                    st.write(f"**質問:** {item['question']}")
                    st.write(f"**回答:** {item['response']}")
                    st.write(f"**評価:** {item['evaluation'] or '未評価'}")
                    st.write(f"**評価日時:** {item['time'].strftime('%Y-%m-%d %H:%M:%S')}")
                    st.markdown("---")
        else:
            st.write("該当する履歴がありません")
    



# --- Main App Logic ---
def main():

    # ページ選択のためのラジオボタン
    page = st.sidebar.radio("ページを選択", ("質問送信", "回答評価", "履歴"))

    st.title("質問アプリ")
    if page == "質問送信":
        st.subheader('質問送信')
    elif page == "回答評価":
        st.subheader('回答評価')
    else :
        st.subheader('履歴')


    openai_api_key = os.getenv("OPENAI_API_KEY")
    llm = ChatOpenAI(temperature=0, api_key=openai_api_key)

    app_state = AppState()
    chat_manager = ChatManager(app_state, llm)
    reminder_manager = ReminderManager(app_state)
    history_manager = HistoryManager()

    
    if page == "質問送信":
        # 1. 時刻設定（最初に設定）
        if not app_state.get_reminder_time():
            reminder_manager.set_reminder()

        # 2. 質問の入力
        user_input = st.text_input("質問を入力してください:", "", key="question_input", autocomplete="off")
        if st.button("質問を送信"):
            app_state.add_question(user_input)

        # 3. 回答を待っている質問の数を表示
        pending_count = chat_manager.count_pending_questions()
        st.write(f"回答を待っている質問の数: {pending_count}")

    elif page == "回答評価":
        # 4. 現在の質問と回答を表示（1つだけ）
        chat_manager.show_current_question()

    elif page == "履歴":
        # 6. 履歴の表示
        if st.button("履歴を表示"):
            history_manager.show_history()
     

if __name__ == '__main__':
    main()

# streamlit run /Users/hb21a088/Desktop/python_lesson/my_python/main.py
