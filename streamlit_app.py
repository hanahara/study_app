import streamlit as st
from datetime import datetime, timedelta
from langchain.chat_models import ChatOpenAI
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import os
import random


def initialize_state():
    """セッションステートの初期化"""
    if "all_questions" not in st.session_state:
        st.session_state.all_questions = []
    if "current_question" not in st.session_state:
        st.session_state.current_question = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def add_question(question):
    question_id = len(st.session_state.all_questions) + 1
    question_data = {
        "id": question_id,
        "question": question,
        "timer": 60,  # 1分 (60秒)
        "time": datetime.now(),
        "response": None,
        "fun_fact": None,
        "visible": False,
        "evaluated": False,
        "evaluation": None
    }
    st.session_state.all_questions.append(question_data)













# --- ChatManager Class for Handling Q&A ---
class ChatManager:
    def __init__(self, llm):
        self.llm = llm

    def generate_response(self, question_data):
        # 回答がまだ生成されていない場合のみ生成
        if question_data["response"] is None:
            st.session_state.messages.append(HumanMessage(content=question_data["question"]))
            with st.spinner("回答を待っています..."):
                response = self.llm(st.session_state.messages)
                question_data["response"] = response.content  # 回答をデータに保存
                st.session_state.messages.append(AIMessage(content=response.content))
                st.success("回答が届きました！")

    def generate_fun_fact(self, question_data):
        # 豆知識がまだ生成されていない場合のみ生成
        if question_data["fun_fact"] is None:
            content = f"質問: {question_data['question']} に関する興味深い豆知識を教えてください。"
            st.session_state.messages.append(HumanMessage(content))
            fun_fact = self.llm(st.session_state.messages)
            question_data["fun_fact"] = fun_fact.content
            st.session_state.messages.append(AIMessage(content=fun_fact.content))

    def display_random_response(self, question_data):
        now = datetime.now()

        # 時間が経過していない場合は、次の回答までの時間を表示
        timer = question_data["timer"]
        if (now - question_data["time"]).seconds < timer:
            next_update = question_data["time"] + timedelta(seconds=timer)
            remaining_time = next_update - datetime.now()
            minutes, seconds = divmod(remaining_time.seconds, 60)
            st.info(f"次の回答まで: {minutes}分 {seconds}秒")
            return

        # 回答と豆知識を生成
        self.generate_response(question_data)
        self.generate_fun_fact(question_data)

        # 回答を表示
        st.write(f"### 質問 {question_data['id']}: {question_data['question']}")
        st.write(f"**回答:** {question_data['response']}")
        st.write(f"**豆知識:** {question_data['fun_fact']}")

        # 評価の処理
        self.get_evaluation(question_data)

    def get_evaluation(self, question_data):
        if not question_data["evaluated"]:
            evaluation = st.slider(f"質問 {question_data['id']} の評価", min_value=1, max_value=10, value=5)
            if st.button("評価を送信"):
                question_data["evaluated"] = True
                question_data["evaluation"] = evaluation
                st.success(f"質問 {question_data['id']} の評価が送信されました！")












# --- HistoryManager Class ---
class HistoryManager:
    def show_history(self):
        # 評価済みの質問のみ表示
        questions = [q for q in st.session_state.all_questions if q["evaluated"]]
        for q in questions:
            st.write(f"**質問 {q['id']}**: {q['question']}")
            st.write(f"- 回答: {q['response'] or '未回答'}")
            st.write(f"- 豆知識: {q['fun_fact'] or '未回答'}")
            st.write(f"- 評価: {q['evaluation']}")
            st.write(f"- 質問日時: {(q['time']).strftime('%Y-%m-%d %H:%M')}")
            st.markdown("---")












# --- Main App Logic ---
def main():
    page = st.sidebar.radio("ページを選択", ("質問送信", "回答評価", "履歴"))

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        st.error("OpenAI APIキーが設定されていません。環境変数を確認してください。")
        return

    llm = ChatOpenAI(temperature=0, api_key=openai_api_key)
    
    chat_manager = ChatManager(llm)
    history_manager = HistoryManager()

    initialize_state()

    if page == "質問送信":
        st.subheader('質問送信')
        user_input = st.text_input("質問を入力してください:", "", key="question_input", autocomplete="off")
        
        if st.button("質問を送信"):
            if user_input.strip():  # 空白入力を防ぐ
                add_question(user_input)
                st.success(f"質問 '{user_input}' が送信されました。")
                user_input = ""  # 入力欄をリセット
            else:
                st.warning("質問を入力してください。")

        # 未抽選の質問の数
        pending_count = len([q for q in st.session_state.all_questions if not q['evaluated']])
        st.write(f"未抽選の質問の数: {pending_count}")

        # 質問の抽選を開始
        if st.button("質問の抽選を開始"):
            if pending_count > 0 and st.session_state.current_question is None:  # 前回の評価が終わっていない場合は抽選不可
                next_question = random.choice([q for q in st.session_state.all_questions if not q['evaluated']])
                st.session_state.current_question = next_question
                st.success(f"質問 '{next_question['question']}' が抽選されました。")
            else:
                st.write("評価されていない質問がまだあります。")

    elif page == "回答評価":
        st.subheader('回答評価')
        if st.session_state.current_question:
            chat_manager.display_random_response(st.session_state.current_question)
        else:
            st.warning("質問が選ばれていません。質問送信ページで質問を送信してください。")

    elif page == "履歴":
        st.subheader('履歴')
        history_manager.show_history()

if __name__ == '__main__':
    main()


# streamlit run /Users/hb21a088/Desktop/python_lesson/my_python/main.py
