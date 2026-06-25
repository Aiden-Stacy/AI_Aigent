import streamlit as st
import requests
import base64
import os
import io
from PIL import Image
import tempfile

# ----------------- CẤU HÌNH -----------------
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.2"  

# ----------------- HÀM ĐỌC FILE -----------------
def read_text_file(uploaded_file):
    ext = os.path.splitext(uploaded_file.name)[1].lower()
    try:
        if ext == ".txt":
            return uploaded_file.read().decode("utf-8")
        elif ext == ".csv":
            return uploaded_file.read().decode("utf-8")
        elif ext == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(uploaded_file.read()))
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        elif ext == ".docx":
            import docx
            doc = docx.Document(io.BytesIO(uploaded_file.read()))
            return "\n".join([p.text for p in doc.paragraphs])
        else:
            return f"[File: {uploaded_file.name} - Không thể đọc nội dung]"
    except Exception as e:
        return f"Lỗi đọc file: {str(e)}"

# ----------------- HÀM GỌI OLLAMA (CÓ HỖ TRỢ ẢNH) -----------------
def call_ollama(prompt, image_base64=None, history=None, system_prompt=None):
    """
    Gọi Ollama với tùy chọn system prompt và lịch sử.
    Nếu không có history, chỉ gửi một tin nhắn user.
    """
    messages = []
    # Thêm system prompt nếu có
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    
    # Nếu có history, thêm vào (bỏ qua system nếu có)
    if history:
        # Lọc ra các tin nhắn không phải system để tránh trùng
        for msg in history:
            if msg["role"] != "system":
                messages.append(msg)
    
    # Tạo message user
    user_msg = {"role": "user", "content": prompt}
    if image_base64:
        user_msg["images"] = [image_base64]
    messages.append(user_msg)
    
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        assistant_msg = data["message"]["content"]
        # Trả về tin nhắn assistant và lịch sử mới (chỉ khi có history)
        if history is not None:
            history.append(user_msg)
            history.append({"role": "assistant", "content": assistant_msg})
            return assistant_msg, history
        else:
            return assistant_msg, None
    except Exception as e:
        st.error(f"Lỗi kết nối Ollama: {str(e)}")
        if hasattr(e, 'response') and e.response:
            st.error(f"Chi tiết từ Ollama: {e.response.text}")
        return None, (history if history is not None else None)

# ----------------- CÁC HÀM XỬ LÝ CHUYÊN BIỆT -----------------
def generate_quiz(topic, num_questions, context_text):
    """Sinh câu hỏi ôn tập"""
    if not topic:
        return "⚠️ Vui lòng nhập chủ đề."
    system_prompt = """Bạn là trợ lý ôn thi chuyên nghiệp. Trả lời bằng định dạng Markdown đẹp, sử dụng **in đậm** cho tiêu đề, gạch đầu dòng, và bảng nếu cần."""
    user_prompt = f"""
    Hãy sinh **{num_questions} câu hỏi ôn tập** chất lượng cao về chủ đề "{topic}".
    - Bao gồm cả câu trắc nghiệm (4 đáp án A, B, C, D) và câu tự luận.
    - Trình bày dưới dạng danh sách đánh số rõ ràng.
    - Với câu trắc nghiệm, xuống dòng cho từng đáp án.
    - Cuối cùng, cung cấp đáp án cho các câu trắc nghiệm.
    - Nếu có nội dung đề cương bên dưới, hãy bám sát nội dung đó.
    """
    if context_text:
        user_prompt += f"\n\n=== ĐỀ CƯƠNG MÔN HỌC ===\n{context_text}"
    answer, _ = call_ollama(user_prompt, image_base64=None, history=None, system_prompt=system_prompt)
    return answer

def explain_concept(concept, context_text):
    """Giải thích Khái Niệm"""
    if not concept:
        return "⚠️ Vui lòng nhập khái niệm cần giải thích."
    system_prompt = "Bạn là giáo viên giỏi. Giải thích rõ ràng, có cấu trúc, dễ hiểu. Sử dụng Markdown."
    user_prompt = f"""
    Hãy giải thích khái niệm **"{concept}"** một cách chi tiết, dễ hiểu.
    Trình bày có cấu trúc:
    - **Định nghĩa chính xác**
    - **Ví dụ minh họa** (liên hệ với đề cương nếu có)
    - **Ý nghĩa / ứng dụng** (dạng gạch đầu dòng)
    """
    if context_text:
        user_prompt += f"\n\n=== ĐỀ CƯƠNG MÔN HỌC ===\n{context_text}"
    answer, _ = call_ollama(user_prompt, image_base64=None, history=None, system_prompt=system_prompt)
    return answer

def create_flashcards(topic, num_cards, context_text):
    """Tạo bảng flashcard"""
    if not topic:
        return "⚠️ Vui lòng nhập chủ đề."
    system_prompt = """Bạn là trợ lý học tập. Xuất kết quả dưới dạng bảng Markdown với 3 cột: STT | Mặt trước | Mặt sau."""
    user_prompt = f"""
    Hãy trích xuất **{num_cards} thuật ngữ / khái niệm quan trọng nhất** về chủ đề "{topic}".
    **YÊU CẦU ĐỊNH DẠNG BẮT BUỘC:** Bạn PHẢI tạo ra một bảng Markdown với 3 cột như sau:

    | STT | Mặt trước (Thuật ngữ / Câu hỏi) | Mặt sau (Định nghĩa / Trả lời ngắn gọn) |
    |-----|--------------------------------|-----------------------------------------|
    | 1   | ...                            | ...                                     |
    | 2   | ...                            | ...                                     |

    (Tạo đủ số lượng yêu cầu. Nội dung phải bám sát đề cương được cung cấp)
    """
    if context_text:
        user_prompt += f"\n\n=== ĐỀ CƯƠNG MÔN HỌC ===\n{context_text}"
    answer, _ = call_ollama(user_prompt, image_base64=None, history=None, system_prompt=system_prompt)
    return answer

