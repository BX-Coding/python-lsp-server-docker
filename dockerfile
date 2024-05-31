# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the edited files into the container
COPY edits/jedi_completion.py /usr/local/lib/python3.11/site-packages/pylsp/plugins/jedi_completion.py
COPY edits/pyflakes_lint.py /usr/local/lib/python3.11/site-packages/pylsp/plugins/pyflakes_lint.py
COPY edits/plugin.py /usr/local/lib/python3.11/site-packages/pylsp_ruff/plugin.py

# Expose port 8000 for WebSocket
EXPOSE 8080

# Command to run the Python LSP server with WebSocket support on port 8000
CMD ["pylsp", "--ws", "--port", "8080"]
