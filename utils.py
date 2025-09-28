import os

os.environ["CUDA_VISIBLE_DEVICES"] = "0"

import fitz
from sentence_transformers import SentenceTransformer
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
import markdown
import bleach
import re
import time
import ruptures as rpt
import json



# === load document ===

def create_chunks(words, chunk_size=500, stride=100):
    chunks = []
    for i in range(0, len(words) - chunk_size + 1, stride):
        chunk = " ".join(words[i:i + chunk_size])
        chunks.append(chunk)
    return chunks

def pdf_to_chunks(pdf_path, chunk_size=500, saved_data_path="saved_data"):
    
    print(f"Loading PDF from: {pdf_path}")
    doc = fitz.open(pdf_path)
    text = ""
    for i, page in enumerate(doc):
        page_text = page.get_text()
        print(f"Extracted text from page {i + 1} (length: {len(page_text)})", end="\r")
        text += page_text
    doc.close()

    words = text.split()
    print(f"Total words extracted: {len(words)}")

    chunks = create_chunks(words)
    print(f"Created {len(chunks)} chunks with chunk size {chunk_size}")

    return chunks

def txt_to_chunks(txt_path, chunk_size=500):
    print(f"Loading text file from: {txt_path}")
    with open(txt_path, "r", encoding="utf-8") as f:
        text = f.read()

    words = text.split()
    print(f"Total words extracted: {len(words)}")

    chunks = create_chunks(words)
    print(f"Created {len(chunks)} chunks with chunk size {chunk_size}")

    return chunks

from ebooklib import epub, ITEM_DOCUMENT
from bs4 import BeautifulSoup
def epub_to_chunks(epub_path, chunk_size=500):
    print(f"Loading EPUB file from: {epub_path}")
    book = epub.read_epub(epub_path)

    full_text = ""
    for item in book.get_items_of_type(ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        text = soup.get_text()
        full_text += text + " "

    words = full_text.split()
    print(f"Total words extracted: {len(words)}")

    chunks = create_chunks(words)
    print(f"Created {len(chunks)} chunks with chunk size {chunk_size}")

    return chunks

def file_path_to_chunks(file_path):
    if file_path.endswith('.epub'):
        return epub_to_chunks(file_path)
    elif file_path.endswith('.pdf'):
        return pdf_to_chunks(file_path)
    elif file_path.endswith('.txt'):
        return txt_to_chunks(file_path)
    else:
        raise ValueError("Unsupported file type. Only .pdf and .txt are allowed.")




# === embed chunks ===

def embed_chunks(chunks):
    print("Generating new embeddings using SentenceTransformer model")
    model = SentenceTransformer('all-MiniLM-L12-v2')
    # model = SentenceTransformer('all-mpnet-base-v2')

    print(f"Encoding {len(chunks)} chunks in batches...")
    all_embeddings = []
    for i in range(0, len(chunks), 50):
        batch = chunks[i:i+50]
        batch_embeddings = model.encode(batch, batch_size=8, show_progress_bar=True)
        all_embeddings.extend(batch_embeddings)

    embeddings = np.array(all_embeddings)
    print(f"Generated embeddings shape: {embeddings.shape}")

    return embeddings



# === clusterization ===

def get_breakpoints(embeddings, kernel="rbf", min_size=3):
    X = np.array(embeddings)

    model = rpt.KernelCPD(kernel=kernel, min_size=min_size)
    model.fit(X)

    breakpoints = model.predict(pen=4)

    if len(breakpoints) < 3:
        breakpoints = model.predict(pen=3)

    print(f"Total sections: {len(breakpoints)}")
    return breakpoints



# === cluster summarization utils ===

def get_top_k_indices(array, k):
    """Return the indices of the top-k values in the array."""
    return np.argsort(array)[-k:][::-1]

# def combine_sections(breakpoints, total_chunks, target_sections=12):
#     """
#     Recompute breakpoints to combine sections down to a target number.
#     """
#     chunks_per_section = total_chunks // target_sections
#     new_breakpoints = [0]
#     for i in range(1, target_sections):
#         new_breakpoints.append(i * chunks_per_section)
#     new_breakpoints.append(total_chunks)
#     return new_breakpoints




# === md to html utils ===

def escape_outside_inline_code(line):
    parts = re.split(r'(`[^`]*`)', line)  
    for i, part in enumerate(parts):
        if not part.startswith('`'):  
            parts[i] = bleach.clean(part)
    return ''.join(parts)

def escape_outside_code_blocks(text):
    result = []
    in_fenced_block = False
    fenced_delim = "```"

    for line in text.splitlines():
        if line.strip().startswith(fenced_delim):
            in_fenced_block = not in_fenced_block
            result.append(line)
            continue

        if not in_fenced_block:
            
            line = escape_outside_inline_code(line)
        result.append(line)

    return '\n'.join(result)

