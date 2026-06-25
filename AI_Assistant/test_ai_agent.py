import requests
import csv
import json
import time
import os
from datetime import datetime

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_TEXT = "llama3.2"       # Dùng model text cho test
# MODEL_VISION = "llava"      # Không dùng ảnh ở đây

# Đọc câu hỏi từ file CSV
def load_questions(file_path):
    questions = []
    with open(file_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append({
                "id": row["id"],
                "question": row["question"],
                "expected": row["expected_answer"]
            })
    return questions

# Gửi một câu hỏi đến Ollama
def ask_ollama(question, model=MODEL_TEXT, context=None):
    messages = []
    if context:
        messages = context.copy()
    messages.append({"role": "user", "content": question})

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": 0.3}  # Giảm ngẫu nhiên để ổn định
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return data["message"]["content"]
    except Exception as e:
        return f"LỖI: {str(e)}"

# Hàm đánh giá câu trả lời (bằng cách so sánh với đáp án mẫu hoặc dùng AI)
def evaluate_answer(question, answer, expected):
    # Đánh giá thủ công đơn giản: xem có từ khóa quan trọng trong câu trả lời không
    keywords = expected.lower().split()
    score = 0
    answer_lower = answer.lower()
    for kw in keywords:
        if kw in answer_lower:
            score += 1
    # Tỷ lệ từ khóa xuất hiện
    ratio = score / len(keywords) if keywords else 0
    return ratio  # 0->1, có thể làm ngưỡng 0.5 là đạt

# Hàm chính test
def run_test():
    print("=== BẮT ĐẦU TEST AI AGENT ===")
    questions = load_questions("questions.csv")
    results = []

    total = len(questions)
    correct = 0

    for idx, q in enumerate(questions, 1):
        print(f"\n[{idx}/{total}] Hỏi: {q['question']}")
        start_time = time.time()
        answer = ask_ollama(q["question"])
        elapsed = time.time() - start_time

        # Đánh giá mức độ tương đồng (đơn giản)
        score = evaluate_answer(q["question"], answer, q["expected"])
        is_acceptable = score >= 0.4  # ngưỡng 40% từ khóa xuất hiện

        # Thông tin kết quả
        result = {
            "id": q["id"],
            "question": q["question"],
            "expected": q["expected"],
            "answer": answer,
            "score": score,
            "acceptable": is_acceptable,
            "time": round(elapsed, 2)
        }
        results.append(result)

        if is_acceptable:
            correct += 1
            status = "✅ ĐẠT"
        else:
            status = "❌ CHƯA ĐẠT"

        print(f"   Đáp án mẫu: {q['expected']}")
        print(f"   Câu trả lời: {answer[:150]}...")
        print(f"   Điểm từ khóa: {score:.2f} - {status}")
        print(f"   Thời gian: {elapsed:.2f}s")

        # Nghỉ 1s để tránh quá tải
        time.sleep(1)

    # Tổng kết
    accuracy = correct / total * 100
    avg_time = sum(r["time"] for r in results) / total

    print("\n" + "="*50)
    print("=== KẾT QUẢ TỔNG HỢP ===")
    print(f"Tổng số câu hỏi: {total}")
    print(f"Số câu trả lời đạt yêu cầu: {correct}/{total}")
    print(f"Độ chính xác (thô): {accuracy:.2f}%")
    print(f"Thời gian phản hồi trung bình: {avg_time:.2f}s")

    # Lưu kết quả ra file CSV để báo cáo
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = f"test_results_{timestamp}.csv"
    with open(out_file, 'w', newline='', encoding='utf-8-sig') as f:
        fieldnames = ["id", "question", "expected", "answer", "score", "acceptable", "time"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"Kết quả đã lưu vào file: {out_file}")

    return results, accuracy

if __name__ == "__main__":
    run_test()