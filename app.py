import os
from flask import (
    Flask,
    request,
    render_template,
    send_from_directory,
    jsonify,
    Response,
    session,
    redirect,
    url_for,
    stream_with_context
)
from werkzeug.utils import secure_filename
from typing import TypedDict
from sentence_transformers import SentenceTransformer
import json
import markdown
from openai import OpenAI
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
import threading

import utils


UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"txt", "pdf", "epub"}

app = Flask(__name__)
app.secret_key = "secr9332j0fd92et"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

model = SentenceTransformer('all-MiniLM-L12-v2')

control_flags = {
    "stop": False
}
control_lock = threading.Lock()

def set_stop_flag(value: bool):
    with control_lock:
        control_flags["stop"] = value

def get_stop_flag() -> bool:
    with control_lock:
        return control_flags["stop"]



def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/")
def index():
    if not all(
        [session.get("api_key"), session.get("base_url"), session.get("language_model")]
    ):
        return redirect(url_for("get_credentials"))
    return render_template("index.html")


@app.route("/credentials", methods=["GET", "POST"])
def get_credentials():
    if request.method == "POST":
        session.clear()
        session["api_key"] = request.form["api_key"].strip()
        session["base_url"] = request.form["base_url"].strip()
        session["language_model"] = request.form["language_model"].strip()

        return redirect(url_for("index"))
    return render_template("credentials.html")


@app.route("/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file part", 400
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400
    if file and allowed_file(file.filename):
        # delete existing files in the upload folder
        for f in os.listdir(app.config["UPLOAD_FOLDER"]):
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], f)
            if os.path.isfile(file_path):
                os.remove(file_path)

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(filepath)
        return jsonify({"message": "File uploaded successfully", "filename": filename}), 200

    return "Invalid file type", 400

@app.route("/remove", methods=["POST"])
def remove_file():
    for f in os.listdir(app.config["UPLOAD_FOLDER"]):
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], f)
        if os.path.isfile(file_path):
            os.remove(file_path)
    return "Files removed", 200