# ----------------- GIAO DIỆN STREAMLIT -----------------
st.set_page_config(page_title="AI Trợ Lý Học Tập", layout="wide")
st.title("📚 TRỢ LÝ AI HỌC TẬP THEO ĐỀ CƯƠNG VIP PRO MAX 999+")
st.caption(f"ĐANG SỬ DỤNG MODEL: `{MODEL_NAME}`")

# Khởi tạo session state
if "history" not in st.session_state:
    st.session_state.history = []          # Lịch sử cho tab Chat
if "uploaded_image_b64" not in st.session_state:
    st.session_state.uploaded_image_b64 = None
if "uploaded_text" not in st.session_state:
    st.session_state.uploaded_text = None


    # Hiển thị trạng thái
    if st.session_state.uploaded_text:
        st.info("📄 Đã có nội dung văn bản (đề cương) trong ngữ cảnh.")
    if st.session_state.uploaded_image_b64:
        st.info("🖼️ Đã có ảnh trong ngữ cảnh (chỉ dùng cho Chat).")

    if st.button("🗑️ Xóa lịch sử chat"):
        st.session_state.history = []
        st.rerun()

# Main area: Tabs chức năng
tab1, tab2, tab3, tab4 = st.tabs(["💬 Chat tự do", "📝 Sinh câu hỏi", "💡 Giải thích khái niệm", "🃏 Tạo Flashcard"])

# ----- Tab 1: Chat tự do (giữ nguyên chức năng cũ) -----
with tab1:
    st.subheader("Trò chuyện với AI (có thể kèm ảnh)")
    # Hiển thị lịch sử chat
    for msg in st.session_state.history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    
    prompt = st.chat_input("Nhập câu hỏi của bạn...")
    if prompt:
        # Hiển thị câu hỏi
        with st.chat_message("user"):
            st.markdown(prompt)
        # Chuẩn bị nội dung
        final_prompt = prompt
        if st.session_state.uploaded_text:
            final_prompt = f"{prompt}\n\nNội dung file đính kèm:\n{st.session_state.uploaded_text}"
        image_b64 = st.session_state.uploaded_image_b64
        # Gọi Ollama với lịch sử
        with st.chat_message("assistant"):
            placeholder = st.empty()
            with st.spinner("Đang suy nghĩ..."):
                answer, new_history = call_ollama(final_prompt, image_b64, st.session_state.history)
                if answer:
                    placeholder.markdown(answer)
                    st.session_state.history = new_history
                else:
                    placeholder.error("Không nhận được phản hồi từ Ollama.")

# ----- Tab 2: Sinh câu hỏi -----
with tab2:
    st.subheader("📝 Sinh câu hỏi ôn tập")
    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("Chủ đề cần ôn", placeholder="Ví dụ: Hệ điều hành, Mạng máy tính...")
    with col2:
        num_q = st.number_input("Số lượng câu hỏi", min_value=3, max_value=15, value=5, step=1)
    if st.button("🚀 Sinh câu hỏi", type="primary"):
        if not topic:
            st.warning("Vui lòng nhập chủ đề.")
        else:
            context = st.session_state.uploaded_text if st.session_state.uploaded_text else ""
            with st.spinner("Đang tạo câu hỏi..."):
                result = generate_quiz(topic, num_q, context)
                if result:
                    st.markdown(result)

# ----- Tab 3: Giải thích khái niệm -----
with tab3:
    st.subheader("💡 Giải thích khái niệm")
    concept = st.text_input("Nhập khái niệm cần giải thích", placeholder="Ví dụ: Đa luồng (Multithreading)")
    if st.button("🔍 Giải thích ngay", type="primary"):
        if not concept:
            st.warning("Vui lòng nhập khái niệm.")
        else:
            context = st.session_state.uploaded_text if st.session_state.uploaded_text else ""
            with st.spinner("Đang giải thích..."):
                result = explain_concept(concept, context)
                if result:
                    st.markdown(result)

# ----- Tab 4: Tạo Flashcard -----
with tab4:
    st.subheader("🃏 Tạo Flashcard dạng bảng")
    col1, col2 = st.columns([3, 1])
    with col1:
        flash_topic = st.text_input("Chủ đề tạo flashcard", placeholder="Ví dụ: Các khái niệm cơ bản về AI")
    with col2:
        num_cards = st.number_input("Số lượng thẻ", min_value=5, max_value=30, value=10, step=1)
    if st.button("🛠️ Tạo Flashcard", type="primary"):
        if not flash_topic:
            st.warning("Vui lòng nhập chủ đề.")
        else:
            context = st.session_state.uploaded_text if st.session_state.uploaded_text else ""
            with st.spinner("Đang tạo flashcard..."):
                result = create_flashcards(flash_topic, num_cards, context)
                if result:
                    st.markdown(result)
                    # Thêm nút tải xuống (tùy chọn)
                    st.download_button(
                        label="📥 Tải flashcard dạng Markdown",
                        data=result,
                        file_name="flashcard.md",
                        mime="text/markdown"
                    )