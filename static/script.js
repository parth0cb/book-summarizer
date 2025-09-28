// Get DOM elements
const fileInput = document.getElementById('file-input');
const uploadFileButton = document.getElementById('upload-file-button');
const summarizeButton = document.getElementById('summarize-button');
const summaryOutputSection = document.getElementById('summary-output');
const fileNameElement = document.querySelector('.file-name');
const removeFileButton = document.getElementById('remove-file-button')
const stopButton = document.querySelector('.stop-button')
const tokensInMonitor = document.getElementById('tokens-in')
const tokensOutMonitor = document.getElementById('tokens-out')
const downloadPDFButton = document.getElementById('download-pdf-button')

// Enable summarize button on page load if a file was already uploaded
window.addEventListener('DOMContentLoaded', () => {
    const fileName = fileNameElement.textContent.trim();
    if (fileName) {
        summarizeButton.disabled = false;
    } else {
        removeFileUIChanges()
    }
});

// Enable file input when upload button is clicked
uploadFileButton.addEventListener('click', (e) => {
    e.preventDefault();
    fileInput.click();
});

// Update filename display when a file is selected
fileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        const file = e.target.files[0];
        const fileName = file.name;
        fileNameElement.textContent = fileName;
        summarizeButton.disabled = false;

        // Upload the file to Flask backend
        const formData = new FormData();
        formData.append('file', file);

        fetch('/upload', {
            method: 'POST',
            body: formData,
        })
        .then(response => {
            if (!response.ok) {
                throw new Error("Upload failed");
            }
            removeFileButton.style.display = "block";
            fileNameElement.classList.remove("no-file-selected");
            return response.json();
        })
        .catch(error => {
            console.error("Error:", error);
        });
    }
});

removeFileButton.addEventListener('click', (e) => {
    e.preventDefault();

    fetch('/remove', {
        method: 'POST'
    })
    .then(response => {
        if (!response.ok) {
            throw new Error("Remove request failed");
        }
        removeFileUIChanges();
    })
    .catch(error => {
        console.error("Error:", error);
    });
});

function removeFileUIChanges () {
    removeFileButton.style.display = "none";
    fileNameElement.innerHTML = "No File Selected";
    summarizeButton.disabled = true;
    fileNameElement.classList.add("no-file-selected")
};


// Handle summarize button click
summarizeButton.addEventListener('click', async () => {
    
    const fileName = fileNameElement.textContent;
    if (!fileName) return;

    summarizeButton.disabled = true;
    
    summaryOutputSection.innerHTML = '';
    
    downloadPDFButton.style.display = 'none'

    stopButton.style.display = 'flex';
    
    try {
        const response = await fetch(`/summarize_book_function`, {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // stream reading
        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');

        accumulatedData = '';
        
        // stream processing
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const value_str = decoder.decode(value, { stream: true });
            accumulatedData += value_str;
            
            const lines = accumulatedData.split('\n');
            accumulatedData = lines.pop();
            
            for (const line of lines) {
                if (!line.trim()) continue;

                try {
                    const { type, content } = JSON.parse(line);

                    switch (type) {
                        case 'main':
                            summaryOutputSection.innerHTML = content;
                            summaryOutputSection.scrollTop = summaryOutputSection.scrollHeight;
                            break;
                        case 'tokens':
                            const { tokensIn, tokensOut } = JSON.parse(content);
                            tokensInMonitor.innerHTML = `In: ${tokensIn}`;
                            tokensOutMonitor.innerHTML = `Out: ${tokensOut}`;
                            break;
                        case 'error':
                            summaryOutputSection.innerHTML = content;
                            break
                        case 'stop':
                            summaryOutputSection.innerHTML = content;
                        default:
                            console.warn('Unknown type:', type);
                    }
                } catch (err) {
                    console.error('JSON parse error:', err, value);
                }
            }
            
            downloadPDFButton.classList.remove('disable-link')
            summaryOutputSection.scrollTop = summaryOutputSection.scrollHeight;
        }
    } catch (error) {
        console.error('Error fetching summary:', error);
        summaryOutputSection.textContent = 'Error generating summary. Please try again.';
    }

    summarizeButton.disabled = false;

    stopButton.style.display = 'none'

    downloadPDFButton.style.display = 'block'
    
    summaryOutputSection.scrollTop = summaryOutputSection.scrollHeight;
});

stopButton.addEventListener('click', async () => {
    fetch("/stop_session", {
        method: "POST"
    })
})

function generatePDF() {
    const element = document.getElementById('summary-output');

    const clone = element.cloneNode(true);
    
    clone.querySelectorAll('*').forEach(el => {
        el.style.color = 'black';
    });
    
    const button = this;
    
    // Show loading state
    button.textContent = 'Generating PDF...';
    button.disabled = true;

    const fileName = fileNameElement.textContent.trim();
    
    // PDF options for optimal output
    const options = {
        margin: [10, 10, 10, 10], // top, left, bottom, right in mm
        filename: `Summary of ${fileName}.pdf`,
        image: { 
            type: 'jpeg', 
            quality: 0.98 
        },
        html2canvas: { 
            scale: 2,
            useCORS: true,
            letterRendering: true,
            allowTaint: false
        },
        jsPDF: { 
            unit: 'mm', 
            format: 'a4', 
            orientation: 'portrait',
            compress: true
        },
        pagebreak: { 
            mode: ['avoid-all', 'css', 'legacy'],
            before: '.page-break-before',
            after: '.page-break-after',
            avoid: '.no-page-break'
        }
    };
    
    // Generate PDF
    html2pdf()
        .set(options)
        .from(clone)
        .save()
        .then(() => {
            // Reset button state
            button.textContent = 'Download as PDF';
            button.disabled = false;
        })
        .catch((error) => {
            console.error('PDF generation failed:', error);
            button.textContent = 'Download as PDF';
            button.disabled = false;
            alert('Failed to generate PDF. Please try again.');
        });
}