@app.route("/summarize_book_function", methods=["POST"])
def summarize_book_function():
    if not all(k in session for k in ["api_key", "base_url", "language_model"]):
        return redirect(url_for("get_credentials"))

    upload_folder = app.config["UPLOAD_FOLDER"]
    files = os.listdir(upload_folder)
    if not files:
        return "No file found", 404

    file_path = os.path.join(upload_folder, files[0])

    set_stop_flag(False)

    @stream_with_context
    def generate():
        try:
            client = OpenAI(
                api_key=session["api_key"],
                base_url=session["base_url"]
            )
            
            total_tokens_in = 0
            total_tokens_out = 0
            
            def send_json(type_name, content):
                return json.dumps({"type": type_name, "content": content}) + "\n"
            
            def send_tokens():
                token_data = json.dumps({"tokensIn": total_tokens_in, "tokensOut": total_tokens_out})
                return send_json("tokens", token_data)
            
            def loading_message(message):
                html = (
                    '<div class="loading-wrapper">'
                    '<div class="spinner"></div>'
                    f'<span class="log-message">{message}</span>'
                    # '<div class="log-sub">(This may take few minutes)</div>'
                    '</div>'
                )
                return send_json("main", html)
            
            def stop_message_yield():
                html = "Stopped."
                return send_json("stop", html)
            
            yield loading_message("Splitting files into chunks...")
            chunks = utils.file_path_to_chunks(file_path)
                
            if get_stop_flag():
                yield stop_message_yield()
                return
            
            yield loading_message('Generating embeddings...')
            all_embeddings = []
            for i in range(0, len(chunks), 50):
                if get_stop_flag():
                    yield stop_message_yield()
                    return
                batch = chunks[i:i+50]
                batch_embeddings = model.encode(batch, batch_size=8, show_progress_bar=True)
                all_embeddings.extend(batch_embeddings)
            embeddings = np.array(all_embeddings)
                
            if get_stop_flag():
                yield stop_message_yield()
                return
            
            yield loading_message("Clustering embeddings...")
            breakpoints = utils.get_breakpoints(embeddings)
                
            if get_stop_flag():
                yield stop_message_yield()
                return
            
            yield loading_message(f"Analysing clusters...")
            summaries_of_sections = []
            
            for i in range(len(breakpoints)):
                
                if get_stop_flag():
                    yield stop_message_yield()
                    return

                start = 0 if i == 0 else breakpoints[i - 1]
                end = breakpoints[i]
                section_embeddings = embeddings[start:end]
                section_array = np.stack(section_embeddings)
                
                centroid = np.mean(section_array, axis=0, keepdims=True)
                similarities = cosine_similarity(section_array, centroid).flatten()
                top_indices = utils.get_top_k_indices(similarities, k=min(5, len(similarities)))
                global_indices = [start + idx for idx in top_indices]
                top_chunks = [chunks[idx] for idx in global_indices]
                
                combined_text = "\n\n".join(top_chunks)
                prompt = (
                    f"You are given the top 5 most relevant text chunks extracted from the book/document: \"{Path(file_path).name}\".\n"
                    "---\n"
                    "Chunks:\n"
                    f"{combined_text}\n"
                    "---\n"
                    "Please summarize the overall content of these excerpts in **one coherent paragraph**, capturing the key ideas, themes, and context. Respond with one paragraph."
                )
                            
                response = client.chat.completions.create(
                    model=session["language_model"],
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.5,
                    stream = True
                )

                content = ""
                for chunk in response:
                    if hasattr(chunk, 'usage') and chunk.usage:
                        total_tokens_in += chunk.usage.prompt_tokens or 0
                        total_tokens_out += chunk.usage.completion_tokens or 0
                        yield send_tokens()

                    if get_stop_flag():
                        yield stop_message_yield()
                        return
                        
                    content += chunk.choices[0].delta.content

                yield send_tokens()
                
                if get_stop_flag():
                    yield stop_message_yield()
                    return
                
                summaries_of_sections.append(content)
            
            summaries_of_sections_str = "\n\n".join(
                f"Summary of section {i}:\n{summary}" 
                for i, summary in enumerate(summaries_of_sections, 1)
            ) + "\n\n"
            
            yield loading_message("Generating final summary...")
            
            prompt = (
                "You are a book summarizer. Currently, you are summarizing: \"{Path(file_path).name}\"\n\n"

                "---\n"
                f"{summaries_of_sections_str}\n"
                "---\n\n"

                "Act as if you are summarizing the whole book/document.\n"
                "Give title to your response as follows: \"Summary of ...\".\n"
                "Do not hesitate making the summary detailed if there is alot of information.\n"
                "Make your response sound like a professional summary of the book/document.\n"
                "Apply md formatting for better readability."
            )

            response = client.chat.completions.create(
                model=session["language_model"],
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                stream=True
            )
            
            content = ""
            for chunk in response:
                if chunk.choices and chunk.choices[0].delta:
                    
                    if hasattr(chunk, 'usage') and chunk.usage:
                        total_tokens_in += chunk.usage.prompt_tokens or 0
                        total_tokens_out += chunk.usage.completion_tokens or 0
                        yield send_tokens()
                
                    if get_stop_flag():
                        return
                    
                    delta = chunk.choices[0].delta
                    if hasattr(delta, "content") and delta.content:
                        content += delta.content
                        content_to_yield = utils.escape_outside_code_blocks(content)
                        content_to_yield = content_to_yield.replace("\n- ", "\n\n- ")
                        content_to_yield = content_to_yield.replace("\n* ", "\n\n* ")
                        content_to_yield = markdown.markdown(content_to_yield, extensions=['fenced_code'])
                        yield send_json("main", content_to_yield)
            
            yield send_tokens()

        except Exception as e:
            error_html = f"<div class=\"error-message\"><p>An error occured: {str(e)}</p></div>"
            error_message = json.dumps({
                "type": "error",
                "content": error_html
            }) + "\n"
            yield error_message


    return Response(generate(), content_type="text/plain; charset=utf-8")


@app.route("/stop_session", methods=["POST"])
def stop_session():
    if not get_stop_flag():
        set_stop_flag(True)
        return "Session stopped", 200
    else:
        return "No active session to stop", 404


if __name__ == "__main__":
    import os
    os.environ["CUDA_VISIBLE_DEVICES"] = "0"
    app.run(debug=True, use_reloader=True, reloader_type="stat")

