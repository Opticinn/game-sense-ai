# app/services/rag_chat.py
from langchain_ollama       import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from app.config              import settings
from app.services.agent_tools import ALL_TOOLS


class RAGChatEngine:
    """
    Engine utama yang menggabungkan:
    - Qwen2.5 7B (via Ollama) sebagai LLM
    - LangChain tools untuk tool calling
    - Vector Store untuk semantic search
    """

    def __init__(self):
        self.agent   = None
        self.loaded  = False


    def load(self):
        """Inisialisasi LLM dan agent."""
        if self.loaded:
            return

        print("🔄 Loading Qwen2.5 7B via Ollama...")

        from langgraph.prebuilt import create_react_agent

        llm = ChatOllama(
            model       = settings.LLM_MODEL,
            base_url    = settings.OLLAMA_BASE_URL,
            temperature = 0.7,
            num_predict = 1000,
        )

        self.agent = create_react_agent(
            model = llm,
            tools = ALL_TOOLS,
        )

        self.loaded = True
        print("✅ RAG Chat Engine loaded!")


    def ask(self, query: str, user_id: str = None) -> dict:
        """
        Terima query user dan kembalikan jawaban dari agent.
        """
        self.load()

        # System message — instruksi untuk LLM
        system_msg = SystemMessage(content="""You are GameSense AI, an intelligent game recommendation assistant.
You help users find the best games based on their preferences.
You can answer in Bahasa Indonesia or English depending on the user's language.
If user asks about mods, always use get_mod_games tool first.
If user asks about price, use get_game_price tool.
If user asks about gameplay videos, use get_gameplay_video tool.
If no login, add at the end: '💡 Login untuk rekomendasi yang lebih personal!'
Always be helpful, concise, and accurate.""")

        human_msg = HumanMessage(content=query)

        try:
            result   = self.agent.invoke({"messages": [system_msg, human_msg]})
            messages = result.get("messages", [])

            # Ambil pesan terakhir dari agent
            answer = ""
            for msg in reversed(messages):
                if hasattr(msg, "content") and msg.content:
                    answer = msg.content
                    break

            if not answer:
                answer = "Maaf, tidak bisa menghasilkan jawaban."

            # Tambahkan notifikasi login kalau belum login
            if not user_id and "login" not in answer.lower():
                answer += "\n\n💡 Login untuk rekomendasi yang lebih personal!"

            return {
                "answer"     : answer,
                "sources"    : [],
                "is_personal": user_id is not None,
            }

        except Exception as e:
            print(f"❌ Error: {e}")
            return {
                "answer"     : f"Maaf, terjadi kesalahan. Pastikan Ollama sedang berjalan.",
                "sources"    : [],
                "is_personal": False,
            }


# Singleton
rag_chat_engine = RAGChatEngine()