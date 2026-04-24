import os
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
import sqlite3
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

EMBED_FN = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2", device="cpu")
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="messages", embedding_function=EMBED_FN)

def build_vector_index():
    conn = sqlite3.connect("messages.db")
    c = conn.cursor()
    c.execute("SELECT id, channel_name, author_name, content, timestamp FROM messages")
    rows = c.fetchall()
    conn.close()
    existing = set(collection.get()["ids"])
    docs, ids, metas = [], [], []
    for row in rows:
        msg_id = str(row[0])
        if msg_id in existing:
            continue
        docs.append(f"[#{row[1]}] {row[2]}: {row[3]}")
        ids.append(msg_id)
        metas.append({"channel": row[1], "author": row[2], "timestamp": row[4], "content": row[3]})
    if docs:
        for i in range(0, len(docs), 100):
            collection.add(documents=docs[i:i+100], ids=ids[i:i+100], metadatas=metas[i:i+100])
        print(f"✅ Indexed {len(docs)} messages")
    else:
        print("✅ Already up to date")

def add_message_to_index(msg_id, channel, author, content, timestamp):
    try:
        collection.add(
            documents=[f"[#{channel}] {author}: {content}"],
            ids=[str(msg_id)],
            metadatas=[{"channel": channel, "author": author, "timestamp": timestamp, "content": content}]
        )
    except Exception as e:
        print(f"Vector index error: {e}")

def search_messages_vector(query, n_results=20):
    try:
        total = collection.count()
        if total == 0:
            return ""
        results = collection.query(query_texts=[query], n_results=min(n_results, total))
        if not results["documents"][0]:
            return ""
        lines = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            lines.append(f"[{meta['timestamp']}] {doc}")
        header = f"=== RELEVANT MESSAGES (Total DB: {total}, shown: {len(lines)}) ===\n"
        return header + "\n".join(lines)
    except Exception as e:
        print(f"Vector search error: {e}")
        return ""
