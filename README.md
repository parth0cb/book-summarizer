# Book Summarizer

A web application that automatically summarizes large documents using AI. The application processes the uploaded file (PDF, TXT, EPUB) and generates comprehensive summary using language model of your choice.

The uploaded document can be a fictional or a non-fictional book, or it can be some other large text document of allowed format.

## Demo

https://github.com/user-attachments/assets/d79aa561-fd36-4f9e-a7c8-d8717c8a2eab

## Features

- **Multi-format Support** (PDF, TXT, and EPUB)
- Handles **large documents** by breaking them into manageable sections.
- Groups related content using sentence embeddings for **smarter summarization**.
- More **coherent summaries** by analyzing sections before the full document.
- Connect to **any language model** API (OpenAI-compatible)
- **Monitor token usage** to manage costs and performance.
- Easily **download and share your summary as a polished PDF**.
- **Ability to stop** the summarization process at any time.

## Technical Architecture

### Backend (Flask)

The application is built on Flask and uses the following key components:

- **File Processing**: Handles uploads and extracts text from PDF, TXT, and EPUB files
- **Text Chunking**: Splits documents into overlapping chunks for analysis
- **Embedding Generation**: Uses SentenceTransformer (`all-MiniLM-L12-v2`) to create semantic embeddings
- **Clustering**: Uses the ruptures library to detect breakpoints in the document based on embedding similarity
- **Summarization Pipeline**: Implements a two-stage summarization process
- **Streaming Response**: Uses Flask's `Response` with `stream_with_context` for real-time updates

### Frontend

- **HTML/CSS/JavaScript**: Responsive interface with modern styling
- **Event-Driven**: Handles file uploads, summarization requests, and UI updates
- **Streaming Parser**: Processes the server's streaming response and updates the UI in real-time
- **PDF Generation**: Uses html2pdf.js to convert the summary to PDF format

## Installation and Setup

### Prerequisites

- Python 3.8+
- Node.js (for PDF generation functionality)
- pip package manager

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/parth0cb/book-summarizer.git
cd book-summarizer
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### 1. Start the Application

```bash
flask run
```

The application will be available at `http://localhost:5000` after few minutes.

### 2. Configure Language Model

On first launch, you'll be directed to the credentials page where you need to provide:

- **API Key**: Your language model provider's API key
- **Base URL**: The API endpoint (e.g., `https://api.openai.com/v1` for OpenAI)
- **Model Name**: The specific model to use (e.g., `gpt-3.5-turbo`, `gpt-4`, or any OpenAI-compatible model)

### 3. Upload a Document

Click "Upload Book" and select a PDF, TXT, or EPUB file from your device.

### 4. Generate Summary

Click the "Summarize" button to start the summarization process. The application will:

1. Split the document into chunks
2. Generate embeddings for each chunk
3. Cluster chunks into thematic sections
4. Summarize key content from each section
5. Generate a final comprehensive summary

### 5. Monitor Progress

- The interface shows real-time progress with loading messages
- Token usage is displayed and updated during processing
- You can stop the process at any time using the "Stop" button

### 6. Export Results

Click "Download as PDF" to save the generated summary as a PDF file.

## File Structure

```
book-summarizer/
├── app.py                    # Main Flask application
├── utils.py                  # Utility functions for text processing
├── static/                   # Static assets
│   ├── script.js             # Client-side JavaScript
│   ├── style.css             # Main stylesheet
│   └── llm_credentials_page.css  # Credentials page styling
├── templates/                # HTML templates
│   ├── index.html            # Main interface
│   └── credentials.html      # LLM credentials page
├── uploads/                  # Temporary storage for uploaded files
├── saved_data/               # (Optional) Persistent storage for processed data
└── requirements.txt          # Python dependencies
```

## Dependencies

- Flask - Web framework
- Flask-WTF - Form handling
- sentence-transformers - For generating text embeddings
- PyMuPDF (fitz) - PDF text extraction
- ebooklib - EPUB processing
- beautifulsoup4 - HTML parsing for EPUBs
- numpy - Numerical computations
- scikit-learn - Machine learning utilities
- sklearn - For cosine similarity calculations
- ruptures - Change point detection for clustering
- markdown - Markdown to HTML conversion
- bleach - HTML sanitization
- openai - OpenAI API client

## How It Works

### 1. Document Processing

When a file is uploaded, the application extracts all text content:

- **PDF**: Uses PyMuPDF (fitz) to extract text from each page
- **TXT**: Reads the entire file as plain text
- **EPUB**: Uses ebooklib to extract HTML content, then BeautifulSoup to extract text

### 2. Text Chunking

The extracted text is split into overlapping chunks (default: 500 words with 100-word stride) to maintain context between sections.

### 3. Semantic Analysis

Each chunk is converted into a semantic embedding using the SentenceTransformer model. This creates a numerical representation of the chunk's meaning.

### 4. Section Detection

The application uses change point detection (via the ruptures library) on the sequence of embeddings to identify natural breakpoints in the document. This clusters semantically similar chunks together, effectively dividing the document into thematic sections.

### 5. Hierarchical Summarization

The summarization occurs in two stages:

**Stage 1 - Section Summaries**
- For each detected section, the application identifies the 5 most representative chunks (using cosine similarity to the section centroid)
- These key chunks are sent to the language model for summarization
- This creates a summary of the main content for each section

**Stage 2 - Final Summary**
- All section summaries are combined and sent to the language model
- The model generates a comprehensive summary of the entire document
- The final output is formatted with Markdown for enhanced readability

### 6. Streaming Output

The application uses Flask's streaming response capability to send the summary in real-time as it's generated, providing immediate feedback to the user.

## Customization Options

- **Chunk Size**: Modify the `chunk_size` parameter in `utils.py` functions
- **Embedding Model**: Change the model in both `app.py` and `utils.py` (currently `all-MiniLM-L12-v2`)
- **Clustering Parameters**: Adjust `kernel` and `min_size` in `get_breakpoints()` function
- **Language Model Settings**: Temperature is set to 0.5 for balanced creativity and consistency

## Security Considerations

- **Input Validation**: File type checking ensures only supported formats are processed
- **Session Management**: LLM credentials are stored in Flask sessions
- **HTML Sanitization**: Uses bleach to sanitize any HTML output
- **Markdown Processing**: Carefully handles code blocks and inline code to prevent XSS
- **File Uploads**: Uploaded files are stored in a dedicated directory with proper permissions

## Troubleshooting

### Common Issues

**1. File Upload Fails**
- Ensure the file extension is .pdf, .txt, or .epub
- Check file size (very large files may cause timeouts)
- Verify the uploads directory has write permissions

**2. Summarization Stalls**
- Check your LLM API key and connectivity
- Verify the base URL is correct and accessible
- Ensure the model name is valid for your provider

**3. PDF Generation Fails**
- Ensure html2pdf.js is properly installed
- Check browser console for JavaScript errors
- Verify the summary content doesn't contain problematic HTML

## Future Enhancements

- **Multiple Language Support**: Extend to non-English documents
- **Custom Summarization Styles**: Options for different summary lengths and formats
- **API Endpoint**: Expose summarization as a REST API
- **Enhanced UI**: Progress bars, estimated time remaining
- **Batch Processing**: Handle multiple documents sequentially

## License

MIT